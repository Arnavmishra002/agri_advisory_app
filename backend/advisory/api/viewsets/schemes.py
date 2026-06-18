"""Government schemes API (unified realtime service)."""

import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..location_utils import attach_location_metadata, resolve_request_location
from ..errors import safe_error_message
from ...services.unified_realtime_service import schemes_service

logger = logging.getLogger(__name__)


class GovernmentSchemesViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        try:
            ctx = resolve_request_location(request)
            category = request.GET.get("category")
            data = schemes_service.get_schemes(ctx.query_label, category)
            return Response(attach_location_metadata(data, ctx))
        except Exception as exc:
            logger.exception("Government schemes API error: %s", exc)
            return Response(
                {
                    "status": "error",
                    "error": "Unable to load government schemes",
                    "message": safe_error_message(exc, context="schemes"),
                    "schemes": [],
                    "total": 0,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def eligibility(self, request):
        try:
            profile = request.data.get("farmer_profile", {})
            if not isinstance(profile, dict):
                return Response(
                    {"status": "error", "message": "farmer_profile must be a JSON object"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            data = schemes_service.check_eligibility(profile)
            return Response(data)
        except Exception as exc:
            logger.exception("Eligibility check error: %s", exc)
            return Response(
                {
                    "status": "error",
                    "error": "Unable to check eligibility",
                    "message": safe_error_message(exc, context="schemes"),
                    "eligible_schemes": [],
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
