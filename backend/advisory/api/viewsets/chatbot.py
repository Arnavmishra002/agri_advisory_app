"""
KrishiMitra Chatbot API
Multi-turn, context-aware, 22-language agricultural chatbot.
Accepts conversation history for intelligent follow-up handling.
"""

from datetime import datetime
from typing import List, Dict, Any

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..errors import safe_error_message
from ..location_utils import attach_location_metadata, resolve_request_location
from ..validation import MAX_CHAT_QUERY_LENGTH, query_too_long
from ...services.chat_intelligence_service import chat_intelligence_service


class ChatbotViewSet(viewsets.ViewSet):
    """
    Intelligent agricultural chatbot with multi-turn conversation support.

    POST /api/chatbot/
    POST /api/chatbot/query/

    Request body:
    {
      "query": "गेहूँ की बुवाई कब करूँ?",
      "language": "hi",            // or "en", "ta", "te", "mr", "gu", ... "auto"
      "latitude": 28.7041,         // optional GPS (overrides IP geolocation)
      "longitude": 77.1025,
      "history": [                 // optional conversation history for multi-turn
        {"role": "user",      "content": "नमस्ते"},
        {"role": "assistant", "content": "नमस्ते किसान भाई! ..."}
      ]
    }
    """

    permission_classes = [AllowAny]

    def create(self, request):
        return self._handle_query(request)

    @action(detail=False, methods=["post"])
    def query(self, request):
        return self._handle_query(request)

    def _handle_query(self, request):
        query    = (request.data.get("query") or "").strip()
        language = request.data.get("language", "hi")
        ctx      = resolve_request_location(request)

        if not query:
            return Response(
                {"error": "Query required", "hint": "Send {query: 'your question'}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        too_long = query_too_long(query, MAX_CHAT_QUERY_LENGTH, field="query")
        if too_long:
            return too_long

        # Parse conversation history (optional)
        history: List[Dict[str, Any]] = request.data.get("history") or []
        if not isinstance(history, list):
            history = []
        # Sanitise: keep only role + content keys, limit to last 10 turns
        history = [
            {"role": str(h.get("role", "user")), "content": str(h.get("content", ""))}
            for h in history[-10:]
            if isinstance(h, dict) and h.get("content")
        ]

        try:
            result = chat_intelligence_service.answer(
                query, ctx, language=language, history=history
            )
        except Exception as exc:
            return Response(
                {"status": "error", "message": safe_error_message(exc, context="chatbot")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

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
            "timestamp":       result.get("timestamp", datetime.now().isoformat()),
            "context": {
                "intent":         result.get("intent"),
                "crops_detected": result.get("crops_detected", []),
                "language":       result.get("language"),
            },
        }, ctx))
