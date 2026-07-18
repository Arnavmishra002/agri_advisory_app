from unittest.mock import patch
from datetime import datetime, timedelta

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from advisory.api.viewsets.field_advisory import FieldAdvisoryViewSet
from advisory.services.field_sensor_service import FieldSensorService


class FieldDataTruthfulnessTests(SimpleTestCase):
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
