"""The disease model must serve on a host without TensorFlow.

Production runs on a 512 MB free-tier instance that installs
``backend/requirements.txt`` only -- TensorFlow (~2 GB) is not there and would
not fit. The training run therefore exports a float16 ``.tflite`` alongside the
``.keras`` file, and the predictor must load it through ``tflite-runtime``.

Without this path a trained model would still answer "model unavailable" to
every farmer, so these tests guard the whole feature.

The interpreter is stubbed with the exact ``tflite_runtime`` API surface
(allocate_tensors / get_input_details / get_output_details / set_tensor /
invoke / get_tensor) so the test stays fast and does not need a real model
file, while still exercising our loading, preprocessing, and gating code.
"""

from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
from django.test import SimpleTestCase

from advisory.ml import inference as inference_module
from advisory.ml.inference import CropDiseasePredictor

LABELS = ["apple__healthy", "tomato__late_blight", "unknown__unknown"]


class _StubInterpreter:
    """Mirrors the tflite_runtime.Interpreter API used by the predictor."""

    def __init__(self, probabilities):
        self._probabilities = np.array([probabilities], dtype=np.float32)
        self.received = None

    def allocate_tensors(self):
        return None

    def get_input_details(self):
        return [{"index": 0, "dtype": np.float32, "shape": np.array([1, 224, 224, 3])}]

    def get_output_details(self):
        return [{"index": 1, "dtype": np.float32, "shape": np.array([1, len(LABELS)])}]

    def set_tensor(self, index, value):
        self.received = value

    def invoke(self):
        return None

    def get_tensor(self, index):
        return self._probabilities


def _leaf_image_bytes() -> bytes:
    """A green frame so the pre-CNN plant validator does not reject it."""
    from PIL import Image

    arr = np.zeros((256, 256, 3), dtype=np.uint8)
    arr[:, :, 0] = 60
    arr[:, :, 1] = 190
    arr[:, :, 2] = 50
    buffer = io.BytesIO()
    Image.fromarray(arr).save(buffer, format="JPEG")
    return buffer.getvalue()


class TFLiteServingTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model_dir = Path(tempfile.mkdtemp()) / "crop_disease"
        cls.model_dir.mkdir(parents=True)
        (cls.model_dir / "class_labels.json").write_text(
            json.dumps(
                {
                    "labels": LABELS,
                    "unknown_label": "unknown__unknown",
                    "format": "crop__disease",
                }
            ),
            encoding="utf-8",
        )
        # Metrics that clear the production promotion gate.
        (cls.model_dir / "metrics.json").write_text(
            json.dumps(
                {
                    "model": "EfficientNet-B3",
                    "architecture": "efficientnetb3",
                    "input_size": [224, 224],
                    "preprocess": "efficientnet",
                    "class_count": len(LABELS),
                    "best_val_accuracy": 0.95,
                    "best_val_top3_accuracy": 0.99,
                    "evaluation_accuracy": 0.94,
                    "evaluation_top3_accuracy": 0.99,
                    "evaluation_limited": False,
                    "all_classes_evaluated": True,
                    "non_plant_test_samples": 695,
                    "dataset_manifest": {"usage_approved": True},
                }
            ),
            encoding="utf-8",
        )
        (cls.model_dir / "efficientnetb3_crop_disease.tflite").write_bytes(b"TFL3-stub")
        cls.leaf = _leaf_image_bytes()

    def _predictor(self, probabilities):
        stub = _StubInterpreter(probabilities)
        with patch.object(
            inference_module.CropDiseasePredictor,
            "_load_tflite_interpreter",
            staticmethod(lambda _path: stub),
        ):
            predictor = CropDiseasePredictor(model_dir=self.model_dir)
        return predictor, stub

    def test_loads_tflite_backend_and_passes_promotion_gate(self):
        predictor, _ = self._predictor([0.02, 0.95, 0.03])
        self.assertEqual(predictor.backend, "tflite")
        self.assertTrue(predictor.is_ready)
        self.assertTrue(predictor.is_production_ready)
        self.assertEqual(predictor._input_size(), (224, 224))

    def test_confident_prediction_is_returned(self):
        predictor, stub = self._predictor([0.02, 0.95, 0.03])
        with self.settings():
            with patch.dict("os.environ", {"DISEASE_CLASSIFICATION_ENABLED": "true"}):
                result = predictor.predict(self.leaf)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["disease_name"], "Late Blight")
        self.assertGreater(result["confidence"], 0.9)
        # The interpreter must receive a correctly shaped float32 batch.
        self.assertEqual(stub.received.dtype, np.float32)
        self.assertEqual(tuple(stub.received.shape), (1, 224, 224, 3))

    def test_non_plant_class_is_refused(self):
        """A photo the model calls unknown must never surface as a disease."""
        predictor, _ = self._predictor([0.05, 0.05, 0.90])
        with patch.dict("os.environ", {"DISEASE_CLASSIFICATION_ENABLED": "true"}):
            result = predictor.predict(self.leaf)
        self.assertEqual(result["status"], "low_confidence")
        self.assertIsNone(result["disease_name"])

    def test_low_confidence_is_refused(self):
        predictor, _ = self._predictor([0.40, 0.35, 0.25])
        with patch.dict("os.environ", {"DISEASE_CLASSIFICATION_ENABLED": "true"}):
            result = predictor.predict(self.leaf)
        self.assertEqual(result["status"], "low_confidence")
        self.assertIsNone(result["disease_name"])

    def test_model_below_gate_is_not_served(self):
        """Weak metrics must yield model_unverified, not a guess."""
        weak_dir = Path(tempfile.mkdtemp()) / "crop_disease"
        weak_dir.mkdir(parents=True)
        (weak_dir / "class_labels.json").write_text(
            json.dumps({"labels": LABELS, "unknown_label": "unknown__unknown"}),
            encoding="utf-8",
        )
        (weak_dir / "metrics.json").write_text(
            json.dumps(
                {
                    "input_size": [224, 224],
                    "preprocess": "efficientnet",
                    "best_val_accuracy": 0.31,
                    "best_val_top3_accuracy": 0.52,
                }
            ),
            encoding="utf-8",
        )
        (weak_dir / "efficientnetb3_crop_disease.tflite").write_bytes(b"TFL3-stub")
        stub = _StubInterpreter([0.1, 0.8, 0.1])
        with patch.object(
            inference_module.CropDiseasePredictor,
            "_load_tflite_interpreter",
            staticmethod(lambda _path: stub),
        ):
            predictor = CropDiseasePredictor(model_dir=weak_dir)
        with patch.dict("os.environ", {"DISEASE_CLASSIFICATION_ENABLED": "true"}):
            result = predictor.predict(self.leaf)
        self.assertEqual(result["status"], "model_unverified")
        self.assertIsNone(result["disease_name"])
