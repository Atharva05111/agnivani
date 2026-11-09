"""Language packs: voices, zone names, evacuation announcements and replies.

Every string a worker hears lives here, so a native speaker can review and
fix wording without touching any logic. Numbers in spoken text are written
out as words (Gnani's input-formatting guidance), while the screen shows
digits.
"""
from __future__ import annotations

from dataclasses import dataclass

# code -> (display name in its own script, English name, default Timbre v2.5 voice)
LANGUAGES: dict[str, tuple[str, str, str]] = {
    "mr-IN": ("मराठी", "Marathi", "Zahira"),
    "hi-IN": ("हिंदी", "Hindi", "Nalini"),
    "en-IN": ("English", "English", "Kaveri"),
    "gu-IN": ("ગુજરાતી", "Gujarati", "Falak"),
    "bn-IN": ("বাংলা", "Bengali", "Kirra"),
    "pa-IN": ("ਪੰਜਾਬੀ", "Punjabi", "Mehuli"),
    "ta-IN": ("தமிழ்", "Tamil", "Asmita"),
    "te-IN": ("తెలుగు", "Telugu", "Suhana"),
    "kn-IN": ("ಕನ್ನಡ", "Kannada", "Saanvi"),
    "ml-IN": ("മലയാളം", "Malayalam", "Reshma"),
}

# Languages the voice console can answer in (query understanding is tuned for these).
CONVERSATION_LANGS = ("mr-IN", "hi-IN", "en-IN")

ZONE_NAMES: dict[str, dict[str, str]] = {
    "A": {"en-IN": "production floor", "hi-IN": "प्रोडक्शन फ्लोर", "mr-IN": "प्रोडक्शन फ्लोअर",
          "gu-IN": "પ્રોડક્શન ફ્લોર", "bn-IN": "প্রোডাকশন ফ্লোর", "pa-IN": "ਪ੍ਰੋਡਕਸ਼ਨ ਫਲੋਰ",
          "ta-IN": "ப்ரொடக்ஷன் ஃப்ளோர்", "te-IN": "ప్రొడక్షన్ ఫ్లోర్", "kn-IN": "ಪ್ರೊಡಕ್ಷನ್ ಫ್ಲೋರ್",
          "ml-IN": "പ്രൊഡക്ഷൻ ഫ്ലോർ"},
    "B": {"en-IN": "warehouse", "hi-IN": "गोदाम", "mr-IN": "गोदाम",
          "gu-IN": "ગોડાઉન", "bn-IN": "গুদাম", "pa-IN": "ਗੋਦਾਮ",
          "ta-IN": "கிடங்கு", "te-IN": "గోడౌన్", "kn-IN": "ಗೋದಾಮು", "ml-IN": "ഗോഡൗൺ"},
    "C": {"en-IN": "server room", "hi-IN": "सर्वर रूम", "mr-IN": "सर्व्हर रूम",
          "gu-IN": "સર્વર રૂમ", "bn-IN": "সার্ভার রুম", "pa-IN": "ਸਰਵਰ ਰੂਮ",
          "ta-IN": "சர்வர் ரூம்", "te-IN": "సర్వర్ రూమ్", "kn-IN": "ಸರ್ವರ್ ರೂಮ್", "ml-IN": "സെർവർ റൂം"},
    "D": {"en-IN": "canteen", "hi-IN": "कैंटीन", "mr-IN": "कॅन्टीन",
          "gu-IN": "કેન્ટીન", "bn-IN": "ক্যান্টিন", "pa-IN": "ਕੈਂਟੀਨ",
          "ta-IN": "கேன்டீன்", "te-IN": "క్యాంటీన్", "kn-IN": "ಕ್ಯಾಂಟೀನ್", "ml-IN": "കാന്റീൻ"},
}

SMALL_NUMBERS: dict[str, list[str]] = {
    "en-IN": ["zero", "one", "two", "three", "four"],
    "hi-IN": ["शून्य", "एक", "दो", "तीन", "चार"],
    "mr-IN": ["शून्य", "एक", "दोन", "तीन", "चार"],
    "gu-IN": ["શૂન્ય", "એક", "બે", "ત્રણ", "ચાર"],
    "bn-IN": ["শূন্য", "এক", "দুই", "তিন", "চার"],
    "pa-IN": ["ਸਿਫ਼ਰ", "ਇੱਕ", "ਦੋ", "ਤਿੰਨ", "ਚਾਰ"],
    "ta-IN": ["பூஜ்யம்", "ஒன்று", "இரண்டு", "மூன்று", "நான்கு"],
    "te-IN": ["సున్నా", "ఒకటి", "రెండు", "మూడు", "నాలుగు"],
    "kn-IN": ["ಸೊನ್ನೆ", "ಒಂದು", "ಎರಡು", "ಮೂರು", "ನಾಲ್ಕು"],
    "ml-IN": ["പൂജ്യം", "ഒന്ന്", "രണ്ട്", "മൂന്ന്", "നാല്"],
}

