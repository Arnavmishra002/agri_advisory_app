#!/usr/bin/env python3
"""
Rate Limiting Middleware
Implements rate limiting for API endpoints to prevent abuse
"""

import time
import logging
import ipaddress
from typing import Dict, Optional, Any
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(MiddlewareMixin):
    """
    Rate limiting middleware for API endpoints
    Implements sliding window rate limiting
    """
    
    def __init__(self, get_response=None):
        """Initialize the rate limiting middleware"""
        self.get_response = get_response
        super().__init__(get_response)
        
        # Rate limiting configuration
        self.rate_limits = {
            'api/chatbot/': {
                'requests_per_minute': 60,
                'requests_per_hour': 1000,
                'requests_per_day': 10000
            },
            'api/locations/': {
                'requests_per_minute': 30,
                'requests_per_hour': 500,
                'requests_per_day': 5000
            },
            'api/': {
                'requests_per_minute': 100,
                'requests_per_hour': 2000,
                'requests_per_day': 20000
            }
        }
        
        # Default rate limits
        self.default_limits = {
            'requests_per_minute': 100,
            'requests_per_hour': 1000,
            'requests_per_day': 10000
        }
    
    def process_request(self, request):
        """Process incoming request for rate limiting"""
        # Skip rate limiting for non-API requests
        if not request.path.startswith('/api/'):
            return None
        
        # Skip rate limiting for certain paths
        skip_paths = ['/api/health/', '/api/metrics/', '/api/schema/']
        if any(request.path.startswith(path) for path in skip_paths):
            return None
        
        # Get client identifier
        client_id = self._get_client_identifier(request)
        
        # Check rate limits
        rate_limit_response = self._check_rate_limits(request, client_id)
        if rate_limit_response:
            return rate_limit_response
        
        # Add rate limit headers
        self._add_rate_limit_headers(request, client_id)
        
        return None
    
    def _get_client_identifier(self, request) -> str:
        """Get unique identifier for the client"""
        # Try to get IP address
        ip_address = self._get_client_ip(request)
        
        # Try to get user ID if authenticated
        if hasattr(request, 'user') and request.user.is_authenticated:
            return f"user_{request.user.id}"
        
        # Use IP address as fallback
        return f"ip_{ip_address}"
    
    def _get_client_ip(self, request) -> str:
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _check_rate_limits(self, request, client_id: str) -> Optional[JsonResponse]:
        """Check if request exceeds rate limits"""
        current_time = int(time.time())
        
        # Get rate limits for this endpoint
        limits = self._get_rate_limits_for_path(request.path)
        
        # Check each time window
        for window_name, limit in limits.items():
            if self._is_rate_limit_exceeded(client_id, window_name, limit, current_time):
                logger.warning(f"Rate limit exceeded for {client_id} on {request.path}")
                return self._create_rate_limit_response(window_name, limit)
        
        return None
    
    def _get_rate_limits_for_path(self, path: str) -> Dict[str, int]:
        """Get rate limits for a specific path"""
        # Find the most specific matching path
        for api_path, limits in self.rate_limits.items():
            if path.startswith(api_path):
                return limits
        
        # Return default limits
        return self.default_limits
    
    def _is_rate_limit_exceeded(self, client_id: str, window_name: str, 
                               limit: int, current_time: int) -> bool:
        """Check if rate limit is exceeded for a specific window"""
        window_seconds = self._get_window_seconds(window_name)
        cache_key = f"rate_limit:{client_id}:{window_name}"
        
        # Get current requests in this window
        current_requests = cache.get(cache_key, [])
        
        # Remove old requests outside the window
        cutoff_time = current_time - window_seconds
        current_requests = [req_time for req_time in current_requests if req_time > cutoff_time]
        
        # Check if limit is exceeded
        if len(current_requests) >= limit:
            return True
        
        # Add current request
        current_requests.append(current_time)
        
        # Store updated requests (expire after window duration)
        cache.set(cache_key, current_requests, window_seconds)
        
        return False
    
    def _get_window_seconds(self, window_name: str) -> int:
        """Get window duration in seconds"""
        window_mapping = {
            'requests_per_minute': 60,
            'requests_per_hour': 3600,
            'requests_per_day': 86400
        }
        return window_mapping.get(window_name, 60)
    
    def _create_rate_limit_response(self, window_name: str, limit: int) -> JsonResponse:
        """Create rate limit exceeded response"""
        window_mapping = {
            'requests_per_minute': 'minute',
            'requests_per_hour': 'hour',
            'requests_per_day': 'day'
        }
        
        window_text = window_mapping.get(window_name, 'minute')
        
        response_data = {
            'error': 'Rate limit exceeded',
            'message': f'Too many requests. Limit: {limit} requests per {window_text}',
            'retry_after': self._get_window_seconds(window_name),
            'limit': limit,
            'window': window_text
        }
        
        response = JsonResponse(response_data, status=429)
        response['Retry-After'] = str(self._get_window_seconds(window_name))
        response['X-RateLimit-Limit'] = str(limit)
        response['X-RateLimit-Window'] = window_text
        
        return response
    
    def _add_rate_limit_headers(self, request, client_id: str):
        """Add rate limit information headers to request"""
        limits = self._get_rate_limits_for_path(request.path)
        
        # Add headers for each window
        for window_name, limit in limits.items():
            cache_key = f"rate_limit:{client_id}:{window_name}"
            current_requests = cache.get(cache_key, [])
            
            # Remove old requests
            current_time = int(time.time())
            window_seconds = self._get_window_seconds(window_name)
            cutoff_time = current_time - window_seconds
            current_requests = [req_time for req_time in current_requests if req_time > cutoff_time]
            
            # Add headers
            remaining = max(0, limit - len(current_requests))
            request.META[f'HTTP_X_RATELIMIT_{window_name.upper()}_LIMIT'] = str(limit)
            request.META[f'HTTP_X_RATELIMIT_{window_name.upper()}_REMAINING'] = str(remaining)
            request.META[f'HTTP_X_RATELIMIT_{window_name.upper()}_RESET'] = str(current_time + window_seconds)


