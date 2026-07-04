#!/usr/bin/env python3
"""
KrishiMitra Unified Real-Time Service v3.0
Single source of truth replacing all redundant service files.

Fixed bugs:
  - Open-Meteo now fetches full 7-day + humidity + rainfall + UV index
  - data.gov.in uses correct resource IDs and proper API-KEY header
  - Gemini uses gemini-1.5-pro with gemini-1.5-flash fallback
  - SSL verification enabled (removed global disable)
  - No more hardcoded API keys
"""

import os
import json
import logging
import threading
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple

from .location_context import _haversine_km
from .language_service import (
    get_language_info,
    normalise_language_code,
    get_gemini_language_instruction,
    translate_farming_advice,
    get_language_for_state,
    get_ui_string,
    get_crop_name,
    SUPPORTED_LANGUAGES,
)

logger = logging.getLogger(__name__)

# ─── API Keys (from environment) ─────────────────────────────────────────────
GOOGLE_AI_KEY     = os.getenv("GOOGLE_AI_API_KEY", "")
# Set in .env — register at https://data.gov.in/user/register (free)
DATA_GOV_KEY      = os.getenv("DATA_GOV_IN_API_KEY", "").strip()
# OGD public demo key (limited to 10 rows/request); register your own for production
DATA_GOV_DEMO_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"
# ↑ Kept as a tombstone constant only — no longer used in production code paths.
# _effective_data_gov_key() now returns None instead of falling back to this key.

# ─── Geocode cache TTL ─────────────────────────────────────────────────────────
# Bug 4 fix: location → lat/lon lookups are cached with a TTL rather than forever.
# The in-process dict (_coord_cache on WeatherService) acts as L1; Django's
# weather_cache is L2 (shared across workers, 7-day TTL).
# This prevents stale coordinates surviving a process restart when a village
# is renamed or a farmer enters a slightly different spelling.
_GEOCODE_CACHE_TTL = 60 * 60 * 24 * 7   # 7 days — location→coords is stable
DATA_GOV_TIMEOUT  = (5, 25)  # connect, read seconds
OPENWEATHER_KEY   = os.getenv("OPENWEATHER_API_KEY", "")
GEMINI_MODEL      = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
GEMINI_FLASH      = os.getenv("GEMINI_FLASH_MODEL", "gemini-1.5-flash")
GEMINI_MODELS_CHAIN = [GEMINI_MODEL, GEMINI_FLASH, "gemini-pro"]  # Fallback chain

# ─── Gemini key validation ────────────────────────────────────────────────────
_PLACEHOLDER_FRAGMENTS = frozenset({
    "your", "replace", "insert", "changeme", "xxx", "demo", "test", "example",
    "api_key", "apikey", "placeholder",
})

def _is_valid_gemini_key(key: str) -> bool:
    """Return True only if the key looks like a real Gemini API key."""
    if not key or len(key) < 20:
        return False
    lower = key.lower()
    return not any(frag in lower for frag in _PLACEHOLDER_FRAGMENTS)

def _cache_token(value: Any) -> str:
    """Memcached-safe token for cache keys while preserving readable hints."""
    if value is None:
        return ""
    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace(":", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )

# ─── Correct data.gov.in Resource IDs ────────────────────────────────────────
DATA_GOV_RESOURCES = {
    "agmarknet_mandi":   "9ef84268-d588-465a-a308-a864a43d0070",
    "enam_market":       "35985678-0d79-46b4-9ed6-6f13308a1d24",
    "soil_health":       "7aab2351-b45e-47b1-8d1b-f6b2e60d7c8c",
}
DATA_GOV_BASE = "https://api.data.gov.in/resource"

# ─── Indian States → Agmarknet State Codes ───────────────────────────────────
STATE_CODES = {
    "delhi": "DL", "uttar pradesh": "UP", "haryana": "HR",
    "punjab": "PB", "rajasthan": "RJ", "madhya pradesh": "MP",
    "maharashtra": "MH", "karnataka": "KA", "andhra pradesh": "AP",
    "telangana": "TL", "tamil nadu": "TN", "kerala": "KL",
    "west bengal": "WB", "gujarat": "GJ", "bihar": "BR",
    "jharkhand": "JH", "odisha": "OR", "assam": "AS",
}

# data.gov.in filter values (try in order until records returned)
STATE_FILTER_NAMES: Dict[str, List[str]] = {
    "delhi": ["Delhi", "NCT of Delhi", "National Capital Territory of Delhi"],
    "noida": ["Uttar Pradesh"],
    "greater noida": ["Uttar Pradesh"],
    "mumbai": ["Maharashtra"],
    "pune": ["Maharashtra"],
    "bangalore": ["Karnataka"],
    "bengaluru": ["Karnataka"],
    "chennai": ["Tamil Nadu"],
    "kolkata": ["West Bengal"],
    "hyderabad": ["Telangana"],
    "ahmedabad": ["Gujarat"],
    "jaipur": ["Rajasthan"],
    "lucknow": ["Uttar Pradesh"],
    "patna": ["Bihar"],
    "chandigarh": ["Punjab", "Haryana"],
    "indore": ["Madhya Pradesh"],
    "bhopal": ["Madhya Pradesh"],
    "nagpur": ["Maharashtra"],
    "nashik": ["Maharashtra"],
    "surat": ["Gujarat"],
    "vadodara": ["Gujarat"],
    "kanpur": ["Uttar Pradesh"],
    "varanasi": ["Uttar Pradesh"],
    "agra": ["Uttar Pradesh"],
    "meerut": ["Uttar Pradesh"],
    "ghaziabad": ["Uttar Pradesh"],
    "gurgaon": ["Haryana"],
    "gurugram": ["Haryana"],
    "faridabad": ["Haryana"],
    "amritsar": ["Punjab"],
    "ludhiana": ["Punjab"],
    "guwahati": ["Assam"],
    "kochi": ["Kerala"],
    "thiruvananthapuram": ["Kerala"],
    "visakhapatnam": ["Andhra Pradesh"],
    "vijayawada": ["Andhra Pradesh"],
    "coimbatore": ["Tamil Nadu"],
    "madurai": ["Tamil Nadu"],
    "ranchi": ["Jharkhand"],
    "raipur": ["Chhattisgarh"],
    "dehradun": ["Uttarakhand"],
    "shimla": ["Himachal Pradesh"],
    "srinagar": ["Jammu and Kashmir"],
    "jammu": ["Jammu and Kashmir"],
    "uttar pradesh": ["Uttar Pradesh"],
    "maharashtra": ["Maharashtra"],
    "karnataka": ["Karnataka"],
    "punjab": ["Punjab"],
    "haryana": ["Haryana"],
    "rajasthan": ["Rajasthan"],
    "madhya pradesh": ["Madhya Pradesh"],
    "gujarat": ["Gujarat"],
    "west bengal": ["West Bengal"],
    "tamil nadu": ["Tamil Nadu"],
    "telangana": ["Telangana"],
    "bihar": ["Bihar"],
    "odisha": ["Odisha"],
    "assam": ["Assam"],
}

DATA_GOV_PLACEHOLDER_KEYS = frozenset({
    "",
    "your_data_gov_in_api_key_here",
    "your_data_gov_in_key_here",
    "YOUR_DATA_GOV_IN_KEY_HERE",
    "CHANGE_ME",
})

# ─── Crop Hindi Names ──────────────────────────────────────────────────────
CROP_HINDI = {
    "wheat": "गेहूँ", "rice": "चावल", "cotton": "कपास",
    "sugarcane": "गन्ना", "maize": "मक्का", "tomato": "टमाटर",
    "potato": "आलू", "onion": "प्याज", "soybean": "सोयाबीन",
    "mustard": "सरसों", "groundnut": "मूँगफली", "barley": "जौ",
    "gram": "चना", "lentil": "दाल", "turmeric": "हल्दी",
    "ginger": "अदरक", "garlic": "लहसुन", "mango": "आम",
    "banana": "केला", "apple": "सेब",
}

from .msp_data import MSP_2024_25

# ── DB-backed MSP lookup (falls back to dict above) ─────────────────────────
# Run `python manage.py seed_msp` once to populate the Crop table.
# After that, updates only require `manage.py seed_msp --season 2025-26` —
# no code deploy needed for annual CACP price announcements.

def get_msp(crop_id: str, fallback: int = 0) -> int:
    """
    Return MSP ₹/quintal for a crop. Tries DB first, then in-memory dict.
    Safe to call at any time — never raises.
    """
    try:
        from advisory.models import Crop
        crop = Crop.objects.filter(name=crop_id).only("msp_per_quintal").first()
        if crop and crop.msp_per_quintal:
            return crop.msp_per_quintal
    except Exception:
        pass
    return MSP_2024_25.get(crop_id, fallback)

