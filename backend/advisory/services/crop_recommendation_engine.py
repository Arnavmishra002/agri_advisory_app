#!/usr/bin/env python3
"""
KrishiMitra Crop Recommendation Engine v3.0
Multi-factor scoring using 150+ crop database + real-time data.

Scoring factors (total 100 points):
  1. Season match           — 25 pts
  2. Soil suitability       — 20 pts
  3. Water / irrigation     — 15 pts
  4. Temperature suitability — 10 pts
  5. Market demand + MSP    — 10 pts
  6. Regional priority      — 10 pts
  7. Live weather outlook   — 10 pts (drought / flood / heatwave penalty)
"""

from __future__ import annotations

import logging
import os
import re
import atexit
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .location_context import LocationContext
from .unified_realtime_service import market_service, weather_service
try:
    from .comprehensive_crop_database import ALL_CROP_DATA
except Exception:
    ALL_CROP_DATA = {}

logger = logging.getLogger(__name__)

_REC_FETCH_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="crop-rec-fetch")
atexit.register(_REC_FETCH_POOL.shutdown, wait=False, cancel_futures=True)

# Rainfall category boundaries (mm/year)
RAINFALL_BANDS = {
    "Very Low": (0,   350),
    "Low":      (350, 700),
    "Medium":   (700, 1200),
    "High":     (1200, 2000),
    "Very High":(2000, 9999),
}

# Water requirement → minimum irrigation level needed when rainfall is Low
WATER_IRRIGATION_MIN = {
    "Low":       "Low",
    "Moderate":  "Low",
    "High":      "Medium",
    "Very High": "High",
}

def _current_season() -> str:
    m = datetime.now().month
    # AGRONOMIC BUG FIX: Oct (10) and Nov (11) were in BOTH kharif and rabi sets.
    # Kharif is checked first, so Oct/Nov incorrectly returned "kharif" even though
    # this is the peak Rabi sowing window. Fix aligns with ICAR calendar:
    #   Kharif: sown Jun-Jul, harvested Sep-Oct  → Jun-Sep (months 6-9)
    #   Rabi:   sown Oct-Nov, harvested Mar-Apr  → Oct-Mar (months 10-12, 1-3)
    #   Zaid:   Apr-May (months 4-5)
    if m in (6, 7, 8, 9):
        return "kharif"
    if m in (10, 11, 12, 1, 2, 3):
        return "rabi"
    return "zaid"  # Apr-May

def _season_label(season_key: str) -> str:
    return {
        "kharif": "खरीफ (Kharif — June-Nov)",
        "rabi":   "रबी (Rabi — Oct-Mar)",
        "zaid":   "जायद (Zaid — Mar-Jun)",
        "year_round": "वर्ष भर (Year Round)",
    }.get(season_key, season_key)

def _rainfall_band(mm: Optional[float]) -> str:
    if mm is None:
        return "Medium"
    for band, (lo, hi) in RAINFALL_BANDS.items():
        if lo <= mm < hi:
            return band
    return "Very High"

def _irrigation_level(irr_str: Optional[str]) -> str:
    """Normalise irrigation strings to Low/Medium/High."""
    if not irr_str:
        return "Medium"
    s = str(irr_str).lower()
    if "high" in s:
        return "High"
    if "medium" in s or "moderate" in s:
        return "Medium"
    return "Low"


