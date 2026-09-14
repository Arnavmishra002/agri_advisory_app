from unittest.mock import patch

from django.test import SimpleTestCase

from advisory.services.unified_realtime_service import GeminiService


class GeminiProvenanceTests(SimpleTestCase):
    def test_missing_key_returns_no_model_answer(self):
        service = GeminiService()
        service.api_key = ""
        with patch.object(service, "_call_api") as api:
            self.assertEqual(service.generate("wheat sowing"), "")
        api.assert_not_called()

    def test_failed_models_do_not_masquerade_rules_as_gemini(self):
        service = GeminiService()
        service.api_key = "A" * 32
        with patch.object(service, "_call_api", return_value=None), \
             patch.object(service, "_rule_based_response") as rules:
            self.assertEqual(service.generate("wheat sowing"), "")
        rules.assert_not_called()

    def test_success_is_still_the_model_response(self):
        service = GeminiService()
        service.api_key = "A" * 32
        with patch.object(service, "_call_api", return_value="Grounded model answer."):
            self.assertEqual(service.generate("question"), "Grounded model answer.")
