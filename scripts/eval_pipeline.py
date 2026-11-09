"""Measure the voice pipeline end to end: Timbre speech -> Prisma -> intent engine.

    python scripts/eval_pipeline.py                # clean and noisy runs
    python scripts/eval_pipeline.py --offline      # re-score saved transcripts, no API calls
    python scripts/eval_pipeline.py --holdout      # phrases not used for tuning, final setup only

Clips and transcripts are saved under data/eval/, so a phrase is only synthesized
and transcribed once per setup. The noisy runs mix in machinery noise at 5 dB SNR
and band-limit to 8 kHz, a rough stand-in for a phone on a factory floor. The
speech is synthetic, so treat the numbers as a comparison between setups.
"""
import argparse
import asyncio
import hashlib
import io
import json
import math
import os
import random
import sys
import wave
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv  # noqa: E402

from app.gnani import GnaniClient, GnaniError  # noqa: E402
from app.intents import STT_FORMAT, STT_KEYTERMS, STT_LANGUAGES, detect_language, parse  # noqa: E402

load_dotenv(ROOT / ".env")
OUT = ROOT / "data" / "eval"

HI_EN, HI, MR, MR2, EN = ("hi-en", "Poorvi"), ("hi-IN", "Bhavna"), ("mr-IN", "Zahira"), ("mr-IN", "Ishaan"), ("en-IN", "Devika")

# text, (tts language, voice), intent, zone, reply language
PHRASES = [
    ("Zone B ka temperature kitna hai?", HI_EN, "temperature", "B", "hi-IN"),
    ("Aag kahan lagi hai?", HI_EN, "fire_where", None, "hi-IN"),
    ("Warehouse se bahar kaise nikle?", HI_EN, "evacuate", "B", "hi-IN"),
    ("Alarm band karo", HI_EN, "silence", None, "hi-IN"),
    ("Alarm band mat karo", HI_EN, "status", None, "hi-IN"),
    ("Server room mein dhuan kitna hai?", HI_EN, "smoke", "C", "hi-IN"),
    ("Fire pump chalu hai kya?", HI_EN, "pump", None, "hi-IN"),
    ("पंप चालू आहे का?", MR, "pump", None, "mr-IN"),
    ("आग कुठे लागली आहे?", MR2, "fire_where", None, "mr-IN"),
    ("गोदाम मध्ये तापमान किती आहे?", MR, "temperature", "B", "mr-IN"),
    ("कॅन्टीन मधून बाहेर कसं पडायचं?", MR2, "evacuate", "D", "mr-IN"),
    ("अलार्म बंद करा", MR, "silence", None, "mr-IN"),
    ("अलार्म बंद करू नका", MR2, "status", None, "mr-IN"),
    ("सिस्टम रीसेट करा", MR, "reset", None, "mr-IN"),
    ("ज़ोन सी में धुआं कितना है?", HI, "smoke", "C", "hi-IN"),
    ("पानी की टंकी कितनी भरी है?", HI, "tank", None, "hi-IN"),
    ("सब ठीक है क्या?", HI, "status", None, "hi-IN"),
    ("What is the temperature in the canteen?", EN, "temperature", "D", "en-IN"),
    ("Is there a fire in the warehouse?", EN, "fire_where", "B", "en-IN"),
    ("Silence the alarm.", EN, "silence", None, "en-IN"),
    ("Do not reset the system.", EN, "status", None, "en-IN"),
    ("Reset the system.", EN, "reset", None, "en-IN"),
]

# Kept out of tuning: the intent rules were not adjusted against these.
HOLDOUT = [
    ("Canteen mein kitna dhuan hai?", HI_EN, "smoke", "D", "hi-IN"),
    ("Production floor ka status batao", HI_EN, "status", "A", "hi-IN"),
    ("Siren band kar do", HI_EN, "silence", None, "hi-IN"),
    ("Siren band mat karna", HI_EN, "status", None, "hi-IN"),
    ("Zone D se kaise nikle?", HI_EN, "evacuate", "D", "hi-IN"),
    ("Tank mein kitna paani hai?", HI_EN, "tank", None, "hi-IN"),
    ("सर्व्हर रूम मध्ये धूर किती आहे?", MR2, "smoke", "C", "mr-IN"),
    ("झोन ए ची स्थिती सांगा", MR, "status", "A", "mr-IN"),
    ("सायरन बंद करा", MR2, "silence", None, "mr-IN"),
    ("सायरन बंद करू नका", MR, "status", None, "mr-IN"),
    ("प्रेशर किती आहे?", MR2, "pressure", None, "mr-IN"),
    ("गोदामातून बाहेर कसं जायचं?", MR, "evacuate", "B", "mr-IN"),
    ("कैंटीन का तापमान बताओ", HI, "temperature", "D", "hi-IN"),
    ("क्या कहीं आग लगी है?", HI, "fire_where", None, "hi-IN"),
    ("अलार्म बंद मत करो", HI, "status", None, "hi-IN"),
    ("How much smoke is in zone A?", EN, "smoke", "A", "en-IN"),
    ("Which exit do I use from the server room?", EN, "evacuate", "C", "en-IN"),
    ("Turn off the siren.", EN, "silence", None, "en-IN"),
    ("Is the main pump running?", EN, "pump", None, "en-IN"),
    ("Who silenced the alarm?", EN, "status", None, "en-IN"),
]

