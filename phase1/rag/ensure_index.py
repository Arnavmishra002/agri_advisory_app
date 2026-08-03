#!/usr/bin/env python3
"""Refresh the local Chroma index when knowledge source files change."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from rag.kb_fingerprint import knowledge_fingerprint
else:
    from .kb_fingerprint import knowledge_fingerprint


ROOT = Path(__file__).resolve().parents[1]
KB_DIR = ROOT / "knowledge_base"
CHROMA_DIR = ROOT / "chroma_db"
FINGERPRINT_FILE = CHROMA_DIR / "kb_fingerprint.txt"


def index_storage_is_readable() -> Tuple[bool, str]:
    """Distinguish a stale/missing index from an incompatible Chroma store."""
    if not (CHROMA_DIR / "chroma.sqlite3").is_file():
        return True, ""
    try:
        import chromadb

        chromadb.PersistentClient(path=str(CHROMA_DIR)).list_collections()
        return True, ""
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def quarantine_incompatible_index(
    chroma_dir: Path,
    reason: str,
) -> Optional[Path]:
    """Preserve incompatible generated index files before a clean rebuild."""
    if not chroma_dir.exists():
        return None
    children = [child for child in chroma_dir.iterdir() if child.name != "_incompatible"]
    if not children:
        return None

    archive_root = chroma_dir / "_incompatible"
    archive_dir = archive_root / time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    suffix = 1
    while archive_dir.exists():
        archive_dir = archive_root / (
            time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + f"-{suffix}"
        )
        suffix += 1
    archive_dir.mkdir(parents=True)
    for child in children:
        shutil.move(str(child), str(archive_dir / child.name))
    (archive_dir / "REASON.txt").write_text(reason + "\n", encoding="utf-8")
    return archive_dir


def index_is_current() -> bool:
    if not FINGERPRINT_FILE.is_file():
        return False
    try:
        if FINGERPRINT_FILE.read_text(encoding="ascii").strip() != knowledge_fingerprint(KB_DIR):
            return False
        import chromadb

        collection = chromadb.PersistentClient(path=str(CHROMA_DIR)).get_collection("krishimitra_kb")
        return collection.count() > 0
    except Exception:
        return False


def main() -> int:
    if index_is_current():
        print("RAG index is current")
        return 0

    storage_readable, storage_error = index_storage_is_readable()
    if not storage_readable:
        archive_dir = quarantine_incompatible_index(CHROMA_DIR, storage_error)
        if archive_dir:
            print(
                "Archived incompatible RAG index before rebuild: "
                f"{archive_dir.relative_to(CHROMA_DIR)}"
            )

    print("RAG source changed or index missing; rebuilding before Phase 1 starts")
    result = subprocess.run([sys.executable, str(ROOT / "rag" / "ingest.py")], check=False)
    if result.returncode == 0:
        return 0

    if os.getenv("RAG_INDEX_REQUIRED", "false").strip().lower() in {"1", "true", "yes"}:
        print("RAG index rebuild failed and RAG_INDEX_REQUIRED=true", file=sys.stderr)
        return result.returncode

    print("RAG index rebuild failed; Phase 1 will start in degraded mode", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
