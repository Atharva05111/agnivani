# Submission kit

Edit anything that doesn't sound like you before pasting.

## Form fields

**Project title:** AgniVani — fire safety that speaks every worker's language

**The problem you are solving**
Indian factories and warehouses run on multilingual shifts. A worker from Pune, one from Kolkata and one from Chennai can stand on the same floor, yet fire alarms are a siren plus, at best, a Hindi or English announcement. In the first minutes of a fire, people who don't understand the instruction hesitate, go to the wrong exit, or wait for someone to translate. Control-room operators face the same gap the other way: checking a zone means reading a screen while the alarm is ringing.

**Who will use it**
Safety officers and control-room operators in manufacturing plants, warehouses and industrial parks, and the shop-floor workers who hear the announcements. It is designed to sit on top of an existing fire detection system (heat and smoke sensors, flame-detection cameras, manual call points).

**Gnani AI models / APIs used**
- Gnani Prisma v3.0 speech-to-text (`/stt/v3`, `indic-auto`), with automatic fallback to Prisma v2.5
- Gnani Timbre v2.5 text-to-speech (`/api/v1/tts/inference`), 10 Indian languages
- Gnani voice cloning (`/api/v1/tts/voice-clone/embeddings` + `vachana-vc-v1`)

**Each member's contribution:** Solo project. I designed and built the full system: the Gnani integration, the multilingual intent engine, the language packs, the plant simulation and detector API, and the dashboard.

## Written project explanation

AgniVani adds a voice layer to fire detection, built entirely on Gnani AI's Indian-language speech models.

When a zone goes into alarm, AgniVani sounds a siren and loops spoken evacuation instructions, naming the zone, the exit number and the assembly point, in every language the supervisor has selected for that shift. Ten Indian languages are supported through Gnani Timbre. The safety officer can record 15 seconds of their own voice, and Gnani voice cloning then speaks every announcement in that familiar voice, in every language.

Operators control the system by voice. They hold a button and ask in Marathi, Hindi, English, or a mix of them, the way people actually talk on the floor: "Zone B ka temperature kitna hai?", "Pump chalu aahe ka?", "Canteen se bahar kaise nikle?". Gnani Prisma transcribes the speech and detects the language. AgniVani works out the question, reads the live plant data, and answers out loud in the same language through Timbre. Operators can also silence or reset the alarm by voice ("alarm band karo").

Design decisions:
- **Deterministic answers.** Questions are matched with keyword sets covering Devanagari, Latin and mixed script rather than a generative model, so the system never makes up a reading during an emergency.
- **Spoken numbers.** Readings are converted to words in each language before synthesis ("सत्तावन्न डिग्री"), following Gnani's input-formatting guidance, so temperatures and exit numbers are pronounced correctly.
- **Built to connect.** Any detector can raise an alarm with one HTTP call to `/api/events/detection`, so it plugs into existing sensors, IoT gateways or an edge flame-detection camera.
- **Low latency.** Announcements for all languages are generated in parallel and cached, and the siren covers generation time.

I work as a software engineer in the IoT division of a fire protection company, building industrial monitoring and edge fire detection systems, so this comes from a problem I see in real plants.

## LinkedIn / X post

> In a fire, every second a worker spends trying to understand the alarm is a second lost.
>
> Indian factories run on multilingual shifts, but most fire alarms speak one language, if any. So for the #GreatIndianAIInternshipChallenge I built AgniVani (अग्निवाणी): a voice layer for fire safety, built on @Gnani AI's speech models.
>
> 🔥 When a zone catches fire, evacuation instructions play in every language on the shift: Marathi, Hindi, English, Bengali, Tamil and more (Gnani Timbre TTS)
> 🎙️ Operators ask in code-mixed speech, like "Zone B ka temperature kitna hai?", and hear the answer back in their language (Gnani Prisma STT)
> 🗣️ Announcements can play in the safety officer's own cloned voice (Gnani voice cloning)
> 🔌 It plugs into real detectors (sensors, flame-detection cameras) through a simple API
>
> Demo below 👇
>
> #GnaniAI #GreatIndianAIInternshipChallenge #FireSafety #VoiceAI #IndianLanguages

On LinkedIn, type `@Gnani` and pick the company page from the dropdown so the tag links. Upload the video natively rather than as a YouTube link.

## Demo video plan (about 2 minutes)

Record at 1080p with OBS or the Xbox Game Bar (Win+Alt+R). Turn on system audio capture so the announcements are recorded.

1. **0:00–0:15 — The problem.** Talk over the idle dashboard: multilingual shifts, single-language alarms.
2. **0:15–0:30 — Shift setup.** Select मराठी, हिंदी, English and বাংলা.
3. **0:30–1:00 — The fire.** Click *Heat and smoke rise* on Warehouse. Let the zone go amber, then red. The siren and announcements play in each language, with the current one highlighted. Leave about 15 seconds of audio.
4. **1:00–1:35 — Voice control.** Hold the mic and ask, in order: "Aag kahan lagi hai?", "Warehouse se bahar kaise nikle?", "Pump chalu aahe ka?". Let each reply play.
5. **1:35–1:50 — Officer voice.** Show the recorded officer voice playing an announcement. Record this ahead of time.
6. **1:50–2:00 — Close.** Say "alarm band karo", then "reset". Name the three Gnani APIs used.
