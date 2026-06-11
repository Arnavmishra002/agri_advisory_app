"""Realtime weather API."""

import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..location_utils import attach_location_metadata, resolve_request_location
from ...services.language_service import normalise_language_code
from ...services.unified_realtime_service import weather_service

logger = logging.getLogger(__name__)


class WeatherViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=["get"])
    def current(self, request):
        try:
            ctx = resolve_request_location(request)
            lang = normalise_language_code(
                request.query_params.get("language", "hi")
            )
            data = weather_service.get_weather(
                ctx.query_label, ctx.latitude, ctx.longitude, lang=lang
            )
            return Response(attach_location_metadata(data, ctx))
        except Exception as exc:
            logger.exception("Weather API error: %s", exc)
            return Response(
                {
                    "status": "error",
                    "error": "Unable to fetch weather",
                    "message": str(exc),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def list(self, request):
        return self.current(request)
