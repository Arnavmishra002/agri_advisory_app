import socket
import unittest
from unittest.mock import patch

from . import ollama_service


class OllamaServiceTimeoutTests(unittest.TestCase):
    @patch.object(ollama_service, "_ollama_available", return_value=True)
    @patch.object(ollama_service.urllib.request, "urlopen")
    def test_chat_timeout_returns_empty_so_caller_can_use_grounded_fallback(self, urlopen, _available):
        urlopen.side_effect = socket.timeout("timed out")

        response = ollama_service.chat("prompt")

        self.assertEqual(response, "")

    @patch.object(ollama_service, "_ollama_available", return_value=True)
    @patch.object(ollama_service.urllib.request, "urlopen")
    def test_chat_caps_answer_length_for_responsive_completion(self, urlopen, _available):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        response.read.return_value = b'{"message":{"content":"ok"}}'
        urlopen.return_value = response

        ollama_service.chat("prompt")

        payload = urlopen.call_args.args[0].data.decode("utf-8")
        self.assertIn('"num_predict": 320', payload)

    @patch.object(ollama_service, "_ollama_available", return_value=False)
    def test_offline_stream_emits_no_fake_answer_token(self, _available):
        self.assertEqual(list(ollama_service.stream_chat("prompt")), [])


class FarmingPromptSensorGuardTests(unittest.TestCase):
    def test_verified_local_knowledge_has_priority_over_broad_rag(self):
        prompt = ollama_service.build_farming_prompt(
            question="When should I sow wheat?",
            verified_knowledge="Normal wheat sowing window: 1-30 November.",
            rag_chunks=["Late-sown wheat may be planted after 15 December."],
        )

        self.assertIn("[VERIFIED LOCAL KNOWLEDGE", prompt)
        self.assertNotIn("[SUPPLEMENTARY RAG KNOWLEDGE]", prompt)
        self.assertNotIn("Late-sown wheat", prompt)
        self.assertIn("do not copy the paragraph verbatim", prompt)

    def test_weather_only_prompt_marks_field_sensor_data_absent(self):
        prompt = ollama_service.build_farming_prompt(
            question="wheat yellow rust control dose",
            rag_chunks=["Yellow rust spray guidance from ICAR."],
            weather_summary="Current: 35°C\nAir humidity: 64% (not soil moisture)",
            sensor_data=None,
        )

        self.assertIn("[LIVE FIELD SENSOR DATA]", prompt)
        self.assertIn("Not provided for this request", prompt)
        self.assertIn("air humidity is not soil moisture", prompt)
        self.assertNotIn("Soil Moisture  : 64%", prompt)

    def test_system_prompt_forbids_inferring_soil_moisture_from_air_humidity(self):
        self.assertIn("Air humidity or weather humidity", ollama_service.AGRI_SYSTEM_PROMPT)
        self.assertIn("never invent soil", ollama_service.AGRI_SYSTEM_PROMPT)
        self.assertIn("Do not begin with thanks", ollama_service.AGRI_SYSTEM_PROMPT)

    @patch.object(ollama_service, "_ollama_available", return_value=True)
    @patch.object(ollama_service.urllib.request, "urlopen")
    def test_stream_caps_answer_length_for_responsive_completion(self, urlopen, _available):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        response.__iter__.return_value = iter([])
        urlopen.return_value = response

        list(ollama_service.stream_chat("prompt"))

        payload = urlopen.call_args.args[0].data.decode("utf-8")
        self.assertIn('"num_predict": 320', payload)


if __name__ == "__main__":
    unittest.main()
