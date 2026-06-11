"""EfficientNet-B3 model with transfer learning."""

from __future__ import annotations

from typing import Tuple

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

from .config import BACKBONE, DROPOUT, FINE_TUNE_AT, IMG_SIZE


def build_model(num_classes: int, learning_rate: float = 1e-4) -> keras.Model:
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


def get_preprocess_fn():
    return keras.applications.efficientnet.preprocess_input
