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
        r"कौन\s*सी\s*फसल",
        r"कौन सी फसल",
    ]),
    (INTENT_MARKET_PRICE, [
        r"\b(msp|mandi|market\s*price|bhav|भाव|मंडी)\b",
        r"price\s+of",
        r"की\s*कीमत",
        r"बिक्री\s*मूल्य",
        r"modal\s*price",
        r"बाजार\s*भाव",
        r"दाम",
    ]),
    (INTENT_WEATHER, [
        r"\b(weather|mausam|मौसम|barish|बारिश|rain|forecast|तापमान|temperature)\b",
        r"imd\b",
        r"सिंचाई\s*का\s*समय",
        r"बुवाई\s*का\s*समय",
        r"कल\s*मौसम",
        r"आज\s*मौसम",
    ]),
    (INTENT_GOVERNMENT_SCHEME, [
        r"\b(pm[- ]?kisan|pmfby|kcc|kusum|enam|scheme|yojana|योजना)\b",
        r"सब्सिडी",
        r"loan\s+for\s+farmer",
        r"किसान\s*क्रेडिट",
        r"सरकारी\s*योजना",
        r"अनुदान",
    ]),
    (INTENT_PEST_DISEASE, [
        r"\b(pest|disease|keet|kit|rog|रोग|कीट|blight|blast)\b",
        r"उपचार",
        r"सफेद\s*मक्खी",
        r"पीली\s*पत्ती",
        r"फसल\s*बीमारी",
        r"दवाई\s*डालें",
    ]),
    (INTENT_SOIL, [
        r"\b(soil|mitti|मिट्टी|npk|ph)\b",
        r"soil\s*health",
        r"मिट्टी\s*जांच",
        r"भूमि\s*परीक्षण",
    ]),
    (INTENT_IRRIGATION, [
        r"\b(irrigation|sinchai|सिंचाई|drip|sprinkler)\b",
        r"पानी\s*देना",
        r"कब\s*सिंचाई",
    ]),
    (INTENT_FERTILIZER, [
        r"\b(urea|dap|fertilizer|urvarak|उर्वरक|npk)\b",
        r"खाद\s*डाल",
        r"कितनी\s*खाद",
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
5. Match the user's language exactly: Hindi → Hindi, English → English, Hinglish → simple Hinglish.
6. Be practical, use short paragraphs and bullet points for steps.
7. For crop recommendations, cite suitability scores and reasons from the data block.
8. For pest/disease: recommend KrishiRaksha photo upload in the app for accurate diagnosis.
9. Always mention the farmer's actual GPS location and current weather in your answer.
10. Format key numbers (MSP, prices, temperatures) in bold or with ₹ symbol.

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
                "ml": "ദയവായി നിങ്ങളുടെ ചോദ്യം ಟೈപ്പ് ചെയ്യുക.",
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
        # Pass lang into _build_official_context so crop engine uses right language
        context_block, sources = self._build_official_context(ctx, query, intent, crops_mentioned, lang=lang)

        loc = ctx.display_name
        if ctx.state:
            loc = f"{loc}, {ctx.state}"

        # Build multi-language instruction for Gemini
        lang_instruction = get_gemini_language_instruction(lang)

        # Build current date/season context
        now = datetime.now()
        season = _current_season(now.month)

        user_prompt = f"""Farmer location: {loc} (GPS: {ctx.latitude:.4f}, {ctx.longitude:.4f})
Date: {now.strftime('%d %B %Y')}, Season: {season}
{lang_instruction}
Detected intent: {intent}
Crops mentioned: {', '.join(c['name'] for c in crops_mentioned) or 'none'}

=== Official live data (authoritative — cite these facts) ===
{context_block}

=== Farmer question ===
{query}

Answer using ONLY the official data above. Be specific about the farmer's location ({loc}) and current season ({season}).
If crop recommendation was asked, list top 3 crops with suitability scores and profit/ha from the data block."""

        has_gemini = (
            gemini_service.api_key
            and not gemini_service.api_key.startswith("your")
            and gemini_service.api_key != "YOUR_GEMINI_API_KEY_HERE"
        )

        if has_gemini:
            response_text = gemini_service.generate(
                user_prompt,
                self.SYSTEM_PROMPT,
                max_tokens=1500,
                user_query=query,
                temperature=0.3,
            )
        else:
            # Rich context-aware rule-based response (no Gemini needed)
            response_text = self._context_aware_rule_response(
                query, intent, crops_mentioned, ctx, context_block, lang
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
            + (" + Gemini AI" if has_gemini else " (smart rule-based)"),
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
        lang: str = "hi",
    ) -> Tuple[str, List[str]]:
        lines: List[str] = []
        sources: List[str] = []

        # ── Live Weather ───────────────────────────────────────────────────
        weather = weather_service.get_weather(
            ctx.query_label, ctx.latitude, ctx.longitude, lang=lang
        )
        cur = weather.get("current") or {}
        temp = cur.get("temperature")
        humidity = cur.get("humidity")
        condition = cur.get("condition_local") or cur.get("condition", "")
        wind = cur.get("wind_speed")
        rain_now = cur.get("rainfall_mm", 0)

        lines.append(
            f"Live weather at {ctx.display_name}: {temp}°C, {condition}, "
            f"humidity {humidity}%, wind {wind} km/h, rain {rain_now} mm/hr"
        )
        if weather.get("farming_advice"):
            lines.append(f"Farming advice (live): {weather['farming_advice']}")
        sources.append(weather.get("data_source", "Open-Meteo weather"))

        # 7-day forecast — use correct key names
        forecast = (
            weather.get("forecast_7day")
            or weather.get("forecast_7_days")
            or weather.get("forecast")
            or []
        )
        if forecast:
            lines.append(f"7-day forecast for {ctx.display_name}:")
            for day in forecast[:4]:
                lines.append(
                    f"  - {day.get('date')}: max {day.get('max_temp')}°C, "
                    f"rain {day.get('rainfall_mm', 0)} mm, "
                    f"prob {day.get('rain_probability', 0)}%"
                )

        alerts = weather.get("farming_alerts") or []
        if alerts:
            lines.append("Farming alerts: " + " | ".join(str(a) for a in alerts[:3]))

        # ── Live Mandi Prices ─────────────────────────────────────────────
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
                    "Live mandi prices: Not available (DATA_GOV_IN_API_KEY not set). "
                    "Visit agmarknet.gov.in for today's prices."
                )
            else:
                lines.append(f"Live mandi prices near {ctx.display_name} (Rs/quintal):")
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
                        f"  - {c.get('crop_name')} ({c.get('crop_name_hindi','')}): "
                        f"modal Rs{c.get('modal_price')}/q, "
                        f"MSP Rs{c.get('msp')}/q, mandi: {c.get('mandi_name', 'N/A')}"
                    )

        # ── Crop Recommendations ──────────────────────────────────────────
        if intent in (INTENT_CROP_RECOMMENDATION, INTENT_GENERAL) or \
           any(w in query.lower() for w in ("crop", "fasal", "फसल", "खेती", "उगा", "लगा")):
            try:
                rec = crop_recommendation_engine.recommend_from_context(ctx, language=lang)
                sources.append(rec.get("data_source", "Crop advisory engine"))
                season = rec.get("season", "")
                zone = rec.get("agro_zone") or rec.get("region") or ""
                lines.append(
                    f"Crop advisory for {ctx.display_name} — season: {season}, zone: {zone}:"
                )
                for r in (rec.get("recommendations") or [])[:5]:
                    local_name = r.get("crop_name_local") or r.get("crop_name_hindi") or r.get("crop_name", "")
                    lines.append(
                        f"  - {r.get('crop_name')} ({local_name}): "
                        f"suitability {r.get('suitability_score')}%, "
                        f"reason: {r.get('reason_hindi') or r.get('reason', '')}, "
                        f"profit Rs{r.get('profit_per_hectare', 0):,}/ha, "
                        f"MSP Rs{r.get('msp_per_quintal', 0)}/q"
                    )
            except Exception as exc:
                logger.warning("Crop recommendation error in chat context: %s", exc)

        # ── Government Schemes ────────────────────────────────────────────
        if intent == INTENT_GOVERNMENT_SCHEME or any(
            w in query.lower() for w in ("yojana", "scheme", "kisan", "योजना", "सब्सिडी", "subsidy")
        ):
            try:
                schemes = schemes_service.get_schemes(ctx.query_label)
                sources.append("Government schemes catalog (MoAFW / PM-Kisan / PMFBY)")
                for s in (schemes.get("schemes") or [])[:6]:
                    lines.append(
                        f"  - {s.get('name')} / {s.get('name_hindi', '')}: "
                        f"{s.get('benefit', s.get('description', ''))[:150]}"
                    )
            except Exception as exc:
                logger.warning("Schemes error in chat context: %s", exc)

        # ── MSP for mentioned crops ───────────────────────────────────────
        for crop in crops[:3]:
            msp = crop.get("msp") or MSP_2024_25.get(crop["id"])
            if msp:
                lines.append(f"MSP 2024-25 for {crop['name']}: Rs{msp}/quintal (Cabinet approved)")

        # ── Pest/disease note ─────────────────────────────────────────────
        if intent == INTENT_PEST_DISEASE:
            lines.append(
                "Pest/disease note: Upload a clear leaf/plant photo in KrishiRaksha for "
                "ML-assisted diagnosis. General IPM: monitor weekly, remove infected parts, "
                "use neem oil 5ml/L as first step; follow ICAR package of practices."
            )
            sources.append("ICAR IPM guidelines (general)")

        return "\n".join(lines), list(dict.fromkeys(sources))

    # ── Rich rule-based response when Gemini is not configured ───────────
    def _context_aware_rule_response(
        self,
        query: str,
        intent: str,
        crops: List[Dict[str, Any]],
        ctx: LocationContext,
        context_block: str,
        lang: str = "hi",
    ) -> str:
        """Build a rich, context-aware answer from the live data block without Gemini."""
        loc = ctx.display_name
        if ctx.state and ctx.state != loc:
            loc = f"{ctx.display_name}, {ctx.state}"

        # Parse live values from context_block for inline use
        weather_line = next((l for l in context_block.splitlines() if l.startswith("Live weather")), "")
        temp_match = re.search(r"([\d.]+)°C", weather_line)
        temp = temp_match.group(1) if temp_match else "—"

        advice_line = next((l for l in context_block.splitlines() if l.startswith("Farming advice")), "")
        farming_advice = advice_line.replace("Farming advice (live): ", "").strip()

        # Crop recommendations from context
        rec_lines = [l for l in context_block.splitlines() if l.strip().startswith("- ") and "suitability" in l]

        if intent == INTENT_GREETING:
            return {
                "hi": (f"नमस्ते! 🌾 मैं KrishiMitra AI हूँ — आपका डिजिटल कृषि सहायक।\n\n"
                       f"📍 आपकी लोकेशन: {loc}\n"
                       f"🌡️ अभी का मौसम: {temp}°C — {farming_advice or 'सामान्य कृषि कार्य जारी रखें'}\n\n"
                       f"आप पूछ सकते हैं:\n• फसल सुझाव — कौन सी फसल उगाऊं?\n"
                       f"• मंडी भाव — गेहूँ/धान का आज का भाव?\n• मौसम पूर्वानुमान\n"
                       f"• सरकारी योजनाएं — PM-Kisan, PMFBY\n• कीट/रोग उपचार\n\n"
                       f"📞 किसान कॉल सेंटर: 1800-180-1551"),
                "en": (f"Hello! 🌾 I'm KrishiMitra AI — your digital farming assistant.\n\n"
                       f"📍 Your location: {loc}\n"
                       f"🌡️ Current weather: {temp}°C — {farming_advice or 'Suitable for farming'}\n\n"
                       f"You can ask about:\n• Crop recommendations\n• Mandi prices\n"
                       f"• Weather forecast\n• Government schemes\n• Pest/disease treatment\n\n"
                       f"📞 Kisan Call Centre: 1800-180-1551"),
            }.get(lang, f"Namaste! KrishiMitra AI — {loc}. Weather: {temp}°C. Ask about crops, prices, weather.")

        if intent == INTENT_WEATHER:
            forecast_lines = [l for l in context_block.splitlines() if l.strip().startswith("- 202")]
            forecast_text = "\n".join(forecast_lines[:4]) if forecast_lines else ""
            alerts = [l for l in context_block.splitlines() if "alert" in l.lower() or "🚨" in l or "🌡️" in l]
            alerts_text = "\n".join(alerts[:3]) if alerts else ""

            resp = {
                "hi": f"🌦️ {loc} का लाइव मौसम:\n\n• तापमान: {temp}°C\n• कृषि सलाह: {farming_advice or 'सामान्य कार्य जारी रखें'}\n\n",
                "en": f"🌦️ Live weather for {loc}:\n\n• Temperature: {temp}°C\n• Farming advice: {farming_advice or 'Continue normal farm activities'}\n\n",
            }.get(lang, f"🌦️ Live weather {loc}: {temp}°C\n{farming_advice}\n\n")

            if forecast_text:
                resp += ("📅 7 दिन का पूर्वानुमान:\n" if lang == "hi" else "📅 7-day forecast:\n")
                resp += forecast_text + "\n\n"
            if alerts_text:
                resp += alerts_text + "\n\n"
            resp += "🌐 IMD: mausam.imd.gov.in"
            return resp

        if intent == INTENT_CROP_RECOMMENDATION:
            intro = {
                "hi": f"🌾 {loc} के लिए फसल सुझाव (अभी का मौसम):\n\n",
                "en": f"🌾 Crop recommendations for {loc} (current season):\n\n",
            }.get(lang, f"🌾 Crop suggestions for {loc}:\n\n")

            body = ""
            if rec_lines:
                body = "\n".join(f"• {l.strip().lstrip('- ')}" for l in rec_lines[:5])
            else:
                body = (
                    "• गेहूँ (Wheat) — रबी सीजन, MSP ₹2,275/q\n"
                    "• सरसों (Mustard) — कम पानी, अच्छा मुनाफा, MSP ₹5,650/q\n"
                    "• चना (Gram) — रबी, MSP ₹5,440/q\n"
                    "• मक्का (Maize) — खरीफ, MSP ₹2,090/q"
                    if lang == "hi" else
                    "• Wheat — Rabi season, MSP ₹2,275/q\n"
                    "• Mustard — low water, high profit, MSP ₹5,650/q\n"
                    "• Gram — Rabi, MSP ₹5,440/q\n"
                    "• Maize — Kharif, MSP ₹2,090/q"
                )

            footer = {
                "hi": f"\n\n🌡️ मौसम: {temp}°C — {farming_advice or ''}\n📞 ICAR: 1800-180-1551",
                "en": f"\n\n🌡️ Weather: {temp}°C — {farming_advice or ''}\n📞 ICAR: 1800-180-1551",
            }.get(lang, "")
            return intro + body + footer

        if intent == INTENT_MARKET_PRICE:
            price_lines = [l for l in context_block.splitlines() if "modal Rs" in l or "modal ₹" in l]

            if price_lines:
                intro = {
                    "hi": f"💰 {loc} के पास मंडी भाव (आज):\n\n",
                    "en": f"💰 Mandi prices near {loc} (today):\n\n",
                }.get(lang, f"Mandi prices near {loc}:\n\n")
                body = "\n".join(f"• {l.strip().lstrip('- ')}" for l in price_lines[:8])
                footer = {
                    "hi": "\n\n📊 स्रोत: Agmarknet / data.gov.in\n🌐 agmarknet.gov.in",
                    "en": "\n\n📊 Source: Agmarknet / data.gov.in\n🌐 agmarknet.gov.in",
                }.get(lang, "")
                return intro + body + footer
            else:
                msp_info = ""
                for c in crops[:3]:
                    msp = c.get("msp") or MSP_2024_25.get(c["id"])
                    if msp:
                        msp_info += f"• {c['name']}: MSP ₹{msp}/q (2024-25)\n"
                if not msp_info:
                    msp_info = "• गेहूँ: ₹2,275/q | धान: ₹2,300/q | सरसों: ₹5,650/q\n" if lang == "hi" else "• Wheat: ₹2,275/q | Rice: ₹2,300/q | Mustard: ₹5,650/q\n"
                return {
                    "hi": (f"⚠️ आज का लाइव मंडी भाव उपलब्ध नहीं।\n\n"
                           f"न्यूनतम समर्थन मूल्य (MSP 2024-25):\n{msp_info}\n"
                           f"🌐 agmarknet.gov.in\n📞 1800-270-0224 (eNAM हेल्पलाइन)"),
                    "en": (f"⚠️ Live mandi prices not available today.\n\n"
                           f"Minimum Support Prices (MSP 2024-25):\n{msp_info}\n"
                           f"🌐 agmarknet.gov.in\n📞 1800-270-0224 (eNAM helpline)"),
                }.get(lang, f"Live mandi prices unavailable. MSP: {msp_info}. Check agmarknet.gov.in")

        if intent == INTENT_GOVERNMENT_SCHEME:
            scheme_lines = [l for l in context_block.splitlines() if l.strip().startswith("- ") and "/" in l]
            intro = {
                "hi": f"🏛️ किसानों के लिए सरकारी योजनाएं ({ctx.state or 'भारत'}):\n\n",
                "en": f"🏛️ Government schemes for farmers ({ctx.state or 'India'}):\n\n",
            }.get(lang, "")
            if scheme_lines:
                body = "\n".join(f"• {l.strip().lstrip('- ')}" for l in scheme_lines[:6])
            else:
                body = (
                    "• PM-Kisan — ₹6,000/वर्ष, 3 किस्तों में (pmkisan.gov.in)\n"
                    "• PMFBY — फसल बीमा, प्रीमियम 1.5-2% (pmfby.gov.in)\n"
                    "• KCC — किसान क्रेडिट कार्ड, 4% ब्याज पर ऋण\n"
                    "• PM KUSUM — सौर पंप सब्सिडी 60%\n"
                    "• eNAM — ऑनलाइन मंडी (enam.gov.in)"
                    if lang == "hi" else
                    "• PM-Kisan — ₹6,000/year in 3 installments (pmkisan.gov.in)\n"
                    "• PMFBY — Crop insurance, premium 1.5-2% (pmfby.gov.in)\n"
                    "• KCC — Kisan Credit Card, loan at 4% interest\n"
                    "• PM KUSUM — Solar pump subsidy 60%\n"
                    "• eNAM — Online mandi platform (enam.gov.in)"
                )
            return intro + body

        if intent == INTENT_PEST_DISEASE:
            return {
                "hi": (f"🔬 कीट/रोग प्रबंधन ({loc}):\n\n"
                       f"• पहचान: KrishiRaksha में पत्ते की फोटो अपलोड करें — AI से सटीक निदान\n"
                       f"• IPM (एकीकृत कीट प्रबंधन):\n"
                       f"  - नीम तेल: 5 ml/लीटर पानी में मिलाकर स्प्रे\n"
                       f"  - पीले चिपचिपे ट्रैप (सफेद मक्खी के लिए)\n"
                       f"  - रोगग्रस्त पत्तियां तुरंत हटाएं\n"
                       f"• रासायनिक: ICAR पैकेज के अनुसार\n"
                       f"• मौसम: {temp}°C — उचित समय पर स्प्रे करें\n"
                       f"📞 ICAR: 1800-180-1551"),
                "en": (f"🔬 Pest/Disease Management ({loc}):\n\n"
                       f"• Upload leaf photo in KrishiRaksha for AI diagnosis\n"
                       f"• IPM: Neem oil 5ml/L, yellow sticky traps, remove infected leaves\n"
                       f"• Chemical: Follow ICAR package of practices\n"
                       f"• Weather: {temp}°C — spray at appropriate time\n"
                       f"📞 ICAR helpline: 1800-180-1551"),
            }.get(lang, f"🔬 Pest management — upload photo in KrishiRaksha. Neem oil 5ml/L. ICAR: 1800-180-1551")

        if intent == INTENT_SOIL:
            return {
                "hi": (f"🌱 मिट्टी जांच और स्वास्थ्य ({loc}):\n\n"
                       f"• soilhealth.dac.gov.in पर Soil Health Card देखें\n"
                       f"• उर्वरक सिफारिश (NPK):\n"
                       f"  - गेहूँ: 120:60:40 kg/ha\n"
                       f"  - धान: 100:50:50 kg/ha\n"
                       f"  - सरसों: 80:40:30 kg/ha\n"
                       f"• आदर्श pH: 6.5-7.5\n"
                       f"📞 KVK: 1800-180-1551"),
                "en": (f"🌱 Soil Health & Testing ({loc}):\n\n"
                       f"• Check soilhealth.dac.gov.in for your Soil Health Card\n"
                       f"• NPK recommendation:\n"
                       f"  - Wheat: 120:60:40 kg/ha\n"
                       f"  - Rice: 100:50:50 kg/ha\n"
                       f"  - Mustard: 80:40:30 kg/ha\n"
                       f"• Ideal pH: 6.5-7.5\n"
                       f"📞 KVK: 1800-180-1551"),
            }.get(lang, f"🌱 Soil testing: soilhealth.dac.gov.in | Ideal pH 6.5-7.5")

        if intent == INTENT_FERTILIZER:
            return {
                "hi": (f"💊 उर्वरक उपयोग ({loc}):\n\n"
                       f"• DAP: 100-150 kg/ha बुवाई के समय\n"
                       f"• यूरिया: 2-3 बार बाँटकर (50-50 kg)\n"
                       f"• MOP (पोटाश): 50-60 kg/ha\n"
                       f"• मिट्टी जांच के बाद सटीक सलाह\n"
                       f"• मौसम: {temp}°C\n📞 1800-180-1551"),
                "en": (f"💊 Fertilizer Guidance ({loc}):\n\n"
                       f"• DAP: 100-150 kg/ha at sowing\n"
                       f"• Urea: Split in 2-3 doses (50-50 kg each)\n"
                       f"• MOP: 50-60 kg/ha\n"
                       f"• Get soil tested for precise recommendations\n"
                       f"• Weather: {temp}°C\n📞 1800-180-1551"),
            }.get(lang, f"Fertilizer: DAP 100-150 kg/ha, Urea split doses. 1800-180-1551")

        if intent == INTENT_IRRIGATION:
            return {
                "hi": (f"💧 सिंचाई प्रबंधन ({loc}):\n\n"
                       f"• तापमान: {temp}°C — {farming_advice or 'सामान्य'}\n"
                       f"• ड्रिप सिंचाई: 40-60% पानी बचत (PM KUSUM सब्सिडी)\n"
                       f"• गेहूँ में: 6 सिंचाई — CRI, कल्ले, बाली, दाना भरते समय\n"
                       f"• धान में: 5cm पानी खड़ा रखें\n📞 1800-180-1551"),
                "en": (f"💧 Irrigation Management ({loc}):\n\n"
                       f"• Temp: {temp}°C — {farming_advice or 'Normal'}\n"
                       f"• Drip: 40-60% water savings (PM KUSUM subsidy)\n"
                       f"• Wheat: 6 irrigations — CRI, tillering, ear, grain fill\n"
                       f"• Rice: Keep 5cm standing water\n📞 1800-180-1551"),
            }.get(lang, f"Irrigation: Drip saves 40-60% water. Wheat 6 irrigations. 1800-180-1551")

        # Specific crop info
        if crops:
            crop = crops[0]
            msp = crop.get("msp") or MSP_2024_25.get(crop["id"], 0)
            return {
                "hi": (f"🌾 {crop.get('hindi', crop['name'])} ({crop['name']}) — {loc}:\n\n"
                       f"• MSP 2024-25: ₹{msp:,}/क्विंटल\n"
                       f"• मौसम: {temp}°C — {farming_advice or 'सामान्य'}\n"
                       f"• विस्तृत जानकारी: ICAR या KVK से संपर्क करें\n"
                       f"📞 1800-180-1551"),
                "en": (f"🌾 {crop['name']} — {loc}:\n\n"
                       f"• MSP 2024-25: ₹{msp:,}/quintal\n"
                       f"• Weather: {temp}°C — {farming_advice or 'Normal'}\n"
                       f"• For detailed guidance, contact ICAR or KVK\n"
                       f"📞 1800-180-1551"),
            }.get(lang, f"{crop['name']} MSP: ₹{msp}/q. Weather: {temp}°C. 1800-180-1551")

        # Ultimate general fallback
        return {
            "hi": (f"🌾 KrishiMitra AI — {loc}\n\n"
                   f"🌡️ अभी का मौसम: {temp}°C — {farming_advice or 'सामान्य कृषि कार्य जारी रखें'}\n\n"
                   f"आप इन विषयों पर पूछ सकते हैं:\n"
                   f"• फसल सुझाव — कौन सी फसल उगाऊं?\n"
                   f"• मंडी भाव — गेहूँ/धान का आज का भाव?\n"
                   f"• मौसम — अगले 7 दिन का पूर्वानुमान\n"
                   f"• सरकारी योजनाएं — PM-Kisan, PMFBY\n"
                   f"• कीट/रोग — फसल में क्या लगा है?\n\n"
                   f"📞 किसान कॉल सेंटर: 1800-180-1551"),
            "en": (f"🌾 KrishiMitra AI — {loc}\n\n"
                   f"🌡️ Current weather: {temp}°C — {farming_advice or 'Normal farming conditions'}\n\n"
                   f"You can ask about:\n"
                   f"• Crop recommendations — what to grow this season?\n"
                   f"• Mandi prices — today's wheat/rice prices?\n"
                   f"• Weather — 7-day forecast\n"
                   f"• Govt schemes — PM-Kisan, PMFBY benefits\n"
                   f"• Pest/disease — what's affecting my crop?\n\n"
                   f"📞 Kisan Call Centre: 1800-180-1551"),
        }.get(lang, f"KrishiMitra AI — {loc}. Weather: {temp}°C. Ask about crops, prices, weather, schemes.")

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
            except Exception as exc:
                logger.warning("Crop suggestions error: %s", exc)
                return []

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
                    if not pr.get("is_live"):
                        msp = c.get("msp") or MSP_2024_25.get(c["id"])
                        out.append({
                            "type": "market_price",
                            "crop": c["name"],
                            "msp": msp,
                            "note": "Live mandi price unavailable — configure DATA_GOV_IN_API_KEY",
                        })
                        continue
                    row = (pr.get("top_crops") or [{}])[0]
                    out.append({
                        "type": "market_price",
                        "crop": c["name"],
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
