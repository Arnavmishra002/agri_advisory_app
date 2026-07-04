from django.test import TestCase

from advisory.services.disease_chat_bridge import disease_chat_bridge
from advisory.services.krishi_raksha_pest_service import KrishiRakshaPestService


class DiseaseDiagnosisSafetyTests(TestCase):
    def test_missing_model_fallback_does_not_expose_fake_disease_or_confidence(self):
        service = KrishiRakshaPestService()
        service._run_ml_inference = lambda images: {
            "status": "model_unavailable",
            "message": "No trained crop disease model is installed.",
        }
        service.weather_api.get_current_weather = lambda *args, **kwargs: {
            "temperature": 25,
            "humidity": "65",
        }

        result = service.diagnose_crop(
            session_id="test-session",
            crop_name="wheat",
            location="Lucknow",
            images={"leaf": "uploaded-image-placeholder"},
            latitude=26.8467,
            longitude=80.9462,
            state="Uttar Pradesh",
        )

        self.assertEqual(result["status"], "advisory_fallback")
        self.assertGreater(len(result["diagnosis"]), 0)
        for diagnosis in result["diagnosis"]:
            self.assertEqual(diagnosis["confidence"], 0.0)
            self.assertEqual(diagnosis["source"], "safety")
            self.assertIn("not image classification", diagnosis["explanation"].lower())
            self.assertNotIn("rust", diagnosis["name"].lower())
            self.assertNotIn("smut", diagnosis["name"].lower())
            self.assertNotIn("borer", diagnosis["name"].lower())

        api_result = disease_chat_bridge.format_for_api(result, ctx=None, language="en")

        self.assertEqual(api_result["data_source"], "advisory_fallback")
        self.assertEqual(api_result["confidence"], 0.0)
        self.assertEqual(api_result["disease"], "Disease model unavailable")
        self.assertIn("not image classification", api_result["response"].lower())
