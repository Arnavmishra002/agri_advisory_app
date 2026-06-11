"""Heuristic checks so non-plant images (laptop, desk, etc.) are rejected before CNN inference."""

from __future__ import annotations

from typing import Any, Dict, Tuple, Union

import numpy as np

from .preprocess import load_image_from_bytes, load_image_from_path

try:
    import cv2

    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

MIN_GREEN_RATIO = 0.10
MAX_GRAY_RATIO = 0.42
MIN_IMAGE_SIDE = 48


def _resize_rgb(arr: np.ndarray, size: int = 224) -> np.ndarray:
    if HAS_CV2:
        return cv2.resize(arr, (size, size), interpolation=cv2.INTER_AREA)
    try:
        from PIL import Image

        img = Image.fromarray(arr.astype(np.uint8))
        return np.array(img.resize((size, size), Image.Resampling.BILINEAR))
    except Exception:
        return arr


def _metrics_pil(arr: np.ndarray) -> Dict[str, float]:
    """Green vs gray ratios without OpenCV."""
    small = _resize_rgb(arr, 224)
    r = small[:, :, 0].astype(np.float32)
    g = small[:, :, 1].astype(np.float32)
    b = small[:, :, 2].astype(np.float32)
    pixels = float(small.shape[0] * small.shape[1])

    green_dom = (g > r * 1.08) & (g > b * 1.08) & (g > 55)
    green_ratio = float(np.count_nonzero(green_dom)) / pixels

    chroma = np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b)
    gray_mask = chroma < 28
    gray_ratio = float(np.count_nonzero(gray_mask)) / pixels

    blue_dom = (b > r * 1.05) & (b > g * 1.02) & (b > 60)
    blue_ratio = float(np.count_nonzero(blue_dom)) / pixels

    return {
        "green_ratio": round(green_ratio, 3),
        "gray_ratio": round(gray_ratio, 3),
        "blue_ratio": round(blue_ratio, 3),
    }


def _metrics_cv2(arr: np.ndarray) -> Dict[str, float]:
    small = cv2.resize(arr, (224, 224), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)
    pixels = float(224 * 224)

    green_mask = cv2.inRange(hsv, np.array([25, 35, 35]), np.array([95, 255, 255]))
    green_ratio = float(np.count_nonzero(green_mask)) / pixels

    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    gray_mask = (sat < 35) & (val > 35) & (val < 220)
    gray_ratio = float(np.count_nonzero(gray_mask)) / pixels

    blue_mask = cv2.inRange(hsv, np.array([90, 40, 40]), np.array([130, 255, 255]))
    blue_ratio = float(np.count_nonzero(blue_mask)) / pixels

    return {
        "green_ratio": round(green_ratio, 3),
        "gray_ratio": round(gray_ratio, 3),
        "blue_ratio": round(blue_ratio, 3),
    }


def _classify_metrics(metrics: Dict[str, float]) -> Tuple[bool, str]:
    green_ratio = metrics["green_ratio"]
    gray_ratio = metrics["gray_ratio"]
    blue_ratio = metrics["blue_ratio"]

    if green_ratio < MIN_GREEN_RATIO:
        if gray_ratio >= MAX_GRAY_RATIO or blue_ratio > 0.18:
            return False, "not_plant"
        return False, "not_plant"

    if gray_ratio >= 0.55 and green_ratio < 0.18:
        return False, "not_plant"

    return True, "ok"


def validate_plant_image(image: Union[bytes, str, np.ndarray]) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Returns (is_valid, reason_code, metrics).
    reason_code: ok | not_plant | unreadable
    """
    try:
        if isinstance(image, bytes):
            arr = load_image_from_bytes(image)
        elif isinstance(image, str):
            arr = load_image_from_path(image)
        else:
            arr = np.asarray(image, dtype=np.uint8)
    except Exception:
        return False, "unreadable", {}

    if arr.ndim != 3 or arr.shape[0] < MIN_IMAGE_SIDE or arr.shape[1] < MIN_IMAGE_SIDE:
        return False, "unreadable", {}

    metrics = _metrics_cv2(arr) if HAS_CV2 else _metrics_pil(arr)
    valid, reason = _classify_metrics(metrics)
    return valid, reason, metrics
