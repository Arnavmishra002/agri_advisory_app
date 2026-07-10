import re
import time
from unittest.mock import patch

from django.test import SimpleTestCase

from advisory.services.chat_intelligence_service import (
    INTENT_CROP_RECOMMENDATION,
    INTENT_FERTILIZER,
    INTENT_GOVERNMENT_SCHEME,
    INTENT_IRRIGATION,
    INTENT_MARKET_PRICE,
    INTENT_PEST_DISEASE,
    INTENT_WEATHER,
    ChatIntelligenceService,
)
from advisory.services.location_context import LocationContext


class ChatbotFarmerQualityTests(SimpleTestCase):
    def setUp(self):
        self.service = ChatIntelligenceService()
        self.ctx = LocationContext(
            latitude=28.6139,
            longitude=77.2090,
            display_name="Delhi",
            state="Delhi",
        )

    def test_multilingual_farmer_questions_classify_to_expected_service(self):
        cases = {
            "kal barish hogi kya": INTENT_WEATHER,
            "gehu ka mandi bhav kya hai": INTENT_MARKET_PRICE,
            "wheat leaves have rust disease": INTENT_PEST_DISEASE,
            "धान में खाद कब डालें": INTENT_FERTILIZER,
            "cotton ko pani kab dena hai": INTENT_IRRIGATION,
            "PM Kisan scheme eligibility": INTENT_GOVERNMENT_SCHEME,
            "meri location ke liye best crop": INTENT_CROP_RECOMMENDATION,
        }

        for query, expected in cases.items():
            with self.subTest(query=query):
                intent, _ = self.service.classify_query(query)
                self.assertEqual(intent, expected)

    def test_greetings_match_requested_language_and_latency_budget(self):
        started = time.monotonic()
        hindi = self.service.answer("नमस्ते", self.ctx, language="hi")
        elapsed_ms = (time.monotonic() - started) * 1000
        english = self.service.answer("hello", self.ctx, language="en")

        self.assertLess(elapsed_ms, 500)
        self.assertRegex(hindi["response"], r"[\u0900-\u097F]")
        self.assertNotRegex(english["response"], r"[\u0900-\u097F]")
        self.assertEqual(hindi["ai_data_quality"]["tier"], "instant_rule")

    @patch("advisory.services.chat_intelligence_service.market_service.get_prices")
    @patch("advisory.services.chat_intelligence_service.weather_service.get_weather")
    @patch("advisory.services.knowledge_base.knowledge_base.answer")
    def test_missing_live_mandi_data_is_not_presented_as_live_price(
        self,
        kb_answer,
        weather,
        market,
    ):
        kb_answer.return_value = {"answer": None}
        weather.return_value = {
            "status": "fallback",
            "is_live": False,
            "current": {},
            "data_source": "unavailable",
        }
        market.return_value = {
            "status": "unavailable",
            "is_live": False,
            "top_crops": [],
            "data_source": "unavailable",
        }

        result = self.service.answer(
            "What is wheat mandi price today?",
            self.ctx,
            language="en",
            fast_mode=True,
        )

        self.assertIn("Live mandi prices unavailable", result["response"])
        self.assertIn("unavailable", [source.lower() for source in result["sources"]])
        self.assertEqual(result["ai_data_quality"]["status"], "degraded")

    @patch("advisory.services.chat_intelligence_service.weather_service.get_weather")
    @patch("advisory.services.knowledge_base.knowledge_base.answer")
    def test_pesticide_dose_requires_an_icar_source(self, kb_answer, weather):
        kb_answer.return_value = {"answer": None}
        weather.return_value = {
            "status": "fallback",
            "is_live": False,
            "current": {},
            "data_source": "unavailable",
        }

        result = self.service.answer(
            "wheat rust pesticide dose?",
            self.ctx,
            language="en",
            fast_mode=True,
        )

        contains_dose = bool(re.search(r"\d+(?:\.\d+)?(?:%|ml/L|kg/ha)", result["response"]))
        if contains_dose:
            self.assertTrue(
                any("icar" in source.lower() for source in result["sources"]),
                result,
            )
