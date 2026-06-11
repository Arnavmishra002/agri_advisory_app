#!/usr/bin/env python3
"""
Crop-aware chat intelligence: NLP intent routing + official data grounding.

Answers are built from live weather, mandi (Agmarknet/data.gov.in), crop advisory
engine, MSP, and government schemes — then summarized by Gemini with strict
grounding rules (or rule-based fallback when API key is absent).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .crop_catalog import crop_catalog
from .crop_recommendation_engine import crop_recommendation_engine
from .language_service import (
    normalise_language_code,
    get_gemini_language_instruction,
    get_language_for_state,
    SUPPORTED_LANGUAGES,
)
from .location_context import LocationContext
from .unified_realtime_service import (
    MSP_2024_25,
    gemini_service,
    market_service,
    schemes_service,
    weather_service,
)

logger = logging.getLogger(__name__)

# Intent labels returned to the client
INTENT_CROP_RECOMMENDATION = "crop_recommendation"
INTENT_MARKET_PRICE = "market_price"
INTENT_WEATHER = "weather"
INTENT_GOVERNMENT_SCHEME = "government_scheme"
INTENT_PEST_DISEASE = "pest_disease"
INTENT_SOIL = "soil"
INTENT_IRRIGATION = "irrigation"
INTENT_FERTILIZER = "fertilizer"
INTENT_CROP_INFO = "crop_info"
INTENT_GREETING = "greeting"
INTENT_GENERAL = "general"

STAPLE_FOR_CHAT = ["wheat", "rice", "maize", "mustard", "tomato", "onion", "potato"]

_INTENT_PATTERNS: List[Tuple[str, List[str]]] = [
    (INTENT_GREETING, [
        r"\b(hi|hello|namaste|namaskar|नमस्ते|नमस्कार|hey)\b",
    ]),
    (INTENT_CROP_RECOMMENDATION, [
        r"crop\s*(suggest|recommend|advice|choice)",
        r"which\s+crop",
        r"what\s+(crop|fasal)\s+(to\s+)?(grow|plant|sow)",
        r"(kaunsi|konsi|कौन\s*सी)\s*(fasal|फसल)",
        r"फसल\s*(सुझाव|सिफारिश|बताओ|चुन|चुनें)",
        r"fasal\s*(suggest|recommend|kaun)",
        r"best\s+crop\s+for",
        r"खेती\s*के\s*लिए\s*फसल",
    ]),
    (INTENT_MARKET_PRICE, [
        r"\b(msp|mandi|market\s*price|bhav|भाव|मंडी)\b",
        r"price\s+of",
        r"की\s*कीमत",
        r"बिक्री\s*मूल्य",
        r"modal\s*price",
    ]),
    (INTENT_WEATHER, [
        r"\b(weather|mausam|मौसम|barish|बारिश|rain|forecast)\b",
        r"imd\b",
        r"सिंचाई\s*का\s*समय",
        r"बुवाई\s*का\s*समय",
    ]),
    (INTENT_GOVERNMENT_SCHEME, [
        r"\b(pm[- ]?kisan|pmfby|kcc|kusum|enam|scheme|yojana|योजना)\b",
        r"सब्सिडी",
        r"loan\s+for\s+farmer",
        r"किसान\s*क्रेडिट",
    ]),
    (INTENT_PEST_DISEASE, [
        r"\b(pest|disease|keet|kit|rog|रोग|कीट|blight|blast)\b",
        r"उपचार",
        r"सफेद\s*मक्खी",
        r"पीली\s*पत्ती",
    ]),
    (INTENT_SOIL, [
        r"\b(soil|mitti|मिट्टी|npk|ph)\b",
        r"soil\s*health",
        r"मिट्टी\s*जांच",
    ]),
    (INTENT_IRRIGATION, [
        r"\b(irrigation|sinchai|सिंचाई|drip|sprinkler)\b",
        r"पानी\s*देना",
    ]),
    (INTENT_FERTILIZER, [
        r"\b(urea|dap|fertilizer|urvarak|उर्वरक|npk)\b",
        r"खाद\s*डाल",
    ]),
]


class ChatIntelligenceService:
    """Route farmer queries to official data, then generate grounded answers."""

    SYSTEM_PROMPT = """You are KrishiMitra AI — a trusted digital assistant for Indian farmers.

