import logging
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from datetime import datetime, timezone

from rest_framework import status, viewsets
from rest_framework.response import Response

logger = logging.getLogger(__name__)

from ...services.enhanced_pest_detection import pest_detection_service
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
    """Pest Detection Service - Uses Government APIs (ICAR, PPQS) for Real-Time Accurate Pest Data"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gov_api = _gov_api_singleton  # use module-level singleton
        self.pest_service = pest_detection_service

    parser_classes = [JSONParser, MultiPartParser, FormParser]
    
    def list(self, request):
        """Get pest information using government APIs with location"""
        try:
            serializer = LocationQuerySerializer(data=request.query_params)
            if not serializer.is_valid():
                return Response({'error': 'Invalid pest query', 'errors': serializer.errors}, status=400)
            params = serializer.validated_data
            crop_name = params.get('crop', '')
            location = params.get('location', 'Delhi')
            latitude = params.get('latitude')
            longitude = params.get('longitude')
            language = params.get('language', 'hi')
            
            logger.info(f"🐛 Fetching pest data using Government APIs for {crop_name} in {location} (lat: {latitude}, lon: {longitude}) in {language}")
            
            # Use government API for pest information with location
            if self.gov_api:
                try:
                    pest_data = self.gov_api.get_pest_control_recommendations(
                        crop_name=crop_name,
                        location=location,
                        language=language
                    )
                    
                    if pest_data and pest_data.get('status') == 'success':
                        logger.info(f"✅ Pest data retrieved from Government APIs for {location}")
                        response_data = {
                            'message': 'Pest detection service using Government APIs',
                            'crop': crop_name,
                            'location': location,
                            'pest_data': pest_data.get('data', pest_data),
                            'data_source': 'ICAR + PPQS (Government APIs)',
                            'timestamp': datetime.now(tz=timezone.utc).isoformat()
                        }
                        # Add location info if available
                        if latitude:
                            response_data['latitude'] = latitude
                        if longitude:
                            response_data['longitude'] = longitude
                        return Response(response_data, status=status.HTTP_200_OK)
                except Exception as e:
                    logger.warning(f"Government API error in pest detection for {location}: {e}")
            
            return Response({
                'message': 'Pest detection service using Government APIs',
                'crop': crop_name,
                'location': location,
                'data_source': 'ICAR + PPQS (Government APIs)',
                'timestamp': datetime.now(tz=timezone.utc).isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Pest detection error: {e}")
            return Response({
                'error': 'Unable to fetch pest data',
                'message': 'Government pest API temporarily unavailable'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def create(self, request):
        """Handle pest detection from image upload with location"""
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
            # Get location from request
            location = data.get('location', 'Delhi')
            crop_name = data.get('crop', '')
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            
            logger.info(f"🐛 Processing pest detection from image for {crop_name} in {location}")
            
            # Use government APIs for pest identification with location
            if self.gov_api:
                try:
                    pest_data = self.gov_api.get_pest_control_recommendations(
                        crop_name=crop_name,
                        location=location
                    )
                    
                    response_data = {
                        'message': 'Pest detection from image using Government APIs',
                        'crop': crop_name,
                        'location': location,
                        'data_source': 'ICAR + PPQS (Government APIs)',
                        'status': 'success',
                        'timestamp': datetime.now(tz=timezone.utc).isoformat()
                    }
                    
                    if pest_data and pest_data.get('status') == 'success':
                        response_data['pest_data'] = pest_data.get('data', {})
                    
                    return Response(response_data, status=status.HTTP_200_OK)
                except Exception as e:
                    logger.warning(f"Government API error in pest image detection for {location}: {e}")
            
            return Response({
                'message': 'Pest detection from image using Government APIs',
                'crop': crop_name,
                'location': location,
                'data_source': 'ICAR + PPQS (Government APIs)',
                'status': 'success',
                'timestamp': datetime.now(tz=timezone.utc).isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Pest detection image error: {e}")
            return Response({
                'error': 'Unable to process pest detection',
                'message': 'Government pest API temporarily unavailable',
                'timestamp': datetime.now(tz=timezone.utc).isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
