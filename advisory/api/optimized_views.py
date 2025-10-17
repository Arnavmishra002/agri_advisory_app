#!/usr/bin/env python3
"""
Optimized API Views for Krishimitra AI
Uses unified service architecture with performance optimization
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List

# Import unified services
from ..services.unified_service_architecture import unified_service_manager
from ..services.performance_optimizer import (
    performance_optimizer, monitor_performance, cache_function_result
)

logger = logging.getLogger(__name__)


class OptimizedChatbotViewSet(viewsets.ViewSet):
    """
    Optimized AI-Powered Chatbot using Unified Service Architecture
    
    Features:
    - Unified service management
    - Performance monitoring
    - Intelligent caching
    - Context-aware responses
    - Multilingual support
    - Smart query routing
    """
    
    def create(self, request):
        """Process chatbot queries with optimized performance"""
        start_time = time.time()
        
        try:
            # Extract request data
            query = request.data.get('query', '').strip()
            session_id = request.data.get('session_id', f'session_{int(time.time())}')
            language = request.data.get('language', 'auto')
            location = request.data.get('location', '')
            latitude = request.data.get('latitude')
            longitude = request.data.get('longitude')
            
            # Validate input
            if not query:
                return Response({
                    'response': 'Please provide a query.',
                    'data_source': 'validation_error',
                    'timestamp': datetime.now().isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Process query using unified service manager
            result = unified_service_manager.process_query(
                query=query,
                session_id=session_id,
                location=location,
                latitude=latitude,
                longitude=longitude
            )
            
            # Optimize response
            optimized_result = performance_optimizer.optimize_api_response(result)
            
            # Record performance metrics
            execution_time = time.time() - start_time
            performance_optimizer.monitor.record_metric(
                'chatbot_response_time', 
                execution_time,
                {'query_type': result.get('classification', {}).get('category', 'unknown')}
            )
            
            return Response(optimized_result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Chatbot error: {e}")
            execution_time = time.time() - start_time
            
            return Response({
                'response': 'I apologize, but I encountered an error processing your query. Please try again.',
                'data_source': 'error_fallback',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'execution_time': execution_time
            }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """Get chatbot service status"""
        try:
            service_status = unified_service_manager.get_service_status()
            performance_summary = performance_optimizer.get_performance_summary()
            
            return Response({
                'status': 'operational',
                'services': service_status,
                'performance': performance_summary,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            return Response({
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OptimizedCropRecommendationsViewSet(viewsets.ViewSet):
    """
    Optimized Crop Recommendations using Unified Service Architecture
    """
    
    @monitor_performance('crop_recommendations_time')
    @cache_function_result(timeout=1800)  # Cache for 30 minutes
    def list(self, request):
        """Get crop recommendations with caching and optimization"""
        try:
            # Extract parameters
            location = request.query_params.get('location', 'Delhi')
            latitude = request.query_params.get('latitude')
            longitude = request.query_params.get('longitude')
            soil_type = request.query_params.get('soil_type')
            season = request.query_params.get('season')
            
            # Convert coordinates if provided
            if latitude:
                latitude = float(latitude)
            if longitude:
                longitude = float(longitude)
            
            # Get crop recommendations using unified service
            crop_service = unified_service_manager.services['crop']
            recommendations = crop_service.get_crop_recommendations(
                location=location,
                latitude=latitude,
                longitude=longitude,
                soil_type=soil_type,
                season=season
            )
            
            # Optimize response
            optimized_result = performance_optimizer.optimize_api_response(recommendations)
            
            return Response(optimized_result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Crop recommendations error: {e}")
            return Response({
                'error': 'Failed to get crop recommendations',
                'details': str(e),
                'timestamp': datetime.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search for specific crop information"""
        try:
            crop_name = request.query_params.get('crop', '').lower()
            location = request.query_params.get('location', '')
            
            if not crop_name:
                return Response({
                    'error': 'Crop name is required',
                    'timestamp': datetime.now().isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get crop information
            crop_service = unified_service_manager.services['crop']
            crop_info = crop_service.crop_database.get(crop_name)
            
            if not crop_info:
                return Response({
                    'error': f'Crop "{crop_name}" not found',
                    'available_crops': list(crop_service.crop_database.keys()),
                    'timestamp': datetime.now().isoformat()
                }, status=status.HTTP_404_NOT_FOUND)
            
            result = {
                'crop_info': crop_info,
                'location': location,
                'timestamp': datetime.now().isoformat()
            }
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Crop search error: {e}")
            return Response({
                'error': 'Failed to search crop information',
                'details': str(e),
                'timestamp': datetime.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OptimizedWeatherViewSet(viewsets.ViewSet):
    """
    Optimized Weather Data using Unified Service Architecture
    """
    
    @monitor_performance('weather_api_time')
    @cache_function_result(timeout=300)  # Cache for 5 minutes
    def list(self, request):
        """Get weather data with caching"""
        try:
            # Extract parameters
            location = request.query_params.get('location', 'Delhi')
            latitude = request.query_params.get('latitude')
            longitude = request.query_params.get('longitude')
            
            # Convert coordinates if provided
            if latitude:
                latitude = float(latitude)
            if longitude:
                longitude = float(longitude)
            
            # Get weather data using unified service
            government_service = unified_service_manager.services['government']
            weather_data = government_service.get_weather_data(
                location=location,
                latitude=latitude,
                longitude=longitude
            )
            
            return Response(weather_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Weather API error: {e}")
            return Response({
                'error': 'Failed to get weather data',
                'details': str(e),
                'timestamp': datetime.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OptimizedMarketPricesViewSet(viewsets.ViewSet):
    """
    Optimized Market Prices using Unified Service Architecture
    """
    
    @monitor_performance('market_prices_time')
    @cache_function_result(timeout=600)  # Cache for 10 minutes
    def list(self, request):
        """Get market prices with caching"""
        try:
            # Extract parameters
            crop = request.query_params.get('crop')
            location = request.query_params.get('location', 'Delhi')
            
            # Get market prices using unified service
            government_service = unified_service_manager.services['government']
            market_data = government_service.get_market_prices(
                crop=crop,
                location=location
            )
            
            return Response(market_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Market prices error: {e}")
            return Response({
                'error': 'Failed to get market prices',
                'details': str(e),
                'timestamp': datetime.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OptimizedGovernmentSchemesViewSet(viewsets.ViewSet):
    """
    Optimized Government Schemes using Unified Service Architecture
    """
    
    @monitor_performance('government_schemes_time')
    @cache_function_result(timeout=3600)  # Cache for 1 hour
    def list(self, request):
        """Get government schemes with caching"""
        try:
            # Extract parameters
            location = request.query_params.get('location', 'Delhi')
            
            # Get government schemes using unified service
            government_service = unified_service_manager.services['government']
            schemes_data = government_service.get_government_schemes(location=location)
            
            return Response(schemes_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Government schemes error: {e}")
            return Response({
                'error': 'Failed to get government schemes',
                'details': str(e),
                'timestamp': datetime.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OptimizedPestDetectionViewSet(viewsets.ViewSet):
    """
    Optimized Pest Detection using Unified Service Architecture
    """
    
    @monitor_performance('pest_detection_time')
    @cache_function_result(timeout=1800)  # Cache for 30 minutes
    def create(self, request):
        """Detect pests and diseases with caching"""
        try:
            # Extract parameters
            crop = request.data.get('crop', '').lower()
            symptoms = request.data.get('symptoms', '')
            location = request.data.get('location', '')
            
            if not crop or not symptoms:
                return Response({
                    'error': 'Crop and symptoms are required',
                    'timestamp': datetime.now().isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get pest detection using unified service
            crop_service = unified_service_manager.services['crop']
            pest_analysis = crop_service.detect_pest_disease(
                crop=crop,
                symptoms=symptoms,
                location=location
            )
            
            return Response(pest_analysis, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Pest detection error: {e}")
            return Response({
                'error': 'Failed to detect pests',
                'details': str(e),
                'timestamp': datetime.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OptimizedLocationViewSet(viewsets.ViewSet):
    """
    Optimized Location Services using Unified Service Architecture
    """
    
    @monitor_performance('location_search_time')
    @cache_function_result(timeout=3600)  # Cache for 1 hour
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search for locations with caching"""
        try:
            query = request.query_params.get('q', '').strip()
            
            if not query:
                return Response({
                    'error': 'Search query is required',
                    'timestamp': datetime.now().isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get location data using unified service
            government_service = unified_service_manager.services['government']
            locations = []
            
            # Search in known locations
            for loc_name, coords in government_service.locations.items():
                if query.lower() in loc_name.lower():
                    locations.append({
                        'name': loc_name.title(),
                        'latitude': coords['lat'],
                        'longitude': coords['lon'],
                        'state': coords['state']
                    })
            
            result = {
                'query': query,
                'locations': locations,
                'total_found': len(locations),
                'timestamp': datetime.now().isoformat()
            }
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Location search error: {e}")
            return Response({
                'error': 'Failed to search locations',
                'details': str(e),
                'timestamp': datetime.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @monitor_performance('reverse_geocoding_time')
    @cache_function_result(timeout=3600)  # Cache for 1 hour
    @action(detail=False, methods=['get'])
    def reverse(self, request):
        """Reverse geocoding with caching"""
        try:
            latitude = request.query_params.get('lat')
            longitude = request.query_params.get('lon')
            
            if not latitude or not longitude:
                return Response({
                    'error': 'Latitude and longitude are required',
                    'timestamp': datetime.now().isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                lat = float(latitude)
                lon = float(longitude)
            except ValueError:
                return Response({
                    'error': 'Invalid latitude or longitude format',
                    'timestamp': datetime.now().isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Find closest location
            government_service = unified_service_manager.services['government']
            closest_location = None
            min_distance = float('inf')
            
            for loc_name, coords in government_service.locations.items():
                distance = ((lat - coords['lat']) ** 2 + (lon - coords['lon']) ** 2) ** 0.5
                if distance < min_distance:
                    min_distance = distance
                    closest_location = {
                        'name': loc_name.title(),
                        'latitude': coords['lat'],
                        'longitude': coords['lon'],
                        'state': coords['state'],
                        'distance_km': distance * 111  # Approximate km per degree
                    }
            
            result = {
                'input_coordinates': {'latitude': lat, 'longitude': lon},
                'location': closest_location,
                'timestamp': datetime.now().isoformat()
            }
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Reverse geocoding error: {e}")
            return Response({
                'error': 'Failed to perform reverse geocoding',
                'details': str(e),
                'timestamp': datetime.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PerformanceMonitoringViewSet(viewsets.ViewSet):
    """
    Performance Monitoring and System Status
    """
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """Get comprehensive system status"""
        try:
            # Get service status
            service_status = unified_service_manager.get_service_status()
            
            # Get performance metrics
            performance_summary = performance_optimizer.get_performance_summary()
            
            # Get cache statistics
            cache_stats = performance_optimizer.cache_manager.get_stats()
            
            result = {
                'status': 'operational',
                'services': service_status,
                'performance': performance_summary,
                'cache': cache_stats,
                'timestamp': datetime.now().isoformat()
            }
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Status check error: {e}")
            return Response({
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def clear_cache(self, request):
        """Clear system cache"""
        try:
            service_name = request.data.get('service')
            
            if service_name:
                unified_service_manager.clear_cache(service_name)
                message = f"Cleared cache for {service_name} service"
            else:
                unified_service_manager.clear_cache()
                message = "Cleared cache for all services"
            
            return Response({
                'message': message,
                'timestamp': datetime.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return Response({
                'error': 'Failed to clear cache',
                'details': str(e),
                'timestamp': datetime.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def metrics(self, request):
        """Get detailed performance metrics"""
        try:
            time_window = int(request.query_params.get('time_window', 3600))  # Default 1 hour
            
            metrics = performance_optimizer.monitor.get_metrics(time_window=time_window)
            
            # Calculate summary statistics
            summary_stats = {}
            for metric_name in metrics:
                summary_stats[metric_name] = performance_optimizer.monitor.get_summary_stats(
                    metric_name, time_window
                )
            
            result = {
                'metrics': metrics,
                'summary_stats': summary_stats,
                'time_window': time_window,
                'timestamp': datetime.now().isoformat()
            }
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Metrics error: {e}")
            return Response({
                'error': 'Failed to get metrics',
                'details': str(e),
                'timestamp': datetime.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Health check endpoints
def simple_health_check(request):
    """Simple health check endpoint"""
    return JsonResponse({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


def readiness_check(request):
    """Readiness check endpoint"""
    try:
        # Check if services are ready
        service_status = unified_service_manager.get_service_status()
        
        all_healthy = all(
            service.get('status') == 'healthy' 
            for service in service_status['services'].values()
        )
        
        if all_healthy:
            return JsonResponse({
                'status': 'ready',
                'services': service_status,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return JsonResponse({
                'status': 'not_ready',
                'services': service_status,
                'timestamp': datetime.now().isoformat()
            }, status=503)
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, status=503)


def liveness_check(request):
    """Liveness check endpoint"""
    return JsonResponse({
        'status': 'alive',
        'timestamp': datetime.now().isoformat()
    })







