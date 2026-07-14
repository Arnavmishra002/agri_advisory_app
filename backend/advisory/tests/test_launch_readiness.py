import json
from unittest.mock import patch

from django.http import JsonResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from advisory.api.monitoring_views import launch_readiness_check, readiness_check


def _runtime_readiness(*, healthy: bool) -> JsonResponse:
    checks = {
        "database": "ok",
        "database_backend": "postgresql",
        "cache": "ok",
        "redis": "ok (shared)" if healthy else "unavailable",
        "phase1_ai": "ok (rag=True, ollama=True)" if healthy else "offline",
        "ollama": (
            "ok (model=krishimitra-llm, present=yes)"
            if healthy
            else "offline"
        ),
        "crop_disease_model": (
            "ok (EfficientNet-B3 ready)" if healthy else "degraded (needs retraining)"
        ),
    }
    return JsonResponse({"status": "ready", "checks": checks})


class LaunchReadinessTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().get("/api/health/launch-readiness/")

    @override_settings(DEBUG=True, RATE_LIMIT_ENABLED=False, SENTRY_DSN="")
    @patch.dict("os.environ", {"LAUNCH_CHECK": "false"}, clear=True)
    @patch("advisory.api.monitoring_views.readiness_check")
    def test_development_readiness_reports_degraded_without_failing(self, readiness):
        readiness.return_value = _runtime_readiness(healthy=False)

        response = launch_readiness_check(self.request)
        body = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "degraded")

    @override_settings(DEBUG=False, RATE_LIMIT_ENABLED=True, SENTRY_DSN="")
    @patch.dict("os.environ", {"LAUNCH_CHECK": "true"}, clear=True)
    @patch("advisory.api.monitoring_views.readiness_check")
    def test_strict_launch_gate_returns_503_with_actionable_blockers(self, readiness):
        readiness.return_value = _runtime_readiness(healthy=False)

        response = launch_readiness_check(self.request)
        body = json.loads(response.content)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(body["status"], "blocked_for_launch")
        codes = {item["code"] for item in body["blockers"]}
        self.assertIn("redis_required", codes)
        self.assertIn("mandi_api_key_missing", codes)
        self.assertIn("phase1_offline", codes)
        self.assertIn("ollama_model_unavailable", codes)
        self.assertNotIn("disease_model_unverified", codes)
        self.assertIn("phase1_service_token_missing", codes)
        self.assertIn("rag_index_not_required", codes)
        self.assertIn("otp_provider_unconfigured", codes)
        self.assertIn("sentry_missing", codes)

    @override_settings(
        DEBUG=False,
        RATE_LIMIT_ENABLED=True,
        SENTRY_DSN="https://public@example.invalid/1",
        STRICT_PRODUCTION_CONFIG=True,
        CORS_ALLOW_ALL_ORIGINS=False,
        ALLOWED_HOSTS=["api.krishimitra.example"],
    )
    @patch.dict(
        "os.environ",
        {
            "LAUNCH_CHECK": "true",
            "REDIS_URL": "redis://redis:6379/0",
            "DATA_GOV_IN_API_KEY": "configured-key",
            "RAG_INDEX_REQUIRED": "true",
            "PHASE1_SERVICE_TOKEN": "phase1-secret",
            "TWILIO_ACCOUNT_SID": "AC-test",
            "TWILIO_AUTH_TOKEN": "twilio-secret",
            "TWILIO_FROM_NUMBER": "+911234567890",
            "STRICT_PRODUCTION_CONFIG": "true",
        },
        clear=True,
    )
    @patch("advisory.api.monitoring_views.readiness_check")
    def test_strict_launch_gate_is_ready_when_requirements_pass(self, readiness):
        readiness.return_value = _runtime_readiness(healthy=True)

        response = launch_readiness_check(self.request)
        body = json.loads(response.content)

        self.assertEqual(response.status_code, 200, body)
        self.assertEqual(body["status"], "ready")
        self.assertEqual(body["blockers"], [])
        self.assertEqual(body["checks"]["disease_mode"], "advisory_fallback")

    @patch("advisory.api.monitoring_views.connection")
    @patch("urllib.request.urlopen", side_effect=OSError("upstream secret"))
    def test_readiness_does_not_expose_internal_exception_text(self, _urlopen, connection_mock):
        connection_mock.cursor.side_effect = RuntimeError("db secret path")
        response = readiness_check(RequestFactory().get("/api/health/readiness/"))
        body = json.loads(response.content)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(body["checks"]["database"], "unavailable")
        rendered = json.dumps(body)
        self.assertNotIn("db secret path", rendered)
        self.assertNotIn("upstream secret", rendered)
