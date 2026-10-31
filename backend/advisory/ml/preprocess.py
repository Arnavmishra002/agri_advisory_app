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


def _half_pixel_weights(in_size: int, out_size: int):
    """Sample positions of TensorFlow's half-pixel-centre bilinear resize.

    TensorFlow's kernel evaluates ``(i + 0.5) * scale - 0.5`` with a fused
    multiply-add, i.e. one float32 rounding; computing it in float64 and
    rounding once reproduces that exactly.
    """
    scale = np.float64(np.float32(in_size / out_size))
    pos = ((np.arange(out_size, dtype=np.float64) + 0.5) * scale - 0.5).astype(np.float32)
    floor = np.floor(pos)
    lower = np.maximum(floor, 0).astype(np.int64)
    upper = np.minimum(np.ceil(pos), in_size - 1).astype(np.int64)
    return lower, upper, (pos - floor).astype(np.float32)


def resize_like_training(image: np.ndarray, size: Tuple[int, int] = IMG_SIZE) -> np.ndarray:
    """Resize exactly as training did: ``tf.image.resize(img, [h, w])``.

    That call is bilinear with half-pixel centres and no antialiasing, and it
    returns unrounded float32. The confidence and unknown-class thresholds were
    calibrated on that input, so inference must reproduce it: OpenCV's area
    resize, Pillow's antialiased bilinear resize and the green-mask background
    blur all shift the model's output on real photographs. Each lerp is rounded
    to float32 once, as TensorFlow's fused multiply-adds do, which makes the
    result bit-identical to ``tf.image.resize``.
    """
    out_w, out_h = size
    img = image.astype(np.float64)
    y_lo, y_hi, y_lerp = _half_pixel_weights(image.shape[0], out_h)
    x_lo, x_hi, x_lerp = _half_pixel_weights(image.shape[1], out_w)
    x_lerp = x_lerp.astype(np.float64)[None, :, None]
    top = (img[y_lo][:, x_lo] + (img[y_lo][:, x_hi] - img[y_lo][:, x_lo]) * x_lerp).astype(np.float32)
    bottom = (img[y_hi][:, x_lo] + (img[y_hi][:, x_hi] - img[y_hi][:, x_lo]) * x_lerp).astype(np.float32)
    step = (bottom - top).astype(np.float64)
    return (top.astype(np.float64) + step * y_lerp.astype(np.float64)[:, None, None]).astype(np.float32)


def resize_and_normalize(
    image: np.ndarray,
    size: Tuple[int, int] = IMG_SIZE,
    remove_bg: bool = False,
) -> np.ndarray:
    """Resize to target size; return float32 [0, 255] RGB for EfficientNet preprocess_input.

    ``remove_bg`` is off by default: training never blurred the background,
    and doing so at inference blurs brown and grey lesions outside the green
    mask.
    """
    if image.ndim == 2:
        image = np.stack([image] * IMG_CHANNELS, axis=-1)
    if remove_bg:
        image = remove_background_simple(image)
    return resize_like_training(image, size)


def prepare_for_model(
    image: Union[np.ndarray, bytes, str],
    remove_bg: bool = False,
    size: Tuple[int, int] = IMG_SIZE,
) -> np.ndarray:
    """Single image -> batch-ready float tensor (1, H, W, 3), unnormalized RGB."""
    if isinstance(image, bytes):
        arr = load_image_from_bytes(image)
    elif isinstance(image, str):
        arr = load_image_from_path(image)
    else:
        arr = image

    arr = resize_and_normalize(arr, size=size, remove_bg=remove_bg)
    return np.expand_dims(arr, axis=0)
