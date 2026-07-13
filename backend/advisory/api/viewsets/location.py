import logging
from datetime import datetime, timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

logger = logging.getLogger(__name__)

from ...services.location_context import location_resolver
from ..location_utils import resolve_request_location
from ..validation import MAX_LOCATION_QUERY_LENGTH, query_too_long
from ..errors import safe_error_message
from ..serializers import LocationQuerySerializer


class LocationRecommendationViewSet(viewsets.ViewSet):
    """Location search, GPS resolve, and reverse geocoding (India-wide)."""

    @action(detail=False, methods=["get"])
    def search(self, request):
        try:
            serializer = LocationQuerySerializer(data=request.query_params)
            if not serializer.is_valid():
                return Response({"error": "Invalid location search parameters", "errors": serializer.errors}, status=400)
            params = serializer.validated_data
            query = params.get("q", "").strip()
            if not query:
                return Response(
                    {"error": "Query parameter q is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            too_long = query_too_long(query, MAX_LOCATION_QUERY_LENGTH, field="q")
            if too_long:
                return too_long

            try:
                limit = min(max(params.get("limit", 12), 1), 20)
            except (TypeError, ValueError):
                limit = 12
            results = location_resolver.search(query, limit=limit)[:limit]
            return Response({
                "query": query,
                "results": results,
                "total": len(results),
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            })
        except Exception as e:
            return Response(
                {"error": "Unable to search locations", "message": safe_error_message(e, context="location_search")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get", "post"])
    def resolve(self, request):
        """Resolve GPS or text into full location context (village/society/city)."""
        try:
            source = request.query_params if request.method == "GET" else request.data
            serializer = LocationQuerySerializer(data=source)
            if not serializer.is_valid():
                return Response({"error": "Invalid location parameters", "errors": serializer.errors}, status=400)
            ctx = resolve_request_location(request)
            return Response({
                "status": "success",
                "location": ctx.to_dict(),
                "coordinates": {"lat": ctx.latitude, "lon": ctx.longitude},
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            })
        except Exception as e:
            return Response(
                {"error": "Unable to resolve location", "message": safe_error_message(e, context="location_resolve")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    def reverse(self, request):
        """Reverse geocode lat/lon (high zoom for ≤10 m GPS accuracy)."""
        try:
            serializer = LocationQuerySerializer(data=request.query_params)
            if not serializer.is_valid():
                return Response({"error": "Invalid reverse-geocoding parameters", "errors": serializer.errors}, status=400)
            params = serializer.validated_data
            lat = params.get("lat") or params.get("latitude")
            lon = params.get("lon") or params.get("longitude")
            if not lat or not lon:
                return Response(
                    {"error": "lat and lon parameters are required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            ctx = resolve_request_location(request)

            return Response({
                "status": "success",
                "coordinates": {"lat": ctx.latitude, "lon": ctx.longitude},
                "location": {
                    "name": ctx.display_name,
                    "display_name": ctx.display_name,
                    "city": ctx.city,
                    "village": ctx.village,
                    "locality": ctx.locality,
                    "sublocality": ctx.sublocality,
                    "district": ctx.district,
                    "state": ctx.state,
                    "pincode": ctx.pincode,
                    "region": ctx.region,
                    "type": ctx.location_type,
                    "accuracy_meters": ctx.accuracy_meters,
                    "accuracy_label": ctx.accuracy_label,
                    "source": ctx.source,
                    "full_address": ctx.full_address,
                    "coordinates": {"lat": ctx.latitude, "lng": ctx.longitude},
                },
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            })
        except Exception as e:
            return Response(
                {"error": "Unable to perform reverse geocoding", "message": safe_error_message(e, context="location_reverse")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
