"""Crop disease model builders."""

from __future__ import annotations

from typing import Any, Dict

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

from .config import BACKBONE, DROPOUT, IMG_SIZE


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
        input_shape=(*IMG_SIZE, 3),
        pooling="avg",
    )
    base.trainable = False

    # Start with a frozen ImageNet backbone. Fine-tuning is enabled only after
    # the classification head has learned a stable label mapping.
    x = base(inputs, training=False)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(DROPOUT)(x)
    outputs = layers.Dense(num_classes, activation="softmax", name="predictions")(x)

    model = keras.Model(inputs=inputs, outputs=outputs, name="crop_disease_efficientnetb3")
    compile_model(model, learning_rate)
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


def _find_backbone(model: keras.Model) -> keras.Model:
    for layer in model.layers:
        if isinstance(layer, keras.Model) and layer.name.startswith("efficientnet"):
            return layer
    raise ValueError("Disease model does not contain an EfficientNet backbone layer")


def configure_fine_tuning(model: keras.Model, trainable_layers: int = 30) -> int:
    """Unfreeze only the top non-BatchNorm backbone layers."""
    backbone = _find_backbone(model)
    backbone.trainable = True
    for layer in backbone.layers:
        layer.trainable = False

    candidates = [
        layer
        for layer in backbone.layers
        if not isinstance(layer, (layers.InputLayer, layers.BatchNormalization))
    ]
    count = max(0, int(trainable_layers))
    selected = candidates[-count:] if count else []
    for layer in selected:
        layer.trainable = True
    return len(selected)


def compile_model(model: keras.Model, learning_rate: float) -> None:
    """Compile after every trainability change so Keras updates its graph."""
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
        loss="sparse_categorical_crossentropy",
        metrics=[
            "accuracy",
            keras.metrics.SparseTopKCategoricalAccuracy(k=3, name="top3_accuracy"),
        ],
    )


def get_preprocess_fn():
    return keras.applications.efficientnet.preprocess_input
