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
from typing import Optional

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
    METRICS_FILENAME,
    MODEL_FILENAME,
    USE_CLASS_WEIGHTS,
)
from .dataset_loader import build_splits, save_dataset_artifacts
from .dataset_manifest import load_and_validate_manifest, manifest_summary
from .model_builder import build_model, get_architecture_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def train(
    data_dir: Path,
    output_dir: Path,
    epochs: int = EPOCHS,
    batch_size: int = BATCH_SIZE,
    learning_rate: float = LEARNING_RATE,
    max_samples_per_class: Optional[int] = None,
    architecture: str = "efficientnetb3",
    augment: bool = True,
    use_class_weights: bool = USE_CLASS_WEIGHTS,
    dataset_manifest: Optional[Path] = None,
    require_manifest: bool = False,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = dataset_manifest or (data_dir / "dataset_manifest.json")
    manifest_data = None
    if manifest_path.exists():
        manifest_data = load_and_validate_manifest(manifest_path)
        (output_dir / "dataset_manifest.json").write_text(
            json.dumps(manifest_data, indent=2),
            encoding="utf-8",
        )
    elif require_manifest:
        raise ValueError(
            f"Dataset manifest required but not found: {manifest_path}. "
            "Training is blocked until dataset licensing and splits are documented."
        )
    else:
        logger.warning("Dataset manifest missing: %s", manifest_path)
    model_settings = get_architecture_settings(architecture)
    image_size = tuple(model_settings["input_size"])
    preprocess_mode = model_settings["preprocess"]

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
        image_size=image_size,
        preprocess_mode=preprocess_mode,
        augment=augment,
    )

    model = build_model(
        len(dataset.class_names),
        learning_rate=learning_rate,
        architecture=model_settings["architecture"],
    )

    class_weight = dataset.class_weights if use_class_weights else None

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

    hist = history.history
    metrics = {
        "model": model_settings["display_name"],
        "architecture": model_settings["architecture"],
        "input_size": list(image_size),
        "preprocess": preprocess_mode,
        "class_count": len(dataset.class_names),
        "train_samples": len(train_paths),
        "val_samples": len(val_paths),
        "test_samples": len(dataset.test.paths),
        "epochs_requested": epochs,
        "epochs_trained": len(hist.get("loss", [])),
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "max_samples_per_class": max_samples_per_class,
        "augmentation": augment,
        "class_weights": use_class_weights,
        "dataset_manifest": (
            manifest_summary(manifest_data) if manifest_data else {"status": "missing"}
        ),
        "best_val_accuracy": max(
            [float(x) for x in hist.get("val_accuracy", [])],
            default=None,
        ),
        "best_val_top3_accuracy": max(
            [float(x) for x in hist.get("val_top3_accuracy", [])],
            default=None,
        ),
        "final_train_accuracy": float(hist["accuracy"][-1]) if hist.get("accuracy") else None,
        "final_val_loss": float(hist["val_loss"][-1]) if hist.get("val_loss") else None,
    }
    (output_dir / METRICS_FILENAME).write_text(
        json.dumps(metrics, indent=2),
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
        "--architecture",
        default="efficientnetb3",
        choices=["efficientnetb3", "plantvillage_cnn", "cnn"],
        help="Model architecture to train",
    )
    parser.add_argument(
        "--max-per-class",
        type=int,
        default=None,
        help="Cap images per class for faster training (e.g. 200)",
    )
    parser.add_argument(
        "--no-augmentation",
        action="store_true",
        help="Use clean preprocessing for train images; useful for Kaggle-style CNN baselines.",
    )
    parser.add_argument(
        "--no-class-weights",
        action="store_true",
        help="Disable class weights for balanced/capped datasets.",
    )
    parser.add_argument(
        "--dataset-manifest",
        type=Path,
        default=None,
        help="Dataset provenance manifest; defaults to DATA_DIR/dataset_manifest.json.",
    )
    parser.add_argument(
        "--require-manifest",
        action="store_true",
        help="Refuse to train when the licensed dataset manifest is missing or invalid.",
    )
    args = parser.parse_args()

    train(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        max_samples_per_class=args.max_per_class,
        architecture=args.architecture,
        augment=not args.no_augmentation,
        use_class_weights=not args.no_class_weights,
        dataset_manifest=args.dataset_manifest,
        require_manifest=args.require_manifest,
    )


if __name__ == "__main__":
    main()
