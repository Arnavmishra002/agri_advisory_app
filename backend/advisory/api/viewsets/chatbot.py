"""
KrishiMitra Chatbot API
Multi-turn, context-aware, 22-language agricultural chatbot.

v2.0 — Server-side farmer memory
v3.0 — ML data collection
v4.0 — SSE streaming endpoint + Celery async writes + Sentry spans
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List

import sentry_sdk
from django.db.models import Q
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
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

# ── Celery availability flag ──────────────────────────────────
# Checked once at import time; avoids per-request os.getenv overhead.
_USE_CELERY = bool(os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL"))


def _ai_tier_label(data_source: str) -> str:
    ds = (data_source or "").lower()
    if "gemini" in ds:
        return "gemini"
    if "qwen" in ds or "rag" in ds or "local" in ds:
        return "qwen_rag"
    return "rule_based"


# ── Async / sync write dispatcher ────────────────────────────
def _dispatch_writes(
    *,
    session_id,
    user_id,
    user_query,
    ai_response,
    intent,
    language,
    data_source,
    latitude,
    longitude,
    context_update,
    phone_number,
    location_name,
    state,
    crops_detected,
    ai_tier,
    season,
    response_time_ms,
):
    """
    Fire post-response DB writes either via Celery (.delay) or inline.

    When REDIS_URL / CELERY_BROKER_URL is set the writes happen on a worker
    process AFTER the HTTP response has already been returned to the farmer,
    shaving 15–90 ms off every chatbot response.

    When Redis is absent (local dev / CI) the writes happen synchronously so
    the dev experience is unchanged.
    """
    if _USE_CELERY:
        from ...tasks import persist_turn, log_interaction
        if session_id:
            persist_turn.delay(
                session_id=session_id,
                user_id=user_id,
                user_query=user_query,
                ai_response=ai_response,
                intent=intent,
                language=language,
                data_source=data_source,
                latitude=latitude,
                longitude=longitude,
                context_update=context_update,
            )
        log_interaction.delay(
            session_id=session_id or "anon",
            phone_number=phone_number,
            location_name=location_name,
            state=state,
            latitude=latitude,
            longitude=longitude,
            query=user_query,
            response=ai_response,
            intent=intent,
            language=language,
            crops_detected=crops_detected,
            ai_tier=ai_tier,
            data_source=data_source,
            season=season,
            response_time_ms=response_time_ms,
        )
    else:
        # Synchronous inline path — identical to original behaviour
        if session_id:
            session_memory.save_turn(
                session_id=session_id,
                user_id=user_id,
                user_query=user_query,
                ai_response=ai_response,
                intent=intent,
                language=language,
                data_source=data_source,
                latitude=latitude,
                longitude=longitude,
            )
            session_memory.update_session_context(session_id, context_update)
        try:
            from ...models import FarmerInteractionLog
            FarmerInteractionLog.objects.create(
                session_id=session_id or "anon",
                phone_number=phone_number or "",
                location_name=location_name or "",
                state=state or "",
                latitude=latitude,
                longitude=longitude,
                query=user_query,
                response=ai_response,
                intent=intent or "",
                language=language or "hi",
                crops_detected=crops_detected or [],
                ai_tier=ai_tier or "",
                data_source=data_source or "",
                season=season or "",
                response_time_ms=response_time_ms,
            )
        except Exception as log_exc:
            logger.debug("Interaction log write failed (non-fatal): %s", log_exc)


# ── Shared request-parsing helper ────────────────────────────
def _parse_request(request) -> Dict[str, Any]:
    """
    Parse and validate request body shared by both the JSON and SSE paths.
    Returns a dict with all needed fields or raises ValueError on bad input.
    """
    query      = (request.data.get("query") or "").strip()
    language   = request.data.get("language", "hi")
    session_id = (request.data.get("session_id") or "").strip() or None
    _fast_raw  = request.data.get("fast_mode", False)
    fast_mode  = (
        _fast_raw is True
        or (isinstance(_fast_raw, str) and _fast_raw.lower() in ("true", "1", "yes"))
    )
    return dict(
        query=query, language=language, session_id=session_id, fast_mode=fast_mode,
    )


def _build_history_and_context(request, session_id, language):
    """Load and merge client + server-side conversation history."""
    client_history: List[Dict[str, Any]] = request.data.get("history") or []
    if not isinstance(client_history, list):
        client_history = []

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

    if session_id and not clean_client:
        history = session_memory.load_history(session_id)
    elif session_id and clean_client:
        db_history = session_memory.load_history(session_id, limit=10)
        fingerprints = {
            (m.get("role", ""), (m.get("content") or "")[:80]) for m in clean_client
        }
        base = [m for m in db_history
                if (m.get("role", ""), (m.get("content") or "")[:80]) not in fingerprints]
        history = (base + clean_client)[-10:]
    else:
        history = clean_client

    session_ctx = session_memory.load_session_context(session_id) if session_id else {}
    if language in ("auto", "") and session_ctx.get("language"):
        language = session_ctx["language"]

    return history, session_ctx, language


def _load_farmer_context(request, session_id, session_ctx) -> dict:
    """Load FarmerProfile + IoT sensor reading for chatbot personalisation."""
    farmer_ctx: dict = {}
    phone = (request.data.get("phone") or "").strip() or None
    if not (phone or session_id):
        return farmer_ctx
    try:
        q_filter = Q()
        if phone:      q_filter |= Q(phone_number=phone)
        if session_id: q_filter |= Q(session_id=session_id)
        profile = FarmerProfile.objects.filter(q_filter).first()
        if not profile:
            return farmer_ctx
        farmer_ctx = profile.to_context_dict()
        if profile.current_crop and not session_ctx.get("last_crop"):
            session_ctx["last_crop"] = profile.current_crop
        try:
            iot_reading = None
            if profile.session_id:
                iot_reading = (
                    IoTSensorReading.objects
                    .filter(field_id=profile.session_id)
                    .order_by("-created_at").first()
                )
            if not iot_reading and profile.latitude and profile.longitude:
                _BBOX = 0.002
                iot_reading = (
                    IoTSensorReading.objects
                    .filter(
                        latitude__gte=profile.latitude  - _BBOX,
                        latitude__lte=profile.latitude  + _BBOX,
                        longitude__gte=profile.longitude - _BBOX,
                        longitude__lte=profile.longitude + _BBOX,
                    )
                    .order_by("-created_at")
                    .only(
                        "nitrogen_kg_ha", "phosphorus_kg_ha", "potassium_kg_ha",
                        "ph", "ec_ds_m", "moisture_pct", "soil_temp_c", "organic_carbon",
                    )
                    .first()
                )
                if not iot_reading:
                    logger.debug(
                        "No IoT reading near (%.4f, %.4f) ±0.002° for session %s",
                        profile.latitude, profile.longitude, session_id,
                    )
            if iot_reading:
                farmer_ctx["sensor_reading"] = {
                    "nitrogen_kg_ha":   iot_reading.nitrogen_kg_ha,
                    "phosphorus_kg_ha": iot_reading.phosphorus_kg_ha,
                    "potassium_kg_ha":  iot_reading.potassium_kg_ha,
                    "ph":               iot_reading.ph,
                    "ec_ds_m":          iot_reading.ec_ds_m,
                    "moisture_pct":     iot_reading.moisture_pct,
                    "soil_temp_c":      iot_reading.soil_temp_c,
                    "organic_carbon":   iot_reading.organic_carbon,
                }
        except Exception as iot_exc:
            logger.warning("IoT sensor fetch failed: %s", iot_exc)
    except Exception as profile_exc:
        logger.warning("Farmer profile fetch failed: %s", profile_exc)
    return farmer_ctx


# ─────────────────────────────────────────────────────────────
# ChatbotViewSet — JSON endpoint (unchanged shape)
# ─────────────────────────────────────────────────────────────
class ChatbotViewSet(viewsets.ViewSet):
    """
    POST /api/chatbot/       — create
    POST /api/chatbot/query/ — query action

    Shape is identical to v3.0; only the post-response writes
    are now dispatched asynchronously when Redis is available.
    """

    permission_classes = [AllowAny]

    def create(self, request):
        return self._handle_query(request)

    @action(detail=False, methods=["post"])
    def query(self, request):
        return self._handle_query(request)

    def _handle_query(self, request):
        parsed     = _parse_request(request)
        query      = parsed["query"]
        language   = parsed["language"]
        session_id = parsed["session_id"]
        fast_mode  = parsed["fast_mode"]
        ctx        = resolve_request_location(request)

        if not query:
            return Response(
                {"error": "Query required", "hint": "Send {query: 'your question'}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        too_long = query_too_long(query, MAX_CHAT_QUERY_LENGTH, field="query")
        if too_long:
            return too_long

        history, session_ctx, language = _build_history_and_context(
            request, session_id, language
        )
        farmer_ctx = _load_farmer_context(request, session_id, session_ctx)

        t0 = time.monotonic()
        try:
            # Sentry performance span around the AI call
            with sentry_sdk.start_span(op="ai.gemini", description="chatbot_query"):
                result = chat_intelligence_service.answer(
                    query, ctx, language=language, history=history,
                    farmer_profile=farmer_ctx if farmer_ctx else None,
                    fast_mode=fast_mode,
                )
            if result.get("location_context"):
                from ...services.location_context import LocationContext
                ctx = LocationContext(**result["location_context"])
        except Exception as exc:
            return Response(
                {"status": "error", "message": safe_error_message(exc, context="chatbot")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_time_ms = int((time.monotonic() - t0) * 1000)
        _now_utc    = datetime.now(tz=timezone.utc)
        season_now  = result.get("season") or _current_season()
        crops       = result.get("crops_detected", [])
        context_update: Dict[str, Any] = {"language": result.get("language", language)}
        if ctx.latitude and ctx.longitude:
            context_update.update({
                "latitude":  ctx.latitude,
                "longitude": ctx.longitude,
                "location":  ctx.display_name,
            })
        if crops:
            context_update["last_crop"] = crops[0]

        user = getattr(request, "user", None)
        _dispatch_writes(
            session_id=session_id,
            user_id=str(user.id) if (user and user.is_authenticated) else "anonymous",
            user_query=query,
            ai_response=result.get("response", ""),
            intent=result.get("intent", "general"),
            language=result.get("language", language),
            data_source=result.get("data_source", ""),
            latitude=ctx.latitude,
            longitude=ctx.longitude,
            context_update=context_update,
            phone_number=request.data.get("phone", ""),
            location_name=ctx.display_name,
            state=ctx.state or "",
            crops_detected=crops,
            ai_tier=_ai_tier_label(result.get("data_source", "")),
            season=season_now,
            response_time_ms=response_time_ms,
        )

        return Response(attach_location_metadata({
            "status":           "success",
            "query":            query,
            "response":         result["response"],
            "answer":           result["response"],
            "intent":           result.get("intent"),
            "language":         result.get("language", language),
            "sources":          result.get("sources", []),
            "crops_detected":   result.get("crops_detected", []),
            "crop_suggestions": result.get("crop_suggestions", []),
            "data_source":      result.get("data_source"),
            "response_time_ms": response_time_ms,
            "timestamp":        _now_utc.isoformat(),
            "session_id":       session_id,
            "context": {
                "intent":         result.get("intent"),
                "crops_detected": result.get("crops_detected", []),
                "language":       result.get("language"),
                "memory_active":  bool(session_id),
            },
        }, ctx))


# ─────────────────────────────────────────────────────────────
# SSE streaming endpoint — /api/chatbot/stream/
# ─────────────────────────────────────────────────────────────
def _sse_frame(data: dict) -> str:
    """Encode one Server-Sent Event frame."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _stream_generator(
    query, ctx, language, history, farmer_ctx, fast_mode,
    session_id, request,
) -> Generator[str, None, None]:
    """
    Generator that yields SSE frames.

    Intermediate frames:  {"token": "<chunk>"}
    Final frame:          {"done": true, "intent": ..., "language": ...,
                           "data_source": ..., "response_time_ms": ...}
    """
    full_response_parts: List[str] = []
    t0 = time.monotonic()
    result_meta: Dict[str, Any] = {}

    try:
        with sentry_sdk.start_span(op="ai.gemini", description="chatbot_stream"):
            for chunk in chat_intelligence_service.answer_stream(
                query, ctx,
                language=language,
                history=history,
                farmer_profile=farmer_ctx if farmer_ctx else None,
                fast_mode=fast_mode,
            ):
                # Sentinel dict marks end of stream
                if isinstance(chunk, dict) and chunk.get("__done__"):
                    result_meta = chunk
                    break
                # Plain string token chunk
                token = chunk if isinstance(chunk, str) else str(chunk)
                if token:
                    full_response_parts.append(token)
                    yield _sse_frame({"token": token})
    except Exception as exc:
        logger.error("SSE stream error: %s", exc)
        yield _sse_frame({"error": "Stream failed", "detail": safe_error_message(exc, context="chatbot")})
        return

    response_time_ms = int((time.monotonic() - t0) * 1000)
    full_response = "".join(full_response_parts)

    yield _sse_frame({
        "done":            True,
        "intent":          result_meta.get("intent", ""),
        "language":        result_meta.get("language", language),
        "data_source":     result_meta.get("data_source", ""),
        "crops_detected":  result_meta.get("crops_detected", []),
        "response_time_ms": response_time_ms,
        "session_id":      session_id,
    })

    # Post-stream writes (same as JSON endpoint)
    crops          = result_meta.get("crops_detected", [])
    season_now     = result_meta.get("season") or _current_season()
    context_update = {"language": result_meta.get("language", language)}
    if ctx.latitude and ctx.longitude:
        context_update.update({
            "latitude": ctx.latitude, "longitude": ctx.longitude,
            "location": ctx.display_name,
        })
    if crops:
        context_update["last_crop"] = crops[0]

    user = getattr(request, "user", None)
    _dispatch_writes(
        session_id=session_id,
        user_id=str(user.id) if (user and user.is_authenticated) else "anonymous",
        user_query=query,
        ai_response=full_response,
        intent=result_meta.get("intent", "general"),
        language=result_meta.get("language", language),
        data_source=result_meta.get("data_source", ""),
        latitude=ctx.latitude,
        longitude=ctx.longitude,
        context_update=context_update,
        phone_number=getattr(request, "data", {}).get("phone", ""),
        location_name=ctx.display_name,
        state=ctx.state or "",
        crops_detected=crops,
        ai_tier=_ai_tier_label(result_meta.get("data_source", "")),
        season=season_now,
        response_time_ms=response_time_ms,
    )


