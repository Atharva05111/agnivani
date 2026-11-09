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


def _has(text: str, words) -> bool:
    for w in words:
        if w.isascii():
            if re.search(rf"\b{re.escape(w)}", text):
                return True
        elif w in text:
            return True
    return False


# ------------------------------------------------------------ language
MR_MARKERS = ("आहे", "किती", "काय", "मध्ये", "कुठे", "करा", "सांगा", "सगळं", "आहेत", "चालू आहे", "बंद करा",
              "कोणत्या", "पडू", "ahe", "aahe", "kiti", "kay", "madhe", "madhye", "kuthe", "kara", "sanga", "sagla")
HI_MARKERS = ("है", "कितना", "कितनी", "क्या", "में", "कहां", "करो", "बताओ", "बताइए", "सब", "किस", "निकलें", "कैसे",
              "hai", "kitna", "kitni", "kya", "mein", "kahan", "kahaan", "karo", "batao", "bata", "kaise", "kidhar", "kis")
DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def detect_language(text: str, detected: str | None = None) -> str:
    """Pick the reply language: mr-IN, hi-IN or en-IN."""
    t = normalize(text)
    mr = sum(1 for m in MR_MARKERS if _has(t, [m]))
    hi = sum(1 for m in HI_MARKERS if _has(t, [m]))
    if detected == "mr-IN":
        mr += 2
    elif detected == "hi-IN":
        hi += 2
    if mr > hi:
        return "mr-IN"
    if hi > mr:
        return "hi-IN"
    if mr and mr == hi:
        return detected if detected in ("mr-IN", "hi-IN") else "hi-IN"
    if DEVANAGARI.search(t):
        return detected if detected in ("mr-IN", "hi-IN") else "hi-IN"
    return "en-IN"


# ------------------------------------------------------------- intents
ZONE_WORDS = {
    "A": ("production", "प्रोडक्शन", "प्रॉडक्शन", "floor", "फ्लोर", "फ्लोअर", "assembly line"),
    "B": ("warehouse", "वेयरहाउस", "वेअरहाउस", "वेअरहाऊस", "गोदाम", "godown", "godam", "गोडाउन", "गोडाऊन", "store"),
    "C": ("server", "सर्वर", "सर्व्हर", "data centre", "data center"),
    "D": ("canteen", "कैंटीन", "कॅन्टीन", "कैन्टीन", "केंटीन", "cafeteria", "mess"),
}
ZONE_LETTER = re.compile(r"(?:zone|jone|जोन|झोन|ज़ोन)\s*(a|b|c|d|ए|बी|सी|डी|एक|दो|दोन|तीन|चार|1|2|3|4)(?=\s|$)")
LETTER_MAP = {"a": "A", "b": "B", "c": "C", "d": "D", "ए": "A", "बी": "B", "सी": "C", "डी": "D",
              "1": "A", "2": "B", "3": "C", "4": "D", "एक": "A", "दो": "B", "दोन": "B", "तीन": "C", "चार": "D"}

SILENCE = ("silence", "mute", "acknowledge", "alarm band", "alarm bandh", "alarm off", "siren band", "siren off",
           "अलार्म बंद", "सायरन बंद", "सायरन बन्द", "अलार्म बन्द", "stop alarm", "stop the alarm")
RESET = ("reset", "रीसेट", "रिसेट", "all clear", "ऑल क्लियर")
FIRE = ("fire", "aag", "आग", "फायर", "flame", "blaze")
WHERE = ("where", "which zone", "kahan", "kahaan", "kidhar", "kuthe", "कहां", "किधर", "कुठे", "कोणत्या", "किस")
EVAC = ("exit", "evacuat", "escape", "way out", "bahar", "baher", "बाहर", "बाहेर", "nikle", "nikal", "निकल",
        "रास्ता", "raasta", "rasta", "मार्ग", "marg", "route", "एग्जिट", "एक्झिट", "पड")
TEMP = ("temperature", "temp", "तापमान", "टेम्परेचर", "टेंपरेचर", "टेम्प्रेचर", "टेम्पेरेचर", "garmi", "गर्मी", "heat", "hot", "taapman", "tapman")
SMOKE = ("smoke", "धुआं", "धुंआ", "धुआ", "धुएं", "dhuan", "dhuaan", "dhua", "धूर", "dhur", "स्मोक")
PUMP = ("pump", "पंप", "पम्प", "jockey", "जॉकी")
PRESSURE = ("pressure", "प्रेशर", "दबाव", "दाब", "dabav", "dabaav", "daab", "bar")
TANK = ("tank", "टैंक", "टंकी", "टाकी", "water", "पानी", "पाणी", "paani", "pani")
STATUS = ("status", "स्थिति", "स्थिती", "halat", "हालत", "situation", "report", "रिपोर्ट", "update", "अपडेट",
          "sab theek", "sab thik", "सब ठीक", "सगळं ठीक", "everything", "overall", "kaisa", "कैसा", "कसं", "kasa")


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
    if _has(t, RESET):
        return Intent("reset")
    if _has(t, SILENCE):
        return Intent("silence")
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
