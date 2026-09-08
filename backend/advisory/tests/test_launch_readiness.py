import json
from unittest.mock import patch

from django.http import JsonResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from advisory.api.monitoring_views import (
    _readiness_status,
    launch_readiness_check,
    readiness_check,
)


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

    def test_runtime_readiness_is_degraded_when_optional_farmer_services_are_down(self):
        checks = {
            "database": "ok",
            "cache": "ok",
            "redis": "not_configured",
            "phase1_ai": "offline",
            "ollama": "offline",
            "chatbot_runtime": "ok (local_ai_active=0/1, phase1_cb=closed)",
            "crop_disease_model": "degraded (needs retraining)",
        }

        self.assertEqual(_readiness_status(checks, hard_ready=True), "degraded")

    def test_runtime_readiness_is_not_ready_when_database_is_down(self):
        self.assertEqual(
            _readiness_status({"database": "unavailable"}, hard_ready=False),
            "not_ready",
        )

    def test_advisory_only_disease_mode_does_not_degrade_runtime(self):
        checks = {
            "cache": "ok",
            "redis": "ok (shared)",
            "phase1_ai": "ok (rag=True, ollama=True)",
            "ollama": "ok (model=qwen2.5:7b, present=yes)",
            "chatbot_runtime": "ok (local_ai_active=0/1, phase1_cb=closed)",
            "crop_disease_model": "ok (advisory_fallback; image classification disabled)",
            "crop_disease_candidate": "degraded (needs validation)",
        }

        self.assertEqual(_readiness_status(checks, hard_ready=True), "ready")

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
            "DATA_GOV_IN_API_KEY": "notarealkey-testfixture-only-000000000",
            "RAG_INDEX_REQUIRED": "true",
            "PHASE1_SERVICE_TOKEN": "phase1-service-token-0123456789",
            "TWILIO_ACCOUNT_SID": "ACnotarealsid-testfixture-only-00",
            "TWILIO_AUTH_TOKEN": "notarealtoken-testfixture-only-0",
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
