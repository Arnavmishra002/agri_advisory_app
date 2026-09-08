"""Open-model LLM over the network (OpenAI-compatible).

Makes an open LLM (Llama / Qwen / Mixtral …) run *over the internet* with no GPU
host — via any OpenAI-compatible endpoint. Defaults to Groq (free tier, very
fast). This is the production stand-in for the local Ollama tier: when there is
no GPU box running Ollama, this hosted open model still gives real, question-
aware answers instead of falling back to canned rules.

Works with:
  * Groq        — base https://api.groq.com/openai/v1  (default)
  * OpenRouter  — base https://openrouter.ai/api/v1
  * Together    — base https://api.together.xyz/v1
  * A hosted Ollama in OpenAI-compat mode — base http://<host>:11434/v1
Configure with env:
  OPEN_LLM_BASE_URL   (default Groq)
  OPEN_LLM_API_KEY    (falls back to GROQ_API_KEY)
  OPEN_LLM_MODEL      (default llama-3.3-70b-versatile)

Same grounded prompt as the other tiers → answers are composed per-request from
the farmer's question + live data, never pre-stored. Truthfulness guards in the
caller still apply. Fails soft (returns "") so the chain continues.
"""

import os
import logging

import requests
from .api_keys import env_key

logger = logging.getLogger(__name__)

OPEN_LLM_BASE_URL = os.getenv("OPEN_LLM_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
OPEN_LLM_API_KEY = env_key("OPEN_LLM_API_KEY") or env_key("GROQ_API_KEY")
OPEN_LLM_MODEL = os.getenv("OPEN_LLM_MODEL", "llama-3.3-70b-versatile").strip()
_TIMEOUT = (5, 30)

# Reuse the same behavioural contract as the Claude tier for consistency.
DEFAULT_SYSTEM_PROMPT = (
    "You are KrishiMitra, an expert agricultural advisor for Indian farmers. "
    "Answer the farmer's ACTUAL question directly and specifically — never reply "
    "with a generic template. Use the live data in the context (weather, mandi "
    "prices, MSP, soil, profile) and reason about their crop, season and location.\n"
    "Rules: reply in the SAME language/script the farmer used; use ONLY the numbers "
    "given in the context for prices/weather/MSP/doses and never invent them (say "
    "'currently unavailable' and cite the official source if missing); never state a "
    "pesticide dose without the ICAR attribution in the context; be concise and "
    "practical; never claim a disease is confirmed from text alone."
)


def _is_valid_open_llm_key(key: str) -> bool:
    if not key:
        return False
    k = key.strip()
    if len(k) < 12:
        return False
    return k.lower() not in {"changeme", "your_key", "placeholder", "none", "null"}


class OpenLLMService:
    """OpenAI-compatible chat client for a hosted open model. Fails soft."""

    def __init__(self):
        self.api_key = OPEN_LLM_API_KEY
        self.base_url = OPEN_LLM_BASE_URL
        self.model = OPEN_LLM_MODEL

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 1600,
        user_query: str = None,
        temperature: float = 0.3,
    ) -> str:
        """Return the model's answer text, or "" on missing key / any failure."""
        if not _is_valid_open_llm_key(self.api_key):
            return ""
        system = system_prompt.strip() or DEFAULT_SYSTEM_PROMPT
        payload = {
            "model": self.model,
            "max_tokens": int(max_tokens),
            "temperature": float(temperature),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload, headers=headers, timeout=_TIMEOUT,
            )
            if resp.status_code != 200:
                logger.warning("Open LLM %s: %s", resp.status_code, resp.text[:200])
                return ""
            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                return ""
            return (choices[0].get("message") or {}).get("content", "").strip()
        except Exception as exc:  # network / JSON — fail soft
            logger.warning("Open LLM request failed: %s", exc)
            return ""


open_llm_service = OpenLLMService()
