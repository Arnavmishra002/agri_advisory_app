"""Stage operator-reviewed corrections; never mutate a model or a live KB."""

import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

from django.core.management.base import BaseCommand, CommandError


def validate_record(record, line):
    def reject(reason):
        raise CommandError(f"Record {line}: {reason}")

    if not isinstance(record, dict):
        reject("expected an object")
    if record.get("review_status") != "approved":
        reject("agronomist approval required")
    for field in ("privacy_review_passed", "source_verified", "safety_review_passed", "consent_verified"):
        if record.get(field) is not True:
            reject(f"{field} must be true")
    # Weather, prices and individual sensor observations must remain runtime data.
    if record.get("knowledge_type") != "stable_agronomy":
        reject("only stable agronomy corrections may be staged")
    for field in ("record_id", "reviewer_id", "reviewed_question", "reviewed_answer"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            reject(f"{field} is required")
    references = record.get("source_references")
    if not isinstance(references, list) or not references:
        reject("attributable source references required")
    for reference in references:
        if not isinstance(reference, str):
            reject("source references must be URLs")
        try:
            parsed = urlparse(reference)
            valid = parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password
        except ValueError:
            valid = False
        if not valid:
            reject("source references must be HTTPS URLs without credentials")
    # All approvals are human attestations, not automated proof of correctness.
    return {
        "record_id": record["record_id"].strip(),
        "reviewer_id": record["reviewer_id"].strip(),
        "question": record["reviewed_question"].strip(),
        "answer": record["reviewed_answer"].strip(),
        "source_references": references,
    }


class Command(BaseCommand):
    help = "Stage reviewed corrections for evaluation, not training or production."

    def add_arguments(self, parser):
        parser.add_argument("--input", required=True)
        parser.add_argument("--output", required=True)

    def handle(self, *args, **options):
        source = Path(options["input"]).expanduser().resolve()
        output = Path(options["output"]).expanduser().resolve()
        records = []
        seen = set()
        try:
            with source.open(encoding="utf-8") as stream:
                for line, raw in enumerate(stream, 1):
                    if not raw.strip():
                        continue
                    record = validate_record(json.loads(raw), line)
                    if record["record_id"] in seen:
                        raise CommandError(f"Record {line}: duplicate record ID")
                    seen.add(record["record_id"])
                    records.append(record)
                    if len(records) > 10000:
                        raise CommandError("At most 10000 records per review batch")
        except (OSError, ValueError) as exc:
            raise CommandError("Cannot read valid reviewed JSONL input") from exc
        if not records:
            raise CommandError("No approved records supplied")
        canonical = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        bundle = {
            "schema_version": "1.0",
            "content_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            "record_count": len(records),
            "promotion_stage": "awaiting_evaluation",
            "training_eligible": False,
            "production_eligible": False,
            "required_gates": ["held_out_safety", "source_grounding", "multilingual_quality", "regression", "staging_approval"],
            "records": records,
        }
        try:
            # Exclusive creation protects previous reviewed versions from overwrite.
            with output.open("x", encoding="utf-8") as stream:
                json.dump(bundle, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
        except OSError as exc:
            raise CommandError("Cannot create output; use a new path in an existing private directory") from exc
        self.stdout.write(f"Staged {len(records)} corrections for evaluation. No KB/model changes made.")
