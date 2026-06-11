"""Label encoding: crop__disease ↔ display names."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

from .config import UNKNOWN_DISPLAY, UNKNOWN_LABEL


def make_label(crop: str, disease: str) -> str:
    crop_s = _slug(crop)
    disease_s = _slug(disease)
    if crop_s in ("unknown", "none", "") or disease_s in ("unknown", "none", ""):
        return UNKNOWN_LABEL
    return f"{crop_s}__{disease_s}"


def parse_label(label: str) -> Tuple[str, str]:
    if label == UNKNOWN_LABEL or label.lower().startswith("unknown"):
        return UNKNOWN_DISPLAY, "Not a supported crop or unclear image"
    if "__" in label:
        crop, disease = label.split("__", 1)
        return _display(crop), _display(disease)
    return _display(label), "Healthy"


def _slug(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "unknown"


def _display(slug: str) -> str:
    return slug.replace("_", " ").title()


def save_labels(labels: List[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "labels": labels,
        "unknown_label": UNKNOWN_LABEL,
        "format": "crop__disease",
    }
    path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def load_labels(path: Path) -> List[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data["labels"])
