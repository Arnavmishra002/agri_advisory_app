import unittest
from unittest.mock import patch

try:
    from . import main
except ImportError:
    import main


class Phase1WeatherContextTests(unittest.TestCase):
    def test_uv_notice_is_not_injected_into_agronomy_prompt_context(self):
        weather_service = unittest.mock.Mock()
        weather_service.get_weather.return_value = {
            "current": {"temperature": 31, "condition": "clear", "humidity": 54},
            "farming_alerts": [
                "Extreme UV (10) - avoid midday fieldwork",
                "Heavy rain (55mm) - ensure drainage",
            ],
            "forecast_7day": [],
        }

        with patch.object(main, "_get_weather_service", return_value=weather_service):
            summary = main._get_weather_summary("Unnao", 26.5393, 80.4878, "en")

        self.assertNotIn("UV", summary)
        self.assertIn("Heavy rain", summary)


if __name__ == "__main__":
    unittest.main()
