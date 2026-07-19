import json
from unittest.mock import patch

import requests
from django.test import SimpleTestCase

from advisory.services import chat_intelligence_service as chat_module
from advisory.services.chat_intelligence_service import (
    ChatIntelligenceService,
    SensorContext,
    WeatherConstraints,
    chatbot_quality_metadata,
)
from advisory.services.location_context import LocationContext


class _FakeStreamingResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        return None

    def iter_lines(self, **kwargs):
        self.iter_lines_kwargs = kwargs
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


class _FakeOfflineStreamingResponse(_FakeStreamingResponse):
    def iter_lines(self, **kwargs):
        self.iter_lines_kwargs = kwargs
        return iter([
            json.dumps({"token": "AI सेवा ऑफलाइन है। Kisan Helpline: 1800-180-1551"}).encode("utf-8") + b"\n",
            json.dumps({"done": True}).encode("utf-8") + b"\n",
        ])


class _FakeInterruptedStreamingResponse(_FakeStreamingResponse):
    def iter_lines(self, **kwargs):
        self.iter_lines_kwargs = kwargs
        yield json.dumps({"token": "grounded start"}).encode("utf-8") + b"\n"
        raise requests.Timeout("stream interrupted")


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
    @patch("advisory.services.chat_intelligence_service.requests.post", return_value=_FakeStreamingResponse())
    @patch("advisory.services.knowledge_base.knowledge_base.answer")
    def test_stream_composes_kb_backed_question_with_local_rag(
        self,
        kb_answer,
        requests_post,
        gemini_key_check,
    ):
        kb_answer.return_value = {
            "answer": "Stored KB answer",
            "source": "knowledge_base",
            "confidence": "high",
        }

        chunks = list(self.service.answer_stream("wheat MSP", self.ctx, language="en"))

        text = "".join(c for c in chunks if isinstance(c, str))
        self.assertEqual(text, "local rag")
        self.assertNotIn("Stored KB answer", text)
        self.assertEqual(chunks[-1]["data_source"], "KrishiMitra local RAG (stream)")
        requests_post.assert_called_once()
        kb_answer.assert_called_once()
        payload = json.loads(requests_post.call_args.kwargs["data"].decode("utf-8"))
        self.assertEqual(payload["verified_knowledge"], "Stored KB answer")
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
                "rice crop management advice",
                self.ctx,
                language="en",
                farmer_profile={"current_crop": "rice"},
            )
        )

        text = "".join(c for c in chunks if isinstance(c, str))
        self.assertEqual(text, "local rag")
        self.assertEqual(chunks[-1]["data_source"], "KrishiMitra local RAG (stream)")
        gemini_key_check.assert_not_called()

        self.assertEqual(requests_post.call_args.kwargs["timeout"], chat_module._PHASE1_STREAM_TIMEOUT)
        self.assertTrue(requests_post.call_args.kwargs["stream"])
        self.assertEqual(requests_post.return_value.iter_lines_kwargs["chunk_size"], 1)
        payload = json.loads(requests_post.call_args.kwargs["data"].decode("utf-8"))
        self.assertEqual(payload["location"], "Lucknow")
        self.assertEqual(payload["latitude"], 26.8467)
        self.assertEqual(payload["longitude"], 80.9462)
        self.assertEqual(payload["crop"], "Rice")
        self.assertEqual(payload["farmer_profile"]["current_crop"], "rice")

    @patch(
        "advisory.services.chat_intelligence_service.requests.post",
        return_value=_FakeInterruptedStreamingResponse(),
    )
    @patch("advisory.services.knowledge_base.knowledge_base.answer")
    def test_partial_stream_does_not_append_a_second_fallback_answer(
        self,
        kb_answer,
        requests_post,
    ):
        kb_answer.return_value = {"answer": "verified rice facts", "source": "knowledge_base"}

        chunks = list(self.service.answer_stream("rice crop management advice", self.ctx, language="en"))

        text = "".join(chunk for chunk in chunks if isinstance(chunk, str))
        self.assertIn("grounded start", text)
        self.assertIn("response was interrupted", text)
        self.assertNotIn("Kisan Helpline", text)
        self.assertEqual(chunks[-1]["chatbot_diagnostics"]["selected_tier"], "phase1_partial_stream")
        self.assertEqual(chunks[-1]["data_source"], "KrishiMitra local RAG (partial)")
        requests_post.assert_called_once()

    @patch("advisory.services.chat_intelligence_service.gemini_service")
    @patch("advisory.services.chat_intelligence_service.requests.post")
    @patch("advisory.services.knowledge_base.knowledge_base.answer")
    def test_stream_busy_local_ai_returns_degraded_done_frame(
        self,
        kb_answer,
        requests_post,
        gemini_service,
    ):
        kb_answer.return_value = {
            "answer": None,
            "source": "escalate_to_gemini",
            "confidence": "low",
        }
        gemini_service.api_key = ""
        self.assertTrue(chat_module._acquire_local_ai_slot())
        try:
            chunks = list(self.service.answer_stream("rice crop management advice", self.ctx, language="en"))
        finally:
            chat_module._release_local_ai_slot()

        text = "".join(c for c in chunks if isinstance(c, str))
        done = chunks[-1]
        self.assertIn("Local AI is busy", text)
        self.assertEqual(done["data_source"], "local_ai_busy_fallback")
        self.assertEqual(done["chatbot_diagnostics"]["selected_tier"], "local_ai_busy_fallback")
        requests_post.assert_not_called()

    @patch("advisory.services.chat_intelligence_service.requests.post")
    @patch("advisory.services.knowledge_base.knowledge_base.answer")
    def test_greeting_stream_skips_kb_and_llm(self, kb_answer, requests_post):
        chunks = list(self.service.answer_stream("hii", self.ctx, language="en"))

        text = "".join(c for c in chunks if isinstance(c, str))
        done = chunks[-1]
        self.assertIn("Hello Farmer", text)
        self.assertEqual(done["chatbot_diagnostics"]["selected_tier"], "instant_rule")
        kb_answer.assert_not_called()
        requests_post.assert_not_called()

    @patch("advisory.services.chat_intelligence_service.requests.post")
    @patch("advisory.services.knowledge_base.knowledge_base.answer")
    def test_hinglish_weather_stream_uses_grounded_realtime_path(
        self,
        kb_answer,
        requests_post,
    ):
        canonical = {
            "response": "Kal Lucknow mein 29°C aur halki baarish ka anuman hai.",
            "intent": "weather",
            "language": "hi",
            "data_source": "Verified realtime weather data",
            "crops_detected": [],
            "sources": ["Open-Meteo live"],
            "chatbot_diagnostics": {"selected_tier": "verified_realtime"},
            "ai_data_quality": {
                "tier": "verified_realtime",
                "label": "Verified live data",
                "status": "live",
            },
        }

        with patch.object(self.service, "answer", return_value=canonical) as answer:
            chunks = list(
                self.service.answer_stream(
                    "kal ka mausam Kaisa hoga",
                    self.ctx,
                    language="hi",
                )
            )

        text = "".join(c for c in chunks if isinstance(c, str))
        done = chunks[-1]
        self.assertEqual(text, canonical["response"])
        self.assertEqual(done["intent"], "weather")
        self.assertEqual(done["data_source"], "Verified realtime weather data")
        self.assertEqual(done["ai_data_quality"]["tier"], "verified_realtime")
        answer.assert_called_once()
        kb_answer.assert_not_called()
        requests_post.assert_not_called()

    @patch("advisory.services.chat_intelligence_service._is_valid_gemini_key", return_value=True)
    @patch("advisory.services.chat_intelligence_service.requests.post", side_effect=requests.Timeout("phase1 stalled"))
    @patch("advisory.services.knowledge_base.knowledge_base.answer")
    def test_stream_timeout_uses_fast_grounded_fallback_without_second_llm_attempt(
        self,
        kb_answer,
        requests_post,
        gemini_key_check,
    ):
        kb_answer.return_value = {
            "answer": None,
            "source": "escalate_to_gemini",
            "confidence": "low",
        }
        canonical = {
            "response": "Verified safe advisory for the exact question.",
            "intent": "pest_disease",
            "language": "en",
            "data_source": "KrishiMitra Advisory Engine",
            "crops_detected": ["Rice"],
            "chatbot_diagnostics": {"selected_tier": "rule_based_fallback"},
        }

        with patch.object(self.service, "answer", return_value=canonical) as answer:
            chunks = list(self.service.answer_stream("rice crop management advice", self.ctx, language="en"))

        text = "".join(c for c in chunks if isinstance(c, str))
        self.assertEqual(text, canonical["response"])
        answer.assert_called_once()
        self.assertTrue(answer.call_args.kwargs["fast_mode"])

    @patch(
        "advisory.services.chat_intelligence_service.requests.post",
        return_value=_FakeOfflineStreamingResponse(),
    )
    @patch("advisory.services.knowledge_base.knowledge_base.answer")
    def test_phase1_offline_text_is_not_shown_as_an_answer(self, kb_answer, requests_post):
        kb_answer.return_value = {"answer": None, "source": "escalate_to_gemini"}
        canonical = {
            "response": "Verified safe fallback for the exact question.",
            "intent": "pest_disease",
            "language": "en",
            "data_source": "KrishiMitra Advisory Engine",
            "crops_detected": [],
            "chatbot_diagnostics": {"selected_tier": "rule_based_fallback"},
        }

        with patch.object(self.service, "answer", return_value=canonical):
            chunks = list(
                self.service.answer_stream(
                    "What should I do for leaf spots?",
                    self.ctx,
                    language="en",
                )
            )

        text = "".join(chunk for chunk in chunks if isinstance(chunk, str))
        self.assertEqual(text, canonical["response"])
        self.assertNotIn("ऑफलाइन", text)


