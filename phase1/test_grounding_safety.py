import os
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

from phase1.main import app


class Phase1GroundingSafetyTests(TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.request = {
            "query": "an unrelated question with no verified agriculture match",
            "language": "en",
            "location": "Lucknow",
        }

    @patch("phase1.main.chat")
    @patch("phase1.main.retrieve_with_sources", return_value=[])
    def test_json_chat_rejects_ungrounded_generation(self, _retrieve, chat):
        with patch.dict(os.environ, {"DEBUG": "true", "PHASE1_SERVICE_TOKEN": ""}):
            response = self.client.post("/chat", json=self.request)

        self.assertEqual(response.status_code, 422, response.content)
        self.assertEqual(response.json()["detail"]["error_code"], "NO_GROUNDING")
        chat.assert_not_called()

    @patch("phase1.main.retrieve", return_value=[])
    def test_stream_chat_rejects_ungrounded_generation(self, _retrieve):
        with patch.dict(os.environ, {"DEBUG": "true", "PHASE1_SERVICE_TOKEN": ""}):
            response = self.client.post("/chat/stream", json=self.request)

        self.assertEqual(response.status_code, 422, response.content)
        self.assertEqual(response.json()["detail"]["error_code"], "NO_GROUNDING")