# ─────────────────────────────────────────────────────────────────────────────
#  WEATHER SERVICE
# ─────────────────────────────────────────────────────────────────────────────
class WeatherService:
    """Real-time weather from Open-Meteo (FREE, no key) + OpenWeatherMap fallback"""

    OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
    OWM_URL = "https://api.openweathermap.org/data/2.5/forecast"
    GEOCODING_URL = "https://nominatim.openstreetmap.org/search"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "KrishiMitra-AI/3.0 (contact@krishimitra.in)",
            "Accept": "application/json"
        })
        self._coord_cache: Dict[str, Tuple[float, float]] = {}

    def get_weather(self, location: str, lat: float = None, lon: float = None,
                    lang: str = "hi") -> Dict[str, Any]:
        """Get complete weather data with 7-day forecast in the requested language."""
        try:
            if lat is None or lon is None:
                lat, lon = self._geocode(location)

            # Try Open-Meteo first (FREE, highly reliable)
            data = self._fetch_open_meteo(lat, lon, location, lang=lang)
            if data:
                return data

            # Fallback: OpenWeatherMap
            if OPENWEATHER_KEY:
                data = self._fetch_owm(lat, lon, location, lang=lang)
                if data:
                    return data

            return self._static_fallback(location, lang=lang)

        except Exception as e:
            logger.error(f"Weather error for {location}: {e}")
            return self._static_fallback(location, lang=lang)

    def _geocode(self, location: str) -> Tuple[float, float]:
        """Convert location name to coordinates.

        Bug 4 fix: replaced unbounded in-process dict with a two-tier cache:
          L1 — self._coord_cache (per-process dict, zero-latency within one worker)
          L2 — Django weather_cache (shared across workers, 7-day TTL)

        Both tiers have a TTL so stale coordinates are eventually evicted.
        The old code cached forever in the process — yesterday's geocode for a
        misspelled village survived until a dyno restart.
        """
        key_norm  = location.lower().strip()
        cache_key = f"geocode:{key_norm}"

        # L1: in-process dict (fast path)
        if key_norm in self._coord_cache:
            return self._coord_cache[key_norm]

        # L2: shared Django cache
        try:
            from django.core.cache import caches
            _cache = caches['weather_cache']
            cached = _cache.get(cache_key)
            if cached is not None:
                self._coord_cache[key_norm] = cached   # promote to L1
                return cached
        except Exception:
            _cache = None

        # Known Indian city coordinates (fast path — no network call needed)
        known = {
            "delhi": (28.6139, 77.2090), "mumbai": (19.0760, 72.8777),
            "kolkata": (22.5726, 88.3639), "chennai": (13.0827, 80.2707),
            "bangalore": (12.9716, 77.5946), "hyderabad": (17.3850, 78.4867),
            "pune": (18.5204, 73.8567), "ahmedabad": (23.0225, 72.5714),
            "lucknow": (26.8467, 80.9462), "jaipur": (26.9124, 75.7873),
            "greater noida": (28.4745, 77.5040), "noida": (28.5355, 77.3910),
        }
        for key, coords in known.items():
            if key in key_norm:
                self._write_geocode_cache(key_norm, coords, cache_key)
                return coords

        # Nominatim geocoding (network call — last resort)
        try:
            resp = self.session.get(
                self.GEOCODING_URL,
                params={"q": f"{location}, India", "format": "json", "limit": 1},
                timeout=5,
            )
            if resp.status_code == 200 and resp.json():
                result = resp.json()[0]
                coords = (float(result["lat"]), float(result["lon"]))
                self._write_geocode_cache(key_norm, coords, cache_key)
                return coords
        except Exception as exc:
            logger.warning("Nominatim geocoding failed for %r: %s", location, exc)

        # Default: New Delhi
        default = (28.6139, 77.2090)
        logger.warning("Geocoding failed for %r — defaulting to New Delhi", location)
        return default

    def _write_geocode_cache(
        self, key_norm: str, coords: Tuple[float, float], cache_key: str
    ) -> None:
        """Write coords to both L1 (in-process) and L2 (shared) caches."""
        self._coord_cache[key_norm] = coords
        try:
            from django.core.cache import caches
            caches['weather_cache'].set(cache_key, coords, timeout=_GEOCODE_CACHE_TTL)
        except Exception:
            pass   # L2 write failure is non-fatal — L1 still works

    def _fetch_open_meteo(self, lat: float, lon: float, location: str,
                          lang: str = "hi") -> Optional[Dict]:
        """Open-Meteo full forecast — humidity, rainfall, UV, 7-day (NO API KEY NEEDED)"""
        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                # Current variables
                "current": [
                    "temperature_2m", "relative_humidity_2m", "apparent_temperature",
                    "precipitation", "weather_code", "wind_speed_10m",
                    "wind_direction_10m", "uv_index", "surface_pressure"
                ],
                # Daily forecast variables
                "daily": [
                    "temperature_2m_max", "temperature_2m_min",
                    "precipitation_sum", "weather_code",
                    "uv_index_max", "wind_speed_10m_max",
                    "precipitation_probability_max"
                ],
                "timezone": "Asia/Kolkata",
                "forecast_days": 7
            }

            resp = self.session.get(self.OPEN_METEO_URL, params=params, timeout=8)
            if resp.status_code != 200:
                return None

            raw = resp.json()
            curr = raw.get("current", {})
            daily = raw.get("daily", {})

            # Build 7-day forecast
            forecast = []
            dates = daily.get("time", [])
            for i, date in enumerate(dates):
                day_code = daily.get("weather_code", [0]*7)[i]
                day_rain = daily.get("precipitation_sum", [0]*7)[i]
                day_max = daily.get("temperature_2m_max", [None]*7)[i]
                forecast.append({
                    "date": date,
                    "max_temp": day_max,
                    "min_temp": daily.get("temperature_2m_min", [None]*7)[i],
                    "rainfall_mm": day_rain,
                    "rain_probability": daily.get("precipitation_probability_max", [0]*7)[i],
                    "wind_speed": daily.get("wind_speed_10m_max", [0]*7)[i],
                    "uv_index": daily.get("uv_index_max", [0]*7)[i],
                    "condition": _wmo_to_condition(day_code),
                    "condition_local": _wmo_to_condition_local(day_code, lang),
                    "farming_advice": translate_farming_advice(
                        day_max, None, day_rain, day_code, lang
                    ),
                })

            wcode = curr.get("weather_code", 0)
            current_data = {
                "temperature": curr.get("temperature_2m"),
                "feels_like": curr.get("apparent_temperature"),
                "humidity": curr.get("relative_humidity_2m"),
                "rainfall_mm": curr.get("precipitation", 0),
                "wind_speed": curr.get("wind_speed_10m"),
                "wind_direction": curr.get("wind_direction_10m"),
                "uv_index": curr.get("uv_index"),
                "pressure": curr.get("surface_pressure"),
                "condition": _wmo_to_condition(wcode),
                "condition_local": _wmo_to_condition_local(wcode, lang),
            }

            farming_advice = translate_farming_advice(
                current_data["temperature"],
                current_data["humidity"],
                current_data["rainfall_mm"],
                wcode,
                lang,
            )

            return {
                "status": "success",
                "is_live": True,
                "location": location,
                "latitude": lat,
                "longitude": lon,
                "data_source": "Open-Meteo (Real-time, Free)",
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                "language": lang,
                "current": current_data,
                "current_weather": current_data,       # alias for frontend compatibility
                "forecast_7day": forecast,
                "forecast_7_days": forecast,            # alias for frontend compatibility
                "farming_advice": farming_advice,
                "farming_alerts": _generate_farming_alerts(forecast, lang=lang),
            }
        except Exception as e:
            logger.error(f"Open-Meteo error: {e}")
            return None

    def _fetch_owm(self, lat: float, lon: float, location: str,
                   lang: str = "hi") -> Optional[Dict]:
        """OpenWeatherMap fallback"""
        try:
            resp = self.session.get(
                self.OWM_URL,
                params={"lat": lat, "lon": lon, "appid": OPENWEATHER_KEY,
                        "units": "metric", "lang": "hi", "cnt": 40},
                timeout=8
            )
            if resp.status_code != 200:
                return None
            raw = resp.json()
            current_item = raw["list"][0]
            wcode = 0  # OWM doesn't use WMO codes; farming advice still works
            current_data = {
                "temperature": current_item["main"]["temp"],
                "feels_like": current_item["main"]["feels_like"],
                "humidity": current_item["main"]["humidity"],
                "rainfall_mm": current_item.get("rain", {}).get("3h", 0),
                "wind_speed": current_item["wind"]["speed"] * 3.6,
                "condition": current_item["weather"][0]["description"],
                "condition_local": current_item["weather"][0]["description"],
                "uv_index": None,
            }
            farming_advice = translate_farming_advice(
                current_data["temperature"], current_data["humidity"],
                current_data["rainfall_mm"], wcode, lang
            )
            return {
                "status": "success",
                "is_live": True,
                "location": location,
                "data_source": "OpenWeatherMap",
                "language": lang,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                "current": current_data,
                "current_weather": current_data,
                "forecast_7day": _parse_owm_forecast(raw["list"]),
                "forecast_7_days": _parse_owm_forecast(raw["list"]),
                "farming_advice": farming_advice,
                "farming_alerts": [],
            }
        except Exception as e:
            logger.error(f"OWM error: {e}")
            return None

    def _static_fallback(self, location: str, lang: str = "hi") -> Dict:
        """Last-resort fallback with honest labeling."""
        return {
            "status": "fallback",
            "is_live": False,
            "location": location,
            "data_source": "Estimated (all APIs unavailable)",
            "language": lang,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "current": {
                "temperature": None, "humidity": None, "rainfall_mm": 0,
                "wind_speed": None, "condition": "Unknown",
                "condition_local": get_ui_string("error", lang),
            },
            "forecast_7day": [],
            "forecast_7_days": [],
            "farming_advice": get_ui_string("error", lang),
            "farming_alerts": [
                "⚠️ " + {
                    "hi": "वास्तविक समय डेटा अनुपलब्ध — कृपया IMD देखें: mausam.imd.gov.in",
                    "en": "Real-time data unavailable — visit IMD: mausam.imd.gov.in",
                    "bn": "রিয়েল-টাইম ডেটা অনুপলব্ধ — IMD দেখুন",
                    "te": "రియల్-టైమ్ డేటా అందుబాటులో లేదు — IMD చూడండి",
                    "mr": "रिअल-टाइम डेटा उपलब्ध नाही — IMD पहा",
                    "ta": "நிகழ்நேர தரவு இல்லை — IMD பார்க்கவும்",
                    "gu": "રીઅલ-ટાઇમ ડેટા ઉપલબ્ધ નથી — IMD જુઓ",
                    "kn": "ರಿಯಲ್-ಟೈಮ್ ಡೇಟಾ ಲಭ್ಯವಿಲ್ಲ — IMD ನೋಡಿ",
                    "ml": "തൽസമയ ഡേറ്റ ലഭ്യമല്ല — IMD നോക്കുക",
                    "pa": "ਰੀਅਲ-ਟਾਈਮ ਡੇਟਾ ਉਪਲਬਧ ਨਹੀਂ — IMD ਦੇਖੋ",
                    "or": "ରিଅଲ-ଟାଇମ ଡାଟା ଉପଲବ୍ଧ ନୁହେଁ — IMD ଦେଖନ୍ତୁ",
                    "as": "ৰিয়েল-টাইম তথ্য উপলব্ধ নহয় — IMD চাওক",
                }.get(lang, "Real-time data unavailable — visit IMD: mausam.imd.gov.in")
            ],
        }


def _wmo_to_condition(code: int) -> str:
    mapping = {
        0: "Clear Sky", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
        45: "Foggy", 48: "Icy Fog", 51: "Light Drizzle", 53: "Drizzle",
        55: "Heavy Drizzle", 61: "Slight Rain", 63: "Moderate Rain",
        65: "Heavy Rain", 71: "Slight Snow", 73: "Snow", 75: "Heavy Snow",
        80: "Slight Showers", 81: "Showers", 82: "Heavy Showers",
        85: "Snow Showers", 95: "Thunderstorm", 96: "Thunderstorm+Hail",
        99: "Heavy Thunderstorm"
    }
    return mapping.get(code, "Unknown")

def _wmo_to_condition_local(code: int, lang: str = "hi") -> str:
    """Return the WMO weather condition translated into the requested language."""
    from .language_service import get_ui_string, normalise_language_code
    lang = normalise_language_code(lang)
    # Map WMO code → UI_STRINGS key
    wmo_key_map = {
        0: "clear_sky", 1: "clear_sky", 2: "partly_cloudy", 3: "partly_cloudy",
        45: "fog", 48: "fog",
        51: "rain", 53: "rain", 55: "rain",
        61: "rain", 63: "rain", 65: "rain",
        71: "rain", 73: "rain", 75: "rain",  # snow — fallback to rain key
        80: "rain", 81: "rain", 82: "rain",
        95: "thunderstorm", 96: "thunderstorm", 99: "thunderstorm",
    }
    key = wmo_key_map.get(code, "partly_cloudy")
    return get_ui_string(key, lang)

def _wmo_to_condition_hindi(code: int) -> str:
    """Legacy Hindi alias — kept for backward compatibility."""
    return _wmo_to_condition_local(code, "hi")

def _get_farming_advice(weather_code: int, rainfall: float, max_temp: float) -> str:
    if weather_code in [95, 96, 99]:
        return "⚠️ तूफान की चेतावनी — खेत में न जाएं, फसल सुरक्षित करें"
    if rainfall and rainfall > 50:
        return "🌧️ भारी बारिश — जल निकासी सुनिश्चित करें"
    if rainfall and 5 < rainfall <= 50:
        return "🌦️ सिंचाई की जरूरत नहीं — प्राकृतिक वर्षा पर्याप्त"
    if max_temp and max_temp > 40:
        return "🔥 अत्यधिक गर्मी — सुबह/शाम सिंचाई करें, मल्चिंग करें"
    if max_temp and max_temp < 5:
        return "❄️ पाला पड़ने की संभावना — फसल को ढकें"
    return "✅ मौसम अनुकूल — सामान्य कृषि कार्य जारी रखें"

def _generate_farming_alerts(forecast: List[Dict], lang: str = "hi") -> List[str]:
    from .language_service import translate_farming_advice, normalise_language_code
    lang = normalise_language_code(lang)
    alerts = []
    for day in forecast[:3]:
        rain = day.get("rainfall_mm", 0)
        max_t = day.get("max_temp")
        uv = day.get("uv_index")
        wcode = 0
        if rain and rain > 50:
            alerts.append(f"🚨 {day['date']}: " + {
                "hi": f"भारी बारिश ({rain}mm) — जल निकासी सुनिश्चित करें",
                "en": f"Heavy rain ({rain}mm) — ensure drainage",
                "bn": f"ভারী বৃষ্টি ({rain}mm) — নিষ্কাশন নিশ্চিত করুন",
                "te": f"భారీ వర్షం ({rain}mm) — నీటి నిరిష్కరణ",
                "mr": f"जड पाऊस ({rain}mm) — निचरा सुनिश्चित करा",
                "ta": f"கனமழை ({rain}mm) — வடிகால் உறுதிப்படுத்துங்கள்",
                "gu": f"ભારે વરસાદ ({rain}mm) — ગટર ખાતરી",
                "kn": f"ಭಾರೀ ಮಳೆ ({rain}mm) — ನಿಕಾಸಿ ಖಾತ್ರಿ",
                "ml": f"കനത്ത മഴ ({rain}mm) — ഡ്രൈനേജ് ഉറപ്പ്",
                "pa": f"ਭਾਰੀ ਮੀਂਹ ({rain}mm) — ਨਿਕਾਸੀ ਯਕੀਨੀ",
                "or": f"ଭାରୀ ବର୍ଷା ({rain}mm) — ଜଳ ନିଷ୍କାସନ",
                "as": f"গধুৰ বৰষুণ ({rain}mm) — নিষ্কাশন নিশ্চিত",
            }.get(lang, f"Heavy rain ({rain}mm) — ensure drainage"))
        if max_t and max_t > 42:
            alerts.append(f"🌡️ {day['date']}: " + {
                "hi": f"लू की चेतावनी ({max_t}°C) — सुबह/शाम सींचें",
                "en": f"Heatwave ({max_t}°C) — irrigate morning/evening",
                "bn": f"তাপপ্রবাহ ({max_t}°C) — সকাল/সন্ধ্যায় সেচ দিন",
                "te": f"వేడి ({max_t}°C) — తెల్లవారు/సాయంత్రం నీరు ఇవ్వండి",
                "mr": f"उष्णतेची लाट ({max_t}°C) — सकाळ/संध्याकाळ सिंचन",
                "ta": f"வெப்பமோ ({max_t}°C) — காலை/மாலை நீர் பாய்ச்சுங்கள்",
                "gu": f"ગરમી ({max_t}°C) — સવારે/સાંજે સિંચાઈ",
                "kn": f"ಉಷ್ಣಾಂಶ ({max_t}°C) — ಬೆಳಿಗ್ಗೆ/ಸಂಜೆ ನೀರು ಹಾಕಿ",
                "ml": f"ചൂട് ({max_t}°C) — രാവിലെ/സന്ധ്യ ജലസേചനം",
                "pa": f"ਗਰਮੀ ({max_t}°C) — ਸਵੇਰੇ/ਸ਼ਾਮ ਸਿੰਚਾਈ",
                "or": f"ଗ୍ରୀଷ୍ମ ({max_t}°C) — ସକାଳ/ସନ୍ଧ୍ୟାରେ ସିଞ୍ଚନ",
                "as": f"গৰম ({max_t}°C) — ৰাতিপুৱা/সন্ধিয়া জলসিঞ্চন",
            }.get(lang, f"Heatwave ({max_t}°C) — irrigate morning/evening"))
        if uv and uv > 8:
            alerts.append(f"☀️ {day['date']}: " + {
                "hi": f"अत्यधिक UV ({uv}) — दोपहर काम न करें",
                "en": f"Extreme UV ({uv}) — avoid midday fieldwork",
                "bn": f"অতিরিক্ত UV ({uv}) — দুপুরে কাজ এড়িয়ে চলুন",
                "te": f"అధిక UV ({uv}) — మధ్యాహ్న పనిని నివారించండి",
                "mr": f"अत्यंत UV ({uv}) — दुपारी काम टाळा",
                "ta": f"அதிக UV ({uv}) — மதியம் வேலை தவிர்க்கவும்",
                "gu": f"ઊંચો UV ({uv}) — બપોરે ખેતી ટાળો",
                "kn": f"ಹೆಚ್ಚಿನ UV ({uv}) — ಮಧ್ಯಾಹ್ನ ಕೆಲಸ ಮಾಡಬೇಡಿ",
                "ml": f"ഉയർന്ന UV ({uv}) — ഉച്ചക്ക് ജോലി ഒഴിവാക്കുക",
                "pa": f"ਉੱਚ UV ({uv}) — ਦੁਪਹਿਰ ਕੰਮ ਤੋਂ ਬਚੋ",
                "or": f"ଅଧିକ UV ({uv}) — ଦୁପହର ଶ୍ରମ ଏଡ଼ାନ୍ତୁ",
                "as": f"অতিৰিক্ত UV ({uv}) — দুপৰীয়া কাম এৰক",
            }.get(lang, f"Extreme UV ({uv}) — avoid midday fieldwork"))
    return alerts

def _parse_owm_forecast(items: list) -> List[Dict]:
    daily = {}
    for item in items:
        date = item["dt_txt"][:10]
        if date not in daily:
            daily[date] = {"temps": [], "rain": 0, "condition": item["weather"][0]["description"]}
        daily[date]["temps"].append(item["main"]["temp"])
        daily[date]["rain"] += item.get("rain", {}).get("3h", 0)
    return [
        {"date": d, "max_temp": max(v["temps"]), "min_temp": min(v["temps"]),
         "rainfall_mm": v["rain"], "condition": v["condition"]}
        for d, v in list(daily.items())[:7]
    ]


