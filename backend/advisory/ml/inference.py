#!/usr/bin/env python3
"""
Production inference for crop + disease classification.

Usage:
  python -m advisory.ml.inference --image leaf.jpg --model-dir models/crop_disease
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Lazy-loaded tensorflow and numpy to optimize worker startup latency

from .config import (
    CONFIDENCE_THRESHOLD,
    DEFAULT_MODEL_DIR,
    LABELS_FILENAME,
    LOW_CONFIDENCE_MESSAGE,
    MODEL_FILENAME,
    NOT_PLANT_MESSAGE,
    TFLITE_FILENAME,
    TOP_K,
    UNKNOWN_DISPLAY,
    UNKNOWN_LABEL,
)
from .image_validation import validate_plant_image
from .labels import load_labels, parse_label
from .model_metadata import load_model_metadata
from .preprocess import prepare_for_model

logger = logging.getLogger(__name__)


class CropDiseasePredictor:
    """Load EfficientNet-B3 and predict with confidence gating."""

    def __init__(self, model_dir: Optional[Path] = None):
        self.model_dir = Path(
            model_dir
            or os.getenv("CROP_DISEASE_MODEL_DIR", str(DEFAULT_MODEL_DIR))
        )
        self.model: Optional[Any] = None
        # "keras" (full TensorFlow) or "tflite" (tflite-runtime, low memory).
        self.backend: Optional[str] = None
        self._tflite_input: Optional[Dict[str, Any]] = None
        self._tflite_output: Optional[Dict[str, Any]] = None
        self.class_names: List[str] = []
        self.metadata: Dict[str, Any] = {}
        self._load()

    @staticmethod
    def _load_tflite_interpreter(model_path: Path):
        """Return a TFLite interpreter, preferring the standalone runtime.

        tflite-runtime is a ~5 MB wheel, against ~2 GB for TensorFlow, so a
        512 MB host can serve the model with it. Full TensorFlow is accepted as
        a fallback for development machines that already have it.
        """
        try:
            from tflite_runtime.interpreter import Interpreter  # type: ignore
        except ImportError:
            try:
                from tensorflow.lite import Interpreter  # type: ignore
            except ImportError:
                return None
        interpreter = Interpreter(model_path=str(model_path))
        interpreter.allocate_tensors()
        return interpreter

    def _load(self) -> None:
        keras_path = self.model_dir / MODEL_FILENAME
        if not keras_path.exists():
            alt = self.model_dir / "checkpoints" / "best.keras"
            if alt.exists():
                keras_path = alt
        tflite_path = self.model_dir / TFLITE_FILENAME

        # Prefer TFLite when TensorFlow is absent (the production case) or when
        # explicitly requested. The two artifacts come from the same training
        # run, so labels, thresholds and metadata apply identically to both.
        prefer_tflite = os.getenv("ML_PREFER_TFLITE", "").lower() in {"1", "true", "yes", "on"}
        if tflite_path.exists():
            tensorflow_available = True
            if not prefer_tflite:
                try:
                    import tensorflow  # noqa: F401
                except ImportError:
                    tensorflow_available = False
            if prefer_tflite or not tensorflow_available:
                interpreter = self._load_tflite_interpreter(tflite_path)
                if interpreter is not None:
                    self.model = interpreter
                    self.backend = "tflite"
                    self._tflite_input = interpreter.get_input_details()[0]
                    self._tflite_output = interpreter.get_output_details()[0]
                    logger.info("Loaded TFLite crop-disease model from %s", tflite_path)

        if self.model is None:
            if not keras_path.exists():
                logger.warning(
                    "No trained model at %s — ML predictions disabled", self.model_dir
                )
                return
            try:
                import tensorflow as tf
            except ImportError:
                logger.warning(
                    "TensorFlow is not installed and no TFLite model is present at %s "
                    "— ML predictions disabled",
                    tflite_path,
                )
                return
            self.model = tf.keras.models.load_model(keras_path)
            self.backend = "keras"

        labels_file = self.model_dir / LABELS_FILENAME
        if labels_file.exists():
            self.class_names = load_labels(labels_file)
        else:
            logger.warning("Missing %s", labels_file)
        self.metadata = load_model_metadata(self.model_dir, self.class_names)

    def _input_size(self) -> tuple[int, int]:
        raw_size = self.metadata.get("input_size")
        if isinstance(raw_size, (list, tuple)) and len(raw_size) == 2:
            try:
                return int(raw_size[0]), int(raw_size[1])
            except (TypeError, ValueError):
                pass
        if self.backend == "tflite" and self._tflite_input is not None:
            shape = self._tflite_input.get("shape")
            if shape is not None and len(shape) >= 3:
                return int(shape[2]), int(shape[1])
        if self.model is not None and self.backend == "keras":
            shape = getattr(self.model, "input_shape", None)
            if isinstance(shape, list):
                shape = shape[0]
            if shape and len(shape) >= 3 and shape[1] and shape[2]:
                return int(shape[2]), int(shape[1])
        return 224, 224

    def _preprocess_batch(self, batch):
        preprocess_mode = self.metadata.get("preprocess") or "efficientnet"
        if preprocess_mode == "rescale_1_255":
            return batch / 255.0
        if preprocess_mode == "none":
            return batch
        # "efficientnet": keras.applications.efficientnet.preprocess_input is a
        # documented no-op — EfficientNet carries its own Rescaling and
        # Normalization layers, so the network expects raw float32 RGB in
        # [0, 255], exactly what prepare_for_model() returns. Importing Keras
        # here would drag TensorFlow into a TFLite-only host, so pass through
        # directly when TensorFlow is unavailable.
        try:
            from .model_builder import get_preprocess_fn
        except ImportError:
            return batch
        try:
            preprocess = get_preprocess_fn()
        except Exception:  # pragma: no cover - TF present but Keras app missing
            return batch
        return preprocess(batch)

    def _predict_probs(self, batch_pp):
        """Run a forward pass on whichever backend is loaded."""
        if self.backend == "tflite":
            import numpy as np

            expected = self._tflite_input["dtype"]
            interpreter = self.model
            interpreter.set_tensor(
                self._tflite_input["index"], batch_pp.astype(expected)
            )
            interpreter.invoke()
            return np.array(interpreter.get_tensor(self._tflite_output["index"])[0])
        return self.model.predict(batch_pp, verbose=0)[0]

    @property
    def is_ready(self) -> bool:
        return self.model is not None and bool(self.class_names)

    @property
    def is_production_ready(self) -> bool:
        return self.metadata.get("quality") == "production_candidate"

    @staticmethod
    def _allow_unverified_model() -> bool:
        return os.getenv("ML_ALLOW_UNVERIFIED_MODEL", "false").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    def predict(
        self,
        image: Union[str, bytes, Any],
        save_gradcam_to: Optional[Path] = None,
        skip_validation: bool = False,
    ) -> Dict[str, Any]:
        classification_enabled = os.getenv(
            "DISEASE_CLASSIFICATION_ENABLED", "false"
        ).lower() in {"1", "true", "yes", "on"}
        if not classification_enabled:
            return {
                "status": "classification_disabled",
                "message": (
                    "Image disease classification is disabled. "
                    "Symptom-based advisory remains available."
                ),
                "crop_name": None,
                "disease_name": None,
                "confidence": 0.0,
                "top_predictions": [],
            }

        raw_bytes: Optional[bytes] = None
        if isinstance(image, bytes):
            raw_bytes = image
        elif isinstance(image, str) and not image.startswith("/") and len(image) > 200:
            try:
                b64 = image.split(",", 1)[-1] if "," in image else image
                raw_bytes = base64.b64decode(b64, validate=True)
            except (ValueError, TypeError, binascii.Error):
                return {
                    "status": "invalid_image",
                    "message": "The image could not be decoded. Please upload a clear JPEG, PNG, or WebP photo.",
                    "crop_name": None,
                    "disease_name": None,
                    "confidence": 0.0,
                    "top_predictions": [],
                }

        if not skip_validation and raw_bytes:
            valid, reason, metrics = validate_plant_image(raw_bytes)
            if not valid and reason == "not_plant":
                return {
                    "status": "not_plant",
                    "message": NOT_PLANT_MESSAGE,
                    "crop_name": UNKNOWN_DISPLAY,
                    "disease_name": None,
                    "confidence": 0.0,
                    "top_predictions": [],
                    "validation": metrics,
                }

        if not self.is_ready:
            return {
                "status": "model_unavailable",
                "message": "Train model with: python -m advisory.ml.train",
                "crop_name": None,
                "disease_name": None,
                "confidence": 0.0,
                "top_predictions": [],
            }

        if not self.is_production_ready and not self._allow_unverified_model():
            return {
                "status": "model_unverified",
                "message": (
                    "Installed crop disease model is not validated for farmer production. "
                    "Retrain and evaluate it before enabling image classification."
                ),
                "crop_name": None,
                "disease_name": None,
                "confidence": 0.0,
                "top_predictions": [],
                "model": self.metadata.get("model") or "EfficientNet-B3",
                "model_quality": self.metadata.get("quality", "unknown"),
                "model_metrics": self.metadata,
            }

        batch = prepare_for_model(image, remove_bg=True, size=self._input_size())
        batch_pp = self._preprocess_batch(batch)
        import numpy as np

        probs = self._predict_probs(batch_pp)
        top_indices = np.argsort(probs)[::-1][:TOP_K]

        top_predictions = []
        for idx in top_indices:
            label = self.class_names[int(idx)]
            crop, disease = parse_label(label)
            top_predictions.append({
                "crop_name": crop,
                "disease_name": disease,
                "label": label,
                "probability": round(float(probs[idx]), 4),
                "confidence_percent": round(float(probs[idx]) * 100, 1),
            })

        best = top_predictions[0]
        confidence = best["probability"]

        result: Dict[str, Any] = {
            "status": "success",
            "crop_name": best["crop_name"],
            "disease_name": best["disease_name"],
            "confidence": confidence,
            "confidence_percent": best["confidence_percent"],
            "top_predictions": top_predictions,
            "model": self.metadata.get("model") or "EfficientNet-B3",
            "model_quality": self.metadata.get("quality", "unknown"),
            "model_metrics": self.metadata,
            "threshold": CONFIDENCE_THRESHOLD,
        }

        if confidence < CONFIDENCE_THRESHOLD or best["label"] == UNKNOWN_LABEL:
            result["status"] = "low_confidence"
            result["message"] = LOW_CONFIDENCE_MESSAGE
            result["crop_name"] = best["crop_name"] if confidence >= 0.4 else None
            result["disease_name"] = None

        if save_gradcam_to and self.model is not None and self.backend == "keras":
            try:
                if isinstance(image, str):
                    from .grad_cam import save_grad_cam_overlay
                    path = save_grad_cam_overlay(
                        self.model,
                        image,
                        int(top_indices[0]),
                        save_gradcam_to,
                    )
                    result["grad_cam_path"] = str(path)
            except Exception as exc:
                logger.warning("Grad-CAM failed: %s", exc)

        return result

    def predict_base64(self, b64_string: str, **kwargs) -> Dict[str, Any]:
        if "," in b64_string:
            b64_string = b64_string.split(",", 1)[1]
        raw = base64.b64decode(b64_string, validate=True)
        return self.predict(raw, **kwargs)


# FIX 5: Thread-safe singleton using double-checked locking.
# lru_cache is NOT thread-safe on the FIRST call — two threads can both see a
# cache miss and construct CropDiseasePredictor() simultaneously, causing TF to
# load the model twice: 2× GPU/RAM usage, potential CUDA deadlock, OOM kill.
_PREDICTOR_LOCK: threading.Lock = threading.Lock()
_predictor_instance: Optional[CropDiseasePredictor] = None


def get_predictor() -> CropDiseasePredictor:
    """Return a singleton CropDiseasePredictor, initialised exactly once
    even under concurrent first-request load (double-checked locking)."""
    global _predictor_instance
    if _predictor_instance is not None:   # fast path — no lock after first load
        return _predictor_instance
    with _PREDICTOR_LOCK:
        if _predictor_instance is None:   # re-check inside lock
            _predictor_instance = CropDiseasePredictor()
    return _predictor_instance


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--gradcam", type=Path, default=None)
    args = parser.parse_args()

    predictor = CropDiseasePredictor(args.model_dir)
    out = predictor.predict(args.image, save_gradcam_to=args.gradcam)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
