"""Generated doses are released only when the request's evidence contains them.

The earlier filter matched only "g/L"-style doses and accepted any dose next to
a citation, so "2 ml per litre", Hindi doses and invented "ICAR document no."
citations all got through. These tests pin the evidence-matched guard and the
streaming path, which previously sent local-model tokens with no guard at all.
"""
import json
from unittest.mock import patch

from django.test import SimpleTestCase

from advisory.services.chat_intelligence_service import (
    ChatIntelligenceService,
    _extract_dose_claims,
    _safe_model_text,
)
from advisory.services.location_context import LocationContext


class DoseExtractionTests(SimpleTestCase):
    def test_extracts_doses_written_in_english_hindi_and_hinglish(self):
        for text in (
            "Spray 2 ml per litre of water.",
            "Use 200 ml per acre.",
            "Apply 1 kg/acre.",
            "Treat seed with 2 g/kg seed.",
            "2 मिली प्रति लीटर पानी में मिलाएं।",
            "२ मिली प्रति लीटर पानी",
            "2 ml ek litre pani me milao",
            "Use 3 grams of copper oxychloride in each litre",
            "Mancozeb 75% WP",
            "0.2% solution ka spray karein",
        ):
            self.assertTrue(_extract_dose_claims(text), text)

    def test_ignores_weather_and_market_numbers(self):
        for text in (
            "Humidity is 80% and rain probability is 70%.",
            "Expect 25 mm of rain tomorrow.",
            "Wheat yield is about 20 quintal per acre.",
            "Temperature 32 °C.",
        ):
            self.assertFalse(_extract_dose_claims(text), text)

    def test_hindi_and_english_forms_of_the_same_dose_match(self):
        self.assertEqual(
            _extract_dose_claims("2 ml per litre"),
            _extract_dose_claims("२ मिली प्रति लीटर"),
        )


class EvidenceGuardTests(SimpleTestCase):
    def test_dose_absent_from_evidence_is_rejected_even_with_a_citation(self):
        text = "Spray imidacloprid 0.5 ml per litre (ICAR document no. 42)."
        self.assertIsNone(_safe_model_text(text, "general", "en", evidence="Keep the field clean."))

    def test_dose_present_in_evidence_is_accepted(self):
        evidence = "Package of practices: imidacloprid 0.5 ml per litre of water."
        text = "As advised, spray imidacloprid 0.5 ml/litre in the evening."
        self.assertEqual(_safe_model_text(text, "general", "en", evidence=evidence), text)

    def test_question_is_not_evidence(self):
        # The caller passes only grounded material; with none, any dose is refused.
        self.assertIsNone(_safe_model_text("Yes, use 5 ml per litre.", "general", "en"))

    def test_answer_without_doses_is_unaffected(self):
        text = "Inspect several plants and confirm with your KVK before spraying."
        self.assertEqual(_safe_model_text(text, "general", "en"), text)


class _FakeStream:
    def __init__(self, tokens):
        self.tokens = tokens

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        return None

    def iter_lines(self, **kwargs):
        frames = [json.dumps({"token": t}).encode() for t in self.tokens]
        return iter(frames + [json.dumps({"done": True}).encode()])


