from django.test import TestCase
from unittest.mock import patch

from advisory.ml.inference import CropDiseasePredictor
from advisory.services.disease_chat_bridge import disease_chat_bridge
from advisory.services.krishi_raksha_pest_service import KrishiRakshaPestService


class DiseaseDiagnosisSafetyTests(TestCase):
    def _diagnose_with_ml_status(self, status):
        service = KrishiRakshaPestService()
        service._run_ml_inference = lambda images: {
            "status": status,
            "message": "Crop disease model is not available for production.",
        }
        service.weather_api.get_current_weather = lambda *args, **kwargs: {
            "temperature": 25,
            "humidity": "65",
        }
        return service.diagnose_crop(
            session_id="test-session",
            crop_name="wheat",
            location="Lucknow",
            images={"leaf": "uploaded-image-placeholder"},
            latitude=26.8467,
            longitude=80.9462,
            state="Uttar Pradesh",
        )

    @patch.dict("os.environ", {"ML_ALLOW_UNVERIFIED_MODEL": "false"})
    def test_unverified_model_is_blocked_before_prediction(self):
        predictor = CropDiseasePredictor.__new__(CropDiseasePredictor)
        predictor.model = object()
        predictor.class_names = ["wheat__rust"]
        predictor.metadata = {
            "quality": "needs_retraining",
            "best_val_accuracy": 0.026,
            "best_val_top3_accuracy": 0.079,
            "class_count": 39,
        }

        result = predictor.predict(b"not-a-real-image", skip_validation=True)

        self.assertEqual(result["status"], "model_unverified")
        self.assertEqual(result["confidence"], 0.0)
        self.assertEqual(result["top_predictions"], [])
        self.assertEqual(result["model_quality"], "needs_retraining")

    def test_missing_model_fallback_does_not_expose_fake_disease_or_confidence(self):
        result = self._diagnose_with_ml_status("model_unavailable")

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

    def test_unverified_model_fallback_does_not_expose_fake_disease_or_confidence(self):
        result = self._diagnose_with_ml_status("model_unverified")

        self.assertEqual(result["status"], "advisory_fallback")
        self.assertEqual(result["diagnosis"][0]["name"], "Disease model unavailable")
        self.assertEqual(result["diagnosis"][0]["confidence"], 0.0)
        self.assertEqual(result["diagnosis"][0]["source"], "safety")
