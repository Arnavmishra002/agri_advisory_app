"""
KrishiMitra Language Service
Supports all 22 scheduled Indian languages + English.

Backend responsibility:
  - Normalise incoming language codes to BCP-47 tags
  - Provide translated UI strings for API responses
  - Pass the correct language tag to Gemini so it replies in the right script
  - Translate key agricultural terms used in API response fields

Frontend responsibility (see app.js i18n block):
  - Render all static UI text from the translations dict
  - Send `language` param on every API call
"""

from __future__ import annotations
from typing import Dict, Optional

# ── Supported languages ────────────────────────────────────────────────────
# Maps the code we receive from the frontend / API to a BCP-47 tag
SUPPORTED_LANGUAGES: Dict[str, Dict[str, str]] = {
    # code: { bcp47, name_english, name_native, script, gemini_lang_hint }
    "hi":  {"bcp47": "hi-IN", "name_english": "Hindi",      "name_native": "हिन्दी",      "script": "Devanagari",   "gemini": "Hindi"},
    "en":  {"bcp47": "en-IN", "name_english": "English",    "name_native": "English",     "script": "Latin",        "gemini": "English"},
    "bn":  {"bcp47": "bn-IN", "name_english": "Bengali",    "name_native": "বাংলা",       "script": "Bengali",      "gemini": "Bengali"},
    "te":  {"bcp47": "te-IN", "name_english": "Telugu",     "name_native": "తెలుగు",      "script": "Telugu",       "gemini": "Telugu"},
    "mr":  {"bcp47": "mr-IN", "name_english": "Marathi",    "name_native": "मराठी",       "script": "Devanagari",   "gemini": "Marathi"},
    "ta":  {"bcp47": "ta-IN", "name_english": "Tamil",      "name_native": "தமிழ்",       "script": "Tamil",        "gemini": "Tamil"},
    "gu":  {"bcp47": "gu-IN", "name_english": "Gujarati",   "name_native": "ગુજરાતી",    "script": "Gujarati",     "gemini": "Gujarati"},
    "kn":  {"bcp47": "kn-IN", "name_english": "Kannada",    "name_native": "ಕನ್ನಡ",       "script": "Kannada",      "gemini": "Kannada"},
    "ml":  {"bcp47": "ml-IN", "name_english": "Malayalam",  "name_native": "മലയാളം",      "script": "Malayalam",    "gemini": "Malayalam"},
    "pa":  {"bcp47": "pa-IN", "name_english": "Punjabi",    "name_native": "ਪੰਜਾਬੀ",     "script": "Gurmukhi",     "gemini": "Punjabi"},
    "or":  {"bcp47": "or-IN", "name_english": "Odia",       "name_native": "ଓଡ଼ିଆ",       "script": "Odia",         "gemini": "Odia"},
    "as":  {"bcp47": "as-IN", "name_english": "Assamese",   "name_native": "অসমীয়া",     "script": "Bengali",      "gemini": "Assamese"},
    "ur":  {"bcp47": "ur-IN", "name_english": "Urdu",       "name_native": "اردو",        "script": "Nastaliq",     "gemini": "Urdu"},
    "mai": {"bcp47": "mai",   "name_english": "Maithili",   "name_native": "मैथिली",      "script": "Devanagari",   "gemini": "Maithili"},
    "sa":  {"bcp47": "sa",    "name_english": "Sanskrit",   "name_native": "संस्कृतम्",   "script": "Devanagari",   "gemini": "Sanskrit"},
    "ne":  {"bcp47": "ne-IN", "name_english": "Nepali",     "name_native": "नेपाली",      "script": "Devanagari",   "gemini": "Nepali"},
    "kok": {"bcp47": "kok",   "name_english": "Konkani",    "name_native": "कोंकणी",      "script": "Devanagari",   "gemini": "Konkani"},
    "mni": {"bcp47": "mni",   "name_english": "Manipuri",   "name_native": "মৈতৈলোন্",   "script": "Bengali",      "gemini": "Manipuri"},
    "sd":  {"bcp47": "sd",    "name_english": "Sindhi",     "name_native": "سنڌي",        "script": "Arabic",       "gemini": "Sindhi"},
    "ks":  {"bcp47": "ks",    "name_english": "Kashmiri",   "name_native": "کشمیری",      "script": "Arabic",       "gemini": "Kashmiri"},
    "bo":  {"bcp47": "bo",    "name_english": "Bodo",       "name_native": "बड़ो",         "script": "Devanagari",   "gemini": "Bodo"},
    "doi": {"bcp47": "doi",   "name_english": "Dogri",      "name_native": "डोगरी",       "script": "Devanagari",   "gemini": "Dogri"},
    "sat": {"bcp47": "sat",   "name_english": "Santali",    "name_native": "ᱥᱟᱱᱛᱟᱲᱤ",   "script": "Ol Chiki",     "gemini": "Santali"},
    # Aliases / shortcuts
    "hinglish": {"bcp47": "hi-IN-x-hinglish", "name_english": "Hinglish", "name_native": "Hinglish", "script": "Latin+Devanagari", "gemini": "Hinglish (Hindi-English mix)"},
    "auto":     {"bcp47": "und",               "name_english": "Auto",     "name_native": "Auto",     "script": "auto",             "gemini": "the same language as the user's question"},
}

