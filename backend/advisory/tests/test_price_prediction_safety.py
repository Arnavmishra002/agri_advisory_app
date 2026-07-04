from django.test import SimpleTestCase

from advisory.services.comprehensive_crop_recommendations import ComprehensiveCropRecommendations


class LegacyPricePredictionSafetyTests(SimpleTestCase):
    def setUp(self):
        self.service = ComprehensiveCropRecommendations()

    def test_future_price_forecast_is_disabled_without_backtested_model(self):
        result = self.service._predict_future_price("wheat", {})

        self.assertEqual(result["status"], "unvalidated")
        self.assertFalse(result["forecast_available"])
        self.assertIsNone(result["next_3_months"])
        self.assertIsNone(result["next_6_months"])
        self.assertIsNone(result["next_year"])
        self.assertEqual(result["confidence"], "Unavailable")
        self.assertIn("no backtested", result["data_source"].lower())

    def test_yield_and_profit_helpers_do_not_return_random_predictions(self):
        yield_result = self.service._predict_next_season_yield("wheat", {})
        profit_result = self.service._predict_next_season_profit("wheat", {})

        self.assertEqual(yield_result["status"], "unvalidated")
        self.assertIsNone(yield_result["predicted_yield"])
        self.assertEqual(yield_result["confidence"], "Unavailable")

        self.assertEqual(profit_result["status"], "unvalidated")
        self.assertIsNone(profit_result["predicted_profit"])
        self.assertEqual(profit_result["confidence"], "Unavailable")

    def test_crop_recommendations_expose_msp_reference_not_price_prediction(self):
        response = self.service.get_crop_recommendations(
            "Lucknow",
            soil_type="loamy",
            season="rabi",
        )

        self.assertTrue(response["recommendations"])
        for crop in response["recommendations"]:
            self.assertIsNone(crop["market_price_prediction"])
            self.assertEqual(crop["market_price_prediction_status"], "unvalidated")
            self.assertIn("msp_reference", crop)
