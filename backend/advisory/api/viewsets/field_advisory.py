"""
Field-Level Precision Advisory API
Accepts IoT sensor data + GPS and returns field-specific crop recommendations.

Endpoints:
  POST /api/field-advisory/recommend/
  POST /api/field-advisory/sensor_data/
  GET  /api/field-advisory/soil_profile/?latitude=&longitude=
  GET  /api/field-advisory/weather_analysis/?latitude=&longitude=
  GET  /api/field-advisory/input_gaps/?latitude=&longitude=&crop=
"""

import logging
from datetime import datetime
from typing import Optional

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..errors import safe_error_message
from ..location_utils import attach_location_metadata, resolve_request_location
from ..validation import query_too_long, MAX_LOCATION_QUERY_LENGTH
from ...services.field_sensor_service import field_sensor_service, CROP_SOIL_REQUIREMENTS
from ...services.language_service import normalise_language_code

logger = logging.getLogger(__name__)


class FieldAdvisoryViewSet(viewsets.ViewSet):
    """
    Field-level precision crop advisory using:
      - IoT NPK/pH/EC/moisture sensors
      - Open-Meteo real-time soil layers
      - Soil Health Card (soilhealth.dac.gov.in)
      - 16-day hyperlocal weather forecast
      - 80-crop agronomic database with ICAR requirements
    """
    permission_classes = [AllowAny]

    # ── Main recommendation endpoint ──────────────────────────────────

    @action(detail=False, methods=["post", "get"])
    def recommend(self, request):
        """
        Full field-level recommendation.

        POST body (all optional except GPS):
        {
          "latitude": 28.6139,
          "longitude": 77.2090,
          "field_id": "farm_001",
          "language": "hi",
          "sensors": {
            "nitrogen_kg_ha": 140,
            "phosphorus_kg_ha": 22,
            "potassium_kg_ha": 180,
            "ph": 6.8,
            "ec_ds_m": 0.4,
            "moisture_pct": 38,
            "soil_temp_c": 24,
            "organic_carbon": 0.65
          },
          "crop_history": ["wheat", "rice"],
          "previous_crop": "wheat",
          "irrigation_type": "drip",
          "field_area_ha": 1.2
        }
        """
        try:
            ctx = resolve_request_location(request)
            data = request.data if request.method == "POST" else request.query_params

            lang        = normalise_language_code(data.get("language", "hi"))
            field_id    = data.get("field_id")
            sensor_data = None

            if request.method == "POST":
                # Accept sensor data either nested under "sensors" or flat
                raw_sensors = data.get("sensors") or {}
                if not raw_sensors:
                    # Try flat structure
                    flat_keys = ["nitrogen_kg_ha","phosphorus_kg_ha","potassium_kg_ha",
                                 "ph","ec_ds_m","moisture_pct","soil_temp_c","organic_carbon",
                                 "bulk_density"]
                    raw_sensors = {k: data.get(k) for k in flat_keys if data.get(k) is not None}

                if raw_sensors or data.get("crop_history") or data.get("previous_crop"):
                    sensor_data = {
                        "sensors":        _parse_sensor_floats(raw_sensors),
                        "crop_history":   data.get("crop_history", []),
                        "previous_crop":  data.get("previous_crop"),
                        "irrigation_type": data.get("irrigation_type", "unknown"),
                        "field_area_ha":  _safe_float(data.get("field_area_ha")),
                    }

            result = field_sensor_service.get_field_recommendation(
                latitude=ctx.latitude,
                longitude=ctx.longitude,
                sensor_data=sensor_data,
                field_id=field_id,
                location_name=ctx.display_name,
                state=ctx.state or None,
                language=lang,
            )

            return Response(attach_location_metadata(result, ctx))

        except Exception as exc:
            logger.exception("Field advisory error: %s", exc)
            return Response(
                {"status": "error", "message": safe_error_message(exc, context="field_advisory")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ── Submit raw sensor reading ──────────────────────────────────────

    @action(detail=False, methods=["post"])
    def sensor_data(self, request):
        """
        Submit IoT sensor reading. Stores it and returns a quick soil assessment.

        POST body: same sensor_data structure as /recommend/
        """
        try:
            ctx  = resolve_request_location(request)
            data = request.data
            lang = normalise_language_code(data.get("language", "hi"))

            raw_sensors = data.get("sensors") or {}
            if not raw_sensors:
                flat_keys = ["nitrogen_kg_ha","phosphorus_kg_ha","potassium_kg_ha",
                             "ph","ec_ds_m","moisture_pct","soil_temp_c","organic_carbon"]
                raw_sensors = {k: data.get(k) for k in flat_keys if data.get(k) is not None}

            if not raw_sensors:
                return Response(
                    {"status": "error", "message": "No sensor values provided"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            sensors_clean = _parse_sensor_floats(raw_sensors)

            # Quick soil classification
            from ...services.field_sensor_service import (
                _band, N_BANDS, P_BANDS, K_BANDS, PH_BANDS, OC_BANDS, EC_BANDS
            )
            soil_status = {}
            if sensors_clean.get("nitrogen_kg_ha")  is not None: soil_status["nitrogen"]  = _band(sensors_clean["nitrogen_kg_ha"],  N_BANDS)
            if sensors_clean.get("phosphorus_kg_ha") is not None: soil_status["phosphorus"] = _band(sensors_clean["phosphorus_kg_ha"], P_BANDS)
            if sensors_clean.get("potassium_kg_ha")  is not None: soil_status["potassium"]  = _band(sensors_clean["potassium_kg_ha"],  K_BANDS)
            if sensors_clean.get("ph")               is not None: soil_status["ph"]          = _band(sensors_clean["ph"],               PH_BANDS)
            if sensors_clean.get("organic_carbon")   is not None: soil_status["organic_carbon"] = _band(sensors_clean["organic_carbon"], OC_BANDS)
            if sensors_clean.get("ec_ds_m")          is not None: soil_status["salinity"]    = _band(sensors_clean["ec_ds_m"],          EC_BANDS)

            # Save to DB if model available
            _save_sensor_reading(ctx, sensors_clean, data.get("field_id"))

            return Response(attach_location_metadata({
                "status": "success",
                "message": "Sensor data received and processed",
                "sensors_received": sensors_clean,
                "soil_status": soil_status,
                "recommendations": _quick_soil_advice(soil_status, lang),
                "timestamp": datetime.now().isoformat(),
                "next_step": "Call POST /api/field-advisory/recommend/ with this sensor data for full crop recommendations",
            }, ctx))

        except Exception as exc:
            logger.exception("Sensor data error: %s", exc)
            return Response(
                {"status": "error", "message": safe_error_message(exc, context="sensor_data")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ── Soil profile only ──────────────────────────────────────────────

    @action(detail=False, methods=["get"])
    def soil_profile(self, request):
        """
        Get real-time soil moisture + temperature layers from Open-Meteo
        + Soil Health Card data for a GPS location.
        No IoT sensor needed.
        """
        try:
            ctx = resolve_request_location(request)
            lang = normalise_language_code(request.query_params.get("language", "hi"))

            om  = field_sensor_service._fetch_open_meteo_soil_weather(ctx.latitude, ctx.longitude)
            gov = field_sensor_service._fetch_soil_health_card(ctx.latitude, ctx.longitude, ctx.state)

            soil = field_sensor_service._merge_soil_data(om, gov, None)
            weather_analysis = field_sensor_service._analyse_weather_for_farming(
                om.get("forecast", []), om.get("current", {})
            )

            return Response(attach_location_metadata({
                "status":         "success",
                "soil_profile":   soil,
                "weather_current": om.get("current", {}),
                "weather_alerts": weather_analysis.get("alerts", []),
                "data_sources":   soil.get("data_sources", []),
                "timestamp":      datetime.now().isoformat(),
            }, ctx))

        except Exception as exc:
            logger.exception("Soil profile error: %s", exc)
            return Response(
                {"status": "error", "message": safe_error_message(exc, context="soil_profile")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ── 16-day weather analysis ────────────────────────────────────────

    @action(detail=False, methods=["get"])
    def weather_analysis(self, request):
        """
        16-day agri weather forecast with:
          - irrigation schedule
          - planting windows
          - farming alerts
          - daily ET₀ and water balance
        """
        try:
            ctx  = resolve_request_location(request)
            lang = normalise_language_code(request.query_params.get("language", "hi"))

            om = field_sensor_service._fetch_open_meteo_soil_weather(ctx.latitude, ctx.longitude)
            analysis = field_sensor_service._analyse_weather_for_farming(
                om.get("forecast", []), om.get("current", {})
            )

            return Response(attach_location_metadata({
                "status":              "success",
                "current_weather":     om.get("current", {}),
                "forecast_16_days":    om.get("forecast", []),
                "farming_alerts":      analysis.get("alerts", []),
                "irrigation_schedule": analysis.get("irrigation_schedule", []),
                "planting_window":     analysis.get("planting_window", ""),
                "weather_risk":        analysis.get("risk", "None"),
                "rain_7d_mm":          analysis.get("rain_7d_mm", 0),
                "rain_14d_mm":         analysis.get("rain_14d_mm", 0),
                "avg_max_temp_7d":     analysis.get("avg_max_temp_7d"),
                "data_source":         "Open-Meteo (real-time, free, 1km grid)",
                "timestamp":           datetime.now().isoformat(),
            }, ctx))

        except Exception as exc:
            logger.exception("Weather analysis error: %s", exc)
            return Response(
                {"status": "error", "message": safe_error_message(exc, context="weather_analysis")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ── Input gap for specific crop ────────────────────────────────────

    @action(detail=False, methods=["get", "post"])
    def input_gaps(self, request):
        """
        Calculate fertiliser/amendment inputs needed for a specific crop
        given the current soil profile.

        GET params: latitude, longitude, crop=wheat, [sensor params]
        POST body:  sensors + crop
        """
        try:
            ctx  = resolve_request_location(request)
            data = request.data if request.method == "POST" else request.query_params
            lang = normalise_language_code(data.get("language", "hi"))
            crop = data.get("crop", "wheat").lower().strip()

            raw_sensors = data.get("sensors") or {}
            if not raw_sensors and request.method == "GET":
                flat_keys = ["nitrogen_kg_ha","phosphorus_kg_ha","potassium_kg_ha",
                             "ph","ec_ds_m","moisture_pct","organic_carbon"]
                raw_sensors = {k: data.get(k) for k in flat_keys if data.get(k) is not None}

            sensors_clean = _parse_sensor_floats(raw_sensors)

            # Build soil profile
            om  = field_sensor_service._fetch_open_meteo_soil_weather(ctx.latitude, ctx.longitude)
            gov = field_sensor_service._fetch_soil_health_card(ctx.latitude, ctx.longitude, ctx.state)
            soil = field_sensor_service._merge_soil_data(om, gov, {"sensors": sensors_clean} if sensors_clean else None)

            # Crop requirements
            req = CROP_SOIL_REQUIREMENTS.get(crop, {})
            if not req:
                return Response(
                    {"status": "error", "message": f"Crop '{crop}' not in ICAR requirements database"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            gaps = field_sensor_service._calculate_input_gaps(soil, [{"crop_name": crop.title(), "crop_name_hindi": crop}])

            return Response(attach_location_metadata({
                "status":           "success",
                "crop":             crop.title(),
                "soil_profile":     soil,
                "crop_requirements": req,
                "input_gaps":       gaps,
                "data_sources":     soil.get("data_sources", []),
                "timestamp":        datetime.now().isoformat(),
            }, ctx))

        except Exception as exc:
            logger.exception("Input gaps error: %s", exc)
            return Response(
                {"status": "error", "message": safe_error_message(exc, context="input_gaps")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ── Sensor requirements info ───────────────────────────────────────

    def list(self, request):
        """API info — list sensor parameters and crop requirements."""
        return Response({
            "service": "KrishiMitra Field-Level Precision Advisory",
            "version": "1.0",
            "endpoints": {
                "POST /api/field-advisory/recommend/":       "Full field recommendation with optional sensor data",
                "POST /api/field-advisory/sensor_data/":     "Submit IoT sensor reading",
                "GET  /api/field-advisory/soil_profile/":    "Real-time soil layers (Open-Meteo + Soil Health Card)",
                "GET  /api/field-advisory/weather_analysis/": "16-day agri forecast with irrigation schedule",
                "GET  /api/field-advisory/input_gaps/":      "Fertiliser input gap calculator",
            },
            "sensor_fields": {
                "nitrogen_kg_ha":   "Available N in soil (kg/ha) — from NPK sensor or soil test",
                "phosphorus_kg_ha": "Available P₂O₅ (kg/ha)",
                "potassium_kg_ha":  "Available K₂O (kg/ha)",
                "ph":               "Soil pH (0-14)",
                "ec_ds_m":          "Electrical Conductivity dS/m (salinity)",
                "moisture_pct":     "Volumetric soil moisture %",
                "soil_temp_c":      "Soil temperature °C",
                "organic_carbon":   "Organic Carbon % (OC)",
                "bulk_density":     "Bulk density g/cm³ (optional)",
            },
            "free_data_sources": [
                "Open-Meteo — real-time soil moisture (5 layers), temperature, ET₀, 16-day forecast (1km, free)",
                "Soil Health Card — soilhealth.dac.gov.in (NPK, pH, OC, micro-nutrients)",
                "NASA POWER — agro-climate data (fallback)",
            ],
            "crops_in_database": 80,
            "timestamp": datetime.now().isoformat(),
        })


# ── Helpers ────────────────────────────────────────────────────────────────

def _parse_sensor_floats(sensors: dict) -> dict:
    """Safely convert all sensor values to float, skip invalid."""
    clean = {}
    for k, v in sensors.items():
        if v is None:
            continue
        try:
            clean[k] = float(v)
        except (TypeError, ValueError):
            pass
    return clean

def _safe_float(val) -> Optional[float]:
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None

def _save_sensor_reading(ctx, sensors: dict, field_id=None):
    """Persist sensor reading to IoT sensor model if available."""
    try:
        from ...models import IoTSensorReading  # May not exist yet
        IoTSensorReading.objects.create(
            field_id=field_id or f"{round(ctx.latitude,4)}_{round(ctx.longitude,4)}",
            latitude=ctx.latitude,
            longitude=ctx.longitude,
            location_name=ctx.display_name,
            state=ctx.state or "",
            nitrogen_kg_ha=sensors.get("nitrogen_kg_ha"),
            phosphorus_kg_ha=sensors.get("phosphorus_kg_ha"),
            potassium_kg_ha=sensors.get("potassium_kg_ha"),
            ph=sensors.get("ph"),
            ec_ds_m=sensors.get("ec_ds_m"),
            moisture_pct=sensors.get("moisture_pct"),
            soil_temp_c=sensors.get("soil_temp_c"),
            organic_carbon=sensors.get("organic_carbon"),
        )
    except Exception:
        pass  # Model not yet created or migration pending

def _quick_soil_advice(soil_status: dict, lang: str) -> list:
    """Return immediate action items based on soil status."""
    advice = []
    advice_map = {
        "nitrogen": {
            "Low": {
                "hi": "🌱 नाइट्रोजन कम — यूरिया 50 किग्रा/एकड़ डालें",
                "en": "🌱 Low Nitrogen — apply 50 kg/acre Urea",
                "ta": "🌱 நைட்ரஜன் குறைவு — 50 கிலோ/ஏக்கர் யூரியா போடுங்கள்",
                "te": "🌱 నత్రజని తక్కువ — 50 కిలో/ఎకరా యూరియా వేయండి",
                "mr": "🌱 नत्र कमी — 50 किलो/एकर युरिया द्या",
                "gu": "🌱 નાઇટ્રોજન ઓછો — 50 કિ.ગ્રા./એકર યુરિયા નાખો",
                "kn": "🌱 ಸಾರಜನಕ ಕಡಿಮೆ — 50 ಕಿ.ಗ್ರಾ/ಎಕರೆ ಯೂರಿಯಾ ಹಾಕಿ",
                "ml": "🌱 നൈട്രജൻ കുറവ് — 50 കി.ഗ്രാം/ഏക്കർ യൂറിയ ഇടുക",
                "pa": "🌱 ਨਾਈਟ੍ਰੋਜਨ ਘੱਟ — 50 ਕਿਲੋ/ਏਕੜ ਯੂਰੀਆ ਪਾਓ",
                "bn": "🌱 নাইট্রোজেন কম — ৫০ কেজি/একর ইউরিয়া দিন",
            },
        },
        "phosphorus": {
            "Low": {
                "hi": "🔴 फास्फोरस कम — DAP 25 किग्रा/एकड़ बुवाई के समय",
                "en": "🔴 Low Phosphorus — apply 25 kg/acre DAP at sowing",
                "ta": "🔴 பாஸ்பரஸ் குறைவு — விதைப்பு நேரத்தில் 25 கிலோ DAP",
                "te": "🔴 భాస్వరం తక్కువ — 25 కిలో DAP విత్తు సమయంలో",
                "mr": "🔴 स्फुरद कमी — पेरणीच्यावेळी 25 किलो DAP",
                "gu": "🔴 ફોસ્ફરસ ઓછો — વાવણી વખતે 25 કિ.ગ્રા DAP",
                "pa": "🔴 ਫਾਸਫੋਰਸ ਘੱਟ — ਬਿਜਾਈ ਸਮੇਂ 25 ਕਿਲੋ DAP ਪਾਓ",
            },
        },
        "ph": {
            "Acidic": {
                "hi": "⚠️ मिट्टी अम्लीय — 2 क्विंटल/एकड़ चूना मिलाएं",
                "en": "⚠️ Acidic soil — apply 2 quintal/acre agricultural lime",
                "ta": "⚠️ அமில மண் — 2 குவிண்டால்/ஏக்கர் சுண்ணாம்பு",
                "te": "⚠️ ఆమ్ల నేల — 2 క్వింటాల్/ఎకరా సున్నం వేయండి",
            },
            "Alkaline": {
                "hi": "⚠️ मिट्टी क्षारीय — 3 क्विंटल/एकड़ जिप्सम डालें",
                "en": "⚠️ Alkaline soil — apply 3 quintal/acre gypsum",
            },
            "Highly Alkaline": {
                "hi": "🚨 अत्यधिक क्षारीय — 5 क्विंटल जिप्सम + सल्फर उपचार",
                "en": "🚨 Highly alkaline — apply 5 quintal gypsum + sulphur",
            },
        },
        "salinity": {
            "Marginal": {
                "hi": "⚠️ हल्की लवणता — नहर का पानी प्रयोग, जिप्सम उपचार",
                "en": "⚠️ Marginal salinity — use canal water, gypsum treatment",
            },
            "Saline": {
                "hi": "🚨 लवणीय मिट्टी — नमक-सहनशील फसलें (जौ, ज्वार) लगाएं",
                "en": "🚨 Saline soil — grow salt-tolerant crops (barley, jowar)",
            },
        },
        "organic_carbon": {
            "Low": {
                "hi": "🌿 जैव कार्बन कम — 2 टन/एकड़ वर्मीकम्पोस्ट डालें",
                "en": "🌿 Low organic carbon — apply 2 tonne/acre vermicompost",
                "ta": "🌿 கரிம கார்பன் குறைவு — 2 டன்/ஏக்கர் மண்புழு உரம்",
            },
        },
        "moisture": {
            "Very Dry": {
                "hi": "💧 मिट्टी बहुत सूखी — तुरंत सिंचाई करें",
                "en": "💧 Very dry soil — irrigate immediately",
                "ta": "💧 மண் மிகவும் வறண்டது — உடனே நீர்ப்பாசனம்",
                "te": "💧 చాలా పొడిగా ఉంది — వెంటనే నీరు పెట్టండి",
                "mr": "💧 माती खूप कोरडी — लगेच पाणी द्या",
                "gu": "💧 જમીન ખૂબ સૂકી — તત્કાળ સિંચાઈ",
                "pa": "💧 ਮਿੱਟੀ ਬਹੁਤ ਸੁੱਕੀ — ਤੁਰੰਤ ਸਿੰਚਾਈ ਕਰੋ",
            },
            "Waterlogged": {
                "hi": "🌊 जलभराव — जल निकासी की व्यवस्था करें तुरंत",
                "en": "🌊 Waterlogged — create drainage immediately",
                "ta": "🌊 நீர் தேக்கம் — உடனே வடிகால் அமையுங்கள்",
            },
        },
    }

    for nutrient, status_val in soil_status.items():
        translations = advice_map.get(nutrient, {}).get(status_val, {})
        if translations:
            msg = translations.get(lang) or translations.get("hi") or translations.get("en")
            if msg:
                advice.append({"nutrient": nutrient, "status": status_val, "action": msg})

    if not advice:
        ok_msgs = {
            "hi": "✅ मिट्टी की स्थिति सामान्य है",
            "en": "✅ Soil status is normal",
            "ta": "✅ மண் நிலை சாதாரணமாக உள்ளது",
            "te": "✅ నేల స్థితి సాధారణంగా ఉంది",
            "mr": "✅ माती स्थिती सामान्य आहे",
        }
        advice.append({"action": ok_msgs.get(lang, ok_msgs["en"])})

    return advice

from typing import Optional
