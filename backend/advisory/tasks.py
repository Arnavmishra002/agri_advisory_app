"""
KrishiMitra — Celery background tasks.

When REDIS_URL / CELERY_BROKER_URL is set these tasks run on a dedicated
Celery worker process so the HTTP response is returned to the farmer BEFORE
any of the post-response DB writes finish.

When Redis is absent (local dev / CI) the helper _dispatch_writes() in
chatbot.py calls the underlying functions directly — no Celery required.
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


# ── Existing placeholder ──────────────────────────────────────
@shared_task
def refresh_location_cache():
    """Placeholder for periodic cache refresh."""
    logger.info("refresh_location_cache: no-op (configure Celery to enable)")
    return {"status": "skipped"}


# ── Task 1: persist one Q→A turn + update session context ─────
@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=5,
    ignore_result=True,
)
def persist_turn(
    self,
    session_id: str,
    user_id: str,
    user_query: str,
    ai_response: str,
    intent: str,
    language: str,
    data_source: str,
    latitude,
    longitude,
    context_update: dict,
):
    """
    Async version of session_memory.save_turn() + update_session_context().

    Grouped into one task to avoid two broker round-trips per request.
    Retries up to 2 times on transient DB errors.  Failures are logged at
    WARNING level and never surface to the farmer — the HTTP response was
    already delivered.
    """
    try:
        from .services.session_memory_service import session_memory
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
    except Exception as exc:
        logger.warning(
            "persist_turn task failed (session=%s, attempt=%d): %s",
            session_id, self.request.retries, exc,
        )
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error(
                "persist_turn: max retries exceeded for session %s", session_id
            )


# ── Task 2: write FarmerInteractionLog row ────────────────────
@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=5,
    ignore_result=True,
)
def log_interaction(
    self,
    session_id: str,
    phone_number: str,
    location_name: str,
    state: str,
    latitude,
    longitude,
    query: str,
    response: str,
    intent: str,
    language: str,
    crops_detected: list,
    ai_tier: str,
    data_source: str,
    season: str,
    response_time_ms: int = None,
):
    """
    Async version of FarmerInteractionLog.objects.create().

    All Q&A interactions are still logged — just 50–100 ms later when
    running asynchronously.  Retries up to 2 times on DB errors.
    """
    try:
        from .models import FarmerInteractionLog
        FarmerInteractionLog.objects.create(
            session_id=session_id,
            phone_number=phone_number or "",
            location_name=location_name or "",
            state=state or "",
            latitude=latitude,
            longitude=longitude,
            query=query,
            response=response,
            intent=intent or "",
            language=language or "hi",
            crops_detected=crops_detected or [],
            ai_tier=ai_tier or "",
            data_source=data_source or "",
            season=season or "",
            response_time_ms=response_time_ms,
        )
    except Exception as exc:
        logger.warning(
            "log_interaction task failed (session=%s, attempt=%d): %s",
            session_id, self.request.retries, exc,
        )
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error(
                "log_interaction: max retries exceeded for session %s", session_id
            )