# State → default language mapping (used when no explicit language given)
STATE_DEFAULT_LANGUAGE: Dict[str, str] = {
    "Delhi": "hi", "Uttar Pradesh": "hi", "Bihar": "hi", "Jharkhand": "hi",
    "Madhya Pradesh": "hi", "Rajasthan": "hi", "Chhattisgarh": "hi",
    "Uttarakhand": "hi", "Himachal Pradesh": "hi", "Haryana": "hi",
    "Jammu and Kashmir": "hi",
    "Maharashtra": "mr", "Goa": "mr",
    "West Bengal": "bn", "Tripura": "bn",
    "Andhra Pradesh": "te", "Telangana": "te",
    "Tamil Nadu": "ta",
    "Gujarat": "gu",
    "Karnataka": "kn",
    "Kerala": "ml",
    "Punjab": "pa",
    "Odisha": "or",
    "Assam": "as",
}

# ── UI string translations ─────────────────────────────────────────────────
# Only a curated key set — Gemini handles the rest via the language prompt.
UI_STRINGS: Dict[str, Dict[str, str]] = {
    # Weather
    "clear_sky":        {"hi": "साफ आसमान",    "en": "Clear Sky",       "bn": "পরিষ্কার আকাশ", "te": "స్వచ్ఛమైన ఆకాశం",  "mr": "स्वच्छ आकाश",   "ta": "தெளிவான வானம்",  "gu": "સ્વચ્છ આકાશ",    "kn": "ಸ್ವಚ್ಛ ಆಕಾಶ",     "ml": "തെളിഞ്ഞ ആകാശം",  "pa": "ਸਾਫ਼ ਅਸਮਾਨ",    "or": "ସ୍ୱଚ୍ଛ ଆକାଶ",    "as": "পৰিষ্কাৰ আকাশ"},
    "partly_cloudy":    {"hi": "आंशिक बादल",   "en": "Partly Cloudy",   "bn": "আংশিক মেঘলা",   "te": "పాక్షిక మేఘావృతం", "mr": "अंशतः ढगाळ",    "ta": "பகுதியளவு மேகமூட்டம்", "gu": "આંશિક વાદળ",  "kn": "ಭಾಗಶಃ ಮೋಡ",     "ml": "ഭാഗികമായി മേഘം","pa": "ਕੁਝ ਬੱਦਲ",       "or": "ଆଂଶିକ ମେଘ",     "as": "আংশিক মেঘীয়া"},
    "rain":             {"hi": "बारिश",         "en": "Rain",            "bn": "বৃষ্টি",        "te": "వర్షం",             "mr": "पाऊस",           "ta": "மழை",             "gu": "વરસાદ",          "kn": "ಮಳೆ",             "ml": "മഴ",              "pa": "ਮੀਂਹ",           "or": "ବର୍ଷା",          "as": "বৰষুণ"},
    "fog":              {"hi": "कोहरा",         "en": "Fog",             "bn": "কুয়াশা",        "te": "పొగమంచు",          "mr": "धुके",           "ta": "மூடுபனி",         "gu": "ધુમ્મસ",         "kn": "ಮಂಜು",            "ml": "മൂടൽ",           "pa": "ਧੁੰਦ",           "or": "କୁହୁଡ଼ି",        "as": "কুঁৱলী"},
    "thunderstorm":     {"hi": "आंधी-तूफान",   "en": "Thunderstorm",    "bn": "বজ্রঝড়",        "te": "ఉరుము తుఫాను",     "mr": "वादळ",           "ta": "இடியுடன் கூடிய மழை", "gu": "વાવાઝોડું",   "kn": "ಗುಡುಗು ಮಳೆ",    "ml": "ഇടിമിന്നൽ",      "pa": "ਗਰਜ਼ਵਾਲਾ ਤੂਫ਼ਾਨ", "or": "ଗର୍ଜ୍ଜନ ଝଡ଼",    "as": "বজ্ৰ-ঝড়"},
    # Agriculture
    "irrigation_needed":  {"hi": "सिंचाई आवश्यक है", "en": "Irrigation needed", "bn": "সেচ প্রয়োজন", "te": "నీటిపారుదల అవసరం", "mr": "सिंचन आवश्यक", "ta": "நீர்ப்பாசனம் தேவை", "gu": "સિંચાઈ જરૂરી", "kn": "ನೀರಾವರಿ ಅಗತ್ಯ", "ml": "ജലസേചനം ആവശ്യം", "pa": "ਸਿੰਚਾਈ ਜ਼ਰੂਰੀ ਹੈ", "or": "ଜଳସେଚନ ଆବଶ୍ୟକ", "as": "জলসিঞ্চন আৱশ্যক"},
    "fungal_risk":        {"hi": "फंगल रोगों से सावधान", "en": "Fungal disease risk", "bn": "ছত্রাক রোগের ঝুঁকি", "te": "శిలీంధ్ర వ్యాధి ప్రమాదం", "mr": "बुरशी रोगाचा धोका", "ta": "பூஞ்சை நோய் அபாயம்", "gu": "ફૂગ રોગ જોખમ", "kn": "ಶಿಲೀಂಧ್ರ ರೋಗ ಅಪಾಯ", "ml": "ഫംഗൽ രോഗ അപകടം", "pa": "ਫੰਗਲ ਰੋਗ ਦਾ ਖਤਰਾ", "or": "ଫଙ୍ଗଲ ରୋଗ ଆଶଙ୍କା", "as": "ফাংগেল ৰোগৰ বিপদ"},
    "good_conditions":    {"hi": "सामान्य कृषि गतिविधियां जारी रखें", "en": "Good conditions — continue normal farm activities", "bn": "স্বাভাবিক কৃষি কার্যক্রম চালিয়ে যান", "te": "సాధారణ వ్యవసాయ కార్యకలాపాలు కొనసాగించండి", "mr": "सामान्य शेती कामे सुरू ठेवा", "ta": "சாதாரண வேளாண் பணிகளை தொடரலாம்", "gu": "સામાન્ય ખેતી પ્રવૃત્તિઓ ચાલુ રાખો", "kn": "ಸಾಮಾನ್ಯ ಕೃಷಿ ಚಟುವಟಿಕೆಗಳನ್ನು ಮುಂದುವರಿಸಿ", "ml": "സാധാരണ കൃഷി പ്രവർത്തനങ്ങൾ തുടരുക", "pa": "ਸਧਾਰਨ ਖੇਤੀ ਕੰਮ ਜਾਰੀ ਰੱਖੋ", "or": "ସାଧାରଣ ଚାଷ କାର୍ଯ୍ୟ ଜାରି ରଖନ୍ତୁ", "as": "সাধাৰণ কৃষি কার্য্য চলাই যাওক"},
    # Market
    "live_data":    {"hi": "लाइव मंडी डेटा", "en": "Live Mandi Data", "bn": "লাইভ মান্ডি ডেটা", "te": "లైవ్ మండి డేటా", "mr": "लाइव्ह मंडी डेटा", "ta": "நேரடி மந்தி தரவு", "gu": "લાઇવ મંડી ડેટા", "kn": "ನೇರ ಮಂಡಿ ಡೇಟಾ", "ml": "ലൈവ് മണ്ടി ഡേറ്റ", "pa": "ਲਾਈਵ ਮੰਡੀ ਡੇਟਾ", "or": "ଲାଇଭ ମଣ୍ଡି ଡାଟା", "as": "লাইভ মণ্ডি তথ্য"},
    "msp_estimate": {"hi": "MSP आधारित अनुमान (असली मंडी भाव नहीं)", "en": "MSP-based estimate (not live mandi trade)", "bn": "MSP ভিত্তিক অনুমান (সরাসরি মান্ডি মূল্য নয়)", "te": "MSP ఆధారిత అంచనా (నేరుగా మండి ధర కాదు)", "mr": "MSP आधारित अंदाज (थेट मंडी भाव नाही)", "ta": "MSP அடிப்படையிலான மதிப்பீடு (நேரடி சந்தை விலை இல்லை)", "gu": "MSP આધારિત અંદાજ (સીધો મંડી ભાવ નહીં)", "kn": "MSP ಆಧಾರಿತ ಅಂದಾಜು (ನೇರ ಮಂಡಿ ಬೆಲೆ ಅಲ್ಲ)", "ml": "MSP അടിസ്ഥാനമാക്കിയ കണക്ക് (നേരിട്ടുള്ള മണ്ടി വില അല്ല)", "pa": "MSP ਅਧਾਰਿਤ ਅਨੁਮਾਨ (ਸਿੱਧਾ ਮੰਡੀ ਭਾਅ ਨਹੀਂ)", "or": "MSP ଆଧାରିତ ଅନୁମାନ (ସିଧା ମଣ୍ଡି ଭାଁ ନୁହେଁ)", "as": "MSP ভিত্তিক অনুমান (প্ৰত্যক্ষ মণ্ডি মূল্য নহয়)"},
    # Schemes
    "scheme_apply": {"hi": "अभी आवेदन करें", "en": "Apply Now", "bn": "এখনই আবেদন করুন", "te": "ఇప్పుడే దరఖాస్తు చేయండి", "mr": "आता अर्ज करा", "ta": "இப்போது விண்ணப்பிக்கவும்", "gu": "હવે અરજી કરો", "kn": "ಈಗ ಅರ್ಜಿ ಹಾಕಿ", "ml": "ഇപ്പോൾ അപേക്ഷിക്കുക", "pa": "ਹੁਣੇ ਅਰਜ਼ੀ ਕਰੋ", "or": "ଏବେ ଆବେଦନ କରନ୍ତୁ", "as": "এতিয়াই আবেদন কৰক"},
    # Loading / errors
    "loading":      {"hi": "लोड हो रहा है...", "en": "Loading...", "bn": "লোড হচ্ছে...", "te": "లోడ్ అవుతోంది...", "mr": "लोड होत आहे...", "ta": "ஏற்றுகிறது...", "gu": "લોડ થઈ રહ્યું છે...", "kn": "ಲೋಡ್ ಆಗುತ್ತಿದೆ...", "ml": "ലോഡ് ആകുന്നു...", "pa": "ਲੋਡ ਹੋ ਰਿਹਾ ਹੈ...", "or": "ଲୋଡ ହେଉଛି...", "as": "লোড হৈছে...", "ur": "لوڈ ہو رہا ہے..."},
    "error":        {"hi": "त्रुटि", "en": "Error", "bn": "ত্রুটি", "te": "లోపం", "mr": "त्रुटी", "ta": "பிழை", "gu": "ભૂલ", "kn": "ದೋಷ", "ml": "പിശക്", "pa": "ਗਲਤੀ", "or": "ତ୍ରୁଟି", "as": "ভুল"},
    # Crop recommendation reasons
    "seasonal_fit":   {"hi": "मौसम के लिए उपयुक्त", "en": "Suitable for season", "bn": "মৌসুমের জন্য উপযুক্ত", "te": "సీజన్‌కు అనుకూలం", "mr": "हंगामासाठी योग्य", "ta": "பருவத்திற்கு ஏற்றது", "gu": "સિઝન માટે યોગ્ય", "kn": "ಋತುವಿಗೆ ಸೂಕ್ತ", "ml": "സീസണിൽ അനുയോജ്യം", "pa": "ਮੌਸਮ ਲਈ ਢੁਕਵਾਂ", "or": "ଋତୁ ପାଇଁ ଉପଯୁକ୍ତ", "as": "ঋতুৰ বাবে উপযুক্ত"},
    "high_profit":    {"hi": "उच्च लाभ", "en": "High profit potential", "bn": "উচ্চ মুনাফা সম্ভাবনা", "te": "అధిక లాభం", "mr": "उच्च नफा", "ta": "அதிக லாபம்", "gu": "ઊંચો નફો", "kn": "ಹೆಚ್ಚಿನ ಲಾಭ", "ml": "ഉയർന്ന ലാഭം", "pa": "ਉੱਚ ਮੁਨਾਫ਼ਾ", "or": "ଉଚ୍ଚ ଲାଭ", "as": "উচ্চ লাভ"},
    "drought_resist": {"hi": "सूखा प्रतिरोधी", "en": "Drought resistant", "bn": "খরা সহনশীল", "te": "కరువు నిరోధక", "mr": "दुष्काळ सहन", "ta": "வறட்சி எதிர்ப்பு", "gu": "દુષ્કાળ પ્રતિરોધક", "kn": "ಬರ ನಿರೋಧಕ", "ml": "വരൾച്ചാ പ്രതിരോധകം", "pa": "ਸੋਕਾ ਰੋਧਕ", "or": "ଖରା ପ୍ରତିରୋଧୀ", "as": "খৰাং প্ৰতিৰোধী"},
}

