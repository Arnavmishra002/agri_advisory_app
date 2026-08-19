import json
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from advisory.models import FarmerInteractionLog


class ReviewedLearningExportTests(TestCase):
    def test_export_is_deidentified_and_never_training_ready(self):
        FarmerInteractionLog.objects.create(
            session_id="private-session-123",
            phone_number="+919876543210",
            location_name="Private Village",
            state="Uttar Pradesh",
            latitude=26.123456,
            longitude=81.123456,
            query="Call me at 9876543210 or farmer@example.com, location 26.123456,81.123456",
            response="Weather unavailable. Contact 9876543210.",
            intent="weather",
            language="en",
            ai_tier="rule_based_fallback",
            feedback_score=1,
            is_helpful=False,
            feedback_text="My email is farmer@example.com",
        )

        with tempfile.TemporaryDirectory() as directory:
            call_command("export_review_queue", output_dir=directory, limit=10)
            record_file = next(Path(directory).glob("*.jsonl"))
            manifest_file = next(Path(directory).glob("*.manifest.json"))
            record = json.loads(record_file.read_text(encoding="utf-8").splitlines()[0])
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))

        serialized = json.dumps(record)
        self.assertNotIn("private-session-123", serialized)
        self.assertNotIn("9876543210", serialized)
        self.assertNotIn("farmer@example.com", serialized)
        self.assertNotIn("Private Village", serialized)
        self.assertNotIn("26.123456", serialized)
        self.assertEqual(record["review_status"], "pending_agronomist_review")
        self.assertFalse(record["training_eligible"])
        self.assertFalse(manifest["training_eligible"])
        self.assertTrue(manifest["review_required"])
