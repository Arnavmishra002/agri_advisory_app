"""TensorFlow-independent image decoding helpers for disease training."""

from __future__ import annotations


def load_image_with_pillow(path_value, label_value, image_size):
    """Decode scalar path and label values supplied by ``tf.py_function``."""
    import os

    import numpy as np
    from PIL import Image

    if hasattr(path_value, "numpy"):
        path_value = path_value.numpy()
    if isinstance(path_value, np.ndarray):
        path_value = path_value.item()
    if hasattr(label_value, "numpy"):
        label_value = label_value.numpy()
    if isinstance(label_value, np.ndarray):
        label_value = label_value.item()

    path = os.fsdecode(path_value)
    height, width = (int(value) for value in image_size)
    try:
        with Image.open(path) as image:
            image = image.convert("RGB")
            image = image.resize((width, height), Image.Resampling.BILINEAR)
            pixels = np.asarray(image, dtype=np.float32)
    except Exception as exc:
        raise ValueError(f"Unable to decode training image {path}: {exc}") from exc
    return pixels, np.int32(label_value)
