"""Crop disease model builders."""

from __future__ import annotations

from typing import Any, Dict

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

from .config import BACKBONE, DROPOUT, FINE_TUNE_AT, IMG_SIZE


ARCHITECTURE_SETTINGS: Dict[str, Dict[str, Any]] = {
    "efficientnetb3": {
        "display_name": "EfficientNet-B3",
        "input_size": IMG_SIZE,
        "preprocess": "efficientnet",
    },
    "plantvillage_cnn": {
        "display_name": "PlantVillage CNN",
        "input_size": (128, 128),
        "preprocess": "rescale_1_255",
    },
}


def normalize_architecture(architecture: str) -> str:
    aliases = {
        "cnn": "plantvillage_cnn",
        "custom_cnn": "plantvillage_cnn",
        "plantvillage-cnn": "plantvillage_cnn",
        "efficientnet": "efficientnetb3",
        "efficientnet-b3": "efficientnetb3",
    }
    value = (architecture or BACKBONE).strip().lower()
    return aliases.get(value, value)


def get_architecture_settings(architecture: str) -> Dict[str, Any]:
    key = normalize_architecture(architecture)
    if key not in ARCHITECTURE_SETTINGS:
        supported = ", ".join(sorted(ARCHITECTURE_SETTINGS))
        raise ValueError(f"Unsupported architecture '{architecture}'. Use one of: {supported}")
    settings = dict(ARCHITECTURE_SETTINGS[key])
    settings["architecture"] = key
    return settings


def build_model(
    num_classes: int,
    learning_rate: float = 1e-4,
    architecture: str = BACKBONE,
) -> keras.Model:
    key = normalize_architecture(architecture)
    if key == "plantvillage_cnn":
        return _build_plantvillage_cnn(num_classes, learning_rate)
    return _build_efficientnetb3(num_classes, learning_rate)


def _build_efficientnetb3(num_classes: int, learning_rate: float) -> keras.Model:
    inputs = keras.Input(shape=(*IMG_SIZE, 3))

    base = keras.applications.EfficientNetB3(
        include_top=False,
        weights="imagenet",
        input_tensor=inputs,
        pooling="avg",
    )
    base.trainable = False

    # Fine-tune top blocks
    for layer in base.layers[FINE_TUNE_AT:]:
        layer.trainable = True

    x = base.output
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(DROPOUT)(x)
    outputs = layers.Dense(num_classes, activation="softmax", name="predictions")(x)

    model = keras.Model(inputs=inputs, outputs=outputs, name="crop_disease_efficientnetb3")

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
        loss="sparse_categorical_crossentropy",
        metrics=[
            "accuracy",
            keras.metrics.SparseTopKCategoricalAccuracy(k=3, name="top3_accuracy"),
        ],
    )
    return model


def _build_plantvillage_cnn(num_classes: int, learning_rate: float) -> keras.Model:
    """Compact CNN based on common PlantVillage Kaggle/GitHub deployments."""
    model = keras.Sequential(
        [
            keras.Input(shape=(128, 128, 3)),
            layers.Conv2D(32, (3, 3), activation="relu", padding="same"),
            layers.Conv2D(32, (3, 3), activation="relu", padding="same"),
            layers.MaxPooling2D((2, 2)),
            layers.Conv2D(64, (3, 3), activation="relu", padding="same"),
            layers.Conv2D(64, (3, 3), activation="relu", padding="same"),
            layers.MaxPooling2D((2, 2)),
            layers.Conv2D(128, (3, 3), activation="relu", padding="same"),
            layers.Conv2D(128, (3, 3), activation="relu", padding="same"),
            layers.MaxPooling2D((2, 2)),
            layers.Conv2D(256, (3, 3), activation="relu", padding="same"),
            layers.Conv2D(256, (3, 3), activation="relu", padding="same"),
            layers.MaxPooling2D((2, 2)),
            layers.Conv2D(512, (3, 3), activation="relu", padding="same"),
            layers.Conv2D(512, (3, 3), activation="relu", padding="same"),
            layers.MaxPooling2D((2, 2)),
            layers.Dropout(0.25),
            layers.Flatten(),
            layers.Dense(1500, activation="relu"),
            layers.Dropout(0.4),
            layers.Dense(num_classes, activation="softmax", name="predictions"),
        ],
        name="crop_disease_plantvillage_cnn",
    )
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
        loss="sparse_categorical_crossentropy",
        metrics=[
            "accuracy",
            keras.metrics.SparseTopKCategoricalAccuracy(k=3, name="top3_accuracy"),
        ],
    )
    return model


def get_preprocess_fn():
    return keras.applications.efficientnet.preprocess_input
