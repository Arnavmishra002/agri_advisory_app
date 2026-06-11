#!/usr/bin/env python3
"""
Unified dataset loader for:
  - PlantVillage (Crop___Disease folders)
  - PlantDoc, Crop Pest and Disease, New Plant Diseases (crop/disease hierarchy)

Also supports explicit unknown class folders.
"""

from __future__ import annotations

import os
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .config import (
    DATASET_SOURCES,
    DEFAULT_DATA_DIR,
    IMG_SIZE,
    SEED,
    UNKNOWN_LABEL,
    VALIDATION_SPLIT,
    TEST_SPLIT,
)
from .labels import make_label, save_labels

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# Container dirs to recurse into (train/valid splits)
_SPLIT_DIR_NAMES = frozenset({"train", "valid", "validation", "test"})

# Skip nested duplicate/meta folders when scanning
_SKIP_DIR_NAMES = frozenset({"plantvillage", ".ds_store"})

# Crop Pest flat folders: "Maize leaf blight"
_CROP_PEST_PREFIXES = ("Cashew", "Cassava", "Maize", "Tomato")


@dataclass
class DatasetSplit:
    paths: List[str]
    labels: List[int]
    class_names: List[str]


@dataclass
class LoadedDataset:
    train: DatasetSplit
    val: DatasetSplit
    test: DatasetSplit
    class_names: List[str]
    class_weights: Dict[int, float]


def discover_images(data_root: Path) -> List[Tuple[str, str]]:
    """
    Scan data_root and nested raw/ folders.
    Returns list of (filepath, label_string).
    """
    samples: List[Tuple[str, str]] = []
    roots: List[Path] = []
    raw = data_root / "raw"
    if raw.is_dir():
        seen_roots = set()
        for name in DATASET_SOURCES:
            p = raw / name
            if p.is_dir():
                roots.append(p)
                seen_roots.add(p.resolve())
        for child in raw.iterdir():
            if child.is_dir() and child.resolve() not in seen_roots:
                roots.append(child)
                seen_roots.add(child.resolve())
    else:
        roots = [data_root]

    for root in roots:
        if not root.is_dir():
            continue
        samples.extend(_scan_directory(root))

    # Deduplicate by path
    seen = set()
    unique = []
    for path, label in samples:
        if path not in seen:
            seen.add(path)
            unique.append((path, label))

    return unique


def _label_from_plantvillage_folder(folder_name: str) -> str:
    """Tomato___Late_blight, Tomato_Bacterial_spot, Pepper__bell___Bacterial_spot."""
    name = folder_name.strip()
    if "___" in name:
        crop, disease = name.split("___", 1)
    elif "__" in name:
        crop, disease = name.split("__", 1)
        disease = disease.replace("_", " ")
    else:
        parts = name.split("_", 1)
        crop = parts[0]
        disease = parts[1] if len(parts) > 1 else "healthy"
    crop = crop.replace("_", " ").strip()
    disease = disease.replace("_", " ").strip()
    return make_label(crop, disease)


def _label_from_flat_folder(folder_name: str) -> str:
    """Crop Pest style: 'Cashew anthracnose', 'Tomato healthy'."""
    name = folder_name.strip()
    lower = name.lower()
    if lower.endswith(" healthy"):
        return make_label(name[: -len(" healthy")].strip(), "healthy")
    for crop in _CROP_PEST_PREFIXES:
        prefix = crop + " "
        if name.startswith(prefix):
            return make_label(crop, name[len(prefix) :].strip())
    parts = name.split(" ", 1)
    if len(parts) == 2:
        return make_label(parts[0], parts[1])
    return make_label(name, "healthy")


def _scan_class_folder(entry: Path) -> List[Tuple[str, str]]:
    """Scan one class folder (images directly inside)."""
    out: List[Tuple[str, str]] = []
    name = entry.name
    if name.lower() in _SKIP_DIR_NAMES:
        return out

    if "___" in name or "__" in name or (
        "_" in name and any(name.startswith(c) for c in _CROP_PEST_PREFIXES + ("Tomato", "Potato", "Pepper", "Corn", "Grape", "Apple"))
    ):
        label = _label_from_plantvillage_folder(name)
        for f in _list_images(entry):
            out.append((str(f), label))
        return out

    if name.lower() in ("unknown", "not_plant", "background", "random"):
        for f in _list_images(entry):
            out.append((str(f), UNKNOWN_LABEL))
        return out

    subdirs = [d for d in entry.iterdir() if d.is_dir()]
    if subdirs:
        for disease_dir in subdirs:
            imgs = _list_images(disease_dir)
            if imgs:
                label = make_label(name, disease_dir.name)
                for f in imgs:
                    out.append((str(f), label))
            else:
                for nested in disease_dir.iterdir():
                    if nested.is_dir():
                        lbl = make_label(name, nested.name)
                        for f in _list_images(nested):
                            out.append((str(f), lbl))
        return out

    imgs = _list_images(entry)
    if imgs:
        if " " in name and not name.startswith("."):
            label = _label_from_flat_folder(name)
        else:
            label = make_label(name, "healthy")
        for f in imgs:
            out.append((str(f), label))
    return out