class CropRecommendationEngine:
    """
    Location-aware, multi-factor crop recommendation system.

    Priority order for location resolution:
      1. Exact district match in DISTRICT_PROFILES
      2. Fuzzy city/state match
      3. State-level defaults
      4. Generic India defaults
    """

    def __init__(self):
        # Defer import to avoid circular imports; reuse shared singleton if available
        try:
            from .ultra_dynamic_government_api import _gov_api_singleton
            self.gov_api = _gov_api_singleton
        except (ImportError, AttributeError):
            from .ultra_dynamic_government_api import UltraDynamicGovernmentAPI
            self.gov_api = UltraDynamicGovernmentAPI()

    # ── Public API ─────────────────────────────────────────────────────

    def recommend(
        self,
        location: str,
        latitude: float,
        longitude: float,
        state: Optional[str] = None,
        language: str = "hi",
    ) -> Dict[str, Any]:
        """Full recommendation pipeline with live weather and market data."""

        # 1. Resolve location profile — GPS-first in v4.0
        profile = self._resolve_location_profile(location, state, latitude, longitude)

        # 2. Get live weather + mandi prices concurrently with partial fallback
        weather, live_market, realtime_status = self._fetch_realtime_context(
            location, latitude, longitude, state, language
        )
        current_weather = weather.get("current") or {}
        forecast = weather.get("forecast_7day") or weather.get("forecast_7_days") or []

        # 3. Build live market signal map
        market_price_map = self._build_market_price_map(live_market)

        # 4. Score all crops
        season_key = _current_season()
        scored = self._score_all_crops(profile, season_key, current_weather, forecast, market_price_map)

        # 5. Localise and format
        recommendations = self._format_recommendations(scored[:12], language, market_price_map, profile)

        return {
            "location": location,
            "state": state or profile.get("state", ""),
            "coordinates": {"lat": latitude, "lon": longitude},
            "region": profile.get("region", "India"),
            "agro_zone": profile.get("agro_zone", ""),
            "season": _season_label(season_key),
            "season_key": season_key,
            "soil_type": profile.get("soil", "Loamy"),
            "irrigation": profile.get("irrigation", "Medium"),
            "recommendations": recommendations,
            "top_4_recommendations": recommendations[:4],
            "weather_snapshot": current_weather,
            "weather_status": weather.get("status", "success"),
            "weather_is_live": bool(weather.get("is_live", bool(current_weather))),
            "weather_data_source": weather.get("data_source", ""),
            "weather_fetched_at": weather.get("fetched_at"),
            "market_is_live": bool(live_market.get("is_live")),
            "market_status": live_market.get("status"),
            "market_data_source": live_market.get("data_source_short") or live_market.get("data_source", ""),
            "market_fetched_at": live_market.get("fetched_at") or live_market.get("timestamp"),
            "market_snapshot": (live_market.get("top_crops") or [])[:5],
            "realtime_status": realtime_status,
            "data_source": "KrishiMitra Agro-Climatic Engine v3 + Open-Meteo + Agmarknet",
            "analysis_method": "multi_factor_scoring_v3",
            "factors_analyzed": [
                f"Season: {_season_label(season_key)}",
                f"Soil: {profile.get('soil', 'Loamy')}",
                f"Rainfall: {profile.get('rainfall', 'Medium')}",
                f"Irrigation: {profile.get('irrigation', 'Medium')}",
                "Live 7-day weather forecast",
                "Live mandi modal prices vs MSP",
                f"{len(ALL_CROP_DATA)} crop agro-climatic profiles",
                "District-level priority crops",
            ],
            "profile_source": profile.get("_source", "state_default"),
            "timestamp": datetime.now().isoformat(),
            "language": language,
        }

    def _fetch_realtime_context(
        self,
        location: str,
        latitude: float,
        longitude: float,
        state: Optional[str],
        language: str,
    ) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, str]]:
        """Fetch weather and mandi signals without letting either block scoring."""
        timeout_s = float(os.getenv("CROP_REC_REALTIME_TIMEOUT_S", "5"))
        weather: Dict[str, Any] = {
            "status": "unavailable",
            "is_live": False,
            "current": {},
            "forecast_7day": [],
            "data_source": "not fetched",
        }
        market: Dict[str, Any] = {
            "status": "unavailable",
            "is_live": False,
            "top_crops": [],
            "data_source": "not fetched",
        }
        status_map = {"weather": "pending", "market": "pending"}

        futures = {
            _REC_FETCH_POOL.submit(
                weather_service.get_weather,
                location,
                latitude,
                longitude,
                lang=language,
            ): "weather",
            _REC_FETCH_POOL.submit(
                market_service.get_prices,
                location,
                lat=latitude,
                lon=longitude,
                state=state,
            ): "market",
        }

        try:
            for fut in as_completed(futures, timeout=timeout_s):
                key = futures[fut]
                try:
                    result = fut.result() or {}
                    if key == "weather":
                        weather = result
                    else:
                        market = result
                    status_map[key] = result.get("status") or (
                        "live" if result.get("is_live") else "success"
                    )
                except Exception as exc:
                    logger.warning("Crop rec %s fetch failed: %s", key, exc)
                    status_map[key] = "error"
        except FuturesTimeout:
            for fut, key in futures.items():
                if fut.done() and not fut.cancelled():
                    try:
                        result = fut.result(timeout=0) or {}
                        if key == "weather":
                            weather = result
                        else:
                            market = result
                        status_map[key] = result.get("status") or (
                            "live" if result.get("is_live") else "success"
                        )
                    except Exception:
                        status_map[key] = "error"
                elif not fut.done():
                    fut.cancel()
                    status_map[key] = "timeout"
            logger.warning(
                "Crop recommendation realtime fetch timed out after %.1fs for %s",
                timeout_s,
                location,
            )

        return weather, market, status_map

    @classmethod
    def recommend_from_context(cls, ctx: LocationContext, language: str = "hi") -> Dict[str, Any]:
        """Singleton-safe context-based entry point."""
        return crop_recommendation_engine.recommend(
            ctx.query_label,
            ctx.latitude,
            ctx.longitude,
            state=ctx.state or None,
            language=language,
        )

    # ── Location profile resolution ────────────────────────────────────

    def _resolve_location_profile(
        self,
        location: str,
        state: Optional[str],
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Return the best agro-climatic profile for the location.

        Priority order (v4.0 — GPS-first):
          1. Exact district match in DISTRICT_PROFILES
          2. Fuzzy district match
          3. GPS coordinate → nearest district (haversine, < 100 km radius)
          4. State-level match (first district in state)
          5. Keyword fallback
        """
        try:
            from .district_data import DISTRICT_PROFILES
        except ImportError:
            DISTRICT_PROFILES = {}

        loc_lower = location.lower().strip()

        # 1. Exact district match
        if loc_lower in DISTRICT_PROFILES:
            p = dict(DISTRICT_PROFILES[loc_lower])
            p["_source"] = "district_exact"
            p["region"] = p.get("state", "India")
            return p

        # 2. Partial district match
        for district_key, profile in DISTRICT_PROFILES.items():
            if district_key in loc_lower or loc_lower in district_key:
                p = dict(profile)
                p["_source"] = "district_fuzzy"
                p["region"] = p.get("state", "India")
                return p

        # 3. GPS coordinate → nearest district (NEW — uses lat/lon passed from recommend())
        if latitude is not None and longitude is not None:
            best_key, best_dist = None, float("inf")
            # District coordinate centroids (lat, lon) for closest-district lookup
            _DISTRICT_CENTROIDS = {
                # Punjab
                "amritsar": (31.634, 74.872), "ludhiana": (30.901, 75.857),
                "jalandhar": (31.326, 75.576), "patiala": (30.339, 76.386),
                "bathinda": (30.211, 74.946), "firozpur": (30.925, 74.614),
                # Haryana
                "karnal": (29.686, 76.990), "hisar": (29.151, 75.722),
                "rohtak": (28.895, 76.607), "gurgaon": (28.459, 77.027),
                "sirsa": (29.533, 75.022),
                # Uttar Pradesh
                "lucknow": (26.847, 80.946), "kanpur": (26.450, 80.332),
                "agra": (27.176, 78.008), "varanasi": (25.318, 82.974),
                "allahabad": (25.435, 81.846), "meerut": (28.984, 77.706),
                "moradabad": (28.839, 78.777), "bareilly": (28.367, 79.430),
                "gorakhpur": (26.760, 83.373), "noida": (28.535, 77.391),
                "mathura": (27.492, 77.673), "ayodhya": (26.795, 82.195),
                "jhansi": (25.448, 78.568), "sitapur": (27.564, 80.682),
                # Rajasthan
                "jaipur": (26.912, 75.787), "jodhpur": (26.239, 73.024),
                "barmer": (25.745, 71.395), "bikaner": (28.013, 73.312),
                "kota": (25.183, 75.838), "ajmer": (26.453, 74.639),
                "udaipur": (24.571, 73.691), "chittorgarh": (24.879, 74.623),
                "alwar": (27.554, 76.597), "sikar": (27.614, 75.140),
                # Madhya Pradesh
                "bhopal": (23.260, 77.413), "indore": (22.719, 75.858),
                "jabalpur": (23.181, 79.987), "gwalior": (26.214, 78.183),
                "rewa": (24.531, 81.296), "sagar": (23.838, 78.739),
                "ujjain": (23.182, 75.783), "dewas": (22.963, 76.053),
                "satna": (24.601, 80.832), "chhindwara": (22.057, 78.934),
                # Maharashtra
                "pune": (18.520, 73.857), "nashik": (19.998, 73.790),
                "nagpur": (21.146, 79.088), "aurangabad": (19.877, 75.343),
                "solapur": (17.686, 75.905), "kolhapur": (16.705, 74.243),
                "amravati": (20.933, 77.757), "latur": (18.400, 76.560),
                "nanded": (19.160, 77.317), "jalgaon": (21.000, 75.563),
                "satara": (17.686, 74.000), "ratnagiri": (17.000, 73.300),
                # Karnataka
                "bangalore": (12.972, 77.595), "mysore": (12.296, 76.638),
                "hubli": (15.364, 75.124), "gulbarga": (17.329, 76.820),
                "shimoga": (13.930, 75.568), "bellary": (15.139, 76.920),
                "mangalore": (12.870, 74.843), "tumkur": (13.342, 77.102),
                "dharwad": (15.458, 75.007), "davangere": (14.466, 75.921),
                # Andhra Pradesh
                "guntur": (16.307, 80.437), "vijayawada": (16.507, 80.648),
                "visakhapatnam": (17.686, 83.218), "kakinada": (16.946, 82.237),
                "nellore": (14.443, 79.987), "tirupati": (13.629, 79.420),
                "kurnool": (15.828, 78.037), "anantapur": (14.683, 77.601),
                "chittoor": (13.212, 79.100), "kadapa": (14.474, 78.824),
                # Telangana
                "hyderabad": (17.385, 78.487), "warangal": (17.977, 79.598),
                "karimnagar": (18.438, 79.129), "nizamabad": (18.672, 78.094),
                "khammam": (17.247, 80.152), "adilabad": (19.664, 78.531),
                # Tamil Nadu
                "chennai": (13.083, 80.271), "coimbatore": (11.017, 76.956),
                "madurai": (9.925, 78.119), "salem": (11.664, 78.147),
                "tirunelveli": (8.729, 77.702), "tiruchirappalli": (10.805, 78.687),
                "vellore": (12.916, 79.133), "erode": (11.341, 77.717),
                "dindigul": (10.362, 77.972), "thoothukudi": (8.764, 78.135),
                # Kerala
                "thiruvananthapuram": (8.524, 76.937), "kochi": (9.931, 76.267),
                "kozhikode": (11.258, 75.780), "thrissur": (10.527, 76.214),
                "palakkad": (10.776, 76.654), "malappuram": (11.040, 76.076),
                "kannur": (11.869, 75.370), "kollam": (8.887, 76.587),
                # West Bengal
                "kolkata": (22.573, 88.364), "howrah": (22.595, 88.258),
                "bardhaman": (23.233, 87.851), "midnapore": (22.423, 87.324),
                "siliguri": (26.726, 88.427), "murshidabad": (24.177, 88.249),
                "nadia": (23.462, 88.560), "north 24 parganas": (22.775, 88.400),
                # Bihar
                "patna": (25.594, 85.138), "muzaffarpur": (26.121, 85.391),
                "gaya": (24.797, 85.001), "bhagalpur": (25.253, 87.014),
                "darbhanga": (26.152, 85.896), "purnia": (25.778, 87.477),
                # Odisha
                "bhubaneswar": (20.296, 85.825), "cuttack": (20.463, 85.883),
                "berhampur": (19.314, 84.791), "sambalpur": (21.467, 83.975),
                "rourkela": (22.260, 84.853),
                # Assam
                "guwahati": (26.145, 91.736), "silchar": (24.827, 92.793),
                "dibrugarh": (27.484, 94.909), "jorhat": (26.751, 94.207),
                "nagaon": (26.346, 92.686), "tezpur": (26.633, 92.801),
                # Gujarat
                "ahmedabad": (23.023, 72.571), "surat": (21.170, 72.831),
                "rajkot": (22.291, 70.794), "vadodara": (22.307, 73.181),
                "bhavnagar": (21.765, 72.143), "jamnagar": (22.471, 70.057),
                "junagadh": (21.521, 70.457), "anand": (22.557, 72.951),
                "surendranagar": (22.728, 71.648), "amreli": (21.600, 71.217),
                # Himachal Pradesh
                "shimla": (31.105, 77.173), "dharamsala": (32.219, 76.324),
                "mandi": (31.708, 76.932), "kullu": (31.958, 77.110),
                "kangra": (32.099, 76.268), "solan": (30.908, 77.099),
                # Uttarakhand
                "dehradun": (30.317, 78.032), "haridwar": (29.946, 78.163),
                "nainital": (29.380, 79.463), "roorkee": (29.852, 77.889),
                # Jharkhand
                "ranchi": (23.344, 85.310), "jamshedpur": (22.805, 86.203),
                "dhanbad": (23.798, 86.434), "bokaro": (23.666, 85.996),
                # Chhattisgarh
                "raipur": (21.251, 81.630), "bilaspur": (22.090, 82.148),
                "durg": (21.190, 81.283), "korba": (22.365, 82.686),
                # Goa
                "panaji": (15.491, 73.828), "margao": (15.274, 73.957),
                # Northeast
                "imphal": (24.818, 93.944), "kohima": (25.667, 94.108),
                "aizawl": (23.727, 92.718), "agartala": (23.831, 91.287),
                "shillong": (25.578, 91.883), "gangtok": (27.331, 88.614),
                "itanagar": (27.084, 93.605), "dispur": (26.145, 91.736),
            }
            for dist_key, (dlat, dlon) in _DISTRICT_CENTROIDS.items():
                if dist_key not in DISTRICT_PROFILES:
                    continue
                # Haversine approximation (fast, no imports needed)
                import math
                dlat_r = math.radians(abs(latitude - dlat))
                dlon_r = math.radians(abs(longitude - dlon))
                a = math.sin(dlat_r/2)**2 + math.cos(math.radians(latitude)) * math.cos(math.radians(dlat)) * math.sin(dlon_r/2)**2
                dist_km = 6371 * 2 * math.asin(math.sqrt(a))
                if dist_km < best_dist:
                    best_dist = dist_km
                    best_key = dist_key
            if best_key and best_dist < 120:  # within 120 km → use that district
                p = dict(DISTRICT_PROFILES[best_key])
                p["_source"] = f"gps_nearest_district_{int(best_dist)}km"
                p["region"] = p.get("state", "India")
                logger.info("GPS zone: %s → nearest district %s (%.0f km)", f"{latitude},{longitude}", best_key, best_dist)
                return p

        # 4. State-level match
        state_name = state or ""
        state_lower = state_name.lower()
        for district_key, profile in DISTRICT_PROFILES.items():
            if profile.get("state", "").lower() == state_lower:
                p = dict(profile)
                p["_source"] = "state_first_district"
                p["region"] = p.get("state", "India")
                return p

        # 5. Keyword fallback
        return self._state_keyword_profile(loc_lower, state_lower)

    def _state_keyword_profile(self, loc: str, state: str) -> Dict[str, Any]:
        """Fallback profile inferred from state/location keywords."""
        combined = f"{loc} {state}"

        if any(k in combined for k in ["punjab", "haryana", "delhi"]):
            return {"state": "Punjab/Haryana", "soil": "Alluvial", "rainfall": "Medium", "irrigation": "High",
                    "agro_zone": "northwest", "priority_crops": ["wheat","rice","cotton","mustard","potato"],
                    "region": "North India", "_source": "keyword"}
        if any(k in combined for k in ["uttar pradesh", "up ", "lucknow", "kanpur", "agra", "varanasi"]):
            return {"state": "Uttar Pradesh", "soil": "Alluvial", "rainfall": "Medium", "irrigation": "High",
                    "agro_zone": "indo_gangetic", "priority_crops": ["wheat","sugarcane","rice","potato","mustard"],
                    "region": "North India", "_source": "keyword"}
        if any(k in combined for k in ["rajasthan", "jaipur", "jodhpur", "bikaner"]):
            return {"state": "Rajasthan", "soil": "Sandy Loam", "rainfall": "Low", "irrigation": "Low",
                    "agro_zone": "thar_desert", "priority_crops": ["bajra","mustard","gram","wheat","cumin"],
                    "region": "North India", "_source": "keyword"}
        if any(k in combined for k in ["madhya pradesh", "mp ", "bhopal", "indore"]):
            return {"state": "Madhya Pradesh", "soil": "Black", "rainfall": "Medium", "irrigation": "Medium",
                    "agro_zone": "central", "priority_crops": ["soybean","wheat","gram","cotton","onion"],
                    "region": "Central India", "_source": "keyword"}
        if any(k in combined for k in ["maharashtra", "pune", "mumbai", "nagpur", "nashik"]):
            return {"state": "Maharashtra", "soil": "Black", "rainfall": "Medium", "irrigation": "Medium",
                    "agro_zone": "deccan", "priority_crops": ["cotton","soybean","sugarcane","onion","tur"],
                    "region": "West India", "_source": "keyword"}
        if any(k in combined for k in ["gujarat", "ahmedabad", "surat", "rajkot"]):
            return {"state": "Gujarat", "soil": "Sandy Loam", "rainfall": "Low", "irrigation": "Medium",
                    "agro_zone": "gujarat", "priority_crops": ["groundnut","cotton","wheat","castor","bajra"],
                    "region": "West India", "_source": "keyword"}
        if any(k in combined for k in ["karnataka", "bangalore", "mysore", "hubli"]):
            return {"state": "Karnataka", "soil": "Red", "rainfall": "Medium", "irrigation": "Medium",
                    "agro_zone": "peninsular", "priority_crops": ["ragi","maize","cotton","sunflower","groundnut"],
                    "region": "South India", "_source": "keyword"}
        if any(k in combined for k in ["andhra pradesh", "ap ", "vijayawada", "guntur"]):
            return {"state": "Andhra Pradesh", "soil": "Black", "rainfall": "Medium", "irrigation": "Medium",
                    "agro_zone": "peninsular", "priority_crops": ["rice","chilli","cotton","tobacco","groundnut"],
                    "region": "South India", "_source": "keyword"}
        if any(k in combined for k in ["telangana", "hyderabad", "warangal"]):
            return {"state": "Telangana", "soil": "Red", "rainfall": "Medium", "irrigation": "Medium",
                    "agro_zone": "peninsular", "priority_crops": ["rice","cotton","maize","turmeric","chilli"],
                    "region": "South India", "_source": "keyword"}
        if any(k in combined for k in ["tamil", "chennai", "coimbatore", "madurai"]):
            return {"state": "Tamil Nadu", "soil": "Red", "rainfall": "Medium", "irrigation": "High",
                    "agro_zone": "peninsular", "priority_crops": ["rice","sugarcane","groundnut","cotton","banana"],
                    "region": "South India", "_source": "keyword"}
        if any(k in combined for k in ["kerala", "kochi", "thiruvananthapuram", "kozhikode"]):
            return {"state": "Kerala", "soil": "Laterite", "rainfall": "Very High", "irrigation": "Medium",
                    "agro_zone": "coastal", "priority_crops": ["coconut","rubber","rice","black_pepper","banana"],
                    "region": "South India", "_source": "keyword"}
        if any(k in combined for k in ["west bengal", "kolkata", "bengal"]):
            return {"state": "West Bengal", "soil": "Alluvial", "rainfall": "High", "irrigation": "High",
                    "agro_zone": "indo_gangetic", "priority_crops": ["rice","jute","potato","mustard","mango"],
                    "region": "East India", "_source": "keyword"}
        if any(k in combined for k in ["bihar", "patna", "muzaffarpur"]):
            return {"state": "Bihar", "soil": "Alluvial", "rainfall": "Medium", "irrigation": "High",
                    "agro_zone": "indo_gangetic", "priority_crops": ["rice","wheat","maize","litchi","potato"],
                    "region": "East India", "_source": "keyword"}
        if any(k in combined for k in ["odisha", "bhubaneswar", "cuttack"]):
            return {"state": "Odisha", "soil": "Red", "rainfall": "High", "irrigation": "Medium",
                    "agro_zone": "coastal", "priority_crops": ["rice","jute","turmeric","ginger","cashew"],
                    "region": "East India", "_source": "keyword"}
        if any(k in combined for k in ["assam", "guwahati", "northeast"]):
            return {"state": "Assam", "soil": "Alluvial", "rainfall": "Very High", "irrigation": "Low",
                    "agro_zone": "northeast", "priority_crops": ["rice","tea","jute","pineapple","ginger"],
                    "region": "Northeast India", "_source": "keyword"}
        if any(k in combined for k in ["himachal", "shimla", "kullu", "manali"]):
            return {"state": "Himachal Pradesh", "soil": "Loamy", "rainfall": "High", "irrigation": "Low",
                    "agro_zone": "himalayan", "priority_crops": ["apple","potato","rajma","peas","strawberry"],
                    "region": "North India", "_source": "keyword"}
        if any(k in combined for k in ["uttarakhand", "dehradun", "haridwar"]):
            return {"state": "Uttarakhand", "soil": "Alluvial", "rainfall": "High", "irrigation": "Medium",
                    "agro_zone": "himalayan", "priority_crops": ["rice","wheat","litchi","sugarcane","lemongrass"],
                    "region": "North India", "_source": "keyword"}
        if any(k in combined for k in ["chhattisgarh", "raipur"]):
            return {"state": "Chhattisgarh", "soil": "Red", "rainfall": "High", "irrigation": "Medium",
                    "agro_zone": "central", "priority_crops": ["rice","maize","soybean","vegetables","sesame"],
                    "region": "Central India", "_source": "keyword"}
        if any(k in combined for k in ["jharkhand", "ranchi"]):
            return {"state": "Jharkhand", "soil": "Red", "rainfall": "High", "irrigation": "Low",
                    "agro_zone": "peninsular", "priority_crops": ["rice","maize","potato","vegetables","tomato"],
                    "region": "East India", "_source": "keyword"}

        # Ultimate fallback — generic India
        return {
            "state": "India", "soil": "Alluvial", "rainfall": "Medium", "irrigation": "Medium",
            "agro_zone": "indo_gangetic", "priority_crops": ["wheat","rice","maize","mustard","potato","gram"],
            "region": "India", "_source": "default",
        }

    # ── Scoring engine ─────────────────────────────────────────────────

    def _score_all_crops(
        self,
        profile: Dict[str, Any],
        season_key: str,
        current_weather: Dict,
        forecast: List[Dict],
        market_price_map: Dict[str, Dict],
    ) -> List[Tuple[float, str, Dict[str, Any]]]:
        """Score every crop in the database and return sorted list."""

        try:
            from .comprehensive_crop_database import ALL_CROP_DATA
        except ImportError:
            from .ultra_dynamic_government_api import _builtin_crop_database
            ALL_CROP_DATA = _builtin_crop_database()

        soil          = profile.get("soil", "Loamy")
        rainfall_band = profile.get("rainfall", "Medium")
        irrigation    = _irrigation_level(profile.get("irrigation", "Medium"))
        priority_list = [c.lower() for c in profile.get("priority_crops", [])]
        agro_zone     = profile.get("agro_zone", "")

        # Derive weather risk from forecast
        weather_risk = self._assess_weather_risk(forecast, current_weather)
        curr_temp    = current_weather.get("temperature") or 28

        results = []
        for crop_key, crop in ALL_CROP_DATA.items():
            score, reasons = self._score_single_crop(
                crop_key, crop, season_key, soil, rainfall_band, irrigation,
                priority_list, agro_zone, weather_risk, curr_temp, market_price_map
            )
            if score > 0:
                results.append((score, crop_key, crop, reasons))

        results.sort(key=lambda x: x[0], reverse=True)
        return results

    def _score_single_crop(
        self, crop_key, crop, season_key, soil, rainfall_band,
        irrigation, priority_list, agro_zone, weather_risk, curr_temp,
        market_price_map
    ) -> Tuple[float, List[str]]:
        score = 0.0
        reasons = []

        crop_season = crop.get("season", "kharif")

        # ── 1. Season match (25 pts) ───────────────────────────────────
        if crop_season == "year_round":
            # Year-round crops get a base score but don't outscore properly-seasonal crops
            # unless they are in the regional priority list
            if crop_key in priority_list:
                score += 20
                reasons.append("Year-round + regional priority")
            else:
                score += 12
                reasons.append("Year-round crop")
        elif crop_season == season_key:
            score += 25
            reasons.append(f"Perfect season match ({season_key})")
        elif (season_key == "zaid" and crop_season == "kharif"):
            score += 10
            reasons.append("Zaid–Kharif overlap")
        else:
            # Wrong season — hard penalty, but still show if priority
            if crop_key in priority_list:
                score -= 10  # smaller penalty for regional priority
                reasons.append(f"Off-season (regional priority)")
            else:
                return 0.0, []  # Hard filter: don't recommend wrong-season crops

        # ── 2. Soil suitability (20 pts) ──────────────────────────────
        crop_soils = [s.lower() for s in crop.get("soil_preference", [])]
        soil_lower = soil.lower()
        if soil_lower in crop_soils or any(soil_lower in s for s in crop_soils):
            score += 20
            reasons.append(f"Ideal soil ({soil})")
        elif any(s in soil_lower for s in crop_soils):
            score += 12
            reasons.append(f"Compatible soil ({soil})")
        else:
            score += 4
            reasons.append("Soil adaptation possible")

        # ── 3. Water / irrigation (15 pts) ────────────────────────────
        water_req = crop.get("water_requirement", "Moderate")
        irr_min   = WATER_IRRIGATION_MIN.get(water_req, "Low")
        irr_levels = {"Low": 0, "Medium": 1, "High": 2}
        irr_val    = irr_levels.get(irrigation, 1)
        rain_val   = irr_levels.get(
            {"Very Low": 0, "Low": 0, "Medium": 1, "High": 2, "Very High": 2}.get(rainfall_band, 1), 1
        )
        effective_water = max(irr_val, rain_val)
        min_val = irr_levels.get(irr_min, 0)

        if effective_water >= min_val:
            if water_req == "Low" and effective_water >= 2:
                score += 8  # over-watered — slight penalty
                reasons.append("Water abundant (drought-resistant crop)")
            else:
                score += 15
                reasons.append(f"Water needs met ({water_req})")
        else:
            # Water deficiency
            deficit = min_val - effective_water
            penalty = deficit * 20
            score -= penalty
            reasons.append(f"WATER DEFICIT — needs {water_req} irrigation")
            if score < 0:
                return max(0.0, score), reasons

        # ── 4. Temperature (10 pts) ────────────────────────────────────
        t_min = crop.get("temperature_min", 10)
        t_max = crop.get("temperature_max", 38)
        if t_min <= curr_temp <= t_max:
            score += 10
            reasons.append(f"Temp optimal ({curr_temp}°C)")
        elif curr_temp < t_min:
            diff = t_min - curr_temp
            score += max(0, 10 - diff * 2)
            if diff > 5:
                reasons.append(f"Too cold ({curr_temp}°C < {t_min}°C min)")
        else:
            diff = curr_temp - t_max
            score += max(0, 10 - diff * 2)
            if diff > 5:
                reasons.append(f"Too hot ({curr_temp}°C > {t_max}°C max)")

        # ── 5. Market demand + MSP (10 pts) ───────────────────────────
        demand = crop.get("market_demand", "Medium")
        msp    = crop.get("msp_per_quintal", 0)
        mkt_info = market_price_map.get(crop_key, {})
        modal    = mkt_info.get("modal_price", 0)

        if demand == "Very High":
            score += 10
        elif demand == "High":
            score += 8
        elif demand == "Medium":
            score += 5
        else:
            score += 2

        if msp > 0:
            score += 3
            reasons.append(f"MSP guaranteed ₹{msp}/q")
        if modal and msp and modal > msp:
            bonus = min(5, round((modal - msp) / msp * 10))
            score += bonus
            reasons.append(f"Mandi ₹{modal} > MSP ₹{msp} (+{bonus}pts)")
        if demand in ("High", "Very High"):
            reasons.append(f"High market demand")

        # ── 6. Regional / district priority (10 pts) ──────────────────
        if crop_key in priority_list[:3]:
            score += 10
            reasons.append("Top regional priority crop")
        elif crop_key in priority_list:
            score += 7
            reasons.append("Regional priority crop")
        elif agro_zone and agro_zone in crop.get("agro_zones", []):
            score += 5
            reasons.append(f"Suited to {agro_zone} agro-zone")

        # ── 7. Live weather outlook (10 pts) ──────────────────────────
        risk = weather_risk.get("risk", "None")
        crop_water = crop.get("water_requirement", "Moderate")

        if risk == "None":
            score += 10
            reasons.append("✅ Favorable weather outlook")
        elif risk == "High Rainfall":
            if crop_water == "High":
                score += 8
                reasons.append("🌧️ Rain suits this crop")
            elif crop_water == "Low":
                score -= 15
                reasons.append("⚠️ Flood risk for drought-resistant crop")
        elif risk == "Drought":
            if crop_water in ("Low", "Moderate"):
                score += 7
                reasons.append("☀️ Drought-tolerant — suitable")
            elif crop_water in ("High", "Very High"):
                score -= 20
                reasons.append("🚨 Drought risk — water-intensive crop")
        elif risk == "Heatwave":
            if t_max >= 38:
                score += 5
                reasons.append("🔥 Heat-tolerant crop")
            elif t_max < 28:
                score -= 10
                reasons.append("⚠️ Heatwave risk for cool-season crop")

        return round(max(0.0, score), 1), reasons

    def _assess_weather_risk(self, forecast: List[Dict], current: Dict) -> Dict[str, Any]:
        """Assess 7-day weather risk for crop scoring."""
        if not forecast:
            return {"risk": "None", "description": "No forecast data"}

        total_rain = sum(d.get("rainfall_mm", 0) or 0 for d in forecast[:7])
        max_temps  = [d.get("max_temp") for d in forecast[:7] if d.get("max_temp")]
        avg_max    = sum(max_temps) / len(max_temps) if max_temps else 28

        # Use real soil moisture from Open-Meteo if available
        humidity = current.get("humidity") or 65

        if total_rain > 150:
            return {"risk": "High Rainfall", "description": f"Heavy rain expected ({total_rain:.0f}mm / 7 days)"}
        if total_rain < 5 and humidity < 30:
            return {"risk": "Drought", "description": "Dry spell — very low moisture"}
        if avg_max > 42:
            return {"risk": "Heatwave", "description": f"Heatwave expected ({avg_max:.1f}°C avg max)"}
        if avg_max < 8:
            return {"risk": "Cold", "description": f"Cold conditions ({avg_max:.1f}°C avg max)"}

        return {"risk": "None", "description": "Favorable weather conditions"}

    # ── Market data ────────────────────────────────────────────────────

    def _build_market_price_map(self, market_data: Dict) -> Dict[str, Dict]:
        """Build crop_key → {modal_price, msp, profit_vs_msp} lookup."""
        price_map = {}
        crops = market_data.get("top_crops") or []
        for row in crops:
            name = str(row.get("crop_name", "")).lower().strip().replace(" ", "_")
            if name:
                price_map[name] = {
                    "modal_price": row.get("modal_price", 0),
                    "msp":         row.get("msp", 0),
                    "profit_vs_msp": row.get("profit_vs_msp"),
                    "is_live":     row.get("is_live", False),
                }
                # Also store under common aliases
                for alias in self._get_crop_aliases(name):
                    if alias not in price_map:
                        price_map[alias] = price_map[name]
        return price_map

    @staticmethod
    def _get_crop_aliases(name: str) -> List[str]:
        alias_map = {
            "wheat": ["गेहूँ", "gehu", "gehun"],
            "rice":  ["paddy", "dhaan", "dhan", "chawal"],
            "maize": ["corn", "makka", "makkai"],
            "gram":  ["chickpea", "chana", "chick_pea"],
            "tur":   ["pigeon_pea", "toor", "arhar", "tuvar"],
            "moong": ["green_gram", "mung"],
            "urad":  ["black_gram", "udad"],
            "masoor":["lentil"],
            "cotton":["kapas"],
            "mustard":["sarson","rape_seed"],
        }
        return alias_map.get(name, [])

    # ── Formatting ─────────────────────────────────────────────────────

    def _format_recommendations(
        self,
        scored: List[Tuple],
        language: str,
        market_price_map: Dict,
        profile: Dict,
    ) -> List[Dict[str, Any]]:
        try:
            from .language_service import normalise_language_code, get_crop_name
            from .comprehensive_crop_database import ALL_CROP_DATA
            lang = normalise_language_code(language)
        except ImportError:
            lang = "hi"
            get_crop_name = lambda k, l: k.title()
            ALL_CROP_DATA = {}

        season_key = _current_season()
        out = []
        for score, crop_key, crop, reasons in scored:
            msp     = crop.get("msp_per_quintal", 0)
            yield_q = crop.get("yield_per_hectare", 0)
            profit  = crop.get("profit_per_hectare", 0)
            input_c = crop.get("input_cost_per_hectare", 0)

            # Use live market price if available
            mkt = market_price_map.get(crop_key, {})
            modal = mkt.get("modal_price") or (msp * 1.1 if msp else 0)

            # Localised crop name
            crop_name_local = get_crop_name(crop_key, lang) if lang != "en" else crop_key.title()
            crop_name_hindi = crop.get("name_hindi", crop_key.title())

            # Build suitability reason in the right language
            reason_local = self._localise_reason(reasons, lang, crop_key)

            out.append({
                "crop_name": crop_key.title(),
                "crop_name_hindi": crop_name_hindi,
                "crop_name_local": crop_name_local,
                "name": crop_key.title(),
                "category": crop.get("category", "General"),
                "season": _season_label(crop.get("season", season_key)),
                "season_key": crop.get("season", season_key),
                "suitability_score": int(min(score, 99)),
                "confidence": round(min(score / 100.0, 0.98), 2),
                "reason": " | ".join(reasons[:3]),
                "reason_hindi": reason_local,
                "factors": reasons,
                "soil_type": ", ".join(crop.get("soil_preference", [])[:3]),
                "water_requirement": crop.get("water_requirement", "Moderate"),
                "duration_days": crop.get("duration_days", 120),
                "temperature_range": f"{crop.get('temperature_min',10)}–{crop.get('temperature_max',38)}°C",
                "yield_per_hectare": yield_q,
                "profit_per_hectare": profit,
                "input_cost_per_hectare": input_c,
                "msp_per_quintal": msp,
                "market_price": round(modal),
                "market_is_live": mkt.get("is_live", False),
                "export_potential": crop.get("export_potential", "Low"),
                "market_demand": crop.get("market_demand", "Medium"),
                "volatility": crop.get("volatility", "Medium"),
                "government_support": crop.get("government_support", "MSP"),
                "states_primary": crop.get("states_primary", [])[:4],
                "financials": {
                    "yield": f"{yield_q} q/ha",
                    "profit_potential": f"₹{profit:,}/ha",
                    "msp": f"₹{msp}/q" if msp else "No MSP",
                    "market_price": f"₹{round(modal)}/q",
                    "input_cost": f"₹{input_c:,}/ha",
                },
                "prediction_data": {
                    "method": "multi_factor_scoring_v3",
                    "score_breakdown": {
                        "season": "see factors",
                        "soil": "see factors",
                        "water": "see factors",
                    },
                },
                "outlook": profile.get("_source", ""),
            })
        return out

    def _localise_reason(self, reasons: List[str], lang: str, crop_key: str) -> str:
        """Return a localised summary reason for the top factors."""
        REASON_MAP = {
            "Perfect season match": {
                "hi": "मौसम के लिए एकदम उपयुक्त",
                "ta": "பருவத்திற்கு மிகவும் பொருத்தமானது",
                "te": "సీజన్‌కు అనువైనది",
                "mr": "हंगामासाठी योग्य",
                "bn": "মৌসুমের জন্য উপযুক্ত",
                "gu": "ઋતુ માટે ઉત્તમ",
                "kn": "ಋತುವಿಗೆ ಸರಿಯಾಗಿ ಹೊಂದಿಕೊಳ್ಳುತ್ತದೆ",
                "ml": "സീസണിൽ അനുയോജ്യം",
                "pa": "ਮੌਸਮ ਲਈ ਢੁਕਵਾਂ",
                "or": "ଋତୁ ପାଇଁ ଉପଯୁକ୍ତ",
                "as": "ঋতুৰ বাবে উপযুক্ত",
            },
            "Top regional priority": {
                "hi": "इस क्षेत्र की सर्वोच्च प्राथमिकता फसल",
                "ta": "பிராந்திய முன்னுரிமை பயிர்",
                "te": "ప్రాంతీయ ప్రాధాన్యత పంట",
                "mr": "या प्रदेशाचे प्रमुख पीक",
                "bn": "এলাকার প্রধান ফসল",
                "gu": "ક્ષેત્રીય પ્રાથમિક પાક",
                "kn": "ಪ್ರಾದೇಶಿಕ ಆದ್ಯತೆಯ ಬೆಳೆ",
                "ml": "പ്രദേശത്തിന്റെ മുൻഗണന വിള",
                "pa": "ਖੇਤਰੀ ਤਰਜੀਹੀ ਫ਼ਸਲ",
                "or": "ଅଞ୍ଚଳର ପ୍ରଧାନ ଫସଲ",
                "as": "অঞ্চলৰ প্ৰধান শস্য",
            },
            "Water needs met": {
                "hi": "पानी की जरूरत पूरी होती है",
                "ta": "நீர்த் தேவை பூர்த்தியாகும்",
                "te": "నీటి అవసరం తీరుతుంది",
                "mr": "पाण्याची गरज भागते",
                "bn": "জলের চাহিদা মেটে",
                "gu": "પાણીની જરૂરિયાત પૂરી",
                "kn": "ನೀರಿನ ಅಗತ್ಯ ಪೂರೈಸಲಾಗುತ್ತದೆ",
                "ml": "ജലാവശ്യകത നിറവേറ്റുന്നു",
                "pa": "ਪਾਣੀ ਦੀ ਲੋੜ ਪੂਰੀ ਹੁੰਦੀ ਹੈ",
                "or": "ଜଳ ଆବଶ୍ୟକତା ପୂରଣ ହୁଏ",
                "as": "পানীৰ প্ৰয়োজনীয়তা পূৰণ হয়",
            },
            "High market demand": {
                "hi": "बाजार में भरपूर मांग",
                "ta": "சந்தையில் அதிக தேவை",
                "te": "మార్కెట్‌లో అధిక డిమాండ్",
                "mr": "बाजारात जास्त मागणी",
                "bn": "বাজারে প্রচুর চাহিদা",
                "gu": "બજારમાં ઊંચી માંગ",
                "kn": "ಮಾರುಕಟ್ಟೆಯಲ್ಲಿ ಹೆಚ್ಚಿನ ಬೇಡಿಕೆ",
                "ml": "ചന്തയിൽ ഉയർന്ന ഡിമാൻഡ്",
                "pa": "ਬਾਜ਼ਾਰ ਵਿੱਚ ਜ਼ਿਆਦਾ ਮੰਗ",
                "or": "ବଜାରରେ ଅଧିକ ଚାହିଦା",
                "as": "বজাৰত প্ৰচুৰ চাহিদা",
            },
        }
        # Find first matching reason key
        for key, translations in REASON_MAP.items():
            for reason in reasons:
                if key.lower() in reason.lower():
                    return translations.get(lang, translations.get("hi", reason))

        # Fallback: return top reason as-is
        return reasons[0] if reasons else crop_key.title()

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _parse_rupees(text: str) -> int:
        if not text:
            return 0
        nums = re.findall(r"[\d,]+", str(text).replace(",", ""))
        return int(nums[0]) if nums else 0

    @staticmethod
    def _parse_quintals(text: str) -> float:
        if not text:
            return 0.0
        m = re.search(r"([\d.]+)", str(text))
        return float(m.group(1)) if m else 0.0


# Module-level singleton
crop_recommendation_engine = CropRecommendationEngine()
