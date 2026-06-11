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
from pathlib import Path

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
)
from .dataset_loader import build_splits
from .labels import load_labels

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


def evaluate(model_dir: Path, data_dir: Path) -> dict:
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
    cm = confusion_matrix(all_true, all_preds).tolist()

    n_classes = max(max(all_true, default=0), max(all_preds, default=0)) + 1
    tnames = class_names[:n_classes] if class_names and len(class_names) >= n_classes else None
    report = classification_report(
        all_true,
        all_preds,
        labels=list(range(n_classes)),
        target_names=tnames,
        zero_division=0,
        output_dict=True,
    )

    metrics = {
        "accuracy": float(acc),
        "precision_weighted": float(prec),
        "recall_weighted": float(rec),
        "f1_weighted": float(f1),
        "confusion_matrix": cm,
        "classification_report": report,
        "num_test_samples": len(all_true),
    }

    metrics_path = model_dir / METRICS_FILENAME
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
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
    args = parser.parse_args()
    evaluate(args.model_dir, args.data_dir)


if __name__ == "__main__":
    main()
