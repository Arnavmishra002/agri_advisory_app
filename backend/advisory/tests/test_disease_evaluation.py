from django.test import SimpleTestCase

from advisory.ml.dataset_manifest import manifest_summary, validate_manifest_data
from advisory.ml.evaluate import _limit_test_samples, _per_class_metrics


class DiseaseEvaluationTests(SimpleTestCase):
    def test_per_class_metrics_include_false_negative_rate(self):
        metrics = _per_class_metrics(
            [0, 0, 1, 1],
            [0, 1, 1, 1],
            ["healthy", "rust"],
        )

        self.assertEqual(metrics["healthy"]["recall"], 0.5)
        self.assertEqual(metrics["healthy"]["false_negative_rate"], 0.5)
        self.assertEqual(metrics["rust"]["false_negative_rate"], 0.0)

    def test_dataset_manifest_requires_approved_license_and_exact_splits(self):
        manifest = {
            "schema_version": "1.0",
            "dataset_name": "test-dataset",
            "created_at": "2026-07-10",
            "sources": [{
                "name": "licensed-source",
                "source_url": "https://example.invalid/dataset",
                "license_name": "Example License",
                "license_url": "https://example.invalid/license",
                "retrieved_at": "2026-07-10",
                "crop_labels": ["wheat"],
                "disease_labels": ["rust"],
                "sample_count": 10,
                "splits": {"train": 7, "validation": 2, "test": 1},
                "usage_approved": True,
            }],
        }

        validated = validate_manifest_data(manifest)
        self.assertEqual(manifest_summary(validated)["sample_count"], 10)

        manifest["sources"][0]["usage_approved"] = False
        with self.assertRaisesRegex(ValueError, "usage_approved"):
            validate_manifest_data(manifest)
    def test_limit_test_samples_is_deterministic_and_bounded(self):
        paths = [f"img-{i}.jpg" for i in range(20)]
        labels = [i % 4 for i in range(20)]

        first_paths, first_labels = _limit_test_samples(paths, labels, max_samples=8)
        second_paths, second_labels = _limit_test_samples(paths, labels, max_samples=8)

        self.assertEqual(first_paths, second_paths)
        self.assertEqual(first_labels, second_labels)
        self.assertEqual(len(first_paths), 8)
        self.assertEqual(len(first_labels), 8)
        self.assertEqual(set(first_labels), {0, 1, 2, 3})

    def test_limit_test_samples_keeps_full_set_when_unbounded(self):
        paths = ["a.jpg", "b.jpg"]
        labels = [1, 2]

        limited_paths, limited_labels = _limit_test_samples(
            paths,
            labels,
            max_samples=None,
        )

        self.assertEqual(limited_paths, paths)
        self.assertEqual(limited_labels, labels)
