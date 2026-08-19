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
    *,
    evaluation_accuracy: Optional[float] = None,
    evaluation_top3_accuracy: Optional[float] = None,
    manifest_approved: bool = False,
    non_plant_test_samples: int = 0,
    evaluation_limited: bool = True,
    all_classes_evaluated: bool = False,
) -> str:
    """Return a farmer-safety quality label backed by held-out evidence."""
    if best_val_accuracy is None and best_val_top3_accuracy is None:
        return "unknown"
    val_ok = (best_val_accuracy or 0.0) >= PRODUCTION_VAL_ACCURACY
    top3_ok = (best_val_top3_accuracy or 0.0) >= PRODUCTION_TOP3_ACCURACY
    if not val_ok or not top3_ok:
        return "needs_retraining"

    evaluation_ok = (
        (evaluation_accuracy or 0.0) >= PRODUCTION_VAL_ACCURACY
        and (evaluation_top3_accuracy or 0.0) >= PRODUCTION_TOP3_ACCURACY
        and not evaluation_limited
        and all_classes_evaluated
    )
    if not evaluation_ok or not manifest_approved or non_plant_test_samples <= 0:
        return "needs_validation"
    return "production_candidate"


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

    dataset_manifest = metrics.get("dataset_manifest") or {}
    evaluation_accuracy = metrics.get("evaluation_accuracy")
    if evaluation_accuracy is None:
        evaluation_accuracy = metrics.get("accuracy")
    evaluation_top3_accuracy = metrics.get("evaluation_top3_accuracy")
    label = quality_label(
        best_val_accuracy,
        best_val_top3_accuracy,
        evaluation_accuracy=evaluation_accuracy,
        evaluation_top3_accuracy=evaluation_top3_accuracy,
        manifest_approved=dataset_manifest.get("usage_approved") is True,
        non_plant_test_samples=int(metrics.get("non_plant_test_samples") or 0),
        evaluation_limited=metrics.get("evaluation_limited") is not False,
        all_classes_evaluated=metrics.get("all_classes_evaluated") is True,
    )
    # Persisted metrics are evidence, not authority. Always write the derived
    # fields last so a stale or manually edited `quality` value cannot promote
    # a model that does not satisfy the current safety policy.
    out: Dict[str, Any] = dict(metrics)
    out.update({
        "quality": label,
        "best_val_accuracy": best_val_accuracy,
        "best_val_top3_accuracy": best_val_top3_accuracy,
        "evaluation_accuracy": evaluation_accuracy,
        "evaluation_top3_accuracy": evaluation_top3_accuracy,
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
    })
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
    elif quality == "needs_validation":
        parts.append("held-out, licensed, and non-plant validation required")

    return f"{prefix} ({', '.join(parts)})"
