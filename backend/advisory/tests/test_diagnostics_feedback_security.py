from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from advisory.models import DiagnosticSession, ExpertVerification


class DiagnosticsFeedbackSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.owner = User.objects.create_user(username="owner", password="pass12345")
        self.other = User.objects.create_user(username="other", password="pass12345")
        self.diagnostic = DiagnosticSession.objects.create(
            user_id=str(self.owner.id),
            session_id="diag-owner",
            crop_detected="tomato",
            final_diagnosis="Early Blight",
            confidence_score=0.71,
            severity_level="Medium",
        )

    def _payload(self):
        return {
            "session_id": self.diagnostic.session_id,
            "is_correct": False,
            "correct_diagnosis": "Late Blight",
        }

    def test_anonymous_feedback_is_rejected(self):
        response = self.client.post(
            "/api/diagnostics/feedback/",
            self._payload(),
            format="json",
        )

        self.assertIn(response.status_code, (401, 403))
        self.assertFalse(ExpertVerification.objects.exists())

    def test_non_owner_feedback_is_forbidden(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.post(
            "/api/diagnostics/feedback/",
            self._payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(ExpertVerification.objects.exists())

    def test_owner_feedback_is_recorded(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/api/diagnostics/feedback/",
            self._payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        verification = ExpertVerification.objects.get(
            diagnostic_session=self.diagnostic
        )
        self.assertEqual(verification.expert_diagnosis, "Late Blight")
        self.assertFalse(verification.is_verified)
        self.assertIsNone(verification.verified_at)
        self.assertIn("pending agronomist review", verification.expert_notes)
        self.assertEqual(response.data["review_status"], "pending_agronomist_review")
        self.assertFalse(response.data["training_eligible"])
