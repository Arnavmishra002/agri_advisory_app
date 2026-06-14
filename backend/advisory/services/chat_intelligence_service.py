#!/usr/bin/env python3
"""
KrishiMitra Chat Intelligence Service v5.0
==========================================
Super-intelligent, fully-interconnected agricultural chatbot.

Features:
- Multi-turn conversation with full history context
- 22-language NLP intent detection + Hinglish normalisation
- 19 intent categories: irrigation, sowing, harvest, storage, organic, seed,
  insurance, profit, pest/disease, soil, fertilizer, weather, market, schemes,
  crop info, crop recommendation, greeting, follow-up, general
- Live data grounding: weather, mandi prices, crop recommendations, schemes
- Field-level IoT sensor integration (NPK, pH, moisture, soil temp)
- District-level soil/climate profile for location-specific advice
- Comprehensive crop database (150+ crops, full agronomic profiles)
- Disease→Chat bridge: ML photo diagnosis feeds directly into chatbot
- Gemini AI primary + Qwen2.5+RAG (local) + Rule-based fallback
- Farmer profile personalisation: crop history, farm size, soil health card
"""

from __future__ import annotations

import atexit
import json
import logging
import re
import re as _re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .crop_catalog import crop_catalog
from .crop_recommendation_engine import crop_recommendation_engine
from .language_service import (
    normalise_language_code,
    get_gemini_language_instruction,
    get_language_for_state,
    get_ui_string,
    translate_farming_advice,
)
from .location_context import LocationContext
from .unified_realtime_service import (
    MSP_2024_25,
    _is_valid_gemini_key,
    gemini_service,
    iot_blockchain,
    market_service,
    schemes_service,
    weather_service,
)

# ── Additional service imports for full interconnection ──────────────────────
# These are imported lazily in methods to avoid circular imports at startup,
# but we reference the module here for IDE type-checking.
try:
    from .comprehensive_crop_database import ALL_CROP_DATA as _ALL_CROP_DATA
    from .field_sensor_service import (
        field_sensor_service,
        CROP_SOIL_REQUIREMENTS as _CROP_SOIL_REQ,
    )
    from .district_data import DISTRICT_PROFILES as _DISTRICT_PROFILES
except ImportError:
    _ALL_CROP_DATA = {}
    field_sensor_service = None          # type: ignore[assignment]
    _CROP_SOIL_REQ = {}
    _DISTRICT_PROFILES = {}

logger = logging.getLogger(__name__)

# FIX 4: Module-level pool — created once, reused for all requests.
# Per-request ThreadPoolExecutor spawned 3 threads per chat call; at 100
# concurrent users that’s 300 threads being created+destroyed simultaneously,
# risking OOM and OS ulimit breaches.
_DATA_FETCH_POOL = ThreadPoolExecutor(max_workers=6, thread_name_prefix="km-fetch")
atexit.register(_DATA_FETCH_POOL.shutdown, wait=False)

# ── Module-level Hindi→English term map (used by _qwen_rag_answer) ───────────
# Built once at import time instead of on every request.
_HINDI_ENGLISH_MAP: Dict[str, str] = {
    "गेहूँ": "wheat", "गेहू": "wheat", "गेहुं": "wheat",
    "धान": "rice paddy", "चावल": "rice",
    "मक्का": "maize corn", "ज्वार": "jowar sorghum",
    "बाजरा": "bajra pearl millet",
    "सरसों": "mustard rapeseed",
    "कपास": "cotton", "गन्ना": "sugarcane",
    "सोयाबीन": "soybean",
    "मूँगफली": "groundnut peanut",
    "चना": "chickpea gram",
    "अरहर": "pigeonpea arhar",
    "मूँग": "moong green gram",
    "उड़द": "urad black gram",
    "हल्दी": "turmeric", "अदरक": "ginger",
    "लहसुन": "garlic", "प्याज": "onion",
    "आलू": "potato", "टमाटर": "tomato",
    "बैंगन": "brinjal", "मिर्च": "chilli",
    "आम": "mango", "केला": "banana",
    "अनार": "pomegranate",
    "माहू": "aphid",
    "सुंडी": "caterpillar larva",
    "तना छेदक": "stem borer",
    "सफेद मक्खी": "whitefly",
    "थ्रिप्स": "thrips",
    "झुलसा": "blight",
    "फफूंदी": "fungal disease mold",
    "जड़ सड़न": "root rot",
    "पीलापन": "yellowing chlorosis",
    "रोग": "disease", "कीट": "pest",
    "कीटनाशक": "pesticide insecticide",
    "दवाई": "pesticide treatment",
    "नीम": "neem",
    "सिंचाई": "irrigation water",
    "बुवाई": "sowing planting",
    "खाद": "fertilizer manure",
    "उर्वरक": "fertilizer",
    "मिट्टी": "soil",
    "उपज": "yield",
    "फसल": "crop",
    "बारिश": "rain rainfall",
    "मौसम": "weather season",
    "तापमान": "temperature",
    "नमी": "moisture humidity",
    "योजना": "scheme",
    "सब्सिडी": "subsidy",
    "बीमा": "insurance",
    "किसान": "farmer",
    "मंडी": "mandi market",
    "एमएसपी": "msp minimum support price",
}
_DEVANAGARI_RE = _re.compile(r"[\u0900-\u097F]")


def _augment_hindi_query(query: str) -> str:
    """Append English equivalents for Hindi terms found in query.
    Called once before sending to Phase 1 RAG server."""
    if not _DEVANAGARI_RE.search(query):
        return query
    extras = [eng for hi, eng in _HINDI_ENGLISH_MAP.items() if hi in query]
    return (query + " " + " ".join(extras)) if extras else query

# ── Intent labels ────────────────────────────────────────────────
INTENT_CROP_RECOMMENDATION = "crop_recommendation"
INTENT_MARKET_PRICE        = "market_price"
INTENT_WEATHER             = "weather"
INTENT_GOVERNMENT_SCHEME   = "government_scheme"
INTENT_PEST_DISEASE        = "pest_disease"
INTENT_SOIL                = "soil"
INTENT_IRRIGATION          = "irrigation"
INTENT_FERTILIZER          = "fertilizer"
INTENT_CROP_INFO           = "crop_info"
INTENT_GREETING            = "greeting"
INTENT_GENERAL             = "general"
INTENT_FOLLOWUP            = "followup"
# New high-value intents
INTENT_HARVEST             = "harvest"          # When to harvest, signs of maturity
INTENT_SOWING              = "sowing"           # When/how to sow, seed rate, spacing
INTENT_STORAGE             = "storage"          # Post-harvest storage, mandi timing
INTENT_ORGANIC             = "organic_farming"  # Organic methods, vermicompost, bio-inputs
INTENT_PROFIT_CALC         = "profit_calc"      # Cost-benefit, profit per bigha/hectare
INTENT_SEED                = "seed"             # Seed variety, certified seed, seed treatment
INTENT_INSURANCE           = "insurance"        # PMFBY claim, crop loss, compensation

STAPLE_FOR_CHAT = ["wheat", "rice", "maize", "mustard", "tomato", "onion", "potato"]

# ── Indian city/district catalog for named-location weather queries ────────────
# Used by _extract_query_location() to detect city names in chat messages like
# "rampur ka mausam" → return Rampur's coordinates instead of GPS location.
# Covers all state capitals + major agricultural districts (~250 entries).
_INDIAN_CITY_CATALOG: Dict[str, Tuple[str, str, float, float]] = {
    # key(lowercase): (display_name, state, lat, lon)
    # ── Metros ──
    "delhi": ("Delhi", "Delhi", 28.7041, 77.1025),
    "mumbai": ("Mumbai", "Maharashtra", 19.0760, 72.8777),
    "bangalore": ("Bangalore", "Karnataka", 12.9716, 77.5946),
    "bengaluru": ("Bangalore", "Karnataka", 12.9716, 77.5946),
    "hyderabad": ("Hyderabad", "Telangana", 17.3850, 78.4867),
    "chennai": ("Chennai", "Tamil Nadu", 13.0827, 80.2707),
    "kolkata": ("Kolkata", "West Bengal", 22.5726, 88.3639),
    # ── State capitals ──
    "lucknow": ("Lucknow", "Uttar Pradesh", 26.8467, 80.9462),
    "jaipur": ("Jaipur", "Rajasthan", 26.9124, 75.7873),
    "bhopal": ("Bhopal", "Madhya Pradesh", 23.2599, 77.4126),
    "patna": ("Patna", "Bihar", 25.5941, 85.1376),
    "raipur": ("Raipur", "Chhattisgarh", 21.2514, 81.6296),
    "ranchi": ("Ranchi", "Jharkhand", 23.3441, 85.3096),
    "bhubaneswar": ("Bhubaneswar", "Odisha", 20.2961, 85.8245),
    "guwahati": ("Guwahati", "Assam", 26.1445, 91.7362),
    "dehradun": ("Dehradun", "Uttarakhand", 30.3165, 78.0322),
    "shimla": ("Shimla", "Himachal Pradesh", 31.1048, 77.1734),
    "chandigarh": ("Chandigarh", "Chandigarh", 30.7333, 76.7794),
    "jammu": ("Jammu", "J&K", 32.7266, 74.8570),
    "srinagar": ("Srinagar", "J&K", 34.0837, 74.7973),
    "gandhinagar": ("Gandhinagar", "Gujarat", 23.2156, 72.6369),
    "panaji": ("Panaji", "Goa", 15.4909, 73.8278),
    "thiruvananthapuram": ("Thiruvananthapuram", "Kerala", 8.5241, 76.9366),
    "trivandrum": ("Thiruvananthapuram", "Kerala", 8.5241, 76.9366),
    "bangalore": ("Bangalore", "Karnataka", 12.9716, 77.5946),
    "imphal": ("Imphal", "Manipur", 24.8170, 93.9368),
    "shillong": ("Shillong", "Meghalaya", 25.5788, 91.8933),
    "aizawl": ("Aizawl", "Mizoram", 23.7271, 92.7176),
    "kohima": ("Kohima", "Nagaland", 25.6751, 94.1086),
    "itanagar": ("Itanagar", "Arunachal Pradesh", 27.0844, 93.6053),
    "agartala": ("Agartala", "Tripura", 23.8315, 91.2868),
    "gangtok": ("Gangtok", "Sikkim", 27.3314, 88.6138),
    "dispur": ("Dispur", "Assam", 26.1433, 91.7898),
    "amaravati": ("Amaravati", "Andhra Pradesh", 16.5062, 80.6480),
    "vijayawada": ("Vijayawada", "Andhra Pradesh", 16.5062, 80.6480),
    "port blair": ("Port Blair", "Andaman", 11.6234, 92.7265),
    # ── Major agricultural cities (UP) ──
    "agra": ("Agra", "Uttar Pradesh", 27.1767, 78.0081),
    "varanasi": ("Varanasi", "Uttar Pradesh", 25.3176, 82.9739),
    "kanpur": ("Kanpur", "Uttar Pradesh", 26.4499, 80.3319),
    "allahabad": ("Prayagraj", "Uttar Pradesh", 25.4358, 81.8463),
    "prayagraj": ("Prayagraj", "Uttar Pradesh", 25.4358, 81.8463),
    "meerut": ("Meerut", "Uttar Pradesh", 28.9845, 77.7064),
    "bareilly": ("Bareilly", "Uttar Pradesh", 28.3670, 79.4304),
    "aligarh": ("Aligarh", "Uttar Pradesh", 27.8974, 78.0880),
    "moradabad": ("Moradabad", "Uttar Pradesh", 28.8386, 78.7733),
    "saharanpur": ("Saharanpur", "Uttar Pradesh", 29.9640, 77.5460),
    "gorakhpur": ("Gorakhpur", "Uttar Pradesh", 26.7606, 83.3732),
    "faizabad": ("Faizabad", "Uttar Pradesh", 26.7749, 82.1376),
    "mathura": ("Mathura", "Uttar Pradesh", 27.4924, 77.6737),
    "rampur": ("Rampur", "Uttar Pradesh", 28.8055, 79.0131),
    "noida": ("Noida", "Uttar Pradesh", 28.5355, 77.3910),
    "ghaziabad": ("Ghaziabad", "Uttar Pradesh", 28.6692, 77.4538),
    "muzaffarnagar": ("Muzaffarnagar", "Uttar Pradesh", 29.4727, 77.7085),
    "shahjahanpur": ("Shahjahanpur", "Uttar Pradesh", 27.8838, 79.9058),
    "etawah": ("Etawah", "Uttar Pradesh", 26.7782, 79.0219),
    "lakhimpur": ("Lakhimpur Kheri", "Uttar Pradesh", 27.9497, 80.7877),
    "sitapur": ("Sitapur", "Uttar Pradesh", 27.5640, 80.6820),
    "jhansi": ("Jhansi", "Uttar Pradesh", 25.4484, 78.5685),
    "banda": ("Banda", "Uttar Pradesh", 25.4742, 80.3352),
    "unnao": ("Unnao", "Uttar Pradesh", 26.5497, 80.4983),
    "rae bareli": ("Rae Bareli", "Uttar Pradesh", 26.2311, 81.2321),
    "raebareli": ("Rae Bareli", "Uttar Pradesh", 26.2311, 81.2321),
    "sultanpur": ("Sultanpur", "Uttar Pradesh", 26.2648, 82.0727),
    "azamgarh": ("Azamgarh", "Uttar Pradesh", 26.0692, 83.1836),
    "jaunpur": ("Jaunpur", "Uttar Pradesh", 25.7468, 82.6836),
    "bijnor": ("Bijnor", "Uttar Pradesh", 29.3721, 78.1358),
    "amroha": ("Amroha", "Uttar Pradesh", 28.9042, 78.4685),
    "bulandshahr": ("Bulandshahr", "Uttar Pradesh", 28.4069, 77.8495),
    "hapur": ("Hapur", "Uttar Pradesh", 28.7295, 77.7795),
    "firozabad": ("Firozabad", "Uttar Pradesh", 27.1520, 78.3950),
    "hardoi": ("Hardoi", "Uttar Pradesh", 27.3947, 80.1206),
    "barabanki": ("Barabanki", "Uttar Pradesh", 26.9336, 81.1961),
    "bahraich": ("Bahraich", "Uttar Pradesh", 27.5740, 81.5960),
    "ballia": ("Ballia", "Uttar Pradesh", 25.7596, 84.1485),
    "basti": ("Basti", "Uttar Pradesh", 26.7964, 82.7327),
    "mirzapur": ("Mirzapur", "Uttar Pradesh", 25.1452, 82.5693),
    "sonbhadra": ("Sonbhadra", "Uttar Pradesh", 24.6899, 83.0680),
    # ── Punjab / Haryana / Himachal ──
    "ludhiana": ("Ludhiana", "Punjab", 30.9010, 75.8573),
    "amritsar": ("Amritsar", "Punjab", 31.6340, 74.8723),
    "patiala": ("Patiala", "Punjab", 30.3398, 76.3869),
    "jalandhar": ("Jalandhar", "Punjab", 31.3260, 75.5762),
    "bathinda": ("Bathinda", "Punjab", 30.2110, 74.9455),
    "ferozepur": ("Ferozepur", "Punjab", 30.9238, 74.6234),
    "gurdaspur": ("Gurdaspur", "Punjab", 32.0349, 75.4057),
    "pathankot": ("Pathankot", "Punjab", 32.2643, 75.6572),
    "hoshiarpur": ("Hoshiarpur", "Punjab", 31.5143, 75.9109),
    "faridkot": ("Faridkot", "Punjab", 30.6680, 74.7577),
    "rohtak": ("Rohtak", "Haryana", 28.8955, 76.6066),
    "hisar": ("Hisar", "Haryana", 29.1492, 75.7217),
    "sirsa": ("Sirsa", "Haryana", 29.5330, 75.0193),
    "karnal": ("Karnal", "Haryana", 29.6857, 76.9905),
    "panipat": ("Panipat", "Haryana", 29.3909, 76.9635),
    "ambala": ("Ambala", "Haryana", 30.3782, 76.7767),
    "faridabad": ("Faridabad", "Haryana", 28.4089, 77.3178),
    "gurgaon": ("Gurgaon", "Haryana", 28.4595, 77.0266),
    "gurugram": ("Gurgaon", "Haryana", 28.4595, 77.0266),
    "rewari": ("Rewari", "Haryana", 28.1961, 76.6166),
    "kaithal": ("Kaithal", "Haryana", 29.8014, 76.3998),
    "kurukshetra": ("Kurukshetra", "Haryana", 29.9695, 76.8783),
    "yamunanagar": ("Yamunanagar", "Haryana", 30.1290, 77.2674),
    "mandi": ("Mandi", "Himachal Pradesh", 31.7080, 76.9318),
    "kullu": ("Kullu", "Himachal Pradesh", 31.9579, 77.1095),
    "dharamsala": ("Dharamsala", "Himachal Pradesh", 32.2190, 76.3234),
    "una": ("Una", "Himachal Pradesh", 31.4686, 76.2701),
    "bilaspur": ("Bilaspur", "Himachal Pradesh", 31.3311, 76.7603),
    # ── Rajasthan ──
    "jodhpur": ("Jodhpur", "Rajasthan", 26.2389, 73.0243),
    "kota": ("Kota", "Rajasthan", 25.2138, 75.8648),
    "ajmer": ("Ajmer", "Rajasthan", 26.4499, 74.6399),
    "bikaner": ("Bikaner", "Rajasthan", 28.0229, 73.3119),
    "udaipur": ("Udaipur", "Rajasthan", 24.5854, 73.7125),
    "alwar": ("Alwar", "Rajasthan", 27.5530, 76.6346),
    "bharatpur": ("Bharatpur", "Rajasthan", 27.2152, 77.4931),
    "ganganagar": ("Ganganagar", "Rajasthan", 29.9038, 73.8772),
    "hanumangarh": ("Hanumangarh", "Rajasthan", 29.5826, 74.3301),
    "churu": ("Churu", "Rajasthan", 28.2996, 74.9665),
    "sikar": ("Sikar", "Rajasthan", 27.6094, 75.1398),
    "nagaur": ("Nagaur", "Rajasthan", 27.2032, 73.7383),
    "barmer": ("Barmer", "Rajasthan", 25.7521, 71.3967),
    "jaisalmer": ("Jaisalmer", "Rajasthan", 26.9157, 70.9083),
    "jhalawar": ("Jhalawar", "Rajasthan", 24.5979, 76.1586),
    # ── Madhya Pradesh ──
    "indore": ("Indore", "Madhya Pradesh", 22.7196, 75.8577),
    "gwalior": ("Gwalior", "Madhya Pradesh", 26.2183, 78.1828),
    "jabalpur": ("Jabalpur", "Madhya Pradesh", 23.1815, 79.9864),
    "ujjain": ("Ujjain", "Madhya Pradesh", 23.1765, 75.7885),
    "sagar": ("Sagar", "Madhya Pradesh", 23.8388, 78.7378),
    "rewa": ("Rewa", "Madhya Pradesh", 24.5332, 81.3042),
    "satna": ("Satna", "Madhya Pradesh", 24.5785, 80.8322),
    "hoshangabad": ("Hoshangabad", "Madhya Pradesh", 22.7513, 77.7264),
    "betul": ("Betul", "Madhya Pradesh", 21.9060, 77.9019),
    "chhindwara": ("Chhindwara", "Madhya Pradesh", 22.0574, 78.9382),
    "dewas": ("Dewas", "Madhya Pradesh", 22.9623, 76.0508),
    "mandsaur": ("Mandsaur", "Madhya Pradesh", 24.0739, 75.0710),
    "neemuch": ("Neemuch", "Madhya Pradesh", 24.4752, 74.8680),
    "ratlam": ("Ratlam", "Madhya Pradesh", 23.3341, 75.0373),
    "vidisha": ("Vidisha", "Madhya Pradesh", 23.5253, 77.8151),
    "morena": ("Morena", "Madhya Pradesh", 26.4960, 77.9994),
    "bhind": ("Bhind", "Madhya Pradesh", 26.5635, 78.7885),
    "sheopur": ("Sheopur", "Madhya Pradesh", 25.6601, 76.7001),
    # ── Maharashtra / Gujarat / Goa ──
    "pune": ("Pune", "Maharashtra", 18.5204, 73.8567),
    "nagpur": ("Nagpur", "Maharashtra", 21.1458, 79.0882),
    "nashik": ("Nashik", "Maharashtra", 19.9975, 73.7898),
    "aurangabad": ("Aurangabad", "Maharashtra", 19.8762, 75.3433),
    "solapur": ("Solapur", "Maharashtra", 17.6599, 75.9064),
    "amravati": ("Amravati", "Maharashtra", 20.9320, 77.7523),
    "kolhapur": ("Kolhapur", "Maharashtra", 16.7050, 74.2433),
    "latur": ("Latur", "Maharashtra", 18.4088, 76.5604),
    "nanded": ("Nanded", "Maharashtra", 19.1601, 77.3013),
    "ahmednagar": ("Ahmednagar", "Maharashtra", 19.0952, 74.7459),
    "sangli": ("Sangli", "Maharashtra", 16.8524, 74.5815),
    "satara": ("Satara", "Maharashtra", 17.6805, 74.0183),
    "jalgaon": ("Jalgaon", "Maharashtra", 21.0077, 75.5626),
    "nandurbar": ("Nandurbar", "Maharashtra", 21.3663, 74.2414),
    "dhule": ("Dhule", "Maharashtra", 20.9042, 74.7749),
    "wardha": ("Wardha", "Maharashtra", 20.7453, 78.6022),
    "yavatmal": ("Yavatmal", "Maharashtra", 20.3888, 78.1204),
    "akola": ("Akola", "Maharashtra", 20.7093, 77.0082),
    "buldhana": ("Buldhana", "Maharashtra", 20.5292, 76.1842),
    "surat": ("Surat", "Gujarat", 21.1702, 72.8311),
    "rajkot": ("Rajkot", "Gujarat", 22.3039, 70.8022),
    "vadodara": ("Vadodara", "Gujarat", 22.3072, 73.1812),
    "bhavnagar": ("Bhavnagar", "Gujarat", 21.7645, 72.1519),
    "anand": ("Anand", "Gujarat", 22.5645, 72.9289),
    "mehsana": ("Mehsana", "Gujarat", 23.5997, 72.3693),
    "banaskantha": ("Banaskantha", "Gujarat", 24.1726, 72.4148),
    "junagadh": ("Junagadh", "Gujarat", 21.5222, 70.4579),
    "surendranagar": ("Surendranagar", "Gujarat", 22.7277, 71.6477),
    "amreli": ("Amreli", "Gujarat", 21.6025, 71.2219),
    # ── Karnataka / Andhra / Telangana / Tamil Nadu / Kerala ──
    "mysuru": ("Mysuru", "Karnataka", 12.2958, 76.6394),
    "mysore": ("Mysuru", "Karnataka", 12.2958, 76.6394),
    "hubli": ("Hubli-Dharwad", "Karnataka", 15.3647, 75.1240),
    "dharwad": ("Dharwad", "Karnataka", 15.4589, 75.0078),
    "belgaum": ("Belagavi", "Karnataka", 15.8497, 74.4977),
    "belagavi": ("Belagavi", "Karnataka", 15.8497, 74.4977),
    "bellary": ("Ballari", "Karnataka", 15.1394, 76.9214),
    "bijapur": ("Vijayapura", "Karnataka", 16.8302, 75.7100),
    "davanagere": ("Davanagere", "Karnataka", 14.4644, 75.9218),
    "tumkur": ("Tumakuru", "Karnataka", 13.3409, 77.1010),
    "kolar": ("Kolar", "Karnataka", 13.1364, 78.1294),
    "mandya": ("Mandya", "Karnataka", 12.5218, 76.8951),
    "raichur": ("Raichur", "Karnataka", 16.2120, 77.3439),
    "gulbarga": ("Kalaburagi", "Karnataka", 17.3297, 76.8200),
    "vizag": ("Visakhapatnam", "Andhra Pradesh", 17.6868, 83.2185),
    "visakhapatnam": ("Visakhapatnam", "Andhra Pradesh", 17.6868, 83.2185),
    "guntur": ("Guntur", "Andhra Pradesh", 16.2999, 80.4570),
    "tirupati": ("Tirupati", "Andhra Pradesh", 13.6288, 79.4192),
    "nellore": ("Nellore", "Andhra Pradesh", 14.4426, 79.9865),
    "kurnool": ("Kurnool", "Andhra Pradesh", 15.8281, 78.0373),
    "warangal": ("Warangal", "Telangana", 17.9784, 79.5941),
    "nizamabad": ("Nizamabad", "Telangana", 18.6725, 78.0940),
    "karimnagar": ("Karimnagar", "Telangana", 18.4386, 79.1288),
    "khammam": ("Khammam", "Telangana", 17.2472, 80.1514),
    "nalgonda": ("Nalgonda", "Telangana", 17.0575, 79.2670),
    "coimbatore": ("Coimbatore", "Tamil Nadu", 11.0168, 76.9558),
    "madurai": ("Madurai", "Tamil Nadu", 9.9252, 78.1198),
    "tiruchirappalli": ("Trichy", "Tamil Nadu", 10.7905, 78.7047),
    "trichy": ("Trichy", "Tamil Nadu", 10.7905, 78.7047),
    "salem": ("Salem", "Tamil Nadu", 11.6643, 78.1460),
    "vellore": ("Vellore", "Tamil Nadu", 12.9165, 79.1325),
    "tirunelveli": ("Tirunelveli", "Tamil Nadu", 8.7139, 77.7567),
    "thanjavur": ("Thanjavur", "Tamil Nadu", 10.7870, 79.1378),
    "erode": ("Erode", "Tamil Nadu", 11.3410, 77.7172),
    "kochi": ("Kochi", "Kerala", 9.9312, 76.2673),
    "kozhikode": ("Kozhikode", "Kerala", 11.2588, 75.7804),
    "thrissur": ("Thrissur", "Kerala", 10.5276, 76.2144),
    "kollam": ("Kollam", "Kerala", 8.8932, 76.6141),
    "palakkad": ("Palakkad", "Kerala", 10.7867, 76.6548),
    "alappuzha": ("Alappuzha", "Kerala", 9.4981, 76.3388),
    # ── Bihar / Jharkhand / Odisha ──
    "gaya": ("Gaya", "Bihar", 24.7914, 85.0002),
    "bhagalpur": ("Bhagalpur", "Bihar", 25.2425, 86.9842),
    "muzaffarpur": ("Muzaffarpur", "Bihar", 26.1209, 85.3647),
    "darbhanga": ("Darbhanga", "Bihar", 26.1542, 85.8918),
    "purnia": ("Purnia", "Bihar", 25.7771, 87.4753),
    "motihari": ("Motihari", "Bihar", 26.6469, 84.9175),
    "chapra": ("Chapra", "Bihar", 25.7801, 84.7415),
    "begusarai": ("Begusarai", "Bihar", 25.4182, 86.1272),
    "samastipur": ("Samastipur", "Bihar", 25.8577, 85.7831),
    "siwan": ("Siwan", "Bihar", 26.2239, 84.3558),
    "dhanbad": ("Dhanbad", "Jharkhand", 23.7957, 86.4304),
    "bokaro": ("Bokaro", "Jharkhand", 23.6693, 85.9845),
    "jamshedpur": ("Jamshedpur", "Jharkhand", 22.8046, 86.2029),
    "hazaribagh": ("Hazaribagh", "Jharkhand", 23.9966, 85.3613),
    "sambalpur": ("Sambalpur", "Odisha", 21.4669, 83.9756),
    "cuttack": ("Cuttack", "Odisha", 20.4625, 85.8828),
    "rourkela": ("Rourkela", "Odisha", 22.2604, 84.8536),
    "berhampur": ("Berhampur", "Odisha", 19.3149, 84.7941),
    "balasore": ("Balasore", "Odisha", 21.4942, 86.9278),
    # ── West Bengal / NE States ──
    "asansol": ("Asansol", "West Bengal", 23.6836, 86.9692),
    "siliguri": ("Siliguri", "West Bengal", 26.7271, 88.3953),
    "durgapur": ("Durgapur", "West Bengal", 23.5204, 87.3119),
    "bardhaman": ("Bardhaman", "West Bengal", 23.2324, 87.8615),
    "murshidabad": ("Murshidabad", "West Bengal", 24.1855, 88.2697),
    "nadia": ("Nadia", "West Bengal", 23.4700, 88.5560),
    "malda": ("Malda", "West Bengal", 25.0108, 88.1415),
    "jalpaiguri": ("Jalpaiguri", "West Bengal", 26.5418, 88.7181),
    "cooch behar": ("Cooch Behar", "West Bengal", 26.3452, 89.4413),
    "dibrugarh": ("Dibrugarh", "Assam", 27.4728, 94.9120),
    "silchar": ("Silchar", "Assam", 24.8333, 92.7789),
    "tezpur": ("Tezpur", "Assam", 26.6338, 92.7957),
    "jorhat": ("Jorhat", "Assam", 26.7509, 94.2037),
    "nagaon": ("Nagaon", "Assam", 26.3468, 92.6863),
    "bongaigaon": ("Bongaigaon", "Assam", 26.4795, 90.5584),
    # ── Chhattisgarh / Uttarakhand ──
    "bilaspur": ("Bilaspur", "Chhattisgarh", 22.0796, 82.1391),
    "durg": ("Durg", "Chhattisgarh", 21.1904, 81.2849),
    "rajnandgaon": ("Rajnandgaon", "Chhattisgarh", 21.0973, 81.0301),
    "jagdalpur": ("Jagdalpur", "Chhattisgarh", 19.0864, 82.0275),
    "haridwar": ("Haridwar", "Uttarakhand", 29.9457, 78.1642),
    "rishikesh": ("Rishikesh", "Uttarakhand", 30.0869, 78.2676),
    "roorkee": ("Roorkee", "Uttarakhand", 29.8543, 77.8880),
    "haldwani": ("Haldwani", "Uttarakhand", 29.2183, 79.5130),
    "nainital": ("Nainital", "Uttarakhand", 29.3919, 79.4542),
    "almora": ("Almora", "Uttarakhand", 29.5973, 79.6593),
    "pithoragarh": ("Pithoragarh", "Uttarakhand", 29.5830, 80.2162),
}