STRICT RULES (never break):
1. Use ONLY facts from the "Official live data" section below. Do not invent prices, MSP, weather, or schemes.
2. If data is missing, say clearly and point to: Agmarknet (agmarknet.gov.in), data.gov.in, IMD (mausam.imd.gov.in), PM-Kisan (pmkisan.gov.in), Kisan Call Centre 1800-180-1551.
3. Distinguish MSP (government minimum) from mandi modal price (market).
4. Prefer organic / IPM before chemical pesticides; mention label dose and safety if chemicals are needed.
5. Match the user's language: Hindi → Hindi, English → English, Hinglish → simple Hinglish.
6. Be practical, short paragraphs, bullet points for steps.
7. For crop recommendations, cite suitability scores and reasons from the data block.
8. For pest/disease: recommend KrishiRaksha photo upload in the app for accurate diagnosis; give only general ICAR-aligned guidance without guessing the disease from text alone.

Never claim you inspected a photo. Never make up mandi names or today's prices."""

    def answer(
        self,
        query: str,
        ctx: LocationContext,
        language: str = "hi",
    ) -> Dict[str, Any]:
        query = (query or "").strip()
        if not query:
            no_query = {
                "hi": "कृपया अपना सवाल लिखें।",
                "en": "Please type your question.",
                "bn": "অনুগ্রহ করে আপনার প্রশ্ন লিখুন।",
                "te": "దయచేసి మీ ప్రశ్న రాయండి.",
                "mr": "कृपया आपला प्रश्न लिहा.",
                "ta": "தயவுசெய்து உங்கள் கேள்வியை தட்டச்சு செய்யுங்கள்.",
                "gu": "કૃપા કરી તમારો પ્રશ્ન લખો.",
                "kn": "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಟೈಪ್ ಮಾಡಿ.",
                "ml": "ദയവായി നിങ്ങളുടെ ചോദ്യം ടൈപ്പ് ചെയ്യുക.",
                "pa": "ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ ਸਵਾਲ ਟਾਈਪ ਕਰੋ।",
                "or": "ଦୟାକରି ଆପଣଙ୍କ ପ୍ରଶ୍ନ ଲିଖନ୍ତୁ।",
                "as": "অনুগ্ৰহ কৰি আপোনাৰ প্ৰশ্ন লিখক।",
            }
            return {
                "response": no_query.get(normalise_language_code(language), no_query["hi"]),
                "intent": INTENT_GENERAL,
                "sources": [],
                "crop_suggestions": [],
            }

        lang = normalise_language_code(language)

        # Auto-detect state language if not explicitly provided and language is "auto"
        if language == "auto" and ctx.state:
            lang = get_language_for_state(ctx.state)

        intent, crops_mentioned = self.classify_query(query)
        context_block, sources = self._build_official_context(ctx, query, intent, crops_mentioned)

        loc = ctx.display_name
        if ctx.state:
            loc = f"{loc}, {ctx.state}"

        # Build multi-language instruction for Gemini
        lang_instruction = get_gemini_language_instruction(lang)

        user_prompt = f"""Farmer location: {loc} (GPS: {ctx.latitude:.4f}, {ctx.longitude:.4f})
{lang_instruction}
Detected intent: {intent}
Crops mentioned: {', '.join(c['name'] for c in crops_mentioned) or 'none'}

=== Official live data (authoritative) ===
{context_block}

=== Farmer question ===
{query}

Answer using the official data above. If crop recommendation was asked, list top crops with scores and reasons."""

        response_text = gemini_service.generate(
            user_prompt,
            self.SYSTEM_PROMPT,
            max_tokens=1200,
            user_query=query,
            temperature=0.35,
        )

        crop_suggestions = self._crop_suggestions_for_intent(ctx, intent, crops_mentioned, lang=lang)

        return {
            "response": response_text,
            "intent": intent,
            "sources": sources,
            "crops_detected": [c["name"] for c in crops_mentioned],
            "crop_suggestions": crop_suggestions,
            "language": lang,
            "data_source": "Official gov APIs + KrishiMitra advisory engine"
            + (" + Gemini" if gemini_service.api_key else " (rule-based)"),
            "timestamp": datetime.now().isoformat(),
        }

    def classify_query(self, query: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Keyword + catalog NLP: intent and crops mentioned."""
        q = query.lower().strip()
        crops_mentioned = self._detect_crops(query)

        for intent, patterns in _INTENT_PATTERNS:
            for pat in patterns:
                if re.search(pat, q, re.IGNORECASE):
                    if intent == INTENT_GREETING and len(q) > 40:
                        continue
                    return intent, crops_mentioned

        if crops_mentioned and any(
            w in q for w in ("kaise", "how", "kab", "when", "kitna", "खेती", "grow", "sow", "बुवाई")
        ):
            return INTENT_CROP_INFO, crops_mentioned

        if crops_mentioned:
            return INTENT_CROP_INFO, crops_mentioned

        return INTENT_GENERAL, crops_mentioned

    def _detect_crops(self, query: str) -> List[Dict[str, Any]]:
        found: List[Dict[str, Any]] = []
        seen = set()
        tokens = re.split(r"[\s,?.!;]+", query.lower())
        for length in (3, 2, 1):
            for i in range(len(tokens) - length + 1):
                phrase = " ".join(tokens[i : i + length])
                if len(phrase) < 2:
                    continue
                norm = crop_catalog.normalize(phrase)
                if norm and norm["id"] not in seen:
                    seen.add(norm["id"])
                    found.append(norm)
        if not found:
            results = crop_catalog.search(query, limit=3)
            for r in results:
                if r["id"] not in seen:
                    seen.add(r["id"])
                    found.append(r)
        return found[:5]

    def _build_official_context(
        self,
        ctx: LocationContext,
        query: str,
        intent: str,
        crops: List[Dict[str, Any]],
    ) -> Tuple[str, List[str]]:
        lines: List[str] = []
        sources: List[str] = []

        weather = weather_service.get_weather(
            ctx.query_label, ctx.latitude, ctx.longitude
        )
        cur = weather.get("current") or {}
        lines.append(
            f"Weather (Open-Meteo/IMD-aligned): {cur.get('temperature')}°C, "
            f"{cur.get('condition')}, humidity {cur.get('humidity')}%, "
            f"wind {cur.get('wind_speed')} km/h"
        )
        if weather.get("farming_advice"):
            lines.append(f"Farming advice: {weather['farming_advice']}")
        sources.append(weather.get("data_source", "Open-Meteo weather"))

        forecast = weather.get("forecast") or []
        if forecast:
            lines.append("7-day forecast (sample):")
            for day in forecast[:3]:
                lines.append(
                    f"  - {day.get('date')}: max {day.get('max_temp')}°C, "
                    f"rain {day.get('rainfall_mm', 0)} mm"
                )

        prices = market_service.get_prices(
            ctx.query_label,
            lat=ctx.latitude,
            lon=ctx.longitude,
            state=ctx.state or None,
        )
        sources.append(prices.get("data_source", "Mandi prices"))

        if intent in (INTENT_MARKET_PRICE, INTENT_GENERAL, INTENT_CROP_INFO) or crops:
            if not prices.get("is_live"):
                lines.append(
                    "Live mandi prices unavailable — set DATA_GOV_IN_API_KEY in .env "
                    "(https://data.gov.in/user/register). I will not quote estimated mandi prices."
                )
            else:
                lines.append("Live mandi prices (₹/quintal, official feed):")
                top = [
                    c for c in (prices.get("top_crops") or [])
                    if c.get("is_live") or c.get("price_source") == "live_mandi"
                ]
                show = top[:8]
                if crops:
                    ids = {c["id"] for c in crops}
                    matched = [
                        c for c in top
                        if crop_catalog.normalize(str(c.get("crop_name", "")))
                        and crop_catalog.normalize(str(c.get("crop_name", "")))["id"] in ids
                    ]
                    if matched:
                        show = matched + [c for c in top if c not in matched][:5]
                for c in show:
                    lines.append(
                        f"  - {c.get('crop_name')}: modal ₹{c.get('modal_price')}, "
                        f"MSP ₹{c.get('msp')}, mandi {c.get('mandi_name', 'N/A')}"
                    )

        if intent in (INTENT_CROP_RECOMMENDATION, INTENT_GENERAL) or "crop" in query.lower() or "fasal" in query.lower() or "फसल" in query:
            rec = crop_recommendation_engine.recommend_from_context(ctx, language=lang)
            sources.append(rec.get("data_source", "Crop advisory engine"))
            lines.append(
                f"Crop advisory — season {rec.get('season')}, zone {rec.get('agro_zone', rec.get('region'))}:"
            )
            for r in (rec.get("recommendations") or [])[:5]:
                local_name = r.get("crop_name_local") or r.get("crop_name_hindi") or r.get("crop_name", "")
                lines.append(
                    f"  - {r.get('crop_name')} ({local_name}): "
                    f"score {r.get('suitability_score')}%, "
                    f"reason: {r.get('reason_hindi') or r.get('reason', '')}, "
                    f"profit ₹{r.get('profit_per_hectare', 0):,}/ha, "
                    f"MSP ₹{r.get('msp_per_quintal', 0)}/q"
                )

        if intent == INTENT_GOVERNMENT_SCHEME or any(
            w in query.lower() for w in ("yojana", "scheme", "kisan", "योजना")
        ):
            schemes = schemes_service.get_schemes(ctx.query_label)
            sources.append("Government schemes catalog (MoAFW / PM-Kisan / PMFBY)")
            for s in (schemes.get("schemes") or [])[:6]:
                lines.append(
                    f"  - {s.get('name')} / {s.get('name_hindi', '')}: "
                    f"{s.get('benefit', s.get('description', ''))[:120]}"
                )

        for crop in crops[:3]:
            msp = crop.get("msp") or MSP_2024_25.get(crop["id"])
            if msp:
                lines.append(f"MSP 2024-25 for {crop['name']}: ₹{msp}/quintal (Cabinet approved)")

        if intent == INTENT_PEST_DISEASE:
            lines.append(
                "Pest/disease note: Upload a clear leaf/plant photo in KrishiRaksha for "
                "ML-assisted diagnosis. General IPM: monitor weekly, remove infected parts, "
                "use neem oil 5ml/L as first step; follow ICAR package of practices."
            )
            sources.append("ICAR IPM guidelines (general)")

        return "\n".join(lines), list(dict.fromkeys(sources))

    def _crop_suggestions_for_intent(
        self,
        ctx: LocationContext,
        intent: str,
        crops: List[Dict[str, Any]],
        lang: str = "hi",
    ) -> List[Dict[str, Any]]:
        if intent == INTENT_CROP_RECOMMENDATION:
            rec = crop_recommendation_engine.recommend_from_context(ctx, language=lang)
            out = []
            for r in (rec.get("recommendations") or [])[:4]:
                out.append({
                    "type": "crop_recommendation",
                    "crop": r.get("crop_name"),
                    "hindi": r.get("crop_name_hindi"),
                    "local": r.get("crop_name_local"),
                    "score": r.get("suitability_score"),
                    "reason": r.get("reason_hindi") or r.get("reason"),
                    "profit": r.get("profit_per_hectare", 0),
                    "msp": r.get("msp_per_quintal", 0),
                })
            return out

        if intent == INTENT_MARKET_PRICE and crops:
            out = []
            for c in crops[:3]:
                pr = market_service.get_prices(
                    ctx.query_label,
                    crop=c["name"],
                    lat=ctx.latitude,
                    lon=ctx.longitude,
                    state=ctx.state or None,
                )
                if not pr.get("is_live"):
                    out.append({
                        "type": "market_price",
                        "crop": c["name"],
                        "note": "Live mandi price unavailable — configure DATA_GOV_IN_API_KEY",
                    })
                    continue
                row = (pr.get("top_crops") or [{}])[0]
                out.append({
                    "type": "market_price",
                    "crop": c["name"],
                    "modal_price": row.get("modal_price"),
                    "msp": row.get("msp"),
                    "mandi": row.get("mandi_name"),
                    "live": True,
                })
            return out

        if intent in (INTENT_CROP_RECOMMENDATION, INTENT_GENERAL):
            return [
                {"type": "quick_crop", "crop": crop_catalog.get(cid)["name"], "id": cid}
                for cid in STAPLE_FOR_CHAT[:4]
                if crop_catalog.get(cid)
            ]

        return []


chat_intelligence_service = ChatIntelligenceService()