ANNOUNCEMENT: dict[str, str] = {
    "en-IN": "Attention please. Fire detected in the {zone}. Leave calmly through exit number {exit}. "
             "Gather at the assembly point near the main gate. Do not use the lift.",
    "hi-IN": "कृपया ध्यान दें। {zone} में आग लगी है। शांति से एग्ज़िट नंबर {exit} से बाहर निकलें। "
             "मुख्य गेट के पास असेंबली पॉइंट पर इकट्ठा हों। लिफ्ट का इस्तेमाल न करें।",
    "mr-IN": "कृपया लक्ष द्या. {zone} मध्ये आग लागली आहे. शांतपणे एक्झिट नंबर {exit} मधून बाहेर पडा. "
             "मुख्य गेटजवळील असेंब्ली पॉइंटवर जमा व्हा. लिफ्टचा वापर करू नका.",
    "gu-IN": "કૃપા કરીને ધ્યાન આપો. {zone} વિસ્તારમાં આગ લાગી છે. શાંતિથી એક્ઝિટ નંબર {exit}થી બહાર નીકળો. "
             "મુખ્ય ગેટ પાસે એસેમ્બલી પોઈન્ટ પર ભેગા થાઓ. લિફ્ટનો ઉપયોગ ન કરો.",
    "bn-IN": "অনুগ্রহ করে মনোযোগ দিন। {zone} এলাকায় আগুন লেগেছে। শান্তভাবে এক্সিট নম্বর {exit} দিয়ে বেরিয়ে যান। "
             "মেইন গেটের কাছে অ্যাসেম্বলি পয়েন্টে জড়ো হন। লিফট ব্যবহার করবেন না।",
    "pa-IN": "ਕਿਰਪਾ ਕਰਕੇ ਧਿਆਨ ਦਿਓ। {zone} ਵਿੱਚ ਅੱਗ ਲੱਗ ਗਈ ਹੈ। ਸ਼ਾਂਤੀ ਨਾਲ ਐਗਜ਼ਿਟ ਨੰਬਰ {exit} ਰਾਹੀਂ ਬਾਹਰ ਨਿਕਲੋ। "
             "ਮੇਨ ਗੇਟ ਕੋਲ ਅਸੈਂਬਲੀ ਪੁਆਇੰਟ ਤੇ ਇਕੱਠੇ ਹੋਵੋ। ਲਿਫਟ ਦੀ ਵਰਤੋਂ ਨਾ ਕਰੋ।",
    "ta-IN": "கவனிக்கவும். {zone} பகுதியில் தீ விபத்து ஏற்பட்டுள்ளது. அமைதியாக எக்ஸிட் எண் {exit} வழியாக வெளியேறவும். "
             "மெயின் கேட் அருகே உள்ள அசெம்பிளி பாயிண்டில் கூடவும். லிஃப்டைப் பயன்படுத்த வேண்டாம்.",
    "te-IN": "దయచేసి గమనించండి. {zone} ప్రాంతంలో అగ్ని ప్రమాదం జరిగింది. ప్రశాంతంగా ఎగ్జిట్ నంబర్ {exit} ద్వారా బయటకు వెళ్ళండి. "
             "మెయిన్ గేట్ దగ్గర ఉన్న అసెంబ్లీ పాయింట్ వద్ద చేరండి. లిఫ్ట్ ఉపయోగించవద్దు.",
    "kn-IN": "ದಯವಿಟ್ಟು ಗಮನಿಸಿ. {zone} ಪ್ರದೇಶದಲ್ಲಿ ಬೆಂಕಿ ಕಾಣಿಸಿಕೊಂಡಿದೆ. ಶಾಂತವಾಗಿ ಎಕ್ಸಿಟ್ ಸಂಖ್ಯೆ {exit} ಮೂಲಕ ಹೊರಗೆ ಹೋಗಿ. "
             "ಮುಖ್ಯ ಗೇಟ್ ಬಳಿಯ ಅಸೆಂಬ್ಲಿ ಪಾಯಿಂಟ್‌ನಲ್ಲಿ ಸೇರಿ. ಲಿಫ್ಟ್ ಬಳಸಬೇಡಿ.",
    "ml-IN": "ദയവായി ശ്രദ്ധിക്കുക. {zone} ഭാഗത്ത് തീപിടിത്തം ഉണ്ടായിരിക്കുന്നു. ശാന്തമായി എക്സിറ്റ് നമ്പർ {exit} വഴി പുറത്തിറങ്ങുക. "
             "മെയിൻ ഗേറ്റിനടുത്തുള്ള അസംബ്ലി പോയിന്റിൽ ഒത്തുചേരുക. ലിഫ്റ്റ് ഉപയോഗിക്കരുത്.",
}


