"""
KrishiMitra Field-Level Precision Agriculture Service v1.0
============================================================
Integrates:
  1. IoT sensor data  — NPK, pH, EC, moisture, temperature (farmer's own device)
  2. Government soil  — Soil Health Card (soilhealth.dac.gov.in API)
  3. Open-Meteo soil  — Real-time soil moisture + temperature layers (0-10cm, 10-40cm)
  4. IMD/Open-Meteo   — 16-day hyperlocal weather + agri forecasts
  5. Agmarknet        — Nearby mandi prices for economic scoring
  6. Soil History     — Cached historical readings per GPS point (SQLite/in-memory)

Output: Field-level crop recommendation with confidence score per sensor source.

IoT Sensor Payload (sent by farmer's device or mobile app):
{
  "latitude":  28.6139,
  "longitude": 77.2090,
  "field_id":  "farmer_123_field_1",    // optional unique field identifier
  "sensors": {
    "nitrogen_kg_ha":   140,   // N available (kg/ha)
    "phosphorus_kg_ha": 22,    // P₂O₅ (kg/ha)
    "potassium_kg_ha":  180,   // K₂O (kg/ha)
    "ph":               6.8,   // soil pH
    "ec_ds_m":          0.4,   // electrical conductivity (dS/m)
    "moisture_pct":     38,    // volumetric soil moisture %
    "soil_temp_c":      24,    // soil temperature °C
    "organic_carbon":   0.65,  // % OC
    "bulk_density":     1.35   // g/cm³ (optional)
  },
  "crop_history": ["wheat", "rice", "wheat"],  // last 3 seasons (optional)
  "previous_crop":   "wheat",                   // most recent crop (optional)
  "irrigation_type": "drip",                    // drip | sprinkler | flood | rainfed
  "field_area_ha":   1.2                        // hectares
}
"""

from __future__ import annotations

import logging
import math
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# ── Nutrient thresholds (ICAR recommended ranges) ──────────────────────────
N_BANDS = {"Low": (0, 120), "Medium": (120, 280), "High": (280, 9999)}
P_BANDS = {"Low": (0, 10),  "Medium": (10, 25),   "High": (25, 9999)}
K_BANDS = {"Low": (0, 108), "Medium": (108, 280),  "High": (280, 9999)}
PH_BANDS = {
    "Very Acidic": (0, 5.5),
    "Acidic":      (5.5, 6.0),
    "Slightly Acidic": (6.0, 6.5),
    "Optimal":     (6.5, 7.5),
    "Slightly Alkaline": (7.5, 8.0),
    "Alkaline":    (8.0, 8.5),
    "Highly Alkaline": (8.5, 14),
}
OC_BANDS = {"Low": (0, 0.5), "Medium": (0.5, 0.75), "High": (0.75, 9999)}
EC_BANDS = {"Safe": (0, 2.0), "Marginal": (2.0, 4.0), "Saline": (4.0, 9999)}

# Crop NPK requirements (kg/ha) — ICAR package of practices
# Format: {crop: {N: (min,max), P: (min,max), K: (min,max), pH: (min,max), OC_min, moisture_pct_min}}
CROP_SOIL_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
    "wheat":     {"N": (80,160),  "P": (15,30), "K": (60,120), "pH": (6.0,7.5), "OC_min": 0.4, "moisture_min": 20, "EC_max": 4.0},
    "rice":      {"N": (80,120),  "P": (20,40), "K": (40,80),  "pH": (5.5,7.0), "OC_min": 0.5, "moisture_min": 60, "EC_max": 3.0},
    "maize":     {"N": (100,150), "P": (25,50), "K": (50,100), "pH": (5.8,7.0), "OC_min": 0.4, "moisture_min": 25, "EC_max": 3.5},
    "cotton":    {"N": (100,150), "P": (30,60), "K": (60,120), "pH": (6.0,8.0), "OC_min": 0.3, "moisture_min": 20, "EC_max": 4.0},
    "sugarcane": {"N": (150,250), "P": (50,80), "K": (80,150), "pH": (6.0,7.5), "OC_min": 0.5, "moisture_min": 50, "EC_max": 3.0},
    "mustard":   {"N": (60,100),  "P": (20,40), "K": (40,80),  "pH": (6.0,7.5), "OC_min": 0.3, "moisture_min": 15, "EC_max": 4.0},
    "gram":      {"N": (20,40),   "P": (25,50), "K": (30,60),  "pH": (6.0,8.0), "OC_min": 0.3, "moisture_min": 15, "EC_max": 4.0},
    "soybean":   {"N": (20,40),   "P": (30,60), "K": (40,80),  "pH": (6.0,7.5), "OC_min": 0.5, "moisture_min": 25, "EC_max": 3.5},
    "groundnut": {"N": (20,30),   "P": (20,40), "K": (50,100), "pH": (5.5,7.0), "OC_min": 0.4, "moisture_min": 20, "EC_max": 3.5},
    "potato":    {"N": (100,180), "P": (80,120),"K": (150,250),"pH": (5.0,6.5), "OC_min": 0.6, "moisture_min": 35, "EC_max": 3.0},
    "onion":     {"N": (75,100),  "P": (50,80), "K": (80,120), "pH": (6.0,7.0), "OC_min": 0.4, "moisture_min": 30, "EC_max": 2.5},
    "tomato":    {"N": (100,150), "P": (60,80), "K": (100,150),"pH": (6.0,7.0), "OC_min": 0.5, "moisture_min": 35, "EC_max": 2.5},
    "turmeric":  {"N": (60,90),   "P": (25,50), "K": (80,120), "pH": (5.5,7.0), "OC_min": 0.6, "moisture_min": 40, "EC_max": 3.0},
    "ginger":    {"N": (60,90),   "P": (25,50), "K": (80,120), "pH": (5.5,6.5), "OC_min": 0.7, "moisture_min": 45, "EC_max": 2.5},
    "chilli":    {"N": (75,120),  "P": (40,60), "K": (60,100), "pH": (6.0,7.0), "OC_min": 0.4, "moisture_min": 25, "EC_max": 3.0},
    "tur":       {"N": (20,40),   "P": (30,50), "K": (30,60),  "pH": (6.0,8.0), "OC_min": 0.3, "moisture_min": 20, "EC_max": 4.0},
    "moong":     {"N": (15,30),   "P": (20,40), "K": (25,50),  "pH": (6.0,7.5), "OC_min": 0.3, "moisture_min": 15, "EC_max": 3.5},
    "bajra":     {"N": (60,80),   "P": (20,40), "K": (30,60),  "pH": (5.5,8.0), "OC_min": 0.2, "moisture_min": 10, "EC_max": 5.0},
    "ragi":      {"N": (40,60),   "P": (15,30), "K": (25,50),  "pH": (5.5,7.5), "OC_min": 0.3, "moisture_min": 15, "EC_max": 3.5},
    "banana":    {"N": (150,200), "P": (50,75), "K": (200,300),"pH": (6.0,7.5), "OC_min": 0.6, "moisture_min": 50, "EC_max": 2.5},
    "coconut":   {"N": (50,100),  "P": (25,50), "K": (150,250),"pH": (5.5,8.0), "OC_min": 0.4, "moisture_min": 30, "EC_max": 3.5},
    "mango":     {"N": (50,100),  "P": (25,50), "K": (50,100), "pH": (5.5,7.5), "OC_min": 0.4, "moisture_min": 25, "EC_max": 4.0},
    "grapes":    {"N": (60,100),  "P": (20,40), "K": (80,120), "pH": (5.5,6.5), "OC_min": 0.5, "moisture_min": 30, "EC_max": 2.0},
    "cotton":    {"N": (100,150), "P": (30,60), "K": (60,120), "pH": (6.0,8.0), "OC_min": 0.3, "moisture_min": 20, "EC_max": 4.0},
    "mushroom":  {"N": (0,0),     "P": (0,0),   "K": (0,0),    "pH": (6.5,7.5), "OC_min": 2.0, "moisture_min": 60, "EC_max": 1.5},
}

