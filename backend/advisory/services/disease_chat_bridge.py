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
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class DiseaseChatBridge:
    """
    Converts an ML diagnosis result into a full treatment advisory
    by routing through the existing chatbot pipeline.
    """

    def get_treatment_advice(
        self,
        crop: str,
        disease: str,
        confidence: float,
        ctx,                            # LocationContext
        language: str = "hi",
        session_id: Optional[str] = None,
        additional_symptoms: str = "",
        severity: str = "Medium",
    ) -> Dict[str, Any]:
        """
        Generate a complete treatment advisory for an ML-identified disease.

        Args:
            crop:                 Crop name (e.g. "tomato", "wheat")
            disease:              Disease name from ML model (e.g. "Early Blight")
            confidence:           ML confidence 0.0–1.0
            ctx:                  LocationContext (GPS + state)
            language:             Response language code
            session_id:           Optional — persist to farmer memory
            additional_symptoms:  Extra symptom text the farmer described
            severity:             "Low" | "Medium" | "High"

        Returns:
            dict with keys: response, disease, crop, confidence, sources, data_source
        """
        try:
            # Build a structured query that the chatbot will answer well
            query = self._build_query(crop, disease, confidence, additional_symptoms, language)

            # Build synthetic history so the AI understands context
            synthetic_history = self._build_history(crop, disease, severity, language)

            # Load server-side history if session_id given
            if session_id:
                try:
                    from .session_memory_service import session_memory
                    db_history   = session_memory.load_history(session_id, limit=6)
                    synthetic_history = db_history + synthetic_history
                except Exception:
                    pass

            # Route through the main chatbot pipeline
            from .chat_intelligence_service import chat_intelligence_service
            result = chat_intelligence_service.answer(
                query=query,
                ctx=ctx,
                language=language,
                history=synthetic_history,
            )

            # Persist to farmer memory if session given
            if session_id and result.get("response"):
                try:
                    from .session_memory_service import session_memory
                    session_memory.save_turn(
                        session_id=session_id,
                        user_id="anonymous",
                        user_query=query,
                        ai_response=result["response"],
                        intent="pest_disease",
                        language=language,
                        data_source=result.get("data_source", ""),
                        latitude=ctx.latitude,
                        longitude=ctx.longitude,
                    )
                except Exception:
                    pass

            return {
                "response":    result.get("response", ""),
                "disease":     disease,
                "crop":        crop,
                "confidence":  confidence,
                "severity":    severity,
                "sources":     result.get("sources", []),
                "data_source": result.get("data_source", ""),
                "intent":      "pest_disease",
            }

        except Exception as exc:
            logger.error("DiseaseChatBridge.get_treatment_advice failed: %s", exc)
            return {
                "response": (
                    "फसल रोग सलाह के लिए Kisan Helpline: 1800-180-1551 पर कॉल करें।\n"
                    "For crop disease advice, call Kisan Helpline: 1800-180-1551 (Free, 24x7)"
                ),
                "disease":   disease,
                "crop":      crop,
                "confidence": confidence,
                "severity":   severity,
                "sources":   [],
                "data_source": "fallback",
            }

    def _build_query(
        self,
        crop: str,
        disease: str,
        confidence: float,
        symptoms: str,
        lang: str,
    ) -> str:
        """Build the query string that will be sent to the chatbot."""
        conf_pct = round(confidence * 100)

        if lang == "hi":
            base = (
                f"मेरी {crop} फसल में **{disease}** रोग की पहचान हुई है "
                f"(AI confidence: {conf_pct}%)। "
            )
            if symptoms:
                base += f"लक्षण: {symptoms}। "
            base += (
                "कृपया बताएं: (1) यह रोग क्यों होता है? "
                "(2) जैविक उपाय क्या हैं? "
                "(3) रासायनिक दवाई की मात्रा और समय? "
                "(4) भविष्य में कैसे रोकें?"
            )
        else:
            base = (
                f"AI diagnosed **{disease}** on my {crop} crop "
                f"(confidence: {conf_pct}%). "
            )
            if symptoms:
                base += f"Symptoms observed: {symptoms}. "
            base += (
                "Please tell me: (1) Why does this disease occur? "
                "(2) Organic/biopesticide remedies? "
                "(3) Chemical treatment dose and timing (ICAR approved)? "
                "(4) Prevention for next season?"
            )
        return base

    def _build_history(
        self,
        crop: str,
        disease: str,
        severity: str,
        lang: str,
    ) -> list:
        """
        Synthetic history turn that sets crop context for the AI.
        Prevents the AI from asking "which crop?" when the diagnosis is clear.
        """
        if lang == "hi":
            user_turn = f"मेरी फसल {crop} है और मुझे रोग की समस्या है।"
            ai_turn   = (
                f"ठीक है, मैं आपकी {crop} फसल में रोग के बारे में मदद करूँगा। "
                f"KrishiRaksha AI ने {disease} ({severity} severity) की पहचान की है।"
            )
        else:
            user_turn = f"I am growing {crop} and facing a disease problem."
            ai_turn   = (
                f"Understood. I'll help with {crop} disease management. "
                f"KrishiRaksha AI identified {disease} ({severity} severity)."
            )

        return [
            {"role": "user",      "content": user_turn},
            {"role": "assistant", "content": ai_turn, "intent": "pest_disease"},
        ]

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
                "This is a crop/weather advisory fallback, not image classification."
            )
            if treatments:
                response += "\n\nSuggested next steps:\n- " + "\n- ".join(str(t) for t in treatments[:5])
            return {
                "response": response,
                "advice": response,
                "disease": top.get("name", "Advisory fallback"),
                "crop": diagnosis_result.get("crop_detected", "unknown"),
                "confidence": float(top.get("confidence", 0.0)),
                "severity": top.get("severity_label", "Low"),
                "sources": ["KrishiRaksha crop/weather advisory fallback"],
                "data_source": "advisory_fallback",
                "intent": "pest_disease",
                "skipped": False,
            }

        if diagnosis_result.get("status") != "success":
            return {"advice": None, "skipped": True, "reason": "diagnosis not successful"}

        top = (diagnosis_result.get("diagnosis") or [{}])[0]
        return self.get_treatment_advice(
            crop=diagnosis_result.get("crop_detected", "unknown"),
            disease=top.get("name", "Unknown Disease"),
            confidence=float(top.get("confidence", 0.0)),
            ctx=ctx,
            language=language,
            severity=top.get("severity_label", "Medium"),
        )


# Module-level singleton
disease_chat_bridge = DiseaseChatBridge()
