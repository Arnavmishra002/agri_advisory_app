import json
from pathlib import Path

from django.test import SimpleTestCase

from advisory.services.chat_intelligence_service import ChatIntelligenceService
from advisory.services.language_service import detect_query_language


EVAL_PATH = Path(__file__).resolve().parents[1] / "evals" / "farmer_beta_v1.json"


class FarmerBetaEvaluationTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dataset = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
        cls.service = ChatIntelligenceService()

    def test_eval_manifest_is_versioned_and_launch_sized(self):
        self.assertEqual(self.dataset["schema_version"], "1.0")
        self.assertEqual(set(self.dataset["launch_languages"]), {"hi", "hinglish", "en"})
        self.assertGreaterEqual(len(self.dataset["cases"]), 24)
        self.assertEqual(
            len({case["id"] for case in self.dataset["cases"]}),
            len(self.dataset["cases"]),
        )

    def test_launch_queries_match_expected_intent_and_language(self):
        for case in self.dataset["cases"]:
            with self.subTest(case=case["id"]):
                intent, _ = self.service.classify_query(case["query"])
                language = detect_query_language(case["query"], fallback="hi")
                self.assertEqual(intent, case["intent"])
                self.assertEqual(language, case["language"])

    def test_eval_queries_do_not_embed_chemical_doses_or_prices(self):
        forbidden = ("ml/l", "g/l", "kg/ha", "₹", "rs.", "rupees")
        for case in self.dataset["cases"]:
            with self.subTest(case=case["id"]):
                query = case["query"].lower()
                self.assertFalse(any(token in query for token in forbidden))
