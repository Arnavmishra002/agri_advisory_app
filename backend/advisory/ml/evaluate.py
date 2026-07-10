#!/usr/bin/env python3
"""
Evaluate trained model: accuracy, precision, recall, F1, confusion matrix.

Usage:
  python -m advisory.ml.evaluate --model-dir models/crop_disease --data-dir data/datasets
"""

from __future__ import annotations

import argparse
import json
import logging
import random
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import tensorflow as tf
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from .augmentation import decode_and_resize, preprocess_val
from .config import (
    DEFAULT_DATA_DIR,
    DEFAULT_MODEL_DIR,
    LABELS_FILENAME,
    METRICS_FILENAME,
    MODEL_FILENAME,
    SEED,
)
from .dataset_loader import build_splits
from .labels import load_labels

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _per_class_metrics(
    all_true: Sequence[int],
    all_preds: Sequence[int],
    class_names: Sequence[str],
) -> Dict[str, Dict[str, float]]:
    labels = list(range(len(class_names)))
    report = classification_report(
        all_true,
        all_preds,
        labels=labels,
        target_names=list(class_names),
        zero_division=0,
        output_dict=True,
    )
    return {
        name: {
            "precision": float(report[name]["precision"]),
            "recall": float(report[name]["recall"]),
            "f1": float(report[name]["f1-score"]),
            "false_negative_rate": float(1.0 - report[name]["recall"]),
            "support": int(report[name]["support"]),
        }
        for name in class_names
    }


def _limit_test_samples(
    paths: Sequence[str],
    labels: Sequence[int],
    max_samples: Optional[int],
    seed: int = SEED,
) -> Tuple[List[str], List[int]]:
    if not max_samples or max_samples <= 0 or max_samples >= len(paths):
        return list(paths), [int(label) for label in labels]

    rng = random.Random(seed)
    by_label = {}
    for idx, (path, label) in enumerate(zip(paths, labels)):
        by_label.setdefault(int(label), []).append((idx, path, int(label)))

    selected = []
    per_class = max(1, max_samples // max(1, len(by_label)))
    for label in sorted(by_label):
        items = by_label[label][:]
        rng.shuffle(items)
        selected.extend(items[:per_class])

    selected_idx = {idx for idx, _, _ in selected}
    if len(selected) < max_samples:
        remaining = [
            (idx, path, int(label))
            for idx, (path, label) in enumerate(zip(paths, labels))
            if idx not in selected_idx
        ]
        rng.shuffle(remaining)
        selected.extend(remaining[: max_samples - len(selected)])

    rng.shuffle(selected)
    selected = selected[:max_samples]
    return [path for _, path, _ in selected], [label for _, _, label in selected]


def _load_test_batch(paths, labels, batch_size=32):
    images, ys = [], []
    for path, y in zip(paths, labels):
        img_bytes = tf.io.read_file(path)
        img = tf.io.decode_image(img_bytes, channels=3, expand_animations=False)
        img = tf.image.resize(img, [224, 224])
        img = tf.cast(img, tf.float32)
        img, label = preprocess_val(img, y)
        images.append(img.numpy())
        ys.append(int(label.numpy() if hasattr(label, "numpy") else label))
    return np.array(images), np.array(ys)


def evaluate(
    model_dir: Path,
    data_dir: Path,
    max_test_samples: Optional[int] = None,
) -> dict:
    model_path = model_dir / MODEL_FILENAME
    if not model_path.exists():
        model_path = model_dir / "checkpoints" / "best.keras"
    model = tf.keras.models.load_model(model_path)

    labels_path = model_dir / LABELS_FILENAME
    if labels_path.exists():
        class_names = load_labels(labels_path)
    else:
        dataset = build_splits(data_dir)
        class_names = dataset.class_names

    dataset = build_splits(data_dir)
    test_paths = [str(p) for p in dataset.test.paths]
    test_labels = dataset.test.labels
    available_test_samples = len(test_paths)
    test_paths, test_labels = _limit_test_samples(
        test_paths,
        test_labels,
        max_test_samples,
    )

    all_preds = []
    all_true = []
    batch_size = 32

    for i in range(0, len(test_paths), batch_size):
        batch_p = test_paths[i : i + batch_size]
        batch_y = test_labels[i : i + batch_size]
        imgs = []
        for path in batch_p:
            img_bytes = tf.io.read_file(path)
            img = tf.io.decode_image(img_bytes, channels=3, expand_animations=False)
            img = tf.image.resize(img, [224, 224])
            img = tf.cast(img, tf.float32)
            img, _ = preprocess_val(img, 0)
            imgs.append(img.numpy())
        X = np.stack(imgs, axis=0)
        probs = model.predict(X, verbose=0)
        preds = np.argmax(probs, axis=1)
        all_preds.extend(preds.tolist())
        all_true.extend(batch_y)

    acc = accuracy_score(all_true, all_preds)
    prec = precision_score(all_true, all_preds, average="weighted", zero_division=0)
    rec = recall_score(all_true, all_preds, average="weighted", zero_division=0)
    f1 = f1_score(all_true, all_preds, average="weighted", zero_division=0)
    n_classes = len(class_names)
    label_ids = list(range(n_classes))
    cm = confusion_matrix(all_true, all_preds, labels=label_ids).tolist()
    report = classification_report(
        all_true,
        all_preds,
        labels=label_ids,
        target_names=class_names,
        zero_division=0,
        output_dict=True,
    )
    per_class = _per_class_metrics(all_true, all_preds, class_names)

    metrics = {
        "accuracy": float(acc),
        "precision_weighted": float(prec),
        "recall_weighted": float(rec),
        "f1_weighted": float(f1),
        "confusion_matrix": cm,
        "classification_report": report,
        "per_class_metrics": per_class,
        "max_false_negative_rate": max(
            (item["false_negative_rate"] for item in per_class.values()),
            default=1.0,
        ),
        "num_test_samples": len(all_true),
        "available_test_samples": available_test_samples,
        "max_test_samples": max_test_samples,
        "evaluation_limited": bool(
            max_test_samples and len(all_true) < available_test_samples
        ),
    }

    metrics_path = model_dir / METRICS_FILENAME
    existing_metrics = {}
    if metrics_path.exists():
        try:
            existing_metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing_metrics = {}
    existing_metrics.update(metrics)
    metrics_path.write_text(json.dumps(existing_metrics, indent=2), encoding="utf-8")
    logger.info("Accuracy=%.4f F1=%.4f — saved %s", acc, f1, metrics_path)

    _plot_confusion_matrix(cm, class_names, model_dir / "confusion_matrix.png")

    return metrics


def _plot_confusion_matrix(cm, class_names, out_path: Path):
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns

        n = len(cm)
        labels = class_names[:n] if class_names and len(class_names) >= n else [str(i) for i in range(n)]
        if n > 30:
            return  # skip huge plots
        plt.figure(figsize=(12, 10))
        sns.heatmap(cm, annot=False, fmt="d", xticklabels=labels, yticklabels=labels)
        plt.xlabel("Predicted")
        plt.ylabel("True")
        plt.title("Confusion Matrix")
        plt.tight_layout()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_path, dpi=120)
        plt.close()
    except ImportError:
        logger.warning("matplotlib/seaborn not installed — skipping confusion matrix plot")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument(
        "--max-test-samples",
        type=int,
        default=None,
        help="Evaluate a deterministic subset for quick local/CI smoke checks.",
    )
    args = parser.parse_args()
    evaluate(args.model_dir, args.data_dir, max_test_samples=args.max_test_samples)


if __name__ == "__main__":
    main()