# Crop name translations — key is English lowercase
CROP_NAMES: Dict[str, Dict[str, str]] = {
    "wheat":      {"hi": "गेहूँ",   "bn": "গম",      "te": "గోధుమ",    "mr": "गहू",     "ta": "கோதுமை",  "gu": "ઘઉં",     "kn": "ಗೋಧಿ",    "ml": "ഗോതമ്പ്", "pa": "ਕਣਕ",    "or": "ଗହମ",     "as": "ঘেঁহু",  "ur": "گندم"},
    "rice":       {"hi": "धान",     "bn": "ধান",     "te": "వరి",      "mr": "भात",     "ta": "நெல்",    "gu": "ડાંગર",   "kn": "ಭತ್ತ",    "ml": "നെല്ല്", "pa": "ਝੋਨਾ",  "or": "ଧାନ",     "as": "ধান",    "ur": "چاول"},
    "maize":      {"hi": "मक्का",   "bn": "ভুট্টা",  "te": "మొక్కజొన్న", "mr": "मका",  "ta": "சோளம்",  "gu": "મકાઈ",    "kn": "ಜೋಳ",      "ml": "ചോളം",   "pa": "ਮੱਕੀ",  "or": "ମକା",     "as": "ভুট্টা", "ur": "مکئی"},
    "mustard":    {"hi": "सरसों",   "bn": "সরিষা",   "te": "ఆవాలు",    "mr": "मोहरी",   "ta": "கடுகு",   "gu": "સરસવ",    "kn": "ಸಾಸಿವೆ",  "ml": "കടുക്",  "pa": "ਸਰ੍ਹੋਂ", "or": "ସୋରିଷ",   "as": "সৰিয়হ","ur": "سرسوں"},
    "cotton":     {"hi": "कपास",    "bn": "তুলা",    "te": "పత్తి",     "mr": "कापूस",   "ta": "பருத்தி", "gu": "કપાસ",    "kn": "ಹತ್ತಿ",   "ml": "പരുത്തി","pa": "ਕਪਾਹ",  "or": "କପା",     "as": "কপাহ",   "ur": "کپاس"},
    "sugarcane":  {"hi": "गन्ना",   "bn": "আখ",      "te": "చెరకు",     "mr": "ऊस",      "ta": "கரும்பு", "gu": "શેરડી",   "kn": "ಕಬ್ಬು",   "ml": "കരിമ്പ്","pa": "ਗੰਨਾ",  "or": "ଆଖୁ",     "as": "কুঁহিয়াৰ","ur": "گنا"},
    "soybean":    {"hi": "सोयाबीन", "bn": "সয়াবিন", "te": "సోయాబీన్", "mr": "सोयाबीन", "ta": "சோயாபீன்","gu": "સોયાબીન", "kn": "ಸೋಯಾಬೀನ್","ml": "സോയ",    "pa": "ਸੋਇਆਬੀਨ","or": "ସୋୟାବିନ", "as": "চয়াবিন","ur": "سویابین"},
    "tomato":     {"hi": "टमाटर",   "bn": "টমেটো",   "te": "టమాటా",    "mr": "टोमॅटो",  "ta": "தக்காளி", "gu": "ટામેટા",  "kn": "ಟೊಮೆಟೊ",  "ml": "തക്കാളി","pa": "ਟਮਾਟਰ", "or": "ଟମାଟୋ",   "as": "টমেটো",  "ur": "ٹماٹر"},
    "onion":      {"hi": "प्याज",   "bn": "পেঁয়াজ", "te": "ఉల్లి",    "mr": "कांदा",   "ta": "வெங்காயம்","gu": "ડુંગળી", "kn": "ಈರುಳ್ಳಿ", "ml": "സവോള",  "pa": "ਪਿਆਜ਼", "or": "ପିଆଜ",    "as": "পিঁয়াজ","ur": "پیاز"},
    "potato":     {"hi": "आलू",     "bn": "আলু",     "te": "బంగాళాదుంప","mr": "बटाटा",   "ta": "உருளைக்கிழங்கு","gu": "બટાટા","kn": "ಆಲೂಗಡ್ಡೆ","ml": "ഉരുളക്കിഴങ്ങ്","pa": "ਆਲੂ","or": "ଆଳୁ",    "as": "আলু",    "ur": "آلو"},
    "gram":       {"hi": "चना",     "bn": "ছোলা",    "te": "శనగ",      "mr": "हरभरा",   "ta": "கடலை",    "gu": "ચણા",     "kn": "ಕಡಲೆ",    "ml": "കടല",    "pa": "ਛੋਲੇ",  "or": "ଚଣା",     "as": "মাহ",    "ur": "چنا"},
    "groundnut":  {"hi": "मूंगफली", "bn": "চিনাবাদাম","te": "వేరుశనగ",  "mr": "भुईमूग",  "ta": "வேர்க்கடலை","gu": "મગફળી", "kn": "ಕಡಲೆ",    "ml": "കപ്പലണ്ടി","pa": "ਮੂੰਗਫਲੀ","or": "ଚିନାବାଦାମ","as": "বাদাম","ur": "مونگ پھلی"},
    "rice paddy": {"hi": "धान",     "bn": "ধান",     "te": "వరి",      "mr": "भात",     "ta": "நெல்",    "gu": "ડાંગર",   "kn": "ಭತ್ತ",    "ml": "നെല്ല്", "pa": "ਝੋਨਾ",  "or": "ଧାନ",     "as": "ধান",    "ur": "چاول"},
}


