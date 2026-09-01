import os
import unittest
from unittest.mock import Mock
from unittest.mock import patch

from . import retriever


class RetrieverRankingTests(unittest.TestCase):
    def test_query_taxonomy_covers_every_generated_crop_profile(self):
        self.assertEqual(len(retriever._QUERY_CROP_TERMS), 202)
        self.assertIn("रामबूटान", retriever._QUERY_CROP_TERMS["rambutan"])
        self.assertIn("अश्वगंधा", retriever._QUERY_CROP_TERMS["ashwagandha"])

    def test_query_crop_detection_does_not_treat_prices_as_rice(self):
        self.assertNotIn(
            "rice",
            retriever._extract_tags("show verified mandi prices", retriever._QUERY_CROP_TERMS),
        )

    def test_romanised_hindi_query_is_augmented_for_english_knowledge_base(self):
        augmented = retriever._augment("gehu ki buwai ka sahi samay")

        self.assertIn("wheat", augmented)
        self.assertIn("sowing", augmented)
        self.assertIn("time", augmented)

    def test_multilingual_crop_aliases_are_augmented_to_canonical_ids(self):
        augmented = retriever._augment("बेर किन्नू नींबू बागवानी")

        self.assertIn("ber", augmented)
        self.assertIn("kinnow", augmented)
        self.assertIn("lemon", augmented)

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

    def test_extended_crop_metadata_outranks_unrelated_high_vector_match(self):
        candidates = [
            {
                "text": "Banana climate and tropical fruit production notes.",
                "source_file": "horticulture_fruits.txt",
                "category": "crops",
                "crops": "banana",
                "topics": "seed",
                "score": 0.72,
            },
            {
                "text": "CROP_ID: rambutan. Rambutan climate fit, soil pH and suitable states.",
                "source_file": "indian_crop_profiles_202.txt",
                "category": "crops",
                "crops": "rambutan",
                "topics": "soil|weather",
                "score": 0.59,
            },
        ]

        ranked = retriever._rerank(candidates, "rambutan climate and soil", final_k=2)

        self.assertEqual(ranked[0]["source_file"], "indian_crop_profiles_202.txt")

    def test_relevance_threshold_filters_weak_matches(self):
        results = [{"score": 0.49}, {"score": 0.51}]

        with patch.dict(os.environ, {"RAG_MIN_RELEVANCE": "0.50"}):
            filtered = retriever._apply_relevance_threshold(results, retriever._min_relevance())

        self.assertEqual(filtered, [{"score": 0.51}])

    def test_keyword_fallback_retrieves_grounded_chunks_without_embeddings(self):
        collection = Mock()
        collection.get.return_value = {
            "documents": [
                "Wheat sowing is recommended in November in North India.",
                "Banana needs a warm climate and regular irrigation.",
            ],
            "metadatas": [
                {"source_file": "wheat.txt", "category": "crops", "crops": "wheat", "topics": "seed"},
                {"source_file": "banana.txt", "category": "crops", "crops": "banana", "topics": "irrigation"},
            ],
        }

        with patch.object(retriever, "_get_collection", return_value=collection):
            results = retriever._keyword_search("wheat sowing", 5, None)

        self.assertEqual(results[0]["source_file"], "wheat.txt")

    def test_hybrid_retrieval_keeps_exact_crop_source_over_generic_vector_match(self):
        collection = Mock()
        collection.count.return_value = 2

        vector_candidate = {
            "text": "General crop calendar and irrigation notes.",
            "source_file": "generic_calendar.txt",
            "category": "crops",
            "crops": "",
            "topics": "weather",
            "score": 0.92,
        }
        keyword_candidate = {
            "text": "ICAR wheat sowing time is 1-15 November in North India.",
            "source_file": "wheat_icar.txt",
            "category": "crops",
            "crops": "wheat",
            "topics": "seed",
            "chunk_index": 0,
            "score": 0.50,
        }

        with patch.object(retriever, "_get_collection", return_value=collection), \
             patch.object(retriever, "_embed", return_value=(0.1,)), \
             patch.object(retriever, "_vector_search", return_value=[vector_candidate]), \
             patch.object(retriever, "_keyword_search", return_value=[keyword_candidate]):
            results = retriever.retrieve_with_sources("wheat sowing time", k=1)

        self.assertEqual(results[0]["source_file"], "wheat_icar.txt")

    def test_source_crop_alignment_rejects_cross_crop_filename_metadata_leak(self):
        ranked = retriever._rerank(
            [
                {
                    "text": "Rice notes that mention wheat sowing.",
                    "source_file": "rice_varieties_zone_wise.txt",
                    "category": "crops",
                    "crops": "wheat",
                    "topics": "seed",
                    "score": 0.90,
                },
                {
                    "text": "ICAR wheat package: sowing is 1-15 November.",
                    "source_file": "wheat_icar.txt",
                    "category": "crops",
                    "crops": "wheat",
                    "topics": "seed",
                    "score": 0.70,
                },
            ],
            "wheat sowing time",
            final_k=2,
        )

        self.assertEqual(ranked[0]["source_file"], "wheat_icar.txt")

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

    def test_is_available_degrades_when_chroma_count_fails(self):
        broken_collection = Mock()
        broken_collection.count.side_effect = RuntimeError("corrupt chroma metadata")

        with patch.object(retriever, "_get_collection", return_value=broken_collection):
            self.assertFalse(retriever.is_available())


if __name__ == "__main__":
    unittest.main()
