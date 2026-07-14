from unittest.mock import patch

from django.test import SimpleTestCase

from advisory.services.unified_realtime_service import WeatherService


class WeatherLocationIntegrityTests(SimpleTestCase):
    def test_failed_geocoding_never_substitutes_delhi(self):
        service = WeatherService()

        with patch.object(service.session, "get", side_effect=TimeoutError("offline")):
            result = service.get_weather("Unknown Farmer Village")

        self.assertEqual(result["status"], "unavailable")
        self.assertFalse(result["is_live"])
        self.assertEqual(result["location"], "Unknown Farmer Village")
        self.assertNotIn("latitude", result)
        self.assertNotIn("longitude", result)
        self.assertEqual(result["provider"], "unavailable")
        self.assertEqual(result["freshness"], "unavailable")
        self.assertTrue(result["is_stale"])
        self.assertIsNone(result["observation_time"])

    def test_live_open_meteo_response_has_freshness_metadata(self):
        service = WeatherService()
        payload = {
            "current": {
                "time": "2026-07-14T09:15",
                "temperature_2m": 31.2,
                "relative_humidity_2m": 68,
                "apparent_temperature": 34.0,
                "precipitation": 0,
                "weather_code": 1,
                "wind_speed_10m": 8.0,
                "wind_direction_10m": 220,
                "uv_index": 4.0,
                "surface_pressure": 995,
            },
            "daily": {"time": []},
        }

        class Response:
            status_code = 200

            @staticmethod
            def json():
                return payload

        with patch.object(service.session, "get", return_value=Response()):
            result = service.get_weather("Raebareli", 26.23, 81.24)

        self.assertEqual(result["provider"], "open-meteo")
        self.assertEqual(result["observation_time"], "2026-07-14T09:15")
        self.assertEqual(result["freshness"], "live")
        self.assertFalse(result["is_stale"])
