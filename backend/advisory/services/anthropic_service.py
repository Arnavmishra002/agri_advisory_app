"""Anthropic Claude service — primary cloud 'brain' for the chatbot.

Mirrors GeminiService.generate() so it can slot into the same tier chain in
chat_intelligence_service. Uses the Messages API over plain ``requests`` (no
extra SDK dependency). Fails soft: returns "" when no key / on any error so the
orchestrator falls through to the next tier (Gemini → local Qwen → rules).

Design goals (why this makes answers 'question-aware', not canned):
  * The caller passes a fully *grounded* prompt built per-request from the
    user's actual question, conversation history, resolved location, live
    weather, live mandi prices, RAG snippets and the farmer's profile. Claude
    composes a fresh answer from that context every time.
  * Truthfulness is preserved: the system prompt forbids inventing prices,
    yields or pesticide doses; numbers must come from the supplied context, and
    the caller still runs _safe_model_text / _has_unverified_market_claim on the
    output.
"""

import os
import logging

import requests

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
# Override via env to match whatever model your key can access.
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest").strip()
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
_TIMEOUT = (5, 30)  # (connect, read) seconds

# Strong, safety-preserving system prompt. The grounded context is supplied in
# the user turn; this fixes *how* Claude must behave.
DEFAULT_SYSTEM_PROMPT = (
    "You are KrishiMitra, an expert agricultural advisor for Indian farmers. "
    "Answer the farmer's ACTUAL question directly and specifically — never reply "
    "with a generic template. Reason about their crop, soil, season, location and "
    "the live data provided, then give practical, actionable guidance.\n\n"
    "STRICT RULES:\n"
    "1. Reply in the SAME language/script the farmer used (Hindi in Devanagari, "
    "English, or the regional language shown in the context).\n"
    "2. Use ONLY the numbers given in the context for prices, weather, MSP, yields "
    "and pesticide doses. NEVER invent or estimate a market price, and never state a "
    "pesticide dose without the ICAR/official attribution present in the context. If "
    "a number is not in the context, say it is currently unavailable and point to the "
    "official source (agmarknet.gov.in, IMD, eNAM 1800-270-0224).\n"
    "3. Be concise and concrete — short paragraphs or bullets a farmer can act on.\n"
    "4. Ground every factual claim in the supplied real-time data / knowledge; if you "
    "are unsure, say so rather than guessing.\n"
    "5. Never claim a disease is confirmed from text alone; recommend verification."
)


def _is_valid_anthropic_key(key: str) -> bool:
    """True only for a real-looking Anthropic key (not blank/placeholder)."""
    if not key:
        return False
    k = key.strip()
    if len(k) < 20:
        return False
    lowered = k.lower()
    if lowered in {"changeme", "your_key", "placeholder", "none", "null"}:
        return False
    return k.startswith("sk-ant")


class ClaudeService:
    """Anthropic Claude client with a Gemini-compatible generate() signature."""

    def __init__(self):
        self.api_key = ANTHROPIC_API_KEY
        self.model = ANTHROPIC_MODEL

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 1600,
        user_query: str = None,
        temperature: float = 0.3,
    ) -> str:
        """Return Claude's answer text, or "" on missing key / any failure."""
        if not _is_valid_anthropic_key(self.api_key):
            return ""
        system = system_prompt.strip() or DEFAULT_SYSTEM_PROMPT
        payload = {
            "model": self.model,
            "max_tokens": int(max_tokens),
            "temperature": float(temperature),
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        try:
            resp = requests.post(
                ANTHROPIC_URL, json=payload, headers=headers, timeout=_TIMEOUT
            )
            if resp.status_code != 200:
                logger.warning(
                    "Claude API %s: %s", resp.status_code, resp.text[:200]
                )
                return ""
            data = resp.json()
            # Messages API returns content as a list of blocks.
            parts = []
            for block in data.get("content", []) or []:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
            return "".join(parts).strip()
        except Exception as exc:  # network, JSON, etc. — fail soft
            logger.warning("Claude request failed: %s", exc)
            return ""


# Module-level singleton, mirroring `gemini_service`.
claude_service = ClaudeService()
