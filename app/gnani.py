"""Thin async client for Gnani's speech APIs.

- Prisma (speech-to-text):  POST {base}/stt/v3            (multipart)
- Timbre (text-to-speech):  POST {base}/api/v1/tts/inference (JSON -> WAV bytes)

Docs: https://docs.gnani.ai/api/introduction/quick-start
"""
from __future__ import annotations

import logging

import httpx

log = logging.getLogger("agnivani.gnani")


class GnaniError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def _error_text(resp: httpx.Response) -> str:
    try:
        data = resp.json()
    except ValueError:
        return resp.text[:300] or resp.reason_phrase
    if isinstance(data, dict):
        for key in ("message", "detail", "error", "error_code"):
            if data.get(key):
                val = data[key]
                return val if isinstance(val, str) else str(val)
    return str(data)[:300]


class GnaniClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.vachana.ai",
        tts_model: str = "timbre-v2.5",
        stt_model: str = "prisma-v3.0",
        timeout: float = 60.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.tts_model = tts_model
        self.stt_model = stt_model
        self._http = httpx.AsyncClient(timeout=timeout)

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise GnaniError("GNANI_API_KEY is not set. Add it to your .env file.")
        return {"X-API-Key-ID": self.api_key}

    async def close(self) -> None:
        await self._http.aclose()

    # ---------------------------------------------------------------- TTS
    async def tts(
        self,
        text: str,
        voice: str,
        language: str,
        speed: float = 1.0,
        sample_rate: int = 24000,
    ) -> bytes:
        """Synthesize `text` and return WAV bytes (Timbre v2.5)."""
        body = {
            "text": text,
            "voice": voice,
            "model": self.tts_model,
            "language": language,
            "speed": speed,
            "audio_config": {
                "sample_rate": sample_rate,
                "num_channels": 1,
                "sample_width": 2,
                "encoding": "linear_pcm",
                "container": "wav",
            },
        }
        resp = await self._http.post(
            f"{self.base_url}/api/v1/tts/inference",
            headers={**self._headers(), "Content-Type": "application/json"},
            json=body,
        )
        if resp.status_code != 200:
            raise GnaniError(f"Timbre TTS failed ({resp.status_code}): {_error_text(resp)}", resp.status_code)
        ctype = resp.headers.get("content-type", "")
        if "json" in ctype:  # some gateways return 200 + JSON error
            raise GnaniError(f"Timbre TTS returned JSON instead of audio: {_error_text(resp)}")
        return resp.content

    # ------------------------------------------------------- Voice cloning
    async def clone_embedding(self, audio: bytes, filename: str = "reference.wav") -> dict:
        """Upload 5-30 s of clear speech, get back a speaker embedding dict."""
        resp = await self._http.post(
            f"{self.base_url}/api/v1/tts/voice-clone/embeddings",
            headers=self._headers(),
            files={"audio_file": (filename, audio, "audio/wav")},
        )
        if resp.status_code != 200:
            raise GnaniError(f"Voice clone embedding failed ({resp.status_code}): {_error_text(resp)}", resp.status_code)
        data = resp.json()
        if not data.get("embedding"):
            raise GnaniError(f"Voice clone returned no embedding: {str(data)[:200]}")
        return {"embedding": data["embedding"], "shape": data.get("shape", [1, 768]), "dtype": data.get("dtype", "torch.bfloat16")}

    async def tts_cloned(self, text: str, speaker_embedding: dict, sample_rate: int = 44100) -> bytes:
        """Synthesize `text` in a cloned voice (model vachana-vc-v1)."""
        body = {
            "text": text,
            "model": "vachana-vc-v1",
            "audio_config": {
                "sample_rate": sample_rate,
                "num_channels": 1,
                "sample_width": 2,
                "encoding": "linear_pcm",
                "container": "wav",
            },
            "speaker_embedding": speaker_embedding,
        }
        resp = await self._http.post(
            f"{self.base_url}/api/v1/tts/inference",
            headers={**self._headers(), "Content-Type": "application/json"},
            json=body,
        )
        if resp.status_code != 200:
            raise GnaniError(f"Cloned-voice TTS failed ({resp.status_code}): {_error_text(resp)}", resp.status_code)
        if "json" in resp.headers.get("content-type", ""):
            raise GnaniError(f"Cloned-voice TTS returned JSON instead of audio: {_error_text(resp)}")
        return resp.content

    # ---------------------------------------------------------------- STT
    async def stt(
        self,
        audio: bytes,
        filename: str = "speech.wav",
        language_code: str = "indic-auto",
        fallback_language: str = "hi-IN",
    ) -> dict:
        """Transcribe a short clip. Returns {'transcript', 'language', 'model'}.

        Tries Prisma v3.0 with automatic language detection first. If that is
        rejected (for example the key is not enabled for v3.0), it falls back
        to Prisma v2.5 with a fixed language hint.
        """
        try:
            return await self._stt_once(audio, filename, self.stt_model, language_code)
        except GnaniError as exc:
            if self.stt_model == "prisma-v2.5" or (exc.status is not None and exc.status in (401, 403) and "scope" in str(exc).lower()):
                raise
            log.warning("Prisma %s failed (%s); retrying with prisma-v2.5", self.stt_model, exc)
            return await self._stt_once(audio, filename, "prisma-v2.5", fallback_language)

    async def _stt_once(self, audio: bytes, filename: str, model: str, language_code: str) -> dict:
        data = {"language_code": language_code}
        if model != "prisma-v2.5":
            data["model"] = model
        resp = await self._http.post(
            f"{self.base_url}/stt/v3",
            headers=self._headers(),
            files={"audio_file": (filename, audio, "audio/wav")},
            data=data,
        )
        if resp.status_code != 200:
            raise GnaniError(f"Prisma STT failed ({resp.status_code}): {_error_text(resp)}", resp.status_code)
        payload = resp.json()
        if payload.get("success") is False:
            raise GnaniError(f"Prisma STT error: {_error_text(resp)}")
        return {
            "transcript": (payload.get("transcript") or "").strip(),
            "language": payload.get("detected_language_code") or (language_code if language_code != "indic-auto" else None),
            "model": payload.get("model", model),
        }
