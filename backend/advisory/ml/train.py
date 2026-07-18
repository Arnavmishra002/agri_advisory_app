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
    FINE_TUNE_LAYERS,
    FINE_TUNE_LR_FACTOR,
    HISTORY_FILENAME,
    LABELS_FILENAME,
    LEARNING_RATE,
    METRICS_FILENAME,
    MODEL_FILENAME,
    USE_CLASS_WEIGHTS,
    WARMUP_EPOCHS,
)
from .dataset_loader import build_splits, save_dataset_artifacts
from .dataset_manifest import (
    ensure_training_approved,
    load_and_validate_manifest,
    manifest_summary,
)
from .model_builder import (
    build_model,
    compile_model,
    configure_fine_tuning,
    get_architecture_settings,
)

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
    require_non_plant: bool = False,
    warmup_epochs: int = WARMUP_EPOCHS,
    fine_tune_layers: int = FINE_TUNE_LAYERS,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = dataset_manifest or (data_dir / "dataset_manifest.json")
    manifest_data = None
    if manifest_path.exists():
        manifest_data = load_and_validate_manifest(manifest_path)
        if require_manifest:
            ensure_training_approved(manifest_data)
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
    unknown_samples = sum(
        1
        for split in (dataset.train, dataset.val, dataset.test)
        for label in split.labels
        if dataset.class_names[label] == "unknown__unknown"
    )
    if require_non_plant and unknown_samples <= 0:
        raise ValueError(
            "Production disease training requires unknown/not_plant negative images."
        )
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

    warmup_epochs = min(max(1, int(warmup_epochs)), max(1, int(epochs)))
    if model_settings["architecture"] != "efficientnetb3":
        warmup_epochs = max(1, int(epochs))
    history_parts = []
    warmup_history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=warmup_epochs,
        class_weight=class_weight,
        callbacks=callbacks,
    )
    history_parts.append(warmup_history.history)

    fine_tuned_layers = 0
    if model_settings["architecture"] == "efficientnetb3" and epochs > warmup_epochs:
        fine_tuned_layers = configure_fine_tuning(model, fine_tune_layers)
        compile_model(model, learning_rate * FINE_TUNE_LR_FACTOR)
        logger.info(
            "Fine-tuning top %s backbone layers at learning rate %.2e",
            fine_tuned_layers,
            learning_rate * FINE_TUNE_LR_FACTOR,
        )
        fine_history = model.fit(
            train_ds,
            validation_data=val_ds,
            initial_epoch=warmup_epochs,
            epochs=epochs,
            class_weight=class_weight,
            callbacks=callbacks,
        )
        history_parts.append(fine_history.history)

    history_data = {}
    for part in history_parts:
        for key, values in part.items():
            history_data.setdefault(key, []).extend(float(value) for value in values)

    final_path = output_dir / MODEL_FILENAME
    best_model = tf.keras.models.load_model(checkpoint_path)
    best_model.save(final_path)
    logger.info("Saved model to %s", final_path)

    hist_path = output_dir / HISTORY_FILENAME
    hist_path.write_text(
        json.dumps(history_data, indent=2),
        encoding="utf-8",
    )

    hist = history_data
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
        "training_strategy": "frozen_backbone_then_top_layer_fine_tune",
        "warmup_epochs": warmup_epochs,
        "fine_tuned_layers": fine_tuned_layers,
        "fine_tune_learning_rate": learning_rate * FINE_TUNE_LR_FACTOR,
        "non_plant_samples": unknown_samples,
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
    parser.add_argument(
        "--require-non-plant",
        action="store_true",
        help="Refuse production training unless unknown/not_plant negatives are present.",
    )
    parser.add_argument("--warmup-epochs", type=int, default=WARMUP_EPOCHS)
    parser.add_argument("--fine-tune-layers", type=int, default=FINE_TUNE_LAYERS)
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
        require_non_plant=args.require_non_plant,
        warmup_epochs=args.warmup_epochs,
        fine_tune_layers=args.fine_tune_layers,
    )


if __name__ == "__main__":
    main()
