"""
Real-Time Government Data ViewSet
Delegates to the canonical CropRecommendationEngine v3 and unified services.
No longer depends on the legacy crop recommendation system.
"""
import logging
from datetime import datetime, timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..location_utils import attach_location_metadata, resolve_request_location
from ...services.crop_catalog import crop_catalog
from ...services.crop_recommendation_engine import crop_recommendation_engine
from ...services.language_service import normalise_language_code
from ...services.unified_realtime_service import market_service, weather_service

logger = logging.getLogger(__name__)

# Module-level singleton — avoid per-request init of UltraDynamicGovernmentAPI
try:
    from ...services.ultra_dynamic_government_api import UltraDynamicGovernmentAPI as _UltraDynamicGovernmentAPI
    _gov_api_singleton = _UltraDynamicGovernmentAPI()
except Exception as _e:
    logger.warning("UltraDynamicGovernmentAPI failed to load: %s", _e)
    _gov_api_singleton = None


class RealTimeGovernmentDataViewSet(viewsets.ViewSet):
    """Aggregated government data endpoints (weather, market, crops, pest)."""

    permission_classes = [AllowAny]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use module-level singleton instead of per-request instantiation
        self.gov_api = _gov_api_singleton

    # ── Weather ───────────────────────────────────────────────
    @action(detail=False, methods=['get'])
    def weather(self, request):
        """Real-time weather — delegates to unified WeatherService (Open-Meteo)."""
        try:
            ctx  = resolve_request_location(request)
            lang = normalise_language_code(request.query_params.get('language', 'hi'))
            data = weather_service.get_weather(ctx.query_label, ctx.latitude, ctx.longitude, lang=lang)
            return Response(attach_location_metadata(data, ctx))
        except Exception as e:
            logger.error("Weather API error: %s", e)
            return Response({'error': 'Unable to fetch weather data'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ── Market Prices ────────────────────────────────────────
    @action(detail=False, methods=['get'])
    def market_prices(self, request):
        """Real-time mandi prices — delegates to unified MarketPricesService."""
        try:
            ctx   = resolve_request_location(request)
            mandi = request.query_params.get('mandi')
            crop  = request.query_params.get('crop')
            norm  = crop_catalog.normalize(crop) if crop else None
            commodity = norm['name'] if norm else crop
            include_estimates = request.query_params.get('include_estimates', '').lower() in ('1', 'true', 'yes')

            data = market_service.get_prices(
                ctx.query_label, mandi=mandi, crop=commodity,
                lat=ctx.latitude, lon=ctx.longitude,
                state=ctx.state or None, include_estimates=include_estimates,
            )
            return Response(attach_location_metadata(data, ctx))
        except Exception as e:
            logger.error("Market prices API error: %s", e)
            return Response({'error': 'Unable to fetch market prices'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ── Crop Recommendations ─────────────────────────────────
    @action(detail=False, methods=['get'])
    def crop_recommendations(self, request):
        """
        Location-aware crop recommendations — uses CropRecommendationEngine v3
        (80 crops, live weather, mandi prices, district profiles).
        """
        try:
            ctx  = resolve_request_location(request)
            lang = normalise_language_code(request.query_params.get('language', 'hi'))
            data = crop_recommendation_engine.recommend_from_context(ctx, language=lang)
            return Response(attach_location_metadata(data, ctx))
        except Exception as e:
            logger.error("Crop recommendations API error: %s", e)
            return Response({'error': 'Unable to fetch crop recommendations'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ── Pest Detection ───────────────────────────────────────
    @action(detail=False, methods=['post'])
    def pest_detection(self, request):
        """Pest guidance for a crop/location — use /api/diagnostics/detect/ for image-based."""
        try:
            crop     = request.data.get('crop', 'Wheat')
            location = request.data.get('location', 'Delhi')
            language = request.data.get('language', 'hi')
            pest_data = self.gov_api.get_pest_control_recommendations(crop, location, language=language)
            return Response({
                'status': 'success',
                'crop': crop,
                'location': location,
                'pest_analysis': pest_data,
                'data_source': 'ICAR pest database',
                'timestamp': datetime.now(tz=timezone.utc).isoformat(),
            })
        except Exception as e:
            logger.error("Pest detection API error: %s", e)
            return Response({'error': 'Unable to process pest detection'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ── Mandi Search ─────────────────────────────────────────
    @action(detail=False, methods=['get'])
    def mandi_search(self, request):
        """Search mandis near the user's location."""
        try:
            ctx   = resolve_request_location(request)
            query = request.query_params.get('q', '').strip()

            mandi_data = market_service.list_mandis(
                ctx.query_label, lat=ctx.latitude, lon=ctx.longitude, state=ctx.state or None
            )
            mandis = mandi_data.get('mandis', [])
            if query:
                mandis = [m for m in mandis if query.lower() in m.get('name', '').lower()]

            return Response(attach_location_metadata({
                'results':  mandis,
                'count':    len(mandis),
                'status':   'success',
                'is_live':  mandi_data.get('is_live', False),
                'coverage': mandi_data.get('coverage', ''),
            }, ctx))
        except Exception as e:
            logger.error("Mandi search error: %s", e)
            return Response({'error': 'Unable to search mandis'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ── Crop Search ──────────────────────────────────────────
    @action(detail=False, methods=['get'])
    def crop_search(self, request):
        """Crop autocomplete using the crop catalog (80+ crops)."""
        try:
            query = (request.query_params.get('crop') or request.query_params.get('q', '')).strip()
            if not query:
                return Response({'error': 'Provide crop or q parameter'},
                                status=status.HTTP_400_BAD_REQUEST)
            try:
                limit = min(int(request.query_params.get('limit', 20)), 50)
            except (ValueError, TypeError):
                limit = 20

            results = crop_catalog.search(query, limit=limit)
            return Response({
                'available_crops': [r['name'] for r in results],
                'results':         results,
                'count':           len(results),
                'status':          'success',
            })
        except Exception as e:
            logger.error("Crop search error: %s", e)
            return Response({'error': 'Unable to search crops'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
