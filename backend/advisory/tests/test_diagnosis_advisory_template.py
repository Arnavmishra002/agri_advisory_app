"""A released diagnosis becomes a fixed advisory, never a chat question.

The old bridge rewrote the label as "please tell me the chemical dose" and sent
it through the chatbot, which routed it elsewhere and dropped the diagnosis.
"""
import re
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from advisory.services.disease_chat_bridge import disease_chat_bridge

DOSE = re.compile(r"\d+(?:\.\d+)?\s*(?:ml|g|gm|kg|l|मिली|ग्राम)\b", re.IGNORECASE)


def _diagnosis(confidence=0.91, alternatives=None):
    return {
        "status": "success",
        "crop_detected": "Tomato",
        "diagnosis": [{
            "name": "Late Blight",
            "confidence": confidence,
            "severity_label": "Medium",
            "top_predictions": [{"disease_name": "Late Blight", "probability": confidence}] + (alternatives or []),
        }],
    }


class DiagnosisAdvisoryTemplateTests(SimpleTestCase):
    def test_names_the_diagnosis_confidence_and_next_steps_without_a_dose(self):
        advice = disease_chat_bridge.format_for_api(_diagnosis(), ctx=None, language="en")
        text = advice["response"]
        self.assertIn("Late Blight", text)
        self.assertIn("91%", text)
        self.assertIn("KVK", text)
        self.assertIn("1800-180-1551", text)
        self.assertIsNone(DOSE.search(text), text)
        self.assertEqual(advice["spray_window"], "unknown")

    def test_lists_only_plausible_alternatives(self):
        advice = disease_chat_bridge.format_for_api(
            _diagnosis(0.80, [{"disease_name": "Early Blight", "probability": 0.12},
                              {"disease_name": "Leaf Mold", "probability": 0.01}]),
            ctx=None, language="en",
        )
        self.assertIn("Early Blight (12%)", advice["response"])
        self.assertNotIn("Leaf Mold", advice["response"])

    def test_hindi_and_hinglish_use_the_right_script(self):
        hindi = disease_chat_bridge.format_for_api(_diagnosis(), ctx=None, language="hi")["response"]
        hinglish = disease_chat_bridge.format_for_api(_diagnosis(), ctx=None, language="hinglish")["response"]
        self.assertRegex(hindi, r"[ऀ-ॿ]")
        self.assertNotRegex(hinglish, r"[ऀ-ॿ]")

    def test_spray_window_follows_the_48_hour_forecast(self):
        ctx = SimpleNamespace(latitude=26.85, longitude=80.95, display_name="Lucknow")
        cases = (
            ([{"rainfall_mm": 25, "rain_probability": 40}, {"rainfall_mm": 0, "rain_probability": 0}], "blocked"),
            ([{"rainfall_mm": 2, "rain_probability": 80}, {"rainfall_mm": 0, "rain_probability": 0}], "blocked"),
            ([{"rainfall_mm": 2, "rain_probability": 30}, {"rainfall_mm": 5, "rain_probability": 60}], "clear"),
        )
        for forecast, expected in cases:
            with patch("advisory.services.unified_realtime_service.weather_service.get_weather",
                       return_value={"is_live": True, "forecast_7day": forecast}):
                advice = disease_chat_bridge.format_for_api(_diagnosis(), ctx=ctx, language="en")
            self.assertEqual(advice["spray_window"], expected, forecast)

    def test_unavailable_weather_is_never_reported_as_clear(self):
        ctx = SimpleNamespace(latitude=26.85, longitude=80.95, display_name="Lucknow")
        with patch("advisory.services.unified_realtime_service.weather_service.get_weather",
                   return_value={"is_live": False, "forecast_7day": []}):
            advice = disease_chat_bridge.format_for_api(_diagnosis(), ctx=ctx, language="en")
        self.assertEqual(advice["spray_window"], "unknown")

    def test_refused_diagnosis_is_not_turned_into_advice(self):
        advice = disease_chat_bridge.format_for_api({"status": "low_confidence"}, ctx=None, language="en")
        self.assertTrue(advice["skipped"])
