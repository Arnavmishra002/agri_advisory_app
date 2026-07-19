from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase

from advisory.services.knowledge_base import KnowledgeBase
from advisory.services.chat_intelligence_service import _phase1_endpoint


class ChatTimeoutBehaviorTests(SimpleTestCase):
    def test_compose_uses_docker_specific_phase1_url(self):
        compose = Path(settings.BASE_DIR).parent.joinpath("docker-compose.yml").read_text()

        self.assertIn(
            "PHASE1_BASE_URL:           ${PHASE1_DOCKER_URL:-http://phase1:8001}",
            compose,
        )
        self.assertNotIn(
            "PHASE1_BASE_URL:           ${PHASE1_BASE_URL:-http://phase1:8001}",
            compose,
        )

    @patch.dict(
        "os.environ",
        {
            "PHASE1_BASE_URL": "http://127.0.0.1:8002",
            "PHASE1_URL": "http://127.0.0.1:8001/chat",
        },
        clear=False,
    )
    def test_canonical_phase1_base_url_wins_over_legacy_chat_url(self):
        self.assertEqual(_phase1_endpoint("/chat"), "http://127.0.0.1:8002/chat")

    def test_concurrent_fetch_timeout_does_not_claim_future_cancel_stops_threads(self):
        source = Path(
            settings.BASE_DIR,
            "advisory/services/chat_intelligence_service.py",
        ).read_text(encoding="utf-8")

        self.assertNotIn("fut.cancel()", source)
        self.assertIn("will finish under service HTTP timeouts", source)

    @patch.object(KnowledgeBase, "_ask_local_llm")
    @patch.object(KnowledgeBase, "_kb_lookup", return_value=None)
    def test_static_kb_mode_does_not_call_ollama(self, _lookup, ask_local_llm):
        result = KnowledgeBase().answer(
            "novel crop question",
            language="en",
            allow_local_llm=False,
        )

        self.assertIsNone(result["answer"])
        self.assertEqual(result["source"], "escalate_to_gemini")
        ask_local_llm.assert_not_called()