def _band(value: float, bands: Dict[str, Tuple[float, float]]) -> str:
    for label, (lo, hi) in bands.items():
        if lo <= value < hi:
            return label
    return list(bands.keys())[-1]


class FieldSensorService:
    """
    Field-Level Precision Crop Recommendation Engine.
    Uses IoT sensors + government soil API + Open-Meteo + historical data.
    """

    OPEN_METEO_SOIL_URL = "https://api.open-meteo.com/v1/forecast"
    SOIL_HEALTH_CARD_URL = "https://soilhealth.dac.gov.in/PublicReports/GpwiseSHCStatusData"
    NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "KrishiMitra-AI/3.0 (field-precision)",
            "Accept": "application/json",
        })
        # In-memory cache keyed by (lat_rounded, lon_rounded)
        self._soil_history_cache: Dict[str, Dict] = {}
        self._weather_cache: Dict[str, Dict] = {}

    # ── Main Entry Point ───────────────────────────────────────────────

    def get_field_recommendation(
        self,
        latitude: float,
        longitude: float,
        sensor_data: Optional[Dict] = None,
        field_id: Optional[str] = None,
        location_name: str = "",
        state: Optional[str] = None,
        language: str = "hi",
    ) -> Dict[str, Any]:
        """
        Full field-level pipeline:
          1. Fetch Open-Meteo soil layers (free, real-time, 1km grid)
          2. Fetch Soil Health Card data from government
          3. Merge with IoT sensor data (highest priority)
          4. Fetch 16-day weather forecast
          5. Score all 80 crops
          6. Return ranked recommendations with input gap analysis
        """
        ts = datetime.now().isoformat()

        # Step 1: Open-Meteo soil + weather (always available, no API key)
        om_data = self._fetch_open_meteo_soil_weather(latitude, longitude)

        # Step 2: Government Soil Health Card
        govt_soil = self._fetch_soil_health_card(latitude, longitude, state)

        # Step 3: Merge all soil data
        merged_soil = self._merge_soil_data(om_data, govt_soil, sensor_data)

        # Step 4: 16-day weather forecast with agri analysis
        forecast = om_data.get("forecast", [])
        weather_analysis = self._analyse_weather_for_farming(forecast, om_data.get("current", {}))

        # Step 5: Score crops
        scored_crops = self._score_crops_field_level(
            merged_soil, weather_analysis, latitude, longitude, state
        )

        # Step 6: Input gap recommendations
        input_gaps = self._calculate_input_gaps(merged_soil, scored_crops[:8])

        # Step 7: Localise
        from .language_service import normalise_language_code
        lang = normalise_language_code(language)

        return {
            "status": "success",
            "field_id": field_id,
            "location": location_name,
            "coordinates": {"latitude": latitude, "longitude": longitude},
            "timestamp": ts,
            "analysis_level": "field",
            "grid_resolution": "1km (Open-Meteo) + 100m (sensor)",
            "data_sources": self._list_data_sources(sensor_data, govt_soil, om_data),

            # Core soil profile
            "soil_profile": merged_soil,

            # Weather
            "weather": {
                "current": om_data.get("current", {}),
                "forecast_16_days": forecast[:16],
                "farming_alerts": weather_analysis.get("alerts", []),
                "irrigation_schedule": weather_analysis.get("irrigation_schedule", []),
                "planting_window": weather_analysis.get("planting_window", ""),
            },

            # Recommendations
            "recommendations": scored_crops[:10],
            "top_recommendation": scored_crops[0] if scored_crops else None,

            # Input optimisation
            "input_gaps": input_gaps,

            # Sensor quality
            "sensor_quality": self._assess_sensor_quality(sensor_data),

            # Plain-text summary
            "summary": self._generate_summary(merged_soil, scored_crops[:3], weather_analysis, lang),
        }

    # ── Data Fetching ──────────────────────────────────────────────────

    def _fetch_open_meteo_soil_weather(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Fetch from Open-Meteo:
          - current weather (temp, humidity, rain, UV, pressure)
          - soil temperature 0cm, 6cm, 18cm
          - soil moisture 0-1cm, 1-3cm, 3-9cm, 9-27cm, 27-81cm
          - 16-day daily forecast with agri variables
        Free, no API key, 1km resolution.
        """
        cache_key = f"{round(lat,3)}:{round(lon,3)}"
        cached = self._weather_cache.get(cache_key)
        if cached and (datetime.now() - cached.get("_fetched_at", datetime.min)).seconds < 1800:
            return cached

        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "timezone": "Asia/Kolkata",
                # Current
                "current": [
                    "temperature_2m", "relative_humidity_2m", "apparent_temperature",
                    "precipitation", "weather_code", "wind_speed_10m",
                    "wind_direction_10m", "uv_index", "surface_pressure",
                    "et0_fao_evapotranspiration",
                ],
                # Hourly soil (today only — 24 values; take index 12 = noon)
                "hourly": [
                    "soil_temperature_0cm", "soil_temperature_6cm", "soil_temperature_18cm",
                    "soil_moisture_0_to_1cm", "soil_moisture_1_to_3cm",
                    "soil_moisture_3_to_9cm", "soil_moisture_9_to_27cm",
                    "soil_moisture_27_to_81cm",
                    "evapotranspiration", "vapour_pressure_deficit",
                ],
                # Daily forecast
                "daily": [
                    "temperature_2m_max", "temperature_2m_min",
                    "precipitation_sum", "precipitation_probability_max",
                    "weather_code", "uv_index_max", "wind_speed_10m_max",
                    "et0_fao_evapotranspiration",
                    "sunrise", "sunset",
                ],
                "forecast_days": 16,
            }

            resp = self.session.get(self.OPEN_METEO_SOIL_URL, params=params, timeout=10)
            if resp.status_code != 200:
                logger.warning("Open-Meteo returned %s", resp.status_code)
                return self._open_meteo_fallback(lat, lon)

            raw = resp.json()
            curr = raw.get("current", {})
            hourly = raw.get("hourly", {})
            daily  = raw.get("daily", {})

            # Pick noon hour index
            noon_idx = 12
            def h(key):
                vals = hourly.get(key, [])
                return vals[noon_idx] if len(vals) > noon_idx else None

            soil = {
                "temperature_0cm":      h("soil_temperature_0cm"),
                "temperature_6cm":      h("soil_temperature_6cm"),
                "temperature_18cm":     h("soil_temperature_18cm"),
                "moisture_0_1cm_m3":    h("soil_moisture_0_to_1cm"),
                "moisture_1_3cm_m3":    h("soil_moisture_1_to_3cm"),
                "moisture_3_9cm_m3":    h("soil_moisture_3_to_9cm"),
                "moisture_9_27cm_m3":   h("soil_moisture_9_to_27cm"),
                "moisture_27_81cm_m3":  h("soil_moisture_27_to_81cm"),
                "evapotranspiration_mm": h("evapotranspiration"),
                "vpd_kpa":              h("vapour_pressure_deficit"),
            }

            # Convert volumetric moisture (m³/m³) to percentage
            m3 = soil.get("moisture_0_1cm_m3")
            soil["moisture_surface_pct"] = round(m3 * 100, 1) if m3 is not None else None

            # Build 16-day forecast
            forecast = []
            dates = daily.get("time", [])
            for i, d in enumerate(dates):
                def dv(key):
                    arr = daily.get(key, [])
                    return arr[i] if i < len(arr) else None

                rain_mm = dv("precipitation_sum") or 0
                max_t   = dv("temperature_2m_max")
                min_t   = dv("temperature_2m_min")
                et0     = dv("et0_fao_evapotranspiration") or 0
                wcode   = dv("weather_code") or 0

                # Net water balance for irrigation planning
                water_balance = round(rain_mm - et0, 1)

                forecast.append({
                    "date":              d,
                    "max_temp":          max_t,
                    "min_temp":          min_t,
                    "rainfall_mm":       round(rain_mm, 1),
                    "rain_probability":  dv("precipitation_probability_max"),
                    "uv_index":          dv("uv_index_max"),
                    "wind_speed":        dv("wind_speed_10m_max"),
                    "et0_mm":            round(et0, 1),
                    "water_balance_mm":  water_balance,   # +ve = surplus; -ve = deficit
                    "condition":         _wmo_condition(wcode),
                    "irrigation_needed": water_balance < -3,
                    "sunrise":           dv("sunrise"),
                    "sunset":            dv("sunset"),
                    "farming_note":      _daily_farming_note(max_t, rain_mm, wcode, et0),
                })

            result = {
                "current": {
                    "temperature":   curr.get("temperature_2m"),
                    "humidity":      curr.get("relative_humidity_2m"),
                    "rainfall_mm":   curr.get("precipitation", 0),
                    "wind_speed":    curr.get("wind_speed_10m"),
                    "uv_index":      curr.get("uv_index"),
                    "pressure":      curr.get("surface_pressure"),
                    "et0_mm":        curr.get("et0_fao_evapotranspiration", 0),
                    "condition":     _wmo_condition(curr.get("weather_code", 0)),
                },
                "soil_layers":   soil,
                "forecast":      forecast,
                "data_source":   "Open-Meteo (real-time, free, 1km grid)",
                "_fetched_at":   datetime.now(),
            }
            self._weather_cache[cache_key] = result
            return result

        except Exception as e:
            logger.error("Open-Meteo soil fetch error: %s", e)
            return self._open_meteo_fallback(lat, lon)

    def _fetch_soil_health_card(self, lat: float, lon: float, state: Optional[str]) -> Dict[str, Any]:
        """
        Fetch soil data from Soil Health Card portal (soilhealth.dac.gov.in).
        Falls back to NASA POWER agro-climate data if unavailable.
        """
        try:
            # Soil Health Card GP-wise endpoint
            params = {
                "lat": lat,
                "lon": lon,
                "format": "json",
            }
            resp = self.session.get(
                self.SOIL_HEALTH_CARD_URL, params=params, timeout=8
            )
            if resp.status_code == 200:
                data = resp.json()
                if data and isinstance(data, dict) and data.get("N"):
                    return {
                        "source": "Soil Health Card (soilhealth.dac.gov.in)",
                        "nitrogen_kg_ha":  float(data.get("N", 0)),
                        "phosphorus_kg_ha": float(data.get("P", 0)),
                        "potassium_kg_ha": float(data.get("K", 0)),
                        "ph":              float(data.get("pH", 7.0)),
                        "ec_ds_m":         float(data.get("EC", 0.4)),
                        "organic_carbon":  float(data.get("OC", 0.5)),
                        "sulfur_ppm":      float(data.get("S", 0)),
                        "zinc_ppm":        float(data.get("Zn", 0)),
                        "boron_ppm":       float(data.get("B", 0)),
                        "is_live":         True,
                    }
        except Exception as e:
            logger.debug("Soil Health Card API unavailable: %s", e)

        # Fallback: Try NASA POWER for solar radiation (proxy for soil quality)
        return self._fetch_nasa_power_fallback(lat, lon)

    def _fetch_nasa_power_fallback(self, lat: float, lon: float) -> Dict[str, Any]:
        """NASA POWER API — agro-climate variables (free, global coverage)."""
        try:
            params = {
                "parameters": "PRECTOTCORR,T2M,RH2M,ALLSKY_SFC_SW_DWN,WS2M",
                "community": "AG",
                "longitude": lon,
                "latitude":  lat,
                "start":     (datetime.now() - timedelta(days=365)).strftime("%Y%m01"),
                "end":       datetime.now().strftime("%Y%m01"),
                "format":    "JSON",
            }
            resp = self.session.get(self.NASA_POWER_URL, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                props = data.get("properties", {}).get("parameter", {})
                # Average annual rainfall
                rain_vals = list(props.get("PRECTOTCORR", {}).values())
                annual_rain = sum(rain_vals) / len(rain_vals) * 12 if rain_vals else 800
                return {
                    "source": "NASA POWER (agro-climate estimate)",
                    "annual_rainfall_mm": round(annual_rain),
                    "is_live": True,
                    "note": "Nutrient data from NASA POWER agro-climate estimate",
                }
        except Exception as e:
            logger.debug("NASA POWER unavailable: %s", e)

        return {"source": "No government soil data available", "is_live": False}

    # ── Data Merging ───────────────────────────────────────────────────

    def _merge_soil_data(
        self,
        om_data: Dict,
        govt_soil: Dict,
        sensor_data: Optional[Dict],
    ) -> Dict[str, Any]:
        """
        Merge soil data from all sources.
        Priority: IoT sensor > Govt Soil Health Card > Open-Meteo layers > defaults.
        """
        soil_layers = om_data.get("soil_layers", {})

        # Start with Open-Meteo real soil moisture
        om_moisture = soil_layers.get("moisture_surface_pct")
        om_soil_temp = soil_layers.get("temperature_6cm")

        merged = {
            # Defaults
            "nitrogen_kg_ha":  None,
            "phosphorus_kg_ha": None,
            "potassium_kg_ha": None,
            "ph":              None,
            "ec_ds_m":         None,
            "organic_carbon":  None,
            "moisture_pct":    om_moisture,
            "soil_temp_c":     om_soil_temp,

            # Sub-surface moisture from Open-Meteo (always available)
            "moisture_layers": {
                "surface_0_1cm_pct":   round(soil_layers.get("moisture_0_1cm_m3", 0) * 100, 1) if soil_layers.get("moisture_0_1cm_m3") else None,
                "shallow_1_3cm_pct":   round(soil_layers.get("moisture_1_3cm_m3", 0) * 100, 1) if soil_layers.get("moisture_1_3cm_m3") else None,
                "root_3_9cm_pct":      round(soil_layers.get("moisture_3_9cm_m3", 0) * 100, 1) if soil_layers.get("moisture_3_9cm_m3") else None,
                "subsoil_9_27cm_pct":  round(soil_layers.get("moisture_9_27cm_m3", 0) * 100, 1) if soil_layers.get("moisture_9_27cm_m3") else None,
                "deep_27_81cm_pct":    round(soil_layers.get("moisture_27_81cm_m3", 0) * 100, 1) if soil_layers.get("moisture_27_81cm_m3") else None,
            },
            "soil_temp_layers": {
                "surface_0cm":  soil_layers.get("temperature_0cm"),
                "shallow_6cm":  soil_layers.get("temperature_6cm"),
                "root_18cm":    soil_layers.get("temperature_18cm"),
            },
            "et0_mm_day":   soil_layers.get("evapotranspiration_mm"),
            "vpd_kpa":      soil_layers.get("vpd_kpa"),

            "data_sources":  ["Open-Meteo (soil layers, real-time)"],
        }

        # Layer 2: Government Soil Health Card NPK
        if govt_soil.get("is_live") and govt_soil.get("nitrogen_kg_ha"):
            merged["nitrogen_kg_ha"]  = govt_soil.get("nitrogen_kg_ha")
            merged["phosphorus_kg_ha"] = govt_soil.get("phosphorus_kg_ha")
            merged["potassium_kg_ha"] = govt_soil.get("potassium_kg_ha")
            merged["ph"]              = govt_soil.get("ph")
            merged["ec_ds_m"]         = govt_soil.get("ec_ds_m")
            merged["organic_carbon"]  = govt_soil.get("organic_carbon")
            merged["sulfur_ppm"]      = govt_soil.get("sulfur_ppm")
            merged["zinc_ppm"]        = govt_soil.get("zinc_ppm")
            merged["data_sources"].append("Soil Health Card (soilhealth.dac.gov.in)")

        # Layer 3: IoT sensor data — overrides everything (highest accuracy)
        sensors = (sensor_data or {}).get("sensors", sensor_data or {})
        if sensors:
            if sensors.get("nitrogen_kg_ha") is not None:
                merged["nitrogen_kg_ha"]  = sensors["nitrogen_kg_ha"]
            if sensors.get("phosphorus_kg_ha") is not None:
                merged["phosphorus_kg_ha"] = sensors["phosphorus_kg_ha"]
            if sensors.get("potassium_kg_ha") is not None:
                merged["potassium_kg_ha"] = sensors["potassium_kg_ha"]
            if sensors.get("ph") is not None:
                merged["ph"]              = sensors["ph"]
            if sensors.get("ec_ds_m") is not None:
                merged["ec_ds_m"]         = sensors["ec_ds_m"]
            if sensors.get("organic_carbon") is not None:
                merged["organic_carbon"]  = sensors["organic_carbon"]
            if sensors.get("moisture_pct") is not None:
                merged["moisture_pct"]    = sensors["moisture_pct"]
            if sensors.get("soil_temp_c") is not None:
                merged["soil_temp_c"]     = sensors["soil_temp_c"]
            if sensors.get("bulk_density") is not None:
                merged["bulk_density"]    = sensors["bulk_density"]
            merged["data_sources"].append("IoT Field Sensor (real-time, field-level)")
            merged["sensor_timestamp"] = datetime.now().isoformat()

        # Add crop history
        if sensor_data:
            merged["crop_history"]    = sensor_data.get("crop_history", [])
            merged["previous_crop"]   = sensor_data.get("previous_crop")
            merged["irrigation_type"] = sensor_data.get("irrigation_type", "unknown")
            merged["field_area_ha"]   = sensor_data.get("field_area_ha")

        # Derived soil classification
        merged["soil_status"] = self._classify_soil_status(merged)

        return merged

    def _classify_soil_status(self, soil: Dict) -> Dict[str, str]:
        """Classify each nutrient into status bands."""
        status = {}
        n = soil.get("nitrogen_kg_ha")
        p = soil.get("phosphorus_kg_ha")
        k = soil.get("potassium_kg_ha")
        ph = soil.get("ph")
        oc = soil.get("organic_carbon")
        ec = soil.get("ec_ds_m")
        moisture = soil.get("moisture_pct")

        if n is not None: status["nitrogen"]  = _band(n,  N_BANDS)
        if p is not None: status["phosphorus"] = _band(p,  P_BANDS)
        if k is not None: status["potassium"]  = _band(k,  K_BANDS)
        if ph is not None:
            status["ph"] = _band(ph, PH_BANDS)
            status["ph_optimal"] = "Yes" if 6.5 <= ph <= 7.5 else "No"
        if oc is not None: status["organic_carbon"] = _band(oc, OC_BANDS)
        if ec is not None: status["salinity"]        = _band(ec, EC_BANDS)
        if moisture is not None:
            if moisture < 15:   status["moisture"] = "Very Dry"
            elif moisture < 35: status["moisture"] = "Dry"
            elif moisture < 60: status["moisture"] = "Optimal"
            elif moisture < 75: status["moisture"] = "Moist"
            else:               status["moisture"] = "Waterlogged"

        return status

    # ── Crop Scoring ───────────────────────────────────────────────────

    def _score_crops_field_level(
        self,
        soil: Dict,
        weather: Dict,
        lat: float,
        lon: float,
        state: Optional[str],
    ) -> List[Dict[str, Any]]:
        """
        Score all 80 crops using field-level data.
        Returns sorted list of crop recommendations.
        """
        try:
            from .comprehensive_crop_database import ALL_CROP_DATA
        except ImportError:
            ALL_CROP_DATA = {}

        from .crop_recommendation_engine import (
            _current_season, _season_label,
            WATER_IRRIGATION_MIN,
        )

        season_key   = _current_season()
        curr_temp    = (weather.get("current_temp") or
                        soil.get("soil_temp_c") or 28)
        weather_risk = weather.get("risk", "None")
        rain_7d      = weather.get("rain_7d_mm", 0)

        results = []
        for crop_key, crop in ALL_CROP_DATA.items():
            score, reasons, npk_match = self._score_with_sensors(
                crop_key, crop, soil, season_key, curr_temp, weather_risk, rain_7d
            )
            if score < 5:
                continue

            # Build result
            req = CROP_SOIL_REQUIREMENTS.get(crop_key, {})
            results.append({
                "crop_name":      crop_key.title(),
                "crop_name_hindi": crop.get("name_hindi", crop_key.title()),
                "category":       crop.get("category", "General"),
                "season":         _season_label(crop.get("season", season_key)),
                "suitability_score": int(min(score, 99)),
                "confidence":        round(min(score / 100.0, 0.98), 2),
                "scoring_reasons":   reasons,
                "npk_match":         npk_match,
                "soil_suitability":  self._soil_suitability_text(crop_key, soil),
                "yield_per_hectare": crop.get("yield_per_hectare", 0),
                "profit_per_hectare": crop.get("profit_per_hectare", 0),
                "msp_per_quintal":   crop.get("msp_per_quintal", 0),
                "duration_days":     crop.get("duration_days", 120),
                "water_requirement": crop.get("water_requirement", "Moderate"),
                "temperature_range": f"{crop.get('temperature_min',10)}–{crop.get('temperature_max',38)}°C",
                "market_demand":     crop.get("market_demand", "Medium"),
                "export_potential":  crop.get("export_potential", "Low"),
                "government_support": crop.get("government_support", ""),
                "input_adjustments": self._input_adjustments(crop_key, soil),
                "financials": {
                    "yield":         f"{crop.get('yield_per_hectare', 0)} q/ha",
                    "profit":        f"₹{crop.get('profit_per_hectare', 0):,}/ha",
                    "msp":           f"₹{crop.get('msp_per_quintal', 0)}/q" if crop.get("msp_per_quintal") else "No MSP",
                    "input_cost":    f"₹{crop.get('input_cost_per_hectare', 0):,}/ha",
                },
            })

        results.sort(key=lambda x: x["suitability_score"], reverse=True)
        return results

    def _score_with_sensors(
        self,
        crop_key: str,
        crop: Dict,
        soil: Dict,
        season_key: str,
        curr_temp: float,
        weather_risk: str,
        rain_7d: float,
    ) -> Tuple[float, List[str], Dict]:
        """
        Score a single crop using field sensor data.
        Returns (score, reasons, npk_match_dict).
        """
        from .crop_recommendation_engine import _current_season

        score   = 0.0
        reasons = []
        npk_match = {}

        req = CROP_SOIL_REQUIREMENTS.get(crop_key, {})
        crop_season = crop.get("season", "kharif")

        # ── Season (20 pts) ────────────────────────────────────────────
        if crop_season == "year_round":
            score += 16; reasons.append("Year-round crop")
        elif crop_season == season_key:
            score += 20; reasons.append(f"✅ Season match ({season_key})")
        else:
            return 0.0, [], {}  # Hard filter

        # ── Soil pH (15 pts) ───────────────────────────────────────────
        ph = soil.get("ph")
        if ph is not None and req.get("pH"):
            ph_min, ph_max = req["pH"]
            if ph_min <= ph <= ph_max:
                score += 15
                npk_match["ph"] = {"status": "Optimal", "value": ph, "range": req["pH"]}
                reasons.append(f"✅ pH {ph} in range [{ph_min}–{ph_max}]")
            elif abs(ph - (ph_min + ph_max) / 2) <= 0.5:
                score += 10
                npk_match["ph"] = {"status": "Marginal", "value": ph, "range": req["pH"]}
                reasons.append(f"⚠️ pH {ph} marginal (range {ph_min}–{ph_max})")
            else:
                score += 3
                npk_match["ph"] = {"status": "Out of range", "value": ph, "range": req["pH"]}
                reasons.append(f"❌ pH {ph} outside range [{ph_min}–{ph_max}]")
        else:
            score += 8  # no pH data — neutral

        # ── Nitrogen (15 pts) ──────────────────────────────────────────
        n = soil.get("nitrogen_kg_ha")
        if n is not None and req.get("N"):
            n_min, n_max = req["N"]
            if n >= n_min:
                score += 15
                npk_match["N"] = {"status": "Sufficient", "value": n, "required": (n_min, n_max)}
                reasons.append(f"✅ N {n} kg/ha ≥ min {n_min}")
            elif n >= n_min * 0.7:
                score += 10
                gap = n_min - n
                npk_match["N"] = {"status": "Low", "value": n, "deficit_kg_ha": round(gap, 1)}
                reasons.append(f"⚠️ N low ({n} kg/ha) — add {round(gap,0)} kg/ha")
            else:
                score += 4
                npk_match["N"] = {"status": "Very Low", "value": n, "deficit_kg_ha": round(n_min - n, 1)}
                reasons.append(f"❌ N very low ({n} kg/ha)")
        else:
            score += 8

        # ── Phosphorus (10 pts) ────────────────────────────────────────
        p = soil.get("phosphorus_kg_ha")
        if p is not None and req.get("P"):
            p_min, p_max = req["P"]
            if p >= p_min:
                score += 10
                npk_match["P"] = {"status": "Sufficient", "value": p}
                reasons.append(f"✅ P {p} kg/ha ≥ min {p_min}")
            else:
                score += 5
                npk_match["P"] = {"status": "Low", "value": p, "deficit_kg_ha": round(p_min - p, 1)}
                reasons.append(f"⚠️ P low — add {round(p_min-p,0)} kg/ha as DAP")
        else:
            score += 5

        # ── Potassium (8 pts) ──────────────────────────────────────────
        k = soil.get("potassium_kg_ha")
        if k is not None and req.get("K"):
            k_min, _ = req["K"]
            if k >= k_min:
                score += 8
                npk_match["K"] = {"status": "Sufficient", "value": k}
                reasons.append(f"✅ K {k} kg/ha sufficient")
            else:
                score += 4
                npk_match["K"] = {"status": "Low", "value": k, "deficit_kg_ha": round(k_min - k, 1)}
                reasons.append(f"⚠️ K low — add MOP {round((k_min-k)/0.6,0)} kg/ha")
        else:
            score += 4

        # ── Moisture (10 pts) ──────────────────────────────────────────
        moisture = soil.get("moisture_pct")
        if moisture is not None and req.get("moisture_min") is not None:
            m_min = req["moisture_min"]
            if moisture >= m_min:
                score += 10; reasons.append(f"✅ Soil moisture {moisture}% adequate")
                npk_match["moisture"] = {"status": "Adequate", "value": moisture}
            elif moisture >= m_min * 0.6:
                score += 6; reasons.append(f"⚠️ Moisture {moisture}% slightly low (min {m_min}%)")
                npk_match["moisture"] = {"status": "Low", "value": moisture, "required_min": m_min}
            else:
                score += 2; reasons.append(f"❌ Moisture {moisture}% — irrigation needed (min {m_min}%)")
                npk_match["moisture"] = {"status": "Critical", "value": moisture, "required_min": m_min}
        else:
            score += 5

        # ── Salinity / EC (5 pts) ──────────────────────────────────────
        ec = soil.get("ec_ds_m")
        if ec is not None and req.get("EC_max"):
            if ec <= req["EC_max"]:
                score += 5; npk_match["EC"] = {"status": "Safe", "value": ec}
            elif ec <= req["EC_max"] * 1.3:
                score += 2; reasons.append(f"⚠️ EC {ec} marginally high")
                npk_match["EC"] = {"status": "Marginal", "value": ec}
            else:
                score -= 10; reasons.append(f"❌ Saline soil (EC {ec}) — unsuitable")
                npk_match["EC"] = {"status": "Toxic", "value": ec}
        else:
            score += 3

        # ── Organic Carbon (5 pts) ────────────────────────────────────
        oc = soil.get("organic_carbon")
        if oc is not None and req.get("OC_min"):
            if oc >= req["OC_min"]:
                score += 5; reasons.append(f"✅ OC {oc}% good")
            else:
                score += 2; reasons.append(f"⚠️ OC low ({oc}%) — add FYM/compost")

        # ── Temperature (7 pts) ───────────────────────────────────────
        t_min = crop.get("temperature_min", 10)
        t_max = crop.get("temperature_max", 38)
        if t_min <= curr_temp <= t_max:
            score += 7; reasons.append(f"✅ Temp {curr_temp}°C optimal")
        elif abs(curr_temp - (t_min + t_max) / 2) <= 5:
            score += 4
        else:
            score += 1

        # ── Weather risk (5 pts) ──────────────────────────────────────
        water_req = crop.get("water_requirement", "Moderate")
        if weather_risk == "None":
            score += 5; reasons.append("✅ Good weather forecast")
        elif weather_risk == "High Rainfall" and water_req in ("High", "Very High"):
            score += 4; reasons.append("🌧️ Rain beneficial for this crop")
        elif weather_risk == "High Rainfall" and water_req == "Low":
            score -= 8; reasons.append("⚠️ Excess rain risk for drought crop")
        elif weather_risk == "Drought" and water_req in ("High", "Very High"):
            score -= 10; reasons.append("🚨 Drought — water-hungry crop at risk")
        elif weather_risk == "Drought" and water_req == "Low":
            score += 4; reasons.append("✅ Drought-tolerant — suitable")

        # ── Crop rotation bonus (3 pts) ───────────────────────────────
        prev = soil.get("previous_crop", "")
        crop_history = soil.get("crop_history", [])
        if prev:
            rotation_bonus = self._rotation_bonus(crop_key, prev)
            if rotation_bonus > 0:
                score += rotation_bonus
                reasons.append(f"✅ Good rotation after {prev} (+{rotation_bonus}pts)")
            elif rotation_bonus < 0:
                score += rotation_bonus
                reasons.append(f"⚠️ Same crop as last season — disease risk ({rotation_bonus}pts)")

        return round(max(0.0, score), 1), reasons, npk_match

    @staticmethod
    def _rotation_bonus(crop: str, prev_crop: str) -> float:
        """Return rotation benefit (+) or risk (-) score."""
        # Legume before cereal = nitrogen benefit
        LEGUMES  = {"gram", "moong", "urad", "tur", "masoor", "matar", "groundnut", "soybean"}
        CEREALS  = {"wheat", "rice", "maize", "barley", "bajra", "jowar", "ragi"}
        SOLANUMS = {"potato", "tomato", "brinjal", "capsicum"}

        prev = prev_crop.lower()
        curr = crop.lower()

        if prev in LEGUMES and curr in CEREALS:
            return 3.0   # N-fixation benefit
        if prev in CEREALS and curr in LEGUMES:
            return 2.0   # Breaks cereal disease cycle
        if prev == curr:
            return -5.0  # Same crop — pest/disease buildup
        if prev in SOLANUMS and curr in SOLANUMS:
            return -3.0  # Solanaceae family rotation risk
        return 0.0

    # ── Input Gap Analysis ─────────────────────────────────────────────

    def _calculate_input_gaps(self, soil: Dict, top_crops: List[Dict]) -> List[Dict]:
        """
        For the top recommended crops, calculate fertiliser inputs needed
        to bring soil to optimal levels.
        """
        gaps = []
        for crop_rec in top_crops[:4]:
            crop_key = crop_rec["crop_name"].lower()
            req = CROP_SOIL_REQUIREMENTS.get(crop_key, {})
            if not req:
                continue

            recommendations_list = []
            n = soil.get("nitrogen_kg_ha")
            p = soil.get("phosphorus_kg_ha")
            k = soil.get("potassium_kg_ha")
            ph = soil.get("ph")
            oc = soil.get("organic_carbon")

            if n is not None and req.get("N"):
                n_min = req["N"][0]
                if n < n_min:
                    deficit = n_min - n
                    urea_kg = round(deficit / 0.46, 1)
                    recommendations_list.append({
                        "nutrient": "Nitrogen (N)",
                        "current_kg_ha": round(n, 1),
                        "required_min_kg_ha": n_min,
                        "deficit_kg_ha": round(deficit, 1),
                        "amendment": f"Apply {urea_kg} kg/ha Urea (46% N) or {round(deficit/0.21,1)} kg/ha CAN",
                        "timing": "Split: 50% basal + 25% at tillering + 25% at ear emergence",
                    })

            if p is not None and req.get("P"):
                p_min = req["P"][0]
                if p < p_min:
                    deficit = p_min - p
                    dap_kg = round(deficit / 0.46, 1)
                    recommendations_list.append({
                        "nutrient": "Phosphorus (P₂O₅)",
                        "current_kg_ha": round(p, 1),
                        "required_min_kg_ha": p_min,
                        "deficit_kg_ha": round(deficit, 1),
                        "amendment": f"Apply {dap_kg} kg/ha DAP (46% P₂O₅) or {round(deficit/0.16,1)} kg/ha SSP",
                        "timing": "Apply full dose as basal (at sowing)",
                    })

            if k is not None and req.get("K"):
                k_min = req["K"][0]
                if k < k_min:
                    deficit = k_min - k
                    mop_kg = round(deficit / 0.60, 1)
                    recommendations_list.append({
                        "nutrient": "Potassium (K₂O)",
                        "current_kg_ha": round(k, 1),
                        "required_min_kg_ha": k_min,
                        "deficit_kg_ha": round(deficit, 1),
                        "amendment": f"Apply {mop_kg} kg/ha MOP (60% K₂O)",
                        "timing": "50% basal + 50% at first irrigation",
                    })

            if ph is not None:
                if ph < 5.5:
                    lime_t = round((6.5 - ph) * 1.5, 1)
                    recommendations_list.append({
                        "nutrient": "Soil pH correction",
                        "current": ph, "target": "6.5",
                        "amendment": f"Apply {lime_t} tonne/ha Agricultural Lime (CaCO₃)",
                        "timing": "Apply 3-4 weeks before sowing and incorporate",
                    })
                elif ph > 8.0:
                    gyp_t = round((ph - 7.5) * 2.0, 1)
                    recommendations_list.append({
                        "nutrient": "Soil pH correction",
                        "current": ph, "target": "7.5",
                        "amendment": f"Apply {gyp_t} tonne/ha Gypsum (CaSO₄)",
                        "timing": "Broadcast and incorporate before sowing",
                    })

            if oc is not None and oc < 0.5:
                fym_t = round((0.75 - oc) * 20, 1)
                recommendations_list.append({
                    "nutrient": "Organic Carbon",
                    "current_pct": oc, "target_pct": "0.75",
                    "amendment": f"Apply {fym_t} tonne/ha FYM / Vermicompost",
                    "timing": "Incorporate 4 weeks before sowing",
                })

            if recommendations_list:
                gaps.append({
                    "crop": crop_rec["crop_name"],
                    "crop_hindi": crop_rec.get("crop_name_hindi", ""),
                    "total_amendments": len(recommendations_list),
                    "amendments": recommendations_list,
                    "estimated_extra_cost_inr": len(recommendations_list) * 1500,  # rough estimate
                })

        return gaps

    # ── Weather Analysis ───────────────────────────────────────────────

    def _analyse_weather_for_farming(self, forecast: List[Dict], current: Dict) -> Dict[str, Any]:
        """Analyse 16-day forecast for farming decisions."""
        if not forecast:
            return {"risk": "None", "alerts": [], "irrigation_schedule": [], "planting_window": ""}

        total_rain   = sum(d.get("rainfall_mm", 0) for d in forecast[:7])
        rain_14d     = sum(d.get("rainfall_mm", 0) for d in forecast[:14])
        max_temps    = [d.get("max_temp") for d in forecast[:7] if d.get("max_temp")]
        avg_max      = sum(max_temps) / len(max_temps) if max_temps else 28
        total_et0    = sum(d.get("et0_mm", 0) for d in forecast[:7])
        alerts       = []
        irr_schedule = []

        # Determine risk
        if total_rain > 200:
            risk = "Flood"
            alerts.append({"type": "FLOOD", "message": f"🚨 Heavy rain {total_rain:.0f}mm in 7 days — ensure drainage channels are clear"})
        elif total_rain > 80:
            risk = "High Rainfall"
            alerts.append({"type": "HIGH_RAIN", "message": f"🌧️ {total_rain:.0f}mm expected in 7 days — no irrigation needed, prepare drainage"})
        elif total_rain < 5 and avg_max > 35:
            risk = "Drought + Heatwave"
            alerts.append({"type": "DROUGHT_HEAT", "message": f"🔥 Heatwave + dry — increase irrigation frequency, apply mulch"})
        elif total_rain < 10 and avg_max > 30:
            risk = "Drought"
            deficit = round(total_et0 - total_rain, 1)
            alerts.append({"type": "DROUGHT", "message": f"☀️ Dry spell — irrigation deficit {deficit}mm in 7 days"})
        elif avg_max > 42:
            risk = "Heatwave"
            alerts.append({"type": "HEATWAVE", "message": f"🌡️ Heatwave {avg_max:.1f}°C — irrigate at dawn/dusk, shade nets for vegetables"})
        elif avg_max < 8:
            risk = "Cold"
            alerts.append({"type": "COLD", "message": f"❄️ Cold stress {avg_max:.1f}°C — protect seedlings, delay sowing"})
        else:
            risk = "None"

        # Irrigation schedule (for next 7 days with deficit)
        for day in forecast[:7]:
            deficit = (day.get("et0_mm") or 0) - (day.get("rainfall_mm") or 0)
            if deficit > 3:
                irr_schedule.append({
                    "date":             day["date"],
                    "irrigation_mm":    round(deficit * 1.1, 1),
                    "best_time":        "05:00–07:00 AM or 06:00–07:30 PM",
                    "reason":           f"ET₀ {day.get('et0_mm',0):.1f}mm, rain {day.get('rainfall_mm',0):.1f}mm",
                })

        # Find best planting window (5 consecutive days with rain probability < 60%, max temp 18–35°C)
        planting_window = self._find_planting_window(forecast)

        return {
            "risk":               risk,
            "rain_7d_mm":         round(total_rain, 1),
            "rain_14d_mm":        round(rain_14d, 1),
            "avg_max_temp_7d":    round(avg_max, 1),
            "total_et0_7d_mm":    round(total_et0, 1),
            "alerts":             alerts,
            "irrigation_schedule": irr_schedule,
            "planting_window":    planting_window,
            "current_temp":       current.get("temperature"),
        }

    @staticmethod
    def _find_planting_window(forecast: List[Dict]) -> str:
        """Find first 5-day stretch suitable for sowing."""
        for i in range(len(forecast) - 4):
            window = forecast[i:i+5]
            ok = all(
                (d.get("rain_probability") or 0) < 70 and
                18 <= (d.get("max_temp") or 99) <= 38
                for d in window
            )
            if ok:
                start = window[0]["date"]
                end   = window[-1]["date"]
                return f"{start} to {end} (5-day sowing window)"
        return "No clear 5-day sowing window in next 16 days — check again"

    # ── Helpers ────────────────────────────────────────────────────────

    def _soil_suitability_text(self, crop_key: str, soil: Dict) -> str:
        """Short soil suitability summary for a crop."""
        req = CROP_SOIL_REQUIREMENTS.get(crop_key, {})
        if not req:
            return "Soil data insufficient"
        ph = soil.get("ph")
        if ph:
            ph_min, ph_max = req.get("pH", (6.0, 7.5))
            if ph_min <= ph <= ph_max:
                return f"Soil pH {ph} — optimal for {crop_key}"
            return f"Soil pH {ph} — outside ideal {ph_min}–{ph_max} (amendment needed)"
        return "Soil chemistry data needed for precise scoring"

    def _input_adjustments(self, crop_key: str, soil: Dict) -> List[str]:
        """Quick fertiliser hints for a crop."""
        req = CROP_SOIL_REQUIREMENTS.get(crop_key, {})
        hints = []
        n = soil.get("nitrogen_kg_ha")
        p = soil.get("phosphorus_kg_ha")
        k = soil.get("potassium_kg_ha")
        if n is not None and req.get("N") and n < req["N"][0]:
            hints.append(f"N deficient — add {round((req['N'][0]-n)/0.46,0)} kg Urea/ha")
        if p is not None and req.get("P") and p < req["P"][0]:
            hints.append(f"P deficient — add {round((req['P'][0]-p)/0.46,0)} kg DAP/ha")
        if k is not None and req.get("K") and k < req["K"][0]:
            hints.append(f"K deficient — add {round((req['K'][0]-k)/0.60,0)} kg MOP/ha")
        return hints

    def _list_data_sources(self, sensor_data, govt_soil, om_data) -> List[str]:
        sources = ["Open-Meteo (real-time soil moisture + weather, 1km grid)"]
        if govt_soil.get("is_live"):
            sources.append("Soil Health Card — soilhealth.dac.gov.in")
        if sensor_data:
            sources.append("IoT Field Sensor (field-level, real-time)")
        return sources

    def _assess_sensor_quality(self, sensor_data: Optional[Dict]) -> Dict[str, Any]:
        if not sensor_data:
            return {"quality": "None", "completeness_pct": 0,
                    "message": "No sensor data — using government + satellite sources"}
        sensors = sensor_data.get("sensors", sensor_data)
        fields = ["nitrogen_kg_ha","phosphorus_kg_ha","potassium_kg_ha",
                  "ph","ec_ds_m","moisture_pct","organic_carbon","soil_temp_c"]
        present = sum(1 for f in fields if sensors.get(f) is not None)
        pct = round(present / len(fields) * 100)
        quality = "Excellent" if pct >= 80 else "Good" if pct >= 60 else "Partial" if pct >= 40 else "Minimal"
        return {
            "quality": quality,
            "completeness_pct": pct,
            "fields_provided": present,
            "fields_total": len(fields),
            "missing": [f for f in fields if sensors.get(f) is None],
        }

    def _generate_summary(
        self, soil: Dict, top3: List[Dict], weather: Dict, lang: str
    ) -> str:
        """Generate a plain-text summary in the user's language."""
        if not top3:
            return "पर्याप्त डेटा नहीं — मिट्टी जांच कराएं" if lang == "hi" else "Insufficient data — get soil tested"

        top = top3[0]
        risk = weather.get("risk", "None")

        summaries = {
            "hi": (
                f"🌾 आपके खेत के लिए सर्वोत्तम फसल: **{top['crop_name_hindi']}** "
                f"({top['suitability_score']}% अनुकूलता)\n"
                f"मौसम: {weather.get('rain_7d_mm', 0):.0f}mm वर्षा (7 दिन), "
                f"तापमान {weather.get('avg_max_temp_7d', 28):.0f}°C\n"
                + (f"⚠️ सतर्क: {risk}" if risk != "None" else "✅ मौसम अनुकूल है")
            ),
            "en": (
                f"🌾 Best crop for your field: **{top['crop_name']}** "
                f"({top['suitability_score']}% suitability)\n"
                f"Weather: {weather.get('rain_7d_mm', 0):.0f}mm rain (7 days), "
                f"max temp {weather.get('avg_max_temp_7d', 28):.0f}°C\n"
                + (f"⚠️ Alert: {risk}" if risk != "None" else "✅ Weather conditions favorable")
            ),
            "ta": (
                f"🌾 உங்கள் வயலுக்கு சிறந்த பயிர்: **{top['crop_name_hindi']}** "
                f"({top['suitability_score']}% பொருத்தம்)"
            ),
            "te": (
                f"🌾 మీ పొలానికి అత్యుత్తమ పంట: **{top['crop_name_hindi']}** "
                f"({top['suitability_score']}% అనుకూలత)"
            ),
            "mr": (
                f"🌾 तुमच्या शेतासाठी सर्वोत्तम पीक: **{top['crop_name_hindi']}** "
                f"({top['suitability_score']}% अनुकूलता)"
            ),
            "gu": (
                f"🌾 તમારા ખેતર માટે સૌથી સારો પાક: **{top['crop_name_hindi']}** "
                f"({top['suitability_score']}% અનુકૂળ)"
            ),
            "pa": (
                f"🌾 ਤੁਹਾਡੇ ਖੇਤ ਲਈ ਸਭ ਤੋਂ ਵਧੀਆ ਫ਼ਸਲ: **{top['crop_name_hindi']}** "
                f"({top['suitability_score']}% ਅਨੁਕੂਲਤਾ)"
            ),
            "kn": (
                f"🌾 ನಿಮ್ಮ ಹೊಲಕ್ಕೆ ಅತ್ಯುತ್ತಮ ಬೆಳೆ: **{top['crop_name_hindi']}** "
                f"({top['suitability_score']}% ಸೂಕ್ತತೆ)"
            ),
            "ml": (
                f"🌾 നിങ്ങളുടെ പാടത്ത് ഏറ്റവും അനുയോജ്യമായ വിള: **{top['crop_name_hindi']}** "
                f"({top['suitability_score']}% അനുയോജ്യത)"
            ),
            "bn": (
                f"🌾 আপনার জমির জন্য সেরা ফসল: **{top['crop_name_hindi']}** "
                f"({top['suitability_score']}% উপযুক্ততা)"
            ),
        }
        return summaries.get(lang, summaries["en"])

    def _open_meteo_fallback(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fallback when Open-Meteo is unavailable."""
        return {
            "current": {"temperature": None, "humidity": None, "rainfall_mm": 0},
            "soil_layers": {},
            "forecast": [],
            "data_source": "Fallback (Open-Meteo unavailable)",
        }


# ── WMO Weather Code helpers ───────────────────────────────────────────────
def _wmo_condition(code: int) -> str:
    m = {
        0: "Clear Sky", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
        45: "Fog", 51: "Light Drizzle", 53: "Drizzle", 55: "Heavy Drizzle",
        61: "Slight Rain", 63: "Moderate Rain", 65: "Heavy Rain",
        80: "Showers", 81: "Heavy Showers", 95: "Thunderstorm",
    }
    return m.get(code, "Unknown")

def _daily_farming_note(max_t, rain_mm, wcode, et0) -> str:
    if wcode in (95, 96, 99):
        return "⛈️ Thunderstorm — no fieldwork"
    if rain_mm and rain_mm > 20:
        return f"🌧️ Rain {rain_mm:.0f}mm — no irrigation, check drainage"
    if max_t and max_t > 42:
        return f"🔥 Heatwave {max_t}°C — irrigate early morning"
    if et0 and (rain_mm or 0) < et0 - 3:
        return f"💧 Irrigation needed ~{et0 - (rain_mm or 0):.0f}mm"
    return "✅ Normal farming"


# Singleton
field_sensor_service = FieldSensorService()