def announcement(lang: str, zone_id: str, exit_no: int) -> str:
    return ANNOUNCEMENT[lang].format(zone=ZONE_NAMES[zone_id][lang], exit=SMALL_NUMBERS[lang][exit_no])


# ------------------------------------------------------------ number words
_HI = ("शून्य एक दो तीन चार पाँच छह सात आठ नौ दस ग्यारह बारह तेरह चौदह पंद्रह सोलह सत्रह अठारह उन्नीस "
       "बीस इक्कीस बाईस तेईस चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस तीस इकतीस बत्तीस तैंतीस चौंतीस "
       "पैंतीस छत्तीस सैंतीस अड़तीस उनतालीस चालीस इकतालीस बयालीस तैंतालीस चवालीस पैंतालीस छियालीस "
       "सैंतालीस अड़तालीस उनचास पचास इक्यावन बावन तिरेपन चौवन पचपन छप्पन सत्तावन अट्ठावन उनसठ साठ "
       "इकसठ बासठ तिरसठ चौंसठ पैंसठ छियासठ सड़सठ अड़सठ उनहत्तर सत्तर इकहत्तर बहत्तर तिहत्तर चौहत्तर "
       "पचहत्तर छिहत्तर सतहत्तर अठहत्तर उन्यासी अस्सी इक्यासी बयासी तिरासी चौरासी पचासी छियासी सत्तासी "
       "अट्ठासी नवासी नब्बे इक्यानवे बानवे तिरानवे चौरानवे पचानवे छियानवे सत्तानवे अट्ठानवे निन्यानवे सौ").split()
_MR = ("शून्य एक दोन तीन चार पाच सहा सात आठ नऊ दहा अकरा बारा तेरा चौदा पंधरा सोळा सतरा अठरा एकोणीस "
       "वीस एकवीस बावीस तेवीस चोवीस पंचवीस सव्वीस सत्तावीस अठ्ठावीस एकोणतीस तीस एकतीस बत्तीस तेहतीस "
       "चौतीस पस्तीस छत्तीस सदतीस अडतीस एकोणचाळीस चाळीस एक्केचाळीस बेचाळीस त्रेचाळीस चव्वेचाळीस "
       "पंचेचाळीस सेहेचाळीस सत्तेचाळीस अठ्ठेचाळीस एकोणपन्नास पन्नास एक्कावन्न बावन्न त्रेपन्न चोपन्न "
       "पंचावन्न छप्पन्न सत्तावन्न अठ्ठावन्न एकोणसाठ साठ एकसष्ट बासष्ट त्रेसष्ट चौसष्ट पासष्ट सहासष्ट "
       "सदुसष्ट अडुसष्ट एकोणसत्तर सत्तर एकाहत्तर बाहत्तर त्र्याहत्तर चौऱ्याहत्तर पंचाहत्तर शहात्तर "
       "सत्याहत्तर अठ्ठ्याहत्तर एकोणऐंशी ऐंशी एक्याऐंशी ब्याऐंशी त्र्याऐंशी चौऱ्याऐंशी पंच्याऐंशी शहाऐंशी "
       "सत्त्याऐंशी अठ्ठ्याऐंशी एकोणनव्वद नव्वद एक्याण्णव ब्याण्णव त्र्याण्णव चौऱ्याण्णव पंच्याण्णव "
       "शहाण्णव सत्त्याण्णव अठ्ठ्याण्णव नव्याण्णव शंभर").split()
_EN_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
_EN_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
assert len(_HI) == 101 and len(_MR) == 101, (len(_HI), len(_MR))


def _int_words(n: int, lang: str) -> str:
    n = max(0, min(100, n))
    if lang == "hi-IN":
        return _HI[n]
    if lang == "mr-IN":
        return _MR[n]
    if n == 100:
        return "one hundred"
    if n < 20:
        return _EN_ONES[n]
    tens, ones = divmod(n, 10)
    return _EN_TENS[tens] + ("" if ones == 0 else " " + _EN_ONES[ones])


