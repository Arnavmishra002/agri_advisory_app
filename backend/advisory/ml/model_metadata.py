"""Model metadata helpers for crop disease readiness and inference."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import HISTORY_FILENAME, METRICS_FILENAME


PRODUCTION_VAL_ACCURACY = 0.75
PRODUCTION_TOP3_ACCURACY = 0.90


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _best_float(values: Any) -> Optional[float]:
    if isinstance(values, (int, float)):
        return float(values)
    if not isinstance(values, list) or not values:
        return None
    nums = []
    for value in values:
        try:
            nums.append(float(value))
        except (TypeError, ValueError):
            continue
    return max(nums) if nums else None


def quality_label(
    best_val_accuracy: Optional[float],
    best_val_top3_accuracy: Optional[float],
) -> str:
    """Return a simple farmer-safety quality label for the installed model."""
    if best_val_accuracy is None and best_val_top3_accuracy is None:
        return "unknown"
    val_ok = (best_val_accuracy or 0.0) >= PRODUCTION_VAL_ACCURACY
    top3_ok = (best_val_top3_accuracy or 0.0) >= PRODUCTION_TOP3_ACCURACY
    return "production_candidate" if val_ok and top3_ok else "needs_retraining"


def load_model_metadata(
    model_dir: Path,
    class_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Load metrics.json, falling back to training_history.json when needed."""
    model_dir = Path(model_dir)
    metrics = _read_json(model_dir / METRICS_FILENAME)
    history = _read_json(model_dir / HISTORY_FILENAME)

    best_val_accuracy = metrics.get("best_val_accuracy")
    if best_val_accuracy is None:
        best_val_accuracy = _best_float(history.get("val_accuracy"))

    best_val_top3_accuracy = metrics.get("best_val_top3_accuracy")
    if best_val_top3_accuracy is None:
        best_val_top3_accuracy = _best_float(history.get("val_top3_accuracy"))

    epochs_trained = metrics.get("epochs_trained")
    if epochs_trained is None:
        epoch_lengths = [len(v) for v in history.values() if isinstance(v, list)]
        epochs_trained = max(epoch_lengths) if epoch_lengths else None

    class_count = metrics.get("class_count")
    if class_count is None and class_names is not None:
        class_count = len(class_names)

    label = quality_label(best_val_accuracy, best_val_top3_accuracy)
    out: Dict[str, Any] = {
        "quality": label,
        "best_val_accuracy": best_val_accuracy,
        "best_val_top3_accuracy": best_val_top3_accuracy,
        "epochs_trained": epochs_trained,
        "class_count": class_count,
        "model": metrics.get("model") or "EfficientNet-B3",
        "architecture": metrics.get("architecture") or "efficientnetb3",
        "input_size": metrics.get("input_size") or [224, 224],
        "preprocess": metrics.get("preprocess") or "efficientnet",
        "production_thresholds": {
            "val_accuracy": PRODUCTION_VAL_ACCURACY,
            "val_top3_accuracy": PRODUCTION_TOP3_ACCURACY,
        },
    }
    out.update(metrics)
    return out


def readiness_summary(metadata: Dict[str, Any]) -> str:
    """Human-readable model quality summary for readiness checks."""
    quality = metadata.get("quality") or "unknown"
    val = metadata.get("best_val_accuracy")
    top3 = metadata.get("best_val_top3_accuracy")
    classes = metadata.get("class_count")

    model_name = metadata.get("model") or "crop disease model"
    parts = [f"{model_name} ready"]
    if classes:
        parts.append(f"{classes} classes")
    if isinstance(val, (int, float)):
        parts.append(f"val_acc={val:.1%}")
    if isinstance(top3, (int, float)):
        parts.append(f"top3={top3:.1%}")

    prefix = "ok" if quality == "production_candidate" else "degraded"
    if quality == "unknown":
        prefix = "degraded"
        parts.append("metrics missing")
    elif quality == "needs_retraining":
        parts.append("retrain before farmer production")

    return f"{prefix} ({', '.join(parts)})"
