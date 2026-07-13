from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.cache import caches
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIClient

from advisory.api.throttling import ConfigurableRateThrottle
from advisory.api.validation import decode_base64_image, validate_image_bytes
from advisory.api.serializers import (
    DiagnosticMultipartPredictInputSerializer,
    TwilioWebhookInputSerializer,
    WhatsAppWebhookInputSerializer,
)
from advisory.api.viewsets.misc import _owned_advisory_audio_session
from advisory.rate_limiters import ExponentialBackoff


class ImageValidationTests(SimpleTestCase):
    def test_invalid_base64_is_rejected_before_inference(self):
        image, error = decode_base64_image("not-base64")

        self.assertIsNone(image)
        self.assertEqual(error.status_code, 400)
        self.assertEqual(error.data["error_code"], "INVALID_IMAGE_ENCODING")

    def test_content_type_must_match_decoded_format(self):
        from PIL import Image

        output = BytesIO()
        Image.new("RGB", (64, 64), (40, 160, 40)).save(output, format="PNG")
        image, error = validate_image_bytes(output.getvalue(), content_type="image/jpeg")

        self.assertIsNone(image)
        self.assertEqual(error.status_code, 415)
        self.assertEqual(error.data["error_code"], "INVALID_CONTENT_TYPE")


class RequestThrottleTests(SimpleTestCase):
    @override_settings(
        RATE_LIMIT_ENABLED=True,
        RATE_LIMIT_WHITELIST=[],
        RATE_LIMIT_PUBLIC_RPM=1,
        RATE_LIMIT_PUBLIC_RPH=1,
        RATE_LIMIT_PUBLIC_RPD=1,
        RATE_LIMIT_FAIL_OPEN=False,
    )
    def test_public_requests_are_limited_per_ip(self):
        caches["rate_limit"].clear()
        request = SimpleNamespace(
            path="/api/crops/",
            META={"REMOTE_ADDR": "203.0.113.10"},
            user=AnonymousUser(),
            data={},
        )

        throttle = ConfigurableRateThrottle()
        self.assertTrue(throttle.allow_request(request, None))
        self.assertFalse(throttle.allow_request(request, None))
        self.assertGreaterEqual(throttle.wait(), 1)


class StrictRequestSchemaTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

    def test_location_search_rejects_unknown_and_invalid_query_fields(self):
        response = self.client.get("/api/locations/search/", {"q": "Lucknow", "limit": "0"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("limit", response.data["errors"])

        response = self.client.get("/api/locations/search/", {"q": "Lucknow", "unexpected": "x"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unexpected field", str(response.data["errors"]))

    def test_eligibility_rejects_unknown_profile_fields(self):
        response = self.client.post(
            "/api/schemes/eligibility/",
            {"farmer_profile": {"state": "Uttar Pradesh", "secret": "ignored"}},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unexpected field", str(response.data["errors"]))

    def test_jwt_refresh_rejects_unknown_fields(self):
        response = self.client.post(
            "/api/token/refresh/",
            {"refresh": "not-a-token", "unexpected": "x"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unexpected field", str(response.data))

    def test_multipart_diagnostics_accepts_mobile_session_id(self):
        payload = {
            "image": SimpleUploadedFile("leaf.png", b"png-placeholder", content_type="image/png"),
            "session_id": "mobile-diagnostic-session",
        }
        serializer = DiagnosticMultipartPredictInputSerializer(data=payload)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["session_id"], "mobile-diagnostic-session")

    def test_provider_webhook_schemas_reject_unknown_fields(self):
        twilio = TwilioWebhookInputSerializer(data={"From": "+919876543210", "Body": "hello", "unexpected": "x"})
        self.assertFalse(twilio.is_valid())

        whatsapp = WhatsAppWebhookInputSerializer(
            data={"object": "whatsapp_business_account", "entry": [], "unexpected": "x"}
        )
        self.assertFalse(whatsapp.is_valid())

    def test_whatsapp_message_schema_bounds_nested_fields(self):
        serializer = WhatsAppWebhookInputSerializer(
            data={
                "object": "whatsapp_business_account",
                "entry": [{
                    "id": "business",
                    "changes": [{
                        "field": "messages",
                        "value": {
                            "messages": [{
                                "from": "919876543210",
                                "type": "text",
                                "text": {"body": "hello"},
                            }],
                        },
                    }],
                }],
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_tts_history_key_is_not_client_supplied(self):
        anonymous = SimpleNamespace(user=AnonymousUser())
        self.assertEqual(_owned_advisory_audio_session(anonymous), "")

        authenticated = SimpleNamespace(
            user=SimpleNamespace(is_authenticated=True, pk=42)
        )
        self.assertEqual(_owned_advisory_audio_session(authenticated), "user:42")


class AuthenticationBackoffTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        get_user_model().objects.create_user(
            username="backoff-user",
            password="correct-password",
        )
        caches["rate_limit"].clear()

    def test_repeated_failed_login_is_delayed(self):
        backoff = ExponentialBackoff(
            "test-login",
            threshold=1,
            base_seconds=30,
            max_seconds=30,
            window_seconds=300,
        )
        with patch("core.auth_views.login_backoff", backoff):
            first = self.client.post(
                "/api/token/",
                {"username": "backoff-user", "password": "wrong-password"},
                format="json",
            )
            second = self.client.post(
                "/api/token/",
                {"username": "backoff-user", "password": "wrong-password"},
                format="json",
            )

        self.assertIn(first.status_code, (400, 401))
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second.data["error_code"], "AUTH_BACKOFF")
