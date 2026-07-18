import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from advisory.api.monitoring_views import data_freshness
from advisory.services.crop_recommendation_engine import (
    CROP_REC_HEALTH_CACHE_KEY,
    CropRecommendationEngine,
)
import advisory.services.crop_recommendation_engine as crop_engine


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

        top_breakdown = result["recommendations"][0]["prediction_data"]["score_breakdown"]
        self.assertEqual(top_breakdown["temperature"]["status"], "unavailable")
        self.assertEqual(top_breakdown["temperature"]["points"], 0)
        self.assertEqual(top_breakdown["weather"]["status"], "unavailable")
        self.assertEqual(top_breakdown["weather"]["points"], 0)

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

    def test_dated_official_market_row_is_not_described_as_live(self):
        engine = CropRecommendationEngine()
        market = {
            "status": "success",
            "is_live": True,
            "data_source": "Agmarknet official",
            "top_crops": [
                {
                    "crop_name": "Maize",
                    "modal_price": 2100,
                    "msp": 2410,
                    "is_live": True,
                    "reported_date": "16-07-2026",
                    "data_age_minutes": 3000,
                }
            ],
        }
        engine._fetch_realtime_context = lambda *args: (
            {
                "status": "success",
                "is_live": True,
                "data_source": "Open-Meteo",
                "current": {"temperature": 28, "humidity": 60},
                "forecast_7day": [{"rainfall_mm": 5, "max_temp": 31}] * 7,
            },
            market,
            {"weather": "live", "market": "live"},
        )

        result = engine.recommend(
            "Varanasi",
            25.3176,
            82.9739,
            state="Uttar Pradesh",
            language="en",
            agronomic_inputs={"season": "kharif", "target_crop": "maize"},
        )

        crop = result["recommendations"][0]
        self.assertEqual(result["market_freshness"], "dated_official")
        self.assertEqual(result["market_reported_date"], "16-07-2026")
        self.assertIn("official report dated 16-07-2026", result["data_source"])
        self.assertNotIn("live mandi", result["data_source"].lower())
        self.assertEqual(crop["market_price_reported_date"], "16-07-2026")
        self.assertEqual(crop["economics_basis"], "official_mandi_modal_price")

    def test_slow_realtime_sources_return_within_caller_budget(self):
        pool = ThreadPoolExecutor(max_workers=2)

        def slow_source(*args, **kwargs):
            time.sleep(0.2)
            return {}

        try:
            with patch.object(crop_engine, "_REC_FETCH_POOL", pool), patch.dict(
                os.environ, {"CROP_REC_REALTIME_TIMEOUT_S": "0.01"}
            ), patch.object(crop_engine.weather_service, "get_weather", side_effect=slow_source), patch.object(
                crop_engine.market_service, "get_prices", side_effect=slow_source
            ):
                started = time.monotonic()
                _, _, status = CropRecommendationEngine()._fetch_realtime_context(
                    "Lucknow", 26.8467, 80.9462, "Uttar Pradesh", "en"
                )
                elapsed = time.monotonic() - started

            self.assertLess(elapsed, 0.15)
            self.assertEqual(status, {"weather": "timeout", "market": "timeout"})
        finally:
            pool.shutdown(wait=True)
