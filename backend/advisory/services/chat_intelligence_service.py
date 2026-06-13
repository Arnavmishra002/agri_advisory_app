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

import json
import logging
import re
import re as _re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout
from dataclasses import dataclass
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
    _is_valid_gemini_key,
    gemini_service,
    iot_blockchain,
    market_service,
    schemes_service,
    weather_service,
)

logger = logging.getLogger(__name__)

# ── Module-level Hindi→English term map (used by _qwen_rag_answer) ───────────
# Built once at import time instead of on every request.
_HINDI_ENGLISH_MAP: Dict[str, str] = {
    "गेहूँ": "wheat", "गेहू": "wheat", "गेहुं": "wheat",
    "धान": "rice paddy", "चावल": "rice",
    "मक्का": "maize corn", "ज्वार": "jowar sorghum",
    "बाजरा": "bajra pearl millet",
    "सरसों": "mustard rapeseed",
    "कपास": "cotton", "गन्ना": "sugarcane",
    "सोयाबीन": "soybean",
    "मूँगफली": "groundnut peanut",
    "चना": "chickpea gram",
    "अरहर": "pigeonpea arhar",
    "मूँग": "moong green gram",
    "उड़द": "urad black gram",
    "हल्दी": "turmeric", "अदरक": "ginger",
    "लहसुन": "garlic", "प्याज": "onion",
    "आलू": "potato", "टमाटर": "tomato",
    "बैंगन": "brinjal", "मिर्च": "chilli",
    "आम": "mango", "केला": "banana",
    "अनार": "pomegranate",
    "माहू": "aphid",
    "सुंडी": "caterpillar larva",
    "तना छेदक": "stem borer",
    "सफेद मक्खी": "whitefly",
    "थ्रिप्स": "thrips",
    "झुलसा": "blight",
    "फफूंदी": "fungal disease mold",
    "जड़ सड़न": "root rot",
    "पीलापन": "yellowing chlorosis",
    "रोग": "disease", "कीट": "pest",
    "कीटनाशक": "pesticide insecticide",
    "दवाई": "pesticide treatment",
    "नीम": "neem",
    "सिंचाई": "irrigation water",
    "बुवाई": "sowing planting",
    "खाद": "fertilizer manure",
    "उर्वरक": "fertilizer",
    "मिट्टी": "soil",
    "उपज": "yield",
    "फसल": "crop",
    "बारिश": "rain rainfall",
    "मौसम": "weather season",
    "तापमान": "temperature",
    "नमी": "moisture humidity",
    "योजना": "scheme",
    "सब्सिडी": "subsidy",
    "बीमा": "insurance",
    "किसान": "farmer",
    "मंडी": "mandi market",
    "एमएसपी": "msp minimum support price",
}
_DEVANAGARI_RE = _re.compile(r"[\u0900-\u097F]")


def _augment_hindi_query(query: str) -> str:
    """Append English equivalents for Hindi terms found in query.
    Called once before sending to Phase 1 RAG server."""
    if not _DEVANAGARI_RE.search(query):
        return query
    extras = [eng for hi, eng in _HINDI_ENGLISH_MAP.items() if hi in query]
    return (query + " " + " ".join(extras)) if extras else query

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


# ── Lightweight sensor context (simulator-only for now; swap DB tier later) ──

@dataclass
class SensorContext:
    """Normalised soil/ambient readings from any source."""
    soil_moisture_pct: Optional[float] = None
    soil_temp_c:       Optional[float] = None
    air_temp_c:        Optional[float] = None   # merged from weather after fetch
    humidity_pct:      Optional[float] = None   # merged from weather after fetch
    nitrogen_kg_ha:    Optional[float] = None
    phosphorus_kg_ha:  Optional[float] = None
    potassium_kg_ha:   Optional[float] = None
    soil_ph:           Optional[float] = None
    soil_health_score: Optional[int]   = None
    soil_health_grade: str             = "—"
    moisture_status:   str             = "Unknown"
    source:            str             = "none"

    def moisture_label(self) -> str:
        if self.soil_moisture_pct is None:
            return "N/A — sensor data unavailable"
        pct = self.soil_moisture_pct
        if pct < 35:
            return f"{pct:.1f}% — ⚠️ CRITICAL: Irrigate immediately"
        if pct < 50:
            return f"{pct:.1f}% — Low: Monitor closely"
        if pct <= 65:
            return f"{pct:.1f}% — Adequate"
        return f"{pct:.1f}% — High: Skip irrigation"


@dataclass
class WeatherConstraints:
    """Gate flags derived from the weather forecast."""
    alerts_text:        str  = "None"
    forecast_3day:      str  = "N/A"
    irrigation_blocked: bool = False   # soil adequate/high OR heavy rain forecast
    spray_blocked:      bool = False   # rain >20mm or >70% prob within 48 h
    frost_warning:      bool = False   # min_temp <2°C in 3 days
    heavy_rain_48h:     bool = False

def _classify_moisture(pct: Optional[float]) -> str:
    if pct is None:
        return "Unknown"
    if pct < 35:
        return "Critical"
    if pct < 50:
        return "Low"
    if pct <= 65:
        return "Adequate"
    return "High"