def get_language_info(code: str) -> Dict[str, str]:
    """Return language metadata dict for a code; falls back to Hindi."""
    code = (code or "hi").strip().lower()
    return SUPPORTED_LANGUAGES.get(code, SUPPORTED_LANGUAGES["hi"])


def normalise_language_code(code: Optional[str]) -> str:
    """Accept any variant the frontend might send and normalise to our internal code."""
    if not code:
        return "hi"
    code = code.strip().lower()
    # Normalise aliases
    aliases = {
        "hindi": "hi", "english": "en", "bengali": "bn", "bangla": "bn",
        "telugu": "te", "marathi": "mr", "tamil": "ta", "gujarati": "gu",
        "kannada": "kn", "malayalam": "ml", "punjabi": "pa", "odia": "or",
        "odiya": "or", "assamese": "as", "urdu": "ur", "maithili": "mai",
        "nepali": "ne", "konkani": "kok", "manipuri": "mni", "sindhi": "sd",
        "kashmiri": "ks", "bodo": "bo", "dogri": "doi", "santali": "sat",
    }
    code = aliases.get(code, code)
    if code in SUPPORTED_LANGUAGES:
        return code
    # Try first 2 chars
    short = code[:2]
    if short in SUPPORTED_LANGUAGES:
        return short
    return "hi"


