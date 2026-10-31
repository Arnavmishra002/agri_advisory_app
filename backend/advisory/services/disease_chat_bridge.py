"""
KrishiMitra Disease→Chat Bridge
================================
Connects the EfficientNet-B3 crop disease ML model to the AI chatbot.

Flow:
  Farmer uploads photo → ML predicts disease → bridge builds rich context
  → context fed into chat_intelligence_service.answer() → complete advisory

This is the "AI plant doctor" feature:
  1. Disease is identified (crop + disease name + confidence)
  2. RAG retrieves ICAR treatment protocol for that disease
  3. Weather constraint check (don't spray before rain)
  4. Qwen/Gemini generates step-by-step treatment plan
  5. Response includes: disease name, severity, organic first-line, chemical
     backup (dose from ICAR), prevention, helpline

Usage (from DiagnosticViewSet or standalone):
    from .disease_chat_bridge import disease_chat_bridge
    advice = disease_chat_bridge.get_treatment_advice(
        crop="tomato",
        disease="Early Blight",
        confidence=0.87,
        ctx=location_context,
        language="hi",
        session_id="sess_abc",
    )
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _template_language(language: str) -> str:
    lang = (language or "hi").lower()
    if lang in ("hinglish", "hi-latn"):
        return "hinglish"
    return "hi" if lang == "hi" else "en"


def _spray_window(ctx) -> str:
    """'blocked', 'clear' or 'unknown' from the live 48-hour forecast.

    Spraying is blocked when more than 20 mm of rain or a rain probability
    above 70% is forecast for today or tomorrow. A missing forecast is
    reported as unknown, never as clear.
    """
    lat, lon = getattr(ctx, "latitude", None), getattr(ctx, "longitude", None)
    if lat is None or lon is None:
        return "unknown"
    try:
        from .unified_realtime_service import weather_service
        weather = weather_service.get_weather(getattr(ctx, "display_name", "") or "", lat=lat, lon=lon)
    except Exception:
        logger.warning("Weather lookup for the spray window failed", exc_info=True)
        return "unknown"
    forecast = (weather or {}).get("forecast_7day") or []
    if not (weather or {}).get("is_live") or len(forecast) < 2:
        return "unknown"
    for day in forecast[:2]:
        if (day.get("rainfall_mm") or 0) > 20 or (day.get("rain_probability") or 0) > 70:
            return "blocked"
    return "clear"



_TEMPLATES = {
    "en": {
        "diagnosis": "Diagnosis: {disease} on {crop} (model confidence {pct}%).",
        "alternatives": "Other possibilities: {items}.",
        "steps": "What to do next:",
        "inspect": "1. Check several plants in different parts of the field for the same symptoms.",
        "confirm": "2. Confirm the diagnosis with your nearest Krishi Vigyan Kendra (KVK) or agriculture officer before buying or spraying anything.",
        "blocked": "3. Do not spray now: more than 20 mm of rain or a rain chance above 70% is forecast within 48 hours.",
        "clear": "3. No heavy rain is forecast for the next 48 hours, so conditions suit a spray if the KVK recommends one.",
        "unknown": "3. The forecast could not be checked. Do not spray if heavy rain is expected within 48 hours.",
        "dose": "4. Use only the product and dose the KVK recommends or the registered product label states.",
        "helpline": "Kisan Call Centre: 1800-180-1551 (free).",
        "note": "This is an AI result from a photo, not a laboratory test.",
    },
    "hi": {
        "diagnosis": "पहचान: {crop} में {disease} (मॉडल का भरोसा {pct}%)।",
        "alternatives": "दूसरी संभावनाएँ: {items}।",
        "steps": "अब क्या करें:",
        "inspect": "1. खेत के अलग-अलग हिस्सों में कई पौधे देखें कि उनमें भी यही लक्षण हैं या नहीं।",
        "confirm": "2. कोई दवा खरीदने या छिड़कने से पहले नज़दीकी कृषि विज्ञान केंद्र (KVK) या कृषि अधिकारी से पहचान की पुष्टि करें।",
        "blocked": "3. अभी छिड़काव न करें: अगले 48 घंटों में 20 मिमी से अधिक बारिश या 70% से अधिक बारिश की संभावना है।",
        "clear": "3. अगले 48 घंटों में भारी बारिश का अनुमान नहीं है, इसलिए KVK सलाह दे तो छिड़काव का मौसम ठीक है।",
        "unknown": "3. मौसम का पूर्वानुमान जाँचा नहीं जा सका। 48 घंटों में भारी बारिश की संभावना हो तो छिड़काव न करें।",
        "dose": "4. केवल वही दवा और मात्रा इस्तेमाल करें जो KVK बताए या पंजीकृत दवा के लेबल पर लिखी हो।",
        "helpline": "किसान कॉल सेंटर: 1800-180-1551 (निःशुल्क)।",
        "note": "यह फोटो से AI का परिणाम है, प्रयोगशाला जाँच नहीं।",
    },
    "hinglish": {
        "diagnosis": "Pehchaan: {crop} mein {disease} (model ka bharosa {pct}%).",
        "alternatives": "Doosri sambhavnayein: {items}.",
        "steps": "Ab kya karein:",
        "inspect": "1. Khet ke alag-alag hisson mein kai paudhe dekhein ki unmein bhi yahi lakshan hain ya nahi.",
        "confirm": "2. Koi dawa khareedne ya chhidakne se pehle nazdeeki KVK ya krishi adhikari se pehchaan confirm karein.",
        "blocked": "3. Abhi spray na karein: agle 48 ghante mein 20 mm se zyada baarish ya 70% se zyada baarish ki sambhavna hai.",
        "clear": "3. Agle 48 ghante mein bhaari baarish ka anumaan nahi hai, isliye KVK salah de to spray ka mausam theek hai.",
        "unknown": "3. Mausam ka forecast check nahi ho saka. 48 ghante mein bhaari baarish ho sakti ho to spray na karein.",
        "dose": "4. Sirf wahi dawa aur maatra use karein jo KVK bataye ya registered dawa ke label par likhi ho.",
        "helpline": "Kisan Call Centre: 1800-180-1551 (free).",
        "note": "Yeh photo se AI ka result hai, lab test nahi.",
    },
}


class DiseaseChatBridge:
    """
    Turns a released ML diagnosis into a fixed, reviewed advisory.

    The advisory is rendered from a template rather than generated: it names
    the diagnosis and the model's confidence, lists plausible alternatives,
    asks the farmer to inspect more plants and confirm with the KVK, reports
    the spray window from the live forecast and gives the helpline. It never
    states a product dose, because the guidance base has not been reviewed by
    an agronomist.
    """

    def get_treatment_advice(
        self,
        crop: str,
        disease: str,
        confidence: float,
        ctx,                            # LocationContext or None
        language: str = "hi",
        session_id: Optional[str] = None,
        severity: str = "Medium",
        alternatives: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        lang = _template_language(language)
        text = _TEMPLATES[lang]
        spray = _spray_window(ctx)
        lines = [text["diagnosis"].format(disease=disease, crop=crop, pct=round(confidence * 100))]
        others = [
            f"{a.get('disease_name') or a.get('label')} ({round(float(a.get('probability', 0)) * 100)}%)"
            for a in (alternatives or [])
            if float(a.get("probability", 0)) >= 0.05
        ]
        if others:
            lines.append(text["alternatives"].format(items=", ".join(others)))
        lines += ["", text["steps"], text["inspect"], text["confirm"], text[spray], text["dose"], "",
                  text["helpline"], text["note"]]
        response = "\n".join(lines)

        if session_id:
            try:
                from .session_memory_service import session_memory
                session_memory.save_turn(
                    session_id=session_id,
                    user_id="anonymous",
                    user_query=f"Leaf photo diagnosis: {crop}",
                    ai_response=response,
                    intent="pest_disease",
                    language=language,
                    data_source="KrishiRaksha diagnosis template",
                    latitude=getattr(ctx, "latitude", None),
                    longitude=getattr(ctx, "longitude", None),
                )
            except Exception:
                logger.debug("Could not save the diagnosis turn", exc_info=True)

        return {
            "response":     response,
            "disease":      disease,
            "crop":         crop,
            "confidence":   confidence,
            "severity":     severity,
            "spray_window": spray,
            "sources":      ["KrishiRaksha EfficientNet-B3 (gated)", "Live weather forecast"],
            "data_source":  "KrishiRaksha diagnosis template",
            "intent":       "pest_disease",
        }

    def format_for_api(self, diagnosis_result: Dict[str, Any], ctx, language: str = "hi") -> Dict[str, Any]:
        """
        Convenience wrapper: takes the raw ML diagnosis dict and returns
        the full treatment advisory. Use this in DiagnosticViewSet.

        Args:
            diagnosis_result: dict from KrishiRakshaPestService.diagnose_crop()
            ctx:              LocationContext
            language:         Farmer's language
        """
        if diagnosis_result.get("status") == "advisory_fallback":
            top = (diagnosis_result.get("diagnosis") or [{}])[0]
            treatments = top.get("treatment") or []
            response = (
                "Image received, but the trained leaf-disease ML model is not installed. "
                "This is a safety advisory fallback, not image classification."
            )
            if treatments:
                response += "\n\nSuggested next steps:\n- " + "\n- ".join(str(t) for t in treatments[:5])
            return {
                "response": response,
                "advice": response,
                "disease": "Disease model unavailable",
                "crop": diagnosis_result.get("crop_detected", "unknown"),
                "confidence": 0.0,
                "severity": "Unknown",
                "sources": ["KrishiRaksha safety advisory fallback"],
                "data_source": "advisory_fallback",
                "intent": "pest_disease",
                "skipped": False,
            }

        if diagnosis_result.get("status") != "success":
            return {"advice": None, "skipped": True, "reason": "diagnosis not successful"}

        top = (diagnosis_result.get("diagnosis") or [{}])[0]
        released = top.get("name", "Unknown Disease")
        alternatives = [
            p for p in (top.get("top_predictions") or [])
            if p.get("disease_name") != released
        ]
        return self.get_treatment_advice(
            crop=diagnosis_result.get("crop_detected", "unknown"),
            disease=released,
            confidence=float(top.get("confidence", 0.0)),
            ctx=ctx,
            language=language,
            severity=top.get("severity_label", "Medium"),
            alternatives=alternatives,
        )


# Module-level singleton
disease_chat_bridge = DiseaseChatBridge()
