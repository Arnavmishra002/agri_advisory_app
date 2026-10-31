"""Soil tests are rated by Soil Health Card class, never subtracted from a dose.

The earlier code compared available soil N (a stock) with the crop's fertiliser
dose, so soil N of 150 kg/ha read as "no N needed" for wheat although the Soil
Health Card rates it Low, and it printed urea, DAP, lime and FYM quantities
from formulas with no source.
"""
import re

from django.test import SimpleTestCase

from advisory.services.field_sensor_service import FieldSensorService, _soil_test_class

# Any number followed by a mass or volume unit, per hectare, acre or nothing.
QUANTITY = re.compile(
    r"\d+(?:\.\d+)?\s*(?:kg|g|q|qtl|quintal|t|tonne|ton|l|litre|ml|किलो|किग्रा|क्विंटल|टन|ग्राम)"
    r"(?![A-Za-z])",
    re.IGNORECASE,
)


class QuantityPatternTests(SimpleTestCase):
    def test_pattern_catches_the_quantities_that_were_removed(self):
        for text in ("Apply 50 kg/acre Urea", "apply 2 quintal/acre agricultural lime",
                     "2 tonne per hectare FYM", "यूरिया 50 किग्रा/एकड़"):
            self.assertIsNotNone(QUANTITY.search(text), text)


class SoilClassTests(SimpleTestCase):
    def test_soil_health_card_nitrogen_classes(self):
        self.assertEqual(_soil_test_class("N", 150), "Low")
        self.assertEqual(_soil_test_class("N", 279), "Low")
        self.assertEqual(_soil_test_class("N", 400), "Medium")
        self.assertEqual(_soil_test_class("N", 600), "High")

    def test_low_soil_nitrogen_is_flagged_for_wheat(self):
        gaps = FieldSensorService()._calculate_input_gaps(
            {"nitrogen_kg_ha": 150}, [{"crop_name": "Wheat"}]
        )
        nitrogen = [a for g in gaps for a in g["amendments"] if a["nutrient"].startswith("Nitrogen")]
        self.assertEqual(len(nitrogen), 1)
        self.assertEqual(nitrogen[0]["soil_class"], "Low")

    def test_high_soil_nitrogen_needs_no_amendment_row(self):
        gaps = FieldSensorService()._calculate_input_gaps(
            {"nitrogen_kg_ha": 600}, [{"crop_name": "Wheat"}]
        )
        self.assertFalse([a for g in gaps for a in g["amendments"] if a["nutrient"].startswith("Nitrogen")])

    def test_no_invented_fertiliser_lime_or_manure_quantities(self):
        gaps = FieldSensorService()._calculate_input_gaps(
            {"nitrogen_kg_ha": 100, "phosphorus_kg_ha": 5, "potassium_kg_ha": 50,
             "ph": 4.9, "organic_carbon": 0.3},
            [{"crop_name": "Wheat"}],
        )
        text = " ".join(f"{a.get('amendment', '')} {a.get('timing', '')}" for g in gaps for a in g["amendments"])
        self.assertTrue(text)
        self.assertIsNone(QUANTITY.search(text), text)
        self.assertNotIn("estimated_extra_cost_inr", gaps[0])

    def test_input_hints_give_no_quantities(self):
        hints = FieldSensorService()._input_adjustments("wheat", {"nitrogen_kg_ha": 150, "phosphorus_kg_ha": 5})
        self.assertTrue(hints)
        self.assertIsNone(QUANTITY.search(" ".join(hints)))


class SoilClassConsistencyTests(SimpleTestCase):
    """Every screen rates the same soil test the same way."""

    def test_quick_sensor_advice_gives_no_quantities_in_any_language(self):
        from advisory.api.viewsets.field_advisory import _quick_soil_advice

        status = {"nitrogen": "Low", "phosphorus": "Low", "ph": "Acidic", "organic_carbon": "Low"}
        for lang in ("en", "hi", "ta", "te", "mr", "pa", "bn"):
            text = " ".join(a["action"] for a in _quick_soil_advice(status, lang))
            self.assertTrue(text, lang)
            self.assertIsNone(
                re.search(r"\d+\s*(?:kg|किग्रा|किलो|quintal|क्विंटल|tonne|टन)", text, re.IGNORECASE), (lang, text)
            )

    def test_crop_engine_uses_soil_health_card_classes(self):
        from advisory.services.crop_recommendation_engine import CropRecommendationEngine
        import inspect

        source = inspect.getsource(CropRecommendationEngine)
        self.assertNotIn('"N": 120', source)
        self.assertIn("_soil_test_class", source)