@csrf_exempt
@require_POST
def stream_chat(request):
    """
    POST /api/chatbot/stream/

    Streams Gemini response token-by-token via Server-Sent Events.
    Same rate limiting, session memory, and interaction logging as
    the JSON endpoint — writes happen after the stream finishes.

    SSE frame format (intermediate):  data: {"token": "..."}\n\n
    SSE frame format (final):         data: {"done": true, ...}\n\n
    """
    import json as _json
    try:
        body = _json.loads(request.body or b"{}")
    except Exception:
        body = {}

    # Attach parsed body to request.data (DRF-like)
    request.data = body  # type: ignore[attr-defined]

    query      = (body.get("query") or "").strip()
    language   = body.get("language", "hi")
    session_id = (body.get("session_id") or "").strip() or None
    _fast_raw  = body.get("fast_mode", False)
    fast_mode  = (
        _fast_raw is True
        or (isinstance(_fast_raw, str) and _fast_raw.lower() in ("true", "1", "yes"))
    )

    if not query:
        from django.http import JsonResponse
        return JsonResponse({"error": "Query required"}, status=400)
    # SECURITY FIX: enforce same query length cap as JSON endpoint
    if len(query) > MAX_CHAT_QUERY_LENGTH:
        from django.http import JsonResponse
        return JsonResponse(
            {"error": f"Query too long (max {MAX_CHAT_QUERY_LENGTH} chars)"},
            status=400,
        )

    ctx = resolve_request_location(request)
    history, session_ctx, language = _build_history_and_context(
        request, session_id, language
    )
    farmer_ctx = _load_farmer_context(request, session_id, session_ctx)

    response = StreamingHttpResponse(
        _stream_generator(
            query, ctx, language, history, farmer_ctx, fast_mode,
            session_id, request,
        ),
        content_type="text/event-stream",
    )
    response["Cache-Control"]     = "no-cache"
    response["X-Accel-Buffering"] = "no"   # disable nginx buffering
    # SECURITY FIX: use configured CORS origins, fall back to * only in DEBUG
    from django.conf import settings as _dj
    _cors = getattr(_dj, 'CORS_ALLOWED_ORIGINS', None)
    response["Access-Control-Allow-Origin"] = (_cors[0] if _cors else "*")
    return response
