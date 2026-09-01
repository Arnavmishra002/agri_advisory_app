r"""Devanagari terms in the intent table must actually be reachable.

Python's ``\w`` matches letters and digits but not Devanagari vowel signs or
the virama (U+093F ि, U+0940 ी, U+094D ्  -- Unicode categories Mc and Mn).
A word such as "मिट्टी" therefore *ends* on a non-word character, so a trailing
``\b`` asks for a word-to-non-word transition that can never happen and the
alternative silently never matches.

An audit of ``_INTENT_PATTERNS`` found this disabling core farmer vocabulary
across nearly every intent -- मंडी, पानी, मिट्टी, बीमा, योजना, पीली, पत्ती,
सफेद मक्खी, बाढ़. It stayed hidden because most groups also contain an
alternative ending in a consonant, so the common phrasings still routed; only
the phrasings where the vowel-ending term was the one that should have matched
fell through to a generic reply.

These tests pin both halves: the boundary helper itself, and the farmer
questions that were observed misrouting before it was applied.
"""

from __future__ import annotations

import re

from django.test import SimpleTestCase

from advisory.services.chat_intelligence_service import (
    ChatIntelligenceService,
    _INTENT_PATTERNS,
    _devanagari_safe_boundaries,
)


class DevanagariBoundaryHelperTests(SimpleTestCase):
    """The helper must fix Devanagari without loosening Latin matching."""

    def test_trailing_boundary_blocks_devanagari_before_the_fix(self):
        """Documents the underlying regex behaviour the fix exists for."""
        self.assertIsNone(re.search(r"\b(soil|मिट्टी)\b", "मेरी मिट्टी कैसी है"))

    def test_helper_makes_the_same_pattern_match(self):
        fixed = _devanagari_safe_boundaries(r"\b(soil|मिट्टी)\b")
        self.assertIsNotNone(re.search(fixed, "मेरी मिट्टी कैसी है"))

    def test_latin_substring_matching_is_still_prevented(self):
        """"soiled" must not match "soil" -- the anchors still do their job."""
        fixed = _devanagari_safe_boundaries(r"\b(soil|मिट्टी)\b")
        self.assertIsNone(re.search(fixed, "the soiled cloth"))
        self.assertIsNotNone(re.search(fixed, "check the soil today"))

    def test_every_pattern_in_the_table_still_compiles(self):
        for intent, patterns in _INTENT_PATTERNS:
            for pattern in patterns:
                with self.subTest(intent=intent, pattern=pattern):
                    re.compile(pattern)

    def test_no_pattern_keeps_a_raw_outer_backslash_b(self):
        """A new pattern added with \\b would silently reintroduce the bug."""
        offenders = [
            (intent, p)
            for intent, patterns in _INTENT_PATTERNS
            for p in patterns
            if p.startswith(r"\b") or p.endswith(r"\b")
        ]
        self.assertEqual(
            offenders, [], f"patterns still carrying an outer \\b: {offenders[:5]}"
        )


class DevanagariRoutingRegressionTests(SimpleTestCase):
    """Questions observed falling through to a generic reply."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.service = ChatIntelligenceService()

    def assert_routes(self, query: str, expected: str) -> None:
        actual, _crops = self.service.classify_query(query)
        self.assertEqual(
            actual, expected, f"{query!r} routed to {actual!r}, expected {expected!r}"
        )

    def test_soil_questions_reach_the_soil_engine(self):
        # "मिट्टी" ends in ी and was unreachable through the trailing \b.
        for q in ("मेरी मिट्टी कैसी है", "मिट्टी की जांच कैसे करें"):
            self.assert_routes(q, "soil")

    def test_seed_quantity_is_a_sowing_question(self):
        # The Hinglish form already worked; the Devanagari forms did not, even
        # though the sowing answer is what carries the seed rate.
        for q in ("कितना बीज लगेगा?", "बीज दर क्या है", "कितना बीज डालना है",
                  "seed rate kitna hai"):
            self.assert_routes(q, "sowing")

    def test_storage_accepts_the_transliterated_verb(self):
        for q in ("फसल कैसे स्टोर करूं", "भंडारण कैसे करें"):
            self.assert_routes(q, "storage")

    def test_weed_questions_reach_crop_protection(self):
        """Weeds have no intent of their own; the generic reply helped nobody."""
        for q in ("खरपतवार कैसे हटाऊं", "कौन सा खरपतवारनाशी डालूं"):
            self.assert_routes(q, "pest_disease")

    def test_previously_working_intents_are_unaffected(self):
        for q, expected in [
            ("कब बोऊं सरसों", "sowing"),
            ("गेहूं का भाव क्या है", "market_price"),
            ("आज मौसम कैसा है", "weather"),
            ("कितना यूरिया डालूं गेहूं में", "fertilizer"),
            ("गेहूं में पीले पत्ते हो रहे हैं", "pest_disease"),
            ("कौन सी फसल लगाऊं", "crop_recommendation"),
            ("PM Kisan ka paisa kab aayega", "government_scheme"),
            ("कब कटाई करूं", "harvest"),
            ("पानी कब दूं", "irrigation"),
            ("नमस्ते", "greeting"),
        ]:
            with self.subTest(query=q):
                self.assert_routes(q, expected)
