from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIClient

from advisory.services.language_service import detect_query_language


class QueryLanguageDetectionTests(SimpleTestCase):
    def test_detects_hinglish_weather_question(self):
        self.assertEqual(
            detect_query_language("kal ka mausam Kaisa hoga", fallback="hi"),
            "hinglish",
        )

    def test_detects_major_indian_scripts(self):
        cases = {
            "আগামীকাল বৃষ্টি হবে?": "bn",
            "రేపు వర్షం పడుతుందా?": "te",
            "நாளை மழை பெய்யுமா?": "ta",
            "કાલે વરસાદ પડશે?": "gu",
            "ನಾಳೆ ಮಳೆ ಬರುತ್ತದೆಯೇ?": "kn",
            "നാളെ മഴ പെയ്യുമോ?": "ml",
            "ਕੱਲ੍ਹ ਮੀਂਹ ਪਵੇਗਾ?": "pa",
            "هل ستمطر غدا": "ur",
            "ᱜᱟᱯᱟ ᱫᱟᱜ ᱵᱟᱹᱨᱤᱥ ᱟ": "sat",
        }
        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertEqual(detect_query_language(query), expected)

    def test_uses_selected_devanagari_language_as_fallback(self):
        self.assertEqual(detect_query_language("उद्या पाऊस पडेल का?", fallback="mr"), "mr")

    @override_settings(RATE_LIMIT_ENABLED=False)
    @patch("advisory.api.viewsets.chatbot._dispatch_writes")
    @patch("advisory.api.viewsets.chatbot.chat_intelligence_service.answer")
    @patch("advisory.api.viewsets.chatbot.session_memory.load_session_context")
    @patch("advisory.api.viewsets.chatbot.session_memory.load_history", return_value=[])
    def test_auto_language_is_not_replaced_by_previous_session_language(
        self,
        _load_history,
        load_session_context,
        answer,
        _dispatch_writes,
    ):
        load_session_context.return_value = {"language": "en"}
        answer.return_value = {
            "response": "Kal baarish ki probability 60% hai.",
            "intent": "weather",
            "language": "hinglish",
            "sources": ["Open-Meteo"],
            "crops_detected": [],
            "crop_suggestions": [],
            "data_source": "Verified realtime weather data",
            "chatbot_diagnostics": {"selected_tier": "verified_realtime"},
        }

        response = APIClient().post(
            "/api/chatbot/query/",
            {
                "query": "kal Lucknow ka mausam kaisa hoga?",
                "language": "auto",
                "location": "Lucknow",
                "session_id": "language-switch-session",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(answer.call_args.kwargs["language"], "auto")
