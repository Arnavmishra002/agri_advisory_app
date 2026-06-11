"""Image preprocessing for training and inference."""

from __future__ import annotations

import io
from typing import Optional, Tuple, Union

import numpy as np

from .config import IMG_CHANNELS, IMG_SIZE

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def load_image_from_bytes(data: bytes) -> np.ndarray:
    """Load RGB image uint8 HWC from bytes."""
    if HAS_PIL:
        img = Image.open(io.BytesIO(data)).convert("RGB")
        return np.array(img, dtype=np.uint8)
    raise RuntimeError("Pillow is required for image loading")


def load_image_from_path(path: str) -> np.ndarray:
    if HAS_PIL:
        return np.array(Image.open(path).convert("RGB"), dtype=np.uint8)
    raise RuntimeError("Pillow is required for image loading")


def remove_background_simple(image: np.ndarray) -> np.ndarray:
    """
    Simple green-plant foreground emphasis (not full segmentation).
    Reduces noisy background when leaf is on soil/sky.
    """
    if not HAS_CV2 or image.ndim != 3:
        return image

    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    # Vegetation-ish mask
    lower = np.array([25, 30, 30])
    upper = np.array([95, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    mask = cv2.GaussianBlur(mask, (5, 5), 0)
    mask_3 = cv2.merge([mask, mask, mask]) / 255.0
    blurred = cv2.GaussianBlur(image, (7, 7), 0)
    enhanced = (image * mask_3 + blurred * (1 - mask_3)).astype(np.uint8)
    return enhanced


def resize_and_normalize(
    image: np.ndarray,
    size: Tuple[int, int] = IMG_SIZE,
    remove_bg: bool = True,
) -> np.ndarray:
    """Resize to target size; return float32 [0, 255] RGB for EfficientNet preprocess_input."""
    if remove_bg:
        image = remove_background_simple(image)

    if HAS_CV2:
        image = cv2.resize(image, size, interpolation=cv2.INTER_AREA)
    elif HAS_PIL:
        image = np.array(
            Image.fromarray(image).resize(size, Image.Resampling.BILINEAR),
            dtype=np.uint8,
        )
    else:
        raise RuntimeError("OpenCV or Pillow required for resize")

    if image.ndim == 2:
        image = np.stack([image] * IMG_CHANNELS, axis=-1)
    return image.astype(np.float32)


def prepare_for_model(
    image: Union[np.ndarray, bytes, str],
    remove_bg: bool = True,
) -> np.ndarray:
    """Single image → batch-ready float tensor (1, H, W, 3) after EfficientNet preprocess."""
    if isinstance(image, bytes):
        arr = load_image_from_bytes(image)
    elif isinstance(image, str):
        arr = load_image_from_path(image)
    else:
        arr = image

    arr = resize_and_normalize(arr, remove_bg=remove_bg)
    return np.expand_dims(arr, axis=0)
