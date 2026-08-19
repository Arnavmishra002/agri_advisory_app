from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

from phase1.main import app


class Phase1ServiceSecurityTests(TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch.dict(
        "os.environ",
        {"DEBUG": "false", "PHASE1_SERVICE_TOKEN": "service-secret"},
        clear=False,
    )
    def test_rag_endpoint_requires_bearer_token(self):
        missing = self.client.get("/rag/status")
        wrong = self.client.get(
            "/rag/status", headers={"Authorization": "Bearer wrong"}
        )
        accepted = self.client.get(
            "/rag/status", headers={"Authorization": "Bearer service-secret"}
        )

        self.assertEqual(missing.status_code, 401)
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(accepted.status_code, 200)

    @patch.dict(
        "os.environ",
        {"DEBUG": "false", "PHASE1_SERVICE_TOKEN": ""},
        clear=False,
    )
    def test_production_requests_fail_closed_without_service_token(self):
        response = self.client.get("/rag/status")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error_code"], "SERVICE_AUTH_NOT_CONFIGURED")

    @patch.dict("os.environ", {"DEBUG": "false"}, clear=False)
    def test_health_probe_remains_public_and_minimal(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("service_token", str(response.json()).lower())
