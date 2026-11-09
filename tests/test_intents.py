import pytest

from app.intents import answer, detect_language, parse
from app.plant import Plant
from app.texts import ANNOUNCEMENT, LANGUAGES, ZONE_NAMES, Num, announcement


@pytest.mark.parametrize("text,intent,zone", [
    ("Zone B ka temperature kitna hai?", "temperature", "B"),
    ("ज़ोन बी का तापमान कितना है?", "temperature", "B"),
    ("गोदाम मध्ये तापमान किती आहे?", "temperature", "B"),
    ("What's the smoke level in the server room?", "smoke", "C"),
    ("server room mein dhuan kitna hai", "smoke", "C"),
    ("Pump chalu aahe ka?", "pump", None),
    ("फायर पंप चालू है क्या", "pump", None),
    ("aag kahan lagi hai", "fire_where", None),
    ("आग कुठे लागली आहे?", "fire_where", None),
    ("canteen se bahar kaise nikle", "evacuate", "D"),
    ("प्रोडक्शन फ्लोअर मधून बाहेर कसं पडायचं?", "evacuate", "A"),
    ("alarm band karo", "silence", None),
    ("अलार्म बंद करा", "silence", None),
    ("reset the system", "reset", None),
    ("sab theek hai?", "status", None),
    ("How is the warehouse?", "status", "B"),
    ("header pressure kitna hai", "pressure", None),
    ("पाण्याची टाकी किती भरली आहे", "tank", None),
    ("tell me a joke", "unknown", None),
])
def test_parse(text, intent, zone):
    got = parse(text)
    assert (got.name, got.zone) == (intent, zone)


@pytest.mark.parametrize("text,detected,lang", [
    ("Zone B ka temperature kitna hai?", "en-IN", "hi-IN"),
    ("Pump chalu aahe ka?", None, "mr-IN"),
    ("गोदाम मध्ये तापमान किती आहे?", "hi-IN", "mr-IN"),
    ("ज़ोन बी का तापमान कितना है?", None, "hi-IN"),
    ("What's the smoke level in the server room?", "en-IN", "en-IN"),
    ("सिस्टम रीसेट", "mr-IN", "mr-IN"),
])
def test_language(text, detected, lang):
    assert detect_language(text, detected) == lang


def test_numbers_spoken():
    assert Num(48).spoken("hi-IN") == "अड़तालीस"
    assert Num(48).spoken("mr-IN") == "अठ्ठेचाळीस"
    assert Num(48).spoken("en-IN") == "forty eight"
    assert Num(6.4, 1).spoken("en-IN") == "six point four"
    assert Num(6.4, 1).display() == "6.4"


def test_language_packs_complete():
    for lang in LANGUAGES:
        assert lang in ANNOUNCEMENT
        for zid in ZONE_NAMES:
            assert ZONE_NAMES[zid][lang]
            assert "{" not in announcement(lang, zid, 2)


def test_answers_cover_every_intent_and_language():
    plant = Plant()
    for text in ["temperature", "smoke", "pump", "pressure", "tank", "exit", "aag kahan", "status", "warehouse",
                 "alarm band", "random words"]:
        for lang in ("mr-IN", "hi-IN", "en-IN"):
            display, spoken, _ = answer(parse(text), lang, plant)
            assert display and spoken and "{" not in display
    plant.ignite("B")
    for _ in range(15):
        plant.tick()
    assert plant.alarm and plant.alarm.zone == "B"
    display, spoken, _ = answer(parse("warehouse"), "en-IN", plant)
    assert "exit number 2" in display and "exit number two" in spoken
