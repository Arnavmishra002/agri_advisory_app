import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from django.test import SimpleTestCase

from advisory.ml.dataset_loader import build_splits, discover_images
from advisory.ml.augmentation import _load_image_with_pillow
from advisory.ml.dataset_manifest import (
    ensure_training_approved,
    manifest_summary,
    validate_manifest_data,
)
from advisory.ml.evaluate import (
    _align_test_labels,
    _limit_test_samples,
    _per_class_metrics,
    _top_k_accuracy,
)
from advisory.ml.model_metadata import load_model_metadata, quality_label
from advisory.ml.model_builder import configure_fine_tuning


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

    def test_dataset_manifest_separates_structure_from_usage_approval(self):
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
        validated = validate_manifest_data(manifest)
        self.assertFalse(manifest_summary(validated)["usage_approved"])
        with self.assertRaisesRegex(ValueError, "not approved"):
            ensure_training_approved(validated)

    def test_dataset_aliases_do_not_duplicate_physical_images(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source" / "Tomato___healthy"
            source.mkdir(parents=True)
            (source / "leaf.jpg").write_bytes(b"\xff\xd8\xff\xe0test-image")
            raw = root / "dataset" / "raw"
            raw.mkdir(parents=True)
            os.symlink(source.parent, raw / "plantvillage")
            try:
                os.symlink(source.parent, raw / "PlantVillage")
            except FileExistsError:
                # Case-insensitive filesystems resolve both aliases to one entry.
                pass

            samples = discover_images(root / "dataset")

        self.assertEqual(len(samples), 1)

    def test_unknown_class_is_not_added_without_negative_samples(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            class_dir = root / "Tomato___healthy"
            class_dir.mkdir(parents=True)
            for index in range(4):
                (class_dir / f"leaf-{index}.jpg").write_bytes(
                    b"\xff\xd8\xff\xe0test-image"
                )

            dataset = build_splits(root)

        self.assertEqual(dataset.class_names, ["tomato__healthy"])

    def test_capped_training_split_cannot_leak_into_full_test_split(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for class_name in ("Tomato___healthy", "Tomato___Late_blight"):
                class_dir = root / class_name
                class_dir.mkdir(parents=True)
                for index in range(20):
                    (class_dir / f"leaf-{index}.jpg").write_bytes(
                        b"\xff\xd8\xff\xe0test-image"
                    )

            full = build_splits(root)
            capped = build_splits(root, max_samples_per_class=10)

        self.assertTrue(set(capped.train.paths).issubset(full.train.paths))
        self.assertTrue(set(capped.val.paths).issubset(full.val.paths))
        self.assertTrue(set(capped.test.paths).issubset(full.test.paths))
        self.assertTrue(set(capped.train.paths).isdisjoint(full.test.paths))

    def test_training_image_decoder_handles_tensor_scalars_and_rejects_corruption(self):
        import tensorflow as tf
        from PIL import Image

        with TemporaryDirectory() as directory:
            image_path = Path(directory) / "leaf.png"
            Image.new("RGB", (12, 10), color=(20, 80, 140)).save(image_path)

            pixels, label = _load_image_with_pillow(
                tf.constant(str(image_path)),
                tf.constant(7),
                (8, 6),
            )

            self.assertEqual(pixels.shape, (8, 6, 3))
            self.assertGreater(float(pixels.mean()), 0.0)
            self.assertEqual(int(label), 7)

            corrupt_path = Path(directory) / "corrupt.jpg"
            corrupt_path.write_bytes(b"not-an-image")
            with self.assertRaisesRegex(ValueError, "Unable to decode training image"):
                _load_image_with_pillow(corrupt_path, 1, (8, 6))

    def test_high_validation_score_alone_cannot_promote_model(self):
        self.assertEqual(quality_label(0.90, 0.98), "needs_validation")
        self.assertEqual(
            quality_label(
                0.90,
                0.98,
                evaluation_accuracy=0.88,
                evaluation_top3_accuracy=0.96,
                manifest_approved=True,
                non_plant_test_samples=50,
                evaluation_limited=False,
                all_classes_evaluated=True,
            ),
            "production_candidate",
        )

    def test_persisted_quality_cannot_override_current_safety_policy(self):
        with TemporaryDirectory() as directory:
            model_dir = Path(directory)
            (model_dir / "metrics.json").write_text(
                json.dumps(
                    {
                        "quality": "production_candidate",
                        "best_val_accuracy": 0.10,
                        "best_val_top3_accuracy": 0.20,
                    }
                ),
                encoding="utf-8",
            )

            metadata = load_model_metadata(model_dir)

        self.assertEqual(metadata["quality"], "needs_retraining")

    def test_evaluation_maps_dataset_labels_to_persisted_model_order(self):
        dataset = SimpleNamespace(
            class_names=["tomato__healthy", "tomato__late_blight"],
            test=SimpleNamespace(paths=["healthy.jpg", "blight.jpg"], labels=[0, 1]),
        )

        paths, labels, missing, unsupported = _align_test_labels(
            dataset,
            ["tomato__late_blight", "tomato__healthy"],
        )

        self.assertEqual(paths, ["healthy.jpg", "blight.jpg"])
        self.assertEqual(labels, [1, 0])
        self.assertEqual(missing, [])
        self.assertEqual(unsupported, [])

    def test_evaluation_rejects_model_label_without_test_samples(self):
        dataset = SimpleNamespace(
            class_names=["tomato__healthy"],
            test=SimpleNamespace(paths=["healthy.jpg"], labels=[0]),
        )

        with self.assertRaisesRegex(ValueError, "without test samples"):
            _align_test_labels(
                dataset,
                ["tomato__healthy", "unknown__unknown"],
            )

    def test_top3_accuracy_uses_model_probabilities(self):
        score = _top_k_accuracy(
            [0, 3],
            [
                [0.4, 0.3, 0.2, 0.1],
                [0.5, 0.25, 0.2, 0.05],
            ],
            k=3,
        )

        self.assertEqual(score, 0.5)

    def test_fine_tuning_unfreezes_only_requested_non_batchnorm_layers(self):
        import tensorflow as tf

        backbone = tf.keras.Sequential(
            [
                tf.keras.Input(shape=(4,)),
                tf.keras.layers.Dense(4, name="early_dense"),
                tf.keras.layers.BatchNormalization(name="stable_batchnorm"),
                tf.keras.layers.Dense(4, name="late_dense"),
            ],
            name="efficientnet_test",
        )
        inputs = tf.keras.Input(shape=(4,))
        model = tf.keras.Model(inputs, backbone(inputs))
        backbone.trainable = False

        selected = configure_fine_tuning(model, trainable_layers=1)

        self.assertEqual(selected, 1)
        self.assertFalse(backbone.get_layer("early_dense").trainable)
        self.assertFalse(backbone.get_layer("stable_batchnorm").trainable)
        self.assertTrue(backbone.get_layer("late_dense").trainable)

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
