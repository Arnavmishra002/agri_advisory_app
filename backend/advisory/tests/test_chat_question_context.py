from unittest.mock import patch

from django.test import SimpleTestCase

from advisory.services.chat_intelligence_service import ChatIntelligenceService, INTENT_FERTILIZER
from advisory.services.location_context import LocationContext


class ChatQuestionContextTests(SimpleTestCase):
    def setUp(self):
        self.service = ChatIntelligenceService()
        self.ctx = LocationContext(latitude=None, longitude=None, display_name="Location not confirmed")

    def test_plural_crop_entities_and_explicit_correction(self):
        for query, expected in [
            ("I grow tomatoes", ["tomato"]),
            ("potatoes and onions", ["potato", "onion"]),
            ("tomato, not wheat", ["tomato"]),
            ("not only wheat but rice", ["wheat", "rice"]),
        ]:
            with self.subTest(query=query):
                self.assertEqual([c["id"] for c in self.service._detect_crops(query)], expected)

    def test_assistant_examples_do_not_become_farmer_crop(self):
        result = self.service.answer(
            "The leaves are yellow. What should I check?", self.ctx,
            language="en", fast_mode=True,
            history=[{"role": "user", "content": "I grow tomatoes"},
                     {"role": "assistant", "content": "For example, wheat leaves can turn yellow."}],
        )
        self.assertEqual(result["crops_detected"], ["Tomato"])
        self.assertNotIn("Wheat", result["response"])

    @patch("advisory.services.chat_intelligence_service.schemes_service.get_schemes")
    def test_applying_fertilizer_does_not_add_scheme_source(self, schemes):
        _, sources = self.service._build_official_context(
            self.ctx, "What should I check before applying fertilizer?",
            INTENT_FERTILIZER, [], "en", _weather={},
        )
        schemes.assert_not_called()
        self.assertNotIn("Government schemes (MoAFW)", sources)

    def test_pre_fertilizer_question_does_not_return_a_dose_schedule(self):
        result = self.service.answer(
            "What should I check before applying fertilizer to tomato?",
            self.ctx, language="en", fast_mode=True,
        )
        self.assertIn("Before adding fertilizer", result["response"])
        self.assertIn("soil test", result["response"].lower())
        self.assertNotIn("kg/ha", result["response"])

    def test_stream_preserves_the_reported_leaf_pattern(self):
        chunks = list(self.service.answer_stream(
            "I grow tomatoes. Older leaves are yellow but new leaves are green. "
            "What should I check before adding fertilizer?", self.ctx, language="en",
        ))
        text = "".join(item for item in chunks if isinstance(item, str))
        self.assertIn("Tomato", text)
        self.assertIn("yellow older leaves", text)
        self.assertNotIn("kg/ha", text)
