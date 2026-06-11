import logging
from datetime import datetime

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

logger = logging.getLogger(__name__)

from ..location_utils import attach_location_metadata, resolve_request_location
from ...services.comprehensive_crop_recommendations import ComprehensiveCropRecommendations
from ...services.crop_catalog import crop_catalog
from ...services.crop_recommendation_engine import crop_recommendation_engine
from ...services.ultra_dynamic_government_api import UltraDynamicGovernmentAPI


class CropAdvisoryViewSet(viewsets.ViewSet):
    """Crop advisory — multi-factor scoring with live weather + mandi data."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gov_api = UltraDynamicGovernmentAPI()
        try:
            self.crop_service = ComprehensiveCropRecommendations()
        except Exception as e:
            logger.warning(f"Could not load ComprehensiveCropRecommendations: {e}")
            self.crop_service = None

    def list(self, request):
        try:
            ctx = resolve_request_location(request)
            language = request.query_params.get("language", "hi")

            logger.info(
                "Crop recommendations (intelligent engine) for %s @ %s,%s",
                ctx.query_label, ctx.latitude, ctx.longitude,
            )

            recommendations = crop_recommendation_engine.recommend_from_context(
                ctx, language=language
            )

            return Response(
                attach_location_metadata(recommendations, ctx),
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Crop advisory error: {e}")
            return Response({
                "error": "Unable to fetch crop recommendations",
                "message": str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TrendingCropsViewSet(viewsets.ViewSet):
    """Trending Crops Service - Uses Government APIs for Real-Time Accurate Data"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gov_api = UltraDynamicGovernmentAPI()

    def list(self, request):
        """Get trending crops using government APIs"""
        try:
            ctx = resolve_request_location(request)
            language = request.query_params.get("language", "hi")

            rec_data = crop_recommendation_engine.recommend_from_context(ctx, language=language)
            trending = rec_data.get("recommendations", [])[:10]

            return Response(attach_location_metadata({
                "location": ctx.query_label,
                "trending_crops": trending,
                "data_source": rec_data.get("data_source"),
                "timestamp": datetime.now().isoformat(),
                "total_crops": len(trending),
            }, ctx), status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Trending crops error: {e}")
            return Response({
                "error": "Unable to fetch trending crops",
                "trending_crops": [],
                "timestamp": datetime.now().isoformat(),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CropViewSet(viewsets.ViewSet):
    """Crop Service - Uses Government APIs for Real-Time Accurate Crop Data"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gov_api = UltraDynamicGovernmentAPI()

    @action(detail=False, methods=["get"])
    def search(self, request):
        """Google-style crop autocomplete (mandi, diagnostics, advisory)."""
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
            "timestamp": datetime.now().isoformat(),
        })

    def list(self, request):
        """Get crop information using government APIs"""
        try:
            crop_name = request.query_params.get("crop", "")
            ctx = resolve_request_location(request)
            language = request.query_params.get("language", "hi")

            gov_data = self.gov_api.get_comprehensive_government_data(
                location=ctx.query_label,
                latitude=ctx.latitude,
                longitude=ctx.longitude,
            )

            crop_info = {}
            if crop_name:
                recs = crop_recommendation_engine.recommend_from_context(ctx, language=language)
                for crop in recs.get("recommendations", []):
                    if crop.get("crop_name", "").lower() == crop_name.lower():
                        crop_info = crop
                        break

            market_data = gov_data.get("government_data", {}).get("market_prices", {})

            return Response(attach_location_metadata({
                "crop": crop_name or "All Crops",
                "crop_info": crop_info,
                "market_data": market_data.get("crops", []) if isinstance(market_data, dict) else [],
                "data_source": "Government APIs + Intelligent Engine",
                "timestamp": datetime.now().isoformat(),
            }, ctx), status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Crop service error: {e}")
            return Response({
                "error": "Unable to fetch crop data",
                "timestamp": datetime.now().isoformat(),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
