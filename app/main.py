"""AgniVani: multilingual voice layer for fire safety, built on Gnani AI.

Run:  uvicorn app.main:app --reload
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from collections import OrderedDict
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .gnani import GnaniClient, GnaniError
from .intents import STT_FORMAT, STT_KEYTERMS, STT_LANGUAGES, answer, detect_language, parse
from .plant import Plant
from .texts import CONVERSATION_LANGS, LANGUAGES, announcement

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("agnivani")

DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
TTS_CACHE = DATA_DIR / "tts"
TTS_CACHE.mkdir(exist_ok=True)
OFFICER_FILE = DATA_DIR / "officer_voice.json"
EVENT_TOKEN = os.getenv("EVENT_TOKEN", "")

gnani = GnaniClient(
    api_key=os.getenv("GNANI_API_KEY", "").strip(),
    base_url=os.getenv("GNANI_BASE_URL", "https://api.vachana.ai"),
    tts_model=os.getenv("GNANI_TTS_MODEL", "timbre-v2.5"),
    stt_model=os.getenv("GNANI_STT_MODEL", "prisma-v3.0"),
)
VOICES = {code: os.getenv(f"VOICE_{code[:2].upper()}", voice) for code, (_, _, voice) in LANGUAGES.items()}

plant = Plant()


class State:
    shift_langs: list[str] = ["mr-IN", "hi-IN", "en-IN"]
    voice_mode: str = "timbre"            # timbre | officer
    officer_embedding: dict | None = None
    announcements: dict[str, dict] = {}   # lang -> {text, audio, voice, error}
    announcement_alarm_id: int | None = None


state = State()
if OFFICER_FILE.exists():
    try:
        state.officer_embedding = json.loads(OFFICER_FILE.read_text())
    except ValueError:
        pass

# ----------------------------------------------------------- audio cache
_audio: OrderedDict[str, bytes] = OrderedDict()
_audio_keys: dict[str, str] = {}


def _store(data: bytes) -> str:
    aid = hashlib.sha1(data).hexdigest()[:16]
    _audio[aid] = data
    _audio.move_to_end(aid)
    while len(_audio) > 300:
        _audio.popitem(last=False)
    return aid


async def speak(text: str, lang: str, officer: bool = False, persist: bool = False) -> tuple[str, str]:
    """Synthesize text, returning (audio_id, voice_label). Cached by voice+text.

    With persist, the audio is also kept on disk so announcements survive a
    restart and an alarm never waits on the network for a phrase already made.
    """
    voice = "officer" if officer else VOICES[lang]
    # A re-recorded officer voice must not reuse audio from the previous recording.
    speaker = hashlib.sha1(json.dumps(state.officer_embedding, sort_keys=True).encode()).hexdigest() if officer else voice
    key = hashlib.sha1(f"{gnani.tts_model}|{speaker}|{lang}|{text}".encode()).hexdigest()
    aid = _audio_keys.get(key)
    if aid and aid in _audio:
        return aid, voice
    path = TTS_CACHE / f"{key}.wav"
    if persist and path.exists():
        data = path.read_bytes()
    else:
        if officer:
            data = await gnani.tts_cloned(text, state.officer_embedding)
        else:
            data = await gnani.tts(text, VOICES[lang], lang)
        if persist:
            path.write_bytes(data)
    aid = _store(data)
    _audio_keys[key] = aid
    return aid, voice


async def build_announcements(alarm_id: int, zone_id: str) -> None:
    langs = list(state.shift_langs)
    use_officer = state.voice_mode == "officer" and state.officer_embedding is not None
    state.announcement_alarm_id = alarm_id
    exit_no = plant.zones[zone_id].exit_no
    state.announcements = {
        lang: {"text": announcement(lang, zone_id, exit_no), "audio": None, "voice": None, "error": None}
        for lang in langs
    }

    async def one(lang: str) -> None:
        entry = state.announcements[lang]
        try:
            entry["audio"], entry["voice"] = await speak(entry["text"], lang, officer=use_officer, persist=True)
        except GnaniError as exc:
            if use_officer:
                log.warning("Officer voice failed for %s (%s); using Timbre", lang, exc)
                try:
                    entry["audio"], entry["voice"] = await speak(entry["text"], lang, persist=True)
                    return
                except GnaniError as exc2:
                    exc = exc2
            entry["error"] = str(exc)
            log.error("Announcement TTS failed for %s: %s", lang, exc)

    await asyncio.gather(*(one(lang) for lang in langs))


async def prewarm_announcements() -> None:
    """Make every zone's announcement ahead of time, so an alarm speaks at once.

    Runs one phrase at a time, so a live question waits for at most one of them.
    """
    use_officer = state.voice_mode == "officer" and state.officer_embedding is not None
    try:
        for zone in plant.zones.values():
            for lang in list(state.shift_langs):
                await speak(announcement(lang, zone.id, zone.exit_no), lang, officer=use_officer, persist=True)
    except GnaniError as exc:
        log.warning("Could not prepare announcements ahead of time: %s", exc)


_prewarm_task: asyncio.Task | None = None


def schedule_prewarm() -> None:
    global _prewarm_task
    if _prewarm_task:
        _prewarm_task.cancel()
    if gnani.configured:
        _prewarm_task = asyncio.create_task(prewarm_announcements())


def on_new_alarm() -> None:
    if plant.alarm:
        asyncio.create_task(build_announcements(plant.alarm.id, plant.alarm.zone))


async def ticker() -> None:
    while True:
        await asyncio.sleep(1.0)
        if plant.tick():
            on_new_alarm()


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(ticker())
    if not gnani.configured:
        log.warning("GNANI_API_KEY is missing. Copy .env.example to .env and add your key.")
    schedule_prewarm()
    yield
    task.cancel()
    if _prewarm_task:
        _prewarm_task.cancel()
    await gnani.close()


app = FastAPI(title="AgniVani", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
async def index():
    return FileResponse(ROOT / "static" / "index.html")


# ------------------------------------------------------------------ state
@app.get("/api/state")
async def get_state():
    snap = plant.snapshot()
    ann = []
    if plant.alarm and state.announcement_alarm_id == plant.alarm.id:
        ann = [{"lang": lang, **v, "audio": f"/api/audio/{v['audio']}" if v["audio"] else None}
               for lang, v in state.announcements.items()]
    return {
        **snap,
        "announcements": ann,
        "settings": {
            "shift_langs": state.shift_langs,
            "voice_mode": state.voice_mode,
            "officer_voice_ready": state.officer_embedding is not None,
            "gnani_configured": gnani.configured,
        },
        "languages": [{"code": c, "native": n, "english": e} for c, (n, e, _) in LANGUAGES.items()],
    }


@app.get("/api/audio/{aid}")
async def get_audio(aid: str):
    data = _audio.get(aid)
    if data is None:
        raise HTTPException(404, "Audio expired. Ask again to regenerate it.")
    return Response(data, media_type="audio/wav", headers={"Cache-Control": "max-age=3600"})


# ----------------------------------------------------------------- drills
class ZoneReq(BaseModel):
    zone: str


def _zone(z: str) -> str:
    z = z.upper()
    if z not in plant.zones:
        raise HTTPException(400, f"Unknown zone {z}. Use A, B, C or D.")
    return z


@app.post("/api/drill/start")
async def drill_start(req: ZoneReq):
    plant.ignite(_zone(req.zone))
    return {"ok": True}


@app.post("/api/drill/camera")
async def drill_camera(req: ZoneReq):
    z = _zone(req.zone)
    plant.ignite(z)
    had = plant.alarm
    plant.raise_alarm(z, "camera", confidence=0.94)
    if had is None:
        on_new_alarm()
    return {"ok": True}


class DetectionEvent(BaseModel):
    zone: str
    source: str = "camera"
    confidence: float | None = None


@app.post("/api/events/detection")
async def detection_event(ev: DetectionEvent, x_event_token: str | None = Header(default=None)):
    """Hook for real detectors (edge flame camera, IoT gateway, manual call point)."""
    if EVENT_TOKEN and x_event_token != EVENT_TOKEN:
        raise HTTPException(401, "Invalid X-Event-Token")
    z = _zone(ev.zone)
    source = ev.source if ev.source in ("sensor", "camera", "manual") else "camera"
    had = plant.alarm
    plant.raise_alarm(z, source, ev.confidence)
    if had is None:
        on_new_alarm()
    return {"ok": True, "alarm_id": plant.alarm.id}


@app.post("/api/alarm/silence")
async def silence():
    return {"ok": plant.acknowledge()}


@app.post("/api/reset")
async def reset():
    plant.reset()
    state.announcements, state.announcement_alarm_id = {}, None
    return {"ok": True}


# --------------------------------------------------------------- settings
class Settings(BaseModel):
    shift_langs: list[str] | None = None
    voice_mode: str | None = None


@app.post("/api/settings")
async def update_settings(s: Settings):
    if s.shift_langs is not None:
        langs = [l for l in s.shift_langs if l in LANGUAGES]
        if not langs:
            raise HTTPException(400, "Pick at least one language for the shift.")
        state.shift_langs = langs
    if s.voice_mode is not None:
        if s.voice_mode == "officer" and state.officer_embedding is None:
            raise HTTPException(400, "Record the safety officer's voice first.")
        state.voice_mode = "officer" if s.voice_mode == "officer" else "timbre"
    if plant.alarm:  # regenerate live announcements with the new settings
        await build_announcements(plant.alarm.id, plant.alarm.zone)
    schedule_prewarm()
    return {"ok": True}


@app.post("/api/officer-voice")
async def officer_voice(audio: UploadFile = File(...)):
    data = await audio.read()
    if len(data) < 16000 * 2 * 4:
        raise HTTPException(400, "Recording is too short. Speak clearly for at least 5 seconds.")
    try:
        state.officer_embedding = await gnani.clone_embedding(data, audio.filename or "reference.wav")
    except GnaniError as exc:
        raise HTTPException(502, str(exc)) from exc
    OFFICER_FILE.write_text(json.dumps(state.officer_embedding))
    state.voice_mode = "officer"
    schedule_prewarm()
    preview_text = "कृपया लक्ष द्या. ही अग्निवाणी प्रणालीची चाचणी आहे."
    preview, error = None, None
    try:
        aid, _ = await speak(preview_text, "mr-IN", officer=True)
        preview = f"/api/audio/{aid}"
    except GnaniError as exc:
        error = str(exc)
    return {"ok": True, "preview": preview, "preview_text": preview_text, "error": error}


@app.delete("/api/officer-voice")
async def delete_officer_voice():
    state.officer_embedding, state.voice_mode = None, "timbre"
    OFFICER_FILE.unlink(missing_ok=True)
    return {"ok": True}


# ---------------------------------------------------------------- console
class AskText(BaseModel):
    text: str
    lang: str | None = None  # force a reply language; None = auto


async def _respond(transcript: str, detected: str | None, forced: str | None) -> dict:
    lang = forced if forced in CONVERSATION_LANGS else detect_language(transcript, detected)
    intent = parse(transcript)
    display, spoken, action = answer(intent, lang, plant)
    if action == "silence":
        plant.acknowledge()
    elif action == "reset":
        plant.reset()
        state.announcements, state.announcement_alarm_id = {}, None
    audio, tts_error = None, None
    try:
        aid, _ = await speak(spoken, lang)
        audio = f"/api/audio/{aid}"
    except GnaniError as exc:
        tts_error = str(exc)
    return {"transcript": transcript, "detected_language": detected, "reply_language": lang,
            "intent": intent.name, "zone": intent.zone, "reply": display, "audio": audio, "tts_error": tts_error}


@app.post("/api/ask/audio")
async def ask_audio(audio: UploadFile = File(...), lang: str | None = Form(default=None)):
    data = await audio.read()
    if len(data) < 16000:  # ~0.5 s of 16 kHz PCM
        raise HTTPException(400, "That recording was too short. Hold the button and speak your question.")
    try:
        stt = await gnani.stt(data, audio.filename or "speech.wav", language_code=STT_LANGUAGES, fmt=STT_FORMAT, keyterms=STT_KEYTERMS)
    except GnaniError as exc:
        raise HTTPException(502, str(exc)) from exc
    if not stt["transcript"]:
        raise HTTPException(422, "No speech was recognised. Try again a little closer to the mic.")
    return await _respond(stt["transcript"], stt["language"], lang) | {"stt_model": stt["model"]}


@app.post("/api/ask/text")
async def ask_text(req: AskText):
    if not req.text.strip():
        raise HTTPException(400, "Type a question first.")
    return await _respond(req.text.strip(), None, req.lang)
