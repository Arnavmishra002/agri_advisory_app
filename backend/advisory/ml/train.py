#!/usr/bin/env python3
"""
Train EfficientNet-B3 crop/disease classifier.

Usage:
  python -m advisory.ml.train --data-dir data/datasets --output-dir models/crop_disease
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import tensorflow as tf

from .augmentation import make_datasets
from .config import (
    BATCH_SIZE,
    DEFAULT_DATA_DIR,
    DEFAULT_MODEL_DIR,
    EPOCHS,
    HISTORY_FILENAME,
    LABELS_FILENAME,
    LEARNING_RATE,
    MODEL_FILENAME,
    USE_CLASS_WEIGHTS,
)
from .dataset_loader import build_splits, save_dataset_artifacts
from .model_builder import build_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def train(
    data_dir: Path,
    output_dir: Path,
    epochs: int = EPOCHS,
    batch_size: int = BATCH_SIZE,
    learning_rate: float = LEARNING_RATE,
    max_samples_per_class: Optional[int] = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset = build_splits(data_dir, max_samples_per_class=max_samples_per_class)
    save_dataset_artifacts(output_dir, dataset.class_names)

    train_paths = [str(p) for p in dataset.train.paths]
    val_paths = [str(p) for p in dataset.val.paths]

    train_ds, val_ds = make_datasets(
        train_paths,
        dataset.train.labels,
        val_paths,
        dataset.val.labels,
        batch_size,
    )

    model = build_model(len(dataset.class_names), learning_rate=learning_rate)

    class_weight = dataset.class_weights if USE_CLASS_WEIGHTS else None

    checkpoint_path = output_dir / "checkpoints" / "best.keras"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            filepath=str(checkpoint_path),
            monitor="val_accuracy",
            save_best_only=True,
            mode="max",
            verbose=1,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=6,
            restore_best_weights=True,
            verbose=1,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=3,
            min_lr=1e-7,
            verbose=1,
        ),
        tf.keras.callbacks.TensorBoard(log_dir=str(output_dir / "logs")),
    ]

    logger.info(
        "Training %s classes | train=%s val=%s",
        len(dataset.class_names),
        len(train_paths),
        len(val_paths),
    )

    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs,
        class_weight=class_weight,
        callbacks=callbacks,
    )

    final_path = output_dir / MODEL_FILENAME
    model.save(final_path)
    logger.info("Saved model to %s", final_path)

    hist_path = output_dir / HISTORY_FILENAME
    hist_path.write_text(
        json.dumps({k: [float(x) for x in v] for k, v in history.history.items()}, indent=2),
        encoding="utf-8",
    )

    return final_path


def main():
    parser = argparse.ArgumentParser(description="Train crop disease EfficientNet-B3")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--lr", type=float, default=LEARNING_RATE)
    parser.add_argument(
        "--max-per-class",
        type=int,
        default=None,
        help="Cap images per class for faster training (e.g. 200)",
    )
    args = parser.parse_args()

    train(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        max_samples_per_class=args.max_per_class,
    )


if __name__ == "__main__":
    main()
