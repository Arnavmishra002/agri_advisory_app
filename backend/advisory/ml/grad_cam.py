"""Grad-CAM visualization for model explanations."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import tensorflow as tf

from .model_builder import get_preprocess_fn
from .preprocess import prepare_for_model


def compute_grad_cam(
    model: tf.keras.Model,
    image_array: np.ndarray,
    class_index: int,
    last_conv_layer_name: Optional[str] = None,
) -> np.ndarray:
    """
    Returns heatmap (H, W) float 0-1.
    """
    if last_conv_layer_name is None:
        last_conv_layer_name = _find_last_conv_layer(model)

    grad_model = tf.keras.models.Model(
        [model.inputs],
        [model.get_layer(last_conv_layer_name).output, model.output],
    )

    preprocess = get_preprocess_fn()
    if image_array.max() > 1.0:
        img_tensor = preprocess(image_array[0])
    else:
        img_tensor = image_array[0]
    img_tensor = tf.expand_dims(img_tensor, 0)

    with tf.GradientTape() as tape:
        conv_outputs, predictions = grad_model(img_tensor)
        if class_index is None:
            class_index = tf.argmax(predictions[0])
        loss = predictions[:, class_index]

    grads = tape.gradient(loss, conv_outputs)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
    conv_outputs = conv_outputs[0]
    heatmap = tf.reduce_sum(tf.multiply(pooled_grads, conv_outputs), axis=-1)
    heatmap = tf.maximum(heatmap, 0) / (tf.reduce_max(heatmap) + 1e-8)
    return heatmap.numpy()


def save_grad_cam_overlay(
    model: tf.keras.Model,
    image_path: str,
    class_index: int,
    output_path: Path,
) -> Path:
    import cv2

    from .preprocess import load_image_from_path, resize_and_normalize

    rgb = resize_and_normalize(load_image_from_path(image_path), remove_bg=True)
    batch = np.expand_dims(rgb, 0)
    heatmap = compute_grad_cam(model, batch, class_index)
    heatmap = cv2.resize(heatmap, (224, 224))
    heatmap_uint8 = np.uint8(255 * heatmap)
    heatmap_color = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)
    heatmap_color = cv2.cvtColor(heatmap_color, cv2.COLOR_BGR2RGB)
    overlay = cv2.addWeighted(rgb.astype(np.uint8), 0.55, heatmap_color, 0.45, 0)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
    return output_path


def _find_last_conv_layer(model: tf.keras.Model) -> str:
    for layer in reversed(model.layers):
        if "block" in layer.name and len(layer.output.shape) == 4:
            return layer.name
    for layer in reversed(model.layers):
        if len(layer.output.shape) == 4:
            return layer.name
    raise ValueError("No convolutional layer found for Grad-CAM")
