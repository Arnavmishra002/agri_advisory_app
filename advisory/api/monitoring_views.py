#!/usr/bin/env python3
"""
Monitoring API Views
Provides endpoints for system monitoring, performance metrics, and health checks
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import logging

from ..monitoring.performance_monitor import performance_monitor, get_performance_summary
from ..middleware.rate_limiting import get_rate_limit_status, reset_rate_limits

logger = logging.getLogger(__name__)


class MonitoringViewSet(viewsets.ViewSet):
    """Monitoring endpoints for system health and performance"""
    
    permission_classes = [AllowAny]  # Allow access for health checks
    
    @action(detail=False, methods=['get'])
    def health(self, request):
        """
        Basic health check endpoint
        Returns simple OK status
        """
        try:
            return Response({
                'status': 'healthy',
                'timestamp': performance_monitor.get_system_health_status()['timestamp'],
                'message': 'Krishimitra AI is running normally'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return Response({
                'status': 'error',
                'message': 'Health check failed',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def system_health(self, request):
        """
        Detailed system health status
        Returns comprehensive system metrics
        """
        try:
            health_status = performance_monitor.get_system_health_status()
            return Response(health_status, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"System health check failed: {e}")
            return Response({
                'status': 'error',
                'message': 'System health check failed',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def performance_summary(self, request):
        """
        Get API performance summary
        Query parameters:
        - hours: Number of hours to look back (default: 24)
        """
        try:
            hours = int(request.GET.get('hours', 24))
            summary = performance_monitor.get_api_performance_summary(hours)
            return Response(summary, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Performance summary failed: {e}")
            return Response({
                'error': 'Failed to get performance summary',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def metrics(self, request):
        """
        Get comprehensive metrics
        Returns both API and system metrics
        """
        try:
            metrics = get_performance_summary()
            return Response(metrics, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Metrics retrieval failed: {e}")
            return Response({
                'error': 'Failed to get metrics',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def record_activity(self, request):
        """
        Record user activity for analytics
        Body: {
            "user_id": "user123",
            "activity_type": "api_call",
            "details": {"endpoint": "/api/chatbot/", "query": "crop recommendation"}
        }
        """
        try:
            user_id = request.data.get('user_id', 'anonymous')
            activity_type = request.data.get('activity_type', 'unknown')
            details = request.data.get('details', {})
            
            performance_monitor.record_user_activity(user_id, activity_type, details)
            
            return Response({
                'status': 'success',
                'message': 'Activity recorded successfully'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Activity recording failed: {e}")
            return Response({
                'error': 'Failed to record activity',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RateLimitViewSet(viewsets.ViewSet):
    """Rate limiting management endpoints"""
    
    permission_classes = [AllowAny]  # Allow anonymous access for rate limit status
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """
        Get rate limit status for the current user
        """
        try:
            # Get client identifier
            client_ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
            user_id = request.user.id if request.user.is_authenticated else None
            
            # Use user ID if available, otherwise use IP
            client_id = f"user_{user_id}" if user_id else f"ip_{client_ip}"
            
            status_info = get_rate_limit_status(client_id)
            
            return Response({
                'client_id': client_id,
                'rate_limits': status_info,
                'timestamp': performance_monitor.get_system_health_status()['timestamp']
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Rate limit status failed: {e}")
            return Response({
                'error': 'Failed to get rate limit status',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def reset(self, request):
        """
        Reset rate limits for a client (admin function)
        Body: {
            "client_id": "user_123" or "ip_192.168.1.1"
        }
        """
        try:
            # Check if user has admin permissions
            if not (request.user.is_staff or request.user.is_superuser):
                return Response({
                    'error': 'Insufficient permissions'
                }, status=status.HTTP_403_FORBIDDEN)
            
            client_id = request.data.get('client_id')
            if not client_id:
                return Response({
                    'error': 'client_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            reset_rate_limits(client_id)
            
            return Response({
                'status': 'success',
                'message': f'Rate limits reset for {client_id}'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Rate limit reset failed: {e}")
            return Response({
                'error': 'Failed to reset rate limits',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
def simple_health_check(request):
    """
    Simple health check endpoint for load balancers
    No authentication required
    """
    try:
        return JsonResponse({
            'status': 'healthy',
            'service': 'Krishimitra AI',
            'timestamp': performance_monitor.get_system_health_status()['timestamp']
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)


@csrf_exempt
def readiness_check(request):
    """
    Readiness check endpoint for Kubernetes
    Checks if the service is ready to accept requests
    """
    try:
        # Check database connectivity
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Check cache connectivity
        from django.core.cache import cache
        cache.set('readiness_check', 'ok', 10)
        cache.get('readiness_check')
        
        return JsonResponse({
            'status': 'ready',
            'checks': {
                'database': 'ok',
                'cache': 'ok'
            },
            'timestamp': performance_monitor.get_system_health_status()['timestamp']
        })
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JsonResponse({
            'status': 'not_ready',
            'error': str(e)
        }, status=503)


@csrf_exempt
def liveness_check(request):
    """
    Liveness check endpoint for Kubernetes
    Checks if the service is alive and responding
    """
    try:
        # Basic system metrics
        system_health = performance_monitor.get_system_health_status()
        
        return JsonResponse({
            'status': 'alive',
            'uptime_seconds': system_health.get('uptime_seconds', 0),
            'timestamp': system_health['timestamp']
        })
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        return JsonResponse({
            'status': 'dead',
            'error': str(e)
        }, status=500)
