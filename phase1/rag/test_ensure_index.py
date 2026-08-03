import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from . import ensure_index


class EnsureIndexRecoveryTests(unittest.TestCase):
    def test_quarantine_preserves_incompatible_index_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            chroma_dir = Path(temp_dir) / "chroma_db"
            chroma_dir.mkdir()
            (chroma_dir / "chroma.sqlite3").write_text("old-db", encoding="utf-8")
            segment = chroma_dir / "segment-id"
            segment.mkdir()
            (segment / "data.bin").write_bytes(b"old-segment")

            archive = ensure_index.quarantine_incompatible_index(
                chroma_dir,
                "KeyError: _type",
            )

            self.assertIsNotNone(archive)
            self.assertFalse((chroma_dir / "chroma.sqlite3").exists())
            self.assertEqual((archive / "chroma.sqlite3").read_text(), "old-db")
            self.assertEqual((archive / "segment-id" / "data.bin").read_bytes(), b"old-segment")
            self.assertIn("KeyError: _type", (archive / "REASON.txt").read_text())

    @patch("phase1.rag.ensure_index.CHROMA_DIR")
    def test_storage_check_reports_incompatible_chroma(self, chroma_dir):
        chroma_dir.__truediv__.return_value.is_file.return_value = True
        client = MagicMock()
        client.list_collections.side_effect = KeyError("_type")
        fake_chromadb = MagicMock()
        fake_chromadb.PersistentClient.return_value = client

        with patch.dict("sys.modules", {"chromadb": fake_chromadb}):
            readable, reason = ensure_index.index_storage_is_readable()

        self.assertFalse(readable)
        self.assertIn("KeyError", reason)
        self.assertIn("_type", reason)


if __name__ == "__main__":
    unittest.main()