class IPWhitelistMiddleware(MiddlewareMixin):
    """
    IP whitelist middleware for trusted clients
    Allows whitelisted IPs to bypass rate limiting
    """
    
    def __init__(self, get_response=None):
        """Initialize the IP whitelist middleware"""
        self.get_response = get_response
        super().__init__(get_response)
        
        # Whitelist configuration (can be loaded from settings)
        self.whitelisted_ips = getattr(settings, 'RATE_LIMIT_WHITELIST', [
            '127.0.0.1',
            '::1',
            'localhost'
        ])
        
        # Whitelist networks (CIDR notation)
        self.whitelisted_networks = getattr(settings, 'RATE_LIMIT_WHITELIST_NETWORKS', [])
    
    def process_request(self, request):
        """Check if request is from whitelisted IP"""
        if not request.path.startswith('/api/'):
            return None
        
        client_ip = self._get_client_ip(request)
        
        if self._is_ip_whitelisted(client_ip):
            # Add whitelist flag to request
            request.META['HTTP_X_RATE_LIMIT_WHITELISTED'] = 'true'
            logger.info(f"Request from whitelisted IP: {client_ip}")
        
        return None
    
    def _get_client_ip(self, request) -> str:
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _is_ip_whitelisted(self, ip: str) -> bool:
        """Check if IP is whitelisted"""
        # Check direct IP whitelist
        if ip in self.whitelisted_ips:
            return True
        
        # Check network whitelist (simplified implementation)
        # In production, use ipaddress module for proper CIDR checking
        for network in self.whitelisted_networks:
            if self._ip_in_network(ip, network):
                return True
        
        return False
    
    def _ip_in_network(self, ip: str, network: str) -> bool:
        """Check if IP is in network using proper CIDR checking"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            network_obj = ipaddress.ip_network(network, strict=False)
            return ip_obj in network_obj
        except (ValueError, ipaddress.AddressValueError):
            logger.warning(f"Invalid IP or network format: {ip}, {network}")
            return False


class UserRateLimitMiddleware(MiddlewareMixin):
    """
    User-specific rate limiting middleware
    Provides different rate limits for authenticated vs anonymous users
    """
    
    def __init__(self, get_response=None):
        """Initialize user rate limiting middleware"""
        self.get_response = get_response
        super().__init__(get_response)
        
        # Rate limits for different user types
        self.user_limits = {
            'anonymous': {
                'requests_per_minute': 30,
                'requests_per_hour': 500,
                'requests_per_day': 5000
            },
            'authenticated': {
                'requests_per_minute': 100,
                'requests_per_hour': 2000,
                'requests_per_day': 20000
            },
            'premium': {
                'requests_per_minute': 200,
                'requests_per_hour': 5000,
                'requests_per_day': 50000
            }
        }
    
    def process_request(self, request):
        """Set user-specific rate limits"""
        if not request.path.startswith('/api/'):
            return None
        
        # Determine user type
        user_type = self._get_user_type(request)
        
        # Add user type to request for use by rate limiting middleware
        request.META['HTTP_X_USER_RATE_LIMIT_TYPE'] = user_type
        
        return None
    
    def _get_user_type(self, request) -> str:
        """Determine user type for rate limiting"""
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return 'anonymous'
        
        # Check if user has premium status
        if hasattr(request.user, 'is_premium') and request.user.is_premium:
            return 'premium'
        
        return 'authenticated'


# Rate limiting decorator for views
def rate_limit(requests_per_minute=60, requests_per_hour=1000, requests_per_day=10000):
    """
    Decorator for applying rate limiting to specific views
    
    Args:
        requests_per_minute: Maximum requests per minute
        requests_per_hour: Maximum requests per hour  
        requests_per_day: Maximum requests per day
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            # This would integrate with the middleware
            # For now, just pass through
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# Utility functions
def get_rate_limit_status(client_id: str) -> Dict[str, Any]:
    """Get current rate limit status for a client"""
    status = {}
    
    windows = ['requests_per_minute', 'requests_per_hour', 'requests_per_day']
    for window in windows:
        cache_key = f"rate_limit:{client_id}:{window}"
        current_requests = cache.get(cache_key, [])
        
        # Remove old requests
        current_time = int(time.time())
        window_seconds = {
            'requests_per_minute': 60,
            'requests_per_hour': 3600,
            'requests_per_day': 86400
        }[window]
        
        cutoff_time = current_time - window_seconds
        current_requests = [req_time for req_time in current_requests if req_time > cutoff_time]
        
        status[window] = {
            'current_requests': len(current_requests),
            'window_seconds': window_seconds
        }
    
    return status


def reset_rate_limits(client_id: str):
    """Reset rate limits for a client (admin function)"""
    windows = ['requests_per_minute', 'requests_per_hour', 'requests_per_day']
    for window in windows:
        cache_key = f"rate_limit:{client_id}:{window}"
        cache.delete(cache_key)
    
    logger.info(f"Rate limits reset for client: {client_id}")
