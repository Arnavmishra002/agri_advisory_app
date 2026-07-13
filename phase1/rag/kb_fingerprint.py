#!/usr/bin/env python3
"""Deterministic fingerprint for the source documents behind the RAG index."""

from __future__ import annotations

import hashlib
from pathlib import Path


SUPPORTED_SUFFIXES = frozenset({".txt", ".pdf"})


def knowledge_fingerprint(kb_dir: Path) -> str:
    """Hash relative paths and bytes so additions, removals and edits are detected."""
    digest = hashlib.sha256()
    paths = sorted(
        path
        for path in kb_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )
    for path in paths:
        relative = path.relative_to(kb_dir).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        content = path.read_bytes()
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    print(knowledge_fingerprint(root / "knowledge_base"))
