"""
KrishiMitra Session Memory Service
===================================
Persists and loads per-farmer conversation context using the existing
ChatSession and ChatHistory models.

The chatbot was previously entirely stateless — the client was responsible
for sending the full history back on every request. This service adds
server-side memory so:
  1. Farmers can switch devices without losing context.
  2. The AI can reference "last week I told you wheat moisture was 28%".
  3. Crop, location, language preferences survive across sessions.

Architecture:
  - ChatSession stores the farmer's profile and last-seen context (JSON).
  - ChatHistory stores the last N turns for the active session.
  - Both are read/written by the chatbot viewset, not the service.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Maximum history turns to keep in DB per session
MAX_HISTORY_TURNS = 20
# Maximum turns to return to the chatbot on each request (keeps prompts small)
HISTORY_WINDOW    = 10


class SessionMemoryService:
    """Read and write farmer conversation memory to the Django ORM."""

    # ── Load ──────────────────────────────────────────────────────────────────

    def load_history(
        self,
        session_id: str,
        limit: int = HISTORY_WINDOW,
    ) -> List[Dict[str, Any]]:
        """
        Return the last `limit` chat turns for this session as a list of
        {role, content, intent?} dicts compatible with chat_intelligence_service.answer().
        Returns [] if no history or model is unavailable.
        """
        try:
            from ..models import ChatHistory
            rows = (
                ChatHistory.objects
                .filter(session_id=session_id)
                .order_by("-created_at")[:limit]
            )
            turns = []
            for row in reversed(list(rows)):  # oldest first
                entry: Dict[str, Any] = {
                    "role":    "user" if row.message_type == "user" else "assistant",
                    "content": row.message_content,
                }
                # Re-attach intent metadata stored in response_type field
                if row.message_type == "assistant" and row.response_type:
                    entry["intent"] = row.response_type
                turns.append(entry)
            return turns
        except Exception as exc:
            logger.warning("SessionMemory.load_history failed: %s", exc)
            return []

    def load_session_context(self, session_id: str) -> Dict[str, Any]:
        """
        Return the persisted farmer profile for this session:
          {location, crop, language, lat, lon, sensor_context}
        Returns {} if no session or model unavailable.
        """
        try:
            from ..models import ChatSession
            sess = ChatSession.objects.filter(session_id=session_id).first()
            if sess:
                return sess.conversation_context or {}
        except Exception as exc:
            logger.warning("SessionMemory.load_session_context failed: %s", exc)
        return {}

    # ── Save ──────────────────────────────────────────────────────────────────

    def save_turn(
        self,
        session_id: str,
        user_id: str,
        user_query: str,
        ai_response: str,
        intent: str,
        language: str,
        data_source: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> None:
        """
        Persist one full Q→A turn (2 ChatHistory rows) and update
        ChatSession stats + last-seen context.
        Fails silently — never blocks the API response.
        """
        try:
            from ..models import ChatHistory, ChatSession
            now = datetime.now()

            # Save user message
            ChatHistory.objects.create(
                user_id=user_id,         # actual farmer identifier (phone / anonymous / session)
                session_id=session_id,
                message_type="user",
                message_content=user_query,
                detected_language=language,
                response_language=language,
                response_source=data_source or "",
                response_type=intent or "",
                has_location=bool(latitude and longitude),
                latitude=latitude,
                longitude=longitude,
            )

            # Save assistant response
            ChatHistory.objects.create(
                user_id=user_id,         # same actual farmer identifier
                session_id=session_id,
                message_type="assistant",
                message_content=ai_response,
                detected_language=language,
                response_language=language,
                response_source=data_source or "",
                response_type=intent or "",   # ← allows follow-up intent resolution
                has_location=bool(latitude and longitude),
                latitude=latitude,
                longitude=longitude,
            )

            # Update or create session record
            ChatSession.objects.update_or_create(
                session_id=session_id,
                defaults={
                    "preferred_language":  language,
                    "latitude":            latitude,
                    "longitude":           longitude,
                    "is_active":           True,
                },
            )

            # Trim old history beyond MAX_HISTORY_TURNS to keep DB lean
            old_ids = list(
                ChatHistory.objects
                .filter(session_id=session_id)
                .order_by("-created_at")
                .values_list("id", flat=True)[MAX_HISTORY_TURNS:]
            )
            if old_ids:
                ChatHistory.objects.filter(id__in=old_ids).delete()

        except Exception as exc:
            logger.warning("SessionMemory.save_turn failed (non-fatal): %s", exc)

    def update_session_context(
        self,
        session_id: str,
        context: Dict[str, Any],
    ) -> None:
        """
        Merge `context` dict into ChatSession.conversation_context.
        Use this to persist: current crop, location, sensor readings, preferences.
        """
        try:
            from ..models import ChatSession
            sess, _ = ChatSession.objects.get_or_create(
                session_id=session_id,
                defaults={"user_id": session_id},
            )
            existing = sess.conversation_context or {}
            existing.update(context)
            sess.conversation_context = existing
            # Do NOT include last_activity in update_fields — it is auto_now=True
            # and Django silently ignores auto_now fields in update_fields lists.
            # A plain .save() triggers auto_now correctly.
            sess.save(update_fields=["conversation_context"])
        except Exception as exc:
            logger.warning("SessionMemory.update_session_context failed: %s", exc)


# Module-level singleton
session_memory = SessionMemoryService()
