#!/usr/bin/env python3
"""
Train crop disease model on linked Downloads datasets.

Fast default writes an experimental candidate without replacing the installed
farmer-facing model. Production mode additionally requires an approved dataset
manifest and non-plant negatives.

  python scripts/train_crop_disease.py
  python scripts/train_crop_disease.py --max-per-class 0 --epochs 20
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-per-class", type=int, default=200)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--architecture", default="efficientnetb3")
    parser.add_argument("--warmup-epochs", type=int, default=3)
    parser.add_argument("--fine-tune-layers", type=int, default=30)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT / "models/crop_disease_candidate",
    )
    parser.add_argument(
        "--dataset-manifest",
        type=Path,
        default=PROJECT / "backend/advisory/ml/dataset_manifest.example.json",
    )
    parser.add_argument("--production", action="store_true")
    parser.add_argument("--skip-evaluation", action="store_true")
    parser.add_argument("--max-test-samples", type=int, default=760)
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
        str(args.output_dir),
        "--epochs",
        str(args.epochs),
        "--batch-size",
        str(args.batch_size),
        "--lr",
        str(args.learning_rate),
        "--architecture",
        args.architecture,
        "--warmup-epochs",
        str(args.warmup_epochs),
        "--fine-tune-layers",
        str(args.fine_tune_layers),
    ]
    if args.max_per_class and args.max_per_class > 0:
        cmd.extend(["--max-per-class", str(args.max_per_class)])
    else:
        cmd.extend(["--max-per-class", "0"])

    if args.dataset_manifest:
        cmd.extend(["--dataset-manifest", str(args.dataset_manifest)])
    if args.production:
        cmd.extend(["--require-manifest", "--require-non-plant"])

    env = dict(os.environ)
    env["PYTHONPATH"] = str(PROJECT / "backend")
    print("Training:", " ".join(cmd))
    result = subprocess.call(cmd, cwd=PROJECT, env=env)
    if result or args.skip_evaluation:
        return result

    evaluate_cmd = [
        sys.executable,
        "-m",
        "advisory.ml.evaluate",
        "--data-dir",
        str(PROJECT / "data/datasets"),
        "--model-dir",
        str(args.output_dir),
    ]
    if args.max_test_samples and args.max_test_samples > 0:
        evaluate_cmd.extend(["--max-test-samples", str(args.max_test_samples)])
    print("Evaluating:", " ".join(evaluate_cmd))
    return subprocess.call(evaluate_cmd, cwd=PROJECT, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