def _scan_directory(root: Path) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []

    # Pattern: train/valid/test splits with class folders inside
    split_dirs = [root / s for s in _SPLIT_DIR_NAMES if (root / s).is_dir()]
    if split_dirs:
        for split_path in split_dirs:
            for entry in split_path.iterdir():
                if entry.is_dir():
                    out.extend(_scan_class_folder(entry))
        if out:
            return out

    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        if entry.name.lower() in _SKIP_DIR_NAMES:
            continue
        # Single nested PlantVillage bundle
        if entry.name == "PlantVillage" and entry.is_dir():
            out.extend(_scan_directory(entry))
            continue
        out.extend(_scan_class_folder(entry))

    return out


def _is_valid_image_file(path: Path) -> bool:
    if path.name.startswith("._") or path.name == ".DS_Store":
        return False
    try:
        head = path.read_bytes()[:12]
    except OSError:
        return False
    if head[:3] == b"\xff\xd8\xff":
        return True
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return True
    if head[:2] == b"BM":
        return True
    if head[0:4] == b"RIFF" and head[8:12] == b"WEBP":
        return True
    return False


def _list_images(folder: Path) -> List[Path]:
    files = []
    for p in folder.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in IMAGE_EXT:
            continue
        if _is_valid_image_file(p):
            files.append(p)
    return files


def stratified_split(
    samples: Sequence[Tuple[str, str]],
    val_ratio: float = VALIDATION_SPLIT,
    test_ratio: float = TEST_SPLIT,
    seed: int = SEED,
) -> Tuple[List, List, List]:
    rng = random.Random(seed)
    by_label: Dict[str, List[str]] = {}
    for path, label in samples:
        by_label.setdefault(label, []).append(path)

    train, val, test = [], [], []
    for label, paths in by_label.items():
        rng.shuffle(paths)
        n = len(paths)
        n_test = max(1, int(n * test_ratio)) if n >= 3 else 0
        n_val = max(1, int(n * val_ratio)) if n >= 3 else 0
        test_paths = paths[:n_test]
        val_paths = paths[n_test : n_test + n_val]
        train_paths = paths[n_test + n_val :]

        for p in train_paths:
            train.append((p, label))
        for p in val_paths:
            val.append((p, label))
        for p in test_paths:
            test.append((p, label))

    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)
    return train, val, test


def compute_class_weights(label_indices: List[int], num_classes: int) -> Dict[int, float]:
    counts = np.bincount(label_indices, minlength=num_classes).astype(np.float64)
    counts = np.maximum(counts, 1.0)
    total = counts.sum()
    weights = total / (num_classes * counts)
    return {int(i): float(weights[i]) for i in range(num_classes)}


def _cap_samples(
    samples: List[Tuple[str, str]],
    max_per_class: Optional[int],
    seed: int = SEED,
) -> List[Tuple[str, str]]:
    if not max_per_class or max_per_class <= 0:
        return samples
    rng = random.Random(seed)
    by_label: Dict[str, List[Tuple[str, str]]] = {}
    for item in samples:
        by_label[item[1]].append(item)
    capped: List[Tuple[str, str]] = []
    for label in sorted(by_label.keys()):
        items = by_label[label]
        rng.shuffle(items)
        capped.extend(items[:max_per_class])
    rng.shuffle(capped)
    return capped


def build_splits(
    data_dir: Optional[Path] = None,
    max_samples_per_class: Optional[int] = None,
) -> LoadedDataset:
    data_dir = Path(data_dir or DEFAULT_DATA_DIR)
    samples = discover_images(data_dir)
    if max_samples_per_class:
        samples = _cap_samples(samples, max_samples_per_class)
    if not samples:
        raise FileNotFoundError(
            f"No images found under {data_dir}. "
            "Place datasets under data/datasets/raw/plantvillage etc."
        )

    # Ensure unknown class exists in label space
    labels_set = sorted({lbl for _, lbl in samples})
    if UNKNOWN_LABEL not in labels_set:
        labels_set.append(UNKNOWN_LABEL)

    label_to_idx = {lbl: i for i, lbl in enumerate(labels_set)}

    train_s, val_s, test_s = stratified_split(samples)

    def _to_split(pairs: List[Tuple[str, str]]) -> DatasetSplit:
        paths = [p for p, _ in pairs]
        labels = [label_to_idx[lbl] for _, lbl in pairs]
        return DatasetSplit(paths=paths, labels=labels, class_names=labels_set)

    train = _to_split(train_s)
    val = _to_split(val_s)
    test = _to_split(test_s)

    weights = compute_class_weights(train.labels, len(labels_set))

    return LoadedDataset(
        train=train,
        val=val,
        test=test,
        class_names=labels_set,
        class_weights=weights,
    )


def save_dataset_artifacts(output_dir: Path, class_names: List[str]) -> Path:
    labels_path = output_dir / "class_labels.json"
    save_labels(class_names, labels_path)
    return labels_path


if __name__ == "__main__":
    ds = build_splits()
    print(f"Classes: {len(ds.class_names)}")
    print(f"Train: {len(ds.train.paths)} Val: {len(ds.val.paths)} Test: {len(ds.test.paths)}")
