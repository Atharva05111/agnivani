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


def stt_request_body(**kwargs) -> bytes:
    seen = {}

    async def handler(request):
        seen["body"] = request.content
        return httpx.Response(200, json={"success": True, "transcript": "x", "model": "prisma-v3.0"})

    async def run():
        client = client_with(handler)
        await client.stt(b"RIFF", **kwargs)
        await client.close()

    asyncio.run(run())
    return seen["body"]


def test_stt_sends_hints_format_and_keyterms():
    body = stt_request_body(language_code="hi-IN,mr-IN", fmt="codemix", keyterms=["अलार्म"]).decode()
    assert "hi-IN,mr-IN" in body and "codemix" in body and "अलार्म" in body


def test_out_of_credit_does_not_fall_back():
    calls = 0

    async def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(402, json={"message": "no credit"})

    async def run():
        client = client_with(handler)
        try:
            await client.stt(b"RIFF")
        finally:
            await client.close()

    with pytest.raises(GnaniError, match="402"):
        asyncio.run(run())
    assert calls == 1


def test_clone_embedding_reads_nested_response():
    async def handler(request):
        inner = {"embedding": "AAAI", "shape": [1, 192], "dtype": "torch.float32"}
        return httpx.Response(200, json={"success": True, "data": {"voice_clone_embedding": inner}})

    async def run():
        client = client_with(handler)
        result = await client.clone_embedding(b"RIFF")
        await client.close()
        return result

    assert asyncio.run(run()) == {"embedding": "AAAI", "shape": [1, 192], "dtype": "torch.float32"}
