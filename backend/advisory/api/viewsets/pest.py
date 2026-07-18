import logging
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from datetime import datetime, timezone

from rest_framework import status, viewsets
from rest_framework.response import Response

logger = logging.getLogger(__name__)

from ...services.enhanced_pest_detection import pest_detection_service
from ..location_utils import (
    attach_location_metadata,
    require_confirmed_location,
    resolve_request_location,
)
from ..validation import decode_base64_image, read_upload_with_limit
from ..serializers import LocationQuerySerializer, PestDetectionInputSerializer

# Module-level singleton — avoid per-request instantiation
try:
    from ...services.ultra_dynamic_government_api import UltraDynamicGovernmentAPI as _UltraDynamicGovernmentAPI
    _gov_api_singleton = _UltraDynamicGovernmentAPI()
except Exception as _e:
    logger.warning("UltraDynamicGovernmentAPI failed to load: %s", _e)
    _gov_api_singleton = None


class PestDetectionViewSet(viewsets.ViewSet):
    """Location-aware pest guidance with honest source and image-use labels."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gov_api = _gov_api_singleton  # use module-level singleton
        self.pest_service = pest_detection_service

    parser_classes = [JSONParser, MultiPartParser, FormParser]
    
    def list(self, request):
        """Get official pest guidance when the configured source is available."""
        try:
            serializer = LocationQuerySerializer(data=request.query_params)
            if not serializer.is_valid():
                return Response({'error': 'Invalid pest query', 'errors': serializer.errors}, status=400)
            params = serializer.validated_data
            crop_name = params.get('crop', '')
            language = params.get('language', 'hi')
            ctx = resolve_request_location(request)
            location_error = require_confirmed_location(ctx, service="pest_guidance")
            if location_error:
                return location_error

            pest_data = self._get_pest_guidance(crop_name, ctx.query_label, language)
            return Response(attach_location_metadata({
                'status': pest_data.get('status', 'unavailable'),
                'is_live': bool(pest_data.get('is_live')),
                'message': (
                    'Official pest guidance retrieved.'
                    if pest_data.get('is_live')
                    else 'Official pest guidance is currently unavailable.'
                ),
                'message_hi': (
                    'आधिकारिक कीट सलाह अभी उपलब्ध नहीं है।'
                    if not pest_data.get('is_live') else None
                ),
                'crop': crop_name,
                'pest_data': pest_data.get('data', {}),
                'data_source': pest_data.get('data_source', 'unavailable'),
                'timestamp': datetime.now(tz=timezone.utc).isoformat(),
            }, ctx), status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Pest detection error: {e}")
            return Response({
                'error': 'Unable to fetch pest data',
                'message': 'Government pest API temporarily unavailable'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def create(self, request):
        """Accept a photo but never claim classification without a verified model."""
        try:
            upload = request.FILES.get("image")
            serializer_data = request.data.copy()
            if upload:
                serializer_data.pop("image", None)
            serializer = PestDetectionInputSerializer(data=serializer_data)
            if not serializer.is_valid():
                return Response({'error': 'Invalid pest detection request', 'errors': serializer.errors}, status=400)
            data = serializer.validated_data
            image_value = data.get("image") or data.get("image_base64")
            if upload:
                _image_bytes, image_error = read_upload_with_limit(upload)
                if image_error:
                    return image_error
            elif image_value:
                _image_bytes, image_error = decode_base64_image(image_value)
                if image_error:
                    return image_error
            else:
                return Response(
                    {
                        "error": "A crop image is required for image-based detection.",
                        "error_code": "IMAGE_REQUIRED",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            crop_name = data.get('crop', '')
            language = data.get('language', 'hi')
            ctx = resolve_request_location(request)
            location_error = require_confirmed_location(ctx, service="pest_photo_advisory")
            if location_error:
                return location_error

            pest_data = self._get_pest_guidance(crop_name, ctx.query_label, language)
            return Response(attach_location_metadata({
                'status': 'advisory_fallback',
                'is_live': bool(pest_data.get('is_live')),
                'image_received': True,
                'image_classification_performed': False,
                'crop': crop_name,
                'message': (
                    'Photo received. A verified image classifier is not enabled, '
                    'so this is crop and location guidance, not a photo diagnosis.'
                ),
                'message_hi': (
                    'फोटो मिल गई है। सत्यापित इमेज मॉडल चालू नहीं है, इसलिए यह '
                    'फोटो निदान नहीं बल्कि फसल और स्थान पर आधारित सलाह है।'
                ),
                'pest_data': pest_data.get('data', {}),
                'data_source': pest_data.get('data_source', 'unavailable'),
                'timestamp': datetime.now(tz=timezone.utc).isoformat(),
            }, ctx), status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Pest detection image error: {e}")
            return Response({
                'error': 'Unable to process pest detection',
                'message': 'Government pest API temporarily unavailable',
                'timestamp': datetime.now(tz=timezone.utc).isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_pest_guidance(self, crop_name, location, language):
        if not self.gov_api:
            return {
                'status': 'unavailable',
                'is_live': False,
                'data_source': 'unavailable',
                'data': {},
            }
        try:
            result = self.gov_api.get_pest_control_recommendations(
                crop_name=crop_name,
                location=location,
                language=language,
            )
            return result if isinstance(result, dict) else {
                'status': 'unavailable',
                'is_live': False,
                'data_source': 'unavailable',
                'data': {},
            }
        except Exception as exc:
            logger.warning("Official pest guidance failed for %s: %s", location, exc)
            return {
                'status': 'unavailable',
                'is_live': False,
                'data_source': 'unavailable',
                'data': {},
            }
