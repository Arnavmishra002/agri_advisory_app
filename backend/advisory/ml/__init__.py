"""
KrishiMitra crop disease classification (EfficientNet-B3).

Train:  python -m advisory.ml.train --data-dir data/datasets
Eval:   python -m advisory.ml.evaluate --model-dir models/crop_disease
Infer:  python -m advisory.ml.inference --image path/to/leaf.jpg
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .inference import CropDiseasePredictor


def get_predictor():
    from .inference import get_predictor as _get

    return _get()


def __getattr__(name: str):
    if name == "CropDiseasePredictor":
        from .inference import CropDiseasePredictor

        return CropDiseasePredictor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["CropDiseasePredictor", "get_predictor"]