class StreamGuardTests(SimpleTestCase):
    def setUp(self):
        self.service = ChatIntelligenceService()
        self.ctx = LocationContext(
            latitude=26.8467, longitude=80.9462, display_name="Lucknow", state="Uttar Pradesh",
        )

    @patch("advisory.services.knowledge_base.knowledge_base.answer",
           return_value={"answer": None, "source": "escalate_to_gemini", "confidence": "low"})
    @patch("advisory.services.chat_intelligence_service.requests.post")
    def test_streamed_unsupported_dose_never_reaches_the_farmer(self, post, _kb):
        post.return_value = _FakeStream(["For seed treatment ", "use 4 ml per kg seed ", "of imidacloprid."])

        chunks = list(self.service.answer_stream("gehu me seed treatment kaise kare", self.ctx, language="en"))

        text = "".join(c for c in chunks if isinstance(c, str))
        self.assertNotIn("4 ml per kg seed", text)
        self.assertEqual(chunks[-1]["chatbot_diagnostics"]["selected_tier"], "rule_based_fallback")

    @patch("advisory.services.knowledge_base.knowledge_base.answer",
           return_value={"answer": None, "source": "escalate_to_gemini", "confidence": "low"})
    @patch("advisory.services.chat_intelligence_service.requests.post")
    def test_streamed_clean_answer_is_delivered(self, post, _kb):
        post.return_value = _FakeStream(["Rotate crops ", "and keep the field clean."])

        chunks = list(self.service.answer_stream("rice crop management advice", self.ctx, language="en"))

        text = "".join(c for c in chunks if isinstance(c, str))
        self.assertEqual(text, "Rotate crops and keep the field clean.")
        self.assertEqual(chunks[-1]["data_source"], "KrishiMitra local RAG (stream)")


class StreamDeliveryTests(SimpleTestCase):
    """Buffering for the guard must not time clients out, leak the local-AI
    slot when a client disconnects, or reject verified MSP figures."""

    def setUp(self):
        self.service = ChatIntelligenceService()
        self.ctx = LocationContext(
            latitude=26.8467, longitude=80.9462, display_name="Lucknow", state="Uttar Pradesh",
        )

    @patch("advisory.services.chat_intelligence_service._STREAM_HEARTBEAT_S", 0.0)
    @patch("advisory.services.knowledge_base.knowledge_base.answer",
           return_value={"answer": None, "source": "escalate_to_gemini", "confidence": "low"})
    @patch("advisory.services.chat_intelligence_service.requests.post")
    def test_heartbeats_are_sent_while_the_answer_is_buffered(self, post, _kb):
        post.return_value = _FakeStream(["Rotate crops ", "and keep the field clean."])

        chunks = list(self.service.answer_stream("rice crop management advice", self.ctx, language="en"))

        self.assertTrue(any(isinstance(c, dict) and c.get("__heartbeat__") for c in chunks))
        text = "".join(c for c in chunks if isinstance(c, str))
        self.assertEqual(text, "Rotate crops and keep the field clean.")

    @patch("advisory.services.chat_intelligence_service._STREAM_HEARTBEAT_S", 0.0)
    @patch("advisory.services.knowledge_base.knowledge_base.answer",
           return_value={"answer": None, "source": "escalate_to_gemini", "confidence": "low"})
    @patch("advisory.services.chat_intelligence_service.requests.post")
    def test_client_disconnect_releases_the_local_ai_slot(self, post, _kb):
        from advisory.services import chat_intelligence_service as chat_module

        post.return_value = _FakeStream(["Rotate crops ", "and keep the field clean."])
        stream = self.service.answer_stream("rice crop management advice", self.ctx, language="en")
        for chunk in stream:
            if isinstance(chunk, dict) and chunk.get("__heartbeat__"):
                break
        stream.close()  # what Django does when the client goes away

        self.assertTrue(chat_module._acquire_local_ai_slot())
        chat_module._release_local_ai_slot()

    @patch("advisory.services.knowledge_base.knowledge_base.answer",
           return_value={"answer": "Wheat MSP for 2025-26 is ₹2,425 per quintal.",
                         "source": "knowledge_base", "confidence": "high"})
    @patch("advisory.services.chat_intelligence_service.requests.post")
    def test_msp_figure_from_the_evidence_is_delivered(self, post, _kb):
        post.return_value = _FakeStream(["The MSP of wheat ", "is ₹2,425 per quintal."])

        chunks = list(self.service.answer_stream("what is the msp of wheat", self.ctx, language="en"))

        text = "".join(c for c in chunks if isinstance(c, str))
        self.assertIn("₹2,425 per quintal", text)
        self.assertEqual(chunks[-1]["data_source"], "KrishiMitra local RAG (stream)")

    @patch("advisory.services.knowledge_base.knowledge_base.answer",
           return_value={"answer": "Wheat MSP for 2025-26 is ₹2,425 per quintal.",
                         "source": "knowledge_base", "confidence": "high"})
    @patch("advisory.services.chat_intelligence_service.requests.post")
    def test_msp_figure_absent_from_the_evidence_is_rejected(self, post, _kb):
        post.return_value = _FakeStream(["The MSP of wheat ", "is ₹2,900 per quintal."])

        chunks = list(self.service.answer_stream("what is the msp of wheat", self.ctx, language="en"))

        text = "".join(c for c in chunks if isinstance(c, str))
        self.assertNotIn("2,900", text)


