import json
from unittest.mock import patch

from django.test import SimpleTestCase

from advisory.services.chat_intelligence_service import ChatIntelligenceService
from advisory.services.location_context import LocationContext


class _FakeStreamingResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def __iter__(self):
        return iter([
            json.dumps({"token": "local "}).encode("utf-8") + b"\n",
            json.dumps({"token": "rag"}).encode("utf-8") + b"\n",
            json.dumps({"done": True}).encode("utf-8") + b"\n",
        ])


class ChatStreamSourceOrderTests(SimpleTestCase):
    def setUp(self):
        self.service = ChatIntelligenceService()
        self.ctx = LocationContext(
            latitude=26.8467,
            longitude=80.9462,
            display_name="Lucknow",
            state="Uttar Pradesh",
        )

    @patch("advisory.services.chat_intelligence_service._is_valid_gemini_key", return_value=True)
    @patch("advisory.services.knowledge_base.knowledge_base.answer")
    def test_stream_uses_local_kb_before_gemini(self, kb_answer, gemini_key_check):
        kb_answer.return_value = {
            "answer": "KB answer",
            "source": "knowledge_base",
            "confidence": "high",
        }

        chunks = list(self.service.answer_stream("wheat MSP", self.ctx, language="en"))

        self.assertIn("KB answer", "".join(c for c in chunks if isinstance(c, str)))
        self.assertEqual(chunks[-1]["data_source"], "KrishiMitra KB (instant)")
        gemini_key_check.assert_not_called()

    @patch("advisory.services.chat_intelligence_service._is_valid_gemini_key", return_value=True)
    @patch("urllib.request.urlopen", return_value=_FakeStreamingResponse())
    @patch("advisory.services.knowledge_base.knowledge_base.answer")
    def test_stream_uses_phase1_before_gemini(self, kb_answer, urlopen, gemini_key_check):
        kb_answer.return_value = {
            "answer": None,
            "source": "escalate_to_gemini",
            "confidence": "low",
        }

        chunks = list(
            self.service.answer_stream(
                "rice blast control",
                self.ctx,
                language="en",
                farmer_profile={"current_crop": "rice"},
            )
        )

        text = "".join(c for c in chunks if isinstance(c, str))
        self.assertEqual(text, "local rag")
        self.assertEqual(chunks[-1]["data_source"], "krishimitra-llm (stream)")
        gemini_key_check.assert_not_called()

        request = urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["location"], "Lucknow")
        self.assertEqual(payload["latitude"], 26.8467)
        self.assertEqual(payload["longitude"], 80.9462)
        self.assertEqual(payload["crop"], "Rice")
        self.assertEqual(payload["farmer_profile"]["current_crop"], "rice")
