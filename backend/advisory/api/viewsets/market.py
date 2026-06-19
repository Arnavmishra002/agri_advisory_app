"""Realtime mandi / market price API."""

import logging
from datetime import datetime, timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..location_utils import attach_location_metadata, resolve_request_location
from ..errors import safe_error_message
from ...services.crop_catalog import crop_catalog
from ...services.unified_realtime_service import market_service

logger = logging.getLogger(__name__)


class MarketPricesViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        """
        Get real-time mandi prices for the user's location.
        Hits Agmarknet 2.0 API → data.gov.in → MSP estimate (labeled).
        """
        try:
            ctx = resolve_request_location(request)
            mandi = request.GET.get("mandi")
            crop  = request.GET.get("crop") or request.GET.get("q")
            norm  = crop_catalog.normalize(crop) if crop else None
            commodity = norm["name"] if norm else crop

            include_estimates = request.GET.get("include_estimates", "").lower() in (
                "1", "true", "yes",
            )

            data = market_service.get_prices(
                ctx.query_label,
                mandi=mandi,
                crop=commodity,
                lat=ctx.latitude,
                lon=ctx.longitude,
                state=ctx.state or None,
                include_estimates=include_estimates,
            )
            if norm:
                data["crop_suggestion"] = norm

            # Always surface data freshness info
            data.setdefault("fetched_at", datetime.now(tz=timezone.utc).isoformat())
            return Response(attach_location_metadata(data, ctx))

        except Exception as exc:
            logger.exception("Market prices API error: %s", exc)
            return Response(
                {
                    "status": "error",
                    "error": "Unable to fetch market prices",
                    "message": safe_error_message(exc, context="market"),
                    "top_crops": [],
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    def mandis(self, request):
        """
        Nearby mandi list sorted by distance from user's GPS.
        Returns the closest mandis first. Use ?radius_km=200 to expand range.
        """
        try:
            ctx = resolve_request_location(request)
            try:
                radius_km = float(request.GET.get("radius_km", 150))
                radius_km = max(10, min(radius_km, 500))   # clamp 10–500 km
            except (ValueError, TypeError):
                radius_km = 150

            data = market_service.list_mandis(
                ctx.query_label,
                lat=ctx.latitude,
                lon=ctx.longitude,
                state=ctx.state or None,
                radius_km=radius_km,
            )
            return Response(attach_location_metadata(data, ctx))
        except Exception as exc:
            logger.exception("Mandi list API error: %s", exc)
            return Response(
                {
                    "status": "error",
                    "error": "Unable to fetch mandi list",
                    "message": safe_error_message(exc, context="market"),
                    "mandis": [],
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="mandi-prices")
    def mandi_prices(self, request):
        """
        Get real-time prices specifically for a single selected mandi.
        Tries Agmarknet 2.0 with mandi filter → data.gov.in filtered →
        MSP seasonal estimate (labeled) as last resort.

        Query params:
          mandi       — mandi name (required)
          state       — state name (optional, improves accuracy)
          crop        — optional commodity filter
          include_estimates — show MSP estimates if no live data (default false)
        """
        try:
            ctx  = resolve_request_location(request)
            mandi = request.GET.get("mandi", "").strip()
            crop  = request.GET.get("crop", "").strip() or None
            include_estimates = request.GET.get("include_estimates", "").lower() in (
                "1", "true", "yes",
            )

            if not mandi:
                return Response(
                    {"status": "error", "message": "mandi parameter is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            norm = crop_catalog.normalize(crop) if crop else None
            commodity = norm["name"] if norm else crop

            # Force mandi-specific fetch — bypass cache to get freshest data
            data = market_service.get_prices(
                ctx.query_label,
                mandi=mandi,
                crop=commodity,
                lat=ctx.latitude,
                lon=ctx.longitude,
                state=ctx.state or None,
                include_estimates=include_estimates,
            )

            # Tag each row with the selected mandi name for frontend clarity
            for row in data.get("top_crops", []):
                row.setdefault("selected_mandi", mandi)
                row.setdefault("mandi_name", row.get("mandi_name") or mandi)

            data["selected_mandi"] = mandi
            data["fetched_at"] = datetime.now(tz=timezone.utc).isoformat()
            data["refresh_interval_seconds"] = 300  # tell frontend when to refresh

            return Response(attach_location_metadata(data, ctx))

        except Exception as exc:
            logger.exception("Mandi-specific prices error: %s", exc)
            return Response(
                {
                    "status": "error",
                    "error": "Unable to fetch mandi prices",
                    "message": safe_error_message(exc, context="market"),
                    "top_crops": [],
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="crop-search")
    def crop_search(self, request):
        """Google-style crop autocomplete for mandi price lookup."""
        query = request.query_params.get("q", "").strip()
        try:
            limit = min(int(request.query_params.get("limit", 10)), 20)
        except (ValueError, TypeError):
            limit = 10
        results = crop_catalog.search(query, limit=limit) if query else crop_catalog.popular(limit)
        return Response({
            "query": query,
            "results": results,
            "total": len(results),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        })

    @action(detail=False, methods=["get"], url_path="live-status")
    def live_status(self, request):
        """
        Check whether live mandi data is available for the user's location.
        Returns the data source status and setup instructions if key is missing.
        """
        try:
            from ...services.data_gov_mandi_client import data_gov_mandi_client
            ctx = resolve_request_location(request)
            has_datagov_key = data_gov_mandi_client.has_valid_api_key()

            probe = data_gov_mandi_client.get_national_prices()
            live_count = len([c for c in probe.get("top_crops", []) if c.get("is_live")])
            active_source = probe.get("data_source_short", probe.get("data_source", ""))

            return Response(attach_location_metadata({
                "status":              "success",
                "is_live":             probe.get("is_live", False),
                "live_rows_available": live_count,
                "active_source":       active_source,
                "data_gov_key_set":    has_datagov_key,
                "source_priority": [
                    {"tier": 1, "name": "data.gov.in OGD API", "active": has_datagov_key},
                    {"tier": 2, "name": "Agmarknet Direct (no key)", "active": not has_datagov_key},
                    {"tier": 3, "name": "Seed/Reference prices", "active": False},
                ],
                "data_source":         probe.get("data_source", ""),
                "setup_instructions": (
                    None if has_datagov_key else
                    "Register free at https://data.gov.in/user/register → "
                    "API Keys → copy key → set DATA_GOV_IN_API_KEY in .env"
                ),
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }, ctx))

        except Exception as exc:
            logger.exception("Live status check error: %s", exc)
            return Response(
                {"status": "error", "message": safe_error_message(exc, context="market")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
