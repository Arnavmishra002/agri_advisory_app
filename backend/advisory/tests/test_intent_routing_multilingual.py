"""Farmer questions must reach the right advisory engine.

Regression guard for intent classification across the scripts farmers actually
type: Devanagari Hindi, Hinglish, and English. Every case here was observed to
misroute at some point -- Devanagari verb forms ("क्या लगाऊं", "कब बोऊं"),
Hindi adjective-first word order ("पीले पत्ते" rather than "patti pili"), and
Devanagari input nouns ("यूरिया" rather than "urea") were absent from the
pattern table, so these questions fell through to a generic answer.

A farmer asking "when do I sow mustard" must not receive a crop menu.
"""

from django.test import SimpleTestCase

from advisory.services.chat_intelligence_service import ChatIntelligenceService


class IntentRoutingMultilingualTests(SimpleTestCase):
    """Each question routes to the engine that can actually answer it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.service = ChatIntelligenceService()

    def _intent(self, query: str) -> str:
        intent, _crops = self.service.classify_query(query)
        return intent

    def assert_routes(self, query: str, expected: str) -> None:
        actual = self._intent(query)
        self.assertEqual(
            actual,
            expected,
            f"{query!r} routed to {actual!r}, expected {expected!r}",
        )

    # ── sowing time ──────────────────────────────────────────────
    def test_devanagari_sowing_questions(self):
        for q in ("कब बोऊं सरसों", "सरसों कब बोऊँ", "गेहूं कब लगाऊं",
                  "सरसों की बुवाई का समय", "बीज कब डालें"):
            self.assert_routes(q, "sowing")

    def test_english_sowing_questions(self):
        for q in ("when to sow mustard", "when should I sow wheat",
                  "best time to plant paddy"):
            self.assert_routes(q, "sowing")

    # ── crop choice / rotation ───────────────────────────────────
    def test_crop_recommendation_and_rotation(self):
        for q in ("कौन सी फसल लगाऊं",
                  "मेरे 2 बीघा खेत में गेहूं के बाद अगली फसल क्या लगाऊं? पानी कम है।",
                  "gehun ke baad kaunsi fasal",
                  "what next crop after wheat"):
            self.assert_routes(q, "crop_recommendation")

    # ── symptoms (Hindi puts the colour before the noun) ─────────
    def test_hindi_symptom_word_order(self):
        for q in ("गेहूं में पीले पत्ते हो रहे हैं", "पत्तों पर भूरे धब्बे"):
            self.assert_routes(q, "pest_disease")

    # ── fertiliser named in Devanagari ───────────────────────────
    def test_devanagari_fertiliser_nouns(self):
        for q in ("कितना यूरिया डालूं गेहूं में", "यूरिया कब डालें", "डीएपी कितनी डालूं"):
            self.assert_routes(q, "fertilizer")

    # ── the additions must not steal other intents ───────────────
    def test_other_intents_unaffected(self):
        self.assert_routes("गेहूं का भाव क्या है", "market_price")
        self.assert_routes("PM Kisan ka paisa kab aayega", "government_scheme")
        self.assert_routes("आज मौसम कैसा है", "weather")
        self.assert_routes("नमस्ते", "greeting")