SETUPS = {
    "auto": {"language_code": "indic-auto"},
    "hints": {"language_code": STT_LANGUAGES},
    "hints+codemix": {"language_code": STT_LANGUAGES, "fmt": STT_FORMAT},
    "hints+codemix+keyterms": {"language_code": STT_LANGUAGES, "fmt": STT_FORMAT, "keyterms": STT_KEYTERMS},
}
FINAL = "hints+codemix+keyterms"


def degrade(clean: bytes, seed: int) -> bytes:
    """Add machinery noise at 5 dB SNR and band-limit to 8 kHz."""
    with wave.open(io.BytesIO(clean)) as w:
        rate, pcm = w.getframerate(), array("h", w.readframes(w.getnframes()))
    rng = random.Random(seed)
    power = sum(x * x for x in pcm) / max(1, len(pcm))
    noise, state = [], 0.0
    for i in range(len(pcm)):
        state = 0.85 * state + rng.gauss(0, 1)
        noise.append(state + 3 * math.sin(2 * math.pi * 120 * i / rate))
    noise_power = sum(n * n for n in noise) / max(1, len(noise))
    gain = math.sqrt(power / (10 ** (5 / 10)) / max(1e-9, noise_power))
    mixed = [p + gain * n for p, n in zip(pcm, noise)]
    step = max(1, rate // 8000)
    low = array("h", (
        max(-32768, min(32767, int(sum(mixed[i:i + step]) / step)))
        for i in range(0, len(mixed) - step + 1, step)
    ))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate // step)
        w.writeframes(low.tobytes())
    return buf.getvalue()


def score(results: dict) -> None:
    print(f"\n{'setup':<34}{'intent':>10}{'language':>10}{'both':>10}")
    for name, rows in results.items():
        n = len(rows)
        intent = sum(r["intent_ok"] for r in rows)
        lang = sum(r["lang_ok"] for r in rows)
        both = sum(r["intent_ok"] and r["lang_ok"] for r in rows)
        print(f"{name:<34}{intent:>7}/{n}{lang:>7}/{n}{both:>7}/{n}")
    for name, rows in results.items():
        misses = [r for r in rows if not (r["intent_ok"] and r["lang_ok"])]
        if misses:
            print(f"\n{name}: misses")
            for r in misses:
                print(f"  said: {r['text']}\n  heard: {r['transcript']!r} [{r['detected']}] -> {r['got_intent']}/{r['got_zone']} {r['got_lang']}")


def judge(phrase, transcript: str, detected: str | None) -> dict:
    text, _, intent, zone, lang = phrase
    got = parse(transcript)
    got_lang = detect_language(transcript, detected)
    return {
        "text": text, "transcript": transcript, "detected": detected,
        "got_intent": got.name, "got_zone": got.zone, "got_lang": got_lang,
        "intent_ok": (got.name, got.zone) == (intent, zone), "lang_ok": got_lang == lang,
    }


def cache_path(setup: dict, text: str, noisy: bool) -> Path:
    key = json.dumps([setup, text, noisy], sort_keys=True, ensure_ascii=False)
    return OUT / "stt" / (hashlib.sha1(key.encode()).hexdigest()[:16] + ".json")


async def clip(client: GnaniClient, phrase) -> bytes:
    text, (lang, voice), *_ = phrase
    path = OUT / "clips" / (hashlib.sha1(f"{voice}|{lang}|{text}".encode()).hexdigest()[:16] + ".wav")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(await client.tts(text, voice, lang, sample_rate=16000))
    return path.read_bytes()


async def transcribe(client: GnaniClient, phrase, setup: dict, noisy: bool) -> dict:
    path = cache_path(setup, phrase[0], noisy)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    audio = await clip(client, phrase)
    if noisy:
        audio = degrade(audio, seed=int(hashlib.sha1(phrase[0].encode()).hexdigest()[:8], 16))
    got = await client._stt_once(audio, "clip.wav", "prisma-v3.0", setup["language_code"], setup.get("fmt"), setup.get("keyterms"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(got, ensure_ascii=False), encoding="utf-8")
    return got


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="only use saved transcripts")
    ap.add_argument("--holdout", action="store_true", help="score the held-out phrases on the final setup")
    ap.add_argument("--noisy-setups", default="auto,hints+codemix+keyterms", help="comma-separated setups to run on noisy audio")
    args = ap.parse_args()

    noisy_names = [n for n in args.noisy_setups.split(",") if n]
    runs = [(n, SETUPS[n], False) for n in SETUPS] + [(n, SETUPS[n], True) for n in noisy_names]
    phrases = PHRASES
    if args.holdout:
        phrases = HOLDOUT
        runs = [(FINAL, SETUPS[FINAL], False), (FINAL, SETUPS[FINAL], True)]
    client = GnaniClient(os.getenv("GNANI_API_KEY", "").strip())
    results: dict[str, list] = {}
    try:
        for name, setup, noisy in runs:
            label = f"{name} (noisy)" if noisy else name
            rows = []
            for phrase in phrases:
                if args.offline and not cache_path(setup, phrase[0], noisy).exists():
                    continue
                got = await transcribe(client, phrase, setup, noisy)
                rows.append(judge(phrase, got["transcript"], got["language"]))
            if rows:
                results[label] = rows
    except GnaniError as exc:
        print(f"Stopped: {exc}")
        if exc.status == 402:
            print("Out of credits. Saved transcripts can still be scored with --offline.")
    finally:
        await client.close()
    score(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
