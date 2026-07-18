from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, SimpleTestCase, override_settings

from advisory.api.monitoring_views import sentry_test


class MonitoringSecurityTests(SimpleTestCase):
    @override_settings(DEBUG=False, SENTRY_DSN="https://example.invalid/1")
    @patch("sentry_sdk.capture_message")
    def test_public_user_cannot_generate_sentry_events(self, capture):
        request = RequestFactory().get("/api/health/sentry-test/")
        request.user = AnonymousUser()

        response = sentry_test(request)

        self.assertEqual(response.status_code, 403)
        capture.assert_not_called()
