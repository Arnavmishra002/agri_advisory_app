"""
KrishiMitra — Ollama / Qwen Chat Service v2
============================================
Implements RAG context compression (RAG-2) on top of the original service:

  - build_farming_prompt() now hard-caps RAG context at _MAX_CONTEXT_TOKENS
    (≈1 500 words) instead of sending all retrieved chunks verbatim.
  - Deduplicates chunks before including them.
  - Logs token estimate so you can tune the cap.

Why this matters (from the RAG optimization post):
  "Sending 15 000 tokens to an LLM is often more expensive than retrieving
   the right 1 500."  More tokens = more time spent reading = higher latency.

All other behaviour (Ollama URL, model name, system prompt, streaming) is
unchanged from v1.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import urllib.request
import urllib.error
from typing import Iterator, List, Optional

logger = logging.getLogger(__name__)

OLLAMA_BASE   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
_OLLAMA_CHAT_TIMEOUT_S = int(os.getenv("OLLAMA_CHAT_TIMEOUT_S", "20"))
_OLLAMA_STREAM_TIMEOUT_S = int(os.getenv("OLLAMA_STREAM_TIMEOUT_S", "60"))
_OLLAMA_MAX_TOKENS = max(96, int(os.getenv("OLLAMA_MAX_TOKENS", "320")))
_OLLAMA_STREAM_MAX_TOKENS = max(96, int(os.getenv("OLLAMA_STREAM_MAX_TOKENS", "320")))

# ── Context compression constants (RAG-2) ────────────────────────────────────
# Approximate tokens in a chunk = chars / 4  (rough but fast).
# We cap total RAG context at 1 500 tokens to keep the prompt lean.
_MAX_CONTEXT_CHARS = 6_000   # ≈ 1 500 tokens at 4 chars/token
_MAX_CHUNK_CHARS   = 600     # already applied in retriever, guard here too

# ── System prompt ─────────────────────────────────────────────────────────────
AGRI_SYSTEM_PROMPT = """\
You are KrishiMitra AI — an expert agricultural advisor for Indian farmers.
You have deep knowledge of ICAR guidelines, government schemes, crop management,
and Indian weather patterns.

STRICT RULES:
1. Use ONLY the information provided in the [KNOWLEDGE BASE] section. Never invent facts.
2. CRITICAL — cite EXACT numbers from the knowledge base: MSP values, ETL thresholds,
   and NPK rates. If you see "MSP 2024-25: Rs. 2425/quintal" in the knowledge
   base, quote ₹2,425/q exactly — never round or estimate from memory.
3. If the knowledge base has no relevant information, say so clearly and suggest:
   "Please call Kisan Helpline 1800-180-1551 (free, 24x7) for expert advice."
4. Always cite your source: "As per ICAR guidelines..." or "As per government data..."
5. Prefer organic/IPM methods before recommending chemicals.
6. Respond in the SAME language the farmer used. If Hindi, reply in Hindi.
   If mixed Hindi-English (Hinglish), reply in Hinglish.
7. Use bullet points for action steps. Bold important numbers (MSP and dates).
8. End every response with ONE concrete next step the farmer should take today.
9. SENSOR DATA RULE: Use soil moisture only when [LIVE FIELD SENSOR DATA] contains
   an explicit "Soil Moisture" value from a sensor. Air humidity or weather humidity
   is NOT soil moisture. If field sensor data is not provided, never invent soil
   moisture, NPK, pH, or live field readings.
10. Give a pesticide dose only when the retrieved excerpt includes a named current
    PPQS/CIB&RC label or package-of-practices document and its attributable URL or
    document number. Otherwise ask the farmer to confirm the registered label with KVK.
11. Answer the farmer's exact question in fresh, natural wording. The knowledge
    base is factual evidence, not a stored response: do not copy a retrieved
    paragraph verbatim or add unrelated sections.
12. Start with a direct answer, then give only the useful steps. Ask one short
    clarifying question only when an essential detail is missing.
13. Do not begin with thanks, greetings, or a restatement of the question.
    Prefer a direct answer followed by at most 3-6 short actionable bullets.
14. Keep the complete answer under 120 words and at most 5 bullets. Stop once
    the exact question is answered; do not add generic background or filler.
