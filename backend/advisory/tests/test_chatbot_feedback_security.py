import hashlib

from django.core import signing
from django.test import TestCase
from rest_framework.test import APIClient

from advisory.models import FarmerInteractionLog


class ChatbotFeedbackSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.interaction = FarmerInteractionLog.objects.create(
            session_id="sess-test-feedback",
            query="kal ka mausam kaisa hoga",
            response="Kal halki baarish ka anuman hai.",
            intent="weather",
            language="hi",
        )

    def _token(self):
        return signing.dumps(
            {
                "session_id": self.interaction.session_id,
                "query_sha256": hashlib.sha256(
                    self.interaction.query.encode("utf-8")
                ).hexdigest(),
                "response_sha256": hashlib.sha256(
                    self.interaction.response.encode("utf-8")
                ).hexdigest(),
            },
            salt="krishimitra.chat-feedback.v1",
            compress=True,
        )

    def test_rejects_unsigned_feedback(self):
        response = self.client.post(
            "/api/chatbot/feedback/",
            {"feedback_token": "not-signed", "is_helpful": False},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.interaction.refresh_from_db()
        self.assertIsNone(self.interaction.is_helpful)

    def test_signed_feedback_updates_only_the_matching_interaction(self):
        response = self.client.post(
            "/api/chatbot/feedback/",
            {
                "feedback_token": self._token(),
                "is_helpful": True,
                "feedback_text": "Useful and clear",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.interaction.refresh_from_db()
        self.assertTrue(self.interaction.is_helpful)
        self.assertEqual(self.interaction.feedback_score, 5)
        self.assertEqual(self.interaction.feedback_text, "Useful and clear")
        self.assertEqual(response.data["learning_mode"], "reviewed_feedback")