_POINT = {"en-IN": "point", "hi-IN": "पॉइंट", "mr-IN": "पॉइंट"}


@dataclass(frozen=True)
class Num:
    value: float
    decimals: int = 0

    def display(self) -> str:
        return f"{self.value:.{self.decimals}f}"

    def spoken(self, lang: str) -> str:
        if self.decimals == 0:
            return _int_words(round(self.value), lang)
        whole, frac = self.display().split(".")
        frac_words = " ".join(_int_words(int(d), lang) for d in frac)
        return f"{_int_words(int(whole), lang)} {_POINT[lang]} {frac_words}"


# ----------------------------------------------------------------- replies
REPLIES: dict[str, dict[str, str]] = {
    "temperature": {
        "en-IN": "The {zone} temperature is {value} degrees Celsius.",
        "hi-IN": "{zone} का तापमान {value} डिग्री सेल्सियस है।",
        "mr-IN": "{zone} मधील तापमान {value} डिग्री सेल्सिअस आहे.",
    },
    "smoke": {
        "en-IN": "Smoke level in the {zone} is {value} percent.",
        "hi-IN": "{zone} में धुएँ का स्तर {value} प्रतिशत है।",
        "mr-IN": "{zone} मध्ये धुराची पातळी {value} टक्के आहे.",
    },
    "zone_normal": {
        "en-IN": "The {zone} is normal. Temperature {temp} degrees, smoke {smoke} percent.",
        "hi-IN": "{zone} में सब सामान्य है। तापमान {temp} डिग्री, धुआँ {smoke} प्रतिशत।",
        "mr-IN": "{zone} मध्ये सर्व काही सामान्य आहे. तापमान {temp} डिग्री, धूर {smoke} टक्के.",
    },
    "zone_warning": {
        "en-IN": "Warning in the {zone}. Temperature is rising, now {temp} degrees, smoke {smoke} percent.",
        "hi-IN": "{zone} में चेतावनी है। तापमान बढ़ रहा है, अभी {temp} डिग्री, धुआँ {smoke} प्रतिशत।",
        "mr-IN": "{zone} मध्ये इशारा आहे. तापमान वाढत आहे, आता {temp} डिग्री, धूर {smoke} टक्के.",
    },
    "zone_fire": {
        "en-IN": "Fire alarm in the {zone}. Temperature {temp} degrees, smoke {smoke} percent. Evacuate through exit number {exit}.",
        "hi-IN": "{zone} में आग का अलार्म है। तापमान {temp} डिग्री, धुआँ {smoke} प्रतिशत। एग्ज़िट नंबर {exit} से बाहर निकलें।",
        "mr-IN": "{zone} मध्ये आगीचा अलार्म आहे. तापमान {temp} डिग्री, धूर {smoke} टक्के. एक्झिट नंबर {exit} मधून बाहेर पडा.",
    },
    "all_normal": {
        "en-IN": "All zones are normal. Header pressure is {pressure} bar and the water tank is {tank} percent full.",
        "hi-IN": "सभी ज़ोन सामान्य हैं। हेडर प्रेशर {pressure} बार है और पानी की टंकी {tank} प्रतिशत भरी है।",
        "mr-IN": "सर्व झोन सामान्य आहेत. हेडर प्रेशर {pressure} बार आहे आणि पाण्याची टाकी {tank} टक्के भरलेली आहे.",
    },
    "fire_active": {
        "en-IN": "Fire detected in the {zone}, reported by {source}. The main fire pump is {main}, header pressure {pressure} bar.",
        "hi-IN": "{zone} में आग का पता चला है, {source} ने रिपोर्ट किया। मुख्य फायर पंप {main} है, हेडर प्रेशर {pressure} बार।",
        "mr-IN": "{zone} मध्ये आग आढळली आहे, {source} ने कळवले. मुख्य फायर पंप {main} आहे, हेडर प्रेशर {pressure} बार.",
    },
    "no_fire": {
        "en-IN": "No fire detected. All zones are normal.",
        "hi-IN": "कहीं आग नहीं है। सभी ज़ोन सामान्य हैं।",
        "mr-IN": "कुठेही आग नाही. सर्व झोन सामान्य आहेत.",
    },
    "pump": {
        "en-IN": "The main fire pump is {main}. The jockey pump is {jockey}. Header pressure is {pressure} bar.",
        "hi-IN": "मुख्य फायर पंप {main} है। जॉकी पंप {jockey} है। हेडर प्रेशर {pressure} बार है।",
        "mr-IN": "मुख्य फायर पंप {main} आहे. जॉकी पंप {jockey} आहे. हेडर प्रेशर {pressure} बार आहे.",
    },
    "pressure": {
        "en-IN": "Fire line header pressure is {pressure} bar.",
        "hi-IN": "फायर लाइन का हेडर प्रेशर {pressure} बार है।",
        "mr-IN": "फायर लाइनचा हेडर प्रेशर {pressure} बार आहे.",
    },
    "tank": {
        "en-IN": "The fire water tank is {tank} percent full.",
        "hi-IN": "फायर वॉटर टंकी {tank} प्रतिशत भरी है।",
        "mr-IN": "फायर वॉटर टाकी {tank} टक्के भरलेली आहे.",
    },
    "evacuate": {
        "en-IN": "From the {zone}, leave through exit number {exit} and go to the assembly point near the main gate.",
        "hi-IN": "{zone} से एग्ज़िट नंबर {exit} से निकलें और मुख्य गेट के पास असेंबली पॉइंट पर जाएँ।",
        "mr-IN": "{zone} मधून एक्झिट नंबर {exit} ने बाहेर पडा आणि मुख्य गेटजवळील असेंब्ली पॉइंटवर जा.",
    },
    "evacuate_which": {
        "en-IN": "Which zone are you in? Say production floor, warehouse, server room or canteen.",
        "hi-IN": "आप किस ज़ोन में हैं? प्रोडक्शन फ्लोर, गोदाम, सर्वर रूम या कैंटीन बताइए।",
        "mr-IN": "तुम्ही कोणत्या झोनमध्ये आहात? प्रोडक्शन फ्लोअर, गोदाम, सर्व्हर रूम किंवा कॅन्टीन सांगा.",
    },
    "silenced": {
        "en-IN": "Alarm silenced. The zone stays in alarm until the system is reset.",
        "hi-IN": "अलार्म बंद कर दिया गया है। सिस्टम रीसेट होने तक ज़ोन अलार्म में रहेगा।",
        "mr-IN": "अलार्म बंद केला आहे. सिस्टम रीसेट होईपर्यंत झोन अलार्ममध्ये राहील.",
    },
    "nothing_to_silence": {
        "en-IN": "There is no active alarm to silence.",
        "hi-IN": "अभी कोई अलार्म चालू नहीं है।",
        "mr-IN": "आत्ता कोणताही अलार्म चालू नाही.",
    },
    "reset": {
        "en-IN": "System reset. All zones are back to normal.",
        "hi-IN": "सिस्टम रीसेट हो गया है। सभी ज़ोन सामान्य हैं।",
        "mr-IN": "सिस्टम रीसेट झाली आहे. सर्व झोन सामान्य आहेत.",
    },
    "help": {
        "en-IN": "I didn't catch that. Ask about temperature, smoke, the fire pump, or the way out of a zone.",
        "hi-IN": "समझ नहीं आया। तापमान, धुआँ, फायर पंप या किसी ज़ोन से बाहर निकलने का रास्ता पूछिए।",
        "mr-IN": "समजलं नाही. तापमान, धूर, फायर पंप किंवा एखाद्या झोनमधून बाहेर पडण्याचा मार्ग विचारा.",
    },
}

