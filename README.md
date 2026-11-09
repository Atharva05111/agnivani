# AgniVani — fire safety that speaks every worker's language

AgniVani (अग्निवाणी, "voice of fire") adds a multilingual voice layer to a plant's fire detection system, built on Gnani AI's speech models.

- **Alarms in every language on the shift.** When a zone goes into fire alarm, AgniVani sounds a siren and loops spoken evacuation instructions (zone, exit number, assembly point) in each language the supervisor has selected: Marathi, Hindi, English, Gujarati, Bengali, Punjabi, Tamil, Telugu, Kannada or Malayalam.
- **Code-mixed voice control.** Operators hold a button and ask in Marathi, Hindi, English or a mix ("Zone B ka temperature kitna hai?", "Pump chalu aahe ka?", "अलार्म बंद करा"). AgniVani answers out loud in the same language, and can silence or reset the alarm by voice.
- **The safety officer's own voice.** Record 15 seconds of the officer speaking; Gnani voice cloning then reads every announcement, in every language, in a voice the workers already know.
- **Plugs into real detectors.** Any detector (an edge flame-detection camera, an IoT gateway, a manual call point) can raise an alarm with one HTTP call.

## Gnani AI models used

| Model | Endpoint | Used for |
|---|---|---|
| Prisma v3.0 speech-to-text (falls back to v2.5) | `POST /stt/v3` with `language_code=hi-IN,mr-IN,en-IN`, `format=codemix` and plant `keyterms` | Transcribing operator questions, including code-mixed speech |
| Timbre v2.5 text-to-speech | `POST /api/v1/tts/inference` | Evacuation announcements in 10 Indian languages and spoken replies |
| Voice cloning (`vachana-vc-v1`) | `POST /api/v1/tts/voice-clone/embeddings` + inference | Announcements in the safety officer's voice |

## Run it (Windows)

1. Install Python 3.10 or newer.
2. Double-click `run.bat`. The first run creates a virtual environment, installs packages, and opens `.env` in Notepad.
3. Paste your key from https://app.gnani.ai/voice/api-keys after `GNANI_API_KEY=` and save. The key needs both Text to Speech and Speech to Text access.
4. Double-click `run.bat` again. The dashboard opens at http://localhost:8000.

Manual setup on any OS:

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env, then add your key
python scripts/test_gnani.py    # checks your key with one TTS and one STT call
uvicorn app.main:app --port 8000
```

Use Chrome or Edge. Allow microphone access when asked; browsers only allow the mic on `localhost` or HTTPS. Click anywhere on the page once so the browser allows the alarm sound.

## Try it

1. In **Shift setup**, pick the languages on the shift.
2. In **Run a drill**, click *Heat and smoke rise* on any zone. Readings climb, the zone turns amber, then red, and announcements start in each language.
3. Hold **Hold to talk** (or the space bar) and ask "Aag kahan lagi hai?" or "Warehouse se bahar kaise nikle?".
4. Say "alarm band karo" to silence it, or "reset" once the drill is over.

## Connecting a real detector

```bash
curl -X POST http://localhost:8000/api/events/detection \
  -H "Content-Type: application/json" \
  -d '{"zone": "B", "source": "camera", "confidence": 0.93}'
```

`source` is `camera`, `sensor` or `manual`. Set `EVENT_TOKEN` in `.env` to require an `X-Event-Token` header.

## How it works

```
mic (16 kHz WAV) ──> Prisma STT ──> language + intent matcher ──> plant state ──> reply text ──> Timbre TTS ──> speaker
detector / drill ──> alarm ──> announcement per shift language ──> Timbre or cloned voice ──> siren + looped playback
```

- `app/gnani.py` — async client for Prisma, Timbre and voice cloning.
- `app/intents.py` — understands questions in Devanagari, Latin script and mixed text. Keyword rules instead of an LLM keep answers deterministic, which matters in a safety system.
- `app/texts.py` — every spoken string, per language. Numbers are written out as words before synthesis so readings are pronounced correctly.
- `app/plant.py` — simulated zones and pump room; replace with a live feed in production.
- `static/` — the dashboard (plain HTML, CSS and JavaScript, no build step).

Run the tests with `python -m pytest`. `python scripts/eval_pipeline.py` measures the full speech path (Timbre, Prisma, intent engine) on clean and noisy audio; it uses API credits, and `--offline` re-scores saved transcripts for free.

## Language notes

Marathi, Hindi and English announcements and replies are complete. The Gujarati, Bengali, Punjabi, Tamil, Telugu, Kannada and Malayalam announcements should be checked by a native speaker before real use; they are all in `app/texts.py`.