def _current_season(month: int = None) -> str:
    m = month or datetime.now().month
    # Kharif: sown Jun-Jul, harvested Sep-Oct  →  Jun-Sep
    if m in (6, 7, 8, 9):
        return "Kharif (Jun-Sep)"
    # Rabi: sown Oct-Nov, harvested Mar-Apr  →  Oct-Mar
    if m in (10, 11, 12, 1, 2, 3):
        return "Rabi (Oct-Mar)"
    # Zaid: Apr-May
    return "Zaid (Apr-May)"


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
        r"\b(crop|crops|fasal|fasalein|phasal)\s+(for|in|ke\s+liye)\s+(this|is|current|season|mausam)\b",
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
        r"\b(weather|mausam|मौसम|barish|बारिश|rain|forecast|flood|baad|बाढ़|drought|sukha|सूखा|temperature|tapman|तापमान|imd|meghdoot)\b",
        r"(हवामान|पाऊस|आবহাওয়া|বৃষ্টি|వాతావరణం|వర్షం|வானிலை|மழை|વરસાદ|ಹವಾಮಾನ|ಮಳೆ|കാലാവസ്ഥ|മഴ|ਮੌਸਮ|ਮੀਂਹ|ਪਾਣਿਪਾਗ|ବର୍ଷା|বতৰ|বৰষুণ)",
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

    v4.0 changes:
    - Structured grounded prompt: IoT sensor block + weather constraints + RAG snippets
    - Fixed follow-up intent: re-classifies prior user turn instead of reading missing key
    - Fixed season overlap: Oct/Nov now correctly Rabi
    - Fixed Gemini key validation: catches all placeholder patterns
    - Fixed null-coordinate guard: no silent TypeError on missing GPS
    - Concurrent data fetch: weather + market in parallel
    """

    # ── Legacy system prompt (kept for reference / fallback) ─────
    _SYSTEM_PROMPT_LEGACY = """You are KrishiMitra AI — a trusted, intelligent digital assistant for Indian farmers.
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

    # ── New structured grounded system prompt ─────────────────────
    # Uses Python single-brace {variable} format slots filled by _render_grounded_prompt().
    SYSTEM_PROMPT_TEMPLATE = (
        "You are KrishiMitra AI — an elite Smart Agricultural Advisory AI for Indian farmers. "
        "Your mission: SAFE, HIGHLY LOCALIZED, DATA-DRIVEN agronomy advice by synthesising "
        "live weather, official government guidelines, and real-time mandi prices.\n\n"

        "### OPERATIONAL FRAMEWORK\n"
        "1. PERCEIVE: Read [LIVE SENSOR DATA] first — flag any critical alerts.\n"
        "2. GROUND: Cross-reference with [GOVERNMENT & WEATHER DATA]. Advice MUST comply "
        "with official data, planting calendars, and active weather threats.\n"
        "3. DECIDE & ACT: Provide a tailored, step-by-step action plan.\n\n"

        "### CRITICAL RULES\n"
        "- DATA TRUTHFULNESS: NEVER recommend irrigation if moisture is Adequate or High. "
        "NEVER ignore an active weather alert.\n"
        "- SAFETY FIRST: For any chemical treatment, rely ONLY on the government snippet below. "
        "If the snippet says 'No specific advisory found', do NOT guess — defer to the local "
        "KVK extension officer or 1800-180-1551.\n"
        "- LANGUAGE: {lang_instruction}\n"
        "- TONALITY: Empathetic expert agronomist. Bullet points for action steps. "
        "Emojis where natural. Address farmer as 'किसान भाई' when responding in Hindi.\n\n"

        "---\n\n"
        "[LIVE SENSOR DATA] (source: {sensor_source})\n"
        "Soil Moisture  : {soil_moisture_label}\n"
        "Soil Temp      : {soil_temp_c}\n"
        "Ambient Temp   : {air_temp_c}\n"
        "Humidity       : {humidity_pct}\n"
        "N (Nitrogen)   : {nitrogen_kg_ha}  ({nitrogen_status})\n"
        "P (Phosphorus) : {phosphorus_kg_ha}  ({phosphorus_status})\n"
        "K (Potassium)  : {potassium_kg_ha}  ({potassium_status})\n"
        "Soil pH        : {soil_ph}  ({ph_status})\n"
        "Soil Health    : Score {soil_health_score}/100 — Grade {soil_health_grade}\n\n"

        "---\n\n"
        "[GOVERNMENT & WEATHER DATA]\n"
        "3-Day Forecast      : {forecast_3day}\n"
        "Severe Weather Alert: {active_weather_warnings}\n"
        "Irrigation Blocked  : {irrigation_blocked}\n"
        "Spray/Fert Blocked  : {spray_blocked}\n"
        "Frost Warning       : {frost_warning}\n\n"
        "Government/ICAR Advisory (use ONLY these facts for treatment recommendations):\n"
        "\"\"\"{government_rag_snippets}\"\"\"\n\n"
        "Current Market Price: {current_market_price}\n"
        "Season              : {season}\n"
        "Location            : {location_label}\n\n"

        "---\n\n"
        "[CONVERSATION HISTORY]\n"
        "{history_block}\n\n"

        "---\n\n"
        "[FARMER'S CURRENT QUERY]\n"
        "{farmer_query}\n\n"

        "---\n\n"
        "### RESPONSE EVALUATION (do silently before writing)\n"
        "1. Does the query CONFLICT with sensor/weather data? "
        "(e.g. asking to irrigate when moisture is Adequate → refuse + explain)\n"
        "2. Is there an active WEATHER ALERT? If yes, mention it FIRST.\n"
        "3. Is any chemical recommendation backed by the government snippet? "
        "If snippet is missing/generic, defer to KVK. Never invent a product or dose.\n\n"
        "Now write your response."
    )

    # ─────────────────────────────────────────────────────────────

    def answer(
        self,
        query: str,
        ctx: LocationContext,
        language: str = "hi",
        history: Optional[List[Dict[str, Any]]] = None,
        farmer_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point. Supports multi-turn conversation via `history`.

        history format (last N messages):
          [{"role": "user", "content": "..."},
           {"role": "assistant", "content": "...", "intent": "market_price"}]
        The "intent" key on assistant turns is optional but improves follow-up resolution.
        """
        query = (query or "").strip()
        lang  = normalise_language_code(language)

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

        # Multi-turn: inherit crops from recent history when none in current query
        if not crops_mentioned and history:
            for msg in reversed((history or [])[-6:]):
                past = msg.get("content") or msg.get("message_content") or ""
                if past:
                    past_crops = self._detect_crops(past)
                    if past_crops:
                        crops_mentioned = past_crops
                        break

        # ── Follow-up intent resolution (BUG FIX) ─────────────────
        # The history list only has {role, content} — "intent" is never present
        # unless the client explicitly stores it back. We use two strategies:
        # 1. Read embedded intent from last assistant turn (if client stores it)
        # 2. Re-classify the most recent prior user message
        if intent == INTENT_FOLLOWUP and history:
            resolved = False
            # Strategy 1: embedded intent key
            for msg in reversed(history):
                if msg.get("role") == "assistant" and msg.get("intent"):
                    intent = msg["intent"]
                    resolved = True
                    break
            # Strategy 2: re-classify prior user message
            if not resolved:
                prior_user_msgs = [m for m in history if m.get("role") == "user"]
                if prior_user_msgs:
                    prior_q = prior_user_msgs[-1].get("content", "")
                    prior_intent, prior_crops = self.classify_query(prior_q)
                    if prior_intent not in (INTENT_FOLLOWUP, INTENT_GENERAL):
                        intent = prior_intent
                        if not crops_mentioned and prior_crops:
                            crops_mentioned = prior_crops

        # ── Concurrent data fetch ─────────────────────────────────
        weather_data: Dict[str, Any] = {}
        prices_data:  Dict[str, Any] = {}
        sc = SensorContext()

        def _fetch_weather():
            return weather_service.get_weather(
                ctx.query_label, ctx.latitude, ctx.longitude, lang=lang
            )

        def _fetch_prices():
            crop_filter = crops_mentioned[0]["name"] if crops_mentioned else None
            return market_service.get_prices(
                ctx.query_label,
                lat=ctx.latitude,
                lon=ctx.longitude,
                state=ctx.state or None,
                crop=crop_filter,
            )

        def _fetch_iot():
            return self._resolve_sensor_context(ctx)

        if ctx.latitude is None or ctx.longitude is None:
            logger.warning(
                "Location context missing coordinates for %s — skipping weather/IoT fetch",
                ctx.display_name,
            )
        else:
            with ThreadPoolExecutor(max_workers=3) as pool:
                futures = {
                    pool.submit(_fetch_weather): "weather",
                    pool.submit(_fetch_prices):  "prices",
                    pool.submit(_fetch_iot):     "iot",
                }
                # Bug 1 fix: as_completed raises FuturesTimeout when the 6s window
                # expires before all futures complete. Catch it and collect whatever
                # results arrived; leave the rest as default empty values.
                try:
                    for fut in as_completed(futures, timeout=6):
                        key = futures[fut]
                        try:
                            result = fut.result()
                            if key == "weather":
                                weather_data = result or {}
                            elif key == "prices":
                                prices_data = result or {}
                            elif key == "iot":
                                sc = result
                        except Exception as exc:
                            logger.warning("Fetch failed for %s: %s", key, exc)
                except FuturesTimeout:
                    # Collect any already-completed futures before the timeout hit
                    for fut, key in futures.items():
                        if fut.done():
                            try:
                                result = fut.result()
                                if key == "weather" and not weather_data:
                                    weather_data = result or {}
                                elif key == "prices" and not prices_data:
                                    prices_data = result or {}
                                elif key == "iot" and sc.source == "none":
                                    sc = result
                            except Exception:
                                pass
                    logger.warning(
                        "Concurrent fetch timed out after 6s for %s — using partial data",
                        ctx.display_name,
                    )

        # Merge ambient readings from weather into sensor context
        cur = weather_data.get("current") or {}
        if sc.air_temp_c is None:
            sc.air_temp_c = cur.get("temperature")
        if sc.humidity_pct is None:
            sc.humidity_pct = cur.get("humidity")

        # ── Derive weather constraints ────────────────────────────
        wc = self._derive_weather_constraints(weather_data, sc)

        # ── Gov RAG snippets + market price string ────────────────
        rag        = self._fetch_gov_rag_snippets(query, intent, crops_mentioned)
        market_str = self._build_market_price_str(prices_data, crops_mentioned)

        # ── Build legacy context_block (for rule-based fallback + crop recs) ─
        context_block, sources = self._build_official_context(
            ctx, query, intent, crops_mentioned, lang=lang,
            _weather=weather_data, _prices=prices_data,
        )

        # ── History block (for Gemini prompt) ────────────────────
        history_block = "(new conversation)"
        if history:
            lines = []
            for msg in (history or [])[-8:]:
                role    = "Farmer" if msg.get("role") == "user" else "KrishiMitra"
                content = (msg.get("content") or msg.get("message_content") or "").strip()
                if content:
                    lines.append(f"{role}: {content}")
            if lines:
                history_block = "\n".join(lines)

        # Inject farmer profile into history block so AI personalises response
        if farmer_profile:
            profile_lines = []
            if farmer_profile.get("crop_history"):
                profile_lines.append(f"Past crops: {farmer_profile['crop_history']}")
            if farmer_profile.get("current_crop"):
                profile_lines.append(f"Current crop: {farmer_profile['current_crop']}")
            if farmer_profile.get("farm_size_bigha"):
                profile_lines.append(f"Farm size: {farmer_profile['farm_size_bigha']} bigha")
            if farmer_profile.get("soil_ph"):
                profile_lines.append(f"Soil pH: {farmer_profile['soil_ph']}")
            if farmer_profile.get("irrigation_type"):
                profile_lines.append(f"Irrigation: {farmer_profile['irrigation_type']}")
            if farmer_profile.get("has_pm_kisan"):
                profile_lines.append("Enrolled: PM-Kisan")
            if farmer_profile.get("sensor_reading"):
                s = farmer_profile["sensor_reading"]
                parts = []
                if s.get("nitrogen_kg_ha") is not None:
                    parts.append(f"N:{s['nitrogen_kg_ha']} kg/ha")
                if s.get("phosphorus_kg_ha") is not None:
                    parts.append(f"P:{s['phosphorus_kg_ha']} kg/ha")
                if s.get("potassium_kg_ha") is not None:
                    parts.append(f"K:{s['potassium_kg_ha']} kg/ha")
                if s.get("ph") is not None:
                    parts.append(f"pH:{s['ph']}")
                if s.get("ec_ds_m") is not None:
                    parts.append(f"EC:{s['ec_ds_m']} dS/m")
                if s.get("moisture_pct") is not None:
                    parts.append(f"Moisture:{s['moisture_pct']}%")
                if s.get("soil_temp_c") is not None:
                    parts.append(f"SoilTemp:{s['soil_temp_c']}°C")
                if s.get("organic_carbon") is not None:
                    parts.append(f"OC:{s['organic_carbon']}%")
                if parts:
                    profile_lines.append("Soil Sensors: " + ", ".join(parts))
            if profile_lines:
                profile_str = "[FARMER PROFILE] " + " | ".join(profile_lines)
                history_block = profile_str + "\n\n" + history_block

        now    = datetime.now()
        season = _current_season(now.month)

        # ── Generate response ─────────────────────────────────────
        # Priority chain:
        #   1. Gemini API (cloud, best quality)
        #   2. Qwen 2.5 7B + RAG (local, zero cost — Phase 1 server on port 8001)
        #   3. Rule-based fallback (always available offline)
        has_gemini    = _is_valid_gemini_key(gemini_service.api_key)
        response_text: Optional[str] = None
        data_source   = "KrishiMitra Advisory Engine"   # safe default — overwritten on success

        if has_gemini:
            try:
                rendered = self._render_grounded_prompt(
                    query=query, ctx=ctx, sc=sc, wc=wc, rag=rag,
                    market_price_str=market_str, history_block=history_block,
                    lang=lang, season=season,
                )
                response_text = gemini_service.generate(
                    prompt=rendered,
                    system_prompt="",  # all context already in rendered prompt
                    max_tokens=1600,
                    user_query=query,
                    temperature=0.3,
                )
                if response_text:
                    data_source = "Gemini AI + Official gov APIs"
                else:
                    logger.warning("Gemini returned empty — trying Qwen+RAG")
            except Exception as exc:
                logger.warning("Gemini failed: %s — trying Qwen+RAG", exc)

        # Tier 2: Qwen 2.5 7B + RAG (runs when Gemini absent or returned empty)
        if not response_text:
            response_text = self._qwen_rag_answer(
                query=query,
                ctx=ctx,
                lang=lang,
                history=history,
                sc=sc,
                wc=wc,
                market_str=market_str,
                farmer_profile=farmer_profile,
            )
            if response_text:
                data_source = "Qwen 2.5 7B + RAG (local)"

        # Tier 3: Rule-based fallback (always available, no external dependencies)
        if not response_text:
            response_text = self._smart_rule_response(
                query, intent, crops_mentioned, ctx, context_block, lang, history,
                sc=sc, wc=wc,
            )
            # data_source already set to default "KrishiMitra Advisory Engine"

        crop_suggestions = self._crop_suggestions_for_intent(
            ctx, intent, crops_mentioned, lang=lang
        )

        return {
            "response":        response_text,
            "intent":          intent,
            "sources":         list(dict.fromkeys(sources)),
            "crops_detected":  [c["name"] for c in crops_mentioned],
            "crop_suggestions": crop_suggestions,
            "language":        lang,
            "data_source":     data_source,
            "timestamp":       now.isoformat(),
        }

    # ── Tier 2: Qwen 2.5 7B + RAG (local Phase 1 server) ────────

    def _qwen_rag_answer(
        self,
        query: str,
        ctx: LocationContext,
        lang: str,
        history: Optional[List[Dict[str, Any]]],
        sc: SensorContext,
        wc: WeatherConstraints,
        market_str: str,
        farmer_profile: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Call the Phase 1 FastAPI server (http://127.0.0.1:8001/chat).
        Returns response text if the server is up and responds, None otherwise.
        All failures are silent — callers fall back to rule-based.

        Bug fixes applied:
        - Bug 2/3: json, urllib, re imported at module level; _HINDI_ENGLISH_MAP
          is a module-level constant — no per-call reconstruction.
        - Bug 5: query is augmented here with _augment_hindi_query() before
          sending to Phase 1. Phase 1's retriever.py also augments, but that's
          a server-side concern on its own query; we send the augmented string
          so the server receives better input even if its augmentation is off.
          To avoid double tokens we send the ORIGINAL query to Phase 1 in the
          `query` field and let Phase 1's retriever handle augmentation there.
          This is the cleanest separation: Django enriches context, Phase 1
          enriches the embedding lookup.
        """
        PHASE1_URL = "http://127.0.0.1:8001/chat"

        # Build sensor_context dict
        sensor_ctx: Optional[Dict[str, Any]] = None
        if sc.source != "none":
            sensor_ctx = {
                "moisture_pct":     sc.soil_moisture_pct,
                "moisture_status":  sc.moisture_status,
                "soil_temp_c":      sc.soil_temp_c,
                "ph":               sc.soil_ph,
                "nitrogen_kg_ha":   sc.nitrogen_kg_ha,
                "phosphorus_kg_ha": sc.phosphorus_kg_ha,
                "potassium_kg_ha":  sc.potassium_kg_ha,
                "temp_c":           sc.air_temp_c,
                "humidity_pct":     sc.humidity_pct,
                "source":           sc.source,
            }

        # Detect crop from conversation history
        crop_hint: Optional[str] = None
        if history:
            for msg in reversed(history[-6:]):
                detected = self._detect_crops(msg.get("content", ""))
                if detected:
                    crop_hint = detected[0]["name"]
                    break

        # Sanitise history for Phase 1
        clean_history = [
            {"role": m.get("role", "user"), "content": m.get("content", "")}
            for m in (history or [])[-8:]
            if m.get("content")
        ]

        payload = json.dumps({
            "query":          query,           # Phase 1 retriever augments internally
            "language":       lang,
            "location":       ctx.display_name,
            "latitude":       ctx.latitude,
            "longitude":      ctx.longitude,
            "crop":           crop_hint or (farmer_profile.get("current_crop") if farmer_profile else None),
            "season":         _current_season(),
            "history":        clean_history,
            "sensor_context": sensor_ctx,
            "farmer_profile": farmer_profile,  # NEW: personalisation context
            "stream":         False,
        }, ensure_ascii=False).encode("utf-8")

        try:
            req = urllib.request.Request(
                PHASE1_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = (data.get("response") or "").strip()
                if text:
                    logger.info(
                        "Qwen+RAG: '%s...' — %d chunks from %s",
                        query[:40],
                        data.get("rag_chunks", 0),
                        data.get("rag_sources", []),
                    )
                    return text
                # Phase 1 returned 200 but empty response — treat as unavailable
                logger.warning("Qwen+RAG returned empty response for: %s...", query[:40])
                return None
        except urllib.error.URLError:
            # Server not running — expected when Phase 1 is offline
            logger.debug("Phase 1 server offline — using rule-based fallback")
            return None
        except Exception as exc:
            logger.warning("Qwen+RAG unexpected error: %s", exc)
            return None

    # ── Sensor context: simulator only (no real hardware yet) ────

    def _resolve_sensor_context(self, ctx: LocationContext) -> SensorContext:
        """Fetch simulated IoT readings from BlockchainIoTSimulator.
        When real sensors are connected, add DB lookup here as Tier 1."""
        try:
            sim = iot_blockchain.get_iot_sensor_data(ctx.query_label)
            readings = sim.get("readings", {})
            npk      = readings.get("npk", {})
            health   = sim.get("soil_health_score", {})
            pct      = readings.get("soil_moisture_pct")
            sc = SensorContext(
                soil_moisture_pct=pct,
                soil_temp_c=readings.get("soil_temperature_c"),
                nitrogen_kg_ha=npk.get("nitrogen_kg_ha"),
                phosphorus_kg_ha=npk.get("phosphorus_kg_ha"),
                potassium_kg_ha=npk.get("potassium_kg_ha"),
                soil_ph=readings.get("soil_ph"),
                soil_health_score=health.get("score") if isinstance(health, dict) else None,
                soil_health_grade=health.get("grade", "—") if isinstance(health, dict) else "—",
                source="simulated",
            )
            sc.moisture_status = _classify_moisture(pct)
            return sc
        except Exception as exc:
            logger.warning("IoT simulator fetch failed: %s", exc)
            return SensorContext(source="none")

    # ── Weather constraints ───────────────────────────────────────

    def _derive_weather_constraints(
        self,
        weather: Dict[str, Any],
        sc: SensorContext,
    ) -> WeatherConstraints:
        wc = WeatherConstraints()

        alerts = weather.get("farming_alerts") or []
        wc.alerts_text = " | ".join(str(a) for a in alerts[:3]) if alerts else "None"

        forecast = (
            weather.get("forecast_7day")
            or weather.get("forecast_7_days")
            or []
        )

        if forecast:
            lines = []
            for day in forecast[:3]:
                lines.append(
                    f"{day.get('date')}: max {day.get('max_temp')}°C, "
                    f"rain {day.get('rainfall_mm', 0)}mm "
                    f"({day.get('rain_probability', 0)}% prob)"
                )
            wc.forecast_3day = "; ".join(lines)
        else:
            wc.forecast_3day = "Forecast unavailable — check mausam.imd.gov.in"

        # Spray block: heavy rain within 48 h
        for day in forecast[:2]:
            if (day.get("rainfall_mm") or 0) > 20 or (day.get("rain_probability") or 0) > 70:
                wc.spray_blocked   = True
                wc.heavy_rain_48h  = True
                break

        # Frost warning: min_temp <2°C in 3 days
        for day in forecast[:3]:
            if day.get("min_temp") is not None and day["min_temp"] < 2:
                wc.frost_warning = True
                break

        # Irrigation block: adequate/high moisture OR heavy rain forecast
        if sc.moisture_status in ("Adequate", "High") or wc.heavy_rain_48h:
            wc.irrigation_blocked = True

        return wc

    # ── Government RAG snippets ───────────────────────────────────

    def _fetch_gov_rag_snippets(
        self,
        query: str,
        intent: str,
        crops: List[Dict[str, Any]],
    ) -> str:
        snippets: List[str] = []

        if intent == INTENT_PEST_DISEASE:
            snippets.append(
                "ICAR IPM Package of Practices: Prefer neem oil (5ml/L) as first-line "
                "treatment. Chemical control: Imidacloprid 17.8SL @ 0.25ml/L for sucking "
                "pests; Mancozeb 75WP @ 2.5g/L for fungal diseases. Source: ICAR/PPQS."
            )

        if intent == INTENT_FERTILIZER:
            snippets.append(
                "ICAR recommends soil testing before fertiliser application. General NPK: "
                "120:60:40 kg/ha for wheat; 100:50:50 for rice. Use neem-coated urea (NCU) "
                "to cut volatilisation loss by 10-15%. Source: ICAR/FAI."
            )

        for crop in crops[:2]:
            try:
                from .comprehensive_crop_database import comprehensive_crop_database
                info = comprehensive_crop_database.get_crop_info(crop["id"])
                if info:
                    if intent == INTENT_PEST_DISEASE:
                        note = (info.get("pest_management") or "")[:200]
                    elif intent == INTENT_FERTILIZER:
                        note = (info.get("fertiliser_schedule") or "")[:200]
                    else:
                        note = ""
                    if note:
                        snippets.append(f"{crop['name'].title()} — {note}")
            except Exception:
                pass

        if not snippets:
            return (
                "No specific advisory found for this query. "
                "Please consult your local KVK extension officer or call 1800-180-1551."
            )

        return (" | ".join(snippets))[:500]

    # ── Market price slot string ──────────────────────────────────

    def _build_market_price_str(
        self,
        prices: Dict[str, Any],
        crops: List[Dict[str, Any]],
    ) -> str:
        if not prices.get("is_live"):
            parts = []
            for crop in crops[:3]:
                msp = MSP_2024_25.get(crop["id"])
                if msp:
                    parts.append(f"{crop['name'].title()}: ₹{msp}/q (MSP 2024-25)")
            base = "; ".join(parts) if parts else "N/A"
            return f"{base} — live mandi data unavailable, check agmarknet.gov.in"

        top = [c for c in (prices.get("top_crops") or []) if c.get("is_live")]
        if crops:
            crop_ids = {c["id"] for c in crops}
            matched = [
                c for c in top
                if crop_catalog.normalize(str(c.get("crop_name", "")))
                and crop_catalog.normalize(str(c.get("crop_name", "")))["id"] in crop_ids
            ]
            top = matched + [c for c in top if c not in matched]

        lines = []
        for c in top[:4]:
            modal  = c.get("modal_price")
            msp    = c.get("msp")
            mandi  = c.get("mandi_name", "N/A")
            profit = (
                f"+{c['profit_vs_msp']}% above MSP"
                if c.get("profit_vs_msp", 0) > 0
                else "below MSP"
            )
            lines.append(f"{c.get('crop_name')} ₹{modal}/q (MSP ₹{msp}) @ {mandi} — {profit}")
        return "; ".join(lines) if lines else "No live price rows today"

    # ── Render grounded prompt ────────────────────────────────────

    def _render_grounded_prompt(
        self,
        query: str,
        ctx: LocationContext,
        sc: SensorContext,
        wc: WeatherConstraints,
        rag: str,
        market_price_str: str,
        history_block: str,
        lang: str,
        season: str,
    ) -> str:
        def _fmt(val, fallback: str = "N/A") -> str:
            return str(val) if val is not None else fallback

        def _npk_status(val: Optional[float], low: float, high: float) -> str:
            if val is None:
                return "unknown"
            if val < low:
                return "⚠️ Low"
            return "✅ Adequate"

        def _ph_status(ph: Optional[float]) -> str:
            if ph is None:
                return "unknown"
            if ph < 5.5:
                return "⚠️ Very Acidic"
            if ph < 6.0:
                return "🟡 Acidic"
            if ph <= 7.5:
                return "✅ Optimal"
            if ph <= 8.0:
                return "🟡 Alkaline"
            return "⚠️ Very Alkaline"

        loc = ctx.display_name
        if ctx.state and ctx.state not in loc:
            loc = f"{ctx.display_name}, {ctx.state}"

        try:
            return self.SYSTEM_PROMPT_TEMPLATE.format(
                lang_instruction        = get_gemini_language_instruction(lang),
                sensor_source           = sc.source,
                soil_moisture_label     = sc.moisture_label(),
                soil_temp_c             = _fmt(sc.soil_temp_c, "N/A") + ("°C" if sc.soil_temp_c is not None else ""),
                air_temp_c              = _fmt(sc.air_temp_c, "N/A") + ("°C" if sc.air_temp_c is not None else ""),
                humidity_pct            = _fmt(sc.humidity_pct, "N/A") + ("%" if sc.humidity_pct is not None else ""),
                nitrogen_kg_ha          = _fmt(sc.nitrogen_kg_ha) + (" kg/ha" if sc.nitrogen_kg_ha is not None else ""),
                nitrogen_status         = _npk_status(sc.nitrogen_kg_ha, 150, 250),
                phosphorus_kg_ha        = _fmt(sc.phosphorus_kg_ha) + (" kg/ha" if sc.phosphorus_kg_ha is not None else ""),
                phosphorus_status       = _npk_status(sc.phosphorus_kg_ha, 10, 25),
                potassium_kg_ha         = _fmt(sc.potassium_kg_ha) + (" kg/ha" if sc.potassium_kg_ha is not None else ""),
                potassium_status        = _npk_status(sc.potassium_kg_ha, 100, 200),
                soil_ph                 = _fmt(sc.soil_ph),
                ph_status               = _ph_status(sc.soil_ph),
                soil_health_score       = sc.soil_health_score if sc.soil_health_score is not None else "—",
                soil_health_grade       = sc.soil_health_grade,
                forecast_3day           = wc.forecast_3day,
                active_weather_warnings = wc.alerts_text,
                irrigation_blocked      = "YES ⚠️" if wc.irrigation_blocked else "No",
                spray_blocked           = "YES ⚠️ (rain forecast within 48h)" if wc.spray_blocked else "No",
                frost_warning           = "YES ❄️" if wc.frost_warning else "No",
                government_rag_snippets = rag,
                current_market_price    = market_price_str,
                season                  = season,
                location_label          = loc,
                history_block           = history_block,
                farmer_query            = query,
            )
        except KeyError as exc:
            logger.warning("Prompt template render failed (%s) — falling back to legacy format", exc)
            return (
                f"Farmer location: {loc}\nSeason: {season}\n"
                f"Language instruction: {get_gemini_language_instruction(lang)}\n\n"
                f"Official live data:\n{rag}\nMarket: {market_price_str}\n\n"
                f"Farmer query: {query}"
            )

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
        _weather: Optional[Dict[str, Any]] = None,
        _prices: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[str]]:
        """Fetch and format live official data for this farmer's location.

        _weather and _prices can be passed in from the concurrent fetch in
        answer() to avoid duplicate network calls.
        """
        lines: List[str] = []
        sources: List[str] = []

        # 1. Live weather (always)
        if ctx.latitude is None or ctx.longitude is None:
            logger.warning(
                "Missing coordinates for %s — skipping weather fetch",
                ctx.display_name,
            )
            lines.append("[WEATHER] Location coordinates unavailable — check mausam.imd.gov.in")
        else:
            try:
                weather = _weather if _weather else weather_service.get_weather(
                    ctx.query_label, ctx.latitude, ctx.longitude, lang=lang
                )
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
                        wb  = day.get("water_balance_mm")
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
            except Exception as exc:
                logger.warning(
                    "Weather fetch failed in chat context (lat=%s, lon=%s): %s",
                    ctx.latitude, ctx.longitude, exc,
                )
                lines.append("[WEATHER] Temporarily unavailable — check mausam.imd.gov.in")

        # 2. Market prices
        try:
            prices = _prices if _prices else market_service.get_prices(
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
        *,
        sc: Optional[SensorContext] = None,
        wc: Optional[WeatherConstraints] = None,
    ) -> str:
        """
        Intelligent, context-aware responses built from live data.
        Personalised to location, weather, season, and conversation history.
        Includes evaluation checks: weather alerts, moisture vs. irrigation,
        spray block before rain.
        """
        sc  = sc  or SensorContext()
        wc  = wc  or WeatherConstraints()
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
        now    = datetime.now()

        # ── Evaluation Check 1: active weather alerts (prefix all responses) ─
        alert_prefix = ""
        if wc.alerts_text and wc.alerts_text != "None":
            alert_prefix = (
                f"⚠️ **कृषि चेतावनी:** {wc.alerts_text}\n\n"
                if lang == "hi" else
                f"⚠️ **Farming Alert:** {wc.alerts_text}\n\n"
            )

        # ── Evaluation Check 2: irrigation vs. moisture ───────────
        if intent == INTENT_IRRIGATION:
            if sc.moisture_status in ("Adequate", "High") and sc.soil_moisture_pct is not None:
                msg = (
                    f"💧 **सिंचाई की जरूरत नहीं।**\n\n"
                    f"आपके खेत की मिट्टी में नमी **{sc.soil_moisture_pct:.1f}%** है "
                    f"(स्तर: {sc.moisture_status}) — अभी सिंचाई न करें, इससे जलभराव होगा।\n\n"
                    f"अगली सिंचाई तब करें जब नमी 45% से नीचे आए।\n\n"
                    f"📞 PM-KUSUM: 1800-180-3333"
                    if lang == "hi" else
                    f"Soil moisture is **{sc.soil_moisture_pct:.1f}%** "
                    f"({sc.moisture_status}) — irrigation is NOT needed right now. "
                    f"Irrigate when moisture drops below 45%.\n\n"
                    f"📞 PM-KUSUM: 1800-180-3333"
                )
                return alert_prefix + msg
            if sc.moisture_status == "Critical" and sc.soil_moisture_pct is not None:
                msg = (
                    f"🚨 **तुरंत सिंचाई करें!**\n\n"
                    f"मिट्टी की नमी **{sc.soil_moisture_pct:.1f}%** है (Critical)। "
                    f"फसल पर सूखे का खतरा है। तुरंत 40-50mm सिंचाई करें।\n\n"
                    f"📞 PM-KUSUM: 1800-180-3333"
                    if lang == "hi" else
                    f"🚨 **Irrigate immediately!** Soil moisture is "
                    f"**{sc.soil_moisture_pct:.1f}%** (Critical). "
                    f"Apply 40-50mm water now to prevent crop stress.\n\n"
                    f"📞 PM-KUSUM: 1800-180-3333"
                )
                return alert_prefix + msg

        # ── Evaluation Check 3: spray/fertiliser before forecasted rain ───
        spray_warning = ""
        if intent in (INTENT_FERTILIZER, INTENT_PEST_DISEASE) and wc.spray_blocked:
            spray_warning = (
                f"⚠️ **स्प्रे/खाद अभी न डालें** — अगले 48 घंटों में भारी बारिश की संभावना है। "
                f"बारिश के बाद ही करें।\n\n"
                if lang == "hi" else
                f"⚠️ **Postpone spray/fertiliser** — heavy rain forecast within 48 hours. "
                f"Apply after the rain.\n\n"
            )

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
            return alert_prefix + msgs.get(lang, msgs["en"])

        # ── WEATHER ──────────────────────────────────────────────
        if intent == INTENT_WEATHER:
            forecast_lines = [l for l in context_block.splitlines() if l.strip().startswith("202")]
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
            return alert_prefix + resp

        # ── CROP RECOMMENDATION ──────────────────────────────────
        if intent in (INTENT_CROP_RECOMMENDATION, INTENT_CROP_INFO):
            rec_lines = [l for l in context_block.splitlines() if "suitability" in l]

            header = {
                "hi": f"🌾 **{loc}** के लिए फसल सुझाव — {season}\n\n🌡️ मौसम: {temp}°C, {cond}\n\n",
                "en": f"🌾 Crop Recommendations for **{loc}** — {season}\n\n🌡️ Weather: {temp}°C, {cond}\n\n",
            }.get(lang, f"Crop recommendations for {loc}:\n\n")

            if rec_lines:
                body = ""
                for i, line in enumerate(rec_lines[:5], 1):
                    m = re.search(
                        r"\s*([^(:]+)\s*(?:\(([^)]*)\))?:\s*suitability\s*([\d]+)%,"
                        r".*profit\s*Rs\s*([\d,]+)/ha,\s*MSP\s*Rs\s*([\d]+)/q",
                        line,
                    )
                    if m:
                        crop_name  = m.group(1).strip()
                        local_desc = f" ({m.group(2).strip()})" if m.group(2) else ""
                        score      = m.group(3)
                        profit     = m.group(4)
                        msp        = m.group(5)
                        bar = "🟢" if int(score) >= 80 else "🟡" if int(score) >= 60 else "🔴"
                        body += (
                            f"{i}. {bar} **{crop_name}{local_desc}** — {score}% सटीकता\n"
                            f"   ₹{profit}/हे. लाभ | MSP ₹{msp}/q\n"
                        )
                    else:
                        body += f"• {line.strip().lstrip('- ')}\n"
            else:
                body = (
                    "• 🟢 **गेहूँ** — रबी सीजन, MSP ₹2,275/q\n"
                    "• 🟢 **सरसों** — कम पानी, MSP ₹5,650/q\n"
                    "• 🟡 **चना** — हल्की मिट्टी, MSP ₹5,440/q\n"
                    if lang == "hi" else
                    "• 🟢 **Wheat** — Rabi season, MSP ₹2,275/q\n"
                    "• 🟢 **Mustard** — low water, MSP ₹5,650/q\n"
                    "• 🟡 **Gram** — light soil, MSP ₹5,440/q\n"
                )

            footer = {
                "hi": f"\n\n💡 {farming_advice or 'बुवाई से पहले मिट्टी जांच करवाएं।'}\n📞 ICAR: 1800-180-1551",
                "en": f"\n\n💡 {farming_advice or 'Get soil tested before sowing.'}\n📞 ICAR: 1800-180-1551",
            }.get(lang, "")
            return alert_prefix + header + body + footer

        # ── MARKET PRICE ─────────────────────────────────────────
        if intent == INTENT_MARKET_PRICE:
            price_lines = [l for l in context_block.splitlines() if "modal Rs" in l]
            msp_lines   = [l for l in context_block.splitlines() if "[MSP 2024-25]" in l or "MSP 2024-25" in l]

            if price_lines:
                header = {
                    "hi": f"💰 **{loc}** के पास मंडी भाव (आज, Agmarknet):\n\n",
                    "en": f"💰 Live Mandi Prices near **{loc}** (Agmarknet today):\n\n",
                }.get(lang, f"Mandi prices near {loc}:\n\n")
                body = ""
                for line in price_lines[:8]:
                    m = re.search(
                        r"\s*([^(:]+)\s*(?:\(([^)]*)\))?:\s*modal\s*Rs\s*([\d]+)"
                        r"(?:/q)?,\s*MSP\s*Rs\s*([\d]+)(?:/q)?,\s*mandi:\s*([^,\n]+)",
                        line,
                    )
                    if m:
                        crop       = m.group(1).strip()
                        local_desc = f" ({m.group(2).strip()})" if m.group(2) else ""
                        modal      = m.group(3)
                        msp        = m.group(4)
                        mandi      = m.group(5).strip()
                        profit     = int(modal) - int(msp)
                        ind = "📈" if profit >= 0 else "📉"
                        body += f"• {ind} **{crop}{local_desc}** : ₹{modal}/q | MSP ₹{msp}/q | 🏪 {mandi}\n"
                    else:
                        body += f"• {line.strip().lstrip('- ')}\n"
                footer = {
                    "hi": "\n📊 स्रोत: Agmarknet/data.gov.in | agmarknet.gov.in",
                    "en": "\n📊 Source: Agmarknet/data.gov.in | agmarknet.gov.in",
                }.get(lang, "")
                return alert_prefix + header + body + footer
            else:
                msp_body = ""
                if msp_lines:
                    for line in msp_lines[:5]:
                        msp_body += f"• {line.replace('[MSP 2024-25]', '').strip()}\n"
                else:
                    msp_body = (
                        "• गेहूँ: ₹2,275/q\n• धान: ₹2,300/q\n• सरसों: ₹5,650/q\n"
                        "• मक्का: ₹2,090/q\n• सोयाबीन: ₹4,892/q"
                        if lang == "hi" else
                        "• Wheat: ₹2,275/q\n• Rice: ₹2,300/q\n• Mustard: ₹5,650/q\n"
                        "• Maize: ₹2,090/q\n• Soybean: ₹4,892/q"
                    )
                no_live = {
                    "hi": (
                        f"⚠️ आज का लाइव मंडी भाव उपलब्ध नहीं।\n\n"
                        f"📊 **MSP 2024-25** (न्यूनतम समर्थन मूल्य):\n{msp_body}\n\n"
                        f"🌐 agmarknet.gov.in पर देखें\n📞 eNAM: 1800-270-0224"
                    ),
                    "en": (
                        f"⚠️ Live mandi prices unavailable.\n\n"
                        f"📊 **MSP 2024-25** (Minimum Support Price):\n{msp_body}\n\n"
                        f"🌐 Check agmarknet.gov.in\n📞 eNAM: 1800-270-0224"
                    ),
                }.get(lang, f"Live mandi prices unavailable. MSP:\n{msp_body}")
                return alert_prefix + no_live

        # ── GOVERNMENT SCHEMES ────────────────────────────────────
        if intent == INTENT_GOVERNMENT_SCHEME:
            scheme_lines = [l for l in context_block.splitlines() if "Apply:" in l]
            header = {
                "hi": "🏛️ **किसानों के लिए सरकारी योजनाएं:**\n\n",
                "en": "🏛️ **Government Schemes for Farmers:**\n\n",
            }.get(lang, "Government schemes:\n\n")
            if scheme_lines:
                body = "\n".join(f"• {l.strip().lstrip('- ')}" for l in scheme_lines[:5])
            else:
                body = (
                    "• **PM-Kisan**: ₹6,000/वर्ष — pmkisan.gov.in | 155261\n"
                    "• **PMFBY**: 2% प्रीमियम फसल बीमा — pmfby.gov.in | 14447\n"
                    "• **KCC**: ₹3 लाख @4% ब्याज — निकटतम बैंक\n"
                    "• **PM-KUSUM**: 90% सब्सिडी सोलर पंप — pmkusum.mnre.gov.in\n"
                    "• **Soil Health Card**: मुफ्त मिट्टी जांच — soilhealth.dac.gov.in"
                    if lang == "hi" else
                    "• **PM-Kisan**: ₹6,000/year — pmkisan.gov.in | 155261\n"
                    "• **PMFBY**: 2% premium crop insurance — pmfby.gov.in | 14447\n"
                    "• **KCC**: ₹3L credit @4% interest — nearest bank\n"
                    "• **PM-KUSUM**: 90% subsidy solar pump — pmkusum.mnre.gov.in\n"
                    "• **Soil Health Card**: Free soil testing — soilhealth.dac.gov.in"
                )
            return alert_prefix + header + body + "\n\n📞 Kisan Call Centre: **1800-180-1551** (Free)"

        # ── PEST / DISEASE ────────────────────────────────────────
        if intent == INTENT_PEST_DISEASE:
            crop_hint = f" ({crops[0]['name']})" if crops else ""
            body = {
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
            return alert_prefix + spray_warning + body

        # ── FERTILIZER ────────────────────────────────────────────
        if intent == INTENT_FERTILIZER:
            crop_hint = f" for {crops[0]['name']}" if crops else ""
            body = {
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
            return alert_prefix + spray_warning + body

        # ── IRRIGATION ────────────────────────────────────────────
        if intent == INTENT_IRRIGATION:
            et0      = _extract(r"ET0 ([\d.]+)mm/day")
            irr_lines = [l for l in context_block.splitlines() if "IRRIGATE" in l]
            body = {
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
                    + "📞 PM-KUSUM: 1800-180-3333"
                ),
                "en": (
                    f"💧 **Irrigation Advisory — {loc}**\n\n"
                    f"🌡️ Weather: {temp}°C | ET₀: {et0} mm/day\n\n"
                    f"**PM-KUSUM Solar Pump:** 90% subsidy — pmkusum.mnre.gov.in\n\n"
                    f"**Methods:**\n• Drip: 40-50% water saving, 90% subsidy\n"
                    f"• Sprinkler: 30-35% saving\n• AWD for paddy: 25% less water\n\n"
                    + (f"⚠️ Irrigate: {', '.join(l.strip() for l in irr_lines[:3])}\n" if irr_lines else "")
                    + "📞 PM-KUSUM: 1800-180-3333"
                ),
            }.get(lang, f"Irrigation: ET0={et0}mm/day. Use drip/sprinkler. PM-KUSUM 90% subsidy.")
            return alert_prefix + body

        # ── GENERAL / FOLLOW-UP ──────────────────────────────────
        lines_out: List[str] = []

        if temp != "—":
            fa_note = f" — {farming_advice}" if farming_advice else ""
            lines_out.append(
                f"🌡️ **{loc}** मौसम: **{temp}°C**, {cond}{fa_note}"
                if lang == "hi" else
                f"🌡️ **{loc}** weather: **{temp}°C**, {cond}{fa_note}"
            )

        if crops:
            for crop in crops[:2]:
                msp = crop.get("msp") or MSP_2024_25.get(crop["id"])
                if msp:
                    lines_out.append(f"• {crop['name']} MSP 2024-25: ₹{msp}/q")

        rec_lines = [l for l in context_block.splitlines() if "suitability" in l]
        if rec_lines:
            lines_out.append("🌾 **फसल सुझाव:**" if lang == "hi" else "🌾 **Crop Suggestions:**")
            for l in rec_lines[:3]:
                m_crop = re.match(r"\s+([^:]+):", l)
                if m_crop:
                    lines_out.append(f"  • {m_crop.group(1).strip()}")

        lines_out.append(
            "\n💬 और पूछें: फसल भाव, मौसम, PM-Kisan, कीट-रोग\n📞 1800-180-1551"
            if lang == "hi" else
            "\n💬 Ask about: prices, weather, PM-Kisan, pest control\n📞 1800-180-1551"
        )

        return alert_prefix + "\n".join(lines_out)

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