def get_ui_string(key: str, lang: str) -> str:
    """Get a translated UI string; falls back to English, then key."""
    lang = normalise_language_code(lang)
    translations = UI_STRINGS.get(key, {})
    return translations.get(lang) or translations.get("en") or key


def get_crop_name(crop_key: str, lang: str) -> str:
    """Return the crop name in the requested language; falls back to Hindi then English title-case."""
    lang = normalise_language_code(lang)
    crop_key_lower = crop_key.lower().strip()
    names = CROP_NAMES.get(crop_key_lower, {})
    # For English, always return the English name
    if lang == "en":
        return crop_key_lower.replace("_", " ").title()
    return names.get(lang) or names.get("hi") or crop_key_lower.replace("_", " ").title()


def get_gemini_language_instruction(lang: str) -> str:
    """Return the language instruction string to embed in Gemini system/user prompt."""
    info = get_language_info(normalise_language_code(lang))
    gemini_lang = info.get("gemini", "Hindi")
    if gemini_lang == "the same language as the user's question":
        return "Detect the language from the question and reply in the same language and script."
    return (
        f"IMPORTANT: You MUST respond entirely in {gemini_lang} "
        f"(script: {info.get('script', 'native')}). "
        f"Do not mix languages unless the user themselves writes in mixed code."
    )


