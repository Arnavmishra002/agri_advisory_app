from unittest.mock import patch

from django.test import SimpleTestCase

from advisory.services.crop_recommendation_engine import CropRecommendationEngine


class RecommendationWeatherEvidenceTests(SimpleTestCase):
    def test_partial_or_missing_values_cannot_prove_favorable_weather(self):
        engine = CropRecommendationEngine()
        for forecast in (
            [{"rainfall_mm": 1, "max_temp": 25}],
            [{"rainfall_mm": None, "max_temp": 25}] * 7,
            [{"rainfall_mm": 1, "max_temp": float("nan")}] * 7,
        ):
            with self.subTest(forecast=forecast):
                self.assertEqual(engine._assess_weather_risk(forecast, {})["risk"], "Unavailable")

    def test_valid_zero_temperature_is_not_replaced_by_warm_default(self):
        result = CropRecommendationEngine()._assess_weather_risk(
            [{"rainfall_mm": 0, "max_temp": 0}] * 7, {},
        )
        self.assertEqual(result["risk"], "Cold")

    def test_standard_provider_forecast_reaches_scoring(self):
        engine = CropRecommendationEngine()
        forecast = [{"rainfall_mm": 25, "max_temp": 30}] * 7
        weather = {"is_live": True, "current": {"temperature": 29}, "forecast": forecast}
        with patch.object(engine, "_fetch_realtime_context", return_value=(weather, {}, {})), \
                patch.object(engine, "_score_all_crops", return_value=[]) as score:
            engine.recommend("Lucknow", 26.85, 80.95, state="Uttar Pradesh")
        self.assertEqual(score.call_args.args[3], forecast)

    def test_each_request_fetches_the_selected_farmer_coordinates(self):
        engine = CropRecommendationEngine()
        with patch.object(engine, "_fetch_realtime_context", return_value=({}, {}, {})) as fetch, \
                patch.object(engine, "_score_all_crops", return_value=[]):
            engine.recommend("Lucknow", 26.85, 80.95, state="Uttar Pradesh", language="en")
            engine.recommend("Mumbai", 19.08, 72.88, state="Maharashtra", language="hi")
        self.assertEqual(fetch.call_args_list[0].args, ("Lucknow", 26.85, 80.95, "Uttar Pradesh", "en"))
        self.assertEqual(fetch.call_args_list[1].args, ("Mumbai", 19.08, 72.88, "Maharashtra", "hi"))
