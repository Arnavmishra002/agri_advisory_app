from unittest.mock import patch
from datetime import datetime, timedelta

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from advisory.api.viewsets.field_advisory import FieldAdvisoryViewSet
from advisory.services.field_sensor_service import FieldSensorService


class FieldDataTruthfulnessTests(SimpleTestCase):
    def _live_open_meteo_payload(self):
        return {
            "status": "success",
            "is_live": True,
            "soil_layers": {"moisture_surface_pct": 33.7},
            "current": {"temperature": 29},
            "forecast": [
                {
                    "date": f"2026-07-{day:02d}",
                    "rainfall_mm": 10,
                    "max_temp": 31,
                    "et0_mm": 3,
                    "rain_probability": 20,
                }
                for day in range(18, 25)
            ],
        }

    def test_two_day_old_field_weather_cache_is_not_treated_as_fresh(self):
        service = FieldSensorService()
        key = "26.847:80.946"
        service._weather_cache[key] = {
            "status": "success",
            "is_live": True,
            "_fetched_at": datetime.now() - timedelta(days=2),
        }

        with patch.object(service.session, "get", side_effect=TimeoutError("offline")) as fetch:
            result = service._fetch_open_meteo_soil_weather(26.8467, 80.9462)

        fetch.assert_called_once()
        self.assertEqual(result["status"], "unavailable")

    def test_open_meteo_failure_is_explicitly_unavailable(self):
        data = FieldSensorService()._open_meteo_fallback(26.8467, 80.9462)

        self.assertEqual(data["status"], "unavailable")
        self.assertFalse(data["is_live"])
        self.assertTrue(data["is_stale"])

    def test_satellite_only_advisory_does_not_claim_iot_sensor(self):
        service = FieldSensorService()
        top = [{
            "crop_name": "Maize",
            "crop_name_hindi": "मक्का",
            "suitability_score": 70,
        }]
        context_without_readings = {
            "sensors": {},
            "previous_crop": "rice",
            "irrigation_type": "drip",
        }
        with patch.object(
            service, "_fetch_open_meteo_soil_weather", return_value=self._live_open_meteo_payload()
        ), patch.object(
            service, "_fetch_soil_health_card", return_value={"is_live": False, "source": "No government soil data available"}
        ), patch.object(service, "_score_crops_field_level", return_value=top), patch.object(
            service, "_calculate_input_gaps", return_value=[]
        ):
            result = service.get_field_recommendation(
                25.3176,
                82.9739,
                sensor_data=context_without_readings,
                location_name="Varanasi",
                state="Uttar Pradesh",
                language="en",
            )

        self.assertFalse(result["iot_sensors_used"])
        self.assertNotIn("sensor", result["grid_resolution"].lower())
        self.assertFalse(any("IoT Field Sensor" in source for source in result["data_sources"]))
        self.assertEqual(result["sensor_quality"]["quality"], "None")
        self.assertEqual(result["weather"]["rain_7d_mm"], 70)
        self.assertEqual(result["weather"]["avg_max_temp_7d"], 31)
        self.assertEqual(result["weather"]["total_et0_7d_mm"], 21)
        self.assertNotIn("**", result["summary"])

    def test_nasa_annual_climate_reference_is_not_labeled_live_or_nutrient_data(self):
        service = FieldSensorService()

        class Response:
            status_code = 200

            @staticmethod
            def json():
                return {
                    "properties": {
                        "parameter": {"PRECTOTCORR": {"202501": 2.0, "202502": 3.0}}
                    }
                }

        with patch.object(service.session, "get", return_value=Response()):
            data = service._fetch_nasa_power_fallback(26.8467, 80.9462)

        self.assertFalse(data["is_live"])
        self.assertEqual(data["data_quality"], "historical_climate_reference")
        self.assertIn("does not provide soil nutrient", data["note"])

    @patch("advisory.api.viewsets.field_advisory.field_sensor_service._fetch_open_meteo_soil_weather")
    def test_field_weather_endpoint_never_claims_live_when_provider_failed(self, fetch):
        fetch.return_value = FieldSensorService()._open_meteo_fallback(26.8467, 80.9462)
        request = APIRequestFactory().get(
            "/api/field-advisory/weather_analysis/",
            {"latitude": 26.8467, "longitude": 80.9462},
        )

        response = FieldAdvisoryViewSet.as_view({"get": "weather_analysis"})(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "unavailable")
        self.assertFalse(response.data["is_live"])
        self.assertNotIn("real-time", response.data["data_source"].lower())
