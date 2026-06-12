#!/usr/bin/env python3
"""
KrishiMitra Chat Intelligence Service v3.0
==========================================
Intelligent, context-aware, multi-turn agricultural chatbot.

Features:
- Multi-turn conversation with full history context
- 22-language NLP intent detection (Hindi, English + all Indian languages)
- Live data grounding: weather, mandi prices, crop recommendations, schemes
- Gemini AI primary + rich rule-based fallback (no API key needed)
- Farmer-location-aware: personalises every answer with GPS data
- Entity extraction: crops, locations, quantities, dates
- Follow-up detection: understands "uska", "iske baad", "yahi", pronouns
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

# ── Intent labels ────────────────────────────────────────────────
INTENT_CROP_RECOMMENDATION = "crop_recommendation"
INTENT_MARKET_PRICE        = "market_price"
INTENT_WEATHER             = "weather"
INTENT_GOVERNMENT_SCHEME   = "government_scheme"
INTENT_PEST_DISEASE        = "pest_disease"
INTENT_SOIL                = "soil"
INTENT_IRRIGATION          = "irrigation"
INTENT_FERTILIZER          = "fertilizer"
INTENT_CROP_INFO           = "crop_info"
INTENT_GREETING            = "greeting"
INTENT_GENERAL             = "general"
INTENT_FOLLOWUP            = "followup"

STAPLE_FOR_CHAT = ["wheat", "rice", "maize", "mustard", "tomato", "onion", "potato"]

def _current_season(month: int = None) -> str:
    m = month or datetime.now().month
    if m in (6, 7, 8, 9, 10, 11):
        return "Kharif (Jun-Nov)"
    if m in (10, 11, 12, 1, 2, 3):
        return "Rabi (Oct-Mar)"
    return "Zaid (Mar-Jun)"


# ── NLP intent patterns (multi-language) ────────────────────────
_INTENT_PATTERNS: List[Tuple[str, List[str]]] = [
    (INTENT_GREETING, [
        r"\b(hi|hello|namaste|namaskar|hey|नमस्ते|नमस्कार|vanakkam|namaskaram|salam|adaab|pranam)\b",
        r"^(helo|hii|kya\s*hal|kaisa\s*hai|kaise\s*hain|good\s*(morning|evening|afternoon))$",
    ]),
    (INTENT_FOLLOWUP, [
        r"\b(uska|uski|iske|isi|yahi|wahi|उसका|उसकी|इसका|इसकी|यही|वही)\b",
        r"\b(aur|phir|फिर|और\s*क्या|next|then|also|more|aage)\b\s*(batao|bataiye|tell|kya|kab|kitna|batao)?",
        r"\b(iske\s*baad|इसके\s*बाद|उसके\s*बाद|uske\s*baad|और\s*बताइए|more\s*about)\b",
    ]),
    (INTENT_CROP_RECOMMENDATION, [
        # English patterns
        r"\bwhich\s+crop",
        r"\bbest\s+crop",
        r"\bwhat\s+(crop|to\s+grow|to\s+sow|to\s+plant)",
        r"\bcrop\s*(suggest|recommend|advice|choice|select)",
        r"\bwhat\s+should\s+i\s+(grow|plant|sow|cultivate)",
        # Hindi/Hinglish patterns
        r"\b(kya|kaun\s*si|kaunsi|konsi)\s+(fasal|crop|phasal|kheti)",
        r"\b(fasal|phasal|crop)\s+(suggest|recommend|batao|bataiye|kaun|kya|kaunsi|konsi|सुझाव|बताओ|चुनें)",
        r"\b(kya|kaun)\s*(lagaun|ugaun|boun|lagaye|ugaye|boye|lagana|ugana|bona)\b",
        r"\b(kharif|rabi|zaid|खरीफ|रबी|जायद)\s*(mein|में|ke\s+liye|के\s+लिए)?\s*(kya|क्या|kaun|konsi|kaunsi)\s*(lagaun|ugaun|boun|lagaye|fasal|crop)?",
        r"\b(is\s*season|is\s*mausam|iss\s*saal)\s*(kya|kaun|konsi|क्या|कौन)",
        r"\b(इस\s*मौसम|इस\s*सीजन)\s*(में|मे)\s*(क्या|कौन)",
        r"\b(कौन\s*सी|konsi|kaunsi)\s*(fasal|फसल|crop|खेती|kheti)",
        r"\b(फसल|fasal)\s*(का|के|की)\s*(सुझाव|चुनाव|select|suggest|recommend)",
        r"\bkaunsi\s+fasal\b",
        r"\bkonsi\s+fasal\b",
        # Regional languages
        r"\b(ফসল|పంట|பயிர்|ਫ਼ਸਲ|ক্ষেত)\b.*\b(পরামর্শ|సూచన|பரிந்துரை|ਸੁਝਾਅ)\b",
        r"\b(kontha|entha|yavanu)\s+(bele|bethanu|balu)\b",  # Kannada
        r"\b(ethu|enna)\s+(paya|payan|vithaykuka)\b",  # Malayalam/Tamil
    ]),
    (INTENT_MARKET_PRICE, [
        r"\b(msp|mandi|market\s*price|bhav|भाव|मंडी|rate|daam|aaj\s*ka\s*bhav|today.*price)\b",
        r"\b(price|कीमत|दाम|भाव|rate)\s*(of|का|की|ke)",
        r"\b(गेहूँ|धान|सरसों|प्याज|आलू|टमाटर|कपास|मक्का|सोयाबीन|wheat|rice|mustard|onion|potato|tomato|cotton|maize|soybean)\s*(ka\s*bhav|ka\s*rate|ka\s*daam|price|भाव|दाम|rate|मूल्य|कीमत)",
        r"\b(today|aaj|आज|kal|कल)\s*(ka|का|ki|की)\s*(bhav|भाव|price|rate|दाम)",
        r"\b(bechna|sell|bikri|बेचना|बिक्री)\s*(kahan|kahaan|कहाँ|kab|कब|kitne\s*mein)",
        r"\b(enam|agmarknet|apmc|मंडी\s*भाव)\b",
        r"\b(minimum\s*support|न्यूनतम\s*समर्थन|msp\s*kya\s*hai|msp\s*kitna)\b",
    ]),
    (INTENT_WEATHER, [
        r"\b(weather|mausam|मौसम|barish|बारिश|rain|forecast|flood|बाढ़|drought|सूखा|temperature|तापमान|imd|meghdoot)\b",
        r"\b(aaj|kal|आज|कल|is\s*hafte|next\s*week)\s*(ka\s*)?(mausam|weather|barish|बारिश)",
        r"\b(बुवाई|सिंचाई|sinchai|buwai|kheti)\s*(kab|कब|ka\s*samay|when)",
        r"\b(garmi|sardi|baarish|तूफान|ओलावृष्टि|olavrishti|hail|storm)\b",
    ]),
    (INTENT_GOVERNMENT_SCHEME, [
        r"\b(pm[- ]?kisan|pmfby|kcc|kusum|enam|yojana|योजना|subsidy|सब्सिडी|अनुदान|fasal\s*bima|kisan\s*credit|soil\s*health\s*card)\b",
        r"\b(sarkaar|sarkaari|government|सरकार|सरकारी)\s*(yojana|योजना|scheme|help|sahayata|paisa)",
        r"\b(paise|पैसे|rupaye|amount)\s*(kab\s*aayega|kab\s*milega|कब\s*आएगा|status|check)",
        r"\b(apply|avedan|आवेदन|register|पंजीयन)\s*(kaise|कैसे|how|karna|karein)",
        r"\b(loan|rin|ऋण|karz|कर्ज|nabard|mudra)\s*(kaise|कैसे|milega|lena)",
    ]),
    (INTENT_PEST_DISEASE, [
        r"\b(pest|keet|कीट|rog|रोग|blight|blast|disease|worm|caterpillar|sundi|सुंडी|wilting|fungus|fungal|spray|davai|दवाई|pesticide|insecticide|fungicide|neem)\b",
        r"\b(patti|पत्ती|leaf|fruit|फल|root|जड़|fasal|crop)\s*(mein|में|pe|पर)\s*(problem|kuch|नुकसान|damage|pili|पीली|sukh|सूख|kala|काला|safed|सफेद)",
        r"\b(kyon|क्यों|why)\s*(sukh|mur|pil|gir|सूख|मुरझा|पीली|झड|curl|fall)",
        r"\b(sundi|afid|aphid|mite|thrips|whitefly|सफेद\s*मक्खी|माहू|टिड्डा|locust)\b",
    ]),
    (INTENT_SOIL, [
        r"\b(soil|mitti|मिट्टी|ph|organic\s*carbon|soil\s*health|soil\s*card|urvarak|fertility|nitrogen|phosphorus|potassium|vermicompost|compost)\b",
        r"\b(mitti|माटी|जमीन)\s*(ki\s*janch|test|जांच|health|ph|ka\s*ph)",
        r"\b(mrida|मृदा)\s*(swasthya|health|परीक्षण)",
        r"\b(sankhyam|NPK|n\.p\.k)\b",
    ]),
    (INTENT_IRRIGATION, [
        r"\b(irrigation|sinchai|सिंचाई|drip|sprinkler|borewell|tubewell|pump|AWD|solar\s*pump|kusum)\b",
        r"\b(pani|पानी|water)\s*(kab|kitna|कब|कितना|when|how\s*much|dene\s*ka\s*samay|schedule)",
        r"\b(sinchai|सिंचाई|irrigat)\s*(kab|kaise|कब|कैसे|when|schedule|time)",
    ]),
    (INTENT_FERTILIZER, [
        r"\b(urea|dap|npk|mkp|mop|fertilizer|khad|खाद|urvarak|उर्वरक|zinc|sulfur|vermicompost|FYM)\b",
        r"\b(kitni|कितनी|how\s*much|kitna)\s*(khad|urea|dap|fertilizer|nitrogen)",
        r"\b(khad|उर्वरक|fertilizer)\s*(kab|कब|when|apply|daalein|डालें|kitni|schedule)",
    ]),
]


class ChatIntelligenceService:
    """
    Context-aware, multi-turn, multi-language agricultural chatbot.
    Uses Gemini AI when configured, falls back to rich rule-based engine.
    """

    # ── Gemini system prompt ─────────────────────────────────────
    SYSTEM_PROMPT = """You are KrishiMitra AI — a trusted, intelligent digital assistant for Indian farmers.
