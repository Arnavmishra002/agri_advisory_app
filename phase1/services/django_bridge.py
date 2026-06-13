"""
KrishiMitra — Django ↔ Phase 1 Bridge
======================================
Adds Qwen + RAG as a fallback tier inside the existing
chat_intelligence_service.py answer() method.

Priority chain (updated):
    1. Gemini API (if key is valid)
    2. Qwen 2.5 7B + RAG  ← NEW (if Ollama is running on localhost:8001)
    3. Rule-based fallback (always available)

To activate, add this ONE call in chat_intelligence_service.py answer():
    from phase1.services.django_bridge import qwen_rag_answer
    ...
    if not has_gemini:
        qwen_resp = qwen_rag_answer(query, ctx, lang, history, sc, wc)
        if qwen_resp:
            return {... "response": qwen_resp, "data_source": "Qwen 2.5 7B + RAG" ...}
    # fall through to rule-based

This file has NO Django dependencies — it calls the Phase 1 FastAPI server
via HTTP, so there are no import conflicts between the two environments.
"""

from __future__ import annotations
import json
import logging
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PHASE1_BASE = "http://localhost:8001"   # Phase 1 FastAPI server


def _phase1_available() -> bool:
    """Check if the Phase 1 FastAPI server is running."""
    try:
        req = urllib.request.Request(f"{PHASE1_BASE}/health")
        with urllib.request.urlopen(req, timeout=2):
            return True
    except Exception:
        return False


def qwen_rag_answer(
    query: str,
    location: str,
    latitude: float,
    longitude: float,
    language: str = "hi",
    history: Optional[List[Dict[str, Any]]] = None,
    sensor_context: Optional[Dict[str, Any]] = None,
    crop: Optional[str] = None,
    season: Optional[str] = None,
    timeout: int = 60,
) -> Optional[str]:
    """
    Ask the Phase 1 Qwen+RAG server and return the response text.
    Returns None if Phase 1 server is unavailable (caller falls through to rule-based).
    """
    if not _phase1_available():
        logger.debug("Phase 1 server not running — skipping Qwen fallback")
        return None

    payload = json.dumps({
        "query":          query,
        "language":       language,
        "location":       location,
        "latitude":       latitude,
        "longitude":      longitude,
        "crop":           crop,
        "season":         season,
        "history":        history or [],
        "sensor_context": sensor_context,
        "stream":         False,
    }, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        f"{PHASE1_BASE}/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            response = data.get("response", "").strip()
            if response:
                logger.info(
                    "Qwen+RAG answered query '%s...' using %d RAG chunks from %s",
                    query[:40],
                    data.get("rag_chunks", 0),
                    data.get("rag_sources", []),
                )
            return response or None
    except urllib.error.URLError as exc:
        logger.warning("Phase 1 server request failed: %s", exc)
        return None
    except Exception as exc:
        logger.error("Unexpected Phase 1 bridge error: %s", exc)
        return None
