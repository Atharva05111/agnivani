"""Understands operator questions in Marathi, Hindi, English and any mix of them.

Prisma returns transcripts in native script, Latin script or a mix of both
(code-mixed speech like "Zone B ka temperature kitna hai?"). Matching is done
with keyword sets that cover all three forms, so no extra LLM is needed and
answers stay deterministic, which matters in a safety system.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .plant import Plant
from .texts import MAIN_PUMP_STATE, PUMP_STATE, SOURCES, ZONE_NAMES, Num, render


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFC", text.lower())
    t = t.replace("़", "")          # nukta: ज़ -> ज
    t = t.replace("ँ", "ं")    # chandrabindu -> anusvara
    # Strip punctuation only. Devanagari vowel signs are combining marks (not \w), so keep category M*.
    t = "".join(" " if unicodedata.category(ch)[0] in "PSZ" else ch for ch in t)
    return re.sub(r"\s+", " ", t).strip()


# Latin keywords match whole words (plurals allowed), so "fire" is not "firefighter" and
# "marg" is not "marginal". The look-arounds also accept glued forms like "canteenमधून".
STEMS = {"evacuat", "nikal", "nikle"}


def _has(text: str, words) -> bool:
    for w in words:
        if w.isascii():
            end = "" if w in STEMS else r"s?(?![a-z])"
            if re.search(rf"(?<![a-z]){re.escape(w)}{end}", text):
                return True
        elif w in text:
            return True
    return False


# ------------------------------------------------------------ language
MR_WORDS = {"ahe", "aahe", "ahet", "aahet", "kiti", "kay", "madhe", "madhye", "madhun", "kuthe", "kara", "sanga", "sagla",
            "zala", "zali", "kela", "nako", "naka", "lagli", "lagla", "kasa", "kashi", "baher", "aani"}
MR_PARTS = ("आहे", "किती", "काय", "मध्ये", "मधून", "मधलं", "मधील", "कुठे", "करा", "सांगा", "सगळं", "सर्व", "कोणत्या", "पडू", "पडा",
            "बाहेर", "लागली", "नको", "नका", "कसं", "जायचं", "टाकी", "पाण्या", "झाला", "झाली", "केला", "करू")
HI_WORDS = {"hai", "hain", "kitna", "kitni", "kya", "mein", "kahan", "kahaan", "karo", "kar", "karna", "batao", "bata", "kaise",
            "kidhar", "kis", "kisi", "mat", "nahi", "nahin", "abhi", "hua", "gaya", "gayi", "ho", "se", "ko", "lagi", "sab",
            "में", "से", "को", "मत", "सब", "किस", "दो", "कर"}
HI_PARTS = ("है", "कितना", "कितनी", "क्या", "कहां", "करो", "बताओ", "बताइए", "कैसे", "किधर", "निकल", "लगी", "टंकी", "पानी",
            "करें", "कीजिए", "नहीं", "हुआ", "गया")
EN_WORDS = {"the", "is", "are", "what", "where", "how", "which", "there", "please", "not", "tell", "about", "give", "me"}
DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def detect_language(text: str, detected: str | None = None) -> str:
    """Pick the reply language: mr-IN, hi-IN or en-IN.

    Prisma derives its language tag from the script, so it cannot separate Hindi
    from Marathi. The words decide, and the tag only breaks a tie.
    """
    t = normalize(text)
    tokens = t.split()
    token_set = set(tokens)
    mr = len(MR_WORDS & token_set) + sum(1 for m in MR_PARTS if m in t)
    hi = len(HI_WORDS & token_set) + sum(1 for m in HI_PARTS if m in t)
    en = len(EN_WORDS & token_set)
    # "ka" ends a Marathi question ("pump chalu aahe ka") and links words in Hindi ("zone B ka temperature").
    if tokens and tokens[-1] in ("ka", "का"):
        mr += 1
    elif token_set & {"ka", "का"}:
        hi += 1
    if en > max(mr, hi):
        return "en-IN"
    if mr > hi:
        return "mr-IN"
    if hi > mr:
        return "hi-IN"
    if mr or DEVANAGARI.search(t):
        return detected if detected in ("mr-IN", "hi-IN") else "hi-IN"
    return "en-IN"


# ------------------------------------------------------------- intents
ZONE_WORDS = {
    "A": ("production", "प्रोडक्शन", "प्रॉडक्शन", "floor", "फ्लोर", "फ्लोअर", "assembly line"),
    "B": ("warehouse", "वेयरहाउस", "वेअरहाउस", "वेअरहाऊस", "गोदाम", "godown", "godam", "गोडाउन", "गोडाऊन", "store"),
    "C": ("server", "सर्वर", "सर्व्हर", "data centre", "data center"),
    "D": ("canteen", "कैंटीन", "कॅन्टीन", "कैन्टीन", "केंटीन", "cafeteria", "mess"),
}
ZONE_LETTER = re.compile(r"(?:zone|jone|जोन|झोन|ज़ोन)\s*(a|b|c|d|ए|बी|सी|डी|एक|दो|दोन|तीन|चार|1|2|3|4"
                         r"|one|two|three|four|ek|do|don|teen|char|bee|see|dee)(?=\s|$)")
LETTER_MAP = {"a": "A", "b": "B", "c": "C", "d": "D", "ए": "A", "बी": "B", "सी": "C", "डी": "D",
              "1": "A", "2": "B", "3": "C", "4": "D", "एक": "A", "दो": "B", "दोन": "B", "तीन": "C", "चार": "D",
              "bee": "B", "see": "C", "dee": "D", "one": "A", "two": "B", "three": "C", "four": "D", "ek": "A", "do": "B", "don": "B", "teen": "C", "char": "D"}

ALARM_WORDS = {"alarm", "siren", "hooter", "अलार्म", "अलाम", "सायरन", "भोंगा", "हूटर"}
OFF_WORDS = {"band", "bandh", "off", "बंद", "बन्द", "बैंड", "chup", "चुप"}
STOP_VERBS = {"stop", "shut", "kill"}
SWITCH_VERBS = {"turn", "switch"}
SILENCE = ("silence", "silenced", "mute", "muted", "acknowledge", "acknowledged")
RESET = ("reset", "रीसेट", "रिसेट", "all clear", "ऑल क्लियर")
RESET_FILLER = {"reset", "रीसेट", "रिसेट", "all", "clear", "ऑल", "क्लियर", "system", "सिस्टम", "सिस्टीम", "plant", "प्लांट", "alarm",
                "अलार्म", "fire", "फायर", "the", "please", "कृपया", "now", "ab", "अब", "abhi", "अभी", "ko", "को", "la", "ला", "karo",
                "करो", "kara", "करा", "kar", "कर", "करें", "कीजिए", "do", "दो", "de", "दे", "दीजिए"}
FIRE = ("fire", "aag", "आग", "फायर", "flame", "blaze")
WHERE = ("where", "which zone", "kahan", "kahaan", "kidhar", "kuthe", "कहां", "किधर", "कुठे", "कोणत्या", "किस")
EVAC = ("exit", "evacuat", "escape", "way out", "get out", "leave", "assembly", "असेंब्ली", "असेंबली", "bahar", "baher", "बाहर", "बाहेर", "nikle", "nikal", "निकल",
        "रास्ता", "रस्ता", "raasta", "rasta", "मार्ग", "marg", "route", "एग्जिट", "एक्झिट", "पडाय", "पडू")
TEMP = ("temperature", "temp", "तापमान", "टेम्परेचर", "टेंपरेचर", "टेम्प्रेचर", "टेम्पेरेचर", "garmi", "गर्मी", "गरमी", "उष्णता", "heat", "hot", "taapman", "tapman")
SMOKE = ("smoke", "धुआं", "धुंआ", "धुआ", "धुएं", "dhuan", "dhuaan", "dhua", "धूर", "धुर", "dhur", "स्मोक")
PUMP = ("pump", "पंप", "पम्प", "jockey", "जॉकी")
PRESSURE = ("pressure", "प्रेशर", "दबाव", "दाब", "dabav", "dabaav", "daab", "bar")
TANK = ("tank", "टैंक", "टंकी", "टाकी", "water", "पानी", "पाणी", "paani", "pani")
STATUS = ("status", "स्थिति", "स्थिती", "halat", "हालत", "situation", "report", "रिपोर्ट", "update", "अपडेट",
          "theek", "thik", "ठीक", "normal", "नॉर्मल", "सामान्य", "all good", "all ok", "all okay", "everything", "overall", "kaisa", "कैसा", "कसं", "kasa")

# Silence and reset change the alarm, so anything but a plain command only reports the state.
NEGATIONS = {"mat", "मत", "nako", "नको", "naka", "नका", "dont", "not", "never", "nahi", "nahin", "नहीं", "नाही"}
# Prisma can hear "band mat karo" as "band mute karo"; right after an off-word these mean "don't".
MISHEARD_MAT = {"mute", "म्यूट", "मैट", "mat", "मत"}
QUESTION_ANYWHERE = {"kya", "क्या", "kyu", "kyun", "kyon", "क्यों", "क्यूं", "kab", "कब", "kadhi", "कधी", "why", "when",
                     "who", "kaun", "कौन", "kon", "कोण", "koni", "कोणी", "should", "whether"}
QUESTION_FIRST = {"is", "was", "did", "has", "how", "does", "are"}
QUESTION_LAST = {"ka", "का", "hai", "है", "ahe", "aahe", "आहे"}
# Words that describe something already done: "alarm band ho gaya", "reset zala".
DONE_WORDS = {"hua", "हुआ", "gaya", "गया", "gayi", "गई", "zala", "झाला", "zali", "झाली", "kela", "केला", "diya", "दिया",
              "silenced", "muted", "acknowledged", "already"}


def _is_alarm(token: str) -> bool:
    return token in ALARM_WORDS or token.startswith("अलार्म") or token.startswith("सायरन")


def _says_silence(t: str) -> bool:
    """True for "alarm band karo", "alarm ko band", "shut off the alarm", "silence"."""
    tokens = t.split()
    for i, tok in enumerate(tokens):
        if _is_alarm(tok) and OFF_WORDS.intersection(tokens[i + 1:i + 4]):
            return True
        if tok in STOP_VERBS and any(_is_alarm(x) for x in tokens[i + 1:i + 4]):
            return True
        if tok in SWITCH_VERBS and "off" in tokens and any(_is_alarm(x) for x in tokens[i + 1:i + 4]):
            return True
    return _has(t, SILENCE)


def _is_command(t: str) -> bool:
    """False when the words negate the action, ask about it, or report it as done."""
    tokens = t.split()
    if "don t" in t or NEGATIONS.intersection(tokens) or QUESTION_ANYWHERE.intersection(tokens) or DONE_WORDS.intersection(tokens):
        return False
    if any(a in OFF_WORDS and b in MISHEARD_MAT for a, b in zip(tokens, tokens[1:])):
        return False
    return not tokens or (tokens[0] not in QUESTION_FIRST and tokens[-1] not in QUESTION_LAST)


# Prisma settings for the voice console, chosen with scripts/eval_pipeline.py. The hints separate
# Hindi from Marathi on short clips, and codemix keeps English words in Latin script.
STT_LANGUAGES = "hi-IN,mr-IN,en-IN"
STT_FORMAT = "codemix"
# Domain words sent to Prisma as keyterms, so short commands transcribe reliably.
STT_KEYTERMS = [
    "alarm", "siren", "reset", "silence", "temperature", "smoke", "pump", "jockey pump", "pressure",
    "tank", "exit", "assembly point", "warehouse", "production floor", "server room", "canteen", "zone",
    "अलार्म", "सायरन", "रीसेट", "तापमान", "धुआं", "धूर", "पंप", "प्रेशर", "टंकी", "टाकी", "एक्झिट",
    "गोदाम", "झोन", "ज़ोन", "आग",
]


@dataclass
class Intent:
    name: str
    zone: str | None = None


def find_zone(t: str) -> str | None:
    m = ZONE_LETTER.search(t)
    if m:
        return LETTER_MAP.get(m.group(1))
    for zid, words in ZONE_WORDS.items():
        if _has(t, words):
            return zid
    return None


def parse(text: str) -> Intent:
    t = normalize(text)
    zone = find_zone(t)
    wants_reset, wants_silence = _has(t, RESET), _says_silence(t)
    if wants_reset or wants_silence:
        # A reset clears a live fire alarm, so every other word must be plain filler ("reset password" is not it).
        if not _is_command(t) or (wants_reset and not RESET_FILLER.issuperset(t.split())):
            return Intent("status", zone)  # report the state, change nothing
        return Intent("reset" if wants_reset else "silence")
    if _has(t, EVAC) and not _has(t, TEMP + SMOKE + PUMP):
        return Intent("evacuate", zone)
    if _has(t, TEMP):
        return Intent("temperature", zone)
    if _has(t, SMOKE):
        return Intent("smoke", zone)
    if _has(t, PUMP):
        return Intent("pump")
    if _has(t, PRESSURE):
        return Intent("pressure")
    if _has(t, TANK):
        return Intent("tank")
    if _has(t, FIRE) or _has(t, WHERE):
        return Intent("fire_where", zone)
    if zone or _has(t, STATUS):
        return Intent("status", zone)
    return Intent("unknown")


# -------------------------------------------------------------- answers
def answer(intent: Intent, lang: str, plant: Plant) -> tuple[str, str, str | None]:
    """Return (display_text, spoken_text, action) where action is 'silence'|'reset'|None."""
    zones, pumps, alarm = plant.zones, plant.pumps, plant.alarm
    zone_id = intent.zone or (alarm.zone if alarm else None)

    def zn(zid: str) -> str:
        return ZONE_NAMES[zid][lang]

    if intent.name == "silence":
        return (*render("silenced" if alarm and not alarm.acknowledged else "nothing_to_silence", lang), "silence")
    if intent.name == "reset":
        return (*render("reset", lang), "reset")
    if intent.name in ("temperature", "smoke"):
        if not zone_id:  # no zone named: report the hottest / smokiest zone
            key = "temp" if intent.name == "temperature" else "smoke"
            zone_id = max(zones.values(), key=lambda z: getattr(z, key)).id
        z = zones[zone_id]
        value = Num(z.temp) if intent.name == "temperature" else Num(z.smoke, 1)
        return (*render(intent.name, lang, zone=zn(zone_id), value=value), None)
    if intent.name == "pump":
        return (*render("pump", lang, main=MAIN_PUMP_STATE[pumps.main_pump][lang], jockey=PUMP_STATE[pumps.jockey_pump][lang],
                        pressure=Num(pumps.pressure, 1)), None)
    if intent.name == "pressure":
        return (*render("pressure", lang, pressure=Num(pumps.pressure, 1)), None)
    if intent.name == "tank":
        return (*render("tank", lang, tank=Num(pumps.tank)), None)
    if intent.name == "evacuate":
        if not zone_id:
            return (*render("evacuate_which", lang), None)
        return (*render("evacuate", lang, zone=zn(zone_id), exit=Num(zones[zone_id].exit_no)), None)
    if intent.name == "fire_where":
        if alarm:
            return (*render("fire_active", lang, zone=zn(alarm.zone), source=SOURCES[alarm.source][lang],
                            main=MAIN_PUMP_STATE[pumps.main_pump][lang], pressure=Num(pumps.pressure, 1)), None)
        return (*render("no_fire", lang), None)
    if intent.name == "status":
        if intent.zone:
            z = zones[intent.zone]
            key = {"normal": "zone_normal", "warning": "zone_warning", "fire": "zone_fire"}[z.status]
            return (*render(key, lang, zone=zn(z.id), temp=Num(z.temp), smoke=Num(z.smoke, 1), exit=Num(z.exit_no)), None)
        if alarm:
            return (*render("fire_active", lang, zone=zn(alarm.zone), source=SOURCES[alarm.source][lang],
                            main=MAIN_PUMP_STATE[pumps.main_pump][lang], pressure=Num(pumps.pressure, 1)), None)
        return (*render("all_normal", lang, pressure=Num(pumps.pressure, 1), tank=Num(pumps.tank)), None)
    return (*render("help", lang), None)
