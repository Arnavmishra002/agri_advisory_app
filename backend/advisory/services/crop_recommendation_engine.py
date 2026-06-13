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
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .location_context import LocationContext
from .unified_realtime_service import market_service, weather_service

logger = logging.getLogger(__name__)

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

        # 1. Resolve location profile
        profile = self._resolve_location_profile(location, state)

        # 2. Get live weather (Open-Meteo, no key needed)
        weather = weather_service.get_weather(location, latitude, longitude, lang=language)
        current_weather = weather.get("current") or {}
        forecast = weather.get("forecast_7day") or weather.get("forecast_7_days") or []

        # 3. Get live market prices
        live_market = market_service.get_prices(
            location, lat=latitude, lon=longitude, state=state
        )
        market_price_map = self._build_market_price_map(live_market)

        # 4. Score all crops
        season_key = _current_season()
        scored = self._score_all_crops(profile, season_key, current_weather, forecast, market_price_map)

        # 5. Localise and format
        recommendations = self._format_recommendations(scored[:12], language, market_price_map, profile)

        return {
            "location": location,
            "state": state or profile.get("state", ""),
            "region": profile.get("region", "India"),
            "agro_zone": profile.get("agro_zone", ""),
            "season": _season_label(season_key),
            "season_key": season_key,
            "soil_type": profile.get("soil", "Loamy"),
            "irrigation": profile.get("irrigation", "Medium"),
            "recommendations": recommendations,
            "top_4_recommendations": recommendations[:4],
            "weather_snapshot": current_weather,
            "market_is_live": bool(live_market.get("is_live")),
            "market_status": live_market.get("status"),
            "market_snapshot": (live_market.get("top_crops") or [])[:5],
            "data_source": "KrishiMitra Agro-Climatic Engine v3 + Open-Meteo + Agmarknet",
            "analysis_method": "multi_factor_scoring_v3",
            "factors_analyzed": [
                f"Season: {_season_label(season_key)}",
                f"Soil: {profile.get('soil', 'Loamy')}",
                f"Rainfall: {profile.get('rainfall', 'Medium')}",
                f"Irrigation: {profile.get('irrigation', 'Medium')}",
                "Live 7-day weather forecast",
                "Live mandi modal prices vs MSP",
                "150+ crop agro-climatic profiles",
                "District-level priority crops",
            ],
            "profile_source": profile.get("_source", "state_default"),
            "timestamp": datetime.now().isoformat(),
            "language": language,
        }

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

    def _resolve_location_profile(self, location: str, state: Optional[str]) -> Dict[str, Any]:
        """Return the best agro-climatic profile for the location."""
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

        # 2. Partial district match (city name inside district key)
        for district_key, profile in DISTRICT_PROFILES.items():
            if district_key in loc_lower or loc_lower in district_key:
                p = dict(profile)
                p["_source"] = "district_fuzzy"
                p["region"] = p.get("state", "India")
                return p

        # 3. State-level match
        state_name = state or ""
        state_lower = state_name.lower()
        for district_key, profile in DISTRICT_PROFILES.items():
            if profile.get("state", "").lower() == state_lower:
                p = dict(profile)
                p["_source"] = "state_first_district"
                p["region"] = p.get("state", "India")
                return p

        # 4. Generic defaults by state name keywords
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
