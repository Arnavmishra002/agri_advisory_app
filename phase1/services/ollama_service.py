"""
KrishiMitra — Ollama / Qwen Chat Service
=========================================
Replaces Gemini API with local Qwen 2.5 7B.
Zero cloud cost, full offline capability, data stays on-device.
"""

from __future__ import annotations
import json
import logging
import urllib.request
import urllib.error
from typing import Iterator, List, Optional

logger = logging.getLogger(__name__)

OLLAMA_BASE   = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:7b"

# ── System prompt for farming advisor role ────────────────────────────────────
AGRI_SYSTEM_PROMPT = """\
You are KrishiMitra AI — an expert agricultural advisor for Indian farmers.
You have deep knowledge of ICAR (Indian Council of Agricultural Research) guidelines,
government schemes, crop management, and Indian weather patterns.

STRICT RULES:
1. Use ONLY the information provided in the [KNOWLEDGE BASE] section. Never invent facts.
2. CRITICAL — cite EXACT numbers from the knowledge base: MSP values, chemical doses,
   ETL thresholds, NPK rates. If you see "MSP 2024-25: Rs. 2275/quintal" in the knowledge
   base, quote ₹2,275/q exactly — never round or estimate from memory.
3. If the knowledge base has no relevant information, say so clearly and suggest:
   "Please call Kisan Helpline 1800-180-1551 (free, 24x7) for expert advice."
4. Always cite your source: "As per ICAR guidelines..." or "As per government data..."
5. Prefer organic/IPM methods before recommending chemicals.
6. Respond in the SAME language the farmer used. If Hindi, reply in Hindi.
   If mixed Hindi-English (Hinglish), reply in Hinglish.
7. Use bullet points for action steps. Bold important numbers (MSP, doses, dates).
8. End every response with ONE concrete next step the farmer should take today.
9. SENSOR DATA RULE: If [LIVE FIELD SENSOR DATA] shows soil moisture is Adequate (50-65%)
   or High (>65%), never recommend irrigation. State the actual % and say irrigation is
   not needed.
10. Never recommend a pesticide dose higher than label-approved amount.
"""


def _ollama_available() -> bool:
    """Check if Ollama server is running."""
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE}/api/tags")
        with urllib.request.urlopen(req, timeout=3):
            return True
    except Exception:
        return False


def build_farming_prompt(
    question: str,
    rag_chunks: List[str],
    weather_summary: Optional[str] = None,
    market_summary: Optional[str] = None,
    sensor_data: Optional[dict] = None,
    farmer_profile: Optional[dict] = None,
    conversation_history: Optional[List[dict]] = None,
) -> str:
    """
    Assemble the full prompt from all available context.
    Everything is clearly labelled so Qwen knows what to trust.
    """
    parts: List[str] = []

    # 1. Knowledge base (RAG — highest trust)
    if rag_chunks:
        kb = "\n\n---\n\n".join(rag_chunks)
        parts.append(f"[KNOWLEDGE BASE — authoritative, cite these facts]\n{kb}")
    else:
        parts.append(
            "[KNOWLEDGE BASE]\n"
            "No specific document matched this query. "
            "Answer from general agricultural knowledge but flag that you are not citing a specific source."
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

    # 3. Weather
    if weather_summary:
        parts.append(f"[LIVE WEATHER DATA]\n{weather_summary}")

    # 4. Market prices
    if market_summary:
        parts.append(f"[MARKET PRICES]\n{market_summary}")

    # 5. Farmer profile
    if farmer_profile:
        profile_lines = []
        if farmer_profile.get("location"):
            profile_lines.append(f"Location: {farmer_profile['location']}")
        if farmer_profile.get("crop"):
            profile_lines.append(f"Current crop: {farmer_profile['crop']}")
        if farmer_profile.get("season"):
            profile_lines.append(f"Season: {farmer_profile['season']}")
        if profile_lines:
            parts.append("[FARMER PROFILE]\n" + "\n".join(profile_lines))

    # 6. Recent conversation history (last 6 turns)
    if conversation_history:
        history_lines = []
        for msg in conversation_history[-6:]:
            role    = "Farmer" if msg.get("role") == "user" else "KrishiMitra AI"
            content = (msg.get("content") or "").strip()
            if content:
                history_lines.append(f"{role}: {content}")
        if history_lines:
            parts.append("[RECENT CONVERSATION]\n" + "\n".join(history_lines))

    # 7. Current question + evaluation instructions
    parts.append(f"[FARMER'S QUESTION]\n{question}")
    parts.append(
        "[YOUR RESPONSE — follow these checks before writing]\n"
        "1. Does the question CONFLICT with sensor data? "
        "(e.g. asking to water but moisture is Adequate → explain no irrigation needed)\n"
        "2. Is there a weather alert that affects this advice? Mention it FIRST.\n"
        "3. Is your chemical recommendation backed by the knowledge base? "
        "If not, defer to Kisan Helpline 1800-180-1551.\n"
        "Now write your response:"
    )

    return "\n\n".join(parts)


def chat(
    prompt: str,
    system: str = AGRI_SYSTEM_PROMPT,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.25,
    max_tokens: int = 1200,
    timeout: int = 90,
) -> str:
    """
    Blocking chat — returns the full response as a string.
    Falls back to a helpful offline message if Ollama is down.
    """
    if not _ollama_available():
        logger.warning("Ollama unavailable — returning offline message")
        return (
            "माफ़ करें, AI सेवा अभी ऑफलाइन है। "
            "कृपया Kisan Helpline 1800-180-1551 पर कॉल करें (Free, 24x7).\n\n"
            "Sorry, AI service is currently offline. "
            "Please call Kisan Helpline 1800-180-1551 (Free, 24x7)."
        )

    payload = json.dumps({
        "model":  model,
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
    except urllib.error.URLError as exc:
        logger.error("Ollama request failed: %s", exc)
        return (
            "AI सेवा में त्रुटि। "
            "Kisan Helpline: 1800-180-1551 पर कॉल करें।"
        )
    except Exception as exc:
        logger.error("Unexpected chat error: %s", exc)
        raise


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
        yield "AI सेवा ऑफलाइन है। Kisan Helpline: 1800-180-1551"
        return

    payload = json.dumps({
        "model":  model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        "options": {"temperature": temperature, "top_p": 0.9},
        "stream": True,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
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
        yield "\n[Stream error — Kisan Helpline: 1800-180-1551]"


def get_model_info() -> dict:
    """Return info about the loaded model."""
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE}/api/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            models = data.get("models", [])
            qwen = next((m for m in models if "qwen2.5" in m["name"]), None)
            return {
                "available": True,
                "model": qwen["name"] if qwen else DEFAULT_MODEL,
                "size_gb": round(qwen["size"] / 1e9, 1) if qwen else None,
            }
    except Exception:
        return {"available": False, "model": DEFAULT_MODEL}
