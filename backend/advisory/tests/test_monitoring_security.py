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


class SecurityHeaderPolicyTests(SimpleTestCase):
    """CSP was Report-Only, and Permissions-Policy was absent entirely.

    The original reason for Report-Only -- an enforced policy blocking a CDN
    stylesheet -- no longer applies now that every vendor asset is self-hosted.
    """

    def test_csp_is_enforcing_not_report_only_by_default(self):
        from django.conf import settings
        headers = getattr(settings, "CSP_HEADERS", {}) or {}
        if not headers:
            self.skipTest("CSP_HEADERS empty under DEBUG")
        self.assertIn("Content-Security-Policy", headers)
        self.assertNotIn("Content-Security-Policy-Report-Only", headers)

    def test_policy_does_not_permit_eval(self):
        from django.conf import settings
        headers = getattr(settings, "CSP_HEADERS", {}) or {}
        if not headers:
            self.skipTest("CSP_HEADERS empty under DEBUG")
        self.assertNotIn("unsafe-eval", headers["Content-Security-Policy"])

    def test_policy_pins_object_base_and_form_targets(self):
        from django.conf import settings
        headers = getattr(settings, "CSP_HEADERS", {}) or {}
        if not headers:
            self.skipTest("CSP_HEADERS empty under DEBUG")
        policy = headers["Content-Security-Policy"]
        for directive in ("object-src 'none'", "base-uri 'self'",
                          "form-action 'self'", "frame-ancestors 'none'"):
            self.assertIn(directive, policy)

    def test_permissions_policy_is_present(self):
        from django.conf import settings
        headers = getattr(settings, "CSP_HEADERS", {}) or {}
        if not headers:
            self.skipTest("CSP_HEADERS empty under DEBUG")
        self.assertIn("Permissions-Policy", headers)
        self.assertIn("camera=()", headers["Permissions-Policy"])
