import socket
import unittest
from unittest.mock import patch

from . import ollama_service


class OllamaServiceTimeoutTests(unittest.TestCase):
    @patch("phase1.services.ollama_service._ollama_available", return_value=True)
    @patch("phase1.services.ollama_service.urllib.request.urlopen")
    def test_chat_timeout_returns_farmer_safe_fallback(self, urlopen, _available):
        urlopen.side_effect = socket.timeout("timed out")

        response = ollama_service.chat("prompt")

        self.assertIn("Kisan Helpline", response)


class FarmingPromptSensorGuardTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
