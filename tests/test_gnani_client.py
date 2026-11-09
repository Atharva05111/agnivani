import asyncio

import httpx
import pytest

from app.gnani import GnaniClient, GnaniError

WAV = {"content-type": "audio/wav"}


def client_with(handler, **kwargs) -> GnaniClient:
    client = GnaniClient("test-key", retry_delay=0, **kwargs)
    client._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return client


def test_requests_run_one_at_a_time():
    active = peak = 0

    async def handler(request):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        return httpx.Response(200, content=b"RIFF", headers=WAV)

    async def run():
        client = client_with(handler)
        results = await asyncio.gather(*(client.tts("x", "Zahira", "mr-IN") for _ in range(5)))
        await client.close()
        return results

    assert asyncio.run(run()) == [b"RIFF"] * 5
    assert peak == 1


def test_rate_limit_is_retried():
    calls = 0

    async def handler(request):
        nonlocal calls
        calls += 1
        if calls < 3:
            return httpx.Response(429, json={"message": "busy"})
        return httpx.Response(200, content=b"RIFF", headers=WAV)

    async def run():
        client = client_with(handler)
        audio = await client.tts("x", "Zahira", "mr-IN")
        await client.close()
        return audio

    assert asyncio.run(run()) == b"RIFF"
    assert calls == 3


def test_retries_stop_and_report_the_error():
    calls = 0

    async def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(429, json={"message": "busy"})

    async def run():
        client = client_with(handler, max_retries=2)
        try:
            await client.tts("x", "Zahira", "mr-IN")
        finally:
            await client.close()

    with pytest.raises(GnaniError, match="429"):
        asyncio.run(run())
    assert calls == 3


def test_auth_errors_are_not_retried():
    calls = 0

    async def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(401, json={"message": "bad key"})

    async def run():
        client = client_with(handler)
        try:
            await client.tts("x", "Zahira", "mr-IN")
        finally:
            await client.close()

    with pytest.raises(GnaniError, match="401"):
        asyncio.run(run())
    assert calls == 1


@pytest.mark.parametrize("error", [httpx.ConnectError("down"), httpx.ReadTimeout("slow")])
def test_network_failures_become_gnani_errors(error):
    async def handler(request):
        raise error

    async def run():
        client = client_with(handler, max_retries=1)
        try:
            await client.tts("x", "Zahira", "mr-IN")
        finally:
            await client.close()

    with pytest.raises(GnaniError):
        asyncio.run(run())
