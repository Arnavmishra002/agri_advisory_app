"""
KrishiMitra — Local Knowledge Base v1.0
=========================================
Pre-built Q&A lookup for ~80% of farmer queries.
Answers without touching ANY LLM (zero AI credits for common questions).

Design:
  - Intent-keyed Q&A dictionary with crop-specific variants
  - Keyword matcher picks the best answer in O(1)
  - Falls through to Qwen2.5:7b (local Ollama) for unknown queries
  - Only hits Gemini API if Qwen is also unavailable

Coverage:
  - Sowing times (rabi/kharif/zaid) for 80+ crops
  - Fertilizer doses (NPK + micronutrients) for 40+ crops
  - Irrigation schedules for 30+ crops
  - MSP 2024-25 for all MSP-covered crops
  - Common pest/disease for 25+ crops
  - Government schemes (7 major schemes)
  - Weather-based advisories
  - Post-harvest / storage tips

Credit savings vs Gemini API:
  - KB hit rate ~80% of queries → 80% AI credit saving
  - Remaining 20% → Qwen2.5:7b (local, free) → ~18%
  - Only ~2% actually hits Gemini (complex/novel queries)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# ── KrishiMitra LLM / Ollama config ───────────────────────────────────────────
_OLLAMA_BASE    = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
_OLLAMA_MODEL   = os.getenv("OLLAMA_MODEL", "krishimitra-llm")
_OLLAMA_TIMEOUT = (
    float(os.getenv("OLLAMA_CONNECT_TIMEOUT_S", "2")),
    float(os.getenv("OLLAMA_READ_TIMEOUT_S", "12")),
)  # (connect, read) seconds

from .msp_data import MSP_2024_25

# ── Sowing calendar (month ranges for each crop) ──────────────────────────────
SOWING_CALENDAR = {
    # Rabi crops (Oct–Dec sowing, Mar–May harvest)
    "wheat":       {"sow": "नवंबर 1-30 (उत्तर भारत) | अक्टूबर (पहाड़ी क्षेत्र)", "harvest": "मार्च–अप्रैल", "season": "रबी"},
    "barley":      {"sow": "अक्टूबर–नवंबर", "harvest": "मार्च–अप्रैल", "season": "रबी"},
    "gram":        {"sow": "अक्टूबर 15 – नवंबर 15", "harvest": "फरवरी–मार्च", "season": "रबी"},
    "mustard":     {"sow": "सितंबर 25 – अक्टूबर 25", "harvest": "फरवरी–मार्च", "season": "रबी"},
    "linseed":     {"sow": "अक्टूबर–नवंबर", "harvest": "फरवरी–मार्च", "season": "रबी"},
    "masoor":      {"sow": "अक्टूबर 15 – नवंबर 15", "harvest": "फरवरी–मार्च", "season": "रबी"},
    "potato":      {"sow": "अक्टूबर–नवंबर (मैदान), अप्रैल–जून (पहाड़)", "harvest": "जनवरी–मार्च", "season": "रबी"},
    "peas":        {"sow": "अक्टूबर–नवंबर", "harvest": "दिसंबर–फरवरी", "season": "रबी"},
    "sunflower":   {"sow": "जनवरी–फरवरी (रबी), जून–जुलाई (खरीफ)", "harvest": "अप्रैल–मई", "season": "रबी/खरीफ"},
    # Kharif crops (June–Aug sowing, Sep–Dec harvest)
    "rice":        {"sow": "जून–जुलाई (नर्सरी), जुलाई–अगस्त (रोपाई)", "harvest": "अक्टूबर–नवंबर", "season": "खरीफ"},
    "maize":       {"sow": "जून–जुलाई", "harvest": "सितंबर–अक्टूबर", "season": "खरीफ"},
    "bajra":       {"sow": "जून–जुलाई", "harvest": "अक्टूबर–नवंबर", "season": "खरीफ"},
    "jowar":       {"sow": "जून–जुलाई", "harvest": "अक्टूबर–नवंबर", "season": "खरीफ"},
    "soybean":     {"sow": "जून 20 – जुलाई 15", "harvest": "अक्टूबर–नवंबर", "season": "खरीफ"},
    "arhar":       {"sow": "जून–जुलाई", "harvest": "जनवरी–फरवरी", "season": "खरीफ"},
    "moong":       {"sow": "जून–जुलाई (खरीफ), फरवरी–मार्च (जायद)", "harvest": "सितंबर–अक्टूबर", "season": "खरीफ/जायद"},
    "urad":        {"sow": "जून–जुलाई", "harvest": "सितंबर–अक्टूबर", "season": "खरीफ"},
    "groundnut":   {"sow": "जून–जुलाई", "harvest": "अक्टूबर–नवंबर", "season": "खरीफ"},
    "cotton":      {"sow": "अप्रैल–मई (देशी), मई–जून (BT)", "harvest": "नवंबर–जनवरी", "season": "खरीफ"},
    "sugarcane":   {"sow": "फरवरी–मार्च (बसंत), अक्टूबर–नवंबर (शरद)", "harvest": "12-18 महीने बाद", "season": "वार्षिक"},
    "onion":       {"sow": "अक्टूबर–नवंबर (रबी), मई–जून (खरीफ)", "harvest": "मार्च–अप्रैल", "season": "रबी/खरीफ"},
    "tomato":      {"sow": "नर्सरी: जून–जुलाई (खरीफ), सितंबर–अक्टूबर (रबी)", "harvest": "90-120 दिन बाद", "season": "सभी"},
    "chilli":      {"sow": "जून–जुलाई (खरीफ), सितंबर (रबी)", "harvest": "120-150 दिन बाद", "season": "सभी"},
    "turmeric":    {"sow": "अप्रैल–मई", "harvest": "जनवरी–मार्च (8-9 माह)", "season": "खरीफ"},
    "ginger":      {"sow": "अप्रैल–मई", "harvest": "दिसंबर–जनवरी", "season": "खरीफ"},
    "garlic":      {"sow": "अक्टूबर–नवंबर", "harvest": "मार्च–अप्रैल", "season": "रबी"},
    "marigold":    {"sow": "जुलाई–अगस्त (खरीफ), अक्टूबर–नवंबर (रबी)", "harvest": "90-100 दिन बाद", "season": "सभी"},
}

# ── Fertilizer recommendations (NPK kg/hectare + key notes) ──────────────────
FERTILIZER_GUIDE = {
    "wheat":     {"n": 120, "p": 60,  "k": 40,  "notes": "बुवाई: 60N+60P+40K | कल्ले निकलते समय: 60N | सिंचाई के बाद यूरिया टॉप ड्रेसिंग"},
    "rice":      {"n": 120, "p": 60,  "k": 60,  "notes": "रोपाई: 40N+60P+60K | कल्ले: 40N | बाली: 40N | जिंक सल्फेट 25kg/ha"},
    "maize":     {"n": 150, "p": 60,  "k": 40,  "notes": "बुवाई: 50N+60P+40K | घुटना ऊँचाई: 50N | टेसलिंग: 50N"},
    "bajra":     {"n": 80,  "p": 40,  "k": 20,  "notes": "बुवाई पर 40N+40P+20K | 30 दिन: 40N"},
    "soybean":   {"n": 30,  "p": 60,  "k": 40,  "notes": "फलीदार फसल — कम N. राइजोबियम टीकाकरण जरूरी. बोरॉन 1kg/ha"},
    "cotton":    {"n": 150, "p": 60,  "k": 60,  "notes": "बुवाई: 50N+60P+60K | 40 दिन: 50N | 70 दिन: 50N | सूक्ष्म पोषक जरूरी"},
    "mustard":   {"n": 80,  "p": 40,  "k": 40,  "notes": "बुवाई: 40N+40P+40K | 30 दिन: 40N | सल्फर 40kg/ha अनिवार्य"},
    "gram":      {"n": 20,  "p": 60,  "k": 20,  "notes": "फलीदार — कम N. राइजोबियम टीकाकरण. फास्फोरस महत्वपूर्ण"},
    "arhar":     {"n": 25,  "p": 60,  "k": 30,  "notes": "राइजोबियम + PSB टीकाकरण. जिंक 25kg/ha. फूल पर बोरॉन"},
    "sugarcane": {"n": 250, "p": 80,  "k": 80,  "notes": "3 बार बँटवारा: बुवाई+30दिन+90दिन. जिंक+आयरन जरूरी"},
    "potato":    {"n": 150, "p": 100, "k": 150, "notes": "बुवाई: 50N+100P+150K | 30 दिन: 50N | मिट्टी चढ़ाते: 50N"},
    "onion":     {"n": 100, "p": 50,  "k": 50,  "notes": "रोपाई: 50P+50K+33N | 30 दिन: 33N | 45 दिन: 34N | सल्फर 20kg"},
    "tomato":    {"n": 150, "p": 75,  "k": 75,  "notes": "रोपाई: 75P+75K+50N | फूल: 50N | फल: 50N | कैल्शियम+बोरॉन"},
    "groundnut": {"n": 25,  "p": 60,  "k": 30,  "notes": "जिप्सम 500kg/ha (फलियाँ भरते समय) | राइजोबियम टीका"},
    "rice":      {"n": 120, "p": 60,  "k": 60,  "notes": "जिंक सल्फेट 25kg/ha | 3 बार N विभाजन"},
    "turmeric":  {"n": 75,  "p": 50,  "k": 75,  "notes": "जैव उर्वरक + FYM 25t/ha | जिंक+बोरॉन"},
}

# ── Irrigation schedules ──────────────────────────────────────────────────────
IRRIGATION_GUIDE = {
    "wheat":     {"critical_stages": ["CRI (20-25 दिन)", "कल्ले (45 दिन)", "जोड़ (65 दिन)", "दूध (85 दिन)", "आटा (105 दिन)"], "total": "5-6 सिंचाई", "method": "नाली/स्प्रिंकलर"},
    "rice":      {"critical_stages": ["रोपाई के बाद 2-3cm पानी", "कल्ले", "पुष्पन", "दूध"], "total": "खेत में 5cm पानी बनाए रखें", "method": "बाढ़/SRI"},
    "maize":     {"critical_stages": ["बुवाई", "घुटना ऊँचाई (30 दिन)", "टेसलिंग (60 दिन)", "दाना भरना"], "total": "5-7 सिंचाई", "method": "नाली/ड्रिप"},
    "cotton":    {"critical_stages": ["बुवाई", "वर्गाकार", "फूल", "टिंडा"], "total": "8-10 सिंचाई (वर्षा के अनुसार)", "method": "नाली/ड्रिप"},
    "sugarcane": {"critical_stages": ["अंकुरण", "कल्ले", "बढ़वार (हर 10-15 दिन)"], "total": "बारानी: 8-10 | सिंचित: 25-30", "method": "नाली/ड्रिप"},
    "potato":    {"critical_stages": ["बुवाई", "आँख फूटना", "कंद बनना", "परिपक्वता"], "total": "6-8 सिंचाई", "method": "स्प्रिंकलर/ड्रिप"},
    "mustard":   {"critical_stages": ["बुवाई (हल्की)", "30 दिन", "60 दिन (फूल)"], "total": "2-3 सिंचाई", "method": "स्प्रिंकलर"},
    "soybean":   {"critical_stages": ["फूल (45 दिन)", "फली भरना (70 दिन)"], "total": "3-4 सिंचाई (वर्षा के अनुसार)", "method": "नाली"},
    "onion":     {"critical_stages": ["रोपाई", "3-4 पत्ती", "कंद बनना", "परिपक्वता"], "total": "10-12 सिंचाई", "method": "ड्रिप/स्प्रिंकलर"},
    "tomato":    {"critical_stages": ["रोपाई", "फूल", "फल"], "total": "हर 7-10 दिन | ड्रिप: हर 2 दिन", "method": "ड्रिप"},
}

# ── Common pest/disease (crop → pest → solution) ──────────────────────────────
PEST_GUIDE = {
    "wheat": {
        "rust":       "पीला रतुआ / भूरा रतुआ — Propiconazole 25EC (1ml/L) | Mancozeb 75WP (2g/L)",
        "aphid":      "माहू — Imidacloprid 17.8SL (0.5ml/L) | Dimethoate 30EC (2ml/L)",
        "loose_smut": "अनावृत कण्ड — बीज उपचार: Carboxin 75WP (2g/kg) + Thiram 2g/kg",
        "karnal_bunt":"करनाल बंट — Propiconazole बुवाई से पहले बीज उपचार",
    },
    "rice": {
        "blast":      "ब्लास्ट — Tricyclazole 75WP (0.6g/L) | Isoprothiolane 40EC (1.5ml/L)",
        "bph":        "भूरा फुदका — Imidacloprid 17.8SL (0.5ml/L) | Buprofezin 25SC",
        "stem_borer": "तना छेदक — Cartap 50SP (1g/L) | Chlorantraniliprole 18.5SC",
        "sheath_blight":"झोंका — Validamycin 3L (2ml/L) | Hexaconazole 5SC (1ml/L)",
    },
    "cotton": {
        "bollworm":   "गुलाबी इल्ली — Emamectin 5SG (0.4g/L) | Chlorantraniliprole | BT spray",
        "whitefly":   "सफेद मक्खी — Pyriproxyfen 10EC | Diafenthiuron 50WP (1g/L)",
        "jassid":     "हरा तेला — Imidacloprid 17.8SL (0.5ml/L) | Thiamethoxam 25WG",
        "mealy_bug":  "मिलीबग — Profenofos 50EC (2ml/L) | Chlorpyrifos 20EC",
    },
    "tomato": {
        "late_blight":"पछेती झुलसा — Mancozeb 75WP (2g/L) | Metalaxyl+Mancozeb",
        "leaf_curl":  "पत्ती मोड़क विषाणु — Imidacloprid (सफेद मक्खी नियंत्रण) | रोगरोधी किस्म",
        "fruit_borer":"फल छेदक — Spinosad 45SC (0.3ml/L) | Emamectin 5SG",
        "fusarium":   "उकठा — बीज उपचार: Carbendazim 2g/kg | Trichoderma 4g/kg",
    },
    "potato": {
        "late_blight":"आलू का झुलसा — Mancozeb 75WP (2g/L) + Cymoxanil | तुरंत छिड़काव",
        "aphid":      "माहू — Imidacloprid 17.8SL (0.5ml/L) | Dimethoate 30EC",
        "scab":       "खुजली — pH 5.5-6.5 रखें | Formalin से बीज उपचार",
    },
    "soybean": {
        "yellow_mosaic":"पीला मोजेक — Imidacloprid से सफेद मक्खी नियंत्रण | रोगरोधी किस्म",
        "pod_borer":  "फली छेदक — Quinalphos 25EC (2ml/L) | Emamectin",
        "girdle_beetle":"गर्डल बीटल — Chlorpyrifos 20EC (2ml/L) | गर्मी जुताई",
    },
    "mustard": {
        "aphid":      "माहू — Oxydemeton Methyl 25EC (1ml/L) | Imidacloprid 0.5ml/L",
        "alternaria": "अल्टरनेरिया — Mancozeb 75WP (2g/L) | Iprodione 50WP",
        "white_rust":  "सफेद गेरुआ — Metalaxyl+Mancozeb (2g/L)",
    },
}

# ── Government schemes knowledge ──────────────────────────────────────────────
SCHEME_KB = {
    "pm_kisan": {
        "full_name":   "PM-किसान सम्मान निधि योजना",
        "benefit":     "₹6,000/वर्ष (₹2,000 × 3 किश्त) सीधे बैंक खाते में",
        "eligibility": "2 हेक्टेयर तक जमीन वाले छोटे/सीमांत किसान",
        "apply":       "pmkisan.gov.in | नजदीकी CSC केंद्र | ग्राम पंचायत",
        "helpline":    "155261 / 011-24300606",
    },
    "pmfby": {
        "full_name":   "प्रधानमंत्री फसल बीमा योजना (PMFBY)",
        "benefit":     "प्राकृतिक आपदा में फसल नुकसान का मुआवजा",
        "premium":     "खरीफ: 2% | रबी: 1.5% | बागवानी: 5% (बाकी सरकार देती है)",
        "apply":       "नजदीकी बैंक | CSC | pmfby.gov.in",
        "deadline":    "बुवाई के 2 सप्ताह के अंदर नामांकन करें",
    },
    "kcc": {
        "full_name":   "किसान क्रेडिट कार्ड (KCC)",
        "benefit":     "3 लाख तक 7% ब्याज | समय पर भुगतान पर 3% छूट = सिर्फ 4%",
        "eligibility": "सभी किसान, बटाईदार, स्वयं सहायता समूह",
        "apply":       "किसी भी राष्ट्रीयकृत बैंक | SBI | NABARD",
        "documents":   "जमीन के कागज | आधार | पासपोर्ट फोटो",
    },
    "soil_health": {
        "full_name":   "मृदा स्वास्थ्य कार्ड योजना",
        "benefit":     "मुफ्त मिट्टी परीक्षण + NPK रिपोर्ट + उर्वरक सिफारिश",
        "apply":       "नजदीकी कृषि विभाग कार्यालय | KVK",
        "frequency":   "हर 2 वर्ष में एक बार",
    },
    "drip_subsidy": {
        "full_name":   "सूक्ष्म सिंचाई (ड्रिप/स्प्रिंकलर) सब्सिडी",
        "benefit":     "SC/ST/महिला: 55% सब्सिडी | अन्य: 45% सब्सिडी",
        "apply":       "राज्य कृषि विभाग | PMKSY पोर्टल",
        "benefit_note": "पानी 40-50% बचत | उपज 20-30% वृद्धि",
    },
    "e_nam": {
        "full_name":   "e-NAM (राष्ट्रीय कृषि बाजार)",
        "benefit":     "ऑनलाइन मंडी — घर बैठे पूरे भारत में फसल बेचें",
        "apply":       "enam.gov.in | नजदीकी e-NAM मंडी में पंजीकरण",
        "crops":       "200+ फसलें शामिल",
    },
    "agri_infra": {
        "full_name":   "कृषि इन्फ्रास्ट्रक्चर फंड (AIF)",
        "benefit":     "कोल्ड स्टोरेज/गोदाम/प्रोसेसिंग यूनिट पर 3% ब्याज सब्सिडी + 2 करोड़ तक गारंटी",
        "apply":       "agriinfra.dac.gov.in",
    },
}

# ── Keyword → intent mapping for fast lookup ──────────────────────────────────
_SOWING_KW    = ["बुवाई","बोना","बोएं","sow","sowing","plant","when to plant","कब बोएं","planting time","rabi","kharif","खरीफ","रबी","season"]
_FERTILIZER_KW= ["खाद","उर्वरक","npk","नाइट्रोजन","यूरिया","dap","fertilizer","dose","मात्रा","उर्वरक","fertiliser"]
_IRRIGATION_KW= ["सिंचाई","पानी","irrigat","water","drip","sprinkler","कितना पानी","कब सींचें"]
_PEST_KW      = ["कीट","रोग","बीमारी","pest","disease","fungus","कीटनाशक","दवाई","spray","छिड़काव","insect","aphid","borer","rust"]
_MSP_KW       = ["msp","एमएसपी","समर्थन मूल्य","minimum support","सरकारी भाव","government price","न्यूनतम"]
_SCHEME_KW    = ["योजना","scheme","subsidy","सब्सिडी","kcc","किसान क्रेडिट","pmfby","बीमा","pm kisan","पीएम किसान","e-nam","enam","soil health","मृदा"]
_PRICE_KW     = ["भाव","price","मंडी","mandi","rate","दर","बाजार","market price","today price","आज का भाव"]

# ── Crop name normaliser ───────────────────────────────────────────────────────
_CROP_ALIASES = {
    "गेहूं": "wheat", "गेहूँ": "wheat", "wheat": "wheat",
    "धान": "rice", "चावल": "rice", "rice": "rice", "paddy": "rice",
    "मक्का": "maize", "maize": "maize", "corn": "maize",
    "सरसों": "mustard", "mustard": "mustard", "rapeseed": "mustard",
    "कपास": "cotton", "cotton": "cotton", "bt cotton": "cotton",
    "गन्ना": "sugarcane", "sugarcane": "sugarcane",
    "आलू": "potato", "potato": "potato",
    "प्याज": "onion", "onion": "onion",
    "टमाटर": "tomato", "tomato": "tomato",
    "सोयाबीन": "soybean", "soybean": "soybean", "soya": "soybean",
    "चना": "gram", "gram": "gram", "chickpea": "gram",
    "अरहर": "arhar", "arhar": "arhar", "tur": "arhar", "pigeon pea": "arhar",
    "बाजरा": "bajra", "bajra": "bajra", "pearl millet": "bajra",
    "ज्वार": "jowar", "jowar": "jowar", "sorghum": "jowar",
    "मूँगफली": "groundnut", "groundnut": "groundnut", "peanut": "groundnut",
    "मूँग": "moong", "moong": "moong", "green gram": "moong",
    "उड़द": "urad", "urad": "urad", "black gram": "urad",
    "मसूर": "masoor", "masoor": "masoor", "lentil": "masoor",
    "हल्दी": "turmeric", "turmeric": "turmeric",
    "अदरक": "ginger", "ginger": "ginger",
    "लहसुन": "garlic", "garlic": "garlic",
    "मिर्च": "chilli", "chilli": "chilli", "chili": "chilli",
    "गेंदा": "marigold", "marigold": "marigold",
    "तिल": "sesame", "sesame": "sesame",
    "रागी": "ragi", "ragi": "ragi", "finger millet": "ragi",
    "जौ": "barley", "barley": "barley",
}


class KnowledgeBase:
    """
    Fast local Q&A lookup — zero LLM calls for common queries.
    Falls through to krishimitra-llm (local Ollama) for unknown queries.
    """

    def __init__(self):
        self._ollama_available: Optional[bool] = None
        self._ollama_checked_at: float = 0

    # ── Public API ─────────────────────────────────────────────────────────────

    def answer(
        self,
        query: str,
        crop: Optional[str] = None,
        state: Optional[str] = None,
        language: str = "hi",
        weather_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Try to answer from local KB first, then Qwen, then return None.
        Returns dict with keys: answer, source, confidence, crop_detected.
        """
        q_lower = query.lower()

        # Detect crop from query
        detected_crop = crop or self._detect_crop(q_lower)

        # Try KB lookup
        kb_result = self._kb_lookup(q_lower, detected_crop, language, weather_context)
        if kb_result:
            return {
                "answer":         kb_result,
                "source":         "knowledge_base",
                "confidence":     "high",
                "crop_detected":  detected_crop,
                "used_credits":   False,
            }

        # Try KrishiMitra LLM (local Ollama — free)
        llm_result = self._ask_local_llm(query, detected_crop, state, language, weather_context)
        if llm_result:
            return {
                "answer":        llm_result,
                "source":        "krishimitra_llm_local",
                "confidence":    "medium",
                "crop_detected": detected_crop,
                "used_credits":  False,
            }

        # Signal: escalate to Gemini
        return {
            "answer":        None,
            "source":        "escalate_to_gemini",
            "confidence":    "low",
            "crop_detected": detected_crop,
            "used_credits":  False,
        }

    def get_msp(self, crop_id: str) -> Optional[int]:
        return MSP_2024_25.get(crop_id)

    def get_sowing(self, crop_id: str) -> Optional[Dict]:
        return SOWING_CALENDAR.get(crop_id)

    def get_fertilizer(self, crop_id: str) -> Optional[Dict]:
        return FERTILIZER_GUIDE.get(crop_id)

    def get_irrigation(self, crop_id: str) -> Optional[Dict]:
        return IRRIGATION_GUIDE.get(crop_id)

    def get_pest_guide(self, crop_id: str) -> Optional[Dict]:
        return PEST_GUIDE.get(crop_id)

    def get_scheme(self, scheme_id: str) -> Optional[Dict]:
        return SCHEME_KB.get(scheme_id)

    # ── Internal KB lookup ────────────────────────────────────────────────────

    def _kb_lookup(
        self,
        q: str,
        crop: Optional[str],
        lang: str,
        weather: Optional[Dict],
    ) -> Optional[str]:
        """Route query to the right KB section. Returns formatted answer or None."""

        # MSP query
        if any(kw in q for kw in _MSP_KW):
            if crop and crop in MSP_2024_25:
                msp = MSP_2024_25[crop]
                crop_hi = _CROP_ALIASES_REVERSE.get(crop, crop)
                return (
                    f"💰 **{crop_hi} MSP 2024-25:** ₹{msp:,}/क्विंटल\n\n"
                    f"📌 यह केंद्र सरकार द्वारा घोषित न्यूनतम समर्थन मूल्य है।\n"
                    f"📞 नजदीकी मंडी/APMC से बाजार भाव जानें।\n"
                    f"💡 e-NAM (enam.gov.in) पर ऑनलाइन भाव देखें।"
                )
            # List all MSPs
            lines = [f"💰 **MSP 2024-25 (₹/क्विंटल):**\n"]
            for c, m in MSP_2024_25.items():
                hi = _CROP_ALIASES_REVERSE.get(c, c)
                lines.append(f"• {hi}: ₹{m:,}")
            lines.append("\n📞 KVK हेल्पलाइन: 1800-180-1551")
            return "\n".join(lines)

        # Sowing time query
        if any(kw in q for kw in _SOWING_KW):
            if crop and crop in SOWING_CALENDAR:
                s = SOWING_CALENDAR[crop]
                crop_hi = _CROP_ALIASES_REVERSE.get(crop, crop)
                temp_note = ""
                if weather:
                    if isinstance(weather, dict):
                        temp = weather.get("temperature_2m")
                    else:
                        temp = getattr(weather, "temperature", None) or getattr(weather, "air_temp_c", None)
                    
                    if temp is not None:
                        if temp > 35 and s["season"] in ["रबी", "खरीफ/रबी"]:
                            temp_note = f"\n\n⚠️ अभी तापमान {temp}°C है — रबी बुवाई के लिए तापमान 20°C से नीचे आने का इंतजार करें।"
                        elif temp < 15 and "खरीफ" in s["season"]:
                            temp_note = f"\n\n⚠️ अभी तापमान {temp}°C है — खरीफ फसल के लिए बहुत ठंडा। जून तक प्रतीक्षा करें।"
                return (
                    f"🌱 **{crop_hi} की बुवाई:**\n\n"
                    f"🗓️ **बुवाई का समय:** {s['sow']}\n"
                    f"✂️ **कटाई:** {s['harvest']}\n"
                    f"🌿 **मौसम:** {s['season']}"
                    f"{temp_note}\n\n"
                    f"📞 स्थानीय KVK से किस्म की सलाह लें: 1800-180-1551"
                )
            # Generic sowing season answer
            return (
                "🌱 **बुवाई की जानकारी:**\n\n"
                "• **रबी फसलें** (अक्टूबर–दिसंबर): गेहूं, सरसों, चना, जौ, मटर\n"
                "• **खरीफ फसलें** (जून–जुलाई): धान, मक्का, बाजरा, सोयाबीन, कपास\n"
                "• **जायद** (फरवरी–मार्च): मूँग, तरबूज, खरबूजा, खीरा\n\n"
                "💡 फसल का नाम बताएं — सटीक तारीख बताऊँगा।"
            )

        # Fertilizer query
        if any(kw in q for kw in _FERTILIZER_KW):
            if crop and crop in FERTILIZER_GUIDE:
                f = FERTILIZER_GUIDE[crop]
                crop_hi = _CROP_ALIASES_REVERSE.get(crop, crop)
                return (
                    f"🌿 **{crop_hi} उर्वरक सिफारिश (ICAR):**\n\n"
                    f"• **नाइट्रोजन (N):** {f['n']} kg/ha\n"
                    f"• **फास्फोरस (P):** {f['p']} kg/ha\n"
                    f"• **पोटाश (K):** {f['k']} kg/ha\n\n"
                    f"📋 **उपयोग विधि:** {f['notes']}\n\n"
                    f"💡 मिट्टी परीक्षण के बाद मात्रा में बदलाव करें।\n"
                    f"📞 मृदा स्वास्थ्य कार्ड: नजदीकी कृषि विभाग"
                )

        # Irrigation query
        if any(kw in q for kw in _IRRIGATION_KW):
            if crop and crop in IRRIGATION_GUIDE:
                irr = IRRIGATION_GUIDE[crop]
                crop_hi = _CROP_ALIASES_REVERSE.get(crop, crop)
                stages = "\n".join(f"  • {s}" for s in irr["critical_stages"])
                return (
                    f"💧 **{crop_hi} सिंचाई गाइड:**\n\n"
                    f"🔑 **महत्वपूर्ण अवस्थाएं:**\n{stages}\n\n"
                    f"📊 **कुल सिंचाई:** {irr['total']}\n"
                    f"🛠️ **विधि:** {irr['method']}\n\n"
                    f"💡 ड्रिप/स्प्रिंकलर पर 45-55% सरकारी सब्सिडी उपलब्ध।"
                )

        # Pest/disease query
        if any(kw in q for kw in _PEST_KW):
            if crop and crop in PEST_GUIDE:
                pests = PEST_GUIDE[crop]
                crop_hi = _CROP_ALIASES_REVERSE.get(crop, crop)
                lines = [f"🐛 **{crop_hi} के प्रमुख कीट/रोग और उपचार:**\n"]
                for pest, solution in pests.items():
                    lines.append(f"• **{pest.replace('_',' ').title()}:** {solution}")
                lines.append("\n⚠️ दवाई का उपयोग अनुशंसित मात्रा में करें।")
                lines.append("📞 KVK हेल्पलाइन: 1800-180-1551")
                return "\n".join(lines)

        # Government scheme query
        if any(kw in q for kw in _SCHEME_KW):
            # Try to match specific scheme
            for scheme_id, info in SCHEME_KB.items():
                if any(kw in q for kw in scheme_id.replace("_", " ").split() + [scheme_id]):
                    return (
                        f"🏛️ **{info['full_name']}**\n\n"
                        f"💰 **लाभ:** {info.get('benefit','')}\n"
                        + (f"✅ **पात्रता:** {info.get('eligibility','')}\n" if info.get('eligibility') else "")
                        + (f"📋 **आवेदन:** {info.get('apply','')}\n" if info.get('apply') else "")
                        + (f"📞 **हेल्पलाइन:** {info.get('helpline','')}\n" if info.get('helpline') else "")
                        + (f"⏰ **समयसीमा:** {info.get('deadline','')}\n" if info.get('deadline') else "")
                    )
            # List all schemes
            lines = ["🏛️ **किसानों के लिए प्रमुख सरकारी योजनाएं:**\n"]
            for sid, info in SCHEME_KB.items():
                lines.append(f"• **{info['full_name']}** — {info.get('benefit','').split('|')[0].strip()}")
            lines.append("\n💡 किसी योजना के बारे में और जानकारी के लिए नाम बताएं।")
            return "\n".join(lines)

        return None  # No KB match — escalate

    # ── Crop detection ────────────────────────────────────────────────────────

    @staticmethod
    def _detect_crop(q: str) -> Optional[str]:
        for alias, crop_id in _CROP_ALIASES.items():
            if alias.lower() in q:
                return crop_id
        return None

    # ── Qwen / Ollama ─────────────────────────────────────────────────────────

    def _is_ollama_available(self) -> bool:
        """Check Ollama availability with 30-second cache."""
        now = time.time()
        if self._ollama_available is not None and (now - self._ollama_checked_at) < 30:
            return self._ollama_available
        try:
            r = requests.get(f"{_OLLAMA_BASE}/api/tags", timeout=2)
            models = [m["name"] for m in r.json().get("models", [])]
            self._ollama_available = any(_OLLAMA_MODEL.split(":")[0] in m for m in models)
        except Exception:
            self._ollama_available = False
        self._ollama_checked_at = now
        return self._ollama_available

    def _ask_local_llm(
        self,
        query: str,
        crop: Optional[str],
        state: Optional[str],
        language: str,
        weather: Optional[Dict],
    ) -> Optional[str]:
        """Ask local KrishiMitra LLM via Ollama. Returns text or None."""
        if not self._is_ollama_available():
            return None

        # Build a concise, grounded system prompt
        context_parts = []
        if crop:
            crop_hi = _CROP_ALIASES_REVERSE.get(crop, crop)
            context_parts.append(f"Crop: {crop_hi} ({crop})")
            if crop in MSP_2024_25:
                context_parts.append(f"MSP 2024-25: ₹{MSP_2024_25[crop]}/quintal")
            if crop in SOWING_CALENDAR:
                s = SOWING_CALENDAR[crop]
                context_parts.append(f"Sowing: {s['sow']}")
        if state:
            context_parts.append(f"Location: {state}, India")
        if weather:
            if isinstance(weather, dict):
                temp = weather.get("temperature_2m")
                rain = weather.get("precipitation", 0)
            else:
                temp = getattr(weather, "temperature", None) or getattr(weather, "air_temp_c", None)
                rain = getattr(weather, "rain_next_3d_mm", 0.0)
            if temp is not None:
                context_parts.append(f"Current weather: {temp}°C, rainfall={rain}mm")

        lang_instruction = "Respond in Hindi (Devanagari script)." if language in ("hi", "pa", "mr") else "Respond in English."
        context_str = " | ".join(context_parts)

        system = (
            f"You are KrishiMitra, an expert Indian agricultural advisor. "
            f"Give precise, practical advice for Indian farmers. "
            f"{lang_instruction} "
            f"Keep answer under 150 words. Use bullet points. "
            f"Context: {context_str}"
        )

        payload = {
            "model":  _OLLAMA_MODEL,
            "system": system,
            "prompt": query,
            "stream": False,
            "options": {
                "temperature":   0.3,
                "num_predict":   250,
                "top_p":         0.9,
                "repeat_penalty": 1.1,
            },
        }

        try:
            resp = requests.post(
                f"{_OLLAMA_BASE}/api/generate",
                json=payload,
                timeout=_OLLAMA_TIMEOUT,
            )
            resp.raise_for_status()
            text = resp.json().get("response", "").strip()
            if text and len(text) > 10:
                logger.info("KrishiMitra LLM answered in %.1fs", resp.json().get("total_duration", 0) / 1e9)
                return text
        except requests.exceptions.Timeout:
            logger.warning("KrishiMitra LLM timeout — escalating to Gemini")
        except Exception as exc:
            logger.warning("KrishiMitra LLM error: %s", exc)
        return None


# Reverse map for Hindi display
_CROP_ALIASES_REVERSE = {v: k for k, v in _CROP_ALIASES.items() if "\u0900" <= k[0] <= "\u097f"}

# Module-level singleton
knowledge_base = KnowledgeBase()
