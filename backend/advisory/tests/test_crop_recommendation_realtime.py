from django.test import SimpleTestCase

from advisory.services.crop_recommendation_engine import CropRecommendationEngine


class CropRecommendationRealtimeTests(SimpleTestCase):
    def test_unavailable_market_does_not_emit_synthetic_mandi_price(self):
        engine = CropRecommendationEngine()

        def fake_realtime(location, latitude, longitude, state, language):
            return (
                {
                    "status": "unavailable",
                    "is_live": False,
                    "current": {},
                    "forecast_7day": [],
                    "data_source": "not fetched",
                },
                {
                    "status": "unavailable",
                    "is_live": False,
                    "top_crops": [],
                    "data_source": "not fetched",
                },
                {"weather": "timeout", "market": "timeout"},
            )

        engine._fetch_realtime_context = fake_realtime

        result = engine.recommend(
            "Lucknow",
            26.8467,
            80.9462,
            state="Uttar Pradesh",
            language="en",
        )

        self.assertFalse(result["market_is_live"])
        self.assertNotIn("Agmarknet", result["data_source"])
        self.assertNotIn("Live mandi modal prices vs MSP", result["factors_analyzed"])

        self.assertGreater(len(result["recommendations"]), 0)
        for rec in result["recommendations"]:
            self.assertIsNone(rec["market_price"])
            self.assertFalse(rec["market_is_live"])
            self.assertEqual(rec["market_price_status"], "unavailable")
            self.assertEqual(rec["market_price_source"], "not_available")
            self.assertEqual(rec["financials"]["market_price"], "Unavailable")
