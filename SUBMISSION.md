# Submission kit

Edit anything that doesn't sound like you before pasting.

## Form fields

**Project title:** AgniVani — fire safety that speaks every worker's language

**The problem you are solving**
Indian factories and warehouses run on multilingual shifts. A worker from Pune, one from Kolkata and one from Chennai can stand on the same floor, yet fire alarms are a siren plus, at best, a Hindi or English announcement. In the first minutes of a fire, people who don't understand the instruction hesitate, go to the wrong exit, or wait for someone to translate. Control-room operators face the same gap the other way: checking a zone means reading a screen while the alarm is ringing.

**Who will use it**
Safety officers and control-room operators in manufacturing plants, warehouses and industrial parks, and the shop-floor workers who hear the announcements. It is designed to sit on top of an existing fire detection system (heat and smoke sensors, flame-detection cameras, manual call points).

**Gnani AI models / APIs used**
- Gnani Prisma v3.0 speech-to-text (`/stt/v3`, Hindi/Marathi/English language hints, `codemix` format and plant-specific `keyterms`), with automatic fallback to Prisma v2.5
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
- **Instant alarms.** Every zone's announcement is generated ahead of time for the languages on the shift and kept on disk, so an alarm has its voices ready in milliseconds and keeps working through a restart.
- **Fails safe.** "Alarm band mat karo" must never silence an alarm, even when speech recognition hears "mat" as "mute". Negated, questioning or ambiguous phrases only report the current state.
- **Measured on noisy speech.** I tuned Prisma's language hints, code-mix format and keyterms with an evaluation script that runs speech through Timbre, Prisma and the intent engine. On 20 phrases kept out of tuning, 19 were fully understood on clean audio and 18 with machinery noise added at 5 dB SNR and an 8 kHz phone band. The reply language was right on all 20 in both runs. The test speech is synthetic.

I work as a software engineer in the IoT division of a fire protection company, building industrial monitoring and edge fire detection systems, so this comes from a problem I see in real plants.

## LinkedIn post

> In a fire, every second a worker spends trying to understand the alarm is a second lost.
> 
> Indian factories run on multilingual shifts, but most fire alarms speak one language, if any.
> 
> So for the #GreatIndianAIInternshipChallenge I built AgniVani (अग्निवाणी): a voice layer for fire safety, built on Gnani AI's speech models.
> 
> 🔥 Evacuation orders in every language on the shift, chosen from 10 languages and ready the moment an alarm trips (Gnani Timbre TTS)
> 🎙️ Operators ask in code-mixed speech, like "Warehouse se bahar kaise nikle?", and hear the answer in the same language (Gnani Prisma v3.0 STT)
> 🛡️ "Alarm band mat karo" keeps the alarm on, even when speech recognition hears "mat" as "mute"
> 🗣️ Announcements can play in the safety officer's own cloned voice (Gnani voice cloning)
> 🔌 Any detector can raise an alarm with one API call
> 
> I measured it too. On 20 phrases kept out of tuning, it understood 19 on clean audio and 18 with factory noise over a phone-quality signal. The test speech was synthetic, so trials with real workers on a real floor come next.
> 
> The demo is below. Which language should it learn to answer in next?
> 
> @Gnani.ai
> 
> #GreatIndianAIInternshipChallenge #GnaniAI #FireSafety #VoiceAI #IndianLanguages

On LinkedIn, replace `@Gnani.ai` by typing `@Gnani` and picking the company page from the dropdown so the tag links. Upload the video natively rather than as a YouTube link.

## X post

> Fire alarms that speak one language fail multilingual shifts.
> 
> AgniVani gives evacuation orders in every language on the shift and answers code-mixed voice questions, built on @GnaniAi Prisma STT + Timbre TTS.
> 
> #GreatIndianAIInternshipChallenge #GnaniAI

Attach the video directly to the post.

## 60-second cut (for the Demo Day Drop award)

A recorded version is in `posting/agnivani-demo-60s.mp4`. Use this shot list to re-record it with your own voice.

1. **0:00–0:08 — Hook.** Over the idle dashboard: "In a fire, every second spent trying to understand the alarm is a second lost."
2. **0:08–0:28 — The fire.** Click *Camera sees flames* on Warehouse. The siren and announcements start at once. Let Marathi, Hindi and English each be heard briefly.
3. **0:28–0:45 — Code-mixed voice.** Ask "Warehouse se bahar kaise nikle?", then "Pump chalu aahe ka?". Let each reply play.
4. **0:45–0:53 — Safety.** Say "alarm band mat karo" and show the alarm staying on, then "alarm band karo" and show it silence.
5. **0:53–1:00 — Close.** "AgniVani, built on Gnani Prisma and Timbre."

## Demo video plan (about 2 minutes)

Record at 1080p with OBS or the Xbox Game Bar (Win+Alt+R). Turn on system audio capture so the announcements are recorded.

1. **0:00–0:15 — The problem.** Talk over the idle dashboard: multilingual shifts, single-language alarms.
2. **0:15–0:30 — Shift setup.** Select मराठी, हिंदी, English and বাংলা.
3. **0:30–1:00 — The fire.** Click *Heat and smoke rise* on Warehouse. Let the zone go amber, then red. The siren and announcements play in each language, with the current one highlighted. Leave about 15 seconds of audio.
4. **1:00–1:35 — Voice control.** Hold the mic and ask, in order: "Aag kahan lagi hai?", "Warehouse se bahar kaise nikle?", "Pump chalu aahe ka?". Let each reply play.
5. **1:35–1:50 — Officer voice.** Show the recorded officer voice playing an announcement. Record this ahead of time.
6. **1:50–2:00 — Close.** Say "alarm band karo", then "reset". Name the three Gnani APIs used.