class DoseGuardReviewCasesTests(SimpleTestCase):
    """Exact strings from the review of the first extractor."""

    def _rejected(self, answer, evidence=""):
        return _safe_model_text(answer, "general", "", evidence=evidence) is None

    def test_doses_written_base_first_or_with_other_units_are_caught(self):
        for answer in (
            "प्रति एकड़ 50 किलो यूरिया डालें।",
            "एक एकड़ में 50 किलो यूरिया डालें।",
            "प्रति लीटर पानी में 5 मिली इमिडाक्लोप्रिड मिलाएं।",
            "एक बीघा में 20 किलो डीएपी डालें।",
            "Ek acre me 60 kg DAP daalo.",
            "Per acre 50 kg urea dalein.",
            "Ek litre pani me 2 ml dawa milao.",
            "Spray 3 ml/lit of chlorpyriphos.",
            "Spray 3 ml/lt.",
            "Mix 2 cc per litre.",
            "Spray two ml per litre.",
            "Do ml prati litre pani.",
            "दवा 2 मिलीलीटर प्रति लीटर पानी में घोलें।",
            "दो मिली प्रति लीटर पानी में मिलाएं।",
            "2 मिलि प्रति लीटर पानी",
            "2 एम.एल. प्रति लीटर पानी",
            "Apply 2 quintal gypsum per acre.",
            "Give a 2% urea spray.",
        ):
            self.assertTrue(self._rejected(answer), answer)

    def test_same_number_with_a_different_base_or_magnitude_is_rejected(self):
        for answer, evidence in (
            ("Apply 120 kg urea per bigha in two splits.", "Nitrogen (N): 120 kg/ha"),
            ("Apply 25 kg zinc sulphate per guntha.", "Zinc sulphate 25 kg/ha"),
            ("Mix 200 ml per litre of water for one acre.", "Imidacloprid 200 ml per acre"),
            ("Mix 100 ml in each litre of water. Spray one acre.", "Use 100 ml per acre."),
            ("Apply 2,500 kg gypsum per ha.", "जिप्सम 500kg/ha"),
            ("Apply 1,250 ml per hectare.", "Apply 250 ml per hectare."),
            ("Spray 5 ml per litre.", "Spray .5 ml per litre."),
            ("Use 2 litre per acre.", "Use 1/2 litre per acre."),
        ):
            self.assertTrue(self._rejected(answer, evidence), answer)

    def test_water_soil_yield_weather_and_prices_are_not_doses(self):
        for answer in (
            "Give each mango plant about 40 litres of water per week through drip.",
            "हर पौधे को रोज़ 4 लीटर पानी ड्रिप से दें।",
            "Keep 1 litre of water ready.",
            "Collect about 500 g of soil from 8-10 spots and mix well.",
            "Wheat yield is about 20 quintal per acre.",
            "Wheat gives an average of 20 quintal per acre.",
            "Humidity is 80% and rain probability is 70%.",
            "Expect 25 mm of rain tomorrow.",
            "The mandi price is ₹2,300 per quintal.",
            "Call Kisan Call Centre on 1800-180-1551.",
        ):
            self.assertFalse(self._rejected(answer), answer)
            self.assertFalse(_extract_dose_claims(answer), answer)

    def test_restatements_of_knowledge_base_notation_are_accepted(self):
        for answer, evidence in (
            ("Spray Imidacloprid 17.8% SL at 0.5 ml per litre of water.",
             "माहू — Imidacloprid 17.8SL (0.5ml/L)"),
            ("Spray Mancozeb 75% WP at 2 g per litre.", "Mancozeb 75WP (2g/L)"),
            ("Treat seed with Carboxin 75WP at 2 g per kg of seed.", "Carboxin 75WP (2g/kg)"),
            ("Use 1 to 2 ml per litre.", "Imidacloprid 1-2 ml/L"),
            ("प्रति लीटर पानी में 2 मिली मिलाएं।", "2 ml per litre"),
        ):
            self.assertFalse(self._rejected(answer, evidence), (answer, _extract_dose_claims(answer),
                                                                _extract_dose_claims(evidence)))


