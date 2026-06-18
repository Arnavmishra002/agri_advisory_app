"""
Realtime weather API.

Endpoints
---------
GET /api/weather/         — current weather + 7-day forecast (via list → current)
GET /api/weather/current/ — same as above

Both hit Open-Meteo (free, no API key) as primary source.
Every response includes:
  fetched_at      — UTC ISO-8601 timestamp of this response
  is_live         — True when fresh from Open-Meteo / OWM
  data_age_minutes — minutes since the weather observation was recorded
"""

import logging
from datetime import datetime, timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..location_utils import attach_location_metadata, resolve_request_location
from ..errors import safe_error_message
from ...services.language_service import normalise_language_code
from ...services.unified_realtime_service import weather_service

logger = logging.getLogger(__name__)


class WeatherViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def _fetch(self, request, force: bool = False):
        ctx  = resolve_request_location(request)
        lang = normalise_language_code(
            request.query_params.get("language", "hi")
        )
        data = weather_service.get_weather(
            ctx.query_label, ctx.latitude, ctx.longitude, lang=lang
        )

        # ── Freshness metadata ─────────────────────────────────────────────
        now_utc = datetime.now(tz=timezone.utc)
        data.setdefault("fetched_at", now_utc.isoformat())

        # Compute data_age_minutes from the observation timestamp if present
        obs_time = (
            (data.get("current") or {}).get("observation_time")
            or data.get("observation_time")
        )
        if obs_time and not data.get("data_age_minutes"):
            try:
                obs_dt = datetime.fromisoformat(str(obs_time).replace("Z", "+00:00"))
                data["data_age_minutes"] = max(
                    0, int((now_utc - obs_dt).total_seconds() / 60)
                )
            except Exception:
                pass

        # If still no age, default to 0 for live or None for non-live
        if "data_age_minutes" not in data:
            data["data_age_minutes"] = 0 if data.get("is_live") else None

        return Response(attach_location_metadata(data, ctx))

    @action(detail=False, methods=["get"])
    def current(self, request):
        """Current weather + 7-day forecast for user's location."""
        try:
            return self._fetch(request)
        except Exception as exc:
            logger.exception("Weather API error: %s", exc)
            return Response(
                {
                    "status": "error",
                    "error": "Unable to fetch weather",
                    "message": safe_error_message(exc, context="weather"),
                    "is_live": False,
                    "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="refresh")
    def refresh(self, request):
        """
        GET /api/weather/refresh/
        Force-bypass the weather cache and fetch fresh data from Open-Meteo.
        Use this when the user explicitly pulls to refresh.
        """
        try:
            ctx  = resolve_request_location(request)
            lang = normalise_language_code(
                request.query_params.get("language", "hi")
            )
            # Invalidate the Django weather_cache for this location
            try:
                from django.core.cache import caches
                cache = caches["weather_cache"]
                key_norm = (ctx.query_label or "").strip().lower().replace(" ", "_")
                cache.delete(f"geocode:{key_norm}")
                cache.delete(f"weather:{key_norm}:{lang}")
            except Exception:
                pass  # cache miss is fine — fresh fetch will repopulate

            data = weather_service.get_weather(
                ctx.query_label, ctx.latitude, ctx.longitude, lang=lang
            )
            now_utc = datetime.now(tz=timezone.utc)
            data["fetched_at"]       = now_utc.isoformat()
            data["cache_invalidated"] = True
            data["data_age_minutes"]  = 0 if data.get("is_live") else None
            return Response(attach_location_metadata(data, ctx))
        except Exception as exc:
            logger.exception("Weather refresh error: %s", exc)
            return Response(
                {"status": "error", "message": safe_error_message(exc, context="weather")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def list(self, request):
        """GET /api/weather/ — alias for current."""
        try:
            return self._fetch(request)
        except Exception as exc:
            logger.exception("Weather list error: %s", exc)
            return Response(
                {
                    "status": "error",
                    "error": "Unable to fetch weather",
                    "message": safe_error_message(exc, context="weather"),
                    "is_live": False,
                    "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
