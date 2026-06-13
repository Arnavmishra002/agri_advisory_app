#!/usr/bin/env python3
"""
Production inference for crop + disease classification.

Usage:
  python -m advisory.ml.inference --image leaf.jpg --model-dir models/crop_disease
"""

from __future__ import annotations

import base64
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
    TOP_K,
    UNKNOWN_DISPLAY,
    UNKNOWN_LABEL,
)
from .image_validation import validate_plant_image
from .labels import load_labels, parse_label
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
        self.class_names: List[str] = []
        self._load()

    def _load(self) -> None:
        model_path = self.model_dir / MODEL_FILENAME
        if not model_path.exists():
            alt = self.model_dir / "checkpoints" / "best.keras"
            if alt.exists():
                model_path = alt
            else:
                logger.warning("No trained model at %s — ML predictions disabled", self.model_dir)
                return

        import tensorflow as tf
        self.model = tf.keras.models.load_model(model_path)
        labels_file = self.model_dir / LABELS_FILENAME
        if labels_file.exists():
            self.class_names = load_labels(labels_file)
        else:
            logger.warning("Missing %s", labels_file)

    @property
    def is_ready(self) -> bool:
        return self.model is not None and bool(self.class_names)

    def predict(
        self,
        image: Union[str, bytes, Any],
        save_gradcam_to: Optional[Path] = None,
        skip_validation: bool = False,
    ) -> Dict[str, Any]:
        raw_bytes: Optional[bytes] = None
        if isinstance(image, bytes):
            raw_bytes = image
        elif isinstance(image, str) and not image.startswith("/") and len(image) > 200:
            try:
                b64 = image.split(",", 1)[-1] if "," in image else image
                raw_bytes = base64.b64decode(b64)
            except Exception:
                raw_bytes = None

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

        batch = prepare_for_model(image, remove_bg=True)
        from .model_builder import get_preprocess_fn
        preprocess = get_preprocess_fn()
        batch_pp = preprocess(batch[0])
        import numpy as np
        batch_pp = np.expand_dims(batch_pp, axis=0)

        probs = self.model.predict(batch_pp, verbose=0)[0]
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
            "model": "EfficientNet-B3",
            "threshold": CONFIDENCE_THRESHOLD,
        }

        if confidence < CONFIDENCE_THRESHOLD or best["label"] == UNKNOWN_LABEL:
            result["status"] = "low_confidence"
            result["message"] = LOW_CONFIDENCE_MESSAGE
            result["crop_name"] = best["crop_name"] if confidence >= 0.4 else None
            result["disease_name"] = None

        if save_gradcam_to and self.model is not None:
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
        raw = base64.b64decode(b64_string)
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
