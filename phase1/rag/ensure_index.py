#!/usr/bin/env python3
"""Refresh the local Chroma index when knowledge source files change."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from rag.kb_fingerprint import knowledge_fingerprint
else:
    from .kb_fingerprint import knowledge_fingerprint


ROOT = Path(__file__).resolve().parents[1]
KB_DIR = ROOT / "knowledge_base"
CHROMA_DIR = ROOT / "chroma_db"
FINGERPRINT_FILE = CHROMA_DIR / "kb_fingerprint.txt"


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
