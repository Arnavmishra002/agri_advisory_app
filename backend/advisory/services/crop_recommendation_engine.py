#!/usr/bin/env python3
"""Location-aware crop recommendation with transparent multi-factor scoring."""

from __future__ import annotations

import logging
import math
import os
import re
import atexit
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .location_context import LocationContext
from .market_data_quality import filter_fresh_live_rows
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
        raw_market_rows = live_market.get("top_crops") or []
        fresh_market_rows, _, _ = filter_fresh_live_rows(
            raw_market_rows if live_market.get("is_live") is True else [],
        )
        live_market = {
            **live_market,
            "top_crops": fresh_market_rows,
            "is_live": bool(fresh_market_rows),
            "status": live_market.get("status", "success") if fresh_market_rows else "unavailable",
        }
        if not fresh_market_rows:
            realtime_status = {**realtime_status, "market": "unavailable"}
        current_weather = weather.get("current") or {}
        forecast = weather.get("forecast_7day") or weather.get("forecast_7_days") or weather.get("forecast") or []

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
            "soil_type": profile.get("soil"),
            "irrigation": profile.get("irrigation"),
            "reference_profile": profile.get("reference_profile"),
            "reference_district": profile.get("reference_district"),
            "guidance_mode": "general_guidance" if any(k not in inputs for k in ("soil_type", "irrigation")) else "field_inputs_supplied",
            "clarification_required": [k for k in ("soil_type", "irrigation") if k not in inputs],
            "score_interpretation": "Ranking points, not a probability of success",
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
                key: "farmer_supplied" if key in inputs else "unknown"
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
                f"Farmer soil: {profile.get('soil') or 'unknown'}",
                f"District reference rainfall: {profile.get('rainfall') or 'unknown'}",
                f"Farmer irrigation: {profile.get('irrigation') or 'unknown'}",
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
        self, location: str, state: Optional[str],
        latitude: Optional[float] = None, longitude: Optional[float] = None,
    ) -> Dict[str, Any]:
        """District references are not observations of this farmer's field.

        Never assign another district's soil/water through a fuzzy, GPS or
        state-first fallback. Retain exact district context separately.
        """
        from .district_data import DISTRICT_PROFILES
        import re

        label = re.sub(r"\s+district\b", "", (location or "").lower()).strip()
        aliases = {"prayagraj": "allahabad", "bengaluru": "bangalore", "gurugram": "gurgaon"}
        parts = [aliases.get(part.strip(), part.strip()) for part in label.split(',')]
        matches = [(key, DISTRICT_PROFILES[key]) for key in parts if key in DISTRICT_PROFILES]
        matches = [(key, value) for key, value in matches
                   if not state or value.get('state', '').casefold() == state.strip().casefold()]
        if len(matches) == 1:
            key, reference = matches[0]
            return {
                **reference, 'soil': None, 'irrigation': None,
                '_source': 'district_exact', 'region': reference.get('state', 'India'),
                'reference_district': key, 'reference_profile': dict(reference),
            }
        return {
            '_source': 'unknown', 'state': state or '', 'region': state or location or 'India',
            'soil': None, 'irrigation': None, 'rainfall': None,
            'priority_crops': [], 'agro_zone': '', 'reference_profile': None,
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

        soil          = profile.get("soil")
        rainfall_band = profile.get("rainfall")
        irrigation    = _irrigation_level(profile['irrigation']) if profile.get('irrigation') else None
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
        soil_lower = (soil or '').lower()
        if not soil_lower:
            factor("soil", 0, 15, "unknown", "Ask farmer for soil type; not inferred from district")
        elif soil_lower in crop_soils or any(soil_lower in s for s in crop_soils):
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
        if not rainfall_band:
            factor("rainfall", 0, 8, "unknown", "No district rainfall reference available")
        elif 0.6 <= rain_ratio <= 1.8:
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

        if irrigation is None:
            factor("water", 0, 12, "unknown", "Ask farmer about irrigation before choosing a crop")
            reasons.append("Irrigation unknown; confirm water availability before planting")
        elif effective_water >= min_val:
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
        if len(forecast) < 7 or not all(
            type(day.get(key)) in (int, float) and math.isfinite(day[key])
            for day in forecast[:7] for key in ("rainfall_mm", "max_temp")
        ):
            return {"risk": "Unavailable", "description": "Complete seven-day forecast unavailable"}

        total_rain = sum(d["rainfall_mm"] for d in forecast[:7])
        max_temps  = [d["max_temp"] for d in forecast[:7]]
        avg_max    = sum(max_temps) / len(max_temps)

        # Air humidity is not a measurement of root-zone soil moisture.
        humidity = current.get("humidity")

        if total_rain > 150:
            return {"risk": "High Rainfall", "description": f"Heavy rain expected ({total_rain:.0f}mm / 7 days)"}
        if total_rain < 5 and type(humidity) in (int, float) and 0 <= humidity < 30:
            return {"risk": "Drought", "description": "Low rainfall and dry air; check soil moisture before irrigation"}
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
        crops, _, _ = filter_fresh_live_rows(crops)
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