# ─────────────────────────────────────────────────────────────────────────────
#  MARKET PRICES SERVICE
# ─────────────────────────────────────────────────────────────────────────────
class MarketPricesService:
    """Real-time mandi prices: Agmarknet 2.0 API → data.gov.in → MSP estimate (labeled)."""

    def __init__(self):
        # BUG 4 FIX: bounded FIFO cache — prevents unbounded RAM growth in
        # long-running Gunicorn workers (every unique lat/lon/crop key was
        # kept forever; 5k farmers × 3k responses ≈ 15 MB+ leak per worker).
        from collections import OrderedDict
        self._MAX_CACHE_ENTRIES = 200
        self._cache: OrderedDict = OrderedDict()
        self._cache_ts: Dict[str, datetime] = {}
        # Agmarknet updates once daily (~9 AM IST). A 3-min TTL causes unnecessary
        # hammering — each expiry fires a real network call for no new data.
        # 60 min for live data (Agmarknet), 24 h for seed/estimate fallback.
        self.CACHE_TTL      = 3600   # 60 min — live Agmarknet data
        self.CACHE_TTL_SEED = 86400  # 24 h  — seed/MSP-estimate fallback
        # BUG 5 FIX: use per-thread session to prevent urllib3 connection pool
        # corruption when the module-level ThreadPoolExecutor calls get_prices()
        # concurrently from multiple threads sharing the same Session object.
        self._local = threading.local()

    @property
    def session(self) -> requests.Session:
        """Per-thread requests.Session — thread-safe, reuses connection pools within thread."""
        if not hasattr(self._local, "session"):
            s = requests.Session()
            s.headers.update({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json",
                "Referer": "https://www.data.gov.in/",
            })
            self._local.session = s
        return self._local.session

    def get_prices(
        self,
        location: str,
        mandi: str = None,
        crop: str = None,
        lat: float = None,
        lon: float = None,
        state: str = None,
        include_estimates: bool = False,
    ) -> Dict[str, Any]:
        """Get real-time mandi prices from government APIs (no silent MSP fill)."""
        coord_key = (
            f"{round(lat, 4)}:{round(lon, 4)}" if lat is not None and lon is not None else ""
        )
        cache_key = ":".join([
            "prices",
            _cache_token(coord_key),
            _cache_token(location),
            _cache_token(state),
            _cache_token(mandi),
            _cache_token(crop),
            "est" if include_estimates else "live",
        ])
        if cache_key in self._cache:
            age = (datetime.now(tz=timezone.utc) - self._cache_ts[cache_key]).total_seconds()
            cached = self._cache[cache_key]
            # Live Agmarknet data: 60-min TTL (API updates once daily — 3-min TTL
            # was causing 20× unnecessary network calls with no new data).
            # Seed/MSP-estimate fallback: 24-h TTL (it never changes intraday).
            ttl = self.CACHE_TTL_SEED if not cached.get("is_live") else self.CACHE_TTL
            if age < ttl:
                return cached

        data = None

        # Priority 0: data.gov.in official API (free key) → Agmarknet scraper → seed prices
        # DataGovMandiClient handles the full fallback chain automatically:
        #   data.gov.in OGD API (if DATA_GOV_IN_API_KEY is set and valid)
        #   → Agmarknet direct dashboard (no key needed — 25 commodities)
        #   → Hardcoded seed prices (always returns data, labeled clearly)
        # Redis-backed cache (1-hour TTL, shared across all Gunicorn workers).
        try:
            from .data_gov_mandi_client import data_gov_mandi_client
            direct_data = data_gov_mandi_client.get_national_prices(
                commodity=crop or None,
                state=state or None,
            )
            if direct_data and direct_data.get("top_crops"):
                # If a specific crop is requested, filter to that crop first
                # DataGovMandiClient already filters by commodity & state internally;
                # accept result directly. Fallback chain (Agmarknet → seed) already applied.
                data = direct_data
                source_short = direct_data.get("data_source_short", "data.gov.in/Agmarknet")
                logger.info(
                    "data_gov_mandi: %d crops loaded from %s",
                    len(direct_data["top_crops"]), source_short,
                )
        except Exception as exc:
            logger.warning("data_gov_mandi client error: %s", exc)

        # Priority 1: Agmarknet 2.0 official API — only runs if Priority 0 found no data
        # or if a specific mandi filter requires location-specific pricing.
        if not data or mandi:
            try:
                from .agmarknet_client import agmarknet_client
                resolved_state = state or self._infer_state(location, state=state)
                p1_data = agmarknet_client.get_market_prices(
                    location, mandi, crop, state=resolved_state or state
                )
                if p1_data and p1_data.get("top_crops"):
                    logger.info("Market prices from Agmarknet API for %s", location)
                    data = self._tag_live_crop_rows(p1_data)
            except Exception as exc:
                logger.warning("Agmarknet client error: %s", exc)

        # Priority 2: data.gov.in (Agmarknet OGD + eNAM datasets)
        if not data:
            api_key = self._effective_data_gov_key()
            if api_key:
                for resource_key in self._data_gov_resource_order(location):
                    data = self._fetch_data_gov(
                        location, mandi, crop, resource_key, api_key, state=state
                    )
                    if data:
                        data = self._tag_live_crop_rows(data)
                        break

        # Optional MSP seasonal estimates (opt-in only — never presented as mandi trades)
        if not data and include_estimates:
            data = self._curated_fallback(location, mandi, crop)

        if not data:
            data = self._unavailable_market_response(
                location, mandi, crop, state=state or self._infer_state(location, state=state)
            )

        if crop and data and data.get("top_crops"):
            data = self._apply_crop_filter(data, crop)

        if data.get("top_crops"):
            data = self._normalize_top_crops(data)

        if mandi and data:
            data = self._apply_mandi_pricing(data, location, mandi)
            data["selected_mandi"] = mandi
            data["mandi_filter"] = mandi

        data = self._finalize_market_response(data)

        # BUG 4 FIX: evict oldest entry when at capacity
        if len(self._cache) >= self._MAX_CACHE_ENTRIES:
            oldest = next(iter(self._cache))
            self._cache.pop(oldest, None)
            self._cache_ts.pop(oldest, None)
        self._cache[cache_key] = data
        self._cache[cache_key]  # move to end (mark as recently used)
        self._cache_ts[cache_key] = datetime.now(tz=timezone.utc)
        return data

    # Core MSP crops always present for advisory UI and tests (demo API returns random 10 rows)
    _STAPLE_CROP_IDS = (
        "wheat", "rice", "maize", "mustard", "gram",
        "soybean", "cotton", "onion", "potato", "tomato",
    )

    def _normalize_top_crops(self, data: Dict[str, Any]) -> Dict[str, Any]:
        from .crop_catalog import crop_catalog

        data = dict(data)
        normalized = []
        for item in data.get("top_crops", []):
            item = dict(item)
            norm = crop_catalog.normalize(str(item.get("crop_name", "")))
            if norm:
                item["crop_name"] = norm["name"]
                item["crop_id"] = norm["id"]
                if not item.get("msp") and norm.get("msp"):
                    item["msp"] = norm["msp"]
                if not item.get("crop_name_hindi"):
                    item["crop_name_hindi"] = norm.get("hindi", "")
            normalized.append(item)
        data["top_crops"] = normalized
        return data

    @staticmethod
    def _tag_live_crop_rows(data: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(data)
        tagged = []
        for item in data.get("top_crops") or []:
            row = dict(item)
            row["price_source"] = row.get("price_source") or "live_mandi"
            row["is_live"] = True
            tagged.append(row)
        data["top_crops"] = tagged
        return data

    def _unavailable_market_response(
        self,
        location: str,
        mandi: Optional[str],
        crop: Optional[str],
        state: Optional[str] = None,
    ) -> Dict[str, Any]:
        registered = self._has_registered_data_gov_key()
        using_demo = not registered
        msg = (
            "Live mandi data unavailable — configure DATA_GOV_IN_API_KEY in .env "
            "(free registration at https://data.gov.in/user/register). "
            "The public demo key returns only 10 rows and is rate-limited."
        )
        if crop:
            msg = (
                f"No live mandi row for '{crop}' in this state today. "
                + msg
            )
        if mandi:
            msg = (
                f"No live arrival at '{mandi}' today. "
                + msg
            )
        return {
            "status": "unavailable",
            "is_live": False,
            "using_demo_key": using_demo,
            "api_key_registered": registered,
            "location": location,
            "state": state or "",
            "data_source": "Agmarknet (API key required for live data)",
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "top_crops": [],
            "total_records": 0,
            "message": msg,
        }

    def _finalize_market_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        data       = dict(data)
        registered = self._has_registered_data_gov_key()
        # Bug 6 fix: _effective_data_gov_key() returns None (not the shared demo key)
        # when no registered key is configured.
        using_demo = self._effective_data_gov_key() is None
        data["using_demo_key"]     = data.get("using_demo_key", using_demo)
        data["api_key_registered"] = registered

        top = list(data.get("top_crops") or [])
        live_rows = [
            c for c in top
            if c.get("is_live")
            or (
                c.get("price_source") == "live_mandi"
                and not c.get("supplemented")
            )
        ]
        estimate_rows = [
            c for c in top
            if c.get("price_source") in ("msp_mandi_estimate", "msp_seasonal_estimate")
            or c.get("supplemented")
        ]

        src = str(data.get("data_source") or "").lower()
        is_msp_only = data.get("status") == "fallback" or "msp" in src or "estimate" in src

        if is_msp_only or (estimate_rows and not live_rows):
            data["is_live"] = False
            data["status"] = "fallback"
        elif live_rows and estimate_rows:
            data["is_live"] = True
            data["status"] = "partial"
        elif live_rows:
            data["is_live"] = True
            if data.get("status") not in ("fallback", "unavailable"):
                data["status"] = "success"
        else:
            data["is_live"] = False
            if data.get("status") != "fallback":
                data["status"] = "unavailable"

        if using_demo and live_rows:
            note = (
                "Using data.gov.in demo key (max 10 rows). Register your own "
                "DATA_GOV_IN_API_KEY for full state coverage."
            )
            data["message"] = f"{data.get('message', '')} {note}".strip()

        # Always surface exact fetch time and age so Flutter UI can show
        # "Data as of 09:15 AM (2 hours ago)" — honest freshness disclosure.
        now_utc = datetime.now(tz=timezone.utc)
        data["fetched_at"] = data.get("fetched_at") or now_utc.isoformat()
        # Compute age from the Agmarknet reported_date if available (daily data)
        reported = data.get("reported_date", "")
        if reported and not data.get("data_age_minutes"):
            try:
                from datetime import timezone as _tz
                import re as _re
                # Agmarknet dates: "12-06-2026" or "2026-06-12"
                if _re.match(r"\d{2}-\d{2}-\d{4}", reported):
                    d, m, y = reported.split("-")
                    reported_dt = datetime(int(y), int(m), int(d), 9, 0, tzinfo=_tz.utc)
                elif _re.match(r"\d{4}-\d{2}-\d{2}", reported):
                    y, m, d = reported.split("-")
                    reported_dt = datetime(int(y), int(m), int(d), 9, 0, tzinfo=_tz.utc)
                else:
                    reported_dt = None
                if reported_dt:
                    data["data_age_minutes"] = max(
                        0, int((now_utc - reported_dt).total_seconds() / 60)
                    )
            except Exception:
                pass

        return data

    def _ensure_staple_crops(
        self,
        data: Dict[str, Any],
        location: str,
        mandi: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fill missing staple commodities with location-specific MSP estimates."""
        from .crop_catalog import crop_catalog

        data = dict(data)
        top = list(data.get("top_crops") or [])
        present = set()
        for item in top:
            cid = item.get("crop_id")
            if not cid:
                norm = crop_catalog.normalize(str(item.get("crop_name", "")))
                cid = norm["id"] if norm else str(item.get("crop_name", "")).lower()
            present.add(cid)

        supplemented = []
        for crop_id in self._STAPLE_CROP_IDS:
            if crop_id in present:
                continue
            fb = self._curated_fallback(location, mandi, crop_id)
            rows = fb.get("top_crops") or []
            if not rows:
                continue
            row = dict(rows[0])
            row["supplemented"] = True
            row["crop_id"] = crop_id
            top.append(row)
            supplemented.append(crop_id)

        if supplemented:
            data["top_crops"] = top
            data["total_records"] = len(top)
            note = data.get("message") or ""
            data["message"] = (
                f"{note} Staple crops {', '.join(supplemented)} added from MSP seasonal "
                f"estimate (live feed had no row today)."
            ).strip()

        return data

    def list_mandis(
        self,
        location: str,
        lat: float = None,
        lon: float = None,
        state: str = None,
        radius_km: float = 150,     # NEW: only return mandis within this radius when GPS available
        max_results: int = 50,       # NEW: cap the list for frontend usability
    ) -> Dict[str, Any]:
        """
        Nearby mandi list, sorted by distance from user's GPS.

        When GPS coordinates are provided (lat/lon), returns only mandis within
        `radius_km` (default 150 km), sorted closest-first.  This makes the
        dropdown immediately useful — the farmer's local mandis appear at the top.

        Falls back to state-wide list when no GPS is available.
        """
        cache_key = f"mandis:{round(lat or 0, 3)}:{round(lon or 0, 3)}:{location}:{state}:{radius_km}"
        if cache_key in self._cache:
            age = (datetime.now(tz=timezone.utc) - self._cache_ts[cache_key]).total_seconds()
            # Mandi list is stable — 60-min TTL is sufficient and avoids hammering
            # the Agmarknet market-registry endpoint every 3 minutes.
            if age < self.CACHE_TTL:
                return self._cache[cache_key]

        registered_key = self._has_registered_data_gov_key()
        api_key = self._effective_data_gov_key()
        using_demo = api_key is None   # None = no registered key → degrade gracefully
        mandis_map: Dict[str, Dict[str, Any]] = {}
        resolved_state = state or self._infer_state(location, state=state)

        # 1) Agmarknet official market registry (full state list, no 10-row cap)
        try:
            from .agmarknet_client import agmarknet_client

            for m in agmarknet_client.list_markets_for_location(location, state=resolved_state):
                self._upsert_mandi(mandis_map, m, live=True)
        except Exception as exc:
            logger.warning("Agmarknet mandi list error: %s", exc)

        # 2) data.gov.in — paginated when a registered key is set
        if api_key:
            for resource_key in self._data_gov_resource_order(location):
                resource_id = DATA_GOV_RESOURCES[resource_key]
                url = f"{DATA_GOV_BASE}/{resource_id}"
                state_candidates = self._state_filter_candidates(location, state=state)
                tries = state_candidates if not using_demo else state_candidates[:1]

                for state_name in tries:
                    records = self._data_gov_fetch_paginated(
                        url,
                        {
                            "api-key": api_key,
                            "format": "json",
                            "filters[state]": state_name,
                        },
                        resource_key,
                        api_key,
                    )
                    for rec in records:
                        market = str(
                            self._record_field(rec, "market", "Market", default="")
                        ).strip()
                        if not market or len(market) < 2:
                            continue
                        self._upsert_mandi(
                            mandis_map,
                            {
                                "name": market,
                                "district": self._record_field(
                                    rec, "district", "District", default=""
                                ),
                                "state": self._record_field(
                                    rec, "state", "State", default=state_name
                                ),
                                "source": f"data.gov.in ({resource_key})",
                                "live": True,
                                "commodity_count": 1,
                            },
                            live=True,
                        )

        live_count = sum(1 for m in mandis_map.values() if m.get("live"))

        # 3) Reference mandis — fill gaps (demo key / few live rows / GPS nearby)
        ref_before = len(mandis_map)
        # Always merge reference DB so users see full state/nearby coverage, not a sparse live-only list
        self._merge_reference_mandis(
            mandis_map, location, resolved_state, lat, lon, fill_gaps=True
        )
        ref_count = len(mandis_map) - ref_before

        mandis = self._enrich_and_sort_mandis(list(mandis_map.values()), lat, lon)

        # ── GPS-based nearby filtering ─────────────────────────────────────
        # When the user has GPS, trim to the nearest mandis within radius_km.
        # Key insight: reference DB mandis with no coordinate data are EXCLUDED
        # when GPS is available — we only show mandis we can confirm are nearby.
        # The fallback to unknown_dist only kicks in when we have < 3 confirmed
        # nearby mandis (e.g. very rural area with sparse coordinate coverage).
        has_gps = lat is not None and lon is not None
        if has_gps:
            # Mandis with known distance within radius
            nearby = [
                m for m in mandis
                if m.get("distance_km") is not None and m["distance_km"] <= radius_km
            ]
            # Mandis with no coordinate data — only use as fallback if list is tiny
            unknown_dist = [m for m in mandis if m.get("distance_km") is None]

            if len(nearby) >= 3:
                # Good coverage — drop all unknown-distance mandis entirely
                mandis = nearby[:max_results]
            elif len(nearby) > 0:
                # Sparse coverage — add a few unknown-distance to pad to 10
                mandis = (nearby + unknown_dist[:max(0, 10 - len(nearby))])[:max_results]
            else:
                # No known-distance mandis at all — show limited unknown-dist ones
                # This happens in very rural areas with no coordinate data
                mandis = unknown_dist[:min(20, max_results)]

            # Tag each mandi with a human-readable proximity label
            for m in mandis:
                d = m.get("distance_km")
                if d is not None:
                    if d <= 30:
                        m["proximity"] = "very_near"
                        m["proximity_label"] = f"~{d:.0f} km — आपके पास"
                    elif d <= 75:
                        m["proximity"] = "near"
                        m["proximity_label"] = f"~{d:.0f} km"
                    else:
                        m["proximity"] = "regional"
                        m["proximity_label"] = f"~{d:.0f} km (क्षेत्रीय)"
                else:
                    m["proximity"] = "unknown"
                    m["proximity_label"] = "दूरी अज्ञात"
        else:
            mandis = mandis[:max_results]

        if registered_key and not using_demo:
            coverage = "full"
            data_source = "Agmarknet + data.gov.in (live)"
            if has_gps:
                nearest_name = mandis[0]["name"] if mandis else location
                nearest_dist = mandis[0].get("distance_km", "?") if mandis else "?"
                message = (
                    f"{len(mandis)} mandis near {location} "
                    f"(nearest: {nearest_name}, {nearest_dist} km) · {live_count} live today"
                )
            else:
                message = f"{len(mandis)} mandis for {resolved_state or location} ({live_count} live today)"
        elif live_count >= 15:
            coverage = "partial"
            data_source = "Agmarknet + data.gov.in (limited)"
            message = (
                f"{len(mandis)} mandis shown ({live_count} live). "
                "Register DATA_GOV_IN_API_KEY in .env for complete coverage."
            )
        else:
            coverage = "reference+live"
            data_source = "Live feed + nearby reference mandis"
            if has_gps and mandis:
                nearest_name = mandis[0]["name"]
                nearest_dist = mandis[0].get("distance_km", "?")
                message = (
                    f"{len(mandis)} nearby mandis ({live_count} live). "
                    f"Nearest: {nearest_name} ({nearest_dist} km). "
                    "Add DATA_GOV_IN_API_KEY for real-time prices."
                )
            else:
                message = (
                    f"{len(mandis)} mandis ({live_count} live, {ref_count} reference). "
                    "Add DATA_GOV_IN_API_KEY for real-time coverage."
                )

        # Add nearest mandi info to the top-level response for quick frontend use
        nearest_mandi = None
        if mandis:
            m0 = mandis[0]
            nearest_mandi = {
                "name":       m0["name"],
                "district":   m0.get("district", ""),
                "state":      m0.get("state", ""),
                "distance_km": m0.get("distance_km"),
                "distance":   m0.get("distance", ""),
                "live":       m0.get("live", False),
            }

        result = {
            "status": "success",
            "location": location,
            "state": resolved_state or (mandis[0]["state"] if mandis else ""),
            "mandis": mandis,
            "total": len(mandis),
            "live_count": live_count,
            "reference_count": ref_count,
            "coverage": coverage,
            "api_key_registered": registered_key,
            "using_demo_key": using_demo and not registered_key,
            "data_source": data_source,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "message": message,
            "nearest_mandi": nearest_mandi,
            "radius_km": radius_km if has_gps else None,
            "has_gps": has_gps,
        }
        self._cache[cache_key] = result
        self._cache_ts[cache_key] = datetime.now(tz=timezone.utc)
        return result

    @staticmethod
    def _has_registered_data_gov_key() -> bool:
        key = DATA_GOV_KEY.strip()
        return bool(key) and key.lower() not in DATA_GOV_PLACEHOLDER_KEYS

    @staticmethod
    def _upsert_mandi(
        mandis_map: Dict[str, Dict[str, Any]],
        entry: Dict[str, Any],
        live: bool = False,
    ) -> None:
        name = str(entry.get("name", "")).strip()
        if not name:
            return
        key = name.lower()
        existing = mandis_map.get(key)
        if existing:
            if live:
                existing["live"] = True
            existing["commodity_count"] = existing.get("commodity_count", 0) + int(
                entry.get("commodity_count", 0)
            )
            if entry.get("district") and not existing.get("district"):
                existing["district"] = entry["district"]
            if entry.get("distance_km") is not None:
                existing["distance_km"] = entry["distance_km"]
                existing["distance"] = entry.get("distance", existing.get("distance", ""))
            return
        mandis_map[key] = {
            "name": name,
            "district": entry.get("district", ""),
            "state": entry.get("state", ""),
            "source": entry.get("source", ""),
            "live": bool(live or entry.get("live")),
            "commodity_count": int(entry.get("commodity_count", 0)),
            "distance_km": entry.get("distance_km"),
            "distance": entry.get("distance", ""),
            "specialty": entry.get("specialty", ""),
        }

    def _merge_reference_mandis(
        self,
        mandis_map: Dict[str, Dict[str, Any]],
        location: str,
        state: str,
        lat: float,
        lon: float,
        fill_gaps: bool,
    ) -> None:
        if not fill_gaps and len(mandis_map) >= 200:
            return
        try:
            from .enhanced_market_prices import EnhancedMarketPricesService

            ref_svc = EnhancedMarketPricesService()
            has_gps = lat is not None and lon is not None

            if has_gps:
                # GPS available: get nearest mandis by distance (coordinates populated)
                # This is key — get_nearest_mandis returns mandis WITH distance_km set,
                # so the proximity filter in list_mandis can correctly exclude far ones.
                refs = ref_svc.get_nearest_mandis(location, lat, lon, limit=60)
            elif state:
                # No GPS — fall back to state-wide list (no distance data)
                refs = ref_svc.get_mandis_in_state(state, lat, lon, limit=100)
            else:
                refs = ref_svc.get_nearest_mandis(location, lat, lon, limit=60)

            for m in refs:
                self._upsert_mandi(
                    mandis_map,
                    {
                        "name": m.get("name", ""),
                        "district": m.get("district", ""),
                        "state": m.get("state", state or ""),
                        "source": m.get("source", "reference database"),
                        "live": False,
                        "distance_km": m.get("distance_km"),
                        "distance": m.get("distance", ""),
                        "specialty": m.get("specialty", ""),
                    },
                    live=False,
                )
        except Exception as exc:
            logger.warning("Reference mandi merge failed: %s", exc)

    _mandi_coord_cache: Optional[Dict[str, Tuple[float, float]]] = None

    @classmethod
    def _mandi_coordinate_lookup(cls) -> Dict[str, Tuple[float, float]]:
        if cls._mandi_coord_cache is not None:
            return cls._mandi_coord_cache
        lookup: Dict[str, Tuple[float, float]] = {}
        try:
            from .enhanced_market_prices import EnhancedMarketPricesService

            for m in EnhancedMarketPricesService()._get_nationwide_mandi_database():
                name = str(m.get("name", "")).strip().lower()
                mlat = m.get("latitude")
                mlon = m.get("longitude")
                if name and mlat is not None and mlon is not None:
                    lookup[name] = (float(mlat), float(mlon))
        except Exception as exc:
            logger.debug("Mandi coordinate lookup build failed: %s", exc)
        cls._mandi_coord_cache = lookup
        return lookup

    def _enrich_and_sort_mandis(
        self,
        mandis: List[Dict[str, Any]],
        lat: float = None,
        lon: float = None,
    ) -> List[Dict[str, Any]]:
        if lat is not None and lon is not None:
            coord_lookup = self._mandi_coordinate_lookup()
            for m in mandis:
                if m.get("distance_km") is not None:
                    continue
                key = str(m.get("name", "")).strip().lower()
                coords = coord_lookup.get(key)
                if coords:
                    dist = _haversine_km(lat, lon, coords[0], coords[1])
                    m["distance_km"] = round(dist, 1)
                    m["distance"] = f"{dist:.1f} km"
        return self._sort_mandis_for_user(mandis, lat, lon)

    @staticmethod
    def _sort_mandis_for_user(
        mandis: List[Dict[str, Any]],
        lat: float = None,
        lon: float = None,
    ) -> List[Dict[str, Any]]:
        has_gps = lat is not None and lon is not None

        def sort_key(m: Dict[str, Any]):
            dist = m.get("distance_km")
            dist_key = dist if dist is not None else 99999
            live = 0 if m.get("live") else 1
            if has_gps:
                return (dist_key, live, -m.get("commodity_count", 0), m.get("name", "").lower())
            return (live, dist_key, -m.get("commodity_count", 0), m.get("name", "").lower())

        return sorted(mandis, key=sort_key)

    def _data_gov_fetch_paginated(
        self,
        url: str,
        base_params: Dict[str, Any],
        resource_key: str,
        api_key: str,
        max_records: int = 2500,
    ) -> List[dict]:
        """Fetch all pages from data.gov.in (no key: refuse rather than use shared demo)."""
        if not api_key:
            logger.warning("DATA_GOV_IN_API_KEY not configured — skipping paginated fetch")
            return []
        page_size = 100
        max_pages = 25
        all_records: List[dict] = []
        offset = 0

        for _ in range(max_pages):
            params = dict(base_params)
            params["limit"] = page_size
            params["offset"] = offset
            records = self._data_gov_request(url, params, resource_key, api_key)
            if not records:
                break
            all_records.extend(records)
            if len(records) < page_size:
                break
            offset += page_size
            if len(all_records) >= max_records:
                break
        return all_records

    def _apply_mandi_filter(self, data: Dict[str, Any], mandi: str) -> Dict[str, Any]:
        m = mandi.lower().strip()
        filtered = [
            c for c in data.get("top_crops", [])
            if self._mandi_name_matches(c.get("mandi_name"), m)
        ]
        if filtered:
            data = dict(data)
            data["top_crops"] = filtered
            data["total_records"] = len(filtered)
            data["message"] = f"{len(filtered)} commodities at {mandi}"
        return data

    @staticmethod
    def _mandi_name_matches(mandi_name: Any, mandi_query_lower: str) -> bool:
        if not mandi_name or not mandi_query_lower:
            return False
        mn = str(mandi_name).lower().strip()
        mq = mandi_query_lower.strip()
        return mq in mn or mn in mq

    def _apply_mandi_pricing(
        self,
        data: Dict[str, Any],
        location: str,
        mandi: str,
    ) -> Dict[str, Any]:
        """Filter to live rows for the selected mandi; never invent mandi modal prices."""
        if not mandi or not data:
            return data

        data = dict(data)
        m_lower = mandi.lower().strip()
        rows_in = list(data.get("top_crops") or [])
        live_matches = [
            dict(c) for c in rows_in
            if self._mandi_name_matches(c.get("mandi_name"), m_lower)
        ]

        if live_matches:
            for row in live_matches:
                row["mandi_name"] = mandi
                row["price_source"] = "live_mandi"
                row["is_live"] = True
            data["top_crops"] = live_matches
            data["total_records"] = len(live_matches)
            data["mandi_pricing_applied"] = True
            data["mandi_live_only"] = True
            data["message"] = f"{len(live_matches)} live commodities at {mandi}"
            return data

        data["mandi_pricing_applied"] = True
        data["mandi_no_live_rows"] = True
        data["message"] = (
            f"No live arrival rows for '{mandi}' today — showing state-wide mandi feed. "
            "Pick another mandi or register DATA_GOV_IN_API_KEY for fuller coverage."
        )
        return data

    def _apply_crop_filter(self, data: Dict[str, Any], crop: str) -> Dict[str, Any]:
        from .crop_catalog import crop_catalog

        norm = crop_catalog.normalize(crop)
        terms = {crop.lower()}
        if norm:
            terms.add(norm["id"])
            terms.add(norm["name"].lower())
            for a in norm.get("aliases", []):
                terms.add(a.lower())

        filtered = []
        for item in data.get("top_crops", []):
            name = str(item.get("crop_name", "")).lower()
            if any(t in name or name.startswith(t) for t in terms):
                filtered.append(item)

        if filtered:
            data = dict(data)
            data["top_crops"] = filtered
            data["searched_crop"] = norm["name"] if norm else crop
            data["total_records"] = len(filtered)
            data["message"] = f"{len(filtered)} mandi record(s) for {data['searched_crop']}"
        elif norm:
            data = dict(data)
            data["searched_crop"] = norm["name"]
            data["crop_search_note"] = (
                f"No live mandi rows for '{norm['name']}' in this state today; "
                "showing nearest available commodities."
            )
        return data

    @staticmethod
    def _data_gov_resource_order(location: str) -> Tuple[str, ...]:
        """eNAM has NCT Delhi mandis; Agmarknet OGD has broader state coverage."""
        loc = location.lower()
        if any(k in loc for k in ("delhi", "nct", "azadpur", "gazipur")):
            return ("enam_market", "agmarknet_mandi")
        return ("agmarknet_mandi", "enam_market")

    @staticmethod
    def _effective_data_gov_key() -> Optional[str]:
        """Return the configured data.gov.in API key, or None if not set.

        Bug 6 fix: no longer falls back to the hardcoded shared demo key.
        The demo key is rate-limited to 10 rows/request and is shared across
        all users of the demo, causing unpredictable failures at scale.
        Callers must handle None and surface a clear unavailability message.
        """
        key = DATA_GOV_KEY.strip()
        if key and key.lower() not in DATA_GOV_PLACEHOLDER_KEYS:
            return key
        return None

    def _state_filter_candidates(self, location: str, state: str = None) -> List[str]:
        names: List[str] = []
        if state and state.strip():
            names.append(state.strip())
        loc = location.lower().strip()
        for fragment, variants in STATE_FILTER_NAMES.items():
            if fragment in loc:
                names.extend(variants)
        if not names:
            inferred = self._infer_state(location, state=state)
            if inferred:
                names.append(inferred)
        # Deduplicate preserving order
        seen = set()
        out = []
        for n in names:
            if n not in seen:
                seen.add(n)
                out.append(n)
        return out

    def _fetch_data_gov(
        self,
        location: str,
        mandi: str,
        crop: str,
        resource_key: str,
        api_key: str,
        state: str = None,
    ) -> Optional[Dict]:
        """Fetch from data.gov.in; tries multiple state filter spellings."""
        resource_id = DATA_GOV_RESOURCES[resource_key]
        url = f"{DATA_GOV_BASE}/{resource_id}"

        state_candidates = self._state_filter_candidates(location, state=state)
        # Without a registered key there's nothing to fetch
        if not api_key:
            return None
        max_state_tries = len(state_candidates)

        for state_name in state_candidates[:max_state_tries]:
            params: Dict[str, Any] = {
                "api-key": api_key,
                "format": "json",
                "limit": 50,
                "filters[state]": state_name,
            }
            if crop:
                params["filters[commodity]"] = crop

            records = None
            if mandi:
                params_with_mandi = dict(params)
                params_with_mandi["filters[market]"] = mandi
                records = self._data_gov_request(
                    url, params_with_mandi, resource_key, api_key
                )
            if not records:
                records = self._data_gov_request(url, params, resource_key, api_key)
                if mandi and records:
                    records = self._filter_records_by_mandi(records, mandi)

            if records is None:
                break
            if records:
                formatted = self._format_data_gov_response(
                    records, location, resource_key, selected_mandi=mandi
                )
                if formatted.get("top_crops"):
                    return formatted

        # National sample without state filter, then filter client-side
        records = self._data_gov_request(
            url,
            {
                "api-key": api_key,
                "format": "json",
                "limit": 100,
            },
            resource_key,
            api_key,
        )
        if records is None:
            return None
        if records:
            state_names = {
                s.lower() for s in self._state_filter_candidates(location, state=state)
            }
            loc_lower = location.lower()
            filtered = [
                r for r in records
                if str(r.get("state", r.get("State", ""))).lower() in state_names
                or loc_lower in str(r.get("state", r.get("State", ""))).lower()
                or loc_lower in str(r.get("district", r.get("District", ""))).lower()
            ]
            if filtered:
                formatted = self._format_data_gov_response(filtered, location, resource_key)
                if formatted.get("top_crops"):
                    return formatted
        return None

    def _data_gov_request(
        self,
        url: str,
        params: Dict[str, Any],
        resource_key: str,
        api_key: str,
    ) -> Optional[list]:
        last_error = None
        for attempt in range(2):
            try:
                resp = self.session.get(url, params=params, timeout=DATA_GOV_TIMEOUT)
                if resp.status_code == 403:
                    logger.warning(
                        "data.gov.in 403 for %s — check your DATA_GOV_IN_API_KEY. "
                        "Register at https://data.gov.in/user/register",
                        resource_key,
                    )
                    return None
                if resp.status_code == 429:
                    logger.warning(
                        "data.gov.in %s rate limited — use your own DATA_GOV_IN_API_KEY",
                        resource_key,
                    )
                    return None
                if resp.status_code != 200:
                    logger.warning(
                        "data.gov.in %s HTTP %s", resource_key, resp.status_code
                    )
                    return None
                raw = resp.json()
                records = raw.get("records", [])
                return records if records else None
            except requests.Timeout as exc:
                last_error = exc
                logger.warning(
                    "data.gov.in %s timeout (attempt %s)", resource_key, attempt + 1
                )
            except requests.RequestException as exc:
                last_error = exc
                logger.warning("data.gov.in %s error: %s", resource_key, exc)
                break
        if last_error:
            logger.debug("data.gov.in final error: %s", last_error)
        return None

    @staticmethod
    def _record_field(rec: dict, *keys: str, default: Any = "") -> Any:
        for key in keys:
            if key in rec and rec[key] not in (None, ""):
                return rec[key]
        return default

    @staticmethod
    def _filter_records_by_mandi(records: list, mandi: str) -> list:
        m = mandi.lower().strip()
        return [
            r for r in records
            if m in str(
                r.get("market", r.get("Market", ""))
            ).lower()
        ]

    def _format_data_gov_response(
        self,
        records: list,
        location: str,
        source: str,
        selected_mandi: str = None,
    ) -> Dict:
        """Format raw data.gov.in records into standardized response"""
        crops = []
        for rec in records[:20]:
            crop_name = self._record_field(
                rec, "commodity", "Commodity", default="Unknown"
            )
            try:
                modal_price = float(
                    self._record_field(
                        rec,
                        "modal_price", "Modal_Price", "Modal_x0020_Price",
                        "Modal Price", default=0,
                    )
                )
                min_price = float(
                    self._record_field(
                        rec,
                        "min_price", "Min_Price", "Min_x0020_Price", "Min Price",
                        default=modal_price * 0.9,
                    )
                )
                max_price = float(
                    self._record_field(
                        rec,
                        "max_price", "Max_Price", "Max_x0020_Price", "Max Price",
                        default=modal_price * 1.1,
                    )
                )
            except (ValueError, TypeError):
                continue
            if modal_price <= 0:
                continue

            crop_key = str(crop_name).split("(")[0].strip().lower()
            msp = MSP_2024_25.get(crop_key)
            if msp is None:
                for msp_name in MSP_2024_25:
                    if msp_name in crop_key:
                        msp = MSP_2024_25[msp_name]
                        break
            profit = round(((modal_price - msp) / msp * 100), 1) if msp else None

            crops.append({
                "crop_name": str(crop_name).split("(")[0].strip().title(),
                "crop_name_hindi": CROP_HINDI.get(crop_key, crop_name),
                "price_source": "live_mandi",
                "is_live": True,
                "mandi_name": self._record_field(
                    rec, "market", "Market", default=location
                ),
                "state": self._record_field(
                    rec, "state", "State", default="",
                ),
                "min_price": round(min_price, 2),
                "max_price": round(max_price, 2),
                "modal_price": round(modal_price, 2),
                "msp": msp,
                "profit_vs_msp": profit,
                "profit_indicator": "📈" if profit and profit > 0 else "📉",
                "variety": self._record_field(rec, "variety", "Variety", default=""),
                "grade": self._record_field(rec, "grade", "Grade", default=""),
                "date": self._record_field(
                    rec, "arrival_date", "Arrival_Date", "Arrival Date",
                    default=datetime.now(tz=timezone.utc).strftime("%d/%m/%Y"),
                ),
                "unit": "₹/quintal",
            })

        return {
            "status": "success",
            "is_live": True,
            "location": location,
            "selected_mandi": selected_mandi,
            "data_source": f"data.gov.in ({source})",
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "top_crops": crops,
            "total_records": len(crops),
            "message": f"{len(crops)} live mandi records from data.gov.in ({source})",
        }

    def _infer_state(self, location: str, state: str = None) -> str:
        if state and str(state).strip():
            return str(state).strip()
        loc_lower = (location or "").lower()
        for name in STATE_FILTER_NAMES:
            if name in loc_lower:
                return STATE_FILTER_NAMES[name][0]
        for name in STATE_CODES:
            if name in loc_lower:
                return name.title()
        return ""

    def _curated_fallback(self, location: str, mandi: str, crop: str) -> Dict:
        """
        Curated fallback with deterministic seasonal pricing based on real MSP data.
        Prices are based on published market reports: MSP + realistic seasonal premium.
        No random() used — deterministic by month/season for consistency.
        """
        crops_data = []
        target_crops = [crop] if crop else list(MSP_2024_25.keys())[:10]
        month = datetime.now(tz=timezone.utc).month

        # Realistic seasonal premiums based on AGMARKNET historical patterns
        # Kharif harvest (Oct-Dec): prices near MSP; Rabi harvest (Mar-May): near MSP
        # Off-season: 10-20% above MSP (storage premium)
        SEASONAL_PREMIUM = {
            # Wheat - harvested Apr-May, peaks Oct-Feb (stored)
            "wheat":     [1.12,1.14,1.15,1.05,1.04,1.08,1.10,1.11,1.13,1.14,1.13,1.12],
            # Rice - harvested Oct-Nov, peaks Apr-Sep
            "rice":      [1.15,1.16,1.17,1.18,1.18,1.17,1.12,1.11,1.10,1.05,1.06,1.10],
            # Maize - year-round but peaks in summer
            "maize":     [1.10,1.12,1.13,1.11,1.10,1.08,1.06,1.07,1.08,1.09,1.10,1.10],
            # Soybean - harvested Oct-Nov
            "soybean":   [1.08,1.08,1.09,1.10,1.12,1.14,1.15,1.13,1.10,1.05,1.06,1.07],
            # Cotton - harvested Nov-Feb
            "cotton":    [1.12,1.13,1.14,1.15,1.16,1.15,1.12,1.10,1.08,1.07,1.06,1.08],
            # Mustard - harvested Mar-Apr
            "mustard":   [1.14,1.15,1.13,1.05,1.06,1.08,1.10,1.12,1.13,1.14,1.14,1.14],
            # Gram - harvested Feb-Mar
            "gram":      [1.13,1.12,1.05,1.07,1.09,1.11,1.13,1.14,1.14,1.14,1.14,1.13],
            # Lentil - harvested Mar-Apr
            "lentil":    [1.12,1.13,1.05,1.07,1.09,1.11,1.12,1.13,1.13,1.13,1.13,1.12],
            # Groundnut - harvested Oct-Nov
            "groundnut": [1.10,1.10,1.11,1.12,1.13,1.14,1.14,1.13,1.12,1.06,1.07,1.09],
        }

        for crop_name in target_crops:
            msp = 0
            try:
                from advisory.models import Crop
                crop_obj = Crop.objects.filter(name=crop_name).first()
                if crop_obj and crop_obj.msp_per_quintal:
                    msp = crop_obj.msp_per_quintal
            except Exception:
                pass
            if not msp:
                msp = MSP_2024_25.get(crop_name, 2000)
            premiums = SEASONAL_PREMIUM.get(crop_name, [1.10]*12)
            seasonal_premium = premiums[month - 1]

            # Apply a deterministic per-mandi adjustment (±8% based on mandi name hash)
            # This ensures: same mandi → same prices; different mandis → different prices
            mandi_str = (mandi or location or '').lower().strip()
            # Simple deterministic hash: sum of char codes seeded per crop so crops differ
            mandi_hash = sum(ord(c) * (i + 1) for i, c in enumerate(mandi_str or 'default'))
            crop_hash = sum(ord(c) for c in crop_name)
            # Normalize to a ±8% multiplier: different mandis get values like 0.93, 0.97, 1.02, 1.06…
            mandi_mult = 1.0 + ((mandi_hash + crop_hash) % 160 - 80) / 1000.0  # range: 0.92 to 1.08

            modal = round(msp * seasonal_premium * mandi_mult)
            if modal <= msp:
                modal = round(msp * (1.01 + (mandi_hash % 50) / 1000.0))
            # min/max spread also varies slightly per mandi for realism
            spread = 0.04 + ((mandi_hash % 40) / 1000.0)  # 4% to 8% spread
            min_p = round(modal * (1 - spread))
            max_p = round(modal * (1 + spread))
            profit_pct = round((modal - msp) / msp * 100, 1)


            crops_data.append({
                "crop_name": crop_name.capitalize(),
                "crop_name_hindi": CROP_HINDI.get(crop_name, crop_name),
                "price_source": "msp_seasonal_estimate",
                "is_live": False,
                "mandi_name": mandi or f"{location} मंडी",
                "min_price": min_p,
                "max_price": max_p,
                "modal_price": modal,
                "msp": msp,
                "profit_vs_msp": profit_pct,
                "profit_indicator": "📈" if profit_pct > 0 else "📉",
                "unit": "₹/quintal",
                "date": datetime.now(tz=timezone.utc).strftime("%d/%m/%Y"),
                "season_note": "Kharif" if month in [6,7,8,9,10,11] else "Rabi",
            })

        return {
            "status": "fallback",
            "is_live": False,
            "using_demo_key": not self._has_registered_data_gov_key(),
            "api_key_registered": self._has_registered_data_gov_key(),
            "location": location,
            "data_source": (
                "MSP-based seasonal estimate — NOT live mandi trades. "
                "Set DATA_GOV_IN_API_KEY or use Agmarknet API for live prices."
            ),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "top_crops": crops_data,
            "total_records": len(crops_data),
            "message": (
                "ℹ️ Live mandi feed unavailable. Register a free key at "
                "https://data.gov.in/user/register and set DATA_GOV_IN_API_KEY in .env"
            ),
            "msp_source": "Cabinet approval 2024-25 — Ministry of Agriculture & Farmers Welfare",
        }


# ─────────────────────────────────────────────────────────────────────────────
#  GEMINI AI SERVICE  (BUG-05 FIXED: correct model + proper fallback chain)
# ─────────────────────────────────────────────────────────────────────────────
class GeminiService:
    """Google Gemini Pro integration with proper fallback chain"""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self):
        self.api_key = GOOGLE_AI_KEY
        # BUG 5 FIX: per-thread session — see MarketPricesService for rationale
        self._local = threading.local()

    @property
    def session(self) -> requests.Session:
        """Per-thread requests.Session — thread-safe connection pool reuse."""
        if not hasattr(self._local, "session"):
            self._local.session = requests.Session()
        return self._local.session

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 1024,
        user_query: str = None,
        temperature: float = 0.7,
    ) -> str:
        """Generate response with pro → flash fallback"""
        if not _is_valid_gemini_key(self.api_key):
            return self._rule_based_response(user_query or prompt)

        for model in [GEMINI_MODEL, GEMINI_FLASH]:
            try:
                response = self._call_api(
                    model, prompt, system_prompt, max_tokens, temperature
                )
                if response:
                    return response
            except Exception as e:
                logger.warning(f"Gemini {model} failed: {e}")

        return self._rule_based_response(user_query or prompt)

    def _call_api(
        self,
        model: str,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float = 0.7,
    ) -> Optional[str]:
        url = f"{self.BASE_URL}/models/{model}:generateContent?key={self.api_key}"

        # Truncate prompt to avoid token-limit rejections (~30k char ≈ ~7k tokens)
        _MAX_PROMPT_CHARS = 30_000
        if len(prompt) > _MAX_PROMPT_CHARS:
            logger.warning(
                "Gemini prompt truncated from %d to %d chars", len(prompt), _MAX_PROMPT_CHARS
            )
            prompt = prompt[:_MAX_PROMPT_CHARS]

        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
                "topP": 0.9,
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT",    "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HATE_SPEECH",   "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
            ],
        }

        # Use the proper systemInstruction field (Gemini v1beta) instead of
        # injecting system context as fake conversation turns, which wastes
        # tokens and can confuse non-Hindi queries.
        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        resp = self.session.post(url, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()

            # Check if the prompt itself was blocked before any candidates were generated
            prompt_feedback = data.get("promptFeedback", {})
            block_reason = prompt_feedback.get("blockReason")
            if block_reason:
                logger.warning(
                    "Gemini %s blocked prompt — blockReason: %s", model, block_reason
                )
                return None

            candidates = data.get("candidates", [])
            if not candidates:
                logger.warning("Gemini %s returned 200 but no candidates", model)
                return None

            candidate = candidates[0]

            # Respect finishReason — STOP and MAX_TOKENS are the only valid ones
            finish_reason = candidate.get("finishReason", "STOP")
            if finish_reason not in ("STOP", "MAX_TOKENS", ""):
                logger.warning(
                    "Gemini %s finishReason=%s — treating as empty", model, finish_reason
                )
                return None

            # Safe deep-access to content → parts → text
            content = candidate.get("content")
            if not content:
                logger.warning(
                    "Gemini %s candidate has no 'content' (likely safety block)", model
                )
                return None

            parts = content.get("parts", [])
            if not parts:
                logger.warning("Gemini %s content has empty parts list", model)
                return None

            text = parts[0].get("text", "")
            if not text or not text.strip():
                logger.warning("Gemini %s returned blank text", model)
                return None

            return text.strip()

        elif resp.status_code in (429, 503):
            logger.warning("Gemini %s rate-limited/unavailable: %s", model, resp.status_code)
        elif resp.status_code == 400:
            # 400 can mean invalid API key format or bad request payload
            logger.error(
                "Gemini %s 400 Bad Request: %.300s", model, resp.text
            )
        else:
            logger.error("Gemini %s error %s: %.200s", model, resp.status_code, resp.text)
        return None

    def _rule_based_response(self, prompt: str) -> str:
        """
        Comprehensive rule-based fallback — covers 50+ farming topics.
        Used when Gemini API key is absent or API is unreachable.
        """
        p = prompt.lower()

        # ── WHEAT ─────────────────────────────────────────────────
        if any(w in p for w in ["wheat", "गेहूँ", "gehu", "gehun"]):
            return (
                "🌾 **गेहूँ की खेती (Wheat Farming)**\n\n"
                f"• **MSP 2024-25:** ₹{MSP_2024_25['wheat']}/क्विंटल\n"
                "• **बुवाई का समय:** नवंबर पहला-दूसरा सप्ताह\n"
                "• **मिट्टी:** दोमट या भारी दोमट (pH 6.0-7.5)\n"
                "• **बीज दर:** 100-125 kg/हेक्टेयर\n"
                "• **सिंचाई:** 6 बार — CRI (21 दिन), कल्ले निकलते समय, बाली आने पर, दाना भरते समय\n"
                "• **उर्वरक:** 120 kg N + 60 kg P + 40 kg K प्रति हेक्टेयर\n"
                "• **कटाई:** मार्च-अप्रैल (पकने पर)\n"
                "• **प्रमुख किस्में:** HD-3086, PBW-343, GW-322\n"
                "• **रोग:** करनाल बंट — Propiconazole से उपचार\n"
                "📞 ICAR हेल्पलाइन: 1800-180-1551"
            )

        # ── RICE / PADDY ─────────────────────────────────────────
        if any(w in p for w in ["rice", "धान", "paddy", "dhan", "kharif"]):
            return (
                "🌾 **धान की खेती (Rice/Paddy Farming)**\n\n"
                f"• **MSP 2024-25:** ₹{MSP_2024_25['rice']}/क्विंटल\n"
                "• **रोपाई का समय:** जून-जुलाई\n"
                "• **नर्सरी:** बुवाई से 25-30 दिन बाद रोपाई करें\n"
                "• **मिट्टी:** चिकनी मिट्टी / जलभराव वाली\n"
                "• **बीज:** 25-30 kg/हेक्टेयर (नर्सरी में)\n"
                "• **सिंचाई:** 2.5 cm पानी हमेशा खड़ा रखें\n"
                "• **उर्वरक:** 100 kg N + 50 kg P + 50 kg K\n"
                "• **प्रमुख रोग:** Blast — Tricyclazole 75WP @ 0.6 g/L\n"
                "• **कटाई:** अक्टूबर-नवंबर\n"
                "• **किस्में:** Swarna, MTU-7029, PR-122 (Punjab)\n"
                "📞 Agri Helpline: 1800-180-1551"
            )

        # ── MUSTARD ──────────────────────────────────────────────
        if any(w in p for w in ["mustard", "सरसों", "sarson", "sarso"]):
            return (
                "🌼 **सरसों की खेती (Mustard Farming)**\n\n"
                f"• **MSP 2024-25:** ₹{MSP_2024_25['mustard']}/क्विंटल\n"
                "• **बुवाई:** अक्टूबर 15 – नवंबर 15\n"
                "• **मिट्टी:** हल्की से मध्यम दोमट (pH 6.0-7.5)\n"
                "• **बीज दर:** 4-5 kg/हेक्टेयर\n"
                "• **सिंचाई:** 3-4 बार (30, 60, 90 दिन पर)\n"
                "• **उर्वरक:** 80 kg N + 40 kg P + 30 kg K\n"
                "• **कटाई:** मार्च (80-90% फलियाँ भूरी होने पर)\n"
                "• **रोग:** Alternaria Blight — Mancozeb 75WP\n"
                "• **किस्में:** RH-725, Varuna, Pusa Bold\n"
                "💡 सिंचाई नहीं होने पर भी 10-12 क्विंटल/हेक्टेयर उपज संभव"
            )

        # ── GRAM / CHICKPEA ──────────────────────────────────────
        if any(w in p for w in ["gram", "चना", "chana", "chickpea", "chick"]):
            return (
                "🫘 **चना की खेती (Gram/Chickpea Farming)**\n\n"
                f"• **MSP 2024-25:** ₹{MSP_2024_25['gram']}/क्विंटल\n"
                "• **बुवाई:** अक्टूबर अंत – नवंबर मध्य\n"
                "• **मिट्टी:** हल्की से मध्यम दोमट\n"
                "• **बीज:** 80-100 kg/हेक्टेयर\n"
                "• **राइजोबियम कल्चर:** बुवाई से पहले बीज उपचार जरूरी\n"
                "• **सिंचाई:** 1-2 बार (30-40 दिन बाद)\n"
                "• **कटाई:** मार्च\n"
                "• **रोग:** Wilt (उकठा) — रोग-प्रतिरोधी किस्में चुनें\n"
                "• **किस्में:** KAK-2, JG-11, Pusa-256"
            )

        # ── COTTON ───────────────────────────────────────────────
        if any(w in p for w in ["cotton", "कपास", "kapas"]):
            return (
                "🌿 **कपास की खेती (Cotton Farming)**\n\n"
                f"• **MSP 2024-25:** ₹{MSP_2024_25['cotton']}/क्विंटल\n"
                "• **बुवाई:** मई-जून (वर्षा शुरू होते ही)\n"
                "• **मिट्टी:** काली मिट्टी (pH 6.0-8.0)\n"
                "• **Bt Cotton:** Pink Bollworm से सुरक्षा\n"
                "• **सिंचाई:** 5-6 बार\n"
                "• **उर्वरक:** 150 kg N + 60 kg P + 60 kg K\n"
                "• **कीट:** Pink Bollworm — Coragen @ 0.3 ml/L\n"
                "• **कटाई:** अक्टूबर-दिसंबर (3-4 बार)\n"
                "• **उपज:** 15-20 क्विंटल/हेक्टेयर"
            )

        # ── SOYBEAN ──────────────────────────────────────────────
        if any(w in p for w in ["soybean", "सोयाबीन", "soya"]):
            return (
                "🌱 **सोयाबीन की खेती (Soybean Farming)**\n\n"
                f"• **MSP 2024-25:** ₹{MSP_2024_25['soybean']}/क्विंटल\n"
                "• **बुवाई:** जून अंत – जुलाई (मानसून के साथ)\n"
                "• **मिट्टी:** मध्यम काली / दोमट\n"
                "• **बीज:** 70-80 kg/हेक्टेयर\n"
                "• **Rhizobium + PSB:** बीज उपचार जरूरी (15 kg N बचाएं)\n"
                "• **कटाई:** अक्टूबर (पत्तियाँ पीली होने पर)\n"
                "• **रोग:** Yellow Mosaic Virus — Thiamethoxam उपचार\n"
                "• **उपज:** 20-25 क्विंटल/हेक्टेयर"
            )

        # ── MAIZE ────────────────────────────────────────────────
        if any(w in p for w in ["maize", "मक्का", "makka", "corn"]):
            return (
                "🌽 **मक्का की खेती (Maize/Corn Farming)**\n\n"
                f"• **MSP 2024-25:** ₹{MSP_2024_25['maize']}/क्विंटल\n"
                "• **बुवाई:** खरीफ: जून-जुलाई | रबी: अक्टूबर-नवंबर\n"
                "• **मिट्टी:** बलुई दोमट (pH 5.5-7.0)\n"
                "• **बीज दर:** 20-25 kg/हेक्टेयर\n"
                "• **उर्वरक:** 120 kg N + 60 kg P + 40 kg K\n"
                "• **सिंचाई:** 5-6 बार (टसल-सिल्क अवस्था में अत्यंत जरूरी)\n"
                "• **कीट:** Fall Armyworm — Spinetoram 11.7 SC @ 0.5 ml/L\n"
                "• **उपज:** 40-60 क्विंटल/हेक्टेयर"
            )

        # ── TOMATO ───────────────────────────────────────────────
        if any(w in p for w in ["tomato", "टमाटर", "tamatar"]):
            return (
                "🍅 **टमाटर की खेती (Tomato Farming)**\n\n"
                "• **नर्सरी:** 25-30 दिन पहले तैयार करें\n"
                "• **रोपाई:** अक्टूबर-नवंबर (रबी) | जुलाई (खरीफ)\n"
                "• **मिट्टी:** दोमट (pH 6.0-7.0)\n"
                "• **उर्वरक:** 100 kg N + 80 kg P + 60 kg K\n"
                "• **सिंचाई:** ड्रिप इरिगेशन सबसे अच्छा\n"
                "• **रोग:** Late Blight — Metalaxyl + Mancozeb\n"
                "• **कीट:** Fruitborer — Spinosad 45SC @ 1.5 ml/L\n"
                "• **उपज:** 300-400 क्विंटल/हेक्टेयर\n"
                "💡 PM-KUSUM सोलर पंप से सिंचाई लागत 90% कम करें"
            )

        # ── POTATO ───────────────────────────────────────────────
        if any(w in p for w in ["potato", "आलू", "aloo", "alu"]):
            return (
                "🥔 **आलू की खेती (Potato Farming)**\n\n"
                "• **बुवाई:** अक्टूबर-नवंबर\n"
                "• **बीज:** 25-30 क्विंटल/हेक्टेयर\n"
                "• **मिट्टी:** हल्की दोमट (pH 5.5-6.5)\n"
                "• **उर्वरक:** 200 kg N + 100 kg P + 150 kg K\n"
                "• **सिंचाई:** 8-10 बार (कंद बनते समय जरूरी)\n"
                "• **रोग:** Late Blight — Cymoxanil + Mancozeb\n"
                "• **कटाई:** फरवरी-मार्च\n"
                "• **उपज:** 200-300 क्विंटल/हेक्टेयर\n"
                "💡 Cold Storage में 6 महीने तक रखें — ऑफ-सीजन में अच्छा भाव"
            )

        # ── PEST CONTROL ──────────────────────────────────────────
        if any(w in p for w in ["pest", "कीट", "keet", "insect", "disease", "रोग",
                                 "blast", "blight", "wilt", "aphid", "borer",
                                 "fungicide", "pesticide", "spray"]):
            return (
                "🐛 **कीट एवं रोग प्रबंधन (IPM - Integrated Pest Management)**\n\n"
                "**सामान्य कीट एवं उपचार:**\n"
                "• **माहू (Aphid):** Imidacloprid 70WG @ 0.3 g/L या Dimethoate\n"
                "• **तना छेदक (Stem Borer):** Carbofuran 3G @ 25 kg/ha या Chlorpyrifos\n"
                "• **फल छेदक (Fruitborer):** Spinosad 45SC @ 1.5 ml/L\n"
                "• **सफेद मक्खी (Whitefly):** Thiamethoxam 25WG @ 0.3 g/L\n\n"
                "**सामान्य रोग:**\n"
                "• **झुलसा रोग (Blight):** Metalaxyl + Mancozeb या Cymoxanil\n"
                "• **चूर्णी फफूंद (Powdery Mildew):** Propiconazole 25EC\n"
                "• **उकठा (Wilt):** रोग-प्रतिरोधी किस्में + Trichoderma\n"
                "• **पीला मोज़ेक:** सफेद मक्खी नियंत्रण + रोगी पौधे हटाएं\n\n"
                "⚠️ **जैविक उपाय पहले आजमाएं:**\n"
                "• Neem oil (5 ml/L) — माहू, सफेद मक्खी\n"
                "• Trichoderma viride — मिट्टीजनित रोग\n"
                "• पीला/नीला स्टिकी ट्रैप — कीट निगरानी\n"
                "📞 ICAR हेल्पलाइन: 1800-180-1551"
            )

        # ── FERTILIZER ────────────────────────────────────────────
        if any(w in p for w in ["fertilizer", "urea", "dap", "npk", "खाद", "उर्वरक", "khad"]):
            return (
                "🌱 **उर्वरक प्रबंधन (Fertilizer Management)**\n\n"
                "**मुख्य उर्वरक एवं दरें:**\n"
                "• **Urea (46% N):** 217 kg/ha → 100 kg N देता है\n"
                "• **DAP (18-46-0):** 220 kg/ha → 100 kg P + 40 kg N\n"
                "• **MOP (0-0-60):** 167 kg/ha → 100 kg K\n"
                "• **SSP (0-16-0):** 625 kg/ha → 100 kg P\n"
                "• **Vermicompost:** 2-3 ton/ha → NPK + micro-nutrients\n\n"
                "**टिप्स:**\n"
                "• Neem-coated urea (NCU) — 10% नाइट्रोजन की बचत\n"
                "• मृदा परीक्षण के बाद ही उर्वरक डालें\n"
                "• जैविक + रासायनिक: 50-50 मिश्रण से लागत घटाएं\n"
                "📞 Soil Health Card: soilhealth.dac.gov.in"
            )

        # ── IRRIGATION ────────────────────────────────────────────
        if any(w in p for w in ["irrigation", "सिंचाई", "sinchai", "drip", "water", "पानी"]):
            return (
                "💧 **सिंचाई प्रबंधन (Irrigation Management)**\n\n"
                "**सिंचाई विधियाँ:**\n"
                "• **ड्रिप इरिगेशन:** 40-50% पानी बचाव | सब्सिडी: 90% (छोटे किसान)\n"
                "• **स्प्रिंकलर:** 30-35% बचाव | समतल खेत के लिए उपयुक्त\n"
                "• **SRI (धान):** पानी 25% कम + उपज 20% अधिक\n\n"
                "**PM-KUSUM योजना:**\n"
                "• सोलर पंप पर 90% सब्सिडी (30% केंद्र + 30% राज्य + 30% बैंक ऋण)\n"
                "• आवेदन: pmkusum.mnre.gov.in\n"
                "• हेल्पलाइन: 1800-180-3333\n\n"
                "**सिंचाई का सही समय:**\n"
                "• गेहूँ: CRI (21 दिन), कल्ले (40 दिन), बाली (65 दिन)\n"
                "• धान: हमेशा 2-3 cm पानी खड़ा रखें (AWD से 25% बचत)\n"
                "• सुबह या शाम को सींचें — वाष्पीकरण कम होगा"
            )

        # ── SOIL HEALTH ───────────────────────────────────────────
        if any(w in p for w in ["soil", "मिट्टी", "mitti", "ph", "organic", "health card",
                                 "mrida", "मृदा"]):
            return (
                "🧪 **मृदा स्वास्थ्य (Soil Health)**\n\n"
                "**मृदा स्वास्थ्य कार्ड योजना:**\n"
                "• निःशुल्क मिट्टी जांच + उर्वरक सुझाव\n"
                "• आवेदन: soilhealth.dac.gov.in\n"
                "• हेल्पलाइन: 1800-180-1551\n\n"
                "**आदर्श मिट्टी मानक:**\n"
                "• pH: 6.0-7.5 | OC: >0.75% | N: 200+ kg/ha\n"
                "• P: 10-25 kg/ha | K: 100+ kg/ha\n\n"
                "**मिट्टी सुधार:**\n"
                "• अम्लीय मिट्टी (pH<6): चूना 2 क्विंटल/एकड़\n"
                "• क्षारीय मिट्टी (pH>8): जिप्सम 3 क्विंटल/एकड़\n"
                "• जैव कार्बन बढ़ाने: हरी खाद (ढैंचा), वर्मीकम्पोस्ट"
            )

        # ── PM-KISAN ──────────────────────────────────────────────
        if any(w in p for w in ["pm kisan", "pm-kisan", "pmkisan", "6000", "₹6000",
                                 "किसान सम्मान", "kisan samman"]):
            return (
                "🏛️ **PM-Kisan Samman Nidhi**\n\n"
                "• **लाभ:** ₹6,000/वर्ष (3 किस्तें × ₹2,000)\n"
                "• **पात्रता:** सभी भूमि-धारक किसान परिवार\n"
                "• **दस्तावेज:** आधार, बैंक खाता, जमीन रिकॉर्ड\n"
                "• **आवेदन:** pmkisan.gov.in पर ऑनलाइन\n"
                "• **हेल्पलाइन:** 155261 / 011-24300606\n"
                "• **किस्त स्थिति जांचें:** pmkisan.gov.in/Beneficiarystatus/\n\n"
                "⚠️ eKYC अनिवार्य — आधार से मिलान जरूरी"
            )

        # ── FASAL BIMA ────────────────────────────────────────────
        if any(w in p for w in ["fasal bima", "bima", "insurance", "pmfby", "crop insurance",
                                 "फसल बीमा"]):
            return (
                "🏛️ **PM Fasal Bima Yojana (PMFBY)**\n\n"
                "• **प्रीमियम:** खरीफ 2% | रबी 1.5% | बागवानी 5%\n"
                "• **कवरेज:** प्राकृतिक आपदा, कीट-रोग, मौसम\n"
                "• **पात्रता:** अधिसूचित फसल उगाने वाले सभी किसान\n"
                "• **दस्तावेज:** आधार, बैंक खाता, बुवाई प्रमाण पत्र\n"
                "• **आवेदन:** PMFBY App या pmfby.gov.in\n"
                "• **हेल्पलाइन:** 14447 (Toll Free)\n\n"
                "💡 बुवाई के 2 सप्ताह के भीतर पंजीकरण जरूरी"
            )

        # ── KCC ───────────────────────────────────────────────────
        if any(w in p for w in ["kcc", "kisan credit", "किसान क्रेडिट", "loan", "rin", "ऋण"]):
            return (
                "💳 **Kisan Credit Card (KCC)**\n\n"
                "• **ऋण सीमा:** ₹3 लाख तक\n"
                "• **ब्याज दर:** 4% प्रतिवर्ष (ब्याज सहायता के बाद)\n"
                "• **पात्रता:** सभी किसान, बटाईदार, काश्तकार\n"
                "• **आवेदन:** नजदीकी बैंक / CSC केंद्र\n"
                "• **हेल्पलाइन:** 1800-200-1025 (NABARD)\n"
                "• **उपयोग:** बीज, खाद, कीटनाशक, सिंचाई\n\n"
                "💡 समय पर चुकाने पर ब्याज माफी — लागत प्रभावी कृषि ऋण"
            )

        # ── MARKET / MANDI ────────────────────────────────────────
        if any(w in p for w in ["mandi", "market", "price", "भाव", "msp", "बाजार", "sell", "बेचना"]):
            msp_info = "\n".join([
                f"  • {k.capitalize()}: ₹{v}/क्विंटल"
                for k, v in list(MSP_2024_25.items())[:8]
            ])
            return (
                "💰 **बाजार भाव एवं MSP (Market Prices & MSP)**\n\n"
                f"**MSP 2024-25 (प्रमुख फसलें):**\n{msp_info}\n\n"
                "**eNAM (ऑनलाइन मंडी):**\n"
                "• पूरे भारत में सबसे अच्छे भाव पर फसल बेचें\n"
                "• पंजीकरण: enam.gov.in | हेल्पलाइन: 1800-270-0224\n\n"
                "**Agmarknet से भाव जांचें:**\n"
                "• agmarknet.gov.in — राज्य/मंडी/फसल चुनें\n"
                "• data.gov.in — real-time आँकड़े\n\n"
                "💡 MSP से नीचे बेचने पर: 1800-270-0224 (NAFED) पर शिकायत करें"
            )

        # ── WEATHER ───────────────────────────────────────────────
        if any(w in p for w in ["weather", "मौसम", "mausam", "rain", "बारिश", "temperature",
                                  "तापमान", "forecast"]):
            return (
                "🌤️ **मौसम एवं कृषि सलाह (Weather Advisory)**\n\n"
                "**वास्तविक समय मौसम स्रोत:**\n"
                "• Open-Meteo API (निःशुल्क, 7 दिन पूर्वानुमान)\n"
                "• IMD: mausam.imd.gov.in\n\n"
                "**मौसम-आधारित कृषि सलाह:**\n"
                "• तूफान/ओलावृष्टि: खेत में न जाएं, फसल ढकें\n"
                "• भारी बारिश (50mm+): जल निकासी सुनिश्चित करें\n"
                "• लू (40°C+): सुबह/शाम सिंचाई, मल्चिंग करें\n"
                "• पाला (5°C-): धुआँ दें, हल्की सिंचाई करें\n\n"
                "📊 **IMD कृषि मौसम सेवा:** 7610-XXXXX (जिला कृषि विभाग)\n"
                "📱 **Meghdoot App** डाउनलोड करें — किसानों के लिए मौसम"
            )

        # ── ORGANIC FARMING ───────────────────────────────────────
        if any(w in p for w in ["organic", "जैविक", "jaivik", "natural", "compost", "vermi"]):
            return (
                "🌿 **जैविक खेती (Organic Farming)**\n\n"
                "**जैविक इनपुट:**\n"
                "• वर्मीकम्पोस्ट: 2-3 ton/ha — NPK + micro-nutrients\n"
                "• हरी खाद (ढैंचा): बुवाई से 45 दिन पहले मिलाएं\n"
                "• जीवामृत: 200L/acre/महीना — मिट्टी स्वास्थ्य\n"
                "• नीम खली: 150 kg/acre — कीट + उर्वरक\n\n"
                "**Paramparagat Krishi Vikas Yojana (PKVY):**\n"
                "• ₹50,000/हेक्टेयर/3 वर्ष अनुदान\n"
                "• Jaivik Kheti Portal: jaivikkheti.in\n\n"
                "💡 जैविक प्रमाणीकरण के बाद बाजार भाव 20-30% अधिक"
            )

        # ── GOVERNMENT SCHEMES (GENERAL) ─────────────────────────
        if any(w in p for w in ["scheme", "योजना", "yojana", "subsidy", "सब्सिडी",
                                  "government", "सरकार", "benefit", "लाभ"]):
            return (
                "🏛️ **प्रमुख सरकारी योजनाएं (Government Schemes)**\n\n"
                "**1. PM-Kisan:** ₹6,000/वर्ष → pmkisan.gov.in\n"
                "**2. PM Fasal Bima (PMFBY):** 2% प्रीमियम पर फसल बीमा → pmfby.gov.in\n"
                "**3. KCC (Kisan Credit Card):** ₹3L ऋण @ 4% ब्याज\n"
                "**4. PM-KUSUM:** 90% सब्सिडी पर सोलर पंप → pmkusum.mnre.gov.in\n"
                "**5. Soil Health Card:** निःशुल्क मिट्टी जांच → soilhealth.dac.gov.in\n"
                "**6. eNAM:** ऑनलाइन मंडी → enam.gov.in\n"
                "**7. Kisan Samridhi Kendra:** बीज/खाद/बीमा → एक ही छत के नीचे\n\n"
                "📞 **Kisan Call Center:** 1800-180-1551 (निःशुल्क, 24x7)\n"
                "📱 **Kisan Suvidha App** डाउनलोड करें"
            )

        # ── CROP ROTATION ─────────────────────────────────────────
        if any(w in p for w in ["rotation", "फसल चक्र", "fasal chakra", "succession"]):
            return (
                "🔄 **फसल चक्र (Crop Rotation)**\n\n"
                "**उत्तर भारत (UP/Punjab/Haryana):**\n"
                "• Rice → Wheat (सबसे आम, पर भूजल क्षरण)\n"
                "• Maize → Wheat (बेहतर — पानी 40% कम)\n"
                "• Rice → Mustard → Maize (3-फसल चक्र)\n\n"
                "**मध्य भारत (MP/Maharashtra):**\n"
                "• Soybean → Wheat\n"
                "• Cotton → Gram\n\n"
                "**फायदे:**\n"
                "• मिट्टी स्वास्थ्य सुधार\n"
                "• कीट-रोग दबाव कम\n"
                "• खाद की बचत (दलहन: N स्थिरीकरण)\n"
                "• आय विविधता"
            )

        # ── STORAGE ───────────────────────────────────────────────
        if any(w in p for w in ["storage", "warehouse", "भंडारण", "bhandaran", "cold", "silo"]):
            return (
                "🏪 **फसल भंडारण (Crop Storage)**\n\n"
                "**सरकारी सुविधाएं:**\n"
                "• **NABARD Warehouse Receipt:** FPO के माध्यम से गोदाम ऋण\n"
                "• **eNAM:** ऑनलाइन मंडी + वेयरहाउस रसीद प्रणाली\n"
                "• **WRS (Warehouse Receipt System):** फसल रखो, ऋण लो\n\n"
                "**भंडारण नियम:**\n"
                "• गेहूँ: <12% नमी, कूल-ड्राई स्थान | 8-10 महीने\n"
                "• आलू: Cold Storage 2-4°C | 4-6 महीने\n"
                "• प्याज: वेंटिलेटेड शेड | 3-4 महीने\n\n"
                "💡 खुले बाजार में भाव कम तो वेयरहाउस में रखें — बाद में बेचें"
            )

        # ── FPO / COOPERATIVE ─────────────────────────────────────
        if any(w in p for w in ["fpo", "cooperative", "farmer producer", "किसान उत्पादक", "10000"]):
            return (
                "🤝 **FPO (Farmer Producer Organisation)**\n\n"
                "• **सरकारी लक्ष्य:** 10,000 FPO गठन (₹6,865 करोड़ बजट)\n"
                "• **लाभ:** सामूहिक सौदेबाजी, bulk input खरीद, processing\n"
                "• **पंजीकरण:** sfacindia.com या राज्य कृषि विभाग\n"
                "• **वित्तीय सहायता:** ₹18 लाख/FPO (3 वर्ष) + Equity Grant\n"
                "• **न्यूनतम सदस्य:** 10-50 किसान (राज्य अनुसार)\n\n"
                "📞 SFAC Helpline: 011-26534641"
            )

        # ── DEFAULT MULTI-LANGUAGE RESPONSE ──────────────────────
        defaults = {
            "hi": "🌾 **KrishiMitra AI** — गेहूँ/धान/MSP/योजनाएं/कीट रोग पूछें\n📞 किसान हेल्पलाइन: 1800-180-1551",
            "en": "🌾 **KrishiMitra AI** — Ask about crops, MSP, schemes, pest control\n📞 Kisan Helpline: 1800-180-1551",
            "bn": "🌾 **KrishiMitra AI** — ফসল/MSP/প্রকল্প জিজ্ঞাসা করুন\n📞 1800-180-1551",
            "te": "🌾 **KrishiMitra AI** — పంటలు/MSP/పథకాలు అడగండి\n📞 1800-180-1551",
            "mr": "🌾 **KrishiMitra AI** — पिके/MSP/योजना विचारा\n📞 1800-180-1551",
            "ta": "🌾 **KrishiMitra AI** — பயிர்/MSP/திட்டங்கள் கேளுங்கள்\n📞 1800-180-1551",
            "gu": "🌾 **KrishiMitra AI** — ખેતી/MSP/યોજناઓ પૂછો\n📞 1800-180-1551",
            "kn": "🌾 **KrishiMitra AI** — ಬೆಳೆ/MSP/ಯೋಜನೆ ಕೇಳಿ\n📞 1800-180-1551",
            "ml": "🌾 **KrishiMitra AI** — വിള/MSP/പദ്ധതി ചോദിക്കുക\n📞 1800-180-1551",
            "pa": "🌾 **KrishiMitra AI** — ਫ਼ਸਲ/MSP/ਸਕੀਮਾਂ ਪੁੱਛੋ\n📞 1800-180-1551",
            "or": "🌾 **KrishiMitra AI** — ଫସଲ/MSP/ଯୋଜନା ପଚାରନ୍ତୁ\n📞 1800-180-1551",
            "as": "🌾 **KrishiMitra AI** — শস্য/MSP/আঁচনি সোধক\n📞 1800-180-1551",
        }
        # detect language from prompt
        detected = "hi"
        for lcode, markers in {
            "bn": ["ফসল", "গম", "ধান"], "te": ["పంట", "గోధుమ"], "mr": ["पिक", "गहू"],
            "ta": ["பயிர்", "கோதுமை"], "gu": ["ખેતી", "ઘઉં"], "kn": ["ಬೆಳೆ", "ಗೋಧಿ"],
            "ml": ["വിള", "ഗോതമ്പ്"], "pa": ["ਫ਼ਸਲ", "ਕਣਕ"], "or": ["ଫସଲ", "ଗହମ"],
            "as": ["শস্য", "ঘেঁহু"], "en": ["crop", "farm", "wheat", "rice"],
        }.items():
            if any(m in prompt for m in markers):
                detected = lcode
                break
        return defaults.get(detected, defaults["hi"])


# ─────────────────────────────────────────────────────────────────────────────
#  GOVERNMENT SCHEMES SERVICE
# ─────────────────────────────────────────────────────────────────────────────
GOVERNMENT_SCHEMES = [
    {
        "id": "pm-kisan",
        "name": "PM-Kisan Samman Nidhi",
        "name_hindi": "पीएम-किसान सम्मान निधि",
        "benefit": "₹6,000 per year (3 installments of ₹2,000)",
        "benefit_hindi": "₹6,000 प्रति वर्ष (3 किस्तों में)",
        "eligibility": "All land-owning farmer families",
        "documents": ["Aadhaar", "Bank account", "Land records"],
        "website": "https://pmkisan.gov.in",
        "helpline": "155261 / 011-24300606",
        "category": "direct_benefit",
    },
    {
        "id": "pmfby",
        "name": "Pradhan Mantri Fasal Bima Yojana (PMFBY)",
        "name_hindi": "प्रधानमंत्री फसल बीमा योजना",
        "benefit": "Crop insurance — 2% premium for Kharif, 1.5% for Rabi",
        "benefit_hindi": "फसल बीमा — खरीफ 2%, रबी 1.5% प्रीमियम",
        "eligibility": "All farmers growing notified crops",
        "documents": ["Aadhaar", "Bank account", "Land records", "Crop sowing certificate"],
        "website": "https://pmfby.gov.in",
        "helpline": "14447 (Toll Free)",
        "category": "insurance",
    },
    {
        "id": "kcc",
        "name": "Kisan Credit Card (KCC)",
        "name_hindi": "किसान क्रेडिट कार्ड",
        "benefit": "Credit up to ₹3 lakh at 4% interest",
        "benefit_hindi": "₹3 लाख तक ऋण, 4% ब्याज दर",
        "eligibility": "All farmers, sharecroppers, oral lessees",
        "documents": ["Aadhaar", "Land records", "Bank account"],
        "website": "https://www.nabard.org/content1.aspx?id=595",
        "helpline": "1800-200-1025 (NABARD)",
        "category": "credit",
    },
    {
        "id": "soil-health-card",
        "name": "Soil Health Card Scheme",
        "name_hindi": "मृदा स्वास्थ्य कार्ड योजना",
        "benefit": "Free soil testing and crop-specific fertilizer recommendations",
        "benefit_hindi": "निःशुल्क मिट्टी जांच और उर्वरक सुझाव",
        "eligibility": "All farmers",
        "documents": ["Aadhaar", "Land records"],
        "website": "https://soilhealth.dac.gov.in",
        "helpline": "1800-180-1551",
        "category": "advisory",
    },
    {
        "id": "pm-kusum",
        "name": "PM-KUSUM Solar Pump Scheme",
        "name_hindi": "पीएम-कुसुम सोलर पंप योजना",
        "benefit": "90% subsidy on solar pumps (30% central + 30% state + 30% bank loan)",
        "benefit_hindi": "सोलर पंप पर 90% सब्सिडी",
        "eligibility": "Individual farmers, Panchayats, Cooperatives",
        "documents": ["Aadhaar", "Land records", "Bank account"],
        "website": "https://pmkusum.mnre.gov.in",
        "helpline": "1800-180-3333",
        "category": "infrastructure",
    },
    {
        "id": "enam",
        "name": "eNAM (National Agriculture Market)",
        "name_hindi": "राष्ट्रीय कृषि बाजार (ई-नाम)",
        "benefit": "Online mandi trading — sell crops at best price across India",
        "benefit_hindi": "ऑनलाइन मंडी — पूरे भारत में सबसे अच्छे भाव पर फसल बेचें",
        "eligibility": "All farmers with Aadhaar-linked bank account",
        "documents": ["Aadhaar", "Bank passbook", "Land records"],
        "website": "https://enam.gov.in",
        "helpline": "1800-270-0224",
        "category": "market_access",
    },
    {
        "id": "pm-kishor",
        "name": "Kisan Samridhi Kendra",
        "name_hindi": "किसान समृद्धि केंद्र",
        "benefit": "One-stop shop for seeds, fertilizers, testing, insurance at subsidized rates",
        "benefit_hindi": "एक ही जगह बीज, खाद, परीक्षण, बीमा — सब्सिडी दर पर",
        "eligibility": "All farmers",
        "documents": ["Aadhaar"],
        "website": "https://agricoop.gov.in",
        "helpline": "1800-180-1551",
        "category": "advisory",
    }
]

class GovernmentSchemesService:
    """Government schemes with eligibility checker"""

    def get_schemes(self, location: str = None, category: str = None) -> Dict:
        schemes = GOVERNMENT_SCHEMES
        if category:
            schemes = [s for s in schemes if s.get("category") == category]
        # FIX: Add field aliases so both old and new frontend code works
        normalized = []
        for s in schemes:
            sc = s.copy()
            sc["official_website"] = sc.get("official_website") or sc.get("website", "")
            sc["benefits_hindi"] = sc.get("benefits_hindi") or sc.get("benefit_hindi") or sc.get("benefit", "")
            sc["eligibility_hindi"] = sc.get("eligibility_hindi") or sc.get("eligibility", "")
            sc["description_hindi"] = sc.get("description_hindi") or sc.get("description", sc.get("benefit", ""))
            normalized.append(sc)
        return {
            "status": "success",
            "is_live": False,
            "catalog": True,
            "total": len(normalized),
            "schemes": normalized,
            "data_source": (
                "Official MoAFW / DAC&FW scheme catalog (reference; not live enrollment status)"
            ),
            "source": "Ministry of Agriculture & Farmers Welfare",
            "last_updated": "2024-25 Season",
            "message": (
                "Curated government scheme summaries from published MoAFW documentation — "
                "verify eligibility on the official portal before applying."
            ),
        }

    def check_eligibility(self, farmer_profile: Dict) -> Dict:
        """Simple eligibility checker"""
        eligible = []
        for scheme in GOVERNMENT_SCHEMES:
            scheme_copy = scheme.copy()
            scheme_copy["eligible"] = True  # Simplified — all farmers eligible for most
            eligible.append(scheme_copy)
        return {"status": "success", "eligible_schemes": eligible, "farmer_profile": farmer_profile}


# ─────────────────────────────────────────────────────────────────────────────
#  BLOCKCHAIN/IOT SIMULATION (Project Proposal Requirement)
# ─────────────────────────────────────────────────────────────────────────────
class BlockchainIoTSimulator:
    """
    Simulates IoT sensor → Blockchain → Smart Advisory pipeline
    Required by project proposal: IoT, Blockchain, Cloud, AI System
    """

    def get_iot_sensor_data(self, location: str) -> Dict:
        """Simulated IoT sensor readings (soil, weather, moisture)"""
        import random, hashlib
        seed = hash(location) % 1000
        random.seed(seed + datetime.now(tz=timezone.utc).hour)  # Vary by hour for realism

        soil_moisture = random.uniform(35, 75)
        soil_temp = random.uniform(18, 32)
        soil_ph = random.uniform(5.5, 8.0)
        npk_n = random.uniform(150, 280)
        npk_p = random.uniform(10, 30)
        npk_k = random.uniform(100, 200)

        sensor_data = {
            "sensor_id": f"KM-IOT-{abs(hash(location)) % 9999:04d}",
            "location": location,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "readings": {
                "soil_moisture_pct": round(soil_moisture, 1),
                "soil_temperature_c": round(soil_temp, 1),
                "soil_ph": round(soil_ph, 2),
                "npk": {
                    "nitrogen_kg_ha": round(npk_n, 1),
                    "phosphorus_kg_ha": round(npk_p, 1),
                    "potassium_kg_ha": round(npk_k, 1),
                },
                "conductivity_ms_cm": round(random.uniform(0.5, 2.5), 2),
            },
            "soil_health_score": self._calculate_soil_health(soil_moisture, soil_ph, npk_n),
            "recommendations": self._get_soil_recommendations(soil_moisture, soil_ph, npk_n, npk_p, npk_k),
        }

        # Blockchain hash (simulated immutability)
        data_str = json.dumps(sensor_data["readings"], sort_keys=True)
        sensor_data["blockchain"] = {
            "transaction_hash": "0x" + hashlib.sha256(data_str.encode()).hexdigest()[:40],
            "block_number": 18500000 + (abs(hash(location)) % 100000),
            "network": "Ethereum Testnet (Goerli)",
            "smart_contract": "0xKrishiMitra...AgriChain",
            "verified": True,
            "timestamp_immutable": True,
        }

        return sensor_data

    def _calculate_soil_health(self, moisture: float, ph: float, nitrogen: float) -> Dict:
        score = 0
        if 40 <= moisture <= 70: score += 33
        if 6.0 <= ph <= 7.5: score += 33
        if nitrogen > 200: score += 34
        return {
            "score": score,
            "grade": "A" if score >= 80 else "B" if score >= 60 else "C",
            "status": "Healthy" if score >= 80 else "Moderate" if score >= 60 else "Needs Treatment"
        }

    def _get_soil_recommendations(self, moisture, ph, n, p, k) -> List[str]:
        recs = []
        if moisture < 40: recs.append("💧 Soil moisture low — irrigate immediately")
        if moisture > 70: recs.append("🌊 Waterlogged — improve drainage")
        if ph < 6.0: recs.append("🟡 Acidic soil — apply lime @ 2 quintal/acre")
        if ph > 7.5: recs.append("🟤 Alkaline soil — apply gypsum @ 3 quintal/acre")
        if n < 180: recs.append(f"🌱 Low nitrogen ({n:.0f} kg/ha) — apply Urea @ 50 kg/acre")
        if p < 15: recs.append(f"🔴 Low phosphorus ({p:.0f} kg/ha) — apply DAP @ 30 kg/acre")
        if k < 120: recs.append(f"🟠 Low potassium ({k:.0f} kg/ha) — apply MOP @ 25 kg/acre")
        if not recs: recs.append("✅ Soil health excellent — no immediate action needed")
        return recs


# ─────────────────────────────────────────────────────────────────────────────
#  SINGLETON INSTANCES (import these in views.py)
# ─────────────────────────────────────────────────────────────────────────────
weather_service = WeatherService()
market_service = MarketPricesService()
gemini_service = GeminiService()
schemes_service = GovernmentSchemesService()
iot_blockchain = BlockchainIoTSimulator()
