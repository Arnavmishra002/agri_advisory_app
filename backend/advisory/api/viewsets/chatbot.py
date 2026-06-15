"""
KrishiMitra Chatbot API
Multi-turn, context-aware, 22-language agricultural chatbot.

v2.0 — Server-side farmer memory:
  - ChatSession persists location, language, crop preference across sessions.
  - ChatHistory stores last N turns so farmers don't need to re-send history.
  - Clients MAY still send history in the request; if both are present,
    client-provided history is merged with DB history (client wins on conflict).
v3.0 — ML data collection:
  - Every Q&A logged to FarmerInteractionLog for future fine-tuning.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ...models import FarmerProfile, IoTSensorReading
from ..errors import safe_error_message
from ..location_utils import attach_location_metadata, resolve_request_location
from ..validation import MAX_CHAT_QUERY_LENGTH, query_too_long
from ...services.chat_intelligence_service import chat_intelligence_service, _current_season
from ...services.session_memory_service import session_memory

logger = logging.getLogger(__name__)


def _ai_tier_label(data_source: str) -> str:
    """Map data_source string to a short tier label for analytics."""
    ds = (data_source or "").lower()
    if "gemini" in ds:
        return "gemini"
    if "qwen" in ds or "rag" in ds or "local" in ds:
        return "qwen_rag"
    return "rule_based"


# Bug 2 fix: removed duplicate import block that was here (lines 43-47 in original).


class ChatbotViewSet(viewsets.ViewSet):
    """
    Intelligent agricultural chatbot with multi-turn conversation support
    and server-side farmer memory.

    POST /api/chatbot/
    POST /api/chatbot/query/

    Request body:
    {
      "query": "गेहूँ की बुवाई कब करूँ?",
      "language": "hi",            // or "en", "ta", "te", "mr", "gu", ... "auto"
      "latitude": 28.7041,         // optional GPS (overrides IP geolocation)
      "longitude": 77.1025,
      "session_id": "sess_abc123", // optional — enables server-side memory
      "history": [                 // optional — merged with DB history if session_id given
        {"role": "user",      "content": "नमस्ते"},
        {"role": "assistant", "content": "नमस्ते किसान भाई! ..."}
      ]
    }

    When session_id is provided:
      - Previous conversation is loaded from DB (no need to resend full history).
      - Each new Q→A turn is automatically saved to DB.
      - Farmer profile (location, crop, language) persists across sessions.
    """

    permission_classes = [AllowAny]

    def create(self, request):
        return self._handle_query(request)

    @action(detail=False, methods=["post"])
    def query(self, request):
        return self._handle_query(request)

    def _handle_query(self, request):
        query      = (request.data.get("query") or "").strip()
        language   = request.data.get("language", "hi")
        session_id = (request.data.get("session_id") or "").strip() or None
        # fast_mode=true returns rule-based instantly; LLM runs in background
        fast_mode  = request.data.get("fast_mode", "false").lower() in ("true", "1", "yes")
        ctx        = resolve_request_location(request)

        if not query:
            return Response(
                {"error": "Query required", "hint": "Send {query: 'your question'}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        too_long = query_too_long(query, MAX_CHAT_QUERY_LENGTH, field="query")
        if too_long:
            return too_long

        # ── Build conversation history ─────────────────────────────────────
        # Priority: client-provided history > DB history
        # Merge: if session_id given, load DB history as the base, then
        # overlay anything the client sent (client turns take precedence for
        # the most recent window).
        client_history: List[Dict[str, Any]] = request.data.get("history") or []
        if not isinstance(client_history, list):
            client_history = []

        # Sanitise client history
        clean_client: List[Dict[str, Any]] = []
        for h in client_history[-10:]:
            if not isinstance(h, dict) or not h.get("content"):
                continue
            entry: Dict[str, Any] = {
                "role":    str(h.get("role", "user")),
                "content": str(h.get("content", "")),
            }
            if entry["role"] == "assistant" and h.get("intent"):
                entry["intent"] = str(h["intent"])
            clean_client.append(entry)

        # Load server-side history if session_id provided
        if session_id and not clean_client:
            # Client didn't send history — load from DB
            history = session_memory.load_history(session_id)
        elif session_id and clean_client:
            # Client sent some history — use DB for older turns, client for recent
            db_history   = session_memory.load_history(session_id, limit=10)
            client_fingerprints = {
                (m.get("role", ""), (m.get("content") or "")[:80])
                for m in clean_client
            }
            base_history = [
                m for m in db_history
                if (m.get("role", ""), (m.get("content") or "")[:80])
                not in client_fingerprints
            ]
            history      = (base_history + clean_client)[-10:]
        else:
            history = clean_client

        # ── Load session context for enriching the response ─────────────────
        session_ctx = session_memory.load_session_context(session_id) if session_id else {}

        # ── Load farmer profile context (for personalized advisory) ──────────
        farmer_ctx: dict = {}
        # Bug A fix: strip and None-guard BOTH identifiers before any DB access.
        # An empty string from a mobile client ("session_id": "") must not create
        # an empty Q() that matches every row (DPDP / data-privacy violation).
        phone      = (request.data.get("phone")      or "").strip() or None
        # session_id was already normalised to None above; re-confirm here.
        if phone or session_id:
            try:
                q_filter = Q()
                if phone:      q_filter |= Q(phone_number=phone)
                if session_id: q_filter |= Q(session_id=session_id)
                profile = FarmerProfile.objects.filter(q_filter).first()
                if profile:
                    farmer_ctx = profile.to_context_dict()
                    # Inject into session context so chatbot history carries it
                    if profile.current_crop and not session_ctx.get("last_crop"):
                        session_ctx["last_crop"] = profile.current_crop

                    # Retrieve latest IoT sensor reading for context enrichment
                    try:
                        # IoTSensorReading imported at module top
                        iot_reading = None
                        if profile.session_id:
                            iot_reading = IoTSensorReading.objects.filter(field_id=profile.session_id).order_by("-created_at").first()
                        if not iot_reading and profile.latitude and profile.longitude:
                            iot_reading = (
                                IoTSensorReading.objects
                                .filter(
                                    latitude__gte=profile.latitude - 0.001,
                                    latitude__lte=profile.latitude + 0.001,
                                    longitude__gte=profile.longitude - 0.001,
                                    longitude__lte=profile.longitude + 0.001,
                                )
                                # BUG 7 FIX: explicit ordering so .first() returns
                                # the newest reading, not oldest insert by OID.
                                .order_by("-created_at")
                                .only(
                                    "nitrogen_kg_ha", "phosphorus_kg_ha",
                                    "potassium_kg_ha", "ph", "ec_ds_m",
                                    "moisture_pct", "soil_temp_c", "organic_carbon",
                                )
                                .first()
                            )
                        if iot_reading:
                            farmer_ctx["sensor_reading"] = {
                                "nitrogen_kg_ha": iot_reading.nitrogen_kg_ha,
                                "phosphorus_kg_ha": iot_reading.phosphorus_kg_ha,
                                "potassium_kg_ha": iot_reading.potassium_kg_ha,
                                "ph": iot_reading.ph,
                                "ec_ds_m": iot_reading.ec_ds_m,
                                "moisture_pct": iot_reading.moisture_pct,
                                "soil_temp_c": iot_reading.soil_temp_c,
                                "organic_carbon": iot_reading.organic_carbon,
                            }
                    except Exception as iot_exc:
                        logger.warning("Failed to fetch IoT sensor readings for chatbot context: %s", iot_exc)
            except Exception as profile_exc:
                logger.warning("Failed to load farmer profile context: %s", profile_exc)

        # Language fallback: prefer request > session > default
        if language in ("auto", "") and session_ctx.get("language"):
            language = session_ctx["language"]

        try:
            result = chat_intelligence_service.answer(
                query, ctx, language=language, history=history,
                farmer_profile=farmer_ctx if farmer_ctx else None,
                fast_mode=fast_mode,   # if True: skip LLM, use rule-based instantly
            )
            # Override local location context if chat service extracted a named location
            if result.get("location_context"):
                from ...services.location_context import LocationContext
                ctx = LocationContext(**result["location_context"])
        except Exception as exc:
            return Response(
                {"status": "error", "message": safe_error_message(exc, context="chatbot")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ── Persist this turn + update session context ───────────────────────
        if session_id:
            user = getattr(request, "user", None)
            session_memory.save_turn(
                session_id=session_id,
                user_id=str(user.id) if (user and user.is_authenticated) else "anonymous",
                user_query=query,
                ai_response=result.get("response", ""),
                intent=result.get("intent", "general"),
                language=result.get("language", language),
                data_source=result.get("data_source", ""),
                latitude=ctx.latitude,
                longitude=ctx.longitude,
            )
            context_update: Dict[str, Any] = {
                "language": result.get("language", language),
            }
            if ctx.latitude and ctx.longitude:
                context_update["latitude"]  = ctx.latitude
                context_update["longitude"] = ctx.longitude
                context_update["location"]  = ctx.display_name
            crops = result.get("crops_detected", [])
            if crops:
                context_update["last_crop"] = crops[0]
            session_memory.update_session_context(session_id, context_update)

        # ── Log interaction for ML training dataset (fire-and-forget) ────────
        # Bug 8 fix: result.get("season") is always "" because answer() never
        # puts "season" in its return dict. Call _current_season() directly.
        # Bug 4 fix: use timezone-aware UTC timestamp throughout.
        _now_utc    = datetime.now(tz=timezone.utc)
        _season_now = result.get("season") or _current_season()

        try:
            from ...models import FarmerInteractionLog
            FarmerInteractionLog.objects.create(
                session_id     = session_id or "anon",
                phone_number   = request.data.get("phone", ""),
                location_name  = ctx.display_name,
                state          = ctx.state or "",
                latitude       = ctx.latitude,
                longitude      = ctx.longitude,
                query          = query,
                response       = result.get("response", ""),
                intent         = result.get("intent", ""),
                language       = result.get("language", language),
                crops_detected = result.get("crops_detected", []),
                ai_tier        = _ai_tier_label(result.get("data_source", "")),
                data_source    = result.get("data_source", ""),
                season         = _season_now,   # Bug 8: always populated now
            )
        except Exception as log_exc:
            logger.debug("Interaction log write failed (non-fatal): %s", log_exc)

        return Response(attach_location_metadata({
            "status":          "success",
            "query":           query,
            "response":        result["response"],
            "answer":          result["response"],   # alias for compatibility
            "intent":          result.get("intent"),
            "language":        result.get("language", language),
            "sources":         result.get("sources", []),
            "crops_detected":  result.get("crops_detected", []),
            "crop_suggestions": result.get("crop_suggestions", []),
            "data_source":     result.get("data_source"),
            "timestamp":       _now_utc.isoformat(),  # Bug 4: always UTC-aware
            "session_id":      session_id,
            "context": {
                "intent":         result.get("intent"),
                "crops_detected": result.get("crops_detected", []),
                "language":       result.get("language"),
                "memory_active":  bool(session_id),
            },
        }, ctx))