You are like an expert agronomist, economist, and government scheme advisor combined.

STRICT RULES (never break):
1. Use ONLY facts from the "Official live data" section. Never invent prices, MSP, weather, or schemes.
2. If data is missing, say so clearly and point to official sources (Agmarknet, IMD, PM-Kisan, ICAR).
3. Distinguish MSP (government minimum) from mandi modal price (actual market).
4. Prefer organic / IPM approaches before chemicals. If chemicals are needed, cite label dose.
5. Match the user's language EXACTLY — detect from their writing and respond in same script.
6. Be conversational, warm, practical. Use short paragraphs, bullet points, emojis where natural.
7. Reference the farmer's actual GPS location, current weather, and season in every crop/weather answer.
8. For follow-up questions, refer back to what was discussed earlier in the conversation.
9. Format key numbers (MSP, prices, temperatures) prominently with ₹ symbol.
10. End with one actionable next step and relevant helpline number when appropriate.

Conversation style:
- If this is a follow-up ("uska", "aur batao", "phir kya"), build on the previous context.
- Acknowledge the farmer's situation empathetically before giving advice.
- Give specific, actionable answers — not generic platitudes.
- For pest/disease: recommend the KrishiRaksha photo upload feature for accurate ML diagnosis.

Never claim you inspected a photo. Never make up mandi names or today's prices."""

    def answer(
        self,
        query: str,
        ctx: LocationContext,
        language: str = "hi",
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point. Supports multi-turn conversation via `history`.

        history format (last N messages):
          [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        """
        query = (query or "").strip()
        lang = normalise_language_code(language)

        # Auto-detect state language
        if language == "auto" and ctx.state:
            lang = get_language_for_state(ctx.state)

        if not query:
            return {
                "response": self._empty_response(lang),
                "intent": INTENT_GENERAL,
                "sources": [],
                "crop_suggestions": [],
                "language": lang,
            }

        # ── NLP: intent + entity extraction ───────────────────────
        intent, crops_mentioned = self.classify_query(query)

        # Multi-turn: if no crops in current query, check conversation history
        if not crops_mentioned and history:
            for msg in reversed((history or [])[-6:]):
                past = msg.get("content") or msg.get("message_content") or ""
                if past:
                    past_crops = self._detect_crops(past)
                    if past_crops:
                        crops_mentioned = past_crops
                        break

        # Detect follow-up intent: inherit context from last assistant turn
        if intent == INTENT_FOLLOWUP and history:
            last_assistant = next(
                (m for m in reversed(history) if m.get("role") == "assistant"),
                None
            )
            if last_assistant:
                prior_intent = last_assistant.get("intent") or INTENT_GENERAL
                intent = prior_intent  # continue the previous topic

        # ── Build live data context block ─────────────────────────
        context_block, sources = self._build_official_context(
            ctx, query, intent, crops_mentioned, lang=lang
        )

        # ── Compose prompt ────────────────────────────────────────
        loc = ctx.display_name
        if ctx.state and ctx.state not in loc:
            loc = f"{ctx.display_name}, {ctx.state}"

        now = datetime.now()
        season = _current_season(now.month)
        lang_instruction = get_gemini_language_instruction(lang)

        # Format conversation history for Gemini
        history_block = ""
        if history:
            lines = []
            for msg in (history or [])[-8:]:
                role = "Farmer" if msg.get("role") == "user" else "KrishiMitra"
                content = (msg.get("content") or msg.get("message_content") or "").strip()
                if content:
                    lines.append(f"{role}: {content}")
            if lines:
                history_block = "=== Conversation so far ===\n" + "\n".join(lines) + "\n\n"

        user_prompt = (
            f"Farmer location: {loc} (GPS: {ctx.latitude:.4f}, {ctx.longitude:.4f})\n"
            f"Date: {now.strftime('%d %B %Y')}, Current season: {season}\n"
            f"{lang_instruction}\n"
            f"Detected intent: {intent}\n"
            f"Crops mentioned: {', '.join(c['name'] for c in crops_mentioned) or 'none'}\n\n"
            f"{history_block}"
            f"=== Official live data (authoritative — use these facts) ===\n"
            f"{context_block}\n\n"
            f"=== Farmer's current question ===\n"
            f"{query}\n\n"
            f"Instructions: Answer specifically for {loc} in {season}. "
            f"If this is a follow-up, connect your answer to the conversation above. "
            f"Cite actual numbers from the data block. End with one concrete next step."
        )

        # ── Generate response ──────────────────────────────────────
        has_gemini = bool(
            gemini_service.api_key
            and len(gemini_service.api_key) > 10
            and not gemini_service.api_key.upper().startswith("YOUR")
        )

        if has_gemini:
            response_text = gemini_service.generate(
                user_prompt,
                self.SYSTEM_PROMPT,
                max_tokens=1600,
                user_query=query,
                temperature=0.3,
            )
            data_source = "Gemini AI + Official gov APIs"
        else:
            response_text = self._smart_rule_response(
                query, intent, crops_mentioned, ctx, context_block, lang, history
            )
            data_source = "KrishiMitra NLP Engine + Official gov APIs"

        crop_suggestions = self._crop_suggestions_for_intent(ctx, intent, crops_mentioned, lang=lang)

        return {
            "response": response_text,
            "intent": intent,
            "sources": sources,
            "crops_detected": [c["name"] for c in crops_mentioned],
            "crop_suggestions": crop_suggestions,
            "language": lang,
            "data_source": data_source,
            "timestamp": now.isoformat(),
        }

    # ── NLP: Intent classification ────────────────────────────────

    def classify_query(self, query: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Multi-language intent classification with entity extraction."""
        q = query.lower().strip()
        crops_mentioned = self._detect_crops(query)

        for intent, patterns in _INTENT_PATTERNS:
            for pat in patterns:
                try:
                    if re.search(pat, q, re.IGNORECASE):
                        if intent == INTENT_GREETING and len(q) > 50:
                            continue
                        return intent, crops_mentioned
                except re.error:
                    continue

        if crops_mentioned:
            return INTENT_CROP_INFO, crops_mentioned

        return INTENT_GENERAL, crops_mentioned

    def _detect_crops(self, text: str) -> List[Dict[str, Any]]:
        """Extract crop entities using the crop catalog."""
        found: List[Dict[str, Any]] = []
        seen = set()
        tokens = re.split(r"[\s,?.!;|]+", text.lower())
        for length in (3, 2, 1):
            for i in range(len(tokens) - length + 1):
                phrase = " ".join(tokens[i:i + length])
                if len(phrase) < 2:
                    continue
                norm = crop_catalog.normalize(phrase)
                if norm and norm["id"] not in seen:
                    seen.add(norm["id"])
                    found.append(norm)
        if not found:
            for r in crop_catalog.search(text, limit=3):
                if r["id"] not in seen:
                    seen.add(r["id"])
                    found.append(r)
        return found[:5]

    # ── Live data context builder ─────────────────────────────────

    def _build_official_context(
        self,
        ctx: LocationContext,
        query: str,
        intent: str,
        crops: List[Dict[str, Any]],
        lang: str = "hi",
    ) -> Tuple[str, List[str]]:
        """Fetch and format live official data for this farmer's location."""
        lines: List[str] = []
        sources: List[str] = []

        # 1. Live weather (always)
        try:
            weather = weather_service.get_weather(ctx.query_label, ctx.latitude, ctx.longitude, lang=lang)
            cur = weather.get("current") or {}
            temp     = cur.get("temperature")
            humidity = cur.get("humidity")
            wind     = cur.get("wind_speed")
            rain     = cur.get("rainfall_mm", 0)
            cond     = cur.get("condition_local") or cur.get("condition", "")
            et0      = cur.get("et0_mm")

            lines.append(
                f"[LIVE WEATHER] {ctx.display_name}: {temp}°C, {cond}, "
                f"humidity {humidity}%, wind {wind} km/h, rain {rain}mm/hr"
                + (f", ET0 {et0}mm/day" if et0 else "")
            )

            if weather.get("farming_advice"):
                lines.append(f"[FARMING ADVICE] {weather['farming_advice']}")

            forecast = (
                weather.get("forecast_7day")
                or weather.get("forecast_7_days")
                or weather.get("forecast")
                or []
            )
            if forecast:
                lines.append("[7-DAY FORECAST]")
                for day in forecast[:5]:
                    wb = day.get("water_balance_mm")
                    irr = " (IRRIGATE)" if day.get("irrigation_needed") else ""
                    lines.append(
                        f"  {day.get('date')}: max {day.get('max_temp')}°C, "
                        f"rain {day.get('rainfall_mm', 0)}mm, "
                        f"prob {day.get('rain_probability', 0)}%"
                        + (f", WB {wb}mm{irr}" if wb is not None else "")
                    )

            alerts = weather.get("farming_alerts") or []
            for alert in alerts[:3]:
                lines.append(f"[ALERT] {str(alert)}")

            sources.append(weather.get("data_source", "Open-Meteo"))
        except Exception as e:
            logger.warning("Weather fetch failed in chat context: %s", e)
            lines.append("[WEATHER] Temporarily unavailable — check mausam.imd.gov.in")

        # 2. Market prices
        try:
            prices = market_service.get_prices(
                ctx.query_label,
                lat=ctx.latitude,
                lon=ctx.longitude,
                state=ctx.state or None,
            )
            sources.append(prices.get("data_source", "Agmarknet/data.gov.in"))

            if intent in (INTENT_MARKET_PRICE, INTENT_GENERAL, INTENT_CROP_INFO, INTENT_CROP_RECOMMENDATION) or crops:
                if prices.get("is_live"):
                    top = [c for c in (prices.get("top_crops") or []) if c.get("is_live")]
                    if crops:
                        crop_ids = {c["id"] for c in crops}
                        matched = [
                            c for c in top
                            if crop_catalog.normalize(str(c.get("crop_name", "")))
                            and crop_catalog.normalize(str(c.get("crop_name", "")))["id"] in crop_ids
                        ]
                        top = matched + [c for c in top if c not in matched]
                    lines.append(f"[LIVE MANDI PRICES near {ctx.display_name}] (Rs/quintal):")
                    for c in top[:8]:
                        profit = c.get("profit_vs_msp")
                        profit_str = f", +{profit}% vs MSP" if profit and profit > 0 else ""
                        lines.append(
                            f"  {c.get('crop_name')} ({c.get('crop_name_hindi', '')}): "
                            f"modal Rs{c.get('modal_price')}, MSP Rs{c.get('msp')}, "
                            f"mandi: {c.get('mandi_name', 'N/A')}{profit_str}"
                        )
                else:
                    lines.append("[MANDI PRICES] Live feed unavailable. Set DATA_GOV_IN_API_KEY for live data.")
                    lines.append("  Register free at data.gov.in/user/register")
        except Exception as e:
            logger.warning("Market fetch failed in chat context: %s", e)

        # 3. Crop recommendations (for crop/general queries)
        if intent in (INTENT_CROP_RECOMMENDATION, INTENT_GENERAL, INTENT_CROP_INFO) or \
           any(w in query.lower() for w in ("crop", "fasal", "फसल", "खेती", "ugaun", "lagaun", "boun")):
            try:
                rec = crop_recommendation_engine.recommend_from_context(ctx, language=lang)
                sources.append(rec.get("data_source", "Crop engine"))
                season_lbl = rec.get("season", "")
                zone = rec.get("agro_zone") or rec.get("region") or ""
                lines.append(f"[CROP RECOMMENDATIONS for {ctx.display_name}] season: {season_lbl}, zone: {zone}")
                for r in (rec.get("recommendations") or [])[:5]:
                    local = r.get("crop_name_local") or r.get("crop_name_hindi") or r.get("crop_name", "")
                    lines.append(
                        f"  {r.get('crop_name')} ({local}): "
                        f"suitability {r.get('suitability_score')}%, "
                        f"profit Rs{r.get('profit_per_hectare', 0):,}/ha, "
                        f"MSP Rs{r.get('msp_per_quintal', 0)}/q, "
                        f"reason: {r.get('reason_hindi') or r.get('reason', '')}"
                    )
                ws = rec.get("weather_snapshot") or {}
                if ws.get("temperature"):
                    lines.append(f"  [Live weather used in scoring: {ws.get('temperature')}°C, {ws.get('condition', '')}]")
            except Exception as e:
                logger.warning("Crop rec failed in chat context: %s", e)

        # 4. Government schemes
        if intent == INTENT_GOVERNMENT_SCHEME or \
           any(w in query.lower() for w in ("yojana", "scheme", "kisan", "योजना", "subsidy", "sarkaar", "apply", "register")):
            try:
                schemes = schemes_service.get_schemes(ctx.query_label)
                sources.append("Government schemes (MoAFW)")
                lines.append(f"[GOVERNMENT SCHEMES for farmers]")
                for s in (schemes.get("schemes") or [])[:6]:
                    lines.append(
                        f"  {s.get('name')} ({s.get('name_hindi', '')}): "
                        f"{(s.get('benefit') or '')[:120]} | "
                        f"Apply: {s.get('website', '')}"
                    )
            except Exception as e:
                logger.warning("Schemes fetch failed in chat context: %s", e)

        # 5. MSP for mentioned crops
        for crop in crops[:3]:
            msp = crop.get("msp") or MSP_2024_25.get(crop["id"])
            if msp:
                lines.append(f"[MSP 2024-25] {crop['name']}: Rs{msp}/quintal (Cabinet approved)")

        # 6. Pest/disease guidance
        if intent == INTENT_PEST_DISEASE:
            lines.append(
                "[PEST/DISEASE] Upload leaf photo in KrishiRaksha for ML diagnosis. "
                "General IPM: neem oil 5ml/L first; ICAR package of practices; "
                "1800-180-1551 for expert advice."
            )
            sources.append("ICAR IPM guidelines")

        return "\n".join(lines), list(dict.fromkeys(sources))

    # ── Intelligent rule-based response (no Gemini needed) ───────

    def _smart_rule_response(
        self,
        query: str,
        intent: str,
        crops: List[Dict[str, Any]],
        ctx: LocationContext,
        context_block: str,
        lang: str = "hi",
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Intelligent, context-aware responses built from live data.
        Personalised to location, weather, season, and conversation history.
        """
        loc = ctx.display_name
        if ctx.state and ctx.state not in loc:
            loc = f"{ctx.display_name}, {ctx.state}"

        # Parse live values from context_block
        def _extract(pattern: str, default: str = "—") -> str:
            m = re.search(pattern, context_block)
            return m.group(1) if m else default

        temp     = _extract(r"([\d.]+)°C")
        humidity = _extract(r"humidity ([\d]+)%")
        cond     = _extract(r"°C, ([^,\n]+),")
        farming_advice = ""
        fa_line = next((l for l in context_block.splitlines() if "[FARMING ADVICE]" in l), "")
        if fa_line:
            farming_advice = fa_line.replace("[FARMING ADVICE]", "").strip()

        season = _current_season()
        now = datetime.now()

        # ── GREETING ──────────────────────────────────────────────
        if intent == INTENT_GREETING:
            msgs = {
                "hi": (
                    f"नमस्ते किसान भाई! 🌾 मैं **KrishiMitra AI** हूँ — आपका स्मार्ट कृषि सहायक।\n\n"
                    f"📍 आपकी लोकेशन: **{loc}**\n"
                    f"🌡️ अभी का मौसम: **{temp}°C**, {cond}\n"
                    f"🗓️ सीजन: **{season}**\n"
                    f"💡 {farming_advice or 'सामान्य कृषि कार्य जारी रखें'}\n\n"
                    f"मैं इन सभी विषयों में मदद कर सकता हूँ:\n"
                    f"🌱 फसल सुझाव — कौन सी फसल उगाऊं?\n"
                    f"💰 मंडी भाव — आज का गेहूँ/धान का भाव?\n"
                    f"🌦️ मौसम — सिंचाई कब करूँ?\n"
                    f"🏛️ योजनाएं — PM-Kisan, PMFBY, KCC\n"
                    f"🐛 कीट-रोग — फसल में रोग क्यों?\n"
                    f"🧪 खाद — कितनी Urea डालूँ?\n\n"
                    f"💬 Hindi, English या Hinglish — किसी भी भाषा में पूछें!\n"
                    f"📞 Kisan Call Centre: **1800-180-1551** (Free, 24x7)"
                ),
                "en": (
                    f"Hello Farmer! 🌾 I'm **KrishiMitra AI** — your intelligent farming assistant.\n\n"
                    f"📍 Your location: **{loc}**\n"
                    f"🌡️ Current weather: **{temp}°C**, {cond}\n"
                    f"🗓️ Season: **{season}**\n"
                    f"💡 {farming_advice or 'Suitable for normal farming activities'}\n\n"
                    f"I can help with:\n"
                    f"🌱 Crop recommendations for your location\n"
                    f"💰 Live mandi prices (Agmarknet/eNAM)\n"
                    f"🌦️ 16-day weather forecast + irrigation schedule\n"
                    f"🏛️ Government schemes (PM-Kisan, PMFBY, KCC)\n"
                    f"🐛 Pest & disease identification\n"
                    f"🧪 Fertiliser recommendations\n\n"
                    f"Ask in any Indian language or English!\n"
                    f"📞 Kisan Helpline: **1800-180-1551** (Free, 24x7)"
                ),
            }
            return msgs.get(lang, msgs["en"])

        # ── WEATHER ──────────────────────────────────────────────
        if intent == INTENT_WEATHER:
            forecast_lines = [l for l in context_block.splitlines() if l.strip().startswith("  202")]
            alerts = [l for l in context_block.splitlines() if "[ALERT]" in l]

            resp = {
                "hi": (
                    f"🌦️ **{loc}** का लाइव मौसम ({now.strftime('%d %B %Y')}):\n\n"
                    f"🌡️ तापमान: **{temp}°C** | 💧 नमी: **{humidity}%** | 🌬️ {cond}\n"
                    f"{'🚨 ' + farming_advice if farming_advice else '✅ सामान्य कृषि कार्य जारी रखें'}\n\n"
                ),
                "en": (
                    f"🌦️ **{loc}** Live Weather ({now.strftime('%d %B %Y')}):\n\n"
                    f"🌡️ Temp: **{temp}°C** | 💧 Humidity: **{humidity}%** | {cond}\n"
                    f"{'🚨 ' + farming_advice if farming_advice else '✅ Normal farming conditions'}\n\n"
                ),
            }.get(lang, f"Weather {loc}: {temp}°C, {cond}. {farming_advice}\n\n")

            if alerts:
                resp += ("⚠️ **कृषि चेतावनी:**\n" if lang == "hi" else "⚠️ **Farming Alerts:**\n")
                resp += "\n".join(a.replace("[ALERT]", "").strip() for a in alerts[:3]) + "\n\n"

            if forecast_lines:
                resp += ("📅 **7 दिन का पूर्वानुमान:**\n" if lang == "hi" else "📅 **7-Day Forecast:**\n")
                resp += "\n".join(f"• {l.strip()}" for l in forecast_lines[:5]) + "\n\n"

            resp += "🌐 IMD: **mausam.imd.gov.in** | Meghdoot App"
            return resp

        # ── CROP RECOMMENDATION ──────────────────────────────────
        if intent in (INTENT_CROP_RECOMMENDATION, INTENT_CROP_INFO):
            rec_lines = [l for l in context_block.splitlines() if "suitability" in l and l.strip().startswith("  ")]

            header = {
                "hi": f"🌾 **{loc}** के लिए फसल सुझाव — {season}\n\n🌡️ मौसम: {temp}°C, {cond}\n\n",
                "en": f"🌾 Crop Recommendations for **{loc}** — {season}\n\n🌡️ Weather: {temp}°C, {cond}\n\n",
            }.get(lang, f"Crop recommendations for {loc}:\n\n")

            if rec_lines:
                body = ""
                for i, line in enumerate(rec_lines[:5], 1):
                    # Extract crop name and score
                    m = re.match(r"\s+([^:]+):\s+suitability\s+([\d]+)%.*profit\s+Rs([\d,]+)/ha.*MSP\s+Rs([\d]+)/q", line)
                    if m:
                        crop_name = m.group(1).strip()
                        score = m.group(2)
                        profit = m.group(3)
                        msp = m.group(4)
                        bar = "🟢" if int(score) >= 80 else "🟡" if int(score) >= 60 else "🔴"
                        body += f"{i}. {bar} **{crop_name}** — {score}% सटीकता\n   ₹{profit}/हे. लाभ | MSP ₹{msp}/q\n"
                    else:
                        body += f"• {line.strip()}\n"
            else:
                body = (
                    "• 🟢 **गेहूँ** — रबी सीजन, MSP ₹2,275/q\n"
                    "• 🟢 **सरसों** — कम पानी, MSP ₹5,650/q\n"
                    "• 🟡 **चना** — हल्की मिट्टी, MSP ₹5,440/q\n"
                ) if lang == "hi" else (
                    "• 🟢 **Wheat** — Rabi season, MSP ₹2,275/q\n"
                    "• 🟢 **Mustard** — low water, MSP ₹5,650/q\n"
                    "• 🟡 **Gram** — light soil, MSP ₹5,440/q\n"
                )

            footer = {
                "hi": f"\n\n💡 {farming_advice or 'बुवाई से पहले मिट्टी जांच करवाएं।'}\n📞 ICAR: 1800-180-1551",
                "en": f"\n\n💡 {farming_advice or 'Get soil tested before sowing.'}\n📞 ICAR: 1800-180-1551",
            }.get(lang, "")
            return header + body + footer

        # ── MARKET PRICE ─────────────────────────────────────────
        if intent == INTENT_MARKET_PRICE:
            price_lines = [l for l in context_block.splitlines() if "modal Rs" in l and l.strip().startswith("  ")]
            msp_lines   = [l for l in context_block.splitlines() if "[MSP 2024-25]" in l]

            if price_lines:
                header = {
                    "hi": f"💰 **{loc}** के पास मंडी भाव (आज, Agmarknet):\n\n",
                    "en": f"💰 Live Mandi Prices near **{loc}** (Agmarknet today):\n\n",
                }.get(lang, f"Mandi prices near {loc}:\n\n")
                body = ""
                for line in price_lines[:8]:
                    m = re.match(r"\s+([^(]+)\s*\(([^)]*)\):\s*modal Rs([\d]+),\s*MSP Rs([\d]+),\s*mandi:\s*([^,\n]+)", line)
                    if m:
                        crop = m.group(1).strip()
                        hindi = m.group(2).strip()
                        modal = m.group(3)
                        msp   = m.group(4)
                        mandi = m.group(5).strip()
                        profit = int(modal) - int(msp)
                        ind = "📈" if profit >= 0 else "📉"
                        body += f"• {ind} **{crop}** ({hindi}): ₹{modal}/q | MSP ₹{msp} | 🏪 {mandi}\n"
                    else:
                        body += f"• {line.strip()}\n"
                footer = {
                    "hi": "\n📊 स्रोत: Agmarknet/data.gov.in | agmarknet.gov.in",
                    "en": "\n📊 Source: Agmarknet/data.gov.in | agmarknet.gov.in",
                }.get(lang, "")
                return header + body + footer
            else:
                # No live data — show MSP
                msp_body = ""
                if msp_lines:
                    for line in msp_lines[:5]:
                        msp_body += f"• {line.replace('[MSP 2024-25]','').strip()}\n"
                else:
                    msp_body = (
                        "• गेहूँ: ₹2,275/q\n• धान: ₹2,300/q\n• सरसों: ₹5,650/q\n"
                        "• मक्का: ₹2,090/q\n• सोयाबीन: ₹4,892/q"
                        if lang == "hi" else
                        "• Wheat: ₹2,275/q\n• Rice: ₹2,300/q\n• Mustard: ₹5,650/q\n"
                        "• Maize: ₹2,090/q\n• Soybean: ₹4,892/q"
                    )
                return {
                    "hi": (
                        f"⚠️ आज का लाइव मंडी भाव उपलब्ध नहीं (DATA_GOV_IN_API_KEY नहीं लगाया)।\n\n"
                        f"📊 **MSP 2024-25** (न्यूनतम समर्थन मूल्य):\n{msp_body}\n\n"
                        f"🌐 agmarknet.gov.in पर देखें\n📞 eNAM: 1800-270-0224"
                    ),
                    "en": (
                        f"⚠️ Live mandi prices unavailable (DATA_GOV_IN_API_KEY not configured).\n\n"
                        f"📊 **MSP 2024-25** (Minimum Support Price):\n{msp_body}\n\n"
                        f"🌐 Check agmarknet.gov.in\n📞 eNAM: 1800-270-0224"
                    ),
                }.get(lang, f"Live mandi prices unavailable. MSP:\n{msp_body}")

        # ── GOVERNMENT SCHEMES ────────────────────────────────────
        if intent == INTENT_GOVERNMENT_SCHEME:
            scheme_lines = [l for l in context_block.splitlines() if l.strip().startswith("  ") and "Apply:" in l]
            header = {
                "hi": "🏛️ **किसानों के लिए सरकारी योजनाएं:**\n\n",
                "en": "🏛️ **Government Schemes for Farmers:**\n\n",
            }.get(lang, "Government schemes:\n\n")
            if scheme_lines:
                body = "\n".join(f"• {l.strip()}" for l in scheme_lines[:5])
            else:
                body = (
                    "• **PM-Kisan**: ₹6,000/वर्ष — pmkisan.gov.in | 155261\n"
                    "• **PMFBY**: 2% प्रीमियम फसल बीमा — pmfby.gov.in | 14447\n"
                    "• **KCC**: ₹3 लाख @4% ब्याज — निकटतम बैंक\n"
                    "• **PM-KUSUM**: 90% सब्सिडी सोलर पंप — pmkusum.mnre.gov.in\n"
                    "• **Soil Health Card**: मुफ्त मिट्टी जांच — soilhealth.dac.gov.in"
                ) if lang == "hi" else (
                    "• **PM-Kisan**: ₹6,000/year — pmkisan.gov.in | 155261\n"
                    "• **PMFBY**: 2% premium crop insurance — pmfby.gov.in | 14447\n"
                    "• **KCC**: ₹3L credit @4% interest — nearest bank\n"
                    "• **PM-KUSUM**: 90% subsidy solar pump — pmkusum.mnre.gov.in\n"
                    "• **Soil Health Card**: Free soil testing — soilhealth.dac.gov.in"
                )
            return header + body + "\n\n📞 Kisan Call Centre: **1800-180-1551** (Free)"

        # ── PEST / DISEASE ────────────────────────────────────────
        if intent == INTENT_PEST_DISEASE:
            crop_hint = f" ({crops[0]['name']})" if crops else ""
            return {
                "hi": (
                    f"🐛 **फसल रोग/कीट उपचार{crop_hint}**\n\n"
                    f"📸 **Step 1:** KrishiRaksha में फोटो अपलोड करें (App में 🐛 वाला बटन)\n"
                    f"   → EfficientNet-B3 AI से 150+ रोगों की पहचान होगी\n\n"
                    f"🌿 **तुरंत जैविक उपाय:**\n"
                    f"• नीम तेल 5ml/L पानी — माहू, सफेद मक्खी, थ्रिप्स\n"
                    f"• Trichoderma viride — मिट्टी जनित रोग\n"
                    f"• पीला/नीला sticky trap — कीट निगरानी\n\n"
                    f"💊 **रासायनिक (ICAR package of practices के अनुसार):**\n"
                    f"• Imidacloprid 70WG — माहू, सफेद मक्खी\n"
                    f"• Mancozeb+Metalaxyl — झुलसा, डाउनी mildew\n"
                    f"• Propiconazole — फफूंदी रोग\n\n"
                    f"📞 **KVK/ICAR सलाह:** 1800-180-1551"
                ),
                "en": (
                    f"🐛 **Pest/Disease Treatment{crop_hint}**\n\n"
                    f"📸 **Step 1:** Upload photo in KrishiRaksha (🐛 button in app)\n"
                    f"   → EfficientNet-B3 AI identifies 150+ diseases\n\n"
                    f"🌿 **Immediate organic remedies:**\n"
                    f"• Neem oil 5ml/L — aphids, whitefly, thrips\n"
                    f"• Trichoderma viride — soil-borne diseases\n"
                    f"• Yellow/blue sticky traps — pest monitoring\n\n"
                    f"💊 **Chemical (ICAR recommended dosage):**\n"
                    f"• Imidacloprid 70WG — aphids, whitefly\n"
                    f"• Mancozeb+Metalaxyl — blight, downy mildew\n"
                    f"• Propiconazole — fungal diseases\n\n"
                    f"📞 **KVK/ICAR advice:** 1800-180-1551"
                ),
            }.get(lang, f"Upload leaf photo in KrishiRaksha for disease ID. Use neem oil first. Call 1800-180-1551.")

        # ── FERTILIZER ────────────────────────────────────────────
        if intent == INTENT_FERTILIZER:
            crop_hint = f" for {crops[0]['name']}" if crops else ""
            return {
                "hi": (
                    f"🌱 **खाद/उर्वरक सुझाव{crop_hint}**\n\n"
                    f"**ICAR अनुशंसित:**\n"
                    f"• **Urea (46% N):** 217 kg/ha → 100 kg N\n"
                    f"• **DAP (18-46-0):** 220 kg/ha → 100 kg P + 40 kg N\n"
                    f"• **MOP (60% K):** 167 kg/ha → 100 kg K\n\n"
                    f"**⚡ Tips:**\n"
                    f"• पहले मिट्टी जांच करवाएं — soilhealth.dac.gov.in\n"
                    f"• Neem-coated urea (NCU) — 10% बचत\n"
                    f"• Split doses: 50% बुवाई पर, 25%-25% बाद में\n"
                    f"• जैविक+रासायनिक: 50-50 मिश्रण से लागत घटाएं\n\n"
                    f"📞 ICAR: 1800-180-1551"
                ),
                "en": (
                    f"🌱 **Fertiliser Recommendations{crop_hint}**\n\n"
                    f"**ICAR recommended:**\n"
                    f"• **Urea (46% N):** 217 kg/ha → 100 kg N\n"
                    f"• **DAP (18-46-0):** 220 kg/ha → 100 kg P + 40 kg N\n"
                    f"• **MOP (60% K):** 167 kg/ha → 100 kg K\n\n"
                    f"**Tips:**\n"
                    f"• Get soil tested first — soilhealth.dac.gov.in\n"
                    f"• Neem-coated urea (NCU) — saves 10% nitrogen\n"
                    f"• Split doses: 50% at sowing, 25%+25% later\n"
                    f"• Mix organic+chemical 50:50 to cut input cost\n\n"
                    f"📞 ICAR: 1800-180-1551"
                ),
            }.get(lang, f"Fertiliser guide: Use neem-coated urea. Get soil tested first. Call 1800-180-1551.")

        # ── IRRIGATION ────────────────────────────────────────────
        if intent == INTENT_IRRIGATION:
            et0 = _extract(r"ET0 ([\d.]+)mm/day")
            irr_lines = [l for l in context_block.splitlines() if "IRRIGATE" in l]
            return {
                "hi": (
                    f"💧 **सिंचाई सलाह — {loc}**\n\n"
                    f"🌡️ मौसम: {temp}°C | ET₀: {et0} mm/दिन\n\n"
                    f"**PM-KUSUM सोलर पंप:**\n"
                    f"• 90% सब्सिडी (30% केंद्र + 30% राज्य + 30% बैंक)\n"
                    f"• Apply: pmkusum.mnre.gov.in | 1800-180-3333\n\n"
                    f"**सिंचाई विधियां:**\n"
                    f"• Drip: 40-50% पानी बचत, 90% सब्सिडी\n"
                    f"• Sprinkler: 30-35% बचत\n"
                    f"• AWD (धान): 25% पानी कम, उपज समान\n\n"
                    + (f"⚠️ सिंचाई जरूरी: {', '.join(l.strip() for l in irr_lines[:3])}\n" if irr_lines else "")
                    + f"📞 PM-KUSUM: 1800-180-3333"
                ),
                "en": (
                    f"💧 **Irrigation Advisory — {loc}**\n\n"
                    f"🌡️ Weather: {temp}°C | ET₀: {et0} mm/day\n\n"
                    f"**PM-KUSUM Solar Pump:** 90% subsidy — pmkusum.mnre.gov.in\n\n"
                    f"**Methods:**\n• Drip: 40-50% water saving, 90% subsidy\n"
                    f"• Sprinkler: 30-35% saving\n• AWD for paddy: 25% less water\n\n"
                    + (f"⚠️ Irrigate: {', '.join(l.strip() for l in irr_lines[:3])}\n" if irr_lines else "")
                    + f"📞 PM-KUSUM: 1800-180-3333"
                ),
            }.get(lang, f"Irrigation: ET0={et0}mm/day. Use drip/sprinkler. PM-KUSUM 90% subsidy.")

        # ── GENERAL / FOLLOW-UP ──────────────────────────────────
        # Build a rich general response using all available context
        lines_out = []

        if temp != "—":
            fa_note = f" — {farming_advice}" if farming_advice else ""
            lines_out.append(f"🌡️ **{loc}** मौसम: **{temp}°C**, {cond}{fa_note}" if lang == "hi"
                             else f"🌡️ **{loc}** weather: **{temp}°C**, {cond}{fa_note}")

        # If there are crops mentioned, give crop-specific advice
        if crops:
            for crop in crops[:2]:
                msp = crop.get("msp") or MSP_2024_25.get(crop["id"])
                if msp:
                    lines_out.append(f"• {crop['name']} MSP 2024-25: ₹{msp}/q")

        rec_lines = [l for l in context_block.splitlines() if "suitability" in l and l.strip().startswith("  ")]
        if rec_lines:
            lines_out.append(("🌾 **फसल सुझाव:**" if lang == "hi" else "🌾 **Crop Suggestions:**"))
            for l in rec_lines[:3]:
                m_crop = re.match(r"\s+([^:]+):", l)
                if m_crop:
                    lines_out.append(f"  • {m_crop.group(1).strip()}")

        lines_out.append(
            "\n💬 और पूछें: फसल भाव, मौसम, PM-Kisan, कीट-रोग\n📞 1800-180-1551" if lang == "hi"
            else "\n💬 Ask about: prices, weather, PM-Kisan, pest control\n📞 1800-180-1551"
        )

        return "\n".join(lines_out)

    def _empty_response(self, lang: str) -> str:
        return {
            "hi": "कृपया अपना सवाल लिखें। मैं फसल, मौसम, मंडी भाव, योजना — सब बता सकता हूँ।",
            "en": "Please type your question. I can help with crops, weather, mandi prices, and schemes.",
            "ta": "தயவுசெய்து உங்கள் கேள்வியை தட்டச்சு செய்யுங்கள்.",
            "te": "దయచేసి మీ ప్రశ్న రాయండి.",
            "mr": "कृपया आपला प्रश्न लिहा.",
            "bn": "অনুগ্রহ করে আপনার প্রশ্ন লিখুন।",
            "gu": "કૃपા કરી તમારો પ્રশ્ন ટાઈپ કरો.",
            "kn": "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಬರೆಯಿರಿ.",
            "ml": "ദയവായി നിങ്ങളുടെ ചോദ്യം ടൈپ് ചെയ്യുക.",
            "pa": "ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ ਸਵਾਲ ਲਿਖੋ।",
        }.get(lang, "Please type your question.")

    # ── Crop suggestion cards ─────────────────────────────────────

    def _crop_suggestions_for_intent(
        self,
        ctx: LocationContext,
        intent: str,
        crops: List[Dict[str, Any]],
        lang: str = "hi",
    ) -> List[Dict[str, Any]]:
        if intent == INTENT_CROP_RECOMMENDATION:
            try:
                rec = crop_recommendation_engine.recommend_from_context(ctx, language=lang)
                return [
                    {
                        "type": "crop_recommendation",
                        "crop":  r.get("crop_name"),
                        "hindi": r.get("crop_name_hindi"),
                        "local": r.get("crop_name_local"),
                        "score": r.get("suitability_score"),
                        "reason": r.get("reason_hindi") or r.get("reason"),
                        "profit": r.get("profit_per_hectare", 0),
                        "msp":    r.get("msp_per_quintal", 0),
                    }
                    for r in (rec.get("recommendations") or [])[:4]
                ]
            except Exception:
                pass

        if intent == INTENT_MARKET_PRICE and crops:
            out = []
            for c in crops[:3]:
                try:
                    pr = market_service.get_prices(
                        ctx.query_label,
                        crop=c["name"],
                        lat=ctx.latitude,
                        lon=ctx.longitude,
                        state=ctx.state or None,
                    )
                    row = (pr.get("top_crops") or [{}])[0]
                    out.append({
                        "type":        "market_price",
                        "crop":        c["name"],
                        "modal_price": row.get("modal_price"),
                        "msp":         row.get("msp"),
                        "mandi":       row.get("mandi_name"),
                        "live":        pr.get("is_live", False),
                    })
                except Exception:
                    out.append({"type": "market_price", "crop": c["name"],
                                "note": "Check agmarknet.gov.in"})
            return out

        # Default: staple crop quick links
        if intent in (INTENT_GENERAL, INTENT_GREETING):
            return [
                {"type": "quick_crop", "crop": crop_catalog.get(cid)["name"], "id": cid}
                for cid in STAPLE_FOR_CHAT[:4]
                if crop_catalog.get(cid)
            ]

        return []


# Module-level singleton
chat_intelligence_service = ChatIntelligenceService()