def get_language_for_state(state: str) -> str:
    """Return the most appropriate default language code for an Indian state."""
    return STATE_DEFAULT_LANGUAGE.get(state, "hi")


def translate_farming_advice(temp: Optional[float], humidity: Optional[float],
                              rain_mm: Optional[float], weather_code: int,
                              lang: str) -> str:
    """Return a localised farming advisory string based on weather params."""
    lang = normalise_language_code(lang)
    advisories = []

    if temp is not None:
        if temp > 40:
            advisories.append(get_ui_string("irrigation_needed", lang))
        elif temp < 5:
            advisories.append({
                "hi": "पाला पड़ने की संभावना — फसल को ढकें",
                "en": "Frost risk — cover crops",
                "bn": "তুষারপাতের আশঙ্কা — ফসল ঢাকুন",
                "te": "మంచు ముప్పు — పంటలు కప్పండి",
                "mr": "दव पडण्याची शक्यता — पिकांना झाका",
                "ta": "பனி ஆபத்து — பயிர்களை மூடுங்கள்",
                "gu": "ઠંડી-પ્રહારથી ખતરો — ફસલ ઢાંકો",
                "kn": "ಮಂಜು ಅಪಾಯ — ಬೆಳೆ ಮುಚ್ಚಿ",
                "ml": "ഹിമ അപകടം — വിള മൂടുക",
                "pa": "ਕੋਰੇ ਦਾ ਖਤਰਾ — ਫ਼ਸਲ ਢੱਕੋ",
                "or": "ଶୀତ ବିପଦ — ଫସଲ ଢ଼ାଙ୍କନ୍ତୁ",
                "as": "তুষাৰপাতৰ বিপদ — শস্য ঢাকক",
            }.get(lang, "Frost risk — cover crops"))

    if humidity is not None and humidity > 80:
        advisories.append(get_ui_string("fungal_risk", lang))

    if rain_mm is not None:
        if rain_mm > 50:
            advisories.append({
                "hi": "भारी बारिश — जल निकासी सुनिश्चित करें",
                "en": "Heavy rain — ensure drainage",
                "bn": "ভারী বৃষ্টি — নিষ্কাশন নিশ্চিত করুন",
                "te": "భారీ వర్షం — నీటి నిరిష్కరణ నిర్ధారించండి",
                "mr": "जड पाऊस — निचरा सुनिश्चित करा",
                "ta": "கனமழை — வடிகால் உறுதிப்படுத்துங்கள்",
                "gu": "ભારે વરસાદ — ગટર સુનિશ્ચિત કરો",
                "kn": "ಭಾರೀ ಮಳೆ — ನಿಕಾಸಿ ಖಾತ್ರಿ ಮಾಡಿ",
                "ml": "കനത്ത മഴ — ഡ്രൈനേജ് ഉറപ്പ് വരുത്തുക",
                "pa": "ਭਾਰੀ ਮੀਂਹ — ਨਿਕਾਸੀ ਯਕੀਨੀ ਕਰੋ",
                "or": "ଭାରୀ ବର୍ଷା — ଜଳ ନିଷ୍କାସନ ନିଶ୍ଚିତ କରନ୍ତୁ",
                "as": "গধুৰ বৰষুণ — নিষ্কাশন নিশ্চিত কৰক",
            }.get(lang, "Heavy rain — ensure drainage"))
        elif 5 < rain_mm <= 50:
            advisories.append({
                "hi": "बारिश हो रही है — सिंचाई की जरूरत नहीं",
                "en": "Raining — no irrigation needed",
                "bn": "বৃষ্টি হচ্ছে — সেচের প্রয়োজন নেই",
                "te": "వర్షం పడుతోంది — సేద్యం అవసరం లేదు",
                "mr": "पाऊस पडतोय — सिंचनाची गरज नाही",
                "ta": "மழை பெய்கிறது — நீர்ப்பாசனம் தேவையில்லை",
                "gu": "વરસાદ — સિંચાઈ જરૂરી નથી",
                "kn": "ಮಳೆ ಬರುತ್ತಿದೆ — ನೀರಾವರಿ ಬೇಡ",
                "ml": "മഴ പെയ്യുന്നു — ജലസേചനം ആവശ്യമില്ല",
                "pa": "ਮੀਂਹ ਪੈ ਰਿਹਾ ਹੈ — ਸਿੰਚਾਈ ਜ਼ਰੂਰੀ ਨਹੀਂ",
                "or": "ବର୍ଷା ହେଉଛି — ଜଳ ଦେବାର ଆବଶ୍ୟକ ନାହିଁ",
                "as": "বৰষুণ হৈছে — জলসিঞ্চন লাগিব নহয়",
            }.get(lang, "Raining — no irrigation needed"))

    if weather_code in (95, 96, 99):
        advisories.append({
            "hi": "⚠️ तूफान की चेतावनी — खेत में न जाएं",
            "en": "⚠️ Storm warning — stay off field",
            "bn": "⚠️ ঝড়ের সতর্কতা — মাঠে যাবেন না",
            "te": "⚠️ తుఫాను హెచ్చరిక — పొలానికి వెళ్ళకండి",
            "mr": "⚠️ वादळाचा इशारा — शेतात जाऊ नका",
            "ta": "⚠️ புயல் எச்சரிக்கை — வயலுக்கு செல்லாதீர்கள்",
            "gu": "⚠️ તોફાન ચેતવણી — ખેતરમાં ન જાઓ",
            "kn": "⚠️ ಬಿರುಗಾಳಿ ಎಚ್ಚರಿಕೆ — ಹೊಲಕ್ಕೆ ಹೋಗಬೇಡಿ",
            "ml": "⚠️ കൊടുങ്കാറ്റ് മുന്നറിയിപ്പ് — വയലിൽ പോകരുത്",
            "pa": "⚠️ ਤੂਫ਼ਾਨ ਚੇਤਾਵਨੀ — ਖੇਤ ਵਿੱਚ ਨਾ ਜਾਓ",
            "or": "⚠️ ଝଡ ସାବଧାନ — ବଡ ଜଗଟ ଯିବ ନାହିଁ",
            "as": "⚠️ ধুমুহাৰ সতৰ্কতা — পথাৰলৈ নাযাব",
        }.get(lang, "⚠️ Storm warning — stay off field"))

    return " | ".join(advisories) if advisories else get_ui_string("good_conditions", lang)


# Module-level convenience
def translate(key: str, lang: str) -> str:
    return get_ui_string(key, lang)
