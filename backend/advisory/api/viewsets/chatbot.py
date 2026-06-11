"""Crop-aware chatbot with NLP routing and official government data grounding."""

from datetime import datetime

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..errors import safe_error_message
from ..location_utils import attach_location_metadata, resolve_request_location
from ..validation import MAX_CHAT_QUERY_LENGTH, query_too_long
from ...services.chat_intelligence_service import chat_intelligence_service


class ChatbotViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def create(self, request):
        return self._handle_query(request)

    @action(detail=False, methods=["post"])
    def query(self, request):
        return self._handle_query(request)

    def _handle_query(self, request):
        query = (request.data.get("query") or "").strip()
        language = request.data.get("language", "hi")
        ctx = resolve_request_location(request)

        if not query:
            return Response({"error": "Query required"}, status=status.HTTP_400_BAD_REQUEST)

        too_long = query_too_long(query, MAX_CHAT_QUERY_LENGTH, field="query")
        if too_long:
            return too_long

        try:
            result = chat_intelligence_service.answer(query, ctx, language=language)
        except Exception as exc:
            return Response(
                {"status": "error", "message": safe_error_message(exc, context="chatbot")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(attach_location_metadata({
            "status": "success",
            "query": query,
            "response": result["response"],
            "answer": result["response"],
            "intent": result.get("intent"),
            "sources": result.get("sources", []),
            "crops_detected": result.get("crops_detected", []),
            "crop_suggestions": result.get("crop_suggestions", []),
            "data_source": result.get("data_source"),
            "timestamp": result.get("timestamp", datetime.now().isoformat()),
            "context": {
                "intent": result.get("intent"),
                "crops_detected": result.get("crops_detected", []),
            },
        }, ctx))
