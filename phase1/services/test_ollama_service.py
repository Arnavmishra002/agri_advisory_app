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


if __name__ == "__main__":
    unittest.main()
