"""Read crop aliases from the generated Phase 1 knowledge snapshot."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Tuple


SNAPSHOT_PATH = (
    Path(__file__).resolve().parents[1]
    / "knowledge_base"
    / "crops"
    / "indian_crop_profiles_202.txt"
)
_LEGACY_CANONICAL_IDS = {"arhar": "tur", "lentil": "masoor"}


def load_crop_terms(path: Path = SNAPSHOT_PATH) -> Dict[str, Tuple[str, ...]]:
    if not path.exists():
        return {}
    terms: Dict[str, Tuple[str, ...]] = {}
    crop_id = ""
    aliases: list[str] = []

    def store() -> None:
        if crop_id:
            values = {crop_id, crop_id.replace("_", " ")}
            values.update(value for value in aliases if value)
            terms[crop_id] = tuple(sorted(values, key=lambda value: (len(value), value)))

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if raw_line.startswith("CROP_ID: "):
            store()
            crop_id = raw_line.split(":", 1)[1].strip()
            aliases = []
        elif raw_line.startswith("CROP: "):
            crop_label = raw_line.split(":", 1)[1]
            aliases.extend(value.strip() for value in crop_label.split("|") if value.strip())
        elif raw_line.startswith("ALIASES: "):
            aliases.extend(
                value.strip()
                for value in raw_line.split(":", 1)[1].split("|")
                if value.strip()
            )
    store()
    return terms


def merge_crop_terms(
    primary: Dict[str, Iterable[str]],
    extra: Dict[str, Iterable[str]],
) -> Dict[str, Tuple[str, ...]]:
    merged: Dict[str, Tuple[str, ...]] = {}
    for crop_id in set(primary) | set(extra):
        values = {str(value).strip() for value in primary.get(crop_id, ()) if str(value).strip()}
        values.update(str(value).strip() for value in extra.get(crop_id, ()) if str(value).strip())
        merged[crop_id] = tuple(sorted(values, key=lambda value: (len(value), value)))
    for legacy_id, canonical_id in _LEGACY_CANONICAL_IDS.items():
        if legacy_id not in merged or canonical_id not in merged:
            continue
        values = set(merged[canonical_id]) | set(merged.pop(legacy_id)) | {legacy_id}
        merged[canonical_id] = tuple(sorted(values, key=lambda value: (len(value), value)))
    return merged
