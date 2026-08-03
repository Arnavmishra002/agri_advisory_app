import tempfile
import unittest
from pathlib import Path

from .ingest import CHUNK_SIZE, chunk_text
from .crop_profile_snapshot import load_crop_terms
from .kb_fingerprint import knowledge_fingerprint


class ChunkTextTests(unittest.TestCase):
    def test_generated_crop_profile_snapshot_covers_full_catalog(self):
        snapshot = (
            Path(__file__).resolve().parents[1]
            / "knowledge_base"
            / "crops"
            / "indian_crop_profiles_202.txt"
        )
        self.assertTrue(snapshot.exists())
        text = snapshot.read_text(encoding="utf-8")
        self.assertEqual(text.count("CROP_ID:"), 202)
        self.assertIn("CROP_ID: rambutan", text)
        self.assertIn("CROP_ID: saffron", text)

        chunks = chunk_text(text, snapshot.name, "crops")
        tagged_crops = {
            crop
            for chunk in chunks
            for crop in chunk["crops"].split("|")
            if crop != "general"
        }
        self.assertTrue(set(load_crop_terms()).issubset(tagged_crops))
        self.assertTrue(
            all(
                chunk["text"].startswith("CROP_ID:")
                for chunk in chunks
                if chunk["crops"] != "general"
            )
        )

    def test_long_sections_are_split_with_metadata(self):
        text = (
            "SHORT INTRO\nSmall wheat note.\n\n"
            "DISEASE MANAGEMENT\n"
            + "Yellow rust control and wheat fungicide dose. " * 80
        )

        chunks = chunk_text(text, "wheat_diseases_rust_smut.txt", "pests")

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk["text"]) <= CHUNK_SIZE for chunk in chunks))
        for idx, chunk in enumerate(chunks):
            self.assertEqual(chunk["source_file"], "wheat_diseases_rust_smut.txt")
            self.assertEqual(chunk["source_stem"], "wheat_diseases_rust_smut")
            self.assertEqual(chunk["category"], "pests")
            self.assertEqual(chunk["chunk_index"], idx)
            self.assertIn("wheat", chunk["crops"])
            self.assertIn("disease", chunk["topics"])
            self.assertEqual(chunk["char_count"], len(chunk["text"]))

    def test_hindi_crop_and_topic_tags_are_detected(self):
        chunks = chunk_text(
            "सरसों में माहू कीट नियंत्रण और सिंचाई सलाह। "
            "फसल की नियमित निगरानी करें और जरूरत होने पर सुरक्षित IPM उपाय अपनाएं।",
            "mustard_icar.txt",
            "crops",
        )

        self.assertEqual(chunks[0]["language"], "hi-en")
        self.assertIn("mustard", chunks[0]["crops"])
        self.assertIn("pest", chunks[0]["topics"])
        self.assertIn("irrigation", chunks[0]["topics"])

    def test_crop_tags_do_not_match_inside_unrelated_words(self):
        chunks = chunk_text(
            "Only fresh official prices may be shown to farmers. Estimates are prohibited.",
            "market_policy.txt",
            "schemes",
        )

        self.assertEqual(chunks[0]["crops"], "general")


class KnowledgeFingerprintTests(unittest.TestCase):
    def test_fingerprint_changes_for_content_addition_edit_and_removal(self):
        with tempfile.TemporaryDirectory() as temporary:
            kb_dir = Path(temporary)
            crops = kb_dir / "crops"
            crops.mkdir()
            first = crops / "wheat.txt"
            first.write_text("wheat irrigation", encoding="utf-8")

            initial = knowledge_fingerprint(kb_dir)
            first.write_text("wheat rust management", encoding="utf-8")
            edited = knowledge_fingerprint(kb_dir)
            self.assertNotEqual(initial, edited)

            second = crops / "rice.txt"
            second.write_text("rice water management", encoding="utf-8")
            added = knowledge_fingerprint(kb_dir)
            self.assertNotEqual(edited, added)

            second.unlink()
            self.assertEqual(edited, knowledge_fingerprint(kb_dir))

    def test_fingerprint_ignores_non_knowledge_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            kb_dir = Path(temporary)
            source = kb_dir / "guide.txt"
            source.write_text("crop guide", encoding="utf-8")
            initial = knowledge_fingerprint(kb_dir)
            (kb_dir / ".gitkeep").write_text("changed", encoding="utf-8")
            self.assertEqual(initial, knowledge_fingerprint(kb_dir))


if __name__ == "__main__":
    unittest.main()
