"""Validation and summaries for crop-disease dataset provenance manifests."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, List


REQUIRED_SOURCE_FIELDS = {
    "name",
    "source_url",
    "license_name",
    "license_url",
    "retrieved_at",
    "crop_labels",
    "disease_labels",
    "sample_count",
    "splits",
    "usage_approved",
}


def _valid_date(value: Any) -> bool:
    try:
        date.fromisoformat(str(value))
        return True
    except (TypeError, ValueError):
        return False


def validate_manifest_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate provenance, licensing, labels, and split counts."""
    errors: List[str] = []
    if data.get("schema_version") != "1.0":
        errors.append("schema_version must be '1.0'")
    if not str(data.get("dataset_name", "")).strip():
        errors.append("dataset_name is required")
    if not _valid_date(data.get("created_at")):
        errors.append("created_at must be an ISO date (YYYY-MM-DD)")

    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("sources must contain at least one dataset source")
        sources = []

    for index, source in enumerate(sources):
        prefix = f"sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{prefix} must be an object")
            continue
        missing = sorted(REQUIRED_SOURCE_FIELDS - set(source))
        if missing:
            errors.append(f"{prefix} missing fields: {', '.join(missing)}")
            continue
        for field in ("name", "source_url", "license_name", "license_url"):
            if not str(source.get(field, "")).strip():
                errors.append(f"{prefix}.{field} must not be empty")
        if not _valid_date(source.get("retrieved_at")):
            errors.append(f"{prefix}.retrieved_at must be an ISO date")
        if source.get("usage_approved") is not True:
            errors.append(f"{prefix}.usage_approved must be true before training")
        for field in ("crop_labels", "disease_labels"):
            values = source.get(field)
            if not isinstance(values, list) or not values or not all(
                isinstance(value, str) and value.strip() for value in values
            ):
                errors.append(f"{prefix}.{field} must be a non-empty string list")

        sample_count = source.get("sample_count")
        splits = source.get("splits")
        if not isinstance(sample_count, int) or sample_count <= 0:
            errors.append(f"{prefix}.sample_count must be a positive integer")
        if not isinstance(splits, dict) or set(splits) != {"train", "validation", "test"}:
            errors.append(f"{prefix}.splits must contain train, validation, and test")
        elif not all(isinstance(value, int) and value >= 0 for value in splits.values()):
            errors.append(f"{prefix}.splits values must be non-negative integers")
        elif isinstance(sample_count, int) and sum(splits.values()) != sample_count:
            errors.append(f"{prefix}.splits must sum to sample_count")

    if errors:
        raise ValueError("Invalid dataset manifest: " + "; ".join(errors))
    return data


def load_and_validate_manifest(path: Path) -> Dict[str, Any]:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read dataset manifest {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Invalid dataset manifest: root must be an object")
    return validate_manifest_data(data)


def manifest_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    sources = data.get("sources", [])
    return {
        "schema_version": data.get("schema_version"),
        "dataset_name": data.get("dataset_name"),
        "source_count": len(sources),
        "sample_count": sum(source.get("sample_count", 0) for source in sources),
        "licenses": sorted({source.get("license_name") for source in sources}),
        "usage_approved": all(source.get("usage_approved") is True for source in sources),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a disease dataset manifest")
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    data = load_and_validate_manifest(args.manifest)
    print(json.dumps(manifest_summary(data), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
