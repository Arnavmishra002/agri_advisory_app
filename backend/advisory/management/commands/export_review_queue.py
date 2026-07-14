"""Export de-identified low-quality chatbot turns for human agronomy review."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import timezone as datetime_timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from advisory.models import FarmerInteractionLog


_PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[-\s]?)?[6-9]\d{9}(?!\d)")
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_COORD_RE = re.compile(r"(?<!\d)-?\d{1,2}\.\d{4,}\s*[,/]\s*-?\d{2,3}\.\d{4,}(?!\d)")


def _scrub_text(value: str) -> str:
    text = str(value or "")
    text = _PHONE_RE.sub("[PHONE_REDACTED]", text)
    text = _EMAIL_RE.sub("[EMAIL_REDACTED]", text)
    return _COORD_RE.sub("[COORDINATES_REDACTED]", text).strip()


def _subject_id(session_id: str) -> str:
    payload = f"{settings.SECRET_KEY}:{session_id}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:20]


class Command(BaseCommand):
    help = "Export a pending, de-identified review queue. It is never training-ready."

    def add_arguments(self, parser):
        parser.add_argument("--output-dir", required=True)
        parser.add_argument("--limit", type=int, default=1000)

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit < 1 or limit > 10000:
            raise CommandError("--limit must be between 1 and 10000")
        output_dir = Path(options["output_dir"]).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        unanswered = (
            Q(response__icontains="unavailable")
            | Q(response__icontains="do not have enough")
            | Q(response__icontains="उपलब्ध नहीं")
            | Q(response__icontains="समझ नहीं")
        )
        queryset = FarmerInteractionLog.objects.filter(
            Q(is_helpful=False) | Q(feedback_score__lte=2) | unanswered
        ).order_by("created_at")[:limit]

        generated_at = timezone.now().astimezone(datetime_timezone.utc)
        version = generated_at.strftime("%Y%m%dT%H%M%SZ")
        queue_path = output_dir / f"review_queue_{version}.jsonl"
        manifest_path = output_dir / f"review_queue_{version}.manifest.json"

        count = 0
        languages = set()
        intents = set()
        with queue_path.open("w", encoding="utf-8") as output:
            for interaction in queryset:
                record = {
                    "record_id": f"chat-{interaction.pk}",
                    "subject_id": _subject_id(interaction.session_id),
                    "query": _scrub_text(interaction.query),
                    "response": _scrub_text(interaction.response),
                    "feedback_text": _scrub_text(interaction.feedback_text),
                    "is_helpful": interaction.is_helpful,
                    "feedback_score": interaction.feedback_score,
                    "intent": interaction.intent,
                    "language": interaction.language,
                    "state": interaction.state,
                    "ai_tier": interaction.ai_tier,
                    "data_source": interaction.data_source,
                    "created_at": interaction.created_at.isoformat(),
                    "review_status": "pending_agronomist_review",
                    "source_verified": False,
                    "safety_review_passed": False,
                    "training_eligible": False,
                    "reviewer_id": None,
                    "source_references": [],
                }
                output.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
                languages.add(interaction.language)
                intents.add(interaction.intent)

        manifest = {
            "schema_version": "1.0",
            "dataset_version": version,
            "generated_at": generated_at.isoformat(),
            "purpose": "human_review_queue",
            "record_count": count,
            "languages": sorted(filter(None, languages)),
            "intents": sorted(filter(None, intents)),
            "contains_raw_pii": False,
            "review_required": True,
            "training_eligible": False,
            "promotion_stage": "review_queue_only",
            "records_file": queue_path.name,
        }
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self.stdout.write(self.style.SUCCESS(f"Exported {count} pending review records"))
        self.stdout.write(str(manifest_path))
