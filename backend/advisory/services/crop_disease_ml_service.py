"""Django service wrapper for crop disease ML inference."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CropDiseaseMLService:
    """Runs EfficientNet-B3 inference when a trained model is present."""

    def predict_image(
        self,
        image_data: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        image_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            raw = image_bytes
            if raw is None and image_data:
                import base64

                b64 = image_data.split(",", 1)[1] if "," in image_data else image_data
                raw = base64.b64decode(b64)

            if raw:
                blocked = self._validate_or_block(raw)
                if blocked:
                    return blocked

            from ..ml.inference import get_predictor

            predictor = get_predictor()
            if not predictor.is_ready:
                return {
                    "status": "model_unavailable",
                    "message": (
                        "ML model not trained. Run: python -m advisory.ml.train "
                        "--data-dir data/datasets"
                    ),
                    "crop_name": None,
                    "disease_name": None,
                    "confidence": 0.0,
                    "top_predictions": [],
                }

            if image_bytes:
                return predictor.predict(image_bytes, skip_validation=False)
            if image_path:
                return predictor.predict(image_path, skip_validation=False)
            if image_data:
                return predictor.predict_base64(image_data)

            return {"status": "error", "message": "No image provided"}

        except ImportError as exc:
            logger.warning("TensorFlow not installed: %s", exc)
            return {
                "status": "tensorflow_missing",
                "message": "Install ML deps: pip install -r requirements-ml.txt",
                "crop_name": None,
                "disease_name": None,
                "confidence": 0.0,
                "top_predictions": [],
            }
        except Exception as exc:
            logger.error("ML prediction failed: %s", exc)
            return {
                "status": "error",
                "message": str(exc),
                "crop_name": None,
                "disease_name": None,
                "confidence": 0.0,
                "top_predictions": [],
            }

    def predict_from_upload_dict(self, images: Dict[str, str]) -> Dict[str, Any]:
        """Run validation + inference on best available upload (close-up preferred)."""
        priority = (
            "close_up",
            "leaf",
            "whole",
            "imgCloseUp",
            "imgLeaf",
            "imgWhole",
        )
        for key in priority:
            if images.get(key):
                return self.predict_image(image_data=images[key])
        for val in images.values():
            if val:
                return self.predict_image(image_data=val)
        return {
            "status": "error",
            "message": "No image provided",
            "crop_name": None,
            "disease_name": None,
            "confidence": 0.0,
            "top_predictions": [],
        }


    @staticmethod
    def _validate_or_block(image_bytes: bytes) -> Optional[Dict[str, Any]]:
        try:
            from ..ml.image_validation import validate_plant_image
            from ..ml.config import NOT_PLANT_MESSAGE, UNKNOWN_DISPLAY

            valid, reason, metrics = validate_plant_image(image_bytes)
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
        except Exception as exc:
            logger.debug("Plant validation skipped: %s", exc)
        return None


crop_disease_ml_service = CropDiseaseMLService()
