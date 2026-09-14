import json
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase


class LearningStagingTests(SimpleTestCase):
    def record(self):
        return {
            "record_id": "chat-1", "review_status": "approved",
            "reviewer_id": "agronomist-1", "privacy_review_passed": True,
            "source_verified": True, "safety_review_passed": True,
            "consent_verified": True, "knowledge_type": "stable_agronomy",
            "reviewed_question": "What should I check before applying fertilizer?",
            "reviewed_answer": "Check a recent soil test and crop stage first.",
            "source_references": ["https://icar.gov.in/"],
            "query": "Private raw query", "response": "Untrusted AI answer",
        }

    def stage(self, records):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "review.jsonl"
            output = Path(directory) / "staging.json"
            source.write_text("\n".join(json.dumps(row) for row in records))
            call_command("stage_reviewed_learning", input=str(source), output=str(output))
            return json.loads(output.read_text())

    def test_pending_feedback_is_rejected(self):
        record = self.record()
        record["review_status"] = "pending_agronomist_review"
        with self.assertRaises(CommandError):
            self.stage([record])

    def test_all_reviews_required_and_strictly_boolean(self):
        for key in ("privacy_review_passed", "source_verified", "safety_review_passed", "consent_verified"):
            record = self.record()
            record[key] = "true"
            with self.subTest(key=key), self.assertRaises(CommandError):
                self.stage([record])

    def test_live_prices_cannot_become_permanent_knowledge(self):
        record = self.record()
        record["knowledge_type"] = "mandi_price"
        with self.assertRaises(CommandError):
            self.stage([record])

    def test_only_reviewed_text_is_staged_and_never_automatically_promoted(self):
        bundle = self.stage([self.record()])
        self.assertNotIn("Private raw query", json.dumps(bundle))
        self.assertNotIn("Untrusted AI answer", json.dumps(bundle))
        self.assertFalse(bundle["training_eligible"])
        self.assertFalse(bundle["production_eligible"])
        self.assertEqual(bundle["promotion_stage"], "awaiting_evaluation")
        self.assertEqual(len(bundle["content_sha256"]), 64)

    def test_empty_batch_and_duplicate_records_rejected(self):
        for rows in ([], [self.record(), self.record()]):
            with self.assertRaises(CommandError):
                self.stage(rows)

    def test_missing_or_credential_bearing_sources_rejected(self):
        for references in ([], ["http://icar.gov.in/"], ["https://user:password@example.com/"]):
            record = self.record()
            record["source_references"] = references
            with self.assertRaises(CommandError):
                self.stage([record])

    def test_existing_artifact_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.jsonl"
            output = Path(directory) / "version.json"
            source.write_text(json.dumps(self.record()))
            output.write_text("previous version")
            with self.assertRaises(CommandError):
                call_command("stage_reviewed_learning", input=str(source), output=str(output))
            self.assertEqual(output.read_text(), "previous version")
