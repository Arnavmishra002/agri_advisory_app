import json
from unittest.mock import patch

import requests
from django.test import SimpleTestCase

from advisory.services import chat_intelligence_service as chat_module
from advisory.services.chat_intelligence_service import (
    ChatIntelligenceService,
    SensorContext,
    WeatherConstraints,
)
from advisory.services.location_context import LocationContext


class _FakeStreamingResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        return None

    def iter_lines(self):
        return iter([
            json.dumps({"token": "local "}).encode("utf-8") + b"\n",
            json.dumps({"token": "rag"}).encode("utf-8") + b"\n",
            json.dumps({"done": True}).encode("utf-8") + b"\n",
        ])


class _FakeJSONResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


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
    @patch("advisory.services.chat_intelligence_service.requests.post", return_value=_FakeStreamingResponse())
    @patch("advisory.services.knowledge_base.knowledge_base.answer")
    def test_stream_uses_phase1_before_gemini(self, kb_answer, requests_post, gemini_key_check):
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

        self.assertEqual(requests_post.call_args.kwargs["timeout"], chat_module._PHASE1_STREAM_TIMEOUT)
        self.assertTrue(requests_post.call_args.kwargs["stream"])
        payload = json.loads(requests_post.call_args.kwargs["data"].decode("utf-8"))
        self.assertEqual(payload["location"], "Lucknow")
        self.assertEqual(payload["latitude"], 26.8467)
        self.assertEqual(payload["longitude"], 80.9462)
        self.assertEqual(payload["crop"], "Rice")
        self.assertEqual(payload["farmer_profile"]["current_crop"], "rice")


class ChatLocalLLMTimeoutTests(SimpleTestCase):
    def setUp(self):
        self.service = ChatIntelligenceService()
        self.ctx = LocationContext(
            latitude=26.8467,
            longitude=80.9462,
            display_name="Lucknow",
            state="Uttar Pradesh",
        )

    @patch("advisory.services.chat_intelligence_service._cb_reset")
    @patch("advisory.services.chat_intelligence_service._cb_is_open", return_value=False)
    @patch("advisory.services.chat_intelligence_service.requests.post")
    def test_phase1_json_uses_split_timeout(self, requests_post, _cb_open, _cb_reset):
        requests_post.return_value = _FakeJSONResponse({"response": "phase1 answer", "rag_chunks": 2})

        answer = self.service._qwen_rag_answer(
            "wheat rust control",
            self.ctx,
            "en",
            history=[],
            sc=SensorContext(),
            wc=WeatherConstraints(),
            market_str="",
        )

        self.assertEqual(answer, "phase1 answer")
        self.assertEqual(requests_post.call_args.kwargs["timeout"], chat_module._PHASE1_TIMEOUT)

    @patch("advisory.services.chat_intelligence_service._cb_reset")
    @patch("advisory.services.chat_intelligence_service._cb_increment")
    @patch("advisory.services.chat_intelligence_service._cb_is_open", return_value=False)
    @patch("advisory.services.chat_intelligence_service.requests.post")
    def test_direct_ollama_uses_split_timeout_after_phase1_timeout(
        self,
        requests_post,
        _cb_open,
        _cb_increment,
        _cb_reset,
    ):
        requests_post.side_effect = [
            requests.Timeout("phase1 slow"),
            _FakeJSONResponse({"message": {"content": "direct answer"}}),
        ]

        answer = self.service._qwen_rag_answer(
            "custom crop question",
            self.ctx,
            "en",
            history=[],
            sc=SensorContext(),
            wc=WeatherConstraints(),
            market_str="",
        )

        self.assertEqual(answer, "direct answer")
        self.assertEqual(requests_post.call_args_list[0].kwargs["timeout"], chat_module._PHASE1_TIMEOUT)
        self.assertEqual(requests_post.call_args_list[1].kwargs["timeout"], chat_module._OLLAMA_DIRECT_TIMEOUT)
        direct_payload = json.loads(requests_post.call_args_list[1].kwargs["data"].decode("utf-8"))
        system_prompt = direct_payload["messages"][0]["content"]
        self.assertIn("not have enough verified context", system_prompt)
        self.assertIn("KVK/agriculture officer", system_prompt)
        _cb_increment.assert_called_once()