class DoseBindingTests(SimpleTestCase):
    """A dose must match the evidence for the same product and the same rate."""

    def _rejected(self, answer, evidence):
        return _safe_model_text(answer, "general", "", evidence=evidence) is None

    def test_another_products_dose_does_not_vouch_for_this_one(self):
        evidence = "Neem oil 5 ml per litre for aphids; imidacloprid 17.8% SL 0.3 ml per litre if severe."
        self.assertTrue(self._rejected("Spray imidacloprid 17.8% SL at 5 ml per litre.", evidence))
        self.assertFalse(self._rejected("Spray neem oil at 5 ml per litre.", evidence))
        self.assertFalse(self._rejected("If severe, spray imidacloprid at 0.3 ml per litre.", evidence))

    def test_base_amount_is_part_of_the_rate(self):
        evidence = "Mancozeb 75% WP: 25 g per 10 litre water."
        self.assertTrue(self._rejected("Spray mancozeb at 25 g per litre.", evidence))
        self.assertFalse(self._rejected("Spray mancozeb at 2.5 g per litre.", evidence))
        self.assertFalse(self._rejected("प्रति 10 लीटर पानी में 25 ग्राम मैंकोजेब मिलाएं।", "25 g per 10 litre"))


class GuardStopsCascadeTests(SimpleTestCase):
    """One rejected answer must not trigger every other model tier and narration."""

    @patch("advisory.services.chat_intelligence_service.weather_service.get_weather",
           return_value={"status": "unavailable", "is_live": False, "current": {}, "forecast_7day": []})
    @patch("advisory.services.chat_intelligence_service.ChatIntelligenceService._qwen_rag_answer")
    @patch("advisory.services.chat_intelligence_service._is_valid_open_llm_key", return_value=True)
    @patch("advisory.services.chat_intelligence_service._is_valid_gemini_key", return_value=True)
    @patch("advisory.services.chat_intelligence_service._is_valid_anthropic_key", return_value=True)
    @patch("advisory.services.chat_intelligence_service.open_llm_service")
    @patch("advisory.services.chat_intelligence_service.gemini_service")
    @patch("advisory.services.chat_intelligence_service.claude_service")
    def test_dose_rejection_goes_straight_to_the_rule_answer(
        self, claude, gemini, open_llm, _k1, _k2, _k3, qwen, _weather,
    ):
        unsupported = "For wheat, apply urea 50 kg per acre in three equal splits."
        for service in (claude, gemini, open_llm):
            service.generate.return_value = unsupported
            service.api_key = "configured"
        qwen.return_value = unsupported
        ctx = LocationContext(latitude=26.8467, longitude=80.9462, display_name="Lucknow",
                              state="Uttar Pradesh")

        result = ChatIntelligenceService().answer("how much urea should I apply to wheat", ctx, language="en")

        self.assertEqual(claude.generate.call_count, 1)
        gemini.generate.assert_not_called()
        open_llm.generate.assert_not_called()
        qwen.assert_not_called()
        self.assertNotIn("50 kg per acre", result["response"])
