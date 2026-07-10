import json
from unittest.mock import patch

from django.http import JsonResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from advisory.api.monitoring_views import launch_readiness_check


def _runtime_readiness(*, healthy: bool) -> JsonResponse:
    checks = {
        "database": "ok",
        "cache": "ok",
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
        self.assertIn("disease_model_unverified", codes)
        self.assertIn("sentry_missing", codes)

    @override_settings(
        DEBUG=False,
        RATE_LIMIT_ENABLED=True,
        SENTRY_DSN="https://public@example.invalid/1",
    )
    @patch.dict(
        "os.environ",
        {
            "LAUNCH_CHECK": "true",
            "REDIS_URL": "redis://redis:6379/0",
            "DATA_GOV_IN_API_KEY": "configured-key",
        },
        clear=True,
    )
    @patch("advisory.api.monitoring_views.readiness_check")
    def test_strict_launch_gate_is_ready_when_requirements_pass(self, readiness):
        readiness.return_value = _runtime_readiness(healthy=True)

        response = launch_readiness_check(self.request)
        body = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "ready")
        self.assertEqual(body["blockers"], [])
