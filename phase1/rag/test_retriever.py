import os
import unittest
from unittest.mock import patch

from . import retriever


class RetrieverRankingTests(unittest.TestCase):
    def test_metadata_alignment_beats_noisy_vector_match(self):
        candidates = [
            {
                "text": "Banana spacing and general fruit crop notes.",
                "source_file": "horticulture_fruits.txt",
                "category": "crops",
                "crops": "banana",
                "topics": "seed",
                "score": 0.70,
            },
            {
                "text": "Groundnut tikka disease management and leaf spot control.",
                "source_file": "groundnut_millets.txt",
                "category": "crops",
                "crops": "groundnut",
                "topics": "disease",
                "score": 0.58,
            },
        ]

        ranked = retriever._rerank(candidates, "groundnut tikka disease management", final_k=2)

        self.assertEqual(ranked[0]["source_file"], "groundnut_millets.txt")
        self.assertGreater(ranked[0]["score"], ranked[1]["score"])

    def test_relevance_threshold_filters_weak_matches(self):
        results = [{"score": 0.49}, {"score": 0.51}]

        with patch.dict(os.environ, {"RAG_MIN_RELEVANCE": "0.50"}):
            filtered = retriever._apply_relevance_threshold(results, retriever._min_relevance())

        self.assertEqual(filtered, [{"score": 0.51}])

    def test_protected_cultivation_topic_outranks_generic_subsidy(self):
        candidates = [
            {
                "text": "FPO mandi export subsidy registration notes.",
                "source_file": "fpo_mandi_export_guide.txt",
                "category": "schemes",
                "topics": "scheme|market",
                "score": 0.69,
            },
            {
                "text": "Polyhouse greenhouse tomato cucumber protected cultivation subsidy.",
                "source_file": "polyhouse_greenhouse_farming.txt",
                "category": "crops",
                "topics": "scheme|protected_cultivation",
                "score": 0.64,
            },
        ]

        ranked = retriever._rerank(candidates, "polyhouse tomato cucumber subsidy", final_k=2)

        self.assertEqual(ranked[0]["source_file"], "polyhouse_greenhouse_farming.txt")


if __name__ == "__main__":
    unittest.main()
