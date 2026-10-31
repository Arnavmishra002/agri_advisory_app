import json
from unittest.mock import patch

from django.test import Client, SimpleTestCase, override_settings


@override_settings(RATE_LIMIT_ENABLED=False)
class ChatStreamEndpointTests(SimpleTestCase):
    def setUp(self):
        self.client = Client()

    @patch("advisory.api.viewsets.chatbot._dispatch_writes")
    @patch("advisory.api.viewsets.chatbot._load_farmer_context", return_value={})
    @patch(
        "advisory.api.viewsets.chatbot._build_history_and_context",
        return_value=([], {}, "en"),
    )
    @patch("advisory.api.viewsets.chatbot.chat_intelligence_service.answer_stream")
    def test_stream_returns_incremental_tokens_and_json_compatible_metadata(
        self,
        answer_stream,
        _history_context,
        _farmer_context,
        dispatch_writes,
    ):
        answer_stream.return_value = iter([
            "soil ",
            "test first",
            {
                "__done__": True,
                "intent": "fertilizer",
                "language": "en",
                "data_source": "KrishiMitra KB (instant)",
                "crops_detected": ["Wheat"],
                "chatbot_diagnostics": {"selected_tier": "knowledge_base"},
                "ai_data_quality": {"label": "Verified knowledge answer"},
                "sources": ["ICAR soil guidance"],
            },
        ])

        response = self.client.post(
            "/api/chatbot/stream/",
            data=json.dumps({
                "query": "fertilizer for wheat",
                "language": "en",
                "location": "Lucknow",
                "latitude": 26.8467,
                "longitude": 80.9462,
                "session_id": "sess_secure_test",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/event-stream; charset=utf-8")
        self.assertEqual(response["X-Accel-Buffering"], "no")
        frames = "".join(part.decode("utf-8") for part in response.streaming_content)
        payloads = [
            json.loads(frame.removeprefix("data: "))
            for frame in frames.strip().split("\n\n")
        ]

        self.assertEqual([row["token"] for row in payloads[:-1]], ["soil ", "test first"])
        done = payloads[-1]
        self.assertTrue(done["done"])
        self.assertEqual(done["intent"], "fertilizer")
        self.assertEqual(done["sources"], ["ICAR soil guidance"])
        self.assertTrue(done["context"]["memory_active"])
        self.assertEqual(done["chatbot_diagnostics"]["selected_tier"], "knowledge_base")
        dispatch_writes.assert_called_once()

    def test_stream_rejects_unknown_fields(self):
        response = self.client.post(
            "/api/chatbot/stream/",
            data=json.dumps({"query": "hello", "unexpected": "reject me"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "INVALID_REQUEST")

    @patch("advisory.api.viewsets.chatbot._dispatch_writes")
    @patch("advisory.api.viewsets.chatbot._load_farmer_context", return_value={})
    @patch(
        "advisory.api.viewsets.chatbot._build_history_and_context",
        return_value=([], {}, "en"),
    )
    @patch("advisory.api.viewsets.chatbot.chat_intelligence_service.answer")
    def test_json_accepts_web_unconfirmed_location_source(
        self,
        answer,
        _history_context,
        _farmer_context,
        _dispatch_writes,
    ):
        answer.return_value = {
            "response": "Hello farmer.",
            "intent": "greeting",
            "language": "en",
            "sources": ["KrishiMitra Advisory Engine"],
            "data_source": "KrishiMitra Advisory Engine",
            "chatbot_diagnostics": {"selected_tier": "instant_rule"},
            "ai_data_quality": {"label": "Instant advisory"},
        }

        response = self.client.post(
            "/api/chatbot/query/",
            data=json.dumps({
                "query": "hello",
                "language": "auto",
                "location_confirmed": False,
                "location_source": "unconfirmed",
                "history": [],
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["intent"], "greeting")

    @patch("advisory.api.viewsets.chatbot._dispatch_writes")
    @patch("advisory.api.viewsets.chatbot._load_farmer_context", return_value={})
    @patch(
        "advisory.api.viewsets.chatbot._build_history_and_context",
        return_value=([], {}, "en"),
    )
    @patch("advisory.api.viewsets.chatbot.chat_intelligence_service.answer_stream")
    def test_stream_accepts_web_unconfirmed_location_source(
        self,
        answer_stream,
        _history_context,
        _farmer_context,
        _dispatch_writes,
    ):
        answer_stream.return_value = iter([
            "Hello farmer.",
            {"__done__": True, "intent": "greeting", "language": "en"},
        ])

        response = self.client.post(
            "/api/chatbot/stream/",
            data=json.dumps({
                "query": "hello",
                "language": "auto",
                "location_confirmed": False,
                "location_source": "unconfirmed",
                "history": [],
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        frames = "".join(part.decode("utf-8") for part in response.streaming_content)
        self.assertIn("Hello farmer.", frames)

    @patch("advisory.api.viewsets.chatbot._dispatch_writes")
    @patch("advisory.api.viewsets.chatbot._load_farmer_context", return_value={})
    @patch(
        "advisory.api.viewsets.chatbot._build_history_and_context",
        return_value=([], {}, "mr"),
    )
    @patch("advisory.api.viewsets.chatbot.chat_intelligence_service.answer_stream")
    def test_stream_accepts_a_supported_regional_language(
        self,
        answer_stream,
        _history_context,
        _farmer_context,
        _dispatch_writes,
    ):
        answer_stream.return_value = iter([
            "नमस्कार",
            {"__done__": True, "intent": "greeting", "language": "mr"},
        ])

        response = self.client.post(
            "/api/chatbot/stream/",
            data=json.dumps({"query": "नमस्कार", "language": "mr"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        frames = "".join(part.decode("utf-8") for part in response.streaming_content)
        self.assertIn("नमस्कार", frames)

    def test_stream_rejects_an_unsupported_language(self):
        response = self.client.post(
            "/api/chatbot/stream/",
            data=json.dumps({"query": "hello", "language": "xx"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("language", response.json()["details"])


@override_settings(RATE_LIMIT_ENABLED=False)
class ChatStreamKeepAliveTests(SimpleTestCase):
    @patch("advisory.api.viewsets.chatbot._dispatch_writes")
    @patch("advisory.api.viewsets.chatbot._load_farmer_context", return_value={})
    @patch("advisory.api.viewsets.chatbot._build_history_and_context", return_value=([], {}, "en"))
    @patch("advisory.api.viewsets.chatbot.chat_intelligence_service.answer_stream")
    def test_heartbeat_becomes_an_sse_comment(self, answer_stream, *_):
        answer_stream.return_value = iter([
            {"__heartbeat__": True},
            "checked answer",
            {"__done__": True, "intent": "general", "language": "en", "data_source": "x"},
        ])

        response = Client().post(
            "/api/chatbot/stream/",
            data=json.dumps({"query": "hello there farmer", "language": "en", "location": "Lucknow",
                             "latitude": 26.8467, "longitude": 80.9462, "session_id": "sess_keepalive"}),
            content_type="application/json",
        )

        frames = "".join(part.decode("utf-8") for part in response.streaming_content)
        self.assertTrue(frames.startswith(": keepalive\n\n"), frames[:80])
        self.assertIn('"token": "checked answer"', frames)
        self.assertNotIn("__heartbeat__", frames)


@override_settings(RATE_LIMIT_ENABLED=False)
class LongHistoryTests(SimpleTestCase):
    """A long earlier answer must not make every later question fail with 400."""

    @patch("advisory.api.viewsets.chatbot._dispatch_writes")
    @patch("advisory.api.viewsets.chatbot._load_farmer_context", return_value={})
    @patch("advisory.api.viewsets.chatbot.chat_intelligence_service.answer_stream")
    def test_long_assistant_turn_is_shortened_not_rejected(self, answer_stream, *_):
        answer_stream.return_value = iter([
            "ok",
            {"__done__": True, "intent": "general", "language": "hi", "data_source": "x"},
        ])
        long_answer = "गेहूं की सिंचाई " * 400  # about 6,000 characters

        response = Client().post(
            "/api/chatbot/stream/",
            data=json.dumps({"query": "aur kya karein", "language": "hi", "location": "Lucknow",
                             "latitude": 26.8467, "longitude": 80.9462,
                             "history": [{"role": "user", "content": "gehu ki sinchai"},
                                         {"role": "assistant", "content": long_answer}]}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        b"".join(response.streaming_content)
        history = answer_stream.call_args.kwargs["history"]
        self.assertTrue(history)
        self.assertTrue(all(len(turn["content"]) <= 2000 for turn in history))

    @patch("advisory.api.viewsets.chatbot._dispatch_writes")
    @patch("advisory.api.viewsets.chatbot._load_farmer_context", return_value={})
    @patch("advisory.api.viewsets.chatbot.chat_intelligence_service.answer_stream")
    def test_turn_cut_inside_an_emoji_is_accepted(self, answer_stream, *_):
        # An older client cut long turns by UTF-16 units, leaving half of 🌾.
        answer_stream.return_value = iter([
            "ok",
            {"__done__": True, "intent": "general", "language": "hi", "data_source": "x"},
        ])
        cut_answer = "क" * 1999 + "\ud83c"

        response = Client().post(
            "/api/chatbot/stream/",
            data=json.dumps({"query": "aur kya karein", "language": "hi", "location": "Lucknow",
                             "latitude": 26.8467, "longitude": 80.9462,
                             "history": [{"role": "assistant", "content": cut_answer}]}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        b"".join(response.streaming_content)
        history = answer_stream.call_args.kwargs["history"]
        self.assertEqual(history[-1]["content"], "क" * 1999)

    @patch("advisory.api.viewsets.chatbot._dispatch_writes")
    @patch("advisory.api.viewsets.chatbot._load_farmer_context", return_value={})
    @patch("advisory.api.viewsets.chatbot.chat_intelligence_service.answer")
    def test_json_endpoint_uses_the_cleaned_history(self, answer, *_):
        # The non-streaming fallback must use validated history too: a lone
        # surrogate reaching the model made the request fail with 500.
        answer.return_value = {
            "response": "ok", "intent": "general", "language": "hi",
            "sources": [], "data_source": "x",
        }
        cut_answer = "क" * 1999 + "\ud83c"  # the half emoji survives the 2,000 cut

        response = Client().post(
            "/api/chatbot/query/",
            data=json.dumps({"query": "aur kya karein", "language": "hi", "location": "Lucknow",
                             "latitude": 26.8467, "longitude": 80.9462,
                             "history": [{"role": "assistant", "content": cut_answer}]}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        history = answer.call_args.kwargs["history"]
        self.assertTrue(history)
        for turn in history:
            self.assertLessEqual(len(turn["content"]), 2000)
            self.assertFalse(any("\ud800" <= ch <= "\udfff" for ch in turn["content"]))
