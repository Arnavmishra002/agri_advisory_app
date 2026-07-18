import logging
from datetime import datetime, timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

logger = logging.getLogger(__name__)

from ..location_utils import (
    attach_location_metadata,
    require_confirmed_location,
    resolve_request_location,
)
from ..errors import safe_error_message
from ...services.crop_catalog import crop_catalog
from ...services.crop_recommendation_engine import crop_recommendation_engine
from ...services.unified_realtime_service import market_service
from ..serializers import CropRecommendationQuerySerializer, LocationQuerySerializer

class CropAdvisoryViewSet(viewsets.ViewSet):
    """Crop advisory — multi-factor scoring with live weather + mandi data."""

    def list(self, request):
        try:
            serializer = CropRecommendationQuerySerializer(data=request.query_params)
            if not serializer.is_valid():
                return Response({"error": "Invalid crop query", "errors": serializer.errors}, status=400)
            params = serializer.validated_data
            ctx = resolve_request_location(request)
            location_error = require_confirmed_location(ctx, service="crop_recommendation")
            if location_error:
                return location_error
            language = params.get("language", "hi")

            logger.info(
                "Crop recommendations (intelligent engine) for %s @ %s,%s",
                ctx.query_label, ctx.latitude, ctx.longitude,
            )

            recommendations = crop_recommendation_engine.recommend_from_context(
                ctx,
                language=language,
                agronomic_inputs=serializer.recommendation_inputs,
            )

            return Response(
                attach_location_metadata(recommendations, ctx),
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Crop advisory error: {e}")
            return Response({
                "error": "Unable to fetch crop recommendations",
                "message": safe_error_message(e, context="crop"),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TrendingCropsViewSet(viewsets.ViewSet):
    """Trending Crops Service - Uses Government APIs for Real-Time Accurate Data"""

    def list(self, request):
        """Get trending crops using government APIs"""
        try:
            serializer = CropRecommendationQuerySerializer(data=request.query_params)
            if not serializer.is_valid():
                return Response({"error": "Invalid trending crop query", "errors": serializer.errors}, status=400)
            params = serializer.validated_data
            ctx = resolve_request_location(request)
            location_error = require_confirmed_location(ctx, service="trending_crops")
            if location_error:
                return location_error
            language = params.get("language", "hi")

            rec_data = crop_recommendation_engine.recommend_from_context(
                ctx,
                language=language,
                agronomic_inputs=serializer.recommendation_inputs,
            )
            trending = rec_data.get("recommendations", [])[:10]

            return Response(attach_location_metadata({
                "location": ctx.query_label,
                "trending_crops": trending,
                "data_source": rec_data.get("data_source"),
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                "total_crops": len(trending),
            }, ctx), status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Trending crops error: {e}")
            return Response({
                "error": "Unable to fetch trending crops",
                "trending_crops": [],
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CropViewSet(viewsets.ViewSet):
    """Crop Service - Uses Government APIs for Real-Time Accurate Crop Data"""

    @action(detail=False, methods=["get"])
    def search(self, request):
        """Google-style crop autocomplete (mandi, diagnostics, advisory)."""
        serializer = LocationQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response({"error": "Invalid crop search parameters", "errors": serializer.errors}, status=400)
        params = serializer.validated_data
        query = params.get("q", "").strip()
        limit = min(params.get("limit", 10), 20)
        results = crop_catalog.search(query, limit=limit) if query else crop_catalog.popular(limit)
        return Response({
            "query": query,
            "results": results,
            "total": len(results),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        })

    def list(self, request):
        """Get crop information using government APIs"""
        try:
            serializer = CropRecommendationQuerySerializer(data=request.query_params)
            if not serializer.is_valid():
                return Response({"error": "Invalid crop query", "errors": serializer.errors}, status=400)
            params = serializer.validated_data
            crop_name = params.get("crop", "")
            ctx = resolve_request_location(request)
            location_error = require_confirmed_location(ctx, service="crop_information")
            if location_error:
                return location_error
            language = params.get("language", "hi")

            recs = crop_recommendation_engine.recommend_from_context(
                ctx,
                language=language,
                agronomic_inputs=serializer.recommendation_inputs,
            )
            crop_info = {}
            if crop_name:
                normalized = crop_catalog.normalize(crop_name)
                canonical_name = normalized["name"] if normalized else crop_name
                for crop in recs.get("recommendations", []):
                    if crop.get("crop_name", "").casefold() == canonical_name.casefold():
                        crop_info = crop
                        break
            else:
                canonical_name = None

            market_data = market_service.get_prices(
                ctx.query_label,
                crop=canonical_name,
                lat=ctx.latitude,
                lon=ctx.longitude,
                state=ctx.state or None,
                include_estimates=False,
            )

            return Response(attach_location_metadata({
                "crop": crop_name or "All Crops",
                "crop_info": crop_info,
                "market_data": market_data.get("top_crops", []),
                "market_data_quality": {
                    "is_live": bool(market_data.get("is_live")),
                    "status": market_data.get("status", "unavailable"),
                    "source": market_data.get("data_source", "unavailable"),
                    "fetched_at": market_data.get("fetched_at"),
                },
                "data_source": recs.get("data_source", "KrishiMitra crop engine"),
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }, ctx), status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Crop service error: {e}")
            return Response({
                "error": "Unable to fetch crop data",
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