class ChatLocalLLMTimeoutTests(SimpleTestCase):
    def setUp(self):
        self.service = ChatIntelligenceService()
        self.ctx = LocationContext(
            latitude=26.8467,
            longitude=80.9462,
            display_name="Lucknow",
            state="Uttar Pradesh",
        )

    def test_quality_metadata_labels_degraded_fallback_honestly(self):
        quality = chatbot_quality_metadata(
            "KrishiMitra Advisory Engine",
            {
                "selected_tier": "rule_based_fallback",
                "total_llm_ms": 120,
            },
        )

        self.assertEqual(quality["status"], "degraded")
        self.assertTrue(quality["is_degraded"])
        self.assertEqual(quality["label"], "Safe advisory")
        self.assertTrue(quality["meets_latency_target"])

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

    @patch("advisory.services.chat_intelligence_service.requests.post")
    @patch("advisory.services.knowledge_base.knowledge_base.answer")
    def test_local_ai_capacity_full_returns_fast_fallback(self, kb_answer, requests_post):
        kb_answer.return_value = {
            "answer": None,
            "source": "escalate_to_gemini",
            "confidence": "low",
        }
        self.assertTrue(chat_module._acquire_local_ai_slot())
        try:
            result = self.service.answer("custom crop question", self.ctx, language="en")
        finally:
            chat_module._release_local_ai_slot()

        self.assertIn("Local AI is busy", result["response"])
        self.assertEqual(result["data_source"], "local_ai_busy_fallback")
        self.assertEqual(result["chatbot_diagnostics"]["selected_tier"], "local_ai_busy_fallback")
        requests_post.assert_not_called()

    @patch("advisory.services.chat_intelligence_service.market_service.get_prices")
    @patch("advisory.services.chat_intelligence_service.weather_service.get_weather")
    @patch("advisory.services.knowledge_base.knowledge_base.answer")
    def test_weather_intent_skips_mandi_fetch(self, kb_answer, get_weather, get_prices):
        kb_answer.return_value = {
            "answer": "Weather answer",
            "source": "knowledge_base",
            "confidence": "high",
        }
        get_weather.return_value = {
            "current": {"temperature": 28, "humidity": 70, "condition": "Cloudy"},
            "forecast_7day": [],
            "farming_alerts": [],
            "data_source": "Open-Meteo live",
            "is_live": True,
        }

        result = self.service.answer("Lucknow weather today", self.ctx, language="en")

        self.assertIn("28", result["response"])
        self.assertEqual(result["ai_data_quality"]["tier"], "verified_realtime")
        get_weather.assert_called()
        get_prices.assert_not_called()

    @patch("advisory.services.chat_intelligence_service.market_service.get_prices")
    @patch("advisory.services.knowledge_base.knowledge_base.answer")
    def test_mandi_intent_keeps_fallback_source_label(self, kb_answer, get_prices):
        kb_answer.return_value = {
            "answer": None,
            "source": "escalate_to_gemini",
            "confidence": "low",
        }
        get_prices.return_value = {
            "is_live": False,
            "top_crops": [],
            "data_source": "Agmarknet fallback estimate (not live)",
        }

        result = self.service.answer("wheat mandi price", self.ctx, language="en", fast_mode=True)

        self.assertIn(
            "Agmarknet official feed checked - no current official row",
            result["sources"],
        )
        self.assertNotIn("Agmarknet fallback estimate (not live)", result["sources"])
