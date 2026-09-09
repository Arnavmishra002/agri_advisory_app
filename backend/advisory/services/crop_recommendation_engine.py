#!/usr/bin/env python3
"""Location-aware crop recommendation with transparent multi-factor scoring."""

from __future__ import annotations

import logging
import os
import re
import atexit
from concurrent.futures import ThreadPoolExecutor, wait
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
CROP_REC_HEALTH_CACHE_KEY = "crop_rec:data_source_health:last"
CROP_REC_HEALTH_CACHE_TTL_SECONDS = 60 * 60

# Rainfall category boundaries (mm/year)
RAINFALL_BANDS = {
    "Very Low": (0,   350),
    "Low":      (350, 700),
    "Medium":   (700, 1200),
    "High":     (1200, 2000),
    "Very High":(2000, 9999),
}

# Long-term rainfall band → the irrigation level it is worth, on the same
# 0/1/2 scale as WATER_IRRIGATION_MIN. Kept as plain ints because the scoring
# code compares it directly against the irrigation level; an earlier version
# fed this through a second, string-keyed lookup, which never matched.
RAINFALL_TO_WATER_LEVEL = {
    "Very Low": 0,
    "Low":      0,
    "Medium":   1,
    "High":     2,
    "Very High": 2,
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

    CONFIDENCE_FARMER_INPUTS = (
        "soil_type", "irrigation", "previous_crop", "ph", "budget_per_hectare",
        "nitrogen_kg_ha", "phosphorus_kg_ha", "potassium_kg_ha",
    )

    # ── Public API ─────────────────────────────────────────────────────

    def recommend(
        self,
        location: str,
        latitude: float,
        longitude: float,
        state: Optional[str] = None,
        language: str = "hi",
        agronomic_inputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Full recommendation pipeline with live weather and market data."""

        # 1. Resolve location profile — GPS-first in v4.0
        profile = self._resolve_location_profile(location, state, latitude, longitude)
        inputs = self._normalise_agronomic_inputs(agronomic_inputs)
        profile = self._apply_farmer_profile(profile, inputs)

        # 2. Get live weather + mandi prices concurrently with partial fallback
        weather, live_market, realtime_status = self._fetch_realtime_context(
            location, latitude, longitude, state, language
        )
        current_weather = weather.get("current") or {}
        forecast = weather.get("forecast_7day") or weather.get("forecast_7_days") or []

        # 3. Build live market signal map
        market_price_map = self._build_market_price_map(live_market)

        # 4. Score all crops
        season_key = inputs.get("season") or _current_season()
        scored = self._score_all_crops(
            profile,
            season_key,
            current_weather,
            forecast,
            market_price_map,
            inputs,
            weather_is_live=bool(weather.get("is_live")),
        )

        # 5. Localise and format
        recommendations = self._format_recommendations(
            scored[:12], language, market_price_map, profile, inputs,
            weather_is_live=bool(weather.get("is_live")),
        )

        weather_is_live = bool(weather.get("is_live"))
        market_is_live = bool(live_market.get("is_live"))
        market_freshness = self._market_freshness_summary(live_market)
        data_quality = self._data_quality_summary(weather, live_market, realtime_status)
        missing_confidence_inputs = self._missing_confidence_inputs(
            inputs, weather_is_live, market_is_live
        )
        self._record_data_source_health(
            location,
            state or profile.get("state", ""),
            latitude,
            longitude,
            data_quality,
        )

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
            "weather_is_live": weather_is_live,
            "weather_data_source": weather.get("data_source", ""),
            "weather_fetched_at": weather.get("fetched_at"),
            "market_is_live": market_is_live,
            "market_status": live_market.get("status"),
            "market_data_source": live_market.get("data_source_short") or live_market.get("data_source", ""),
            "market_fetched_at": live_market.get("fetched_at") or live_market.get("timestamp"),
            "market_reported_date": market_freshness["reported_date"],
            "market_data_age_minutes": market_freshness["data_age_minutes"],
            "market_freshness": market_freshness["status"],
            "market_snapshot": (live_market.get("top_crops") or [])[:5],
            "realtime_status": realtime_status,
            "data_quality_status": data_quality["status"],
            "data_quality": data_quality,
            "data_source": self._data_source_label(weather, live_market),
            "analysis_method": "multi_factor_scoring_v5",
            "database_size": len(ALL_CROP_DATA),
            "crop_profile_version": "2026.07-beta1",
            "confidence_inputs_missing": missing_confidence_inputs,
            "input_parameters": inputs,
            "input_provenance": {
                key: "farmer_supplied" if key in inputs else "regional_assumption"
                for key in ("soil_type", "irrigation")
            },
            "factors_analyzed": self._factors_analyzed(
                profile,
                season_key,
                weather,
                live_market,
                inputs,
            ),
            "profile_source": profile.get("_source", "state_default"),
            "timestamp": datetime.now().isoformat(),
            "language": language,
        }

    @staticmethod
    def _missing_confidence_inputs(
        inputs: Dict[str, Any], weather_is_live: bool, market_is_live: bool
    ) -> List[str]:
        missing = [
            key for key in CropRecommendationEngine.CONFIDENCE_FARMER_INPUTS
            if inputs.get(key) in (None, "")
        ]
        if not weather_is_live:
            missing.append("live_weather")
        if not market_is_live:
            missing.append("verified_market_price")
        return missing

    @staticmethod
    def _normalise_agronomic_inputs(values: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Keep only bounded farmer inputs understood by the scoring model."""
        if not values:
            return {}
        allowed = {
            "season", "soil_type", "irrigation", "farm_size_ha",
            "budget_per_hectare", "risk_tolerance", "preferred_categories",
            "exclude_crops", "previous_crop", "nitrogen_kg_ha",
            "phosphorus_kg_ha", "potassium_kg_ha", "ph", "ec_ds_m",
            "moisture_pct", "organic_carbon", "target_crop",
        }
        inputs = {key: values[key] for key in allowed if values.get(key) not in (None, "")}

        if "soil_type" in inputs:
            inputs["soil_type"] = str(inputs["soil_type"]).lower().replace(" ", "_")
        for key in ("season", "irrigation", "risk_tolerance"):
            if key in inputs:
                inputs[key] = str(inputs[key]).lower()
        for key in ("preferred_categories", "exclude_crops"):
            value = inputs.get(key)
            if value is not None and not isinstance(value, list):
                inputs[key] = [item.strip() for item in str(value).split(",") if item.strip()]
        if inputs.get("preferred_categories"):
            inputs["preferred_categories"] = [
                str(item).replace("_", " ").title()
                for item in inputs["preferred_categories"][:12]
            ]

        try:
            from .crop_catalog import crop_catalog
        except ImportError:
            crop_catalog = None

        def canonical_crop(value: Any) -> str:
            text = str(value or "").strip()
            if crop_catalog:
                match = crop_catalog.normalize(text)
                if match:
                    return match["id"]
            return text.lower().replace("-", "_").replace(" ", "_")

        if inputs.get("previous_crop"):
            inputs["previous_crop"] = canonical_crop(inputs["previous_crop"])
        if inputs.get("target_crop"):
            inputs["target_crop"] = canonical_crop(inputs["target_crop"])
        if inputs.get("exclude_crops"):
            inputs["exclude_crops"] = [canonical_crop(item) for item in inputs["exclude_crops"][:30]]
        return inputs

    @staticmethod
    def _apply_farmer_profile(profile: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        profile = dict(profile)
        if inputs.get("soil_type"):
            profile["soil"] = inputs["soil_type"].replace("_", " ").title()
        if inputs.get("irrigation"):
            irrigation = inputs["irrigation"]
            if irrigation in {"rainfed", "low"}:
                profile["irrigation"] = "Low"
            elif irrigation in {"high", "flood"}:
                profile["irrigation"] = "High"
            else:
                profile["irrigation"] = "Medium"
        if inputs:
            profile["_source"] = f"{profile.get('_source', 'location')}+farmer_inputs"
        return profile

    def _data_source_label(self, weather: Dict[str, Any], market: Dict[str, Any]) -> str:
        sources = ["KrishiMitra Agro-Climatic Engine v5"]
        if weather.get("is_live"):
            sources.append(weather.get("data_source_short") or "live weather")
        else:
            sources.append(f"weather {weather.get('status') or 'unavailable'}")
        if market.get("is_live"):
            freshness = self._market_freshness_summary(market)
            reported = freshness.get("reported_date")
            sources.append(
                f"Agmarknet official report dated {reported}"
                if reported
                else market.get("data_source_short") or "verified official mandi row"
            )
        else:
            sources.append(f"mandi {market.get('status') or 'unavailable'}")
        return " + ".join(str(s) for s in sources if s)

    def _factors_analyzed(
        self,
        profile: Dict[str, Any],
        season_key: str,
        weather: Dict[str, Any],
        market: Dict[str, Any],
        inputs: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        weather_factor = (
            "Live 7-day weather forecast"
            if weather.get("is_live")
            else f"Weather unavailable/degraded ({weather.get('status') or 'unavailable'})"
        )
        market_freshness = self._market_freshness_summary(market)
        market_factor = (
            f"Verified official mandi rows reported {market_freshness['reported_date']}"
            if market.get("is_live") and market_freshness["reported_date"]
            else "Verified official mandi rows available"
            if market.get("is_live")
            else "Mandi prices unavailable; current MSP references only"
        )
        factors = [
                f"Season: {_season_label(season_key)}",
                f"Soil: {profile.get('soil', 'Loamy')}",
                f"Rainfall: {profile.get('rainfall', 'Medium')}",
                f"Irrigation: {profile.get('irrigation', 'Medium')}",
                weather_factor,
                market_factor,
                f"{len(ALL_CROP_DATA)} crop agro-climatic profiles",
                "District-level priority crops",
            ]
        inputs = inputs or {}
        optional = (
            ("ph", "Soil pH"),
            ("ec_ds_m", "Soil EC (dS/m)"),
            ("moisture_pct", "Soil moisture (%)"),
            ("organic_carbon", "Organic carbon (%)"),
            ("nitrogen_kg_ha", "Nitrogen (kg/ha)"),
            ("phosphorus_kg_ha", "Phosphorus (kg/ha)"),
            ("potassium_kg_ha", "Potassium (kg/ha)"),
            ("budget_per_hectare", "Budget per hectare (INR)"),
            ("farm_size_ha", "Farm size (ha)"),
            ("previous_crop", "Previous crop"),
            ("risk_tolerance", "Risk tolerance"),
        )
        factors.extend(
            f"{label}: {inputs[key]}"
            for key, label in optional
            if inputs.get(key) is not None and inputs.get(key) != ""
        )
        if inputs.get("preferred_categories"):
            factors.append("Preferred categories: " + ", ".join(inputs["preferred_categories"]))
        return factors

    def _data_quality_summary(
        self,
        weather: Dict[str, Any],
        market: Dict[str, Any],
        status_map: Dict[str, str],
    ) -> Dict[str, Any]:
        """Summarise live/degraded source state for farmers and ops."""
        generated_at = datetime.now().isoformat()
        sources = {}
        alerts = []

        source_inputs = {
            "weather": weather,
            "market": market,
        }
        for name, data in source_inputs.items():
            is_live = bool(data.get("is_live"))
            status = (
                data.get("status")
                or status_map.get(name)
                or ("live" if is_live else "unavailable")
            )
            source_label = (
                data.get("data_source_short")
                or data.get("data_source")
                or "not_available"
            )
            fetched_at = data.get("fetched_at") or data.get("timestamp")
            sources[name] = {
                "is_live": is_live,
                "status": status,
                "source": source_label,
                "fetched_at": fetched_at,
            }
            if not is_live:
                alerts.append(f"{name} {status}: {source_label}")

        return {
            "status": "ok" if not alerts else "degraded",
            "generated_at": generated_at,
            "sources": sources,
            "alerts": alerts,
        }

    def _record_data_source_health(
        self,
        location: str,
        state: str,
        latitude: float,
        longitude: float,
        data_quality: Dict[str, Any],
    ) -> None:
        """Record latest crop recommendation source health for monitoring."""
        try:
            from django.core.cache import cache

            payload = dict(data_quality)
            payload.update({
                "location": location,
                "state": state,
                "coordinates": {"lat": latitude, "lon": longitude},
                "recorded_at": datetime.now().isoformat(),
            })
            cache.set(
                CROP_REC_HEALTH_CACHE_KEY,
                payload,
                timeout=CROP_REC_HEALTH_CACHE_TTL_SECONDS,
            )
        except Exception as exc:
            logger.debug("Could not record crop recommendation source health: %s", exc)

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

        done, pending = wait(futures, timeout=timeout_s)
        for fut in done:
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

        for fut in pending:
            key = futures[fut]
            # The shared worker may still be completing an HTTP call. The
            # caller is bounded here while service-level HTTP timeouts finish it.
            status_map[key] = "timeout"
        if pending:
            logger.warning(
                "Crop recommendation realtime fetch timed out after %.1fs for %s",
                timeout_s,
                location,
            )

        return weather, market, status_map

    @classmethod
    def recommend_from_context(
        cls,
        ctx: LocationContext,
        language: str = "hi",
        agronomic_inputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Singleton-safe context-based entry point."""
        return crop_recommendation_engine.recommend(
            ctx.query_label,
            ctx.latitude,
            ctx.longitude,
            state=ctx.state or None,
            language=language,
            agronomic_inputs=agronomic_inputs,
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
        agronomic_inputs: Optional[Dict[str, Any]] = None,
        weather_is_live: bool = False,
    ) -> List[Tuple[float, str, Dict[str, Any], List[str], Dict[str, Any]]]:
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
        raw_temp = current_weather.get("temperature") if weather_is_live else None
        try:
            curr_temp = float(raw_temp) if raw_temp is not None else None
        except (TypeError, ValueError):
            curr_temp = None
        if not weather_is_live:
            weather_risk = {"risk": "Unavailable", "description": "Live forecast unavailable"}
        inputs = agronomic_inputs or {}
        excluded = set(inputs.get("exclude_crops") or [])
        target_crop = inputs.get("target_crop")
        preferred_categories = set(inputs.get("preferred_categories") or [])

        results = []
        for crop_key, crop in ALL_CROP_DATA.items():
            if crop_key in excluded:
                continue
            if target_crop and crop_key != target_crop:
                continue
            if preferred_categories and crop.get("category") not in preferred_categories:
                continue
            score, reasons, breakdown = self._score_single_crop(
                crop_key, crop, season_key, soil, rainfall_band, irrigation,
                priority_list, agro_zone, weather_risk, curr_temp,
                market_price_map, inputs,
            )
            if score > 0:
                results.append((score, crop_key, crop, reasons, breakdown))

        results.sort(key=lambda x: x[0], reverse=True)
        return results

    def _score_single_crop(
        self, crop_key, crop, season_key, soil, rainfall_band,
        irrigation, priority_list, agro_zone, weather_risk, curr_temp,
        market_price_map, agronomic_inputs=None,
    ) -> Tuple[float, List[str], Dict[str, Any]]:
        score = 0.0
        reasons = []
        breakdown: Dict[str, Any] = {}
        inputs = agronomic_inputs or {}

        def factor(name: str, points: float, maximum: float, status: str, detail: str):
            nonlocal score
            score += points
            breakdown[name] = {
                "points": round(points, 1),
                "max_points": maximum,
                "status": status,
                "detail": detail,
            }

        crop_season = crop.get("season", "kharif")

        # 1. Season. Off-season annual crops are filtered rather than
        # presented as plausible choices.
        if crop_season == "year_round":
            if crop_key in priority_list:
                factor("season", 18, 20, "good", "Year-round regional crop")
                reasons.append("Year-round + regional priority")
            else:
                factor("season", 12, 20, "compatible", "Year-round crop")
                reasons.append("Year-round crop")
        elif crop_season == season_key:
            factor("season", 20, 20, "ideal", f"Matches {season_key}")
            reasons.append(f"Perfect season match ({season_key})")
        elif (season_key == "zaid" and crop_season == "kharif"):
            factor("season", 8, 20, "conditional", "Zaid-Kharif overlap")
            reasons.append("Zaid–Kharif overlap")
        else:
            if crop_key in priority_list:
                factor("season", -10, 20, "poor", "Off-season regional crop")
                reasons.append(f"Off-season (regional priority)")
            else:
                return 0.0, [], {"season": {"status": "off_season"}}

        # 2. Soil texture.
        crop_soils = [s.lower() for s in crop.get("soil_preference", [])]
        soil_lower = soil.lower()
        if soil_lower in crop_soils or any(soil_lower in s for s in crop_soils):
            factor("soil", 15, 15, "ideal", f"Ideal {soil}")
            reasons.append(f"Ideal soil ({soil})")
        elif any(s in soil_lower for s in crop_soils):
            factor("soil", 9, 15, "compatible", f"Compatible {soil}")
            reasons.append(f"Compatible soil ({soil})")
        else:
            factor("soil", 2, 15, "uncertain", "Local soil adaptation required")
            reasons.append("Soil adaptation possible")

        # 3. Long-term rainfall fit. Location profiles are broad bands, so
        # this remains lower-weight than farmer soil/irrigation readings.
        rain_range = RAINFALL_BANDS.get(rainfall_band, RAINFALL_BANDS["Medium"])
        available_rain = (rain_range[0] + min(rain_range[1], 2500)) / 2
        required_rain = max(float(crop.get("rainfall_mm", 800)), 1)
        rain_ratio = available_rain / required_rain
        if 0.6 <= rain_ratio <= 1.8:
            factor("rainfall", 8, 8, "good", f"Regional rainfall fits {required_rain:.0f} mm need")
        elif 0.35 <= rain_ratio <= 2.4:
            factor("rainfall", 3, 8, "conditional", "Irrigation/drainage may be needed")
        else:
            factor("rainfall", -8, 8, "poor", "Large rainfall mismatch")

        # 4. Water and irrigation.
        # Two inputs bear on water, and they are not interchangeable. The
        # irrigation level is what this farmer says they can actually deliver,
        # year round. The rainfall band is a broad district average that only
        # arrives inside the monsoon window. Rainfall may therefore supplement
        # stated irrigation; it must not silently stand in for it.
        #
        # This previously read
        #     rain_val = irr_levels.get({"Very Low": 0, ...}.get(band, 1), 1)
        # The inner dict returns an int while irr_levels is keyed by str, so the
        # outer .get() never matched and rain_val was always 1. Two consequences:
        # every rainfall band scored alike (a desert district scored as a wet
        # one), and a farmer reporting no irrigation was scored as though they
        # had Medium, which is why rainfed and irrigated farmers received the
        # same rice recommendation.
        water_req = crop.get("water_requirement", "Moderate")
        irr_min   = WATER_IRRIGATION_MIN.get(water_req, "Low")
        irr_levels = {"Low": 0, "Medium": 1, "High": 2}
        irr_val    = irr_levels.get(irrigation, 1)
        rain_val   = RAINFALL_TO_WATER_LEVEL.get(rainfall_band, 1)

        if crop_season in ("kharif", "year_round"):
            # Monsoon rain can lift the effective level, but by at most one
            # step, so "no irrigation" can never be scored as fully irrigated.
            effective_water = max(irr_val, min(rain_val, irr_val + 1))
            water_source = "rainfall" if effective_water > irr_val else "irrigation"
        else:
            # Rabi and zaid crops grow outside the monsoon; only what the
            # farmer can irrigate with counts.
            effective_water = irr_val
            water_source = "irrigation"
        min_val = irr_levels.get(irr_min, 0)

        if effective_water >= min_val:
            if water_req == "Low" and effective_water >= 2:
                factor("water", 6, 12, "compatible", "Drainage needed with abundant water")
                reasons.append("Water abundant (drought-resistant crop)")
            else:
                factor("water", 12, 12, "ideal",
                       f"{water_req} requirement met via {water_source}")
                reasons.append(f"Water needs met ({water_req}, from {water_source})")
        else:
            deficit = min_val - effective_water
            penalty = deficit * -12
            factor("water", penalty, 12, "poor",
                   f"Needs {water_req} water; stated irrigation {irrigation}, "
                   f"district rainfall {rainfall_band}")
            reasons.append(f"WATER DEFICIT — needs {water_req} irrigation")

        # 5. Current temperature.
        t_min = crop.get("temperature_min", 10)
        t_max = crop.get("temperature_max", 38)
        if curr_temp is None:
            factor("temperature", 0, 10, "unavailable", "Live temperature unavailable; no points awarded")
        elif t_min <= curr_temp <= t_max:
            factor("temperature", 10, 10, "ideal", f"{curr_temp} C within crop range")
            reasons.append(f"Temp optimal ({curr_temp}°C)")
        elif curr_temp < t_min:
            diff = t_min - curr_temp
            points = max(-8, 10 - diff * 2)
            factor("temperature", points, 10, "poor" if diff > 5 else "conditional", "Below preferred range")
            if diff > 5:
                reasons.append(f"Too cold ({curr_temp}°C < {t_min}°C min)")
        else:
            diff = curr_temp - t_max
            points = max(-8, 10 - diff * 2)
            factor("temperature", points, 10, "poor" if diff > 5 else "conditional", "Above preferred range")
            if diff > 5:
                reasons.append(f"Too hot ({curr_temp}°C > {t_max}°C max)")

        # 6. Market signal. Static demand has limited weight; only verified
        # live rows can receive the live-price bonus.
        demand = crop.get("market_demand", "Medium")
        msp    = crop.get("msp_per_quintal", 0)
        mkt_info = market_price_map.get(crop_key, {})
        modal    = mkt_info.get("modal_price", 0)
        market_points = {"Very High": 5, "High": 4, "Medium": 2, "Low": 0}.get(demand, 2)
        if msp > 0:
            market_points += 2
            reasons.append(f"MSP reference ₹{msp}/q")
        market_is_live = bool(modal and mkt_info.get("is_live"))
        if market_is_live:
            if not msp:
                bonus = 3
            elif modal >= msp:
                bonus = min(3, max(1, round((modal - msp) / max(msp, 1) * 6)))
            else:
                bonus = 0
            market_points += bonus
            if msp and modal > msp:
                reasons.append(f"Verified mandi ₹{modal} > MSP ₹{msp} (+{bonus}pts)")
            else:
                reasons.append(f"Verified live mandi price ₹{modal}/q")
        factor(
            "market",
            market_points,
            10,
            "live" if market_is_live else "indicative",
            f"Demand {demand}; verified live price {'yes' if market_is_live else 'no'}",
        )
        if demand in ("High", "Very High"):
            reasons.append(f"High market demand")

        # 7. Regional suitability.
        if crop_key in priority_list[:3]:
            factor("region", 10, 10, "ideal", "Top district/state priority")
            reasons.append("Top regional priority crop")
        elif crop_key in priority_list:
            factor("region", 7, 10, "good", "Regional priority")
            reasons.append("Regional priority crop")
        elif agro_zone and agro_zone in crop.get("agro_zones", []):
            factor("region", 5, 10, "compatible", f"Suited to {agro_zone}")
            reasons.append(f"Suited to {agro_zone} agro-zone")
        else:
            factor("region", 0, 10, "uncertain", "No specific regional evidence")

        # 8. Seven-day weather risk.
        risk = weather_risk.get("risk", "None")
        crop_water = crop.get("water_requirement", "Moderate")

        if risk == "Unavailable":
            factor("weather", 0, 10, "unavailable", "Live 7-day forecast unavailable; no points awarded")
        elif risk == "None":
            factor("weather", 10, 10, "good", "No severe 7-day risk")
            reasons.append("✅ Favorable weather outlook")
        elif risk == "High Rainfall":
            if crop_water == "High":
                factor("weather", 7, 10, "compatible", "Rain supports water demand")
                reasons.append("🌧️ Rain suits this crop")
            elif crop_water == "Low":
                factor("weather", -10, 10, "poor", "Waterlogging risk")
                reasons.append("⚠️ Flood risk for drought-resistant crop")
            else:
                factor("weather", 1, 10, "conditional", "Drainage required")
        elif risk == "Drought":
            if crop_water in ("Low", "Moderate"):
                factor("weather", 7, 10, "good", "Drought-tolerant water demand")
                reasons.append("☀️ Drought-tolerant — suitable")
            elif crop_water in ("High", "Very High"):
                factor("weather", -12, 10, "poor", "Drought conflicts with water demand")
                reasons.append("🚨 Drought risk — water-intensive crop")
        elif risk == "Heatwave":
            if t_max >= 38:
                factor("weather", 5, 10, "compatible", "Heat-tolerant range")
                reasons.append("🔥 Heat-tolerant crop")
            elif t_max < 28:
                factor("weather", -10, 10, "poor", "Heatwave above crop range")
                reasons.append("⚠️ Heatwave risk for cool-season crop")
            else:
                factor("weather", 0, 10, "conditional", "Heat mitigation needed")
        else:
            factor("weather", 0, 10, "conditional", str(risk))

        # 9. Farmer soil measurements. Missing readings are not guessed.
        if inputs.get("ph") is not None:
            ph = float(inputs["ph"])
            ph_min = float(crop.get("ph_min", 5.5))
            ph_max = float(crop.get("ph_max", 7.5))
            if ph_min <= ph <= ph_max:
                factor("soil_ph", 8, 8, "ideal", f"pH {ph} within {ph_min}-{ph_max}")
                reasons.append(f"Soil pH {ph} fits crop")
            elif min(abs(ph - ph_min), abs(ph - ph_max)) <= 0.5:
                factor("soil_ph", 2, 8, "conditional", f"pH {ph} near {ph_min}-{ph_max}")
            else:
                factor("soil_ph", -12, 8, "poor", f"pH {ph} outside {ph_min}-{ph_max}")

        if inputs.get("ec_ds_m") is not None:
            ec = float(inputs["ec_ds_m"])
            tolerance = crop.get("salinity_tolerance", "Low")
            if ec <= 2:
                factor("salinity", 4, 4, "good", f"EC {ec} dS/m")
            elif ec <= 4 and tolerance in {"Medium", "High"}:
                factor("salinity", 2, 4, "compatible", f"{tolerance} salinity tolerance")
            else:
                penalty = -6 if tolerance == "High" else -12
                factor("salinity", penalty, 4, "poor", f"EC {ec}; tolerance {tolerance}")

        if inputs.get("moisture_pct") is not None:
            moisture = float(inputs["moisture_pct"])
            if moisture < 25 and crop_water in {"High", "Very High"}:
                factor("soil_moisture", -8, 4, "poor", "Low moisture for water-intensive crop")
            elif moisture > 80 and crop_water == "Low":
                factor("soil_moisture", -6, 4, "poor", "Waterlogging risk")
            else:
                factor("soil_moisture", 4, 4, "good", f"Measured moisture {moisture}%")

        nutrient_values = {
            "N": inputs.get("nitrogen_kg_ha"),
            "P": inputs.get("phosphorus_kg_ha"),
            "K": inputs.get("potassium_kg_ha"),
        }
        measured_nutrients = {key: value for key, value in nutrient_values.items() if value is not None}
        if measured_nutrients:
            thresholds = {"N": 120, "P": 20, "K": 120}
            low = [key for key, value in measured_nutrients.items() if float(value) < thresholds[key]]
            demand_level = crop.get("nutrient_demand", "Medium")
            if not low:
                factor("nutrients", 6, 6, "good", "Measured NPK is not low")
            elif demand_level == "High" and len(low) >= 2:
                factor("nutrients", -8, 6, "poor", f"Low {', '.join(low)} for high-demand crop")
            else:
                factor("nutrients", -2, 6, "conditional", f"Correct low {', '.join(low)} from soil test")

        if inputs.get("organic_carbon") is not None:
            organic_carbon = float(inputs["organic_carbon"])
            if organic_carbon < 0.5 and crop.get("nutrient_demand") == "High":
                factor("organic_carbon", -4, 3, "poor", "Low organic carbon for high-demand crop")
            else:
                factor("organic_carbon", 3, 3, "good", f"Organic carbon {organic_carbon}%")

        # 10. Rotation, budget, scale, category and risk preferences.
        previous_crop = inputs.get("previous_crop")
        if previous_crop:
            previous_profile = ALL_CROP_DATA.get(previous_crop, {})
            previous_category = previous_profile.get("category")
            current_category = crop.get("category")
            if previous_crop == crop_key:
                factor("rotation", -8, 6, "poor", "Avoid immediate same-crop repetition")
            elif previous_category in {"Cereal", "Millet"} and current_category == "Pulse":
                factor("rotation", 6, 6, "ideal", "Legume after cereal supports soil nitrogen")
                reasons.append("Good cereal-legume rotation")
            elif current_category == "Pulse":
                factor("rotation", 4, 6, "good", "Legume diversification")
            else:
                factor("rotation", 1, 6, "neutral", "No known rotation conflict")

        budget = inputs.get("budget_per_hectare")
        input_cost = float(crop.get("input_cost_per_hectare", 0) or 0)
        if budget is not None:
            budget = float(budget)
            if input_cost > budget:
                return 0.0, reasons + ["Above farmer budget"], {
                    **breakdown,
                    "budget": {"points": -20, "max_points": 8, "status": "over_budget", "detail": f"INR {input_cost:.0f} > INR {budget:.0f}"},
                }
            headroom = budget - input_cost
            factor("budget", 8 if headroom >= budget * 0.2 else 4, 8, "good", "Within farmer budget")

        preferred = set(inputs.get("preferred_categories") or [])
        if preferred:
            matched = crop.get("category") in preferred
            factor("category_preference", 6 if matched else 0, 6, "preferred" if matched else "neutral", crop.get("category", ""))

        risk_tolerance = inputs.get("risk_tolerance")
        if risk_tolerance:
            volatility = crop.get("volatility", "Medium")
            duration = int(crop.get("duration_days", 120) or 120)
            if risk_tolerance == "low" and (volatility in {"High", "Very High"} or duration > 365):
                factor("risk", -8, 6, "poor", f"{volatility} volatility / {duration} days")
            elif risk_tolerance == "medium" and volatility == "Very High":
                factor("risk", -3, 6, "conditional", "Very high price volatility")
            else:
                factor("risk", 6, 6, "compatible", f"{volatility} volatility")

        if inputs.get("farm_size_ha") is not None:
            farm_size = float(inputs["farm_size_ha"])
            if farm_size < 0.5 and (input_cost > 100000 or crop.get("duration_days", 0) > 365):
                factor("farm_scale", -4, 3, "conditional", "High establishment cost for a small holding")
            else:
                factor("farm_scale", 3, 3, "good", f"Suitable for {farm_size} ha planning")

        possible = sum(float(item.get("max_points", 0)) for item in breakdown.values()) or 1
        normalized = max(0.0, min(99.0, score / possible * 100.0))
        breakdown["summary"] = {
            "raw_points": round(score, 1),
            "possible_points": round(possible, 1),
            "normalized_score": round(normalized, 1),
        }

        return round(normalized, 1), reasons, breakdown

    def _assess_weather_risk(self, forecast: List[Dict], current: Dict) -> Dict[str, Any]:
        """Assess 7-day weather risk for crop scoring."""
        if not forecast:
            return {"risk": "Unavailable", "description": "No live forecast data"}

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
        if not market_data.get("is_live"):
            return price_map
        crops = market_data.get("top_crops") or []
        for row in crops:
            name = str(row.get("crop_name", "")).lower().strip().replace(" ", "_")
            modal_price = row.get("modal_price", 0)
            try:
                modal_price = float(modal_price)
            except (TypeError, ValueError):
                modal_price = 0
            if modal_price <= 0:
                continue
            if name:
                price_map[name] = {
                    "modal_price": modal_price,
                    "msp":         row.get("msp", 0),
                    "profit_vs_msp": row.get("profit_vs_msp"),
                    "is_live":     row.get("is_live", False),
                    "status":      row.get("status") or "live",
                    "source":      row.get("source") or market_data.get("data_source_short") or market_data.get("data_source"),
                    "fetched_at":  row.get("fetched_at") or market_data.get("fetched_at") or market_data.get("timestamp"),
                    "reported_date": row.get("reported_date") or row.get("date"),
                    "data_age_minutes": row.get("data_age_minutes"),
                    "freshness": row.get("freshness") or "official",
                }
                # Also store under common aliases
                for alias in self._get_crop_aliases(name):
                    if alias not in price_map:
                        price_map[alias] = price_map[name]
        return price_map

    @staticmethod
    def _market_freshness_summary(market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Describe official report freshness without calling dated rows live."""
        rows = market_data.get("top_crops") or []
        candidates = []
        for row in rows:
            age = row.get("data_age_minutes")
            try:
                age_value = int(age)
            except (TypeError, ValueError):
                age_value = None
            candidates.append(
                {
                    "reported_date": row.get("reported_date") or row.get("date"),
                    "data_age_minutes": age_value,
                }
            )
        dated = [item for item in candidates if item["data_age_minutes"] is not None]
        latest = min(dated, key=lambda item: item["data_age_minutes"]) if dated else (candidates[0] if candidates else {})
        age = latest.get("data_age_minutes")
        status = (
            "fresh_official"
            if age is not None and age <= 24 * 60
            else "dated_official"
            if market_data.get("is_live")
            else "unavailable"
        )
        return {
            "status": status,
            "reported_date": latest.get("reported_date"),
            "data_age_minutes": age,
        }

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
        agronomic_inputs: Optional[Dict[str, Any]] = None,
        weather_is_live: bool = False,
    ) -> List[Dict[str, Any]]:
        try:
            from .language_service import normalise_language_code, get_crop_name
            from .comprehensive_crop_database import ALL_CROP_DATA
            lang = normalise_language_code(language)
        except ImportError:
            lang = "hi"
            get_crop_name = lambda k, l: k.title()
            ALL_CROP_DATA = {}

        inputs = agronomic_inputs or {}
        season_key = inputs.get("season") or _current_season()
        missing_farmer_inputs = [
            key for key in self.CONFIDENCE_FARMER_INPUTS
            if inputs.get(key) in (None, "")
        ]
        out = []
        for score, crop_key, crop, reasons, breakdown in scored:
            msp     = crop.get("msp_per_quintal", 0)
            yield_q = crop.get("yield_per_hectare", 0)
            input_c = crop.get("input_cost_per_hectare", 0)

            # Use live market price if available
            mkt = market_price_map.get(crop_key, {})
            modal = mkt.get("modal_price")
            market_price = round(modal) if modal else None
            market_status = mkt.get("status") or "unavailable"
            market_source = mkt.get("source") or "not_available"
            market_fetched_at = mkt.get("fetched_at")
            market_price_text = f"₹{market_price}/q" if market_price else "Unavailable"

            profit = None
            economics_basis = "verified_price_required"
            if yield_q and input_c and market_price:
                profit = round((yield_q * market_price) - input_c)
                economics_basis = "official_mandi_modal_price"
            elif yield_q and input_c and msp:
                profit = round((yield_q * msp) - input_c)
                economics_basis = "current_msp_reference"
            economics_note = (
                "Indicative return uses the dated official mandi modal price; "
                "verify local costs and today's buyer price before sowing."
                if economics_basis == "official_mandi_modal_price"
                else "Indicative return uses current MSP and profile yield/cost; verify local costs before sowing."
                if economics_basis == "current_msp_reference"
                else "A verified sale price is required before estimating return for this crop."
            )

            # Localised crop name
            display_name = crop_key.replace("_", " ").title()
            crop_name_local = get_crop_name(crop_key, lang) if lang != "en" else display_name
            crop_name_hindi = crop.get("name_hindi", display_name)

            # Build suitability reason in the right language
            priority_reasons = self._prioritise_reasons(reasons)
            reason_local = self._localise_reason(priority_reasons, lang, crop_key)

            factor_rows = [value for key, value in breakdown.items() if key != "summary"]
            supported_rows = [
                value for value in factor_rows
                if value.get("status") not in {"uncertain", "neutral", "unavailable"}
            ]
            score_factor_coverage = round(
                len(supported_rows) / max(len(factor_rows), 1), 2
            )
            missing_inputs = self._missing_confidence_inputs(
                inputs, weather_is_live, bool(mkt.get("is_live")),
            )
            input_count = len(self.CONFIDENCE_FARMER_INPUTS) + 2
            data_completeness = round((input_count - len(missing_inputs)) / input_count, 2)

            input_quality = max(0.55, 1.0 - (0.1 * len(missing_farmer_inputs)))
            if not weather_is_live:
                input_quality = max(0.45, input_quality - 0.12)
            if not mkt.get("is_live", False):
                input_quality = max(0.45, input_quality - 0.08)
            confidence = min(
                (score / 100.0) * (0.7 + 0.3 * data_completeness) * input_quality,
                0.98,
            )

            out.append({
                "crop_name": display_name,
                "crop_name_hindi": crop_name_hindi,
                "crop_name_local": crop_name_local,
                "name": display_name,
                "category": crop.get("category", "General"),
                "season": _season_label(crop.get("season", season_key)),
                "season_key": crop.get("season", season_key),
                "suitability_score": int(min(score, 99)),
                "confidence": round(confidence, 2),
                "confidence_kind": "heuristic_not_calibrated_probability",
                "confidence_inputs_missing": missing_inputs,
                "reason": " | ".join(priority_reasons[:3]),
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
                "msp_season": crop.get("msp_season", ""),
                "msp_source": crop.get("msp_source", ""),
                "market_price": market_price,
                "market_price_status": market_status,
                "market_price_source": market_source,
                "market_price_fetched_at": market_fetched_at,
                "market_price_reported_date": mkt.get("reported_date"),
                "market_price_data_age_minutes": mkt.get("data_age_minutes"),
                "market_price_freshness": mkt.get("freshness"),
                "market_is_live": mkt.get("is_live", False),
                "export_potential": crop.get("export_potential", "Low"),
                "market_demand": crop.get("market_demand", "Medium"),
                "volatility": crop.get("volatility", "Medium"),
                "government_support": crop.get("government_support", "No central MSP"),
                "states_primary": crop.get("states_primary", [])[:4],
                "district_suitability": crop.get("district_suitability", {}),
                "rotation": crop.get("rotation", {}),
                "market_mapping": crop.get("market_mapping", {}),
                "agronomy_source": crop.get("agronomy_source", "ICAR/NHB/state package of practices"),
                "economics_status": (
                    "indicative_estimate" if profit is not None else "price_required"
                ),
                "economics_basis": economics_basis,
                "economics_note": economics_note,
                "financials": {
                    "yield": f"{yield_q} q/ha",
                    "profit_potential": f"₹{profit:,}/ha" if profit is not None else "Verified price required",
                    "msp": f"₹{msp}/q ({crop.get('msp_season')})" if msp else "No central MSP",
                    "market_price": market_price_text,
                    "input_cost": f"₹{input_c:,}/ha",
                },
                "prediction_data": {
                    "method": "multi_factor_scoring_v5",
                    "score_breakdown": breakdown,
                    "data_completeness": data_completeness,
                    "score_factor_coverage": score_factor_coverage,
                    "data_completeness_basis": "farmer_inputs_and_live_sources_v1",
                    "farmer_inputs_used": sorted(inputs),
                },
                "outlook": profile.get("_source", ""),
            })
        return out

    @staticmethod
    def _prioritise_reasons(reasons: List[str]) -> List[str]:
        warning_prefixes = (
            "too hot",
            "too cold",
            "soil ph",
            "salinity",
            "high establishment cost",
            "avoid repeating",
            "heavy rain",
            "dry spell",
            "heatwave",
            "cold conditions",
        )
        warnings = [
            reason for reason in reasons
            if str(reason).lower().startswith(warning_prefixes)
        ]
        return warnings + [reason for reason in reasons if reason not in warnings]

    def _localise_reason(self, reasons: List[str], lang: str, crop_key: str) -> str:
        """Return a localised summary reason for the top factors."""
        REASON_MAP = {
            "Perfect season match": {
                "hi": "चुने हुए बुवाई सीजन से अच्छी तरह मेल खाती है",
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
        if reasons:
            first = reasons[0]
            hot = re.search(r"Too hot \(([\d.]+)°C > ([\d.]+)°C max\)", first, re.IGNORECASE)
            if hot and lang == "hi":
                return f"अभी तापमान {hot.group(1)}°C है, जबकि पसंदीदा अधिकतम {hot.group(2)}°C है"
            if hot:
                return first
            cold = re.search(r"Too cold \(([\d.]+)°C < ([\d.]+)°C min\)", first, re.IGNORECASE)
            if cold and lang == "hi":
                return f"अभी तापमान {cold.group(1)}°C है, जबकि पसंदीदा न्यूनतम {cold.group(2)}°C है"
            if cold:
                return first
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
