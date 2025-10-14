#!/usr/bin/env python3
"""
API Views for Agricultural Advisory System
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import logging
from datetime import datetime

from ..services.enhanced_government_api import EnhancedGovernmentAPI
from ..services.realtime_government_ai import RealTimeGovernmentAI
from ..services.enhanced_multilingual import EnhancedMultilingualSupport
from ..services.real_government_data_analysis import RealGovernmentDataAnalysis

logger = logging.getLogger(__name__)

class ChatbotViewSet(viewsets.ViewSet):
    """AI Chatbot for agricultural queries"""
    
    def create(self, request):
        """Process chatbot queries"""
        try:
            # Initialize services for this request
            try:
                realtime_ai = RealTimeGovernmentAI()
            except Exception as init_error:
                logger.error(f"Service initialization error: {init_error}")
                return Response({
                    'response': 'Service temporarily unavailable. Please try again later.',
                    'data_source': 'error_fallback'
                }, status=status.HTTP_200_OK)
            
            data = request.data
            query = data.get('query', '')
            language = data.get('language', 'hindi')
            location = data.get('location', 'Delhi')
            latitude = data.get('latitude', 28.7041)
            longitude = data.get('longitude', 77.1025)
            
            if not query:
                return Response({
                    'error': 'Query is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Process the query using real-time AI
            result = realtime_ai.process_farming_query(
                query=query,
                            language=language,
                location=location,
                latitude=latitude,
                longitude=longitude
            )
            
            return Response(result, status=status.HTTP_200_OK)
            
                except Exception as e:
            logger.error(f"Chatbot error: {e}")
                    return Response({
                        'response': 'Sorry, I encountered an error processing your query. Please try again.',
                        'error': str(e),
                'data_source': 'error_fallback'
            }, status=status.HTTP_200_OK)


class RealTimeGovernmentDataViewSet(viewsets.ViewSet):
    """Real-time government data API endpoints"""
    
    def __init__(self):
        self.gov_api = EnhancedGovernmentAPI()
    
    @action(detail=False, methods=['get'])
    def weather(self, request):
        """Get real-time weather data for location from government APIs"""
        try:
            location = request.query_params.get('location', 'Delhi')
            weather_data = self.gov_api.get_enhanced_weather_data(location)
                return Response({
                'location': location,
                'weather_data': weather_data,
                'data_source': 'IMD Government API',
                'timestamp': datetime.now().isoformat()
            }, status=status.HTTP_200_OK)
            except Exception as e:
            logger.error(f"Weather API error: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def market_prices(self, request):
        """Get real-time market prices for location from government APIs"""
        try:
            location = request.query_params.get('location', 'Delhi')
            crop = request.query_params.get('crop', '')
            
            if crop:
                prices_data = self.gov_api.get_enhanced_market_prices(crop, location)
        else:
                prices_data = self.gov_api.get_enhanced_market_data(location)
            
                return Response({
                'location': location,
                'crop': crop,
                'market_data': prices_data,
                'data_source': 'Agmarknet + e-NAM Government APIs',
                'timestamp': datetime.now().isoformat()
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Market prices API error: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def crop_recommendations(self, request):
        """Get comprehensive crop recommendations using real government data analysis"""
        try:
            location = request.query_params.get('location', 'Delhi')
            season = request.query_params.get('season', 'current')
            
            # Use comprehensive real government data analysis
            analysis_service = RealGovernmentDataAnalysis()
            crop_analyses = analysis_service.get_comprehensive_crop_recommendations(location, season)
            
            # Convert analyses to API response format
            recommendations = []
            for analysis in crop_analyses:
                recommendation = {
                    'name': analysis.crop_name,
                    'season': season,
                    'historical_yield_trend': analysis.historical_yield_trend,
                    'historical_price_trend': analysis.historical_price_trend,
                    'current_yield_prediction': analysis.current_yield_prediction,
                    'future_yield_prediction': analysis.future_yield_prediction,
                    'current_market_price': analysis.current_market_price,
                    'predicted_future_price': analysis.predicted_future_price,
                    'input_cost_analysis': analysis.input_cost_analysis,
                    'profitability_score': analysis.profitability_score,
                    'risk_assessment': analysis.risk_assessment,
                    'government_support': analysis.government_support,
                    'confidence_level': analysis.confidence_level,
                    'data_source': 'Real Government APIs',
                    'timestamp': datetime.now().isoformat()
                }
                recommendations.append(recommendation)
            
            return Response({
                'location': location,
            'season': season,
                'recommendations': recommendations,
                'analysis_summary': {
                    'total_crops_analyzed': len(recommendations),
                    'data_sources': ['IMD', 'Agmarknet', 'e-NAM', 'ICAR', 'Soil Health Card', 'KVK'],
                    'analysis_period': '5-10 years historical + current + future predictions'
                }
            }, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"Crop recommendations API error: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def government_schemes(self, request):
        """Get government schemes for farmers from official government sources"""
        try:
            location = request.query_params.get('location', 'Delhi')
            schemes = self.gov_api.get_government_schemes(location)
                return Response({
                'location': location,
                'government_schemes': schemes,
                'data_source': 'Official Government Databases',
                'timestamp': datetime.now().isoformat()
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Government schemes API error: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def soil_health(self, request):
        """Get soil health data for location from government soil health card APIs"""
        try:
            location = request.query_params.get('location', 'Delhi')
            # Use the existing method in EnhancedGovernmentAPI
            soil_data = self.gov_api._get_comprehensive_soil_data(location)
                return Response({
                'location': location,
                'soil_data': soil_data,
                'data_source': 'Soil Health Card Government API',
                'timestamp': datetime.now().isoformat()
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Soil health API error: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def pest_detection(self, request):
        """Get pest detection and control recommendations using government databases"""
        try:
            data = request.data
            crop_name = data.get('crop', '')
            location = data.get('location', 'Delhi')
            symptoms = data.get('symptoms', '')
            
            # Use government pest and disease database
            pest_data = self.gov_api.get_pest_control_recommendations(crop_name, location, symptoms)
            
                return Response({
                'crop': crop_name,
                'location': location,
                'symptoms': symptoms,
                'pest_analysis': pest_data,
                'data_source': 'ICAR Pest & Disease Database',
                'timestamp': datetime.now().isoformat()
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Pest detection API error: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LocationRecommendationViewSet(viewsets.ViewSet):
    """Location detection and recommendations"""
    
    @action(detail=False, methods=['get'])
    def suggestions(self, request):
        """Get location suggestions"""
        try:
            # Initialize service for this request
            try:
                enhanced_api = EnhancedGovernmentAPI()
            except Exception as init_error:
                logger.error(f"Service initialization error: {init_error}")
        return Response({
                    'suggestions': [],
                    'error': 'Service temporarily unavailable'
        }, status=status.HTTP_200_OK)

            query = request.GET.get('q', '')
            if not query:
                return Response({
                    'suggestions': [],
                    'error': 'Query parameter is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get location suggestions
            result = enhanced_api.detect_location_comprehensive(query)
            
            suggestions = [{
                'name': result.get('location', query),
                'state': result.get('state', 'Unknown'),
                'district': 'Multiple',
                'confidence': result.get('confidence', 0.5),
                'type': 'state' if result.get('state') else 'city'
            }]
            
            return Response({
                'suggestions': suggestions,
                'query': query,
                'count': len(suggestions),
                'timestamp': result.get('timestamp', '')
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Location suggestions error: {e}")
            return Response({
                'suggestions': [],
                'error': str(e)
            }, status=status.HTTP_200_OK)

class CropViewSet(viewsets.ViewSet):
    """Crop-related endpoints"""
    
    def list(self, request):
        """Get list of crops"""
                return Response({
            'message': 'Crop list endpoint',
            'crops': []
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], url_path='recommendations')
    def recommendations(self, request):
        """Get crop recommendations"""
        try:
            from advisory.services.consolidated_crop_service import ConsolidatedCropService
            
            data = request.data
            location = data.get('location', 'Delhi')
            season = data.get('season')
            soil_type = data.get('soil_type')
            
            crop_service = ConsolidatedCropService()
            recommendations = crop_service.get_crop_recommendations(location, season, soil_type)
            
            return Response({
                'message': 'Crop recommendations generated successfully',
                'data': recommendations
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': 'Failed to get crop recommendations',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
class WeatherViewSet(viewsets.ViewSet):
    """Weather-related endpoints"""
    
    def list(self, request):
        """Get weather data"""
                return Response({
            'message': 'Weather endpoint',
            'weather': {}
        }, status=status.HTTP_200_OK)

class MarketPricesViewSet(viewsets.ViewSet):
    """Market prices endpoints"""
    
    def list(self, request):
        """Get market prices"""
                return Response({
            'message': 'Market prices endpoint',
            'prices': {}
        }, status=status.HTTP_200_OK)

class GovernmentSchemesViewSet(viewsets.ViewSet):
    """Government schemes endpoints"""
    
    def list(self, request):
        """Get government schemes"""
                return Response({
            'message': 'Government schemes endpoint',
            'schemes': []
        }, status=status.HTTP_200_OK)

class TrendingCropsViewSet(viewsets.ViewSet):
    """Trending crops endpoints"""
    
    def list(self, request):
        """Get trending crops"""
            return Response({
            'message': 'Trending crops endpoint',
            'trending_crops': []
            }, status=status.HTTP_200_OK)
            
class SMSIVRViewSet(viewsets.ViewSet):
    """SMS/IVR endpoints"""
    
    def list(self, request):
        """Get SMS/IVR data"""
                return Response({
            'message': 'SMS/IVR endpoint',
            'data': {}
        }, status=status.HTTP_200_OK)

class PestDetectionViewSet(viewsets.ViewSet):
    """Pest detection endpoints"""
    
    def list(self, request):
        """Get pest detection data"""
                    return Response({
            'message': 'Pest detection endpoint',
            'detections': []
                    }, status=status.HTTP_200_OK)

class UserViewSet(viewsets.ViewSet):
    """User management endpoints"""
    
    def list(self, request):
        """Get users"""
            return Response({
            'message': 'Users endpoint',
            'users': []
            }, status=status.HTTP_200_OK)
            
class TextToSpeechViewSet(viewsets.ViewSet):
    """Text-to-speech endpoints"""
    
    def list(self, request):
        """Get TTS data"""
                return Response({
            'message': 'Text-to-speech endpoint',
            'data': {}
                }, status=status.HTTP_200_OK)
            
class ForumPostViewSet(viewsets.ViewSet):
    """Forum posts endpoints"""
    
    def list(self, request):
        """Get forum posts"""
            return Response({
            'message': 'Forum posts endpoint',
            'posts': []
            }, status=status.HTTP_200_OK)
            
# Legacy ViewSet for backward compatibility
class CropAdvisoryViewSet(viewsets.ViewSet):
    """Crop advisory endpoints (legacy)"""
    
    def list(self, request):
        """Get crop advisories"""
        return Response({
            'message': 'Crop advisory endpoint',
            'advisories': []
        }, status=status.HTTP_200_OK)