# Stopwords to ignore when scanning a chat query for city names
_WEATHER_STOPWORDS = {
    'mausam', 'weather', 'barish', 'baarish', 'rain', 'rainfa', 'temperature',
    'tapman', 'garmi', 'sardi', 'thand', 'dhoop', 'barf', 'snow',
    'ka', 'ki', 'ke', 'hai', 'hain', 'kaisa', 'kaisi', 'kya', 'aaj', 'kal',
    'abhi', 'is', 'in', 'wahan', 'yahan', 'waha', 'wala', 'wali', 'batao',
    'bata', 'tell', 'how', 'what', 'the', 'and', 'for', 'of', 'at', 'in',
    'today', 'tomorrow', 'now', 'current', 'forecast', 'live', 'hoga',
    'hogi', 'rahega', 'rahegi', 'monsoon', 'season', 'aane', 'wala', 'bad',
}




# ── Lightweight sensor context (simulator-only for now; swap DB tier later) ──

@dataclass
class SensorContext:
    """Normalised soil/ambient readings from any source."""
    soil_moisture_pct: Optional[float] = None
    soil_temp_c:       Optional[float] = None
    air_temp_c:        Optional[float] = None   # merged from weather after fetch
    humidity_pct:      Optional[float] = None   # merged from weather after fetch
    nitrogen_kg_ha:    Optional[float] = None
    phosphorus_kg_ha:  Optional[float] = None
    potassium_kg_ha:   Optional[float] = None
    soil_ph:           Optional[float] = None
    soil_health_score: Optional[int]   = None
    soil_health_grade: str             = "—"
    moisture_status:   str             = "Unknown"
    source:            str             = "none"

    def moisture_label(self) -> str:
        if self.soil_moisture_pct is None:
            return "N/A — sensor data unavailable"
        pct = self.soil_moisture_pct
        if pct < 35:
            return f"{pct:.1f}% — ⚠️ CRITICAL: Irrigate immediately"
        if pct < 50:
            return f"{pct:.1f}% — Low: Monitor closely"
        if pct <= 65:
            return f"{pct:.1f}% — Adequate"
        return f"{pct:.1f}% — High: Skip irrigation"


@dataclass
class WeatherConstraints:
    """Gate flags derived from the weather forecast."""
    alerts_text:        str  = "None"
    forecast_3day:      str  = "N/A"
    irrigation_blocked: bool = False   # soil adequate/high OR heavy rain forecast
    spray_blocked:      bool = False   # rain >20mm or >70% prob within 48 h
    frost_warning:      bool = False   # min_temp <2°C in 3 days
    heavy_rain_48h:     bool = False

def _classify_moisture(pct: Optional[float]) -> str:
    if pct is None:
        return "Unknown"
    if pct < 35:
        return "Critical"
    if pct < 50:
        return "Low"
    if pct <= 65:
        return "Adequate"
    return "High"


def _current_season(month: int = None) -> str:
    m = month or datetime.now().month
    # Kharif: sown Jun-Jul, harvested Sep-Oct  →  Jun-Sep
    if m in (6, 7, 8, 9):
        return "Kharif (Jun-Sep)"
    # Rabi: sown Oct-Nov, harvested Mar-Apr  →  Oct-Mar
    if m in (10, 11, 12, 1, 2, 3):
        return "Rabi (Oct-Mar)"
    # Zaid: Apr-May
    return "Zaid (Apr-May)"


# ── NLP intent patterns (multi-language, v5.0) ──────────────────
# Priority order: first match wins. More specific patterns come first.
# Covers: English, Hindi, Hinglish, all 22 scheduled Indian languages.
_INTENT_PATTERNS: List[Tuple[str, List[str]]] = [

    # ── GREETING ────────────────────────────────────────────────
    (INTENT_GREETING, [
        r"\b(hi|hello|namaste|namaskar|hey|नमस्ते|नमस्कार|vanakkam|namaskaram|salam|adaab|pranam|jai\s*kisan)\b",
        r"^(helo|hii|kya\s*hal|kaisa\s*hai|kaise\s*hain|good\s*(morning|evening|afternoon|night))$",
        r"^(start|शुरू|shuru|help|madad|सहायता)\s*$",
    ]),

    # ── FOLLOW-UP ────────────────────────────────────────────────
    (INTENT_FOLLOWUP, [
        r"\b(uska|uski|iske|isi|yahi|wahi|उसका|उसकी|इसका|इसकी|यही|वही)\b",
        r"\b(aur|phir|फिर|और\s*क्या|next|then|also|more|aage)\b\s*(batao|bataiye|tell|kya|kab|kitna|batao)?",
        r"\b(iske\s*baad|इसके\s*बाद|उसके\s*बाद|uske\s*baad|और\s*बताइए|more\s*about)\b",
        r"^(okay|ok|theek\s*hai|accha|acha|hmm|haan|ha)\s*$",
    ]),

    # ── SOWING (must come before CROP_RECOMMENDATION to catch timing queries) ──
    (INTENT_SOWING, [
        # Hindi/Hinglish timing — explicitly "buwai kab" or "kab boun"
        r"\b(buwai|buai|बुवाई|बुआई)\s*(kab|कब|ka\s*samay|when|kaise|कैसे)",
        r"\b(kab|कब|when)\s*(bouwe|boun|lagaun|ugaun|daalen|लगाएं|बोएं|dalein)",
        r"\b(kab|कब|when)\s*(se|से)?\s*(buwai|buai|बुवाई|sowing|planting|रोपाई)\s*(karein|karo|shuru|start)?",
        # Seed rate — but NOT seed treatment (that goes to SEED)
        r"\b(beej|बीज|seed)\s*(rate|matra|मात्रा|amount|kitna|कितना|how\s*much|per\s*(acre|hectare|bigha|hec))\b",
        r"\b(spacing|doori|दूरी|plant\s*to\s*plant|row\s*to\s*row|katar)\s*(kitni|कितनी|how\s*much)",
        r"\b(sowing\s*(depth|time|date|month|season)|बुवाई\s*(गहराई|समय|तारीख|महीना))\b",
        r"\b(kab\s*lagaye|kab\s*boye|kab\s*daalen|kab\s*ugaye)\b",
        r"\b(rabi|kharif|zaid)\s*(mein|में)\s*(kab|when)\s*(boun|lagaun|sow|plant)\b",
        r"\b(is\s*mahine|इस\s*महीने|this\s*month)\s*(mein|में|me)\s*(kya|kaun|konsi)\s*(lagaun|ugaun|boun)",
    ]),

    # ── HARVEST ─────────────────────────────────────────────────
    (INTENT_HARVEST, [
        r"\b(harvest|katai|कटाई|katnaa|fasal\s*kat|पकना|pakna|pakne|ready\s*to\s*harvest)\b",
        r"\b(kab\s*kat|कब\s*काट|when\s*to\s*(cut|harvest|pick|reap))\b",
        r"\b(fasal|crop|पकी|paki)\s*(kab|when|pakti|पकती|ready|तैयार)\b",
        # "fasal katne ka [sahi] waqt/samay" — katna/katne (infinitive forms)
        r"\b(kat|kaatna|kaaten|katne|काटना|काटें|काटे)\s*ka\s*(sahi\s*)?(samay|waqt|time|tarika)\b",
        r"\b(kat|katne|harvest)\s*(ka\s*)?(sahi\s*)?(waqt|samay|time|kab)\b",
        r"\b(threshing|gathai|गहाई|cleaning|grading|post\s*harvest)\b",
        r"\b(yield|paidawar|उपज|production|फसल\s*की\s*उपज)\s*(kitni|कितनी|how\s*much|expected|aanee)\b",
        r"\b(maturity|परिपक्वता|pakne\s*ka\s*samay|ripening|grain\s*fill)\b",
    ]),

    # ── STORAGE / POST-HARVEST ────────────────────────────────────
    (INTENT_STORAGE, [
        r"\b(storage|bhandaran|भंडारण|store|godown|silo|sirf|cold\s*storage|warehouse)\b",
        r"\b(kitne\s*din|how\s*long|कितने\s*दिन)\s*(rakh\s*sakte|store|रख\s*सकते|preserve)\b",
        r"\b(post\s*harvest|fasal\s*ke\s*baad|कटाई\s*के\s*बाद)\s*(kya|kyaa|treatment|handling)\b",
        r"\b(namami|naami|moisture|nami)\s*(content|level)\s*(grain|storage|before)\b",
        r"\b(weevil|ghun|घुन|storage\s*pest|anaj\s*keet|grain\s*borer)\b",
        r"\b(mandi\s*kab|bechna\s*kab|sell\s*when|कब\s*बेचें|best\s*time\s*to\s*sell)\b",
        r"\b(drying|sukhaana|सुखाना|sun\s*drying|mechanical\s*dryer)\b",
    ]),

    # ── SEED ─────────────────────────────────────────────────────
    (INTENT_SEED, [
        r"\b(variety|kism|किस्म|cultivar|hybrid|HYV|improved\s*seed)\b",
        r"\b(certified\s*seed|प्रमाणित\s*बीज|NSC|foundation\s*seed|breeder\s*seed)\b",
        r"\b(konsi\s*kism|कौन\s*सी\s*किस्म|which\s*variety|best\s*variety|konsa\s*variety)\b",
        r"\b(HD\s*\d+|PBW\s*\d+|WH\s*\d+|GW\s*\d+|DBW\s*\d+|Pusa|BPT|Swarna|HDCSW)\b",  # named varieties
        r"\b(beej|बीज)\s*(kahan|कहाँ|where|kaise|milega|मिलेगा|buy|purchase|खरीदें)\b",
        # seed treatment — BEFORE sowing patterns to take priority
        r"\b(seed\s*treatment|beej\s*upchar|बीज\s*उपचार|imidacloprid|thiram|captan|carbendazim)\b",
        r"\b(beej|seed)\s*(upchar|treatment|ट्रीटमेंट|dressing|dawai|fungicide)\b",
    ]),

    # ── INSURANCE ────────────────────────────────────────────────
    (INTENT_INSURANCE, [
        r"\b(pmfby|pradhan\s*mantri\s*fasal\s*bima|fasal\s*bima|crop\s*insurance)\b",
        r"\b(insurance|bima|बीमा)\s*(claim|dawa|दावा|apply|kaise|milega|status)\b",
        r"\b(crop\s*loss|fasal\s*nuksan|फसल\s*नुकसान|natural\s*calamity)\s*(report|claim|muawaza|मुआवजा)",
        r"\b(praakritik\s*aapda|flood\s*damage|hail\s*damage|drought\s*compensation)\b",
        r"\b(muawaza|मुआवजा|compensation|fasal\s*loss|नुकसान\s*bharpai)\b",
    ]),

    # ── ORGANIC FARMING ──────────────────────────────────────────
    (INTENT_ORGANIC, [
        r"\b(organic|jaivik|जैविक)\s*(farming|kheti|krishi|khad|fertilizer)\b",
        r"\b(vermicompost|vermiculture|केंचुआ\s*खाद|kenchua\s*khad)\b",
        r"\b(jeevamrit|jivamrit|जीवामृत|panchagavya|पंचगव्य|biochar|bio\s*inputs)\b",
        r"\b(compost|FYM|farm\s*yard\s*manure|gobar\s*khad|गोबर\s*खाद)\s*(kaise|how|banaye|बनाएं)\b",
        r"\b(bio\s*pesticide|neem\s*spray|neem\s*oil|botanical\s*pesticide)\b",
        r"\b(natural\s*farming|kudrat|prakriti|zerotillage|zero\s*budget)\b",
        r"\b(Trichoderma|Pseudomonas|Rhizobium|PSB|azotobacter|VAM)\b",
    ]),

    # ── PROFIT / COST CALCULATION ────────────────────────────────
    (INTENT_PROFIT_CALC, [
        r"\b(profit|labh|लाभ|fayda|kitna\s*kamaun|income|aamdani|आमदनी)\s*(per|per\s*bigha|per\s*hectare|per\s*acre)\b",
        r"\b(lagat|lागत|input\s*cost|cost\s*of\s*cultivation|kheti\s*ki\s*lagat)\b",
        r"\b(kitna\s*kamaunga|kitni\s*kamayi|kamayi\s*kitni|return\s*on|ROI)\b",
        r"\b(comparison|tulna|तुलना)\s*(fasal|crop|of)\s*(wheat|rice|mustard|any\s*crop)\b",
    ]),

    # ── CROP RECOMMENDATION ──────────────────────────────────────
    (INTENT_CROP_RECOMMENDATION, [
        r"\bwhich\s+crop",
        r"\bbest\s+crop",
        r"\bwhat\s+(crop|to\s+grow|to\s+sow|to\s+plant)",
        r"\bcrop\s*(suggest|recommend|advice|choice|select)",
        r"\bwhat\s+should\s+i\s+(grow|plant|sow|cultivate)",
        r"\b(crop|crops|fasal|fasalein|phasal)\s+(for|in|ke\s+liye)\s+(this|is|current|season|mausam)\b",
        r"\b(kya|kaun\s*si|kaunsi|konsi)\s+(fasal|crop|phasal|kheti)\s*(lagaun|ugaun|booun|sow|plant|grow|karein)?",
        r"\b(fasal|phasal|crop)\s+(suggest|recommend|batao|bataiye|kaun|kya|kaunsi|konsi|सुझाव|बताओ|चुनें)",
        r"\b(kya|kaun)\s*(lagaun|ugaun|boun|lagaye|ugaye|boye|lagana|ugana|bona)\b",
        r"\b(kya|kaun)\s+\w+\s*(lagaun|ugaun|boun|lagaye|lagana|bona|ugaun)\b",
        r"\b(kharif|rabi|zaid|खरीफ|रबी|जायद)\s*(mein|में|ke\s+liye|के\s+लिए)?\s*(kya|क्या|kaun|konsi|kaunsi)\s*(lagaun|ugaun|boun|lagaye|fasal|crop)?",
        r"\b(is\s*season|is\s*mausam|iss\s*saal)\s*(kya|kaun|konsi|क्या|कौन)",
        r"\b(इस\s*मौसम|इस\s*सीजन)\s*(में|मे)\s*(क्या|कौन)",
        r"\b(कौन\s*सी|konsi|kaunsi)\s*(fasal|फसल|crop|खेती|kheti)",
        r"\b(फसल|fasal)\s*(का|के|की)\s*(सुझाव|चुनाव|select|suggest|recommend)",
        r"\bkaunsi\s+fasal\b",
        r"\bkonsi\s+fasal\b",
        r"\b(mere\s*khet|meri\s*zameen|apni\s*kheti)\s*(ke\s*liye|mein)\s*(kya|konsi)\b",
        # Regional
        r"\b(ফসল|పంట|பயிர்|ਫ਼ਸਲ|ক্ষেত)\b.*\b(পরামর্শ|సూచన|பரிந்துரை|ਸੁਝਾਅ)\b",
        r"\b(kontha|entha|yavanu)\s+(bele|bethanu|balu)\b",
        r"\b(ethu|enna)\s+(paya|payan|vithaykuka)\b",
    ]),

    # ── MARKET PRICE ─────────────────────────────────────────────
    (INTENT_MARKET_PRICE, [
        r"\b(msp|mandi|market\s*price|bhav|भाव|मंडी|daam|aaj\s*ka\s*bhav|today.*price)\b",
        r"\b(price|कीमत|दाम|भाव|rate)\s*(of|का|की|ke|for)\b",
        # Standalone rate/daam/bhav/price as final word or followed by question
        r"\b(rate|daam|भाव|bhav|price|keemat)\s*(kya|kitna|batao|bataiye|hai|hain)?\s*\??$",
        r"\b(गेहूँ|गेहु|धान|सरसों|प्याज|आलू|टमाटर|कपास|मक्का|सोयाबीन|wheat|rice|mustard|onion|potato|tomato|cotton|maize|soybean|garlic|chana|arhar|moong)\s*(ka\s*bhav|ka\s*rate|ka\s*daam|price|भाव|दाम|rate|मूल्य|कीमत)",
        r"\b(today|aaj|आज|kal|कल|abhi)\s*(ka|का|ki|की)\s*(bhav|भाव|price|rate|दाम)",
        r"\b(bechna|sell|bikri|बेचना|बिक्री)\s*(kahan|kahaan|कहाँ|kab|कब|kitne\s*mein|kahan\s*bechun)",
        r"\b(enam|agmarknet|apmc|नाफेड|nafed|मंडी\s*भाव)\b",
        r"\b(minimum\s*support|न्यूनतम\s*समर्थन|msp\s*kya\s*hai|msp\s*kitna|msp\s*2024|msp\s*2025|msp\s*2026)\b",
        r"\b(trend|badhega|बढ़ेगा|girega|गिरेगा|market\s*outlook|price\s*forecast)\b",
        r"\b(fasal\s*bechne|sell\s*crop|mandi\s*mein|apmc\s*mein)\s*(kab|kaise)\b",
    ]),

    # ── WEATHER ──────────────────────────────────────────────────
    (INTENT_WEATHER, [
        # Core weather terms — 'baad' REMOVED (it means "after" not flood)
        r"\b(weather|mausam|मौसम|barish|बारिश|rain|forecast|flood|बाढ़|drought|sukha|सूखा|temperature|tapman|तापमान|imd|meghdoot)\b",
        # Regional weather terms
        r"(हवामान|পাউস|আবহাওয়া|বৃষ্টি|వాతావరణం|వర్షం|வானிலை|மழை|વરસાદ|ಹವಾಮಾನ|ಮಳೆ|കാലാവസ്ഥ|മഴ|ਮੌਸਮ|ਮੀਂਹ|ਪਾਣਿਪਾਗ|ବର୍ଷା|বতৰ|বৰষুণ)",
        r"\b(aaj|kal|आज|कल|is\s*hafte|next\s*week|parson)\s*(ka\s*)?(mausam|weather|barish|बारिश)",
        r"\b(garmi|sardi|baarish|तूफान|ओलावृष्टि|olavrishti|hail|storm|cyclone|andhi)\b",
        r"\b(monsoon|mansoon|मानसून)\s*(kab|आएगा|aayega|this\s*year|2024|2025|2026)\b",
        # Seasonal / agricultural weather
        r"\b(is\s*saal|this\s*year)\s*(barish|rain|monsoon|weather|मौसम)\s*(kaisa|kaisi|kaisa\s*rahega)\b",
        r"\b(barish\s*kab\s*hogi|rain\s*forecast|varsha\s*poorvaanuman)\b",
    ]),

    # ── GOVERNMENT SCHEMES ───────────────────────────────────────
    (INTENT_GOVERNMENT_SCHEME, [
        r"\b(pm[- ]?kisan|pmfby|kcc|kusum|enam|yojana|योजना|subsidy|सब्सिडी|अनुदान|fasal\s*bima|kisan\s*credit|soil\s*health\s*card|pm\s*kusum)\b",
        r"\b(sarkaar|sarkaari|government|सरकार|सरकारी|kendriya|rajya)\s*(yojana|योजना|scheme|help|sahayata|paisa|madad)\b",
        r"\b(paise|पैसे|rupaye|amount|installment|kist)\s*(kab\s*aayega|kab\s*milega|कब\s*आएगा|status|check|track)\b",
        r"\b(apply|avedan|आवेदन|register|पंजीयन|form|फॉर्म)\s*(kaise|कैसे|how|karna|karein|bharna)\b",
        r"\b(loan|rin|ऋण|karz|कर्ज|nabard|mudra|kcc\s*limit|kisan\s*credit)\s*(kaise|कैसे|milega|lena|interest)",
        r"\b(kisan\s*samman|pm\s*kisan\s*status|installment\s*check|6000|2000)\b",
        r"\b(rajya\s*sarkar|state\s*govt)\s*(yojana|scheme)\s*(UP|MP|Rajasthan|Punjab|Haryana|Maharashtra|Bihar)\b",
    ]),

    # ── PEST / DISEASE ───────────────────────────────────────────
    (INTENT_PEST_DISEASE, [
        # Core
        r"\b(pest|keet|कीट|rog|रोग|blight|blast|disease|worm|caterpillar|sundi|सुंडी|wilting|fungus|fungal|spray|davai|दवाई|pesticide|insecticide|fungicide|neem)\b",
        # Symptom-based
        r"\b(patti|पत्ती|leaf|leaves|fruit|फल|root|जड़|fasal|crop|stem|tana|तना)\s*(mein|में|pe|पर|ki|का|की)\s*(problem|kuch|नुकसान|damage|pili|पीली|sukh|सूख|kala|काला|safed|सफेद|laal|red|curl|mur|hole)\b",
        r"\b(kyon|क्यों|why)\s*(sukh|mur|pil|gir|सूख|मुरझा|पीली|झड|curl|fall|rot|sada)\b",
        # Named pests
        r"\b(sundi|afid|aphid|mite|thrips|whitefly|सफेद\s*मक्खी|माहू|टिड्डा|locust|stem\s*borer|bollworm|armyworm|jassid|planthopper)\b",
        # Yellow leaf / yellowing (very common Hinglish symptom query) — broadened
        r"\b(pattian|patti|leaf|पत्तियां|पत्ती)\s*(pili|peli|पीली|yellow|pale|lal|red|kali|brown|safed|white)\b",
        r"\b(fasal|crop|plant|paudha)\s*(pili|peli|pilI|पीली|yellow|sukh|wilt|mar|gal|rot)\s*(rahi|raha|gayi|gaya|ho\s*rahi|pad\s*rahi)?\b",
        r"\b(pila\s*pad|pili\s*ho|yellow\s*ho|peela\s*ho|pattiyaan\s*pili)\b",
        # "wheat/crop pili" without explicit verb — catch direct colour + crop combos
        r"\b(wheat|gehu|rice|dhan|maize|makka|cotton|kapas|mustard|sarson|soybean)\s*(pili|yellow|sukh|wilt|kali|red|lal)\b",
        r"\b(pili|yellow|pale|sukh|wilt)\s*(ho\s*rahi|pad\s*rahi|ja\s*rahi|ho\s*gai)\b",
        # Spray timing
        r"\b(spray|davai|kab|kitni|which)\s*(karo|karein|maro|lagao|डालें|छिड़काव)\b",
        r"\b(fungicide|insecticide|herbicide|khardavai|weedicide|dawaai)\s*(konsi|kaunsi|which|best)\b",
        # Crop-specific diseases
        r"\b(wheat\s*(rust|karwa|blast|bunt|aphid|yellow)|gehu\s*(keet|rog))\b",
        r"\b(paddy\s*(blast|sheath|bug|BPH|BLB)|dhan\s*(rog|jhonka))\b",
        r"\b(cotton\s*(bollworm|pink\s*worm|mealybug|white\s*fly)|kapas\s*(keet|rog))\b",
    ]),

    # ── SOIL ─────────────────────────────────────────────────────
    (INTENT_SOIL, [
        r"\b(soil|mitti|मिट्टी|ph|organic\s*carbon|soil\s*health|soil\s*card|urvarak|fertility|nitrogen|phosphorus|potassium|vermicompost|compost)\b",
        r"\b(mitti|माटी|जमीन|bhumi|भूमि)\s*(ki\s*janch|test|जांच|health|ph|ka\s*ph|type|prakar|badlao)\b",
        r"\b(mrida|मृदा)\s*(swasthya|health|परीक्षण|card|testing)\b",
        r"\b(sankhyam|NPK|n\.p\.k|macronutrient|micronutrient)\b",
        r"\b(soil\s*testing|mitti\s*janch|SHC|Soil\s*Health\s*Card)\s*(kahan|kaise|centre)\b",
        r"\b(kali\s*mitti|red\s*soil|sandy\s*soil|clay|domat|alluvial|black\s*soil|lal\s*mitti)\b",
        r"\b(pH|acidity|alkalinity|saline|khara|क्षारीय|अम्लीय|tizaab|lime|chuna)\b",
    ]),

    # ── IRRIGATION ───────────────────────────────────────────────
    # NOTE: 'sinchai' intentionally NOT in WEATHER patterns
    # NOTE: irrigation patterns appear BEFORE weather in the list so
    #       "barish ke baad sinchai" routes correctly
    (INTENT_IRRIGATION, [
        r"\b(irrigation|sinchai|सिंचाई|drip|sprinkler|borewell|tubewell|pump|AWD|solar\s*pump|kusum)\b",
        r"\b(pani|पानी|water)\s*(kab|kitna|कब|कितना|when|how\s*much|dene\s*ka\s*samay|schedule|de|dene|lagao)\b",
        r"\b(sinchai|सिंचाई|irrigat)\s*(kab|kaise|कब|कैसे|when|schedule|time|kitni|times)\b",
        # "kitne din baad pani de" patterns
        r"\b(kitten|kitne|kitna|how\s*many)\s*(din|days|dino|hafte)\s*(baad|mein|after|me|pehle)?\s*(pani|water|sinchai|irrigation|de|dene)\b",
        r"\b(pani\s*(kab|kitna)\s*(dun|dena|dete|denge|de)|when\s*to\s*(irrigate|water))\b",
        # Sowing/irrigation timing — belongs here not weather
        r"\b(बुवाई|सिंचाई|sinchai|buwai|kheti)\s*(kab|कब|ka\s*samay|when)",
        # Water saving, drought tolerance
        r"\b(pani\s*bachao|water\s*saving|moisture\s*conservation|mulching|mulch)\b",
        r"\b(flood\s*irrigation|furrow|drip\s*tape|micro\s*irrigation|NWDPRA)\b",
        # "barish ke baad sinchai" — after rain, should I irrigate?
        r"\b(barish|baarish|rain|varsha)\s*(ke\s*baad|after|ke\s*bad)\s*(sinchai|pani|irrigat|water)\b",
        r"\b(sinchai|pani|irrigat)\s*(barish|baarish|rain)\s*(ke\s*baad|after)\b",
    ]),

    # ── FERTILIZER ───────────────────────────────────────────────
    (INTENT_FERTILIZER, [
        r"\b(urea|dap|npk|mkp|mop|fertilizer|khad|खाद|urvarak|उर्वरक|zinc|sulfur|boron|magnesium|vermicompost|FYM|neem\s*coated)\b",
        # "kitni khad" or "khad kitni" — quantity question
        r"\b(kitni|कितनी|how\s*much|kitna)\s*(khad|urea|dap|fertilizer|nitrogen|npk|potash)\b",
        # Schedule-only patterns WITHOUT "kab" alone (to avoid grabbing das-based queries)
        r"\b(khad|उर्वरक|fertilizer)\s*(ka\s*schedule|schedule|split|dose|apply|daalein|डालें)\b",
        r"\b(top\s*dress|side\s*dress|basal\s*dose|split\s*dose|foliar\s*spray|पत्तियों\s*पर\s*छिड़काव)\b",
        r"\b(N|P|K|nitrogen|phosphorus|potassium)\s*(deficiency|kami|कमी|excess|symptom|ki\s*kami)\b",
        r"\b(soil\s*health|NPK\s*ratio|recommended\s*dose|package\s*of\s*practices|POP)\b",
        r"\b(nacl|sulphur|zinc\s*sulphate|gypsum|lime|chuna|ammonium)\s*(kitna|kitni|apply|dalo)\b",
        # "X din baad khad" — DAS-based fertilizer query
        r"\b\d+\s*(din|days)\s*(baad|after|mein)?\s*(khad|urea|dap|fertilizer|उर्वरक|top\s*dress)\b",
    ]),

]


