from pathlib import Path

from django.test import SimpleTestCase


class ChatTimeoutBehaviorTests(SimpleTestCase):
    def test_concurrent_fetch_timeout_does_not_claim_future_cancel_stops_threads(self):
        source = Path("advisory/services/chat_intelligence_service.py").read_text(encoding="utf-8")

        self.assertNotIn("fut.cancel()", source)
        self.assertIn("will finish under service HTTP timeouts", source)