PUMP_STATE = {
    True: {"en-IN": "running", "hi-IN": "चालू", "mr-IN": "चालू"},
    False: {"en-IN": "off", "hi-IN": "बंद", "mr-IN": "बंद"},
}
MAIN_PUMP_STATE = {
    True: PUMP_STATE[True],
    False: {"en-IN": "on standby", "hi-IN": "स्टैंडबाय पर", "mr-IN": "स्टँडबाय वर"},
}

SOURCES = {
    "sensor": {"en-IN": "the heat and smoke sensors", "hi-IN": "हीट और स्मोक सेंसर", "mr-IN": "हीट आणि स्मोक सेन्सर"},
    "camera": {"en-IN": "the flame detection camera", "hi-IN": "फ्लेम डिटेक्शन कैमरा", "mr-IN": "फ्लेम डिटेक्शन कॅमेरा"},
    "manual": {"en-IN": "a manual call point", "hi-IN": "मैनुअल कॉल पॉइंट", "mr-IN": "मॅन्युअल कॉल पॉइंट"},
}


def render(key: str, lang: str, **values) -> tuple[str, str]:
    """Return (display_text, spoken_text) for a reply template."""
    template = REPLIES[key][lang]
    disp, spoken = {}, {}
    for k, v in values.items():
        if isinstance(v, Num):
            disp[k], spoken[k] = v.display(), v.spoken(lang)
        else:
            disp[k] = spoken[k] = v
    return template.format(**disp), template.format(**spoken)
