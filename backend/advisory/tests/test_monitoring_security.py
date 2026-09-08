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


class ProductionSecurityHeaderTests(SimpleTestCase):
    """Verify the production header branch, which CI never reaches otherwise.

    ci.yml sets DEBUG="True" for every job, and settings.py computes
    X_FRAME_OPTIONS and CSP_HEADERS inside `if not DEBUG:`. So on CI the
    ambient settings carry SAMEORIGIN and an empty CSP_HEADERS, and the
    earlier version of these tests called skipTest and passed vacuously --
    CI reported skipped=5 where a developer with DEBUG=False saw skipped=1.
    Four security assertions were silently not running on the only machine
    whose result gates a merge.

    Loading settings in a clean subprocess with DEBUG=False exercises the real
    branch and produces the same answer on both machines.
    """

    @staticmethod
    def _production_settings():
        import json, os, subprocess, sys, textwrap

        code = textwrap.dedent(
            """
            import json, os, django
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
            django.setup()
            from django.conf import settings
            print(json.dumps({
                "x_frame": settings.X_FRAME_OPTIONS,
                "csp": dict(getattr(settings, "CSP_HEADERS", {}) or {}),
                "nosniff": settings.SECURE_CONTENT_TYPE_NOSNIFF,
                "referrer": settings.SECURE_REFERRER_POLICY,
                "hsts": settings.SECURE_HSTS_SECONDS,
            }))
            """
        )
        env = dict(os.environ)
        env.update({
            "DEBUG": "False",
            "SECRET_KEY": "test-only-secret-key-not-a-real-credential-0123456789",
            "DATABASE_URL": "sqlite:///:memory:",
            "REDIS_URL": "redis://localhost:6379/0",
            "ALLOWED_HOSTS": "api.example.invalid",
            "LAUNCH_CHECK": "false",
        })
        proc = subprocess.run(
            [sys.executable, "-c", code], env=env, capture_output=True, text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        )
        if proc.returncode != 0:
            raise AssertionError(f"could not load production settings:\n{proc.stderr[-1500:]}")
        return json.loads(proc.stdout.strip().splitlines()[-1])

    def test_clickjacking_is_denied_outright(self):
        self.assertEqual(self._production_settings()["x_frame"], "DENY")

    def test_csp_is_enforcing_not_report_only(self):
        csp = self._production_settings()["csp"]
        self.assertIn("Content-Security-Policy", csp)
        self.assertNotIn("Content-Security-Policy-Report-Only", csp)

    def test_csp_forbids_eval_and_pins_object_base_and_form_targets(self):
        policy = self._production_settings()["csp"]["Content-Security-Policy"]
        self.assertNotIn("unsafe-eval", policy)
        for directive in ("object-src 'none'", "base-uri 'self'",
                          "form-action 'self'", "frame-ancestors 'none'"):
            self.assertIn(directive, policy)

    def test_permissions_policy_denies_hardware_apis(self):
        csp = self._production_settings()["csp"]
        self.assertIn("Permissions-Policy", csp)
        self.assertIn("camera=()", csp["Permissions-Policy"])

    def test_transport_and_sniffing_protections(self):
        s = self._production_settings()
        self.assertTrue(s["nosniff"])
        self.assertEqual(s["referrer"], "strict-origin-when-cross-origin")
        self.assertGreaterEqual(s["hsts"], 86400)
