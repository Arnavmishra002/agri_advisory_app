from django.test import SimpleTestCase

from advisory.services.chat_intelligence_service import ChatIntelligenceService, INTENT_ORGANIC
from advisory.services.location_context import LocationContext


class OrganicFallbackSafetyTests(SimpleTestCase):
    def test_comparison_has_sources_without_unsourced_doses_or_returns(self):
        service = ChatIntelligenceService()
        for language in ("en", "hi", "hinglish"):
            with self.subTest(language=language):
                answer = service._smart_rule_response(
                    "Compare compost and vermicompost; no fertilizer dose.",
                    INTENT_ORGANIC, [], LocationContext(None, None, "Location not confirmed"), "", language,
                )
                self.assertIn("https://www.fao.org/", answer)
                self.assertNotRegex(answer, r"\d\s*(?:ml/L|kg/ha|t/ha)|20-50%|2000-3000")
                self.assertNotIn("Neem oil", answer)
                self.assertIn("1.", answer)
                self.assertIn("3.", answer)

    def test_general_advice_does_not_invent_savings_or_application_rates(self):
        answer = ChatIntelligenceService()._smart_rule_response(
            "How do I start organic farming?", INTENT_ORGANIC, [],
            LocationContext(None, None, "Location not confirmed"), "", "en",
        )
        self.assertNotRegex(answer, r"\d\s*(?:ml/L|kg/ha|t/ha)|20-50%|2000-3000")
        self.assertNotIn("3-year", answer)
