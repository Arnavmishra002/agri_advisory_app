import json

from django.core.cache import cache
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from advisory.api.monitoring_views import data_freshness
from advisory.services.crop_recommendation_engine import (
    CROP_REC_HEALTH_CACHE_KEY,
    CropRecommendationEngine,
)


class CropRecommendationRealtimeTests(SimpleTestCase):
    def setUp(self):
        cache.delete(CROP_REC_HEALTH_CACHE_KEY)

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
        self.assertEqual(result["data_quality_status"], "degraded")
        self.assertIn("weather", result["data_quality"]["sources"])
        self.assertIn("market", result["data_quality"]["sources"])
        self.assertGreaterEqual(len(result["data_quality"]["alerts"]), 2)
        self.assertNotIn("Agmarknet", result["data_source"])
        self.assertNotIn("Live mandi modal prices vs MSP", result["factors_analyzed"])

        cached_health = cache.get(CROP_REC_HEALTH_CACHE_KEY)
        self.assertIsNotNone(cached_health)
        self.assertEqual(cached_health["location"], "Lucknow")
        self.assertEqual(cached_health["status"], "degraded")

        self.assertGreater(len(result["recommendations"]), 0)
        for rec in result["recommendations"]:
            self.assertIsNone(rec["market_price"])
            self.assertFalse(rec["market_is_live"])
            self.assertEqual(rec["market_price_status"], "unavailable")
            self.assertEqual(rec["market_price_source"], "not_available")
            self.assertEqual(rec["financials"]["market_price"], "Unavailable")

    def test_data_freshness_endpoint_exposes_crop_recommendation_health(self):
        cache.set(
            CROP_REC_HEALTH_CACHE_KEY,
            {
                "status": "degraded",
                "location": "Lucknow",
                "alerts": ["market unavailable"],
            },
            timeout=60,
        )

        response = data_freshness(APIRequestFactory().get("/api/health/data-freshness/"))
        payload = json.loads(response.content.decode("utf-8"))

        self.assertEqual(payload["crop_recommendation"]["status"], "degraded")
        self.assertEqual(payload["crop_recommendation"]["location"], "Lucknow")
