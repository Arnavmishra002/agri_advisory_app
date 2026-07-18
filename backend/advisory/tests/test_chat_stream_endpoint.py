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
                "ai_data_quality": {"label": "Verified knowledge base"},
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