"""


def _ollama_available() -> bool:
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE}/api/tags")
        with urllib.request.urlopen(req, timeout=3):
            return True
    except Exception:
        return False


def _compress_chunks(chunks: List[str]) -> str:
    """
    RAG-2: Deduplicate and compress RAG chunks to stay within token budget.

    Steps:
      1. Deduplicate by first-80-char fingerprint
      2. Truncate each chunk to _MAX_CHUNK_CHARS
      3. Join with separator, hard-cap at _MAX_CONTEXT_CHARS
      4. Log estimated token count

    Returns the compressed knowledge-base string.
    """
    if not chunks:
        return ""

    seen:    set       = set()
    unique:  List[str] = []
    for c in chunks:
        fp = c[:80]
        if fp not in seen:
            seen.add(fp)
            unique.append(c[:_MAX_CHUNK_CHARS])

    joined = "\n\n---\n\n".join(unique)
    if len(joined) > _MAX_CONTEXT_CHARS:
        joined = joined[:_MAX_CONTEXT_CHARS] + "\n\n[...context compressed for latency]"

    est_tokens = len(joined) // 4
    logger.debug(
        "RAG context: %d raw chunks → %d unique → ~%d tokens",
        len(chunks), len(unique), est_tokens,
    )
    return joined


def build_farming_prompt(
    question: str,
    rag_chunks: List[str],
    verified_knowledge: Optional[str] = None,
    weather_summary: Optional[str] = None,
    market_summary: Optional[str] = None,
    sensor_data: Optional[dict] = None,
    farmer_profile: Optional[dict] = None,
    conversation_history: Optional[List[dict]] = None,
) -> str:
    """
    Assemble the full prompt from all available context.

    RAG-2 change: rag_chunks are compressed via _compress_chunks() before
    inclusion so the prompt stays well within the 1 500-token context budget.
    """
    parts: List[str] = []

    # 1. Exact local KB match. This is more precise than broad vector search
    # and must win if a supplementary RAG chunk is only loosely related.
    verified_knowledge = (verified_knowledge or "").strip()
    if verified_knowledge:
        parts.append(
            "[VERIFIED LOCAL KNOWLEDGE — HIGHEST PRIORITY FACTS]\n"
            "Use these facts to answer the exact question in fresh wording. "
            "Do not contradict them and do not copy the paragraph verbatim.\n"
            + verified_knowledge[:3000]
        )

    # 2. Broader RAG is useful only when there is no exact KB match. Including
    # both duplicates context, slows first-token latency on CPU, and can let a
    # merely similar crop passage distract from the verified answer.
    if not verified_knowledge:
        kb = _compress_chunks(rag_chunks)
        if kb:
            parts.append(
                "[SUPPLEMENTARY RAG KNOWLEDGE]\n"
                "Use only facts relevant to the farmer's exact question.\n" + kb
            )
        else:
            parts.append(
                "[KNOWLEDGE BASE]\n"
                "No specific document matched this query. "
                "Say the knowledge base does not contain enough matched detail. "
                "Do not provide exact chemical doses, legal eligibility, market prices, or disease certainty "
                "unless they are present in another supplied live-data section. Give safe general next steps "
                "and recommend Kisan Helpline 1800-180-1551 for expert confirmation."
            )

    # 2. Live sensor data
    if sensor_data:
        lines = [
            f"Soil Moisture  : {sensor_data.get('moisture_pct', 'N/A')}%  "
            f"({sensor_data.get('moisture_status', 'unknown')})",
            f"Soil pH        : {sensor_data.get('ph', 'N/A')}",
            f"Nitrogen (N)   : {sensor_data.get('nitrogen_kg_ha', 'N/A')} kg/ha",
            f"Phosphorus (P) : {sensor_data.get('phosphorus_kg_ha', 'N/A')} kg/ha",
            f"Potassium (K)  : {sensor_data.get('potassium_kg_ha', 'N/A')} kg/ha",
            f"Temperature    : {sensor_data.get('temp_c', 'N/A')}°C",
            f"Humidity       : {sensor_data.get('humidity_pct', 'N/A')}%",
            f"Data source    : {sensor_data.get('source', 'simulated')}",
        ]
        parts.append("[LIVE FIELD SENSOR DATA]\n" + "\n".join(lines))
    else:
        parts.append(
            "[LIVE FIELD SENSOR DATA]\n"
            "Not provided for this request. Do not infer soil moisture, NPK, pH, "
            "or field sensor readings from weather, air humidity, crop profile, "
            "or general farming knowledge."
        )

    # 3. Weather
    if weather_summary:
        parts.append(f"[LIVE WEATHER DATA]\n{weather_summary}")

    # 4. Market prices
    if market_summary:
        parts.append(f"[MARKET PRICES]\n{market_summary}")

    # 5. Farmer profile
    if farmer_profile:
        profile_lines = []
        for key, label in [
            ("location", "Location"), ("crop", "Current crop"),
            ("season", "Season"), ("farm_size_bigha", "Farm size (bigha)"),
            ("soil_ph", "Soil pH"), ("irrigation_type", "Irrigation"),
        ]:
            val = farmer_profile.get(key)
            if val:
                profile_lines.append(f"{label}: {val}")
        if profile_lines:
            parts.append("[FARMER PROFILE]\n" + "\n".join(profile_lines))

    # 6. Recent conversation (last 4 turns only — keeps context lean)
    if conversation_history:
        history_lines = []
        for msg in conversation_history[-4:]:
            role    = "Farmer" if msg.get("role") == "user" else "KrishiMitra AI"
            content = (msg.get("content") or "").strip()[:200]   # cap each turn
            if content:
                history_lines.append(f"{role}: {content}")
        if history_lines:
            parts.append("[RECENT CONVERSATION]\n" + "\n".join(history_lines))

    # 7. Current question + response instructions
    parts.append(f"[FARMER'S QUESTION]\n{question}")
    parts.append(
        "[YOUR RESPONSE — follow these checks before writing]\n"
        "1. Does the question CONFLICT with sensor data? "
        "(Only check this if [LIVE FIELD SENSOR DATA] contains a real Soil Moisture value; "
        "air humidity is not soil moisture.)\n"
        "2. Is there a weather alert that affects this advice? Mention it FIRST.\n"
        "3. Is your chemical recommendation backed by the knowledge base? "
        "If not, defer to Kisan Helpline 1800-180-1551.\n"
        "Now write your response:"
    )

    prompt = "\n\n".join(parts)
    logger.debug("Prompt total chars: %d (~%d tokens)", len(prompt), len(prompt) // 4)
    return prompt


def chat(
    prompt: str,
    system: str = AGRI_SYSTEM_PROMPT,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.25,
    max_tokens: int = _OLLAMA_MAX_TOKENS,
    timeout: int = _OLLAMA_CHAT_TIMEOUT_S,
) -> str:
    """Blocking chat — returns the full response as a string."""
    if not _ollama_available():
        logger.warning("Ollama unavailable — returning empty result for caller fallback")
        return ""

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        "options": {
            "temperature":    temperature,
            "num_predict":    max_tokens,
            "top_p":          0.9,
            "repeat_penalty": 1.1,
        },
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["message"]["content"].strip()
    except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
        logger.error("Ollama request failed: %s", exc)
        return ""
    except Exception as exc:
        logger.error("Unexpected chat error: %s", exc)
        return ""


def stream_chat(
    prompt: str,
    system: str = AGRI_SYSTEM_PROMPT,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.25,
) -> Iterator[str]:
    """
    Streaming generator — yields text tokens as they arrive from Qwen.
    Use with StreamingResponse in FastAPI for real-time UX.
    """
    if not _ollama_available():
        return

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        "options": {
            "temperature": temperature,
            "num_predict": _OLLAMA_STREAM_MAX_TOKENS,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
        },
        "stream": True,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_OLLAMA_STREAM_TIMEOUT_S) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    if not chunk.get("done"):
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            yield token
                except json.JSONDecodeError:
                    continue
    except Exception as exc:
        logger.error("Stream failed: %s", exc)
        return


def get_model_info() -> dict:
    """Return info about the loaded model."""
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE}/api/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data   = json.loads(resp.read())
            models = data.get("models", [])
            active = next((m for m in models if DEFAULT_MODEL in m["name"]), None)
            if not active:
                active = next(
                    (m for m in models if "krishimitra" in m["name"] or "qwen2.5" in m["name"]),
                    None,
                )
            return {
                "available": True,
                "model":     active["name"] if active else DEFAULT_MODEL,
                "size_gb":   round(active["size"] / 1e9, 1) if active else None,
            }
    except Exception:
        return {"available": False, "model": DEFAULT_MODEL}
