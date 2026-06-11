#!/usr/bin/env python3
"""
Link downloaded Kaggle datasets into data/datasets/raw/ for training.

Usage:
  python scripts/setup_training_data.py
  python scripts/setup_training_data.py --analyze-only
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
RAW = PROJECT / "data" / "datasets" / "raw"

DEFAULT_SOURCES = {
    "plantvillage": Path("/Users/arnavmishra/Downloads/PlantVillage"),
    "crop_pest_disease": Path("/Users/arnavmishra/Downloads/archive"),
    "new_plant_diseases": Path(
        "/Users/arnavmishra/Downloads/archive-2/"
        "New Plant Diseases Dataset(Augmented)/"
        "New Plant Diseases Dataset(Augmented)"
    ),
}


def _symlink(target: Path, link: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() or link.exists():
        if link.is_symlink() and link.resolve() == target.resolve():
            return
        if link.is_dir() and not link.is_symlink():
            return
        link.unlink()
    os.symlink(target, link)


def setup(links: dict) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for name, src in links.items():
        if not src.is_dir():
            print(f"SKIP (missing): {name} -> {src}")
            continue
        dest = RAW / name
        _symlink(src.resolve(), dest)
        print(f"OK  {dest} -> {src}")


def analyze(data_dir: Path) -> None:
    sys.path.insert(0, str(PROJECT / "backend"))
    from advisory.ml.dataset_loader import build_splits, discover_images

    samples = discover_images(data_dir)
    labels = {lbl for _, lbl in samples}
    print(f"\nTotal images: {len(samples)}")
    print(f"Unique classes: {len(labels)}")
    try:
        ds = build_splits(data_dir)
        print(f"Train: {len(ds.train.paths)}  Val: {len(ds.val.paths)}  Test: {len(ds.test.paths)}")
    except Exception as exc:
        print(f"build_splits: {exc}")
    print("\nSample classes:")
    for lbl in sorted(labels)[:15]:
        print(f"  - {lbl}")
    if len(labels) > 15:
        print(f"  ... and {len(labels) - 15} more")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analyze-only", action="store_true")
    parser.add_argument("--plantvillage", type=Path, default=DEFAULT_SOURCES["plantvillage"])
    parser.add_argument("--crop-pest", type=Path, default=DEFAULT_SOURCES["crop_pest_disease"])
    parser.add_argument("--new-plant", type=Path, default=DEFAULT_SOURCES["new_plant_diseases"])
    args = parser.parse_args()

    links = {
        "plantvillage": args.plantvillage,
        "crop_pest_disease": args.crop_pest,
        "new_plant_diseases": args.new_plant,
    }

    if not args.analyze_only:
        setup(links)
    analyze(PROJECT / "data" / "datasets")


if __name__ == "__main__":
    main()