class ChatIntelligenceService:
    """
    Context-aware, multi-turn, multi-language agricultural chatbot.
    Uses Gemini AI when configured, falls back to rich rule-based engine.

    v4.0 changes:
    - Structured grounded prompt: IoT sensor block + weather constraints + RAG snippets
    - Fixed follow-up intent: re-classifies prior user turn instead of reading missing key
    - Fixed season overlap: Oct/Nov now correctly Rabi
    - Fixed Gemini key validation: catches all placeholder patterns
    - Fixed null-coordinate guard: no silent TypeError on missing GPS
    - Concurrent data fetch: weather + market in parallel
    """

    # ── Legacy system prompt (kept for reference / fallback) ─────
    _SYSTEM_PROMPT_LEGACY = """You are KrishiMitra AI — a trusted, intelligent digital assistant for Indian farmers.
You are like an expert agronomist, economist, and government scheme advisor combined.

STRICT RULES (never break):
1. Use ONLY facts from the "Official live data" section. Never invent prices, MSP, weather, or schemes.
2. If data is missing, say so clearly and point to official sources (Agmarknet, IMD, PM-Kisan, ICAR).
3. Distinguish MSP (government minimum) from mandi modal price (actual market).
4. Prefer organic / IPM approaches before chemicals. If chemicals are needed, cite label dose.
5. Match the user's language EXACTLY — detect from their writing and respond in same script.
6. Be conversational, warm, practical. Use short paragraphs, bullet points, emojis where natural.
7. Reference the farmer's actual GPS location, current weather, and season in every crop/weather answer.
8. For follow-up questions, refer back to what was discussed earlier in the conversation.
9. Format key numbers (MSP, prices, temperatures) prominently with ₹ symbol.
10. End with one actionable next step and relevant helpline number when appropriate.

Conversation style:
- If this is a follow-up ("uska", "aur batao", "phir kya"), build on the previous context.
- Acknowledge the farmer's situation empathetically before giving advice.
- Give specific, actionable answers — not generic platitudes.
- For pest/disease: recommend the KrishiRaksha photo upload feature for accurate ML diagnosis.

Never claim you inspected a photo. Never make up mandi names or today's prices."""

    # ── New structured grounded system prompt ─────────────────────
    # Uses Python single-brace {variable} format slots filled by _render_grounded_prompt().
    SYSTEM_PROMPT_TEMPLATE = (
        "You are KrishiMitra AI — an elite Smart Agricultural Advisory AI for Indian farmers. "
        "Your mission: SAFE, HIGHLY LOCALIZED, DATA-DRIVEN agronomy advice by synthesising "
        "live weather, official government guidelines, and real-time mandi prices.\n\n"

        "### OPERATIONAL FRAMEWORK\n"
        "1. PERCEIVE: Read [LIVE SENSOR DATA] first — flag any critical alerts.\n"
        "2. GROUND: Cross-reference with [GOVERNMENT & WEATHER DATA]. Advice MUST comply "
        "with official data, planting calendars, and active weather threats.\n"
        "3. DECIDE & ACT: Provide a tailored, step-by-step action plan.\n\n"

        "### CRITICAL RULES\n"
        "- DATA TRUTHFULNESS: NEVER recommend irrigation if moisture is Adequate or High. "
        "NEVER ignore an active weather alert.\n"
        "- SAFETY FIRST: For any chemical treatment, rely ONLY on the government snippet below. "
        "If the snippet says 'No specific advisory found', do NOT guess — defer to the local "
        "KVK extension officer or 1800-180-1551.\n"
        "- LANGUAGE: {lang_instruction}\n"
        "- TONALITY: Empathetic expert agronomist. Bullet points for action steps. "
        "Emojis where natural. Address farmer as 'किसान भाई' when responding in Hindi.\n\n"

        "---\n\n"
        "[LIVE SENSOR DATA] (source: {sensor_source})\n"
        "Soil Moisture  : {soil_moisture_label}\n"
        "Soil Temp      : {soil_temp_c}\n"
        "Ambient Temp   : {air_temp_c}\n"
        "Humidity       : {humidity_pct}\n"
        "N (Nitrogen)   : {nitrogen_kg_ha}  ({nitrogen_status})\n"
        "P (Phosphorus) : {phosphorus_kg_ha}  ({phosphorus_status})\n"
        "K (Potassium)  : {potassium_kg_ha}  ({potassium_status})\n"
        "Soil pH        : {soil_ph}  ({ph_status})\n"
        "Soil Health    : Score {soil_health_score}/100 — Grade {soil_health_grade}\n\n"

        "---\n\n"
        "[GOVERNMENT & WEATHER DATA]\n"
        "3-Day Forecast      : {forecast_3day}\n"
        "Severe Weather Alert: {active_weather_warnings}\n"
        "Irrigation Blocked  : {irrigation_blocked}\n"
        "Spray/Fert Blocked  : {spray_blocked}\n"
        "Frost Warning       : {frost_warning}\n\n"
        "Government/ICAR Advisory (use ONLY these facts for treatment recommendations):\n"
        "\"\"\"{government_rag_snippets}\"\"\"\n\n"
        "Current Market Price: {current_market_price}\n"
        "Season              : {season}\n"
        "Location            : {location_label}\n\n"

        "---\n\n"
        "[CONVERSATION HISTORY]\n"
        "{history_block}\n\n"

        "---\n\n"
        "[FARMER'S CURRENT QUERY]\n"
        "{farmer_query}\n\n"

        "---\n\n"
        "### RESPONSE EVALUATION (do silently before writing)\n"
        "1. Does the query CONFLICT with sensor/weather data? "
        "(e.g. asking to irrigate when moisture is Adequate → refuse + explain)\n"
        "2. Is there an active WEATHER ALERT? If yes, mention it FIRST.\n"
        "3. Is any chemical recommendation backed by the government snippet? "
        "If snippet is missing/generic, defer to KVK. Never invent a product or dose.\n\n"
        "Now write your response."
    )

    # ─────────────────────────────────────────────────────────────

    def answer(
        self,
        query: str,
        ctx: LocationContext,
        language: str = "hi",
        history: Optional[List[Dict[str, Any]]] = None,
        farmer_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point. Supports multi-turn conversation via `history`.

        history format (last N messages):
          [{"role": "user", "content": "..."},
           {"role": "assistant", "content": "...", "intent": "market_price"}]
        The "intent" key on assistant turns is optional but improves follow-up resolution.
        """
        query = (query or "").strip()
        lang  = normalise_language_code(language)

        if language == "auto" and ctx.state:
            lang = get_language_for_state(ctx.state)

        if not query:
            return {
                "response": self._empty_response(lang),
                "intent": INTENT_GENERAL,
                "sources": [],
                "crop_suggestions": [],
                "language": lang,
            }

        # ── NLP: intent + entity extraction ───────────────────────
        intent, crops_mentioned = self.classify_query(query)

        # Multi-turn: inherit crops from recent history when none in current query
        if not crops_mentioned and history:
            for msg in reversed((history or [])[-6:]):
                past = msg.get("content") or msg.get("message_content") or ""
                if past:
                    past_crops = self._detect_crops(past)
                    if past_crops:
                        crops_mentioned = past_crops
                        break

        # ── Follow-up intent resolution (BUG FIX) ─────────────────
        # The history list only has {role, content} — "intent" is never present
        # unless the client explicitly stores it back. We use two strategies:
        # 1. Read embedded intent from last assistant turn (if client stores it)
        # 2. Re-classify the most recent prior user message
        if intent == INTENT_FOLLOWUP and history:
            resolved = False
            # Strategy 1: embedded intent key
            for msg in reversed(history):
                if msg.get("role") == "assistant" and msg.get("intent"):
                    intent = msg["intent"]
                    resolved = True
                    break
            # Strategy 2: re-classify prior user message
            if not resolved:
                prior_user_msgs = [m for m in history if m.get("role") == "user"]
                if prior_user_msgs:
                    prior_q = prior_user_msgs[-1].get("content", "")
                    prior_intent, prior_crops = self.classify_query(prior_q)
                    if prior_intent not in (INTENT_FOLLOWUP, INTENT_GENERAL):
                        intent = prior_intent
                        if not crops_mentioned and prior_crops:
                            crops_mentioned = prior_crops

        # ── Named-location override ───────────────────────────────────────────
        # E.g. "rampur ka mausam" or "rampur crop suggestion"
        # Overrides location context if a known city/district is mentioned in the query.
        if intent in (INTENT_WEATHER, INTENT_CROP_RECOMMENDATION, INTENT_MARKET_PRICE, INTENT_GOVERNMENT_SCHEME):
            _named_ctx = self._extract_query_location(query)
            if _named_ctx is not None:
                logger.info(
                    "Named-location override: '%s' → %s (%.4f, %.4f)",
                    query[:60], _named_ctx.display_name,
                    _named_ctx.latitude, _named_ctx.longitude,
                )
                ctx = _named_ctx

        # ── Concurrent data fetch ─────────────────────────────────
        weather_data: Dict[str, Any] = {}
        prices_data:  Dict[str, Any] = {}
        sc = SensorContext()

        def _fetch_weather():
            return weather_service.get_weather(
                ctx.query_label, ctx.latitude, ctx.longitude, lang=lang
            )

        def _fetch_prices():
            crop_filter = crops_mentioned[0]["name"] if crops_mentioned else None
            return market_service.get_prices(
                ctx.query_label,
                lat=ctx.latitude,
                lon=ctx.longitude,
                state=ctx.state or None,
                crop=crop_filter,
            )

        def _fetch_iot():
            return self._resolve_sensor_context(ctx)

        if ctx.latitude is None or ctx.longitude is None:
            logger.warning(
                "Location context missing coordinates for %s — skipping weather/IoT fetch",
                ctx.display_name,
            )
        else:
            # FIX 4: use the module-level pool (no thread create/destroy overhead)
            futures = {
                _DATA_FETCH_POOL.submit(_fetch_weather): "weather",
                _DATA_FETCH_POOL.submit(_fetch_prices):  "prices",
                _DATA_FETCH_POOL.submit(_fetch_iot):     "iot",
            }
            try:
                for fut in as_completed(futures, timeout=6):
                    key = futures[fut]
                    try:
                        result = fut.result()
                        if key == "weather":
                            weather_data = result or {}
                        elif key == "prices":
                            prices_data = result or {}
                        elif key == "iot":
                            sc = result
                    except Exception as exc:
                        logger.warning("Fetch failed for %s: %s", key, exc)
            except FuturesTimeout:
                # Collect any already-completed futures before the timeout hit
                for fut, key in futures.items():
                    if fut.done():
                        try:
                            result = fut.result()
                            if key == "weather" and not weather_data:
                                weather_data = result or {}
                            elif key == "prices" and not prices_data:
                                prices_data = result or {}
                            elif key == "iot" and sc.source == "none":
                                sc = result
                        except Exception:
                            pass
                logger.warning(
                    "Concurrent fetch timed out after 6s for %s — using partial data",
                    ctx.display_name,
                )

        # Merge ambient readings from weather into sensor context
        cur = weather_data.get("current") or {}
        if sc.air_temp_c is None:
            sc.air_temp_c = cur.get("temperature")
        if sc.humidity_pct is None:
            sc.humidity_pct = cur.get("humidity")

        # ── Derive weather constraints ────────────────────────────
        wc = self._derive_weather_constraints(weather_data, sc)

        # ── Gov RAG snippets + market price string ────────────────
        rag        = self._fetch_gov_rag_snippets(query, intent, crops_mentioned)
        market_str = self._build_market_price_str(prices_data, crops_mentioned)

        # ── Build legacy context_block (for rule-based fallback + crop recs) ─
        context_block, sources = self._build_official_context(
            ctx, query, intent, crops_mentioned, lang=lang,
            _weather=weather_data, _prices=prices_data,
        )

        # ── History block (for Gemini prompt) ────────────────────
        history_block = "(new conversation)"
        if history:
            lines = []
            for msg in (history or [])[-8:]:
                role    = "Farmer" if msg.get("role") == "user" else "KrishiMitra"
                content = (msg.get("content") or msg.get("message_content") or "").strip()
                if content:
                    lines.append(f"{role}: {content}")
            if lines:
                history_block = "\n".join(lines)

        # Inject farmer profile into history block so AI personalises response
        if farmer_profile:
            profile_lines = []
            if farmer_profile.get("crop_history"):
                profile_lines.append(f"Past crops: {farmer_profile['crop_history']}")
            if farmer_profile.get("current_crop"):
                profile_lines.append(f"Current crop: {farmer_profile['current_crop']}")
            if farmer_profile.get("farm_size_bigha"):
                profile_lines.append(f"Farm size: {farmer_profile['farm_size_bigha']} bigha")
            if farmer_profile.get("soil_ph"):
                profile_lines.append(f"Soil pH: {farmer_profile['soil_ph']}")
            if farmer_profile.get("irrigation_type"):
                profile_lines.append(f"Irrigation: {farmer_profile['irrigation_type']}")
            if farmer_profile.get("has_pm_kisan"):
                profile_lines.append("Enrolled: PM-Kisan")
            if farmer_profile.get("sensor_reading"):
                s = farmer_profile["sensor_reading"]
                parts = []
                if s.get("nitrogen_kg_ha") is not None:
                    parts.append(f"N:{s['nitrogen_kg_ha']} kg/ha")
                if s.get("phosphorus_kg_ha") is not None:
                    parts.append(f"P:{s['phosphorus_kg_ha']} kg/ha")
                if s.get("potassium_kg_ha") is not None:
                    parts.append(f"K:{s['potassium_kg_ha']} kg/ha")
                if s.get("ph") is not None:
                    parts.append(f"pH:{s['ph']}")
                if s.get("ec_ds_m") is not None:
                    parts.append(f"EC:{s['ec_ds_m']} dS/m")
                if s.get("moisture_pct") is not None:
                    parts.append(f"Moisture:{s['moisture_pct']}%")
                if s.get("soil_temp_c") is not None:
                    parts.append(f"SoilTemp:{s['soil_temp_c']}°C")
                if s.get("organic_carbon") is not None:
                    parts.append(f"OC:{s['organic_carbon']}%")
                if parts:
                    profile_lines.append("Soil Sensors: " + ", ".join(parts))
            if profile_lines:
                profile_str = "[FARMER PROFILE] " + " | ".join(profile_lines)
                history_block = profile_str + "\n\n" + history_block

        now    = datetime.now()
        season = _current_season(now.month)

        # ── Generate response ─────────────────────────────────────
        # Priority chain:
        #   1. Gemini API (cloud, best quality)
        #   2. Qwen 2.5 7B + RAG (local, zero cost — Phase 1 server on port 8001)
        #   3. Rule-based fallback (always available offline)
        has_gemini    = _is_valid_gemini_key(gemini_service.api_key)
        response_text: Optional[str] = None
        data_source   = "KrishiMitra Advisory Engine"   # safe default — overwritten on success

        if has_gemini:
            try:
                rendered = self._render_grounded_prompt(
                    query=query, ctx=ctx, sc=sc, wc=wc, rag=rag,
                    market_price_str=market_str, history_block=history_block,
                    lang=lang, season=season,
                )
                response_text = gemini_service.generate(
                    prompt=rendered,
                    system_prompt="",  # all context already in rendered prompt
                    max_tokens=1600,
                    user_query=query,
                    temperature=0.3,
                )
                if response_text:
                    data_source = "Gemini AI + Official gov APIs"
                else:
                    logger.warning("Gemini returned empty — trying Qwen+RAG")
            except Exception as exc:
                logger.warning("Gemini failed: %s — trying Qwen+RAG", exc)

        # Tier 2: Qwen 2.5 7B + RAG (runs when Gemini absent or returned empty)
        if not response_text:
            response_text = self._qwen_rag_answer(
                query=query,
                ctx=ctx,
                lang=lang,
                history=history,
                sc=sc,
                wc=wc,
                market_str=market_str,
                farmer_profile=farmer_profile,
            )
            if response_text:
                data_source = "Qwen 2.5 7B + RAG (local)"

        # Tier 3: Rule-based fallback (always available, no external dependencies)
        if not response_text:
            response_text = self._smart_rule_response(
                query, intent, crops_mentioned, ctx, context_block, lang, history,
                sc=sc, wc=wc,
            )
            # data_source already set to default "KrishiMitra Advisory Engine"

        crop_suggestions = self._crop_suggestions_for_intent(
            ctx, intent, crops_mentioned, lang=lang
        )

        return {
            "response":        response_text,
            "intent":          intent,
            "sources":         list(dict.fromkeys(sources)),
            "crops_detected":  [c["name"] for c in crops_mentioned],
            "crop_suggestions": crop_suggestions,
            "language":        lang,
            "data_source":     data_source,
            "timestamp":       now.isoformat(),
            "location_context": ctx.to_dict() if hasattr(ctx, "to_dict") else None,
        }

    # ── Tier 2: Qwen 2.5 7B + RAG (local Phase 1 server) ────────

    def _qwen_rag_answer(
        self,
        query: str,
        ctx: LocationContext,
        lang: str,
        history: Optional[List[Dict[str, Any]]],
        sc: SensorContext,
        wc: WeatherConstraints,
        market_str: str,
        farmer_profile: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Call the Phase 1 FastAPI server (http://127.0.0.1:8001/chat).
        Returns response text if the server is up and responds, None otherwise.
        All failures are silent — callers fall back to rule-based.

        Bug fixes applied:
        - Bug 2/3: json, urllib, re imported at module level; _HINDI_ENGLISH_MAP
          is a module-level constant — no per-call reconstruction.
        - Bug 5: query is augmented here with _augment_hindi_query() before
          sending to Phase 1. Phase 1's retriever.py also augments, but that's
          a server-side concern on its own query; we send the augmented string
          so the server receives better input even if its augmentation is off.
          To avoid double tokens we send the ORIGINAL query to Phase 1 in the
          `query` field and let Phase 1's retriever handle augmentation there.
          This is the cleanest separation: Django enriches context, Phase 1
          enriches the embedding lookup.
        """
        PHASE1_URL = "http://127.0.0.1:8001/chat"

        # Build sensor_context dict
        sensor_ctx: Optional[Dict[str, Any]] = None
        if sc.source != "none":
            sensor_ctx = {
                "moisture_pct":     sc.soil_moisture_pct,
                "moisture_status":  sc.moisture_status,
                "soil_temp_c":      sc.soil_temp_c,
                "ph":               sc.soil_ph,
                "nitrogen_kg_ha":   sc.nitrogen_kg_ha,
                "phosphorus_kg_ha": sc.phosphorus_kg_ha,
                "potassium_kg_ha":  sc.potassium_kg_ha,
                "temp_c":           sc.air_temp_c,
                "humidity_pct":     sc.humidity_pct,
                "source":           sc.source,
            }

        # Detect crop from conversation history
        crop_hint: Optional[str] = None
        if history:
            for msg in reversed(history[-6:]):
                detected = self._detect_crops(msg.get("content", ""))
                if detected:
                    crop_hint = detected[0]["name"]
                    break

        # Sanitise history for Phase 1
        clean_history = [
            {"role": m.get("role", "user"), "content": m.get("content", "")}
            for m in (history or [])[-8:]
            if m.get("content")
        ]

        payload = json.dumps({
            "query":          query,           # Phase 1 retriever augments internally
            "language":       lang,
            "location":       ctx.display_name,
            "latitude":       ctx.latitude,
            "longitude":      ctx.longitude,
            "crop":           crop_hint or (farmer_profile.get("current_crop") if farmer_profile else None),
            "season":         _current_season(),
            "history":        clean_history,
            "sensor_context": sensor_ctx,
            "farmer_profile": farmer_profile,  # NEW: personalisation context
            "stream":         False,
        }, ensure_ascii=False).encode("utf-8")

        try:
            req = urllib.request.Request(
                PHASE1_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = (data.get("response") or "").strip()
                if text:
                    logger.info(
                        "Qwen+RAG: '%s...' — %d chunks from %s",
                        query[:40],
                        data.get("rag_chunks", 0),
                        data.get("rag_sources", []),
                    )
                    return text
                # Phase 1 returned 200 but empty response — treat as unavailable
                logger.warning("Qwen+RAG returned empty response for: %s...", query[:40])
                return None
        except urllib.error.URLError:
            # Server not running — expected when Phase 1 is offline
            logger.debug("Phase 1 server offline — using rule-based fallback")
            return None
        except Exception as exc:
            logger.warning("Qwen+RAG unexpected error: %s", exc)
            return None

    # ── Named-location extraction ──────────────────────────────────────────────

    def _extract_query_location(self, query: str) -> Optional[LocationContext]:
        """
        Scan a chat query for a known Indian city/district name and return a
        LocationContext centred on that city.

        Algorithm:
        1. Lower-case and tokenise the query.
        2. Skip tokens in _WEATHER_STOPWORDS (common Hindi/English non-place words).
        3. Try multi-word matches first (e.g. 'rae bareli', 'greater noida'),
           then single-word matches.
        4. Return on first hit; return None if nothing matches.

        Zero external API calls — pure dict lookup, sub-millisecond.
        """
        q_lower = query.lower().strip()
        # Remove punctuation
        q_clean = re.sub(r'[^\w\s]', ' ', q_lower)

        # ── Try multi-word city names first (longest match wins) ──────────────
        for city_key, (display, state, lat, lon) in _INDIAN_CITY_CATALOG.items():
            if ' ' in city_key and city_key in q_clean:
                return LocationContext(
                    latitude=lat,
                    longitude=lon,
                    display_name=display,
                    city=display,
                    state=state,
                    country="India",
                    source="query_city_extraction",
                    confidence=0.85,
                )

        # ── Single-word token scan ─────────────────────────────────────────────
        tokens = [t for t in q_clean.split() if t not in _WEATHER_STOPWORDS and len(t) >= 4]
        for token in tokens:
            if token in _INDIAN_CITY_CATALOG:
                display, state, lat, lon = _INDIAN_CITY_CATALOG[token]
                return LocationContext(
                    latitude=lat,
                    longitude=lon,
                    display_name=display,
                    city=display,
                    state=state,
                    country="India",
                    source="query_city_extraction",
                    confidence=0.85,
                )

        return None

    # ── Sensor context: simulator only (no real hardware yet) ────

    def _resolve_sensor_context(self, ctx: LocationContext) -> SensorContext:
        """Fetch simulated IoT readings from BlockchainIoTSimulator.
        When real sensors are connected, add DB lookup here as Tier 1."""
        try:
            sim = iot_blockchain.get_iot_sensor_data(ctx.query_label)
            readings = sim.get("readings", {})
            npk      = readings.get("npk", {})
            health   = sim.get("soil_health_score", {})
            pct      = readings.get("soil_moisture_pct")
            sc = SensorContext(
                soil_moisture_pct=pct,
                soil_temp_c=readings.get("soil_temperature_c"),
                nitrogen_kg_ha=npk.get("nitrogen_kg_ha"),
                phosphorus_kg_ha=npk.get("phosphorus_kg_ha"),
                potassium_kg_ha=npk.get("potassium_kg_ha"),
                soil_ph=readings.get("soil_ph"),
                soil_health_score=health.get("score") if isinstance(health, dict) else None,
                soil_health_grade=health.get("grade", "—") if isinstance(health, dict) else "—",
                source="simulated",
            )
            sc.moisture_status = _classify_moisture(pct)
            return sc
        except Exception as exc:
            logger.warning("IoT simulator fetch failed: %s", exc)
            return SensorContext(source="none")

    # ── Weather constraints ───────────────────────────────────────

    def _derive_weather_constraints(
        self,
        weather: Dict[str, Any],
        sc: SensorContext,
    ) -> WeatherConstraints:
        wc = WeatherConstraints()

        alerts = weather.get("farming_alerts") or []
        wc.alerts_text = " | ".join(str(a) for a in alerts[:3]) if alerts else "None"

        forecast = (
            weather.get("forecast_7day")
            or weather.get("forecast_7_days")
            or []
        )

        if forecast:
            lines = []
            for day in forecast[:3]:
                lines.append(
                    f"{day.get('date')}: max {day.get('max_temp')}°C, "
                    f"rain {day.get('rainfall_mm', 0)}mm "
                    f"({day.get('rain_probability', 0)}% prob)"
                )
            wc.forecast_3day = "; ".join(lines)
        else:
            wc.forecast_3day = "Forecast unavailable — check mausam.imd.gov.in"

        # Spray block: heavy rain within 48 h
        for day in forecast[:2]:
            if (day.get("rainfall_mm") or 0) > 20 or (day.get("rain_probability") or 0) > 70:
                wc.spray_blocked   = True
                wc.heavy_rain_48h  = True
                break

        # Frost warning: min_temp <2°C in 3 days
        for day in forecast[:3]:
            if day.get("min_temp") is not None and day["min_temp"] < 2:
                wc.frost_warning = True
                break

        # Irrigation block: adequate/high moisture OR heavy rain forecast
        if sc.moisture_status in ("Adequate", "High") or wc.heavy_rain_48h:
            wc.irrigation_blocked = True

        return wc

    # ── Government RAG snippets ───────────────────────────────────

    def _fetch_gov_rag_snippets(
        self,
        query: str,
        intent: str,
        crops: List[Dict[str, Any]],
    ) -> str:
        snippets: List[str] = []

        if intent == INTENT_PEST_DISEASE:
            snippets.append(
                "ICAR IPM Package of Practices: Prefer neem oil (5ml/L) as first-line "
                "treatment. Chemical control: Imidacloprid 17.8SL @ 0.25ml/L for sucking "
                "pests; Mancozeb 75WP @ 2.5g/L for fungal diseases. Source: ICAR/PPQS."
            )

        if intent == INTENT_FERTILIZER:
            snippets.append(
                "ICAR recommends soil testing before fertiliser application. General NPK: "
                "120:60:40 kg/ha for wheat; 100:50:50 for rice. Use neem-coated urea (NCU) "
                "to cut volatilisation loss by 10-15%. Source: ICAR/FAI."
            )

        for crop in crops[:2]:
            try:
                from .comprehensive_crop_database import comprehensive_crop_database
                info = comprehensive_crop_database.get_crop_info(crop["id"])
                if info:
                    if intent == INTENT_PEST_DISEASE:
                        note = (info.get("pest_management") or "")[:200]
                    elif intent == INTENT_FERTILIZER:
                        note = (info.get("fertiliser_schedule") or "")[:200]
                    else:
                        note = ""
                    if note:
                        snippets.append(f"{crop['name'].title()} — {note}")
            except Exception:
                pass

        if not snippets:
            return (
                "No specific advisory found for this query. "
                "Please consult your local KVK extension officer or call 1800-180-1551."
            )

        return (" | ".join(snippets))[:500]

    # ── Market price slot string ──────────────────────────────────

    def _build_market_price_str(
        self,
        prices: Dict[str, Any],
        crops: List[Dict[str, Any]],
    ) -> str:
        if not prices.get("is_live"):
            parts = []
            for crop in crops[:3]:
                msp = MSP_2024_25.get(crop["id"])
                if msp:
                    parts.append(f"{crop['name'].title()}: ₹{msp}/q (MSP 2024-25)")
            base = "; ".join(parts) if parts else "N/A"
            return f"{base} — live mandi data unavailable, check agmarknet.gov.in"

        top = [c for c in (prices.get("top_crops") or []) if c.get("is_live")]
        if crops:
            crop_ids = {c["id"] for c in crops}
            # BUG 1 FIX: normalize() returns None for regional-language crop names
            # (e.g. Agmarknet "गेहूँ"). Double call + subscript on None → TypeError.
            # Single call + .get() is safe and avoids re-evaluating the catalog lookup.
            matched = []
            for c in top:
                norm = crop_catalog.normalize(str(c.get("crop_name", "")))
                if norm and norm.get("id") in crop_ids:
                    matched.append(c)
            top = matched + [c for c in top if c not in matched]

        lines = []
        for c in top[:4]:
            modal  = c.get("modal_price")
            msp    = c.get("msp")
            mandi  = c.get("mandi_name", "N/A")
            profit = (
                f"+{c['profit_vs_msp']}% above MSP"
                if c.get("profit_vs_msp", 0) > 0
                else "below MSP"
            )
            lines.append(f"{c.get('crop_name')} ₹{modal}/q (MSP ₹{msp}) @ {mandi} — {profit}")
        return "; ".join(lines) if lines else "No live price rows today"

    # ── Render grounded prompt ────────────────────────────────────

    def _render_grounded_prompt(
        self,
        query: str,
        ctx: LocationContext,
        sc: SensorContext,
        wc: WeatherConstraints,
        rag: str,
        market_price_str: str,
        history_block: str,
        lang: str,
        season: str,
    ) -> str:
        def _fmt(val, fallback: str = "N/A") -> str:
            return str(val) if val is not None else fallback

        def _npk_status(val: Optional[float], low: float, high: float) -> str:
            if val is None:
                return "unknown"
            if val < low:
                return "⚠️ Low"
            return "✅ Adequate"

        def _ph_status(ph: Optional[float]) -> str:
            if ph is None:
                return "unknown"
            if ph < 5.5:
                return "⚠️ Very Acidic"
            if ph < 6.0:
                return "🟡 Acidic"
            if ph <= 7.5:
                return "✅ Optimal"
            if ph <= 8.0:
                return "🟡 Alkaline"
            return "⚠️ Very Alkaline"

        loc = ctx.display_name
        if ctx.state and ctx.state not in loc:
            loc = f"{ctx.display_name}, {ctx.state}"

        try:
            return self.SYSTEM_PROMPT_TEMPLATE.format(
                lang_instruction        = get_gemini_language_instruction(lang),
                sensor_source           = sc.source,
                soil_moisture_label     = sc.moisture_label(),
                soil_temp_c             = _fmt(sc.soil_temp_c, "N/A") + ("°C" if sc.soil_temp_c is not None else ""),
                air_temp_c              = _fmt(sc.air_temp_c, "N/A") + ("°C" if sc.air_temp_c is not None else ""),
                humidity_pct            = _fmt(sc.humidity_pct, "N/A") + ("%" if sc.humidity_pct is not None else ""),
                nitrogen_kg_ha          = _fmt(sc.nitrogen_kg_ha) + (" kg/ha" if sc.nitrogen_kg_ha is not None else ""),
                nitrogen_status         = _npk_status(sc.nitrogen_kg_ha, 150, 250),
                phosphorus_kg_ha        = _fmt(sc.phosphorus_kg_ha) + (" kg/ha" if sc.phosphorus_kg_ha is not None else ""),
                phosphorus_status       = _npk_status(sc.phosphorus_kg_ha, 10, 25),
                potassium_kg_ha         = _fmt(sc.potassium_kg_ha) + (" kg/ha" if sc.potassium_kg_ha is not None else ""),
                potassium_status        = _npk_status(sc.potassium_kg_ha, 100, 200),
                soil_ph                 = _fmt(sc.soil_ph),
                ph_status               = _ph_status(sc.soil_ph),
                soil_health_score       = sc.soil_health_score if sc.soil_health_score is not None else "—",
                soil_health_grade       = sc.soil_health_grade,
                forecast_3day           = wc.forecast_3day,
                active_weather_warnings = wc.alerts_text,
                irrigation_blocked      = "YES ⚠️" if wc.irrigation_blocked else "No",
                spray_blocked           = "YES ⚠️ (rain forecast within 48h)" if wc.spray_blocked else "No",
                frost_warning           = "YES ❄️" if wc.frost_warning else "No",
                government_rag_snippets = rag,
                current_market_price    = market_price_str,
                season                  = season,
                location_label          = loc,
                history_block           = history_block,
                farmer_query            = query,
            )
        except KeyError as exc:
            logger.warning("Prompt template render failed (%s) — falling back to legacy format", exc)
            return (
                f"Farmer location: {loc}\nSeason: {season}\n"
                f"Language instruction: {get_gemini_language_instruction(lang)}\n\n"
                f"Official live data:\n{rag}\nMarket: {market_price_str}\n\n"
                f"Farmer query: {query}"
            )

    # ── NLP: Intent classification ────────────────────────────────

    # ── Hinglish / colloquial normaliser ─────────────────────────
    # Maps common Hinglish typos / shortenings → canonical words so the
    # intent regex can match them without needing hundreds of variants.
    # Also covers common Marathi/Bengali/Punjabi farming words.
    _HINGLISH_NORM: Dict[str, str] = {
        # Irrigation variants
        "kitten": "kitne", "kittan": "kitne", "kitan": "kitne",
        "pani de": "pani dena", "paani": "pani",
        # Sowing variants
        "buwai": "buwai", "buayi": "buwai", "bunai": "buwai",
        "lagenga": "lagaun", "lagaunga": "lagaun", "lagana": "lagaun",
        "ugana": "ugaun", "bona": "boun",
        # Disease / pest variants
        "keede": "keet", "keeda": "keet", "kida": "keet",
        "pattiyaan": "patti", "patiyan": "patti",
        "peeli": "pili", "peli": "pili",
        "sukh rahi": "sukh raha",
        # Market variants
        "bhaw": "bhav", "bhaav": "bhav",
        "dam": "daam", "daaam": "daam",
        # Weather variants
        "baarish": "barish", "varsha": "barish",
        "taapmaan": "tapman",
        # Fertiliser variants
        "khaad": "khad", "urvarak": "urvarak",
        "diaap": "dap",
        # General farming
        "kheiti": "kheti", "fashal": "fasal", "phasal": "fasal",
        # Numbers/quantities
        "beegha": "bigha", "bheega": "bigha",
        "kuntal": "quintal",
        # ── Marathi farming terms → Hindi equivalents ──────────────
        "bharipak": "katai harvest",       # full maturity / harvest time
        "pivna": "pani dena irrigation",   # to irrigate (Marathi)
        "keva": "kab when",                # when (Marathi)
        "dyave": "dena give",              # to give (Marathi)
        "gahu": "gehu wheat",              # wheat (Marathi)
        "bhuimug": "moongfali groundnut",  # groundnut (Marathi)
        "kanda": "pyaz onion",             # onion (Marathi)
        "batata": "aloo potato",           # potato (Marathi)
        "kapus": "kapas cotton",           # cotton (Marathi)
        "soyabin": "soybean",
        "tur": "arhar pigeonpea",
        "harbhara": "chana gram",
        "paus": "barish rain",             # rain (Marathi)
        "havaman": "mausam weather",       # weather (Marathi)
        # ── Bengali farming terms ───────────────────────────────────
        "dhaan": "dhan rice",
        "aloo": "aloo potato",
        "borsha": "barish rain",
        "jomin": "zameen land soil",
        # ── Punjabi farming terms ───────────────────────────────────
        "gehun": "gehu wheat",
        "sarson": "sarson mustard",
        "makki": "makka maize",
        "mausam": "mausam weather",
        "paani": "pani water",
        # ── Tamil/Telugu farming terms ──────────────────────────────
        "neer": "pani water",              # water (Tamil)
        "mazhai": "barish rain",           # rain (Tamil)
        "nilam": "mitti soil",             # soil (Tamil)
    }

    def _normalise_hinglish(self, text: str) -> str:
        """Replace common Hinglish variations with canonical forms so regexes match."""
        t = text.lower()
        for wrong, right in self._HINGLISH_NORM.items():
            t = t.replace(wrong, right)
        return t

    def classify_query(self, query: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Multi-language intent classification with entity extraction.

        Steps:
        1. Normalise Hinglish typos/variations
        2. Pre-check high-specificity composite patterns (avoid ordering conflicts)
        3. Run pattern matching (first match wins, ordered by specificity)
        4. Context-aware overrides (e.g. crop mention → CROP_INFO fallback)
        """
        raw_q = query.lower().strip()
        q = self._normalise_hinglish(raw_q)
        crops_mentioned = self._detect_crops(query)

        # ── Step 2: High-specificity pre-checks ──────────────────
        # These prevent intent misrouting when two keywords from different
        # intents appear in the same sentence.

        # "barish ke baad [X me] sinchai" → IRRIGATION (not WEATHER)
        # Allow up to ~5 words between "barish ke baad" and "sinchai/pani"
        if re.search(
            r"\b(barish|baarish|rain|varsha)\s*(ke\s*baad|after|ke\s*bad)\b.{0,40}\b(sinchai|pani|irrigat|water)\b",
            q, re.IGNORECASE
        ) or re.search(
            r"\b(sinchai|pani|irrigat)\b.{0,30}\b(barish|rain)\s*(ke\s*baad|after)\b",
            q, re.IGNORECASE
        ):
            return INTENT_IRRIGATION, crops_mentioned

        # "drip/sprinkler + subsidy/scheme" → IRRIGATION (not GOVT SCHEME)
        # But NOT if it's asking about applying for a specific named scheme like PM-KUSUM
        if re.search(r"\b(drip|sprinkler|micro\s*irrigation|borewell)\b", q, re.IGNORECASE) and \
           re.search(r"\b(subsidy|scheme|yojana|milegi)\b", q, re.IGNORECASE) and \
           not re.search(r"\b(apply|avedan|register|pm[- ]?kusum|kusum|form)\b", q, re.IGNORECASE):
            return INTENT_IRRIGATION, crops_mentioned

        # "X din baad khad/urea/fertilizer" → FERTILIZER (not SOWING)
        if re.search(r"\b\d+\s*(din|days)\s*(baad|after)?\s*(khad|urea|dap|fertilizer|उर्वरक)", q, re.IGNORECASE):
            return INTENT_FERTILIZER, crops_mentioned

        # "aaj ka <crop> ka rate/bhav/daam" → MARKET_PRICE
        if re.search(
            r"\b(aaj|today|abhi)\s*ka\s*\w+\s*ka\s*(rate|bhav|daam|price)\b",
            q, re.IGNORECASE
        ):
            return INTENT_MARKET_PRICE, crops_mentioned

        for intent, patterns in _INTENT_PATTERNS:
            for pat in patterns:
                try:
                    if re.search(pat, q, re.IGNORECASE | re.UNICODE):
                        # Don't fire GREETING for long messages
                        if intent == INTENT_GREETING and len(q) > 50:
                            continue
                        return intent, crops_mentioned
                except re.error:
                    continue

        # Context-aware fallbacks ─────────────────────────────────
        if crops_mentioned:
            q_words = set(q.split())
            if q_words & {"kab", "when", "time", "samay", "date", "mahina", "month"}:
                return INTENT_SOWING, crops_mentioned
            if q_words & {"kat", "katai", "harvest", "ready", "pak", "paka"}:
                return INTENT_HARVEST, crops_mentioned
            if q_words & {"rakh", "store", "storage", "bhandar", "godown"}:
                return INTENT_STORAGE, crops_mentioned
            if q_words & {"labh", "profit", "kamayi", "lagat", "cost", "income"}:
                return INTENT_PROFIT_CALC, crops_mentioned
            return INTENT_CROP_INFO, crops_mentioned

        return INTENT_GENERAL, crops_mentioned

    def _detect_crops(self, text: str) -> List[Dict[str, Any]]:
        """Extract crop entities using the crop catalog."""
        found: List[Dict[str, Any]] = []
        seen = set()
        tokens = re.split(r"[\s,?.!;|]+", text.lower())
        for length in (3, 2, 1):
            for i in range(len(tokens) - length + 1):
                phrase = " ".join(tokens[i:i + length])
                if len(phrase) < 2:
                    continue
                norm = crop_catalog.normalize(phrase)
                if norm and norm["id"] not in seen:
                    seen.add(norm["id"])
                    found.append(norm)
        if not found:
            for r in crop_catalog.search(text, limit=3):
                if r["id"] not in seen:
                    seen.add(r["id"])
                    found.append(r)
        return found[:5]

    def _extract_query_entities(self, query: str) -> Dict[str, Any]:
        """
        Extract structured entities from free-form farming queries.

        Returns dict with:
          das       – days after sowing (int), e.g. "40 din baad" → 40
          quantity  – numeric quantity mentioned, e.g. "50 kg" → (50, 'kg')
          area      – land area mentioned, e.g. "2 bigha" → (2, 'bigha')
          stage     – crop growth stage keywords detected
          time_ref  – temporal reference ('morning', 'evening', 'now', 'next_week')
          action    – primary verb/action detected
        """
        q = query.lower()
        entities: Dict[str, Any] = {}

        # Days after sowing / emergence
        das_match = re.search(
            r"(\d+)\s*(?:din|days?|dino)\s*(?:baad|after|mein|me|pehle|before)",
            q
        )
        if das_match:
            entities["das"] = int(das_match.group(1))

        # Quantity with unit
        qty_match = re.search(
            r"(\d+(?:\.\d+)?)\s*(kg|gram|gm|ml|litre|liter|quintal|kuntal|ton|tonne|bag|bora)",
            q
        )
        if qty_match:
            entities["quantity"] = (float(qty_match.group(1)), qty_match.group(2))

        # Land area
        area_match = re.search(
            r"(\d+(?:\.\d+)?)\s*(bigha|beegha|hectare|hec|ha|acre|katta|biswa)",
            q
        )
        if area_match:
            entities["area"] = (float(area_match.group(1)), area_match.group(2))

        # Growth stage keywords
        stage_keywords = {
            "germination": ["germination", "ankur", "अंकुर", "jamav", "ug"],
            "vegetative":  ["vegetative", "jad", "patti", "growth", "tillering", "tiller"],
            "flowering":   ["flower", "phool", "फूल", "booting", "heading"],
            "grain_fill":  ["grain", "dana", "दाना", "fill", "maturity", "pak"],
            "harvest":     ["harvest", "katai", "कटाई", "ready", "taiyar"],
        }
        for stage, kws in stage_keywords.items():
            if any(kw in q for kw in kws):
                entities["stage"] = stage
                break

        # Time reference
        if any(w in q for w in ("subah", "morning", "sveere", "6 baje", "7 baje")):
            entities["time_ref"] = "morning"
        elif any(w in q for w in ("shaam", "evening", "4 baje", "5 baje")):
            entities["time_ref"] = "evening"
        elif any(w in q for w in ("abhi", "now", "turant", "immediately")):
            entities["time_ref"] = "now"
        elif any(w in q for w in ("kal", "tomorrow", "parson", "next week", "agle hafte")):
            entities["time_ref"] = "soon"

        # Primary action
        action_map = {
            "irrigate": ["pani de", "sinchai", "irrigat", "water"],
            "spray":    ["spray", "chidkav", "chidakav", "chidkaav"],
            "apply":    ["daalein", "daalo", "apply", "dena", "lagao"],
            "sow":      ["boun", "lagaun", "buwai", "sow", "plant"],
            "harvest":  ["kat", "harvest", "katai"],
            "sell":     ["becho", "sell", "bechna"],
        }
        for action, kws in action_map.items():
            if any(kw in q for kw in kws):
                entities["action"] = action
                break

        return entities

    # ── Live data context builder ─────────────────────────────────

    def _build_official_context(
        self,
        ctx: LocationContext,
        query: str,
        intent: str,
        crops: List[Dict[str, Any]],
        lang: str = "hi",
        _weather: Optional[Dict[str, Any]] = None,
        _prices: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[str]]:
        """Fetch and format live official data for this farmer's location.

        _weather and _prices can be passed in from the concurrent fetch in
        answer() to avoid duplicate network calls.
        """
        lines: List[str] = []
        sources: List[str] = []

        # 1. Live weather (always)
        if ctx.latitude is None or ctx.longitude is None:
            logger.warning(
                "Missing coordinates for %s — skipping weather fetch",
                ctx.display_name,
            )
            lines.append("[WEATHER] Location coordinates unavailable — check mausam.imd.gov.in")
        else:
            try:
                weather = _weather if _weather else weather_service.get_weather(
                    ctx.query_label, ctx.latitude, ctx.longitude, lang=lang
                )
                cur = weather.get("current") or {}
                temp     = cur.get("temperature")
                humidity = cur.get("humidity")
                wind     = cur.get("wind_speed")
                rain     = cur.get("rainfall_mm", 0)
                cond     = cur.get("condition_local") or cur.get("condition", "")
                et0      = cur.get("et0_mm")

                lines.append(
                    f"[LIVE WEATHER] {ctx.display_name}: {temp}°C, {cond}, "
                    f"humidity {humidity}%, wind {wind} km/h, rain {rain}mm/hr"
                    + (f", ET0 {et0}mm/day" if et0 else "")
                )

                if weather.get("farming_advice"):
                    lines.append(f"[FARMING ADVICE] {weather['farming_advice']}")

                forecast = (
                    weather.get("forecast_7day")
                    or weather.get("forecast_7_days")
                    or weather.get("forecast")
                    or []
                )
                if forecast:
                    lines.append("[7-DAY FORECAST]")
                    for day in forecast[:5]:
                        wb  = day.get("water_balance_mm")
                        irr = " (IRRIGATE)" if day.get("irrigation_needed") else ""
                        lines.append(
                            f"  {day.get('date')}: max {day.get('max_temp')}°C, "
                            f"rain {day.get('rainfall_mm', 0)}mm, "
                            f"prob {day.get('rain_probability', 0)}%"
                            + (f", WB {wb}mm{irr}" if wb is not None else "")
                        )

                alerts = weather.get("farming_alerts") or []
                for alert in alerts[:3]:
                    lines.append(f"[ALERT] {str(alert)}")

                sources.append(weather.get("data_source", "Open-Meteo"))
            except Exception as exc:
                logger.warning(
                    "Weather fetch failed in chat context (lat=%s, lon=%s): %s",
                    ctx.latitude, ctx.longitude, exc,
                )
                lines.append("[WEATHER] Temporarily unavailable — check mausam.imd.gov.in")

        # 2. Market prices
        try:
            prices = _prices if _prices else market_service.get_prices(
                ctx.query_label,
                lat=ctx.latitude,
                lon=ctx.longitude,
                state=ctx.state or None,
            )
            sources.append(prices.get("data_source", "Agmarknet/data.gov.in"))

            if intent in (INTENT_MARKET_PRICE, INTENT_GENERAL, INTENT_CROP_INFO, INTENT_CROP_RECOMMENDATION) or crops:
                if prices.get("is_live"):
                    top = [c for c in (prices.get("top_crops") or []) if c.get("is_live")]
                    if crops:
                        crop_ids = {c["id"] for c in crops}
                        matched = [
                            c for c in top
                            if crop_catalog.normalize(str(c.get("crop_name", "")))
                            and crop_catalog.normalize(str(c.get("crop_name", "")))["id"] in crop_ids
                        ]
                        top = matched + [c for c in top if c not in matched]
                    lines.append(f"[LIVE MANDI PRICES near {ctx.display_name}] (Rs/quintal):")
                    for c in top[:8]:
                        profit = c.get("profit_vs_msp")
                        profit_str = f", +{profit}% vs MSP" if profit and profit > 0 else ""
                        lines.append(
                            f"  {c.get('crop_name')} ({c.get('crop_name_hindi', '')}): "
                            f"modal Rs{c.get('modal_price')}, MSP Rs{c.get('msp')}, "
                            f"mandi: {c.get('mandi_name', 'N/A')}{profit_str}"
                        )
                else:
                    lines.append("[MANDI PRICES] Live feed unavailable. Set DATA_GOV_IN_API_KEY for live data.")
                    lines.append("  Register free at data.gov.in/user/register")
        except Exception as e:
            logger.warning("Market fetch failed in chat context: %s", e)

        # 3. Crop recommendations (for crop/general queries)
        if intent in (INTENT_CROP_RECOMMENDATION, INTENT_GENERAL, INTENT_CROP_INFO) or \
           any(w in query.lower() for w in ("crop", "fasal", "फसल", "खेती", "ugaun", "lagaun", "boun")):
            try:
                rec = crop_recommendation_engine.recommend_from_context(ctx, language=lang)
                sources.append(rec.get("data_source", "Crop engine"))
                season_lbl = rec.get("season", "")
                zone = rec.get("agro_zone") or rec.get("region") or ""
                lines.append(f"[CROP RECOMMENDATIONS for {ctx.display_name}] season: {season_lbl}, zone: {zone}")
                for r in (rec.get("recommendations") or [])[:5]:
                    local = r.get("crop_name_local") or r.get("crop_name_hindi") or r.get("crop_name", "")
                    lines.append(
                        f"  {r.get('crop_name')} ({local}): "
                        f"suitability {r.get('suitability_score')}%, "
                        f"profit Rs{r.get('profit_per_hectare', 0):,}/ha, "
                        f"MSP Rs{r.get('msp_per_quintal', 0)}/q, "
                        f"reason: {r.get('reason_hindi') or r.get('reason', '')}"
                    )
                ws = rec.get("weather_snapshot") or {}
                if ws.get("temperature"):
                    lines.append(f"  [Live weather used in scoring: {ws.get('temperature')}°C, {ws.get('condition', '')}]")
            except Exception as e:
                logger.warning("Crop rec failed in chat context: %s", e)

        # 4. Government schemes
        if intent == INTENT_GOVERNMENT_SCHEME or \
           any(w in query.lower() for w in ("yojana", "scheme", "kisan", "योजना", "subsidy", "sarkaar", "apply", "register")):
            try:
                schemes = schemes_service.get_schemes(ctx.query_label)
                sources.append("Government schemes (MoAFW)")
                lines.append(f"[GOVERNMENT SCHEMES for farmers]")
                for s in (schemes.get("schemes") or [])[:6]:
                    lines.append(
                        f"  {s.get('name')} ({s.get('name_hindi', '')}): "
                        f"{(s.get('benefit') or '')[:120]} | "
                        f"Apply: {s.get('website', '')}"
                    )
            except Exception as e:
                logger.warning("Schemes fetch failed in chat context: %s", e)

        # 5. MSP for mentioned crops
        for crop in crops[:3]:
            msp = crop.get("msp") or MSP_2024_25.get(crop["id"])
            if msp:
                lines.append(f"[MSP 2024-25] {crop['name']}: Rs{msp}/quintal (Cabinet approved)")

        # 6. Pest/disease guidance
        if intent == INTENT_PEST_DISEASE:
            lines.append(
                "[PEST/DISEASE] Upload leaf photo in KrishiRaksha for ML diagnosis. "
                "General IPM: neem oil 5ml/L first; ICAR package of practices; "
                "1800-180-1551 for expert advice."
            )
            sources.append("ICAR IPM guidelines")

        return "\n".join(lines), list(dict.fromkeys(sources))

    # ── Intelligent rule-based response (no Gemini needed) ───────

    def _smart_rule_response(
        self,
        query: str,
        intent: str,
        crops: List[Dict[str, Any]],
        ctx: LocationContext,
        context_block: str,
        lang: str = "hi",
        history: Optional[List[Dict[str, Any]]] = None,
        *,
        sc: Optional[SensorContext] = None,
        wc: Optional[WeatherConstraints] = None,
    ) -> str:
        """
        Intelligent, context-aware responses built from live data.
        Personalised to location, weather, season, and conversation history.
        Includes evaluation checks: weather alerts, moisture vs. irrigation,
        spray block before rain.
        """
        sc  = sc  or SensorContext()
        wc  = wc  or WeatherConstraints()
        loc = ctx.display_name
        if ctx.state and ctx.state not in loc:
            loc = f"{ctx.display_name}, {ctx.state}"

        # ── Extract structured entities from the query ───────────
        qe = self._extract_query_entities(query)

        # Parse live values from context_block
        def _extract(pattern: str, default: str = "—") -> str:
            m = re.search(pattern, context_block)
            return m.group(1) if m else default

        temp     = _extract(r"([\d.]+)°C")
        humidity = _extract(r"humidity ([\d]+)%")
        cond     = _extract(r"°C, ([^,\n]+),")
        farming_advice = ""
        fa_line = next((l for l in context_block.splitlines() if "[FARMING ADVICE]" in l), "")
        if fa_line:
            farming_advice = fa_line.replace("[FARMING ADVICE]", "").strip()

        season = _current_season()
        now    = datetime.now()

        # ── Evaluation Check 1: active weather alerts (prefix all responses) ─
        alert_prefix = ""
        if wc.alerts_text and wc.alerts_text != "None":
            alert_prefix = (
                f"⚠️ **कृषि चेतावनी:** {wc.alerts_text}\n\n"
                if lang == "hi" else
                f"⚠️ **Farming Alert:** {wc.alerts_text}\n\n"
            )

        # ── Evaluation Check 2: irrigation vs. moisture ───────────
        if intent == INTENT_IRRIGATION:
            if sc.moisture_status in ("Adequate", "High") and sc.soil_moisture_pct is not None:
                msg = (
                    f"💧 **सिंचाई की जरूरत नहीं।**\n\n"
                    f"आपके खेत की मिट्टी में नमी **{sc.soil_moisture_pct:.1f}%** है "
                    f"(स्तर: {sc.moisture_status}) — अभी सिंचाई न करें, इससे जलभराव होगा।\n\n"
                    f"अगली सिंचाई तब करें जब नमी 45% से नीचे आए।\n\n"
                    f"📞 PM-KUSUM: 1800-180-3333"
                    if lang == "hi" else
                    f"Soil moisture is **{sc.soil_moisture_pct:.1f}%** "
                    f"({sc.moisture_status}) — irrigation is NOT needed right now. "
                    f"Irrigate when moisture drops below 45%.\n\n"
                    f"📞 PM-KUSUM: 1800-180-3333"
                )
                return alert_prefix + msg
            if sc.moisture_status == "Critical" and sc.soil_moisture_pct is not None:
                msg = (
                    f"🚨 **तुरंत सिंचाई करें!**\n\n"
                    f"मिट्टी की नमी **{sc.soil_moisture_pct:.1f}%** है (Critical)। "
                    f"फसल पर सूखे का खतरा है। तुरंत 40-50mm सिंचाई करें।\n\n"
                    f"📞 PM-KUSUM: 1800-180-3333"
                    if lang == "hi" else
                    f"🚨 **Irrigate immediately!** Soil moisture is "
                    f"**{sc.soil_moisture_pct:.1f}%** (Critical). "
                    f"Apply 40-50mm water now to prevent crop stress.\n\n"
                    f"📞 PM-KUSUM: 1800-180-3333"
                )
                return alert_prefix + msg

        # ── Evaluation Check 3: spray/fertiliser before forecasted rain ───
        spray_warning = ""
        if intent in (INTENT_FERTILIZER, INTENT_PEST_DISEASE) and wc.spray_blocked:
            spray_warning = (
                f"⚠️ **स्प्रे/खाद अभी न डालें** — अगले 48 घंटों में भारी बारिश की संभावना है। "
                f"बारिश के बाद ही करें।\n\n"
                if lang == "hi" else
                f"⚠️ **Postpone spray/fertiliser** — heavy rain forecast within 48 hours. "
                f"Apply after the rain.\n\n"
            )

        # ── GREETING ──────────────────────────────────────────────
        if intent == INTENT_GREETING:
            msgs = {
                "hi": (
                    f"नमस्ते किसान भाई! 🌾 मैं **KrishiMitra AI** हूँ — आपका स्मार्ट कृषि सहायक।\n\n"
                    f"📍 आपकी लोकेशन: **{loc}**\n"
                    f"🌡️ अभी का मौसम: **{temp}°C**, {cond}\n"
                    f"🗓️ सीजन: **{season}**\n"
                    f"💡 {farming_advice or 'सामान्य कृषि कार्य जारी रखें'}\n\n"
                    f"मैं इन सभी विषयों में मदद कर सकता हूँ:\n"
                    f"🌱 फसल सुझाव — कौन सी फसल उगाऊं?\n"
                    f"💰 मंडी भाव — आज का गेहूँ/धान का भाव?\n"
                    f"🌦️ मौसम — सिंचाई कब करूँ?\n"
                    f"🏛️ योजनाएं — PM-Kisan, PMFBY, KCC\n"
                    f"🐛 कीट-रोग — फसल में रोग क्यों?\n"
                    f"🧪 खाद — कितनी Urea डालूँ?\n\n"
                    f"💬 Hindi, English या Hinglish — किसी भी भाषा में पूछें!\n"
                    f"📞 Kisan Call Centre: **1800-180-1551** (Free, 24x7)"
                ),
                "en": (
                    f"Hello Farmer! 🌾 I'm **KrishiMitra AI** — your intelligent farming assistant.\n\n"
                    f"📍 Your location: **{loc}**\n"
                    f"🌡️ Current weather: **{temp}°C**, {cond}\n"
                    f"🗓️ Season: **{season}**\n"
                    f"💡 {farming_advice or 'Suitable for normal farming activities'}\n\n"
                    f"I can help with:\n"
                    f"🌱 Crop recommendations for your location\n"
                    f"💰 Live mandi prices (Agmarknet/eNAM)\n"
                    f"🌦️ 16-day weather forecast + irrigation schedule\n"
                    f"🏛️ Government schemes (PM-Kisan, PMFBY, KCC)\n"
                    f"🐛 Pest & disease identification\n"
                    f"🧪 Fertiliser recommendations\n\n"
                    f"Ask in any Indian language or English!\n"
                    f"📞 Kisan Helpline: **1800-180-1551** (Free, 24x7)"
                ),
            }
            return alert_prefix + msgs.get(lang, msgs["en"])

        # ── WEATHER ──────────────────────────────────────────────
        if intent == INTENT_WEATHER:
            forecast_lines = [l for l in context_block.splitlines() if l.strip().startswith("202")]
            alerts = [l for l in context_block.splitlines() if "[ALERT]" in l]

            resp = {
                "hi": (
                    f"🌦️ **{loc}** का लाइव मौसम ({now.strftime('%d %B %Y')}):\n\n"
                    f"🌡️ तापमान: **{temp}°C** | 💧 नमी: **{humidity}%** | 🌬️ {cond}\n"
                    f"{'🚨 ' + farming_advice if farming_advice else '✅ सामान्य कृषि कार्य जारी रखें'}\n\n"
                ),
                "en": (
                    f"🌦️ **{loc}** Live Weather ({now.strftime('%d %B %Y')}):\n\n"
                    f"🌡️ Temp: **{temp}°C** | 💧 Humidity: **{humidity}%** | {cond}\n"
                    f"{'🚨 ' + farming_advice if farming_advice else '✅ Normal farming conditions'}\n\n"
                ),
            }.get(lang, f"Weather {loc}: {temp}°C, {cond}. {farming_advice}\n\n")

            if alerts:
                resp += ("⚠️ **कृषि चेतावनी:**\n" if lang == "hi" else "⚠️ **Farming Alerts:**\n")
                resp += "\n".join(a.replace("[ALERT]", "").strip() for a in alerts[:3]) + "\n\n"

            if forecast_lines:
                resp += ("📅 **7 दिन का पूर्वानुमान:**\n" if lang == "hi" else "📅 **7-Day Forecast:**\n")
                resp += "\n".join(f"• {l.strip()}" for l in forecast_lines[:5]) + "\n\n"

            resp += "🌐 IMD: **mausam.imd.gov.in** | Meghdoot App"
            return alert_prefix + resp

        # ── CROP RECOMMENDATION ──────────────────────────────────
        if intent in (INTENT_CROP_RECOMMENDATION, INTENT_CROP_INFO):
            rec_lines = [l for l in context_block.splitlines() if "suitability" in l]

            header = {
                "hi": f"🌾 **{loc}** के लिए फसल सुझाव — {season}\n\n🌡️ मौसम: {temp}°C, {cond}\n\n",
                "en": f"🌾 Crop Recommendations for **{loc}** — {season}\n\n🌡️ Weather: {temp}°C, {cond}\n\n",
            }.get(lang, f"Crop recommendations for {loc}:\n\n")

            if rec_lines:
                body = ""
                for i, line in enumerate(rec_lines[:5], 1):
                    m = re.search(
                        r"\s*([^(:]+)\s*(?:\(([^)]*)\))?:\s*suitability\s*([\d]+)%,"
                        r".*profit\s*Rs\s*([\d,]+)/ha,\s*MSP\s*Rs\s*([\d]+)/q",
                        line,
                    )
                    if m:
                        crop_name  = m.group(1).strip()
                        local_val  = m.group(2).strip() if m.group(2) else ""
                        show_local = (
                            local_val and
                            local_val.lower().replace("_", " ").strip() != crop_name.lower().replace("_", " ").strip()
                        )
                        local_desc = f" ({local_val})" if show_local else ""
                        score      = m.group(3)
                        profit     = m.group(4)
                        msp        = m.group(5)
                        bar = "🟢" if int(score) >= 80 else "🟡" if int(score) >= 60 else "🔴"
                        body += (
                            f"{i}. {bar} **{crop_name}{local_desc}** — {score}% सटीकता\n"
                            f"   ₹{profit}/हे. लाभ | MSP ₹{msp}/q\n"
                        )
                    else:
                        body += f"• {line.strip().lstrip('- ')}\n"
            else:
                body = (
                    "• 🟢 **गेहूँ** — रबी सीजन, MSP ₹2,275/q\n"
                    "• 🟢 **सरसों** — कम पानी, MSP ₹5,650/q\n"
                    "• 🟡 **चना** — हल्की मिट्टी, MSP ₹5,440/q\n"
                    if lang == "hi" else
                    "• 🟢 **Wheat** — Rabi season, MSP ₹2,275/q\n"
                    "• 🟢 **Mustard** — low water, MSP ₹5,650/q\n"
                    "• 🟡 **Gram** — light soil, MSP ₹5,440/q\n"
                )

            footer = {
                "hi": f"\n\n💡 {farming_advice or 'बुवाई से पहले मिट्टी जांच करवाएं।'}\n📞 ICAR: 1800-180-1551",
                "en": f"\n\n💡 {farming_advice or 'Get soil tested before sowing.'}\n📞 ICAR: 1800-180-1551",
            }.get(lang, "")
            return alert_prefix + header + body + footer

        # ── MARKET PRICE ─────────────────────────────────────────
        if intent == INTENT_MARKET_PRICE:
            price_lines = [l for l in context_block.splitlines() if "modal Rs" in l]
            msp_lines   = [l for l in context_block.splitlines() if "[MSP 2024-25]" in l or "MSP 2024-25" in l]

            if price_lines:
                header = {
                    "hi": f"💰 **{loc}** के पास मंडी भाव (आज, Agmarknet):\n\n",
                    "en": f"💰 Live Mandi Prices near **{loc}** (Agmarknet today):\n\n",
                }.get(lang, f"Mandi prices near {loc}:\n\n")
                body = ""
                for line in price_lines[:8]:
                    m = re.search(
                        r"\s*([^(:]+)\s*(?:\(([^)]*)\))?:\s*modal\s*Rs\s*([\d]+)"
                        r"(?:/q)?,\s*MSP\s*Rs\s*([\d]+)(?:/q)?,\s*mandi:\s*([^,\n]+)",
                        line,
                    )
                    if m:
                        crop       = m.group(1).strip()
                        local_desc = f" ({m.group(2).strip()})" if m.group(2) else ""
                        modal      = m.group(3)
                        msp        = m.group(4)
                        mandi      = m.group(5).strip()
                        profit     = int(modal) - int(msp)
                        ind = "📈" if profit >= 0 else "📉"
                        body += f"• {ind} **{crop}{local_desc}** : ₹{modal}/q | MSP ₹{msp}/q | 🏪 {mandi}\n"
                    else:
                        body += f"• {line.strip().lstrip('- ')}\n"
                footer = {
                    "hi": "\n📊 स्रोत: Agmarknet/data.gov.in | agmarknet.gov.in",
                    "en": "\n📊 Source: Agmarknet/data.gov.in | agmarknet.gov.in",
                }.get(lang, "")
                return alert_prefix + header + body + footer
            else:
                msp_body = ""
                if msp_lines:
                    for line in msp_lines[:5]:
                        msp_body += f"• {line.replace('[MSP 2024-25]', '').strip()}\n"
                else:
                    msp_body = (
                        "• गेहूँ: ₹2,275/q\n• धान: ₹2,300/q\n• सरसों: ₹5,650/q\n"
                        "• मक्का: ₹2,090/q\n• सोयाबीन: ₹4,892/q"
                        if lang == "hi" else
                        "• Wheat: ₹2,275/q\n• Rice: ₹2,300/q\n• Mustard: ₹5,650/q\n"
                        "• Maize: ₹2,090/q\n• Soybean: ₹4,892/q"
                    )
                no_live = {
                    "hi": (
                        f"⚠️ आज का लाइव मंडी भाव उपलब्ध नहीं।\n\n"
                        f"📊 **MSP 2024-25** (न्यूनतम समर्थन मूल्य):\n{msp_body}\n\n"
                        f"🌐 agmarknet.gov.in पर देखें\n📞 eNAM: 1800-270-0224"
                    ),
                    "en": (
                        f"⚠️ Live mandi prices unavailable.\n\n"
                        f"📊 **MSP 2024-25** (Minimum Support Price):\n{msp_body}\n\n"
                        f"🌐 Check agmarknet.gov.in\n📞 eNAM: 1800-270-0224"
                    ),
                }.get(lang, f"Live mandi prices unavailable. MSP:\n{msp_body}")
                return alert_prefix + no_live

        # ── GOVERNMENT SCHEMES ────────────────────────────────────
        if intent == INTENT_GOVERNMENT_SCHEME:
            scheme_lines = [l for l in context_block.splitlines() if "Apply:" in l]
            header = {
                "hi": "🏛️ **किसानों के लिए सरकारी योजनाएं:**\n\n",
                "en": "🏛️ **Government Schemes for Farmers:**\n\n",
            }.get(lang, "Government schemes:\n\n")
            if scheme_lines:
                body = "\n".join(f"• {l.strip().lstrip('- ')}" for l in scheme_lines[:5])
            else:
                body = (
                    "• **PM-Kisan**: ₹6,000/वर्ष — pmkisan.gov.in | 155261\n"
                    "• **PMFBY**: 2% प्रीमियम फसल बीमा — pmfby.gov.in | 14447\n"
                    "• **KCC**: ₹3 लाख @4% ब्याज — निकटतम बैंक\n"
                    "• **PM-KUSUM**: 90% सब्सिडी सोलर पंप — pmkusum.mnre.gov.in\n"
                    "• **Soil Health Card**: मुफ्त मिट्टी जांच — soilhealth.dac.gov.in"
                    if lang == "hi" else
                    "• **PM-Kisan**: ₹6,000/year — pmkisan.gov.in | 155261\n"
                    "• **PMFBY**: 2% premium crop insurance — pmfby.gov.in | 14447\n"
                    "• **KCC**: ₹3L credit @4% interest — nearest bank\n"
                    "• **PM-KUSUM**: 90% subsidy solar pump — pmkusum.mnre.gov.in\n"
                    "• **Soil Health Card**: Free soil testing — soilhealth.dac.gov.in"
                )
            return alert_prefix + header + body + "\n\n📞 Kisan Call Centre: **1800-180-1551** (Free)"

        # ── PEST / DISEASE ────────────────────────────────────────
        if intent == INTENT_PEST_DISEASE:
            crop_hint = f" ({crops[0]['name']})" if crops else ""
            crop_id   = crops[0].get("id", "").lower() if crops else ""

            # Crop-specific common diseases & treatment (ICAR POP)
            _DISEASE_DB: Dict[str, List[Tuple[str, str, str]]] = {
                # crop → [(disease_hindi, symptom, treatment)]
                "wheat": [
                    ("पीला रतुआ (Yellow Rust)", "पत्तियों पर पीली धारियां — ठंड में फैलता है",
                     "Propiconazole 25EC 0.1% spray | Tebuconazole 250EC 0.1%"),
                    ("भूरा रतुआ (Brown Rust)", "पत्तियों पर भूरे-नारंगी धब्बे",
                     "Mancozeb 0.25% | Propiconazole 0.1% at first sign"),
                    ("करनाल बंट (Karnal Bunt)", "दाने काले-बदबूदार", "Certified seed + Carboxin 75WP seed treatment"),
                    ("माहू (Aphid)", "पत्तियां मुड़ी, चिपचिपी — रस चूसता है",
                     "Imidacloprid 17.8SL 0.5ml/L या Dimethoate 30EC 1.5ml/L"),
                ],
                "rice": [
                    ("ब्लास्ट (Blast)", "पत्तियों पर हीरे के आकार के धब्बे — नेक ब्लास्ट में गर्दन टूटती है",
                     "Tricyclazole 75WP 0.6g/L या Isoprothiolane 40EC 1.5ml/L"),
                    ("शीथ ब्लाइट", "निचली पत्तियों पर हरे-भूरे धब्बे",
                     "Hexaconazole 5SC 2ml/L | Propiconazole 0.1%"),
                    ("BPH (Brown Planthopper)", "पौध पीला-सूख जाना (Hopper Burn)",
                     "Buprofezin 25SC 1ml/L | Clothianidin 50WDG 0.3g/L"),
                    ("तना छेदक (Stem Borer)", "Dead heart/White ear — तने में छेद",
                     "Chlorpyriphos 20EC 2.5ml/L | Cartap 50SP 1g/L"),
                ],
                "maize": [
                    ("Fall Armyworm (FAW)", "पत्तियों में छेद, केंद्र में देखो — नया खतरा",
                     "Emamectin Benzoate 5SG 0.4g/L या Chlorantraniliprole 0.4ml/L"),
                    ("तना सड़न (Stalk Rot)", "पके समय पौध गिर जाना",
                     "Potassium fertilizer balance | avoid waterlogging"),
                    ("मेड़ तुड़ाई (Downy Mildew)", "पत्तियां हरी-पीली धारियां",
                     "Metalaxyl 35SD seed treatment + Mancozeb 0.25% spray"),
                ],
                "mustard": [
                    ("सफेद रतुआ (White Rust)", "पत्तियों पर सफेद धब्बे, पुष्पक्रम विकृत",
                     "Mancozeb 0.25% या Metalaxyl+Mancozeb 0.25% 2-3 बार"),
                    ("तुलसीता (Downy Mildew)", "पत्तियां नीचे से सफेद-भूरे धब्बे",
                     "Ridomil MZ 0.2% spray at first sign"),
                    ("माहू (Aphid)", "फूलने के समय पुष्पों पर — उपज 30% कम",
                     "Oxydemeton methyl 25EC 1ml/L या Dimethoate 30EC 1.5ml/L"),
                ],
                "soybean": [
                    ("पर्ण धब्बा (Leaf Spot)", "भूरे-पीले गोल धब्बे",
                     "Mancozeb+Carbendazim 0.2% spray"),
                    ("तना सड़न (Stem Rot)", "जड़ के पास सफेद फफूंदी",
                     "Soil drenching with Carbendazim 0.1%"),
                    ("गर्डल बीटल", "तने पर गोल निशान — जड़ टूट जाती है",
                     "Chlorpyriphos 20EC 2ml/L foliar"),
                ],
                "cotton": [
                    ("गुलाबी सुंडी (Pink Bollworm)", "फूल-फल में छेद — डोडे काटे",
                     "Spinosad 45SC 0.3ml/L | Emamectin 0.4g/L | Pheromone traps 5/ha"),
                    ("सफेद मक्खी (Whitefly)", "पत्तियां पीली-मुड़ी — Virus वाहक",
                     "Imidacloprid 0.3ml/L (seed treatment preferred) | Neem oil 5ml/L"),
                    ("अमेरिकन सुंडी (Bollworm)", "डोडे में छेद",
                     "Chlorantraniliprole 18.5SC 0.3ml/L | Bt spray"),
                ],
                "tomato": [
                    ("झुलसा (Early Blight)", "पत्तियों पर भूरे-काले गोल छल्लेदार धब्बे",
                     "Mancozeb 0.25% + Copper Oxychloride 0.3% spray 10 दिन में"),
                    ("late Blight", "पत्तियां काली पड़ जाती हैं — ठंड+नमी में फैलता है",
                     "Metalaxyl+Mancozeb (Ridomil) 0.2% spray immediately"),
                    ("फल छेदक (Fruitborer)", "फलों में छेद",
                     "Spinosad 0.3ml/L | Pheromone trap 15/ha"),
                ],
                "potato": [
                    ("पिछेता झुलसा (Late Blight)", "पत्तियां भूरी-काली, सड़ाँव गंध",
                     "Cymoxanil+Mancozeb 0.3% या Chlorothalonil 0.2% हर 5-7 दिन"),
                    ("आगेता झुलसा (Early Blight)", "पत्तियों पर गोल भूरे धब्बे",
                     "Mancozeb 0.25% spray preventively"),
                ],
            }

            # Try to identify which disease/pest is being asked about
            q_lower = query.lower()
            pest_keywords = {
                "yellow": "पीली पत्तियां — Yellow Rust/Chlorosis",
                "pili":   "पीली पत्तियां — Yellow Rust/Chlorosis",
                "blast":  "Blast disease",
                "rust":   "Rust disease",
                "aphid":  "Aphid/Mahu",
                "mahu":   "Aphid/Mahu",
                "maahu":  "Aphid/Mahu",
                "sundi":  "Bollworm/Caterpillar",
                "boll":   "Bollworm",
                "whitefly":"Whitefly",
                "mite":   "Spider mite",
                "stem borer": "Stem borer",
                "tana":   "Stem borer",
                "jad":    "Root rot",
                "rot":    "Root/Stem rot",
                "wilt":   "Wilting disease",
                "mur":    "Wilting",
            }
            detected_pest = next(
                (label for kw, label in pest_keywords.items() if kw in q_lower), None
            )

            if crop_id and crop_id in _DISEASE_DB:
                diseases = _DISEASE_DB[crop_id]
                crop_name_display = crops[0]["name"] if crops else crop_id.title()

                # If specific pest detected, show that one first
                if detected_pest:
                    relevant = [d for d in diseases if any(
                        kw in d[0].lower() or kw in d[1].lower()
                        for kw in q_lower.split()
                    )] or diseases[:2]
                else:
                    relevant = diseases[:3]

                body = {
                    "hi": (
                        f"🐛 **{crop_name_display} — कीट/रोग उपचार ({loc})**\n\n"
                        + "".join(
                            f"**{i+1}. {dis}**\n"
                            f"   🔍 लक्षण: {sym}\n"
                            f"   💊 उपचार: {trt}\n\n"
                            for i, (dis, sym, trt) in enumerate(relevant)
                        )
                        + f"📸 **फोटो पहचान:** KrishiRaksha में तस्वीर अपलोड करें → AI से 150+ रोग पहचान\n"
                        + f"🌿 **जैविक विकल्प:** नीम तेल 5ml/L पानी | Trichoderma viride 2.5 kg/ha\n\n"
                        + (f"⚠️ **स्प्रे रोकें** — अगले 48 घंटे बारिश संभावित\n" if wc.spray_blocked else
                           f"✅ **स्प्रे के लिए उचित समय:** सुबह 7-10 बजे या शाम 4-6 बजे\n")
                        + f"\n📞 KVK/ICAR: 1800-180-1551"
                    ),
                    "en": (
                        f"🐛 **{crop_name_display} — Pest/Disease Treatment ({loc})**\n\n"
                        + "".join(
                            f"**{i+1}. {dis}**\n"
                            f"   🔍 Symptoms: {sym}\n"
                            f"   💊 Treatment: {trt}\n\n"
                            for i, (dis, sym, trt) in enumerate(relevant)
                        )
                        + f"📸 **Photo ID:** Upload photo in KrishiRaksha → AI identifies 150+ diseases\n"
                        + f"🌿 **Organic:** Neem oil 5ml/L | Trichoderma viride 2.5 kg/ha\n\n"
                        + (f"⚠️ **Hold spray** — rain in 48h\n" if wc.spray_blocked else
                           f"✅ **Best spray time:** 7-10 AM or 4-6 PM\n")
                        + f"\n📞 KVK/ICAR: 1800-180-1551"
                    ),
                }.get(lang, f"{crop_name_display} diseases: {'; '.join(d[0] for d in relevant[:2])}. Spray {relevant[0][2] if relevant else 'Mancozeb 0.25%'}.")
            else:
                # Generic pest/disease response
                body = {
                    "hi": (
                        f"🐛 **फसल रोग/कीट उपचार{crop_hint} — {loc}**\n\n"
                        f"📸 **Step 1:** KrishiRaksha में फोटो अपलोड करें (🐛 बटन)\n"
                        f"   → EfficientNet-B3 AI से 150+ रोगों की पहचान\n\n"
                        f"🌿 **तुरंत जैविक उपाय:**\n"
                        f"• नीम तेल 5ml/L — माहू, सफेद मक्खी, थ्रिप्स\n"
                        f"• Trichoderma viride 2.5 kg/ha — जड़ सड़न\n"
                        f"• पीला/नीला sticky trap — कीट निगरानी\n\n"
                        f"💊 **रासायनिक (ICAR अनुशंसित):**\n"
                        f"• Imidacloprid 17.8SL 0.5ml/L — माहू, सफेद मक्खी\n"
                        f"• Mancozeb 0.25% — फफूंद रोग\n"
                        f"• Propiconazole 0.1% — रतुआ, ब्लाइट\n"
                        f"• Chlorpyriphos 20EC 2ml/L — तना छेदक\n\n"
                        + (f"⚠️ **स्प्रे न करें** — 48 घंटे बारिश संभावित\n" if wc.spray_blocked else "")
                        + f"📞 KVK/ICAR: 1800-180-1551"
                    ),
                    "en": (
                        f"🐛 **Pest/Disease Treatment{crop_hint} — {loc}**\n\n"
                        f"📸 **Step 1:** Upload photo in KrishiRaksha (🐛 button)\n"
                        f"   → EfficientNet-B3 AI identifies 150+ diseases\n\n"
                        f"🌿 **Immediate organic remedies:**\n"
                        f"• Neem oil 5ml/L — aphids, whitefly, thrips\n"
                        f"• Trichoderma viride 2.5 kg/ha — root rot\n"
                        f"• Yellow/blue sticky traps — pest monitoring\n\n"
                        f"💊 **Chemical (ICAR recommended):**\n"
                        f"• Imidacloprid 17.8SL 0.5ml/L — aphids, whitefly\n"
                        f"• Mancozeb 0.25% — fungal diseases\n"
                        f"• Propiconazole 0.1% — rust, blight\n"
                        f"• Chlorpyriphos 20EC 2ml/L — stem borers\n\n"
                        + (f"⚠️ **Hold spray** — rain forecast in 48h\n" if wc.spray_blocked else "")
                        + f"📞 KVK/ICAR: 1800-180-1551"
                    ),
                }.get(lang, "Upload leaf photo in KrishiRaksha for disease ID. Use neem oil first. Call 1800-180-1551.")
            return alert_prefix + spray_warning + body

        # ── FERTILIZER ────────────────────────────────────────────
        if intent == INTENT_FERTILIZER:
            crop_hint = f" for {crops[0]['name']}" if crops else ""
            crop_id   = crops[0].get("id", "").lower() if crops else ""

            # Stage-specific fertilizer schedule (ICAR package of practices)
            _FERT_SCHEDULE: Dict[str, List[Tuple[str, str, str]]] = {
                # crop_id → list of (timing, dose, notes)
                "wheat": [
                    ("बुवाई पर (Basal)", "120 kg DAP + 25 kg MOP/ha", "सारा P+K + आधा N"),
                    ("21 DAS — CRI (पहला पानी)", "65 kg Urea/ha top-dress", "बाकी 50% N"),
                    ("40 DAS — Tillering", "30 kg Urea/ha (foliar या top-dress)", "यदि पत्तियां पीली हों"),
                    ("60 DAS — Jointing", "Zinc Sulphate 25 kg/ha (यदि कमी हो)", "optional"),
                ],
                "rice": [
                    ("Transplanting Basal", "100 kg DAP + 50 kg MOP/ha", "पूरा P+K"),
                    ("10-12 DAS (establishment)", "65 kg Urea/ha", "33% N"),
                    ("25-30 DAS (active tillering)", "65 kg Urea/ha", "33% N"),
                    ("45-50 DAS (panicle initiation)", "65 kg Urea/ha", "33% N"),
                    ("60 DAS (optional foliar)", "Urea 1% spray if pale", "optional"),
                ],
                "maize": [
                    ("Basal (Sowing)", "150 kg DAP/ha", "पूरा P + 33% N"),
                    ("25-30 DAS (V6 stage)", "87 kg Urea/ha", "33% N top-dress"),
                    ("45-50 DAS (VT/Tasseling)", "87 kg Urea/ha", "33% N — critical stage"),
                ],
                "mustard": [
                    ("Basal (Sowing)", "75 kg DAP + 37 kg MOP/ha", "पूरा P+K + 50% N"),
                    ("25-30 DAS (Branching)", "43 kg Urea/ha top-dress", "50% N"),
                    ("55-60 DAS (Pre-flowering)", "Boron 1g/L foliar spray", "pod set improvement"),
                ],
                "gram": [
                    ("Basal", "50 kg DAP + Rhizobium + PSB culture", "P + biofert"),
                    ("25-30 DAS (Branching)", "20 kg Urea (only if poor growth)", "minimal N"),
                    ("55-60 DAS (Pre-flowering)", "Borax 1.5 kg/ha foliar", "pod set"),
                ],
                "soybean": [
                    ("Basal", "125 kg DAP + 50 kg MOP + Rhizobium", "पूरा P+K + biofert"),
                    ("20-25 DAS", "Micronutrient: Zinc 25 kg/ha (if deficient)", "optional"),
                    ("45 DAS (Flowering)", "Potash foliar 1% if lodging", "optional"),
                ],
                "cotton": [
                    ("Basal", "75 kg DAP + 25 kg MOP/ha", "P+K base"),
                    ("30 DAS (Squaring)", "65 kg Urea/ha", "N for vegetative"),
                    ("60 DAS (Boll development)", "65 kg Urea + 25 kg MOP/ha", "N+K for bolls"),
                    ("90 DAS (Boll opening)", "Potash 1% foliar", "quality improvement"),
                ],
                "potato": [
                    ("Planting", "200 kg DAP + 120 kg MOP/ha", "full P+K"),
                    ("25-30 DAS (earthing up)", "100 kg Urea/ha", "50% N"),
                    ("50-55 DAS (tuber init)", "50 kg Urea/ha", "remaining N"),
                    ("75 DAS (bulking)", "SOP 100 kg/ha foliar or soil", "quality K"),
                ],
            }

            # Use DAS entity to give stage-specific advice
            das = qe.get("das")
            stage = qe.get("stage")

            if crop_id and crop_id in _FERT_SCHEDULE:
                schedule = _FERT_SCHEDULE[crop_id]
                crop_name_display = crops[0]["name"] if crops else crop_id.title()

                # If DAS mentioned, give targeted advice for that stage
                if das is not None:
                    # Find closest schedule entry
                    best_entry = schedule[-1]  # default last
                    for entry in schedule:
                        # Extract DAS number from timing string if present
                        das_m = re.search(r"(\d+)\s*DAS", entry[0])
                        if das_m and int(das_m.group(1)) <= das:
                            best_entry = entry
                    timing, dose, notes = best_entry
                    body = {
                        "hi": (
                            f"🌱 **{crop_name_display} — {das} DAS पर खाद ({loc})**\n\n"
                            f"📅 **अभी का चरण:** {timing}\n"
                            f"💊 **अनुशंसित खाद:** {dose}\n"
                            f"📝 **नोट:** {notes}\n\n"
                            f"**ICAR पूरा कार्यक्रम:**\n"
                            + "\n".join(f"• {t}: {d} — {n}" for t, d, n in schedule)
                            + f"\n\n⚠️ खाद डालने से पहले: नमी जरूरी — सूखे में न डालें\n"
                            + (f"⛔ अगले {wc.forecast_3day} में बारिश — खाद डालना ठीक है" if not wc.spray_blocked else "⚠️ बारिश की संभावना — 48 घंटे रुकें")
                            + f"\n\n📞 ICAR: 1800-180-1551"
                        ),
                        "en": (
                            f"🌱 **{crop_name_display} — Fertiliser at {das} DAS ({loc})**\n\n"
                            f"📅 **Current stage:** {timing}\n"
                            f"💊 **Recommended dose:** {dose}\n"
                            f"📝 **Note:** {notes}\n\n"
                            f"**Full ICAR schedule:**\n"
                            + "\n".join(f"• {t}: {d} — {n}" for t, d, n in schedule)
                            + f"\n\n⚠️ Apply only when soil is moist\n"
                            + (f"⛔ Rain forecast: good time for fertiliser" if not wc.spray_blocked else "⚠️ Rain in 48h — wait before applying urea")
                            + f"\n\n📞 ICAR: 1800-180-1551"
                        ),
                    }.get(lang, f"{crop_name_display} at {das} DAS: apply {dose}.")
                else:
                    # No DAS — give full schedule
                    body = {
                        "hi": (
                            f"🌱 **{crop_name_display} खाद कार्यक्रम (ICAR) — {loc}**\n\n"
                            + "\n".join(f"**{i+1}. {t}**\n   • {d}\n   • {n}" for i, (t, d, n) in enumerate(schedule))
                            + f"\n\n💡 **सामान्य नियम:**\n"
                            f"• Neem Coated Urea (NCU) — 8-10% N बचत\n"
                            f"• मिट्टी जांच के बाद ही खाद डालें\n"
                            f"• सिंचाई के बाद top-dress करें\n"
                            + (f"\n⚠️ बारिश संभावित — 48 घंटे रुकें" if wc.spray_blocked else "")
                            + f"\n\n📞 ICAR: 1800-180-1551"
                        ),
                        "en": (
                            f"🌱 **{crop_name_display} Fertiliser Schedule (ICAR) — {loc}**\n\n"
                            + "\n".join(f"**{i+1}. {t}**\n   • {d}\n   • {n}" for i, (t, d, n) in enumerate(schedule))
                            + f"\n\n💡 **General rules:**\n"
                            f"• Use neem-coated urea (NCU) — saves 8-10% N\n"
                            f"• Always get soil tested first\n"
                            f"• Apply after irrigation, not before\n"
                            + (f"\n⚠️ Rain forecast — wait 48h" if wc.spray_blocked else "")
                            + f"\n\n📞 ICAR: 1800-180-1551"
                        ),
                    }.get(lang, f"Full {crop_name_display} fertiliser schedule: " + "; ".join(f"{t}:{d}" for t,d,n in schedule))
            else:
                # Generic fertiliser response
                body = {
                    "hi": (
                        f"🌱 **खाद/उर्वरक सुझाव{crop_hint} — {loc}**\n\n"
                        f"**ICAR अनुशंसित मात्रा:**\n"
                        f"• **Urea (46% N):** 217 kg/ha → 100 kg N देने के लिए\n"
                        f"• **DAP (18-46-0):** 220 kg/ha → 100 kg P + 40 kg N\n"
                        f"• **MOP (60% K):** 167 kg/ha → 100 kg K\n"
                        f"• **Zinc Sulphate:** 25 kg/ha (यदि कमी हो)\n\n"
                        f"**Split Dose नियम:**\n"
                        f"• 50% N बुवाई पर + 25% N 25 DAS + 25% N 45 DAS\n"
                        f"• पूरा P और K — बुवाई पर ही\n\n"
                        f"💡 मिट्टी जांच: soilhealth.dac.gov.in\n"
                        + (f"⚠️ अगले 48 घंटे में बारिश — Urea top-dress रोकें\n" if wc.spray_blocked else "")
                        + f"📞 ICAR: 1800-180-1551"
                    ),
                    "en": (
                        f"🌱 **Fertiliser Recommendations{crop_hint} — {loc}**\n\n"
                        f"**ICAR standard doses:**\n"
                        f"• **Urea (46% N):** 217 kg/ha → 100 kg N\n"
                        f"• **DAP (18-46-0):** 220 kg/ha → 100 kg P + 40 kg N\n"
                        f"• **MOP (60% K):** 167 kg/ha → 100 kg K\n"
                        f"• **Zinc Sulphate:** 25 kg/ha (if Zn deficient)\n\n"
                        f"**Split dose rule:**\n"
                        f"• 50% N at sowing + 25% at 25 DAS + 25% at 45 DAS\n"
                        f"• All P and K — basal at sowing\n\n"
                        f"💡 Soil test: soilhealth.dac.gov.in\n"
                        + (f"⚠️ Rain in 48h — delay Urea top-dress\n" if wc.spray_blocked else "")
                        + f"📞 ICAR: 1800-180-1551"
                    ),
                }.get(lang, f"Fertiliser: Urea 217 kg/ha, DAP 220 kg/ha, MOP 167 kg/ha. Split 50%+25%+25% N.")
            return alert_prefix + spray_warning + body

        # ── IRRIGATION ────────────────────────────────────────────
        if intent == INTENT_IRRIGATION:
            et0       = _extract(r"ET0 ([\d.]+)mm/day")
            irr_lines = [l for l in context_block.splitlines() if "IRRIGATE" in l]

            # ── Crop-specific irrigation schedule (ICAR data) ──────────────
            # Maps crop id → (interval_days, quantity_mm, critical_stages)
            _CROP_IRR_SCHEDULE = {
                "wheat":     (21, "50-60", "CRI (21 DAS), tillering (40 DAS), jointing (60 DAS), flowering (80 DAS), grain fill (100 DAS)"),
                "gehu":      (21, "50-60", "बुवाई के 21, 40, 60, 80, 100 दिन बाद — 5-6 सिंचाई"),
                "rice":      (3,  "50-70", "निरंतर 5cm जलस्तर या AWD (3-4 दिन सूखने पर)"),
                "paddy":     (3,  "50-70", "Continuous flooding or AWD every 3-4 days"),
                "maize":     (10, "50-60", "तस्सल निकलने (V6), फूल (VT), दाना भरना (R2-R3) — 3 महत्वपूर्ण"),
                "sugarcane": (10, "50-75", "germination (7-15 DAS), tillering, grand growth, maturity"),
                "mustard":   (25, "40-50", "बुवाई के 25-30 दिन बाद (branching), 55-60 दिन (flowering) — 2 सिंचाई"),
                "cotton":    (14, "50-60", "squaring, boll formation, boll opening — avoid excess"),
                "soybean":   (14, "40-50", "vegetative (V3), flowering (R1), pod fill (R3) — 3 critical"),
                "potato":    (7,  "40-50", "planting to emergence, tuber initiation, bulking — every 7-10 days"),
                "tomato":    (7,  "35-50", "transplanting, flowering, fruiting — every 5-7 days"),
                "gram":      (30, "40",    "बुवाई के 30-35 दिन (branching), 60-65 दिन (flowering) — 2 सिंचाई"),
                "chana":     (30, "40",    "शाखाएं निकलने (30 DAS) + फूल (60 DAS) — 2 सिंचाई"),
            }

            # Detect which crop is asked about
            crop_id = None
            if crops:
                crop_id = crops[0].get("id", "").lower()
            else:
                q_lower = query.lower()
                for k in _CROP_IRR_SCHEDULE:
                    if k in q_lower:
                        crop_id = k
                        break
                # Aliases
                if not crop_id:
                    if any(w in q_lower for w in ("gehu", "gehun", "गेहूँ", "गेहू", "wheat")):
                        crop_id = "wheat"
                    elif any(w in q_lower for w in ("dhan", "chawal", "dhaan", "धान", "rice", "paddy")):
                        crop_id = "rice"
                    elif any(w in q_lower for w in ("makka", "maize", "मक्का", "corn")):
                        crop_id = "maize"

            if crop_id and crop_id in _CROP_IRR_SCHEDULE:
                interval, qty_mm, stages = _CROP_IRR_SCHEDULE[crop_id]
                crop_name_display = crops[0]["name"] if crops else crop_id.title()

                # Rain check — reduce need if rain expected
                rain_note = ""
                if wc.rain_next_3d_mm and wc.rain_next_3d_mm > 20:
                    rain_note = (
                        f"\n\n⚠️ अगले 3 दिनों में **{wc.rain_next_3d_mm:.0f}mm** बारिश संभावित — "
                        f"सिंचाई {interval//2} दिन और टालें।"
                        if lang == "hi" else
                        f"\n\n⚠️ Rain forecast {wc.rain_next_3d_mm:.0f}mm in 3 days — "
                        f"delay irrigation by {interval//2} more days."
                    )

                body = {
                    "hi": (
                        f"💧 **{crop_name_display} की सिंचाई — {loc}**\n\n"
                        f"🌡️ अभी: {temp}°C | ET₀: {et0} mm/दिन\n\n"
                        f"**ICAR सिंचाई कार्यक्रम:**\n"
                        f"• सिंचाई अंतर: **{interval} दिन**\n"
                        f"• पानी की मात्रा: **{qty_mm} mm** प्रति सिंचाई\n"
                        f"• महत्वपूर्ण अवस्थाएं: {stages}\n\n"
                        f"**बचत के उपाय:**\n"
                        f"• Drip/Sprinkler से 40% पानी बचाएं\n"
                        f"• सुबह 6-9 बजे सिंचाई करें — वाष्पीकरण कम\n"
                        f"• मल्चिंग से नमी बनाए रखें{rain_note}\n\n"
                        f"📞 PM-KUSUM: 1800-180-3333 | ICAR: 1800-180-1551"
                    ),
                    "en": (
                        f"💧 **{crop_name_display} Irrigation — {loc}**\n\n"
                        f"🌡️ Weather: {temp}°C | ET₀: {et0} mm/day\n\n"
                        f"**ICAR Irrigation Schedule:**\n"
                        f"• Interval: **every {interval} days**\n"
                        f"• Quantity: **{qty_mm} mm** per irrigation\n"
                        f"• Critical stages: {stages}\n\n"
                        f"**Water-saving tips:**\n"
                        f"• Drip/sprinkler saves 40% water\n"
                        f"• Irrigate 6-9 AM to reduce evaporation\n"
                        f"• Mulching retains soil moisture{rain_note}\n\n"
                        f"📞 PM-KUSUM: 1800-180-3333 | ICAR: 1800-180-1551"
                    ),
                }.get(lang, f"{crop_name_display}: irrigate every {interval} days, {qty_mm}mm. Stages: {stages}")
            else:
                # Generic irrigation response when no specific crop detected
                body = {
                    "hi": (
                        f"💧 **सिंचाई सलाह — {loc}**\n\n"
                        f"🌡️ मौसम: {temp}°C | ET₀: {et0} mm/दिन\n\n"
                        f"**प्रमुख फसलों का सिंचाई अंतर (ICAR):**\n"
                        f"• गेहूँ: **21 दिन** (5-6 सिंचाई पूरी फसल में)\n"
                        f"• धान: **3-4 दिन** (AWD विधि) या निरंतर\n"
                        f"• मक्का: **10 दिन**\n"
                        f"• सरसों: **25-30 दिन** (केवल 2 सिंचाई)\n"
                        f"• चना: **30 दिन** (केवल 2 सिंचाई)\n\n"
                        f"**PM-KUSUM सोलर पंप:** 90% सब्सिडी — pmkusum.mnre.gov.in\n"
                        + (f"⚠️ सिंचाई जरूरी: {', '.join(l.strip() for l in irr_lines[:3])}\n" if irr_lines else "")
                        + "\n📞 PM-KUSUM: 1800-180-3333"
                    ),
                    "en": (
                        f"💧 **Irrigation Advisory — {loc}**\n\n"
                        f"🌡️ Weather: {temp}°C | ET₀: {et0} mm/day\n\n"
                        f"**Crop irrigation intervals (ICAR):**\n"
                        f"• Wheat: **every 21 days** (5-6 irrigations total)\n"
                        f"• Rice/Paddy: **AWD every 3-4 days** or continuous\n"
                        f"• Maize: **every 10 days**\n"
                        f"• Mustard: **every 25-30 days** (only 2 irrigations)\n"
                        f"• Gram: **every 30 days** (only 2 irrigations)\n\n"
                        f"**PM-KUSUM Solar Pump:** 90% subsidy — pmkusum.mnre.gov.in\n"
                        + (f"⚠️ Irrigate: {', '.join(l.strip() for l in irr_lines[:3])}\n" if irr_lines else "")
                        + "\n📞 PM-KUSUM: 1800-180-3333"
                    ),
                }.get(lang, f"Irrigation: ET0={et0}mm/day. Use drip/sprinkler. PM-KUSUM 90% subsidy.")
            return alert_prefix + body

        # ── SOWING ───────────────────────────────────────────────
        if intent == INTENT_SOWING:
            # Comprehensive sowing calendar (ICAR + state KVK data)
            # key → (sowing_window, seed_rate_kg_ha, spacing_cm, depth_cm, varieties)
            _SOWING_CALENDAR = {
                "wheat": {
                    "window_hi": "नवंबर 1-30 (उत्तर भारत) | अक्टूबर (पहाड़ी क्षेत्र)",
                    "window_en": "Nov 1-30 (North India) | Oct (hills) | Dec (late sowing)",
                    "seed_rate": "100-125 kg/ha (irrigated) | 125-150 kg/ha (rainfed)",
                    "spacing":   "20-22 cm row spacing",
                    "depth":     "5-6 cm",
                    "varieties_hi": "HD-2967, DBW-187, DBW-222 (उत्तर भारत) | GW-322 (गुजरात) | HI-8498 (मध्य भारत)",
                    "varieties_en": "HD-2967, DBW-187, DBW-222 (North) | GW-322 (Gujarat) | HI-8498 (Central)",
                    "treatment":  "Thiram 2.5g/kg + Carbendazim 2g/kg बीज उपचार",
                },
                "rice": {
                    "window_hi": "जून-जुलाई (खरीफ) | नर्सरी: मई-जून",
                    "window_en": "Jun-Jul transplanting | Nursery: May-Jun | Direct seeding: Jun",
                    "seed_rate": "20-25 kg/ha (transplanting) | 80-100 kg/ha (direct)",
                    "spacing":   "20×15 cm or 20×20 cm",
                    "depth":     "2-3 cm (direct) | transplant 2-3 leaf seedlings",
                    "varieties_hi": "Swarna (MTU-7029), Pusa-44, BPT-5204 | HYV: IR-36, Samba Mahsuri",
                    "varieties_en": "Swarna (MTU-7029), Pusa-44, BPT-5204 | HYV: IR-36, Samba Mahsuri",
                    "treatment":  "Carbendazim 2g/kg बीज उपचार",
                },
                "maize": {
                    "window_hi": "जून-जुलाई (खरीफ) | रबी: अक्टूबर-नवंबर (दक्षिण भारत)",
                    "window_en": "Jun-Jul (Kharif) | Oct-Nov Rabi (South India)",
                    "seed_rate": "20-25 kg/ha (hybrid) | 15-20 kg/ha (composite)",
                    "spacing":   "60×20 cm (irrigated) | 75×25 cm (rainfed)",
                    "depth":     "4-5 cm",
                    "varieties_hi": "DKC-9144, Pioneer-3401, Pusa HM-4 | देसी: Amber",
                    "varieties_en": "DKC-9144, Pioneer-3401, Pusa HM-4 | Open pollinated: Amber",
                    "treatment":  "Imidacloprid 600 FS @ 4ml/kg",
                },
                "mustard": {
                    "window_hi": "अक्टूबर 1-30 (उत्तर भारत) | देर बुवाई: नवंबर 15 तक",
                    "window_en": "Oct 1-30 (North India) | Late sowing: up to Nov 15",
                    "seed_rate": "4-5 kg/ha (irrigated) | 5-6 kg/ha (rainfed)",
                    "spacing":   "30-45 cm row spacing | 10-15 cm plant spacing",
                    "depth":     "1-2 cm",
                    "varieties_hi": "Pusa Bold (B-54), NRCDR-2, RH-749, Varuna",
                    "varieties_en": "Pusa Bold (B-54), NRCDR-2, RH-749, Varuna",
                    "treatment":  "Thiram 2.5g/kg",
                },
                "gram": {
                    "window_hi": "अक्टूबर 25 - नवंबर 20",
                    "window_en": "Oct 25 - Nov 20 (Rabi season)",
                    "seed_rate": "75-80 kg/ha (desi) | 65-70 kg/ha (kabuli)",
                    "spacing":   "30×10 cm",
                    "depth":     "8-10 cm",
                    "varieties_hi": "JG-11, GNG-1958, HC-5, Pusa-372",
                    "varieties_en": "JG-11, GNG-1958, HC-5, Pusa-372",
                    "treatment":  "Thiram + Carbendazim (3:1) @ 3g/kg + Rhizobium culture",
                },
                "soybean": {
                    "window_hi": "जून 20 - जुलाई 15 (मध्य प्रदेश, महाराष्ट्र)",
                    "window_en": "Jun 20 - Jul 15 | Delay >Jul 15 reduces yield 15-20%",
                    "seed_rate": "70-80 kg/ha",
                    "spacing":   "45×5 cm",
                    "depth":     "3-4 cm",
                    "varieties_hi": "JS-9752, JS-335, Pusa-16, NRC-7",
                    "varieties_en": "JS-9752, JS-335, Pusa-16, NRC-7",
                    "treatment":  "Thiram 2.5g/kg + Rhizobium + PSB culture",
                },
                "cotton": {
                    "window_hi": "मई 1 - जून 30 (उत्तर भारत: अप्रैल-मई, दक्षिण: जुलाई तक)",
                    "window_en": "May 1 - Jun 30 | North India: Apr-May | South: up to Jul",
                    "seed_rate": "2.5-3 kg/ha (Bt hybrid)",
                    "spacing":   "90×60 cm (irrigated) | 60×30 cm (rainfed) for Bt",
                    "depth":     "3-4 cm",
                    "varieties_hi": "Bt Hybrids: RCH-2, MRC-7301, Bunny, Jadoo",
                    "varieties_en": "Bt Hybrids: RCH-2, MRC-7301 | Desi: MCU-5, LPS-141",
                    "treatment":  "Imidacloprid 600 FS 4ml/kg (aphid/thrip protection)",
                },
                "potato": {
                    "window_hi": "अक्टूबर 15 - नवंबर 30 (उत्तर भारत)",
                    "window_en": "Oct 15 - Nov 30 (North India) | Feb-Mar (hills)",
                    "seed_rate": "2000-2500 kg/ha (seed tubers, 40-50g each)",
                    "spacing":   "60×20 cm or 60×25 cm",
                    "depth":     "8-10 cm",
                    "varieties_hi": "Kufri Jyoti, Kufri Sinduri, Kufri Chipsona-1",
                    "varieties_en": "Kufri Jyoti, Kufri Sinduri, Kufri Chipsona-1",
                    "treatment":  "Mancozeb 0.3% dip + Bavistin 0.1%",
                },
            }

            crop_id = crops[0].get("id", "").lower() if crops else None
            # Alias normalisation
            if not crop_id:
                q_l = query.lower()
                if any(w in q_l for w in ("gehu","gehun","गेहूँ","गेहू","wheat")): crop_id = "wheat"
                elif any(w in q_l for w in ("dhan","chawal","dhaan","धान","rice","paddy")): crop_id = "rice"
                elif any(w in q_l for w in ("makka","maize","मक्का","corn")): crop_id = "maize"
                elif any(w in q_l for w in ("sarson","सरसों","mustard","rapeseed")): crop_id = "mustard"
                elif any(w in q_l for w in ("chana","gram","चना","chickpea")): crop_id = "gram"
                elif any(w in q_l for w in ("soybean","soya","सोयाबीन")): crop_id = "soybean"
                elif any(w in q_l for w in ("cotton","kapas","कपास")): crop_id = "cotton"
                elif any(w in q_l for w in ("potato","aloo","आलू")): crop_id = "potato"

            crop_name_display = crops[0]["name"] if crops else (crop_id.title() if crop_id else "")

            if crop_id and crop_id in _SOWING_CALENDAR:
                sc_data = _SOWING_CALENDAR[crop_id]
                body = {
                    "hi": (
                        f"🌱 **{crop_name_display} की बुवाई — {loc}**\n\n"
                        f"🗓️ **बुवाई का समय:** {sc_data['window_hi']}\n\n"
                        f"**ICAR अनुशंसित:**\n"
                        f"• बीज दर: **{sc_data['seed_rate']}**\n"
                        f"• पंक्ति दूरी: **{sc_data['spacing']}**\n"
                        f"• बुवाई गहराई: **{sc_data['depth']}**\n\n"
                        f"**किस्में:** {sc_data['varieties_hi']}\n\n"
                        f"**बीज उपचार:** {sc_data['treatment']}\n\n"
                        f"💡 **अभी का मौसम ({loc}):** {temp}°C — "
                        + ("बुवाई के लिए उपयुक्त" if temp and float(temp) < 30 else "तापमान अधिक है — बुवाई के लिए प्रतीक्षा करें")
                        + f"\n\n📞 KVK/ICAR: 1800-180-1551"
                    ),
                    "en": (
                        f"🌱 **{crop_name_display} Sowing Guide — {loc}**\n\n"
                        f"🗓️ **Sowing window:** {sc_data['window_en']}\n\n"
                        f"**ICAR recommended:**\n"
                        f"• Seed rate: **{sc_data['seed_rate']}**\n"
                        f"• Spacing: **{sc_data['spacing']}**\n"
                        f"• Sowing depth: **{sc_data['depth']}**\n\n"
                        f"**Varieties:** {sc_data['varieties_en']}\n\n"
                        f"**Seed treatment:** {sc_data['treatment']}\n\n"
                        f"💡 **Current weather ({loc}):** {temp}°C — "
                        + ("suitable for sowing" if temp and float(temp) < 30 else "too hot — wait for temperature to drop")
                        + f"\n\n📞 KVK/ICAR: 1800-180-1551"
                    ),
                }.get(lang, f"{crop_name_display}: sow {sc_data['window_en']}. Seed rate {sc_data['seed_rate']}.")
            else:
                # Season-based generic advice
                s = _current_season()
                body = {
                    "hi": (
                        f"🌱 **बुवाई कैलेंडर — {loc}** ({season})\n\n"
                        f"**खरीफ (जून-जुलाई):**\n"
                        f"• धान: 20-25 kg/ha | मक्का: 20-25 kg/ha\n"
                        f"• सोयाबीन: 75-80 kg/ha | कपास: 2.5 kg/ha (Bt)\n"
                        f"• मूँगफली: 100-120 kg/ha | उड़द/मूँग: 15-20 kg/ha\n\n"
                        f"**रबी (अक्टूबर-नवंबर):**\n"
                        f"• गेहूँ: 100-125 kg/ha | सरसों: 4-5 kg/ha\n"
                        f"• चना: 75-80 kg/ha | मसूर: 35-40 kg/ha\n"
                        f"• आलू: 2000-2500 kg/ha (कंद)\n\n"
                        f"📞 KVK सलाह: 1800-180-1551"
                    ),
                    "en": (
                        f"🌱 **Sowing Calendar — {loc}** ({season})\n\n"
                        f"**Kharif (Jun-Jul):**\n"
                        f"• Rice: 20-25 kg/ha | Maize: 20-25 kg/ha\n"
                        f"• Soybean: 75-80 kg/ha | Cotton (Bt): 2.5 kg/ha\n"
                        f"• Groundnut: 100-120 kg/ha | Urad/Moong: 15-20 kg/ha\n\n"
                        f"**Rabi (Oct-Nov):**\n"
                        f"• Wheat: 100-125 kg/ha | Mustard: 4-5 kg/ha\n"
                        f"• Gram: 75-80 kg/ha | Lentil: 35-40 kg/ha\n"
                        f"• Potato: 2000-2500 kg/ha (tubers)\n\n"
                        f"📞 KVK advice: 1800-180-1551"
                    ),
                }.get(lang, "Sowing calendar: Kharif(Jun-Jul) — Rice, Maize, Cotton. Rabi(Oct-Nov) — Wheat, Mustard, Gram.")
            return alert_prefix + body

        # ── HARVEST ──────────────────────────────────────────────
        if intent == INTENT_HARVEST:
            _HARVEST_DATA = {
                "wheat":     ("Mar-Apr", "अप्रैल — जब दाना कड़ा हो, नमी 20% से कम", "45 q/ha", "Combine harvester"),
                "rice":      ("Sep-Oct", "सितंबर-अक्टूबर — 80% दाने सुनहरे हों, नमी 18-20%", "40 q/ha", "Paddy thresher"),
                "maize":     ("Sep-Oct", "अक्टूबर — भुट्टा सूखा, नमी 25% से कम", "35 q/ha", "Maize sheller"),
                "mustard":   ("Feb-Mar", "फरवरी-मार्च — फलियां सुनहरी-भूरी हों, 80% पकी हों", "15 q/ha", "Combine/manual"),
                "soybean":   ("Oct", "अक्टूबर — फलियां भूरी-पीली, पत्तियां झड़ चुकी हों", "20 q/ha", "Combine/thresher"),
                "gram":      ("Mar-Apr", "मार्च-अप्रैल — फलियां सूखी, दाने मजबूत", "12 q/ha", "Manual/thresher"),
                "cotton":    ("Oct-Jan", "अक्टूबर से जनवरी — 3-4 picking", "20 q/ha (lint)", "Manual picking"),
                "potato":    ("Jan-Mar", "जनवरी-मार्च — पत्तियां पीली होने पर", "200-250 q/ha", "Manual/tractor"),
                "sugarcane": ("Nov-Mar", "नवंबर-मार्च — 12 महीने बाद", "700-800 q/ha", "Manual/harvester"),
            }
            crop_id = crops[0].get("id", "").lower() if crops else None
            if not crop_id:
                q_l = query.lower()
                for k in _HARVEST_DATA:
                    if k in q_l: crop_id = k; break
            crop_name_display = crops[0]["name"] if crops else (crop_id.title() if crop_id else "")

            if crop_id and crop_id in _HARVEST_DATA:
                hw, signs_hi, exp_yield, equipment = _HARVEST_DATA[crop_id]
                body = {
                    "hi": (
                        f"🌾 **{crop_name_display} की कटाई — {loc}**\n\n"
                        f"🗓️ **कटाई का समय:** {hw}\n"
                        f"✅ **पकने के संकेत:** {signs_hi}\n"
                        f"📦 **अनुमानित उपज:** {exp_yield}\n"
                        f"🚜 **उपकरण:** {equipment}\n\n"
                        f"**कटाई के बाद:**\n"
                        f"• तुरंत सुखाएं — नमी 12-14% तक\n"
                        f"• साफ सुथरे बोरे में भंडारण करें\n"
                        f"• मंडी में बेचने से पहले भाव चेक करें — agmarknet.gov.in\n\n"
                        f"💡 अभी का मौसम: {temp}°C — "
                        + ("कटाई के लिए ठीक" if temp and float(temp) < 35 else "बारिश/तेज धूप से फसल बचाएं")
                        + f"\n\n📞 ICAR: 1800-180-1551"
                    ),
                    "en": (
                        f"🌾 **{crop_name_display} Harvest — {loc}**\n\n"
                        f"🗓️ **Harvest window:** {hw}\n"
                        f"✅ **Maturity signs:** {signs_hi}\n"
                        f"📦 **Expected yield:** {exp_yield}\n"
                        f"🚜 **Equipment:** {equipment}\n\n"
                        f"**Post-harvest:**\n"
                        f"• Dry immediately to 12-14% moisture\n"
                        f"• Store in clean gunny bags\n"
                        f"• Check prices at agmarknet.gov.in before selling\n\n"
                        f"Current weather: {temp}°C\n📞 ICAR: 1800-180-1551"
                    ),
                }.get(lang, f"{crop_name_display}: harvest {hw}. Expected {exp_yield}. Equipment: {equipment}.")
            else:
                body = {
                    "hi": (
                        f"🌾 **फसल कटाई कैलेंडर — {loc}**\n\n"
                        f"• गेहूँ: मार्च-अप्रैल | धान: सितंबर-अक्टूबर\n"
                        f"• मक्का: अक्टूबर | सरसों: फरवरी-मार्च\n"
                        f"• सोयाबीन: अक्टूबर | चना: मार्च-अप्रैल\n"
                        f"• कपास: अक्टूबर-जनवरी (3-4 picking)\n"
                        f"• आलू: जनवरी-मार्च | गन्ना: नवंबर-मार्च\n\n"
                        f"📞 ICAR: 1800-180-1551"
                    ),
                    "en": (
                        f"🌾 **Harvest Calendar — {loc}**\n\n"
                        f"• Wheat: Mar-Apr | Rice: Sep-Oct | Maize: Oct\n"
                        f"• Mustard: Feb-Mar | Soybean: Oct | Gram: Mar-Apr\n"
                        f"• Cotton: Oct-Jan (3-4 picks) | Potato: Jan-Mar\n"
                        f"• Sugarcane: Nov-Mar\n\n📞 ICAR: 1800-180-1551"
                    ),
                }.get(lang, "Harvest: Wheat(Mar-Apr), Rice(Sep-Oct), Maize(Oct), Mustard(Feb-Mar).")
            return alert_prefix + body

        # ── STORAGE ──────────────────────────────────────────────
        if intent == INTENT_STORAGE:
            _STORAGE_DATA = {
                "wheat":  ("12-14%", "18-24 महीने", "Aluminum phosphide 3g/quintal — घुन नियंत्रण"),
                "rice":   ("12-14%", "12-18 महीने", "Silica gel packets + Neem leaves layer"),
                "maize":  ("12-13%", "6-12 महीने", "Cob को अच्छे से सुखाएं — aflatoxin से बचें"),
                "mustard":("6-8%",  "12-18 महीने", "Dry cool place, avoid sunlight"),
                "potato": ("85-90% RH, 3-5°C", "4-6 महीने (cold storage)", "CIPC sprout inhibitor"),
                "gram":   ("8-10%", "18-24 महीने", "Neem oil 5ml/kg grain coating"),
                "soybean":("11-13%","12 महीने",    "Metal bin / HDPE bag, avoid moisture"),
            }
            crop_id = crops[0].get("id", "").lower() if crops else None
            if not crop_id:
                q_l = query.lower()
                for k in _STORAGE_DATA:
                    if k in q_l: crop_id = k; break

            crop_name_display = crops[0]["name"] if crops else (crop_id.title() if crop_id else "")
            if crop_id and crop_id in _STORAGE_DATA:
                moisture, shelf_life, pest_ctrl = _STORAGE_DATA[crop_id]
                body = {
                    "hi": (
                        f"🏪 **{crop_name_display} भंडारण — {loc}**\n\n"
                        f"💧 **भंडारण के लिए नमी:** {moisture}\n"
                        f"⏰ **शेल्फ लाइफ:** {shelf_life}\n"
                        f"🐛 **कीट नियंत्रण:** {pest_ctrl}\n\n"
                        f"**सुरक्षित भंडारण टिप्स:**\n"
                        f"• साफ, सूखी जगह — ज़मीन से 15cm ऊपर रखें\n"
                        f"• HDPE बैग या धातु बिन का उपयोग करें\n"
                        f"• नियमित जाँच — घुन, फफूंदी की निशानी\n"
                        f"• eNAM पर भाव देखकर सही समय पर बेचें\n\n"
                        f"📞 WDRA (भंडारण): 1800-425-9110 | eNAM: 1800-270-0224"
                    ),
                    "en": (
                        f"🏪 **{crop_name_display} Storage — {loc}**\n\n"
                        f"💧 **Safe moisture content:** {moisture}\n"
                        f"⏰ **Shelf life:** {shelf_life}\n"
                        f"🐛 **Pest control:** {pest_ctrl}\n\n"
                        f"**Storage tips:**\n"
                        f"• Clean dry place — keep 15cm off ground\n"
                        f"• Use HDPE bags or metal bins (not jute)\n"
                        f"• Check regularly for weevils/mold\n"
                        f"• Track eNAM prices, sell at peak\n\n"
                        f"📞 WDRA: 1800-425-9110 | eNAM: 1800-270-0224"
                    ),
                }.get(lang, f"{crop_name_display}: store at {moisture} moisture. Shelf life {shelf_life}.")
            else:
                body = {
                    "hi": (
                        f"🏪 **फसल भंडारण गाइड**\n\n"
                        f"• अनाज: 12-14% नमी पर सुखाएं\n"
                        f"• सब्जियां: 3-5°C cold storage\n"
                        f"• घुन रोकें: Aluminium Phosphide 3g/quintal\n"
                        f"• HDPE बैग सबसे सुरक्षित — जूट से बेहतर\n"
                        f"• एग्री warehousing: NWR/eNAM\n\n"
                        f"📞 WDRA: 1800-425-9110"
                    ),
                    "en": (
                        f"🏪 **Crop Storage Guide**\n\n"
                        f"• Grains: dry to 12-14% moisture\n"
                        f"• Vegetables: 3-5°C cold storage\n"
                        f"• Pest control: Aluminium Phosphide 3g/quintal\n"
                        f"• HDPE bags > jute bags for safety\n"
                        f"• NWR/eNAM for warehouse receipts\n\n"
                        f"📞 WDRA: 1800-425-9110"
                    ),
                }.get(lang, "Storage: dry to 12-14% moisture. HDPE bags. Check for weevils regularly.")
            return alert_prefix + body

        # ── ORGANIC FARMING ──────────────────────────────────────
        if intent == INTENT_ORGANIC:
            crop_hint = f" for {crops[0]['name']}" if crops else ""
            body = {
                "hi": (
                    f"🌿 **जैविक खेती{crop_hint} — {loc}**\n\n"
                    f"**जैविक खाद (घर पर बनाएं):**\n"
                    f"• **वर्मीकम्पोस्ट:** 30-40 दिन | 5-10 टन/हे. | ₹2000-3000/टन बचत\n"
                    f"• **जीवामृत:** 200L पानी + 10kg गोबर + 2kg बेसन + 2kg गुड़ + 2L गोमूत्र — 48 घंटे\n"
                    f"• **FYM (गोबर खाद):** 10-15 टन/हे. — बुवाई से 15-20 दिन पहले\n\n"
                    f"**जैविक कीट नियंत्रण:**\n"
                    f"• नीम तेल 5ml/L — माहू, सफेद मक्खी\n"
                    f"• Trichoderma viride 2.5kg/ha — जड़ सड़न\n"
                    f"• Beauveria bassiana — Stem borer, थ्रिप्स\n"
                    f"• पीला sticky trap — सफेद मक्खी monitor\n\n"
                    f"**प्रमाणन:**\n"
                    f"• PGS India (Participatory Guarantee System) — free, 3 साल\n"
                    f"• NPOP — export के लिए | APEDA: 1800-425-9111\n\n"
                    f"💡 जैविक प्रीमियम: 20-50% अधिक दाम — Big Basket, Organic India\n"
                    f"📞 ICAR-NIAP: 011-25843377"
                ),
                "en": (
                    f"🌿 **Organic Farming{crop_hint} — {loc}**\n\n"
                    f"**Organic inputs (make at home):**\n"
                    f"• **Vermicompost:** 30-40 days | 5-10 t/ha | saves ₹2000-3000/t\n"
                    f"• **Jeevamrit:** 200L water + 10kg dung + 2kg chickpea flour + 2kg jaggery + 2L cow urine — 48 hrs\n"
                    f"• **FYM:** 10-15 t/ha — apply 15-20 days before sowing\n\n"
                    f"**Biopesticides:**\n"
                    f"• Neem oil 5ml/L — aphids, whitefly\n"
                    f"• Trichoderma viride 2.5kg/ha — root rot\n"
                    f"• Beauveria bassiana — stem borers, thrips\n"
                    f"• Yellow sticky traps — whitefly monitoring\n\n"
                    f"**Certification:**\n"
                    f"• PGS India — free, 3-year process\n"
                    f"• NPOP — for export | APEDA: 1800-425-9111\n\n"
                    f"💡 Organic premium: 20-50% higher price\n📞 ICAR: 1800-180-1551"
                ),
            }.get(lang, "Organic farming: use vermicompost, jeevamrit, neem oil, Trichoderma. PGS certification free.")
            return alert_prefix + body

        # ── SEED ─────────────────────────────────────────────────
        if intent == INTENT_SEED:
            crop_hint = f" ({crops[0]['name']})" if crops else ""
            crop_id   = crops[0].get("id", "").lower() if crops else ""
            _VARIETY_DATA = {
                "wheat":    "DBW-187, DBW-222 (latest high-yield) | HD-2967 (popular) | Pusa Wheat-1 (heat tolerant)",
                "rice":     "Swarna MTU-7029 (high yield) | BPT-5204 (basmati quality) | Pusa Basmati-1121 | Pusa-44",
                "maize":    "DKC-9144 (hybrid) | Pioneer-30V92 | NK-6240 (FAO-700)",
                "mustard":  "Pusa Bold B-54 (early) | NRCDR-2 (high oil) | RH-749 (disease resistant)",
                "soybean":  "JS-9752 (most popular MP/Maharashtra) | NRC-7 | JS-335",
                "gram":     "JG-11 (widely adapted) | GNG-1958 (Rajasthan) | HC-5 (Haryana)",
                "cotton":   "Bunny BG-II | Jadoo BG-II | RCH-2 BG-II (Bt hybrids)",
                "tomato":   "Pusa Rohini | Arka Rakshak | Pusa Hybrid-1",
                "onion":    "Pusa Red | Bhima Super | N-2-4-1 (Maharashtra)",
                "potato":   "Kufri Jyoti | Kufri Sinduri | Kufri Chipsona-1",
            }
            varieties_text = _VARIETY_DATA.get(crop_id, "ICAR/KVK से अनुशंसित बीज उपयोग करें")
            body = {
                "hi": (
                    f"🌾 **बीज किस्म{crop_hint} — {loc}**\n\n"
                    f"**अनुशंसित किस्में (ICAR):**\n{varieties_text}\n\n"
                    f"**प्रमाणित बीज कहाँ से लें:**\n"
                    f"• NSC (National Seeds Corporation): seedsportal.nscindia.net\n"
                    f"• IFFCO: iffco.in | KRIBHCO: kribhco.net\n"
                    f"• ई-नाम/CSC केंद्र — नजदीकी KVK\n\n"
                    f"**बीज उपचार जरूरी:**\n"
                    f"• Thiram 2.5g/kg — फफूंद नाशक\n"
                    f"• Imidacloprid 600FS 4ml/kg — कीट नाशक\n"
                    f"• Rhizobium culture — दलहनी फसलें\n\n"
                    f"📞 NSC Helpline: 1800-180-7515"
                ),
                "en": (
                    f"🌾 **Seed Varieties{crop_hint} — {loc}**\n\n"
                    f"**ICAR recommended varieties:**\n{varieties_text}\n\n"
                    f"**Where to buy certified seed:**\n"
                    f"• NSC: seedsportal.nscindia.net\n"
                    f"• IFFCO: iffco.in | KRIBHCO: kribhco.net\n"
                    f"• Nearest KVK or CSC centre\n\n"
                    f"**Seed treatment (essential):**\n"
                    f"• Thiram 2.5g/kg — fungal protection\n"
                    f"• Imidacloprid 4ml/kg — insect protection\n"
                    f"• Rhizobium culture — for all pulses\n\n"
                    f"📞 NSC Helpline: 1800-180-7515"
                ),
            }.get(lang, f"Seeds: {varieties_text}. Buy from NSC/IFFCO. Treat with Thiram+Imidacloprid.")
            return alert_prefix + body

        # ── INSURANCE ────────────────────────────────────────────
        if intent == INTENT_INSURANCE:
            body = {
                "hi": (
                    f"🛡️ **फसल बीमा — PMFBY — {loc}**\n\n"
                    f"**प्रीमियम दरें:**\n"
                    f"• खरीफ: **2%** | रबी: **1.5%** | बागवानी: **5%**\n"
                    f"• बाकी प्रीमियम: 50% केंद्र + 50% राज्य सरकार\n\n"
                    f"**क्लेम कैसे करें:**\n"
                    f"1. नुकसान के **72 घंटे** में बैंक/CSC को सूचित करें\n"
                    f"2. Crop Insurance App पर फोटो अपलोड करें\n"
                    f"3. Land Record/Khasra Number तैयार रखें\n"
                    f"4. नुकसान का मुआवजा: 30-60 दिन में\n\n"
                    f"**ऑनलाइन आवेदन:**\n"
                    f"• pmfby.gov.in | Crop Insurance App (Google Play)\n"
                    f"• CSC Centre | नजदीकी बैंक\n\n"
                    f"📞 PMFBY Helpline: **14447** | Crop Insurance: **1800-200-7710**"
                ),
                "en": (
                    f"🛡️ **Crop Insurance — PMFBY — {loc}**\n\n"
                    f"**Premium rates:**\n"
                    f"• Kharif: **2%** | Rabi: **1.5%** | Horticulture: **5%**\n"
                    f"• Balance: 50% Central + 50% State govt\n\n"
                    f"**How to claim:**\n"
                    f"1. Notify bank/CSC within **72 hours** of crop loss\n"
                    f"2. Upload photos on Crop Insurance App\n"
                    f"3. Keep Land Record/Khasra Number ready\n"
                    f"4. Compensation within 30-60 days\n\n"
                    f"**Apply online:**\n"
                    f"• pmfby.gov.in | Crop Insurance App (Play Store)\n"
                    f"• CSC centre | Nearest bank\n\n"
                    f"📞 PMFBY Helpline: **14447** | 1800-200-7710"
                ),
            }.get(lang, "PMFBY: 2% Kharif, 1.5% Rabi. Claim within 72 hrs at pmfby.gov.in or call 14447.")
            return alert_prefix + body

        # ── PROFIT CALCULATION ───────────────────────────────────
        if intent == INTENT_PROFIT_CALC:
            crop_id   = crops[0].get("id", "").lower() if crops else None
            crop_name_display = crops[0]["name"] if crops else ""
            # Use comprehensive DB data if available
            _PROFIT_TABLE = {
                "wheat":     (25000, 45, 2275, "Rs.77,000/ha"),
                "rice":      (30000, 40, 2300, "Rs.62,000/ha"),
                "maize":     (22000, 35, 2090, "Rs.51,000/ha"),
                "mustard":   (18000, 15, 5650, "Rs.66,750/ha"),
                "gram":      (20000, 12, 5440, "Rs.45,280/ha"),
                "soybean":   (22000, 20, 4892, "Rs.75,840/ha"),
                "cotton":    (35000, 20, 7121, "Rs.107,420/ha (lint+seed)"),
                "tomato":    (80000, 400,0,    "Rs.3,20,000/ha (peak price)"),
                "potato":    (55000, 250,0,    "Rs.1,20,000/ha"),
                "sugarcane": (90000, 700,340,  "Rs.1,48,000/ha"),
            }
            if crop_id and crop_id in _PROFIT_TABLE:
                cost, yld, msp_val, net = _PROFIT_TABLE[crop_id]
                gross = yld * msp_val if msp_val else 0
                body = {
                    "hi": (
                        f"💰 **{crop_name_display} लाभ-लागत विश्लेषण — {loc}**\n\n"
                        f"**इनपुट लागत:** ₹{cost:,}/हे.\n"
                        f"  • बीज + खाद + कीटनाशक + मजदूरी + सिंचाई\n\n"
                        f"**उपज:** {yld} क्विंटल/हे.\n"
                        f"**MSP 2024-25:** {'₹'+str(msp_val)+'/q' if msp_val else 'MSP नहीं'}\n"
                        f"**Gross Revenue (MSP पर):** {'₹'+str(gross)+'/हे.' if gross else 'N/A'}\n"
                        f"**शुद्ध लाभ:** {net}\n\n"
                        f"💡 **B:C Ratio:** {(gross/cost):.1f}:1 — {'>2.5: उत्कृष्ट' if gross and gross/cost > 2.5 else '>1.5: अच्छा' if gross and gross/cost > 1.5 else 'मध्यम'}\n\n"
                        f"📊 लाइव मंडी भाव: agmarknet.gov.in"
                    ),
                    "en": (
                        f"💰 **{crop_name_display} Profit Analysis — {loc}**\n\n"
                        f"**Input cost:** ₹{cost:,}/ha\n"
                        f"  • Seed + fertiliser + pesticide + labour + irrigation\n\n"
                        f"**Yield:** {yld} q/ha\n"
                        f"**MSP 2024-25:** {'₹'+str(msp_val)+'/q' if msp_val else 'No MSP'}\n"
                        f"**Gross revenue (at MSP):** {'₹'+str(gross)+'/ha' if gross else 'N/A'}\n"
                        f"**Net profit:** {net}\n\n"
                        f"💡 **B:C Ratio:** {(gross/cost):.1f}:1\n\n"
                        f"📊 Live mandi prices: agmarknet.gov.in"
                    ),
                }.get(lang, f"{crop_name_display}: cost ₹{cost}/ha, yield {yld}q/ha, net profit {net}.")
            else:
                body = {
                    "hi": (
                        f"💰 **प्रमुख फसलों का लाभ (प्रति हेक्टेयर)**\n\n"
                        f"| फसल     | लागत    | उपज   | MSP    | शुद्ध लाभ |\n"
                        f"|----------|---------|-------|--------|----------|\n"
                        f"| गेहूँ    | ₹25,000 | 45 q  | ₹2,275 | ₹77,000  |\n"
                        f"| सरसों   | ₹18,000 | 15 q  | ₹5,650 | ₹67,000  |\n"
                        f"| चना     | ₹20,000 | 12 q  | ₹5,440 | ₹45,000  |\n"
                        f"| सोयाबीन | ₹22,000 | 20 q  | ₹4,892 | ₹76,000  |\n"
                        f"| मक्का   | ₹22,000 | 35 q  | ₹2,090 | ₹51,000  |\n\n"
                        f"*1 हेक्टेयर = 2.47 एकड़ = 6.17 बीघा (UP)*\n"
                        f"📞 ICAR: 1800-180-1551"
                    ),
                    "en": (
                        f"💰 **Crop Profit Summary (per hectare)**\n\n"
                        f"| Crop    | Cost    | Yield | MSP    | Net Profit |\n"
                        f"|---------|---------|-------|--------|------------|\n"
                        f"| Wheat   | ₹25,000 | 45 q  | ₹2,275 | ₹77,000    |\n"
                        f"| Mustard | ₹18,000 | 15 q  | ₹5,650 | ₹67,000    |\n"
                        f"| Gram    | ₹20,000 | 12 q  | ₹5,440 | ₹45,000    |\n"
                        f"| Soybean | ₹22,000 | 20 q  | ₹4,892 | ₹76,000    |\n"
                        f"| Maize   | ₹22,000 | 35 q  | ₹2,090 | ₹51,000    |\n\n"
                        f"*1 ha = 2.47 acres = 6.17 bigha (UP standard)*\n"
                        f"📞 ICAR: 1800-180-1551"
                    ),
                }.get(lang, "Profit per ha: Wheat ₹77k, Mustard ₹67k, Gram ₹45k, Soybean ₹76k, Maize ₹51k.")
            return alert_prefix + body

        # ── SOIL ─────────────────────────────────────────────────
        if intent == INTENT_SOIL:
            # State → dominant soil type mapping
            _STATE_SOIL = {
                "Uttar Pradesh":    ("Alluvial (दोमट)", "उचित — अधिकांश फसलें", "NPK+Zinc की कमी आम"),
                "Punjab":           ("Alluvial (दोमट)", "उत्कृष्ट — गेहूँ/धान", "Zinc+Iron कमी, pH 7.5-8.5"),
                "Haryana":          ("Alluvial (दोमट)", "उत्कृष्ट — गेहूँ/सरसों", "Zinc+Sulfur कमी"),
                "Madhya Pradesh":   ("Black/Red Mixed (काली+लाल)", "कपास/सोयाबीन के लिए उत्कृष्ट", "P+Zinc कमी आम"),
                "Maharashtra":      ("Black (काली मिट्टी/Vertisol)", "कपास/गन्ना उत्कृष्ट", "P कमी, pH>8 में"),
                "Rajasthan":        ("Sandy Loam (बलुई दोमट)", "Bajra/Mustard अनुकूल", "N+P+Zinc सब कम"),
                "Bihar":            ("Alluvial (जलोढ़)", "धान/गेहूँ उत्कृष्ट", "Zinc+Boron कमी"),
                "West Bengal":      ("Alluvial+Laterite", "धान के लिए अच्छा", "Iron toxicity, pH<5.5"),
                "Karnataka":        ("Red (लाल मिट्टी)", "Ragi/Groundnut/Coffee", "N+P+K सब कम"),
                "Andhra Pradesh":   ("Red+Black Mixed", "Cotton/Rice", "N+P+Zinc"),
                "Tamil Nadu":       ("Red+Black", "Rice/Sugarcane", "Zinc+Boron"),
                "Gujarat":          ("Black+Sandy Mixed", "Cotton/Groundnut", "P+Zinc, अम्लीयता"),
                "Kerala":           ("Laterite (लेटराइट)", "Coconut/Spices", "अत्यधिक अम्लीय, P fixation"),
            }
            state = ctx.state or ""
            soil_info = _STATE_SOIL.get(state)
            if not soil_info:
                # Try partial match
                for st, info in _STATE_SOIL.items():
                    if st.lower() in (state or "").lower():
                        soil_info = info
                        break

            if soil_info:
                soil_type, suitability, deficiency = soil_info
                body = {
                    "hi": (
                        f"🌱 **मिट्टी जानकारी — {loc}**\n\n"
                        f"🏔️ **मिट्टी का प्रकार:** {soil_type}\n"
                        f"✅ **उपयुक्तता:** {suitability}\n"
                        f"⚠️ **आम कमियाँ:** {deficiency}\n\n"
                        f"**मिट्टी जांच कैसे करें:**\n"
                        f"• Soil Health Card (SHC): soilhealth.dac.gov.in\n"
                        f"• नजदीकी KVK या कृषि विभाग\n"
                        f"• लागत: ₹0 (सरकारी) | ₹200-500 (प्राइवेट)\n\n"
                        f"**pH सुधार:**\n"
                        f"• अम्लीय (pH<6.5): चूना (Lime) 2-3 t/ha\n"
                        f"• क्षारीय (pH>8): Gypsum 5-10 t/ha\n"
                        f"• सामान्य (6.5-7.5): सर्वोत्तम — Zinc 25 kg/ha\n\n"
                        f"📞 ICAR-NAAS: 011-25843377 | KVK: 1800-180-1551"
                    ),
                    "en": (
                        f"🌱 **Soil Information — {loc}**\n\n"
                        f"🏔️ **Dominant soil type:** {soil_type}\n"
                        f"✅ **Best suited for:** {suitability}\n"
                        f"⚠️ **Common deficiencies:** {deficiency}\n\n"
                        f"**How to get soil tested:**\n"
                        f"• Soil Health Card: soilhealth.dac.gov.in\n"
                        f"• Nearest KVK or Agriculture Dept\n"
                        f"• Cost: Free (govt) | ₹200-500 (private)\n\n"
                        f"**pH correction:**\n"
                        f"• Acidic (pH<6.5): Lime 2-3 t/ha\n"
                        f"• Alkaline (pH>8): Gypsum 5-10 t/ha\n"
                        f"• Ideal (6.5-7.5): Add Zinc 25 kg/ha\n\n"
                        f"📞 ICAR: 1800-180-1551"
                    ),
                }.get(lang, f"Soil in {loc}: {soil_type}. Common deficiency: {deficiency}.")
            else:
                body = {
                    "hi": (
                        f"🌱 **मिट्टी जांच गाइड — {loc}**\n\n"
                        f"**भारत की प्रमुख मिट्टियाँ:**\n"
                        f"• जलोढ़ (Alluvial): UP/Punjab/Bihar — गेहूँ/धान\n"
                        f"• काली मिट्टी (Black/Vertisol): MP/Maharashtra — कपास\n"
                        f"• लाल मिट्टी (Red): Karnataka/AP — रागी/मूँगफली\n"
                        f"• बलुई (Sandy): Rajasthan — बाजरा/मोठ\n"
                        f"• लेटराइट: Kerala/WB — चाय/रबर\n\n"
                        f"**Soil Health Card बनवाएं:**\n"
                        f"• soilhealth.dac.gov.in\n"
                        f"• 3 साल में एक बार जरूरी\n\n"
                        f"📞 ICAR: 1800-180-1551"
                    ),
                    "en": (
                        f"🌱 **Soil Testing Guide — {loc}**\n\n"
                        f"**India's major soil types:**\n"
                        f"• Alluvial: UP/Punjab/Bihar — Wheat/Rice\n"
                        f"• Black (Vertisol): MP/Maharashtra — Cotton\n"
                        f"• Red: Karnataka/AP — Finger millet/Groundnut\n"
                        f"• Sandy: Rajasthan — Bajra/Moth bean\n"
                        f"• Laterite: Kerala/WB — Tea/Rubber\n\n"
                        f"**Get Soil Health Card:**\n"
                        f"• soilhealth.dac.gov.in | Free every 3 years\n\n"
                        f"📞 ICAR: 1800-180-1551"
                    ),
                }.get(lang, "Soil: get Soil Health Card free at soilhealth.dac.gov.in or nearest KVK.")
            return alert_prefix + body

        # ── GENERAL / FOLLOW-UP ──────────────────────────────────
        # Smart general response: use available context (crops, weather, season)
        # to give a useful answer rather than a blank "ask me anything" response
        lines_out: List[str] = []
        season_now = _current_season()

        if temp != "—":
            # Include farming advice in the right language
            fa_note = f" — {farming_advice}" if farming_advice else ""
            lines_out.append(
                f"🌡️ **{loc}** मौसम: **{temp}°C**, {cond}{fa_note}"
                if lang == "hi" else
                f"🌡️ **{loc}** weather: **{temp}°C**, {cond}{fa_note}"
            )

        if crops:
            for crop in crops[:2]:
                msp_val = crop.get("msp") or MSP_2024_25.get(crop["id"], 0)
                crop_name = crop.get("name", "")
                crop_line = f"• **{crop_name}**"
                if msp_val:
                    crop_line += f" — MSP ₹{msp_val}/q"
                lines_out.append(crop_line)

            # If crop was mentioned without a specific question, proactively
            # suggest the most relevant follow-up intents
            crop_name = crops[0].get("name", "")
            lines_out.append(
                f"\n**{crop_name} के बारे में क्या जानना है?**\n"
                f"• सिंचाई — कब, कितना पानी?\n"
                f"• खाद — कब और कितनी?\n"
                f"• रोग — लक्षण और दवाई\n"
                f"• बुवाई/कटाई — समय और किस्में\n"
                f"• मंडी भाव — आज का भाव"
                if lang == "hi" else
                f"\n**What would you like to know about {crop_name}?**\n"
                f"• Irrigation — when and how much?\n"
                f"• Fertiliser — schedule and dose?\n"
                f"• Disease — symptoms and treatment?\n"
                f"• Sowing/Harvest — timing and varieties?\n"
                f"• Mandi price — today's rate?"
            )
        else:
            # No crop detected — give a season-appropriate suggestion
            rec_lines = [l for l in context_block.splitlines() if "suitability" in l]
            if rec_lines:
                lines_out.append("🌾 **आपके क्षेत्र के लिए उपयुक्त फसलें:**"
                                  if lang == "hi" else "🌾 **Suitable crops for your area:**")
                for l in rec_lines[:3]:
                    m_crop = re.match(r"\s+([^:]+):", l)
                    if m_crop:
                        lines_out.append(f"  • {m_crop.group(1).strip()}")

            lines_out.append(
                f"\n💬 **मैं इन विषयों में मदद कर सकता हूँ ({season_now}):**\n"
                f"🌱 बुवाई सलाह | 💧 सिंचाई | 🌱 खाद\n"
                f"🐛 कीट-रोग | 💰 मंडी भाव | 🏛️ योजनाएं\n"
                f"🌾 कटाई | 🏪 भंडारण | 📊 लाभ-लागत\n"
                f"📞 1800-180-1551"
                if lang == "hi" else
                f"\n💬 **I can help with ({season_now}):**\n"
                f"🌱 Sowing guide | 💧 Irrigation | 🌱 Fertiliser\n"
                f"🐛 Pest/disease | 💰 Mandi prices | 🏛️ Schemes\n"
                f"🌾 Harvest | 🏪 Storage | 📊 Profit-cost\n"
                f"📞 1800-180-1551"
            )

        return alert_prefix + "\n".join(lines_out)

    def _empty_response(self, lang: str) -> str:
        return {
            "hi": "कृपया अपना सवाल लिखें। मैं फसल, मौसम, मंडी भाव, योजना — सब बता सकता हूँ।",
            "en": "Please type your question. I can help with crops, weather, mandi prices, and schemes.",
            "ta": "தயவுசெய்து உங்கள் கேள்வியை தட்டச்சு செய்யுங்கள்.",
            "te": "దయచేసి మీ ప్రశ్న రాయండి.",
            "mr": "कृपया आपला प्रश्न लिहा.",
            "bn": "অনুগ্রহ করে আপনার প্রশ্ন লিখুন।",
            "gu": "કૃपા કરી તમારો પ્રশ્ন ટાઈپ કरો.",
            "kn": "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಬರೆಯಿರಿ.",
            "ml": "ദയവായി നിങ്ങളുടെ ചോദ്യം ടൈپ് ചെയ്യുക.",
            "pa": "ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ ਸਵਾਲ ਲਿਖੋ।",
        }.get(lang, "Please type your question.")

    # ── Crop suggestion cards ─────────────────────────────────────

    def _crop_suggestions_for_intent(
        self,
        ctx: LocationContext,
        intent: str,
        crops: List[Dict[str, Any]],
        lang: str = "hi",
    ) -> List[Dict[str, Any]]:
        if intent == INTENT_CROP_RECOMMENDATION:
            try:
                rec = crop_recommendation_engine.recommend_from_context(ctx, language=lang)
                return [
                    {
                        "type": "crop_recommendation",
                        "crop":  r.get("crop_name"),
                        "hindi": r.get("crop_name_hindi"),
                        "local": r.get("crop_name_local"),
                        "score": r.get("suitability_score"),
                        "reason": r.get("reason_hindi") or r.get("reason"),
                        "profit": r.get("profit_per_hectare", 0),
                        "msp":    r.get("msp_per_quintal", 0),
                    }
                    for r in (rec.get("recommendations") or [])[:4]
                ]
            except Exception:
                pass

        if intent == INTENT_MARKET_PRICE and crops:
            out = []
            for c in crops[:3]:
                try:
                    pr = market_service.get_prices(
                        ctx.query_label,
                        crop=c["name"],
                        lat=ctx.latitude,
                        lon=ctx.longitude,
                        state=ctx.state or None,
                    )
                    row = (pr.get("top_crops") or [{}])[0]
                    out.append({
                        "type":        "market_price",
                        "crop":        c["name"],
                        "modal_price": row.get("modal_price"),
                        "msp":         row.get("msp"),
                        "mandi":       row.get("mandi_name"),
                        "live":        pr.get("is_live", False),
                    })
                except Exception:
                    out.append({"type": "market_price", "crop": c["name"],
                                "note": "Check agmarknet.gov.in"})
            return out

        # Default: staple crop quick links
        if intent in (INTENT_GENERAL, INTENT_GREETING):
            return [
                {"type": "quick_crop", "crop": crop_catalog.get(cid)["name"], "id": cid}
                for cid in STAPLE_FOR_CHAT[:4]
                if crop_catalog.get(cid)
            ]

        return []


# Module-level singleton
chat_intelligence_service = ChatIntelligenceService()
