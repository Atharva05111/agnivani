"""Check that your Gnani API key works before running the app.

    python scripts/test_gnani.py

Writes test_tts.wav (Marathi) and then transcribes it back with Prisma.
"""
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

from app.gnani import GnaniClient, GnaniError  # noqa: E402

load_dotenv(ROOT / ".env")


async def main() -> int:
    key = os.getenv("GNANI_API_KEY", "").strip()
    if not key:
        print("GNANI_API_KEY is empty. Copy .env.example to .env and paste your key.")
        return 1
    client = GnaniClient(key)
    try:
        text = "कृपया लक्ष द्या. गोदाम मध्ये आग लागली आहे."
        print("1/2  Timbre TTS (Marathi, voice Zahira)...")
        audio = await client.tts(text, "Zahira", "mr-IN", sample_rate=16000)
        out = ROOT / "test_tts.wav"
        out.write_bytes(audio)
        print(f"     OK, {len(audio):,} bytes written to {out.name}. Play it to check the voice.")

        print("2/2  Prisma STT on that audio...")
        result = await client.stt(audio, "test_tts.wav")
        print(f"     OK ({result['model']}, detected {result['language']}): {result['transcript']}")
        print("\nYour key works for both speech-to-text and text-to-speech.")
        return 0
    except GnaniError as exc:
        print(f"\nFailed: {exc}")
        if "scope" in str(exc).lower():
            print("Your key is missing a scope. Create a new key with both Text to Speech and Speech to Text turned on.")
        return 1
    finally:
        await client.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
