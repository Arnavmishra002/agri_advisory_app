#!/usr/bin/env python3
"""
Train crop disease model on linked Downloads datasets.

Fast default: 200 images/class, 8 epochs (~1-2 hours CPU).
Full quality: --max-per-class 0 --epochs 25

  python scripts/train_crop_disease.py
  python scripts/train_crop_disease.py --max-per-class 0 --epochs 20
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-per-class", type=int, default=200)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--skip-setup", action="store_true")
    args = parser.parse_args()

    if not args.skip_setup:
        print("Linking datasets from ~/Downloads...")
        subprocess.run(
            [sys.executable, str(PROJECT / "scripts/setup_training_data.py")],
            check=True,
            cwd=PROJECT,
        )

    cmd = [
        sys.executable,
        "-m",
        "advisory.ml.train",
        "--data-dir",
        str(PROJECT / "data/datasets"),
        "--output-dir",
        str(PROJECT / "models/crop_disease"),
        "--epochs",
        str(args.epochs),
        "--batch-size",
        str(args.batch_size),
    ]
    if args.max_per_class and args.max_per_class > 0:
        cmd.extend(["--max-per-class", str(args.max_per_class)])
    else:
        cmd.extend(["--max-per-class", "0"])

    print("Training:", " ".join(cmd))
    return subprocess.call(cmd, cwd=PROJECT)


if __name__ == "__main__":
    raise SystemExit(main())
