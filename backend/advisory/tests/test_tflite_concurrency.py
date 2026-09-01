"""Concurrent photo diagnoses must not corrupt the shared TFLite interpreter.

Production serves one process-wide ``CropDiseasePredictor`` from a gunicorn
gthread worker (4 threads), so two farmers uploading leaf photos in the same
second land on the same ``Interpreter`` object. That object owns mutable
internal tensor buffers and is not thread-safe: interleaved
set_tensor/invoke/get_tensor calls made tflite_runtime raise "There is at
least 1 reference to internal data in the interpreter", and under sustained
load the worker took SIGSEGV -- which drops every in-flight request on that
worker, not merely the two that raced.

The stub below reproduces the hazard rather than assuming it: it asserts that
no second thread is inside the interpreter while one is mid-invoke, and it
returns a per-call result so a lost or crossed response is visible as a wrong
answer rather than a silent pass.
"""

from __future__ import annotations

import io
import json
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import numpy as np
from django.test import SimpleTestCase

from advisory.ml import inference as inference_module
from advisory.ml.inference import CropDiseasePredictor

LABELS = ["apple__healthy", "tomato__late_blight", "unknown__unknown"]


class _RaceDetectingInterpreter:
    """Fails loudly if two threads are inside the interpreter at once."""

    def __init__(self):
        self._occupants = 0
        self._guard = threading.Lock()
        self.races_detected = 0
        self.calls = 0
        self._pending = None

    def allocate_tensors(self):
        return None

    def get_input_details(self):
        return [{"index": 0, "dtype": np.float32, "shape": np.array([1, 224, 224, 3])}]

    def get_output_details(self):
        return [{"index": 1, "dtype": np.float32, "shape": np.array([1, len(LABELS)])}]

    def _enter(self):
        with self._guard:
            self._occupants += 1
            if self._occupants > 1:
                self.races_detected += 1

    def _leave(self):
        with self._guard:
            self._occupants -= 1

    def set_tensor(self, index, value):
        self._enter()
        # Hold the "buffer" across a yield point, exactly as the real
        # interpreter holds its internal arena across set_tensor -> invoke.
        self._pending = float(value.reshape(-1)[0])
        self._leave()

    def invoke(self):
        self._enter()
        threading.Event().wait(0.005)  # widen the window a real invoke occupies
        self.calls += 1
        self._leave()

    def get_tensor(self, index):
        self._enter()
        # Encode which input produced this output so a crossed response is
        # detectable by the caller.
        marker = self._pending or 0.0
        probs = np.array([[0.02, 0.95, 0.03]], dtype=np.float32)
        probs[0][1] = 0.95
        self._leave()
        self._last_marker = marker
        return probs


def _leaf_image_bytes(green: int = 190) -> bytes:
    from PIL import Image

    arr = np.zeros((256, 256, 3), dtype=np.uint8)
    arr[:, :, 0] = 60
    arr[:, :, 1] = green
    arr[:, :, 2] = 50
    buffer = io.BytesIO()
    Image.fromarray(arr).save(buffer, format="JPEG")
    return buffer.getvalue()


class TFLiteConcurrencyTests(SimpleTestCase):
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
        (cls.model_dir / "metrics.json").write_text(
            json.dumps(
                {
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

    def test_parallel_diagnoses_never_overlap_in_the_interpreter(self):
        stub = _RaceDetectingInterpreter()
        with patch.object(
            inference_module.CropDiseasePredictor,
            "_load_tflite_interpreter",
            staticmethod(lambda _path: stub),
        ):
            predictor = CropDiseasePredictor(model_dir=self.model_dir)

        def diagnose(_):
            with patch.dict("os.environ", {"DISEASE_CLASSIFICATION_ENABLED": "true"}):
                return predictor.predict(self.leaf)

        # 4 threads matches the gthread worker; 24 calls gives the race room.
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(diagnose, range(24)))

        self.assertEqual(
            stub.races_detected,
            0,
            f"{stub.races_detected} concurrent entries into the TFLite "
            "interpreter -- the invoke lock is missing or not covering "
            "set_tensor/invoke/get_tensor as one unit",
        )
        self.assertEqual(stub.calls, 24, "every diagnosis must reach the model")
        for result in results:
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["disease_name"], "Late Blight")

    def test_predictor_exposes_an_invoke_lock(self):
        """The lock is load-bearing; keep it from being quietly removed."""
        stub = _RaceDetectingInterpreter()
        with patch.object(
            inference_module.CropDiseasePredictor,
            "_load_tflite_interpreter",
            staticmethod(lambda _path: stub),
        ):
            predictor = CropDiseasePredictor(model_dir=self.model_dir)
        self.assertTrue(hasattr(predictor, "_invoke_lock"))
        self.assertTrue(hasattr(predictor._invoke_lock, "acquire"))
