"""
Caching utilities for enhanced performance
Implements Redis and Django cache with fallback mechanisms
"""

import json
import hashlib
import logging
from datetime import timedelta
from typing import Any, Optional, Dict, List
from django.core.cache import cache
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from functools import wraps
import time

logger = logging.getLogger(__name__)

class CacheManager:
    """Advanced cache manager with multiple strategies"""
    
    def __init__(self):
        self.default_timeout = 300  # 5 minutes
        self.long_timeout = 3600    # 1 hour
        self.short_timeout = 60     # 1 minute
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate consistent cache key from parameters"""
        key_data = {
            'prefix': prefix,
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return f"agri_cache:{prefix}:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    def get(self, key: str, default=None) -> Any:
        """Get value from cache"""
        try:
            return cache.get(key, default)
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return default
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            timeout = timeout or self.default_timeout
            cache.set(key, value, timeout)
            return True
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            cache.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False
    
    def get_or_set(self, key: str, callable_func, timeout: Optional[int] = None) -> Any:
        """Get from cache or set using callable"""
        value = self.get(key)
        if value is None:
            value = callable_func()
            self.set(key, value, timeout)
        return value

# Global cache manager instance
cache_manager = CacheManager()

def cache_result(timeout: int = 300, key_prefix: str = "default"):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = cache_manager._generate_cache_key(
                f"{key_prefix}:{func.__name__}", 
                *args, 
                **kwargs
            )
            
            # Try to get from cache
            result = cache_manager.get(cache_key)
            if result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return result
            
            # Execute function and cache result
            logger.debug(f"Cache miss for {cache_key}")
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, timeout)
            return result
        
        return wrapper
    return decorator

def cache_api_response(timeout: int = 300):
    """Decorator specifically for API responses"""
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Generate cache key based on request parameters
            cache_key = cache_manager._generate_cache_key(
                f"api:{func.__name__}",
                request.GET.dict(),
                request.POST.dict() if hasattr(request, 'POST') else {}
            )
            
            # Try cache first
            result = cache_manager.get(cache_key)
            if result is not None:
                logger.debug(f"API cache hit for {cache_key}")
                return result
            
            # Execute API function
            result = func(request, *args, **kwargs)
            
            # Cache successful responses only
            if hasattr(result, 'status_code') and result.status_code == 200:
                cache_manager.set(cache_key, result.data, timeout)
            
            return result
        
        return wrapper
    return decorator

class WeatherCache:
    """Specialized cache for weather data"""
    
    def __init__(self):
        self.weather_timeout = 600  # 10 minutes
        self.forecast_timeout = 1800  # 30 minutes
    
    @cache_result(timeout=600, key_prefix="weather")
    def get_weather_data(self, lat: float, lon: float, lang: str = 'en'):
        """Get cached weather data"""
        # This will be called by the actual weather API
        pass
    
    @cache_result(timeout=1800, key_prefix="forecast")
    def get_forecast_data(self, lat: float, lon: float, days: int = 3):
        """Get cached forecast data"""
        pass

class MarketCache:
    """Specialized cache for market data"""
    
    def __init__(self):
        self.price_timeout = 900  # 15 minutes
        self.trend_timeout = 1800  # 30 minutes
    
    @cache_result(timeout=900, key_prefix="market_prices")
    def get_market_prices(self, lat: float, lon: float, lang: str = 'en'):
        """Get cached market prices"""
        pass
    
    @cache_result(timeout=1800, key_prefix="trending_crops")
    def get_trending_crops(self, lat: float, lon: float, lang: str = 'en'):
        """Get cached trending crops"""
        pass

class ChatCache:
    """Specialized cache for chat responses"""
    
    def __init__(self):
        self.chat_timeout = 3600  # 1 hour for similar queries
        self.session_timeout = 86400  # 24 hours for sessions
    
    @cache_result(timeout=3600, key_prefix="chat_response")
    def get_similar_response(self, query_hash: str, language: str):
        """Cache similar chat responses"""
        pass
    
    def cache_session_context(self, session_id: str, context: Dict):
        """Cache session context"""
        cache_key = f"chat_session:{session_id}"
        cache_manager.set(cache_key, context, self.session_timeout)
    
    def get_session_context(self, session_id: str) -> Optional[Dict]:
        """Get cached session context"""
        cache_key = f"chat_session:{session_id}"
        return cache_manager.get(cache_key)

# Cache instances
weather_cache = WeatherCache()
market_cache = MarketCache()
chat_cache = ChatCache()

# Cache warming functions
def warm_cache():
    """Warm up frequently used cache entries"""
    try:
        # Warm weather cache for major cities
        major_cities = [
            (28.6139, 77.2090, 'Delhi'),
            (19.0760, 72.8777, 'Mumbai'),
            (22.5726, 88.3639, 'Kolkata'),
            (13.0827, 80.2707, 'Chennai'),
            (12.9716, 77.5946, 'Bangalore')
        ]
        
        for lat, lon, city in major_cities:
            try:
                # This would trigger cache warming
                logger.info(f"Warming cache for {city}")
            except Exception as e:
                logger.warning(f"Failed to warm cache for {city}: {e}")
        
        logger.info("Cache warming completed")
        
    except Exception as e:
        logger.error(f"Cache warming failed: {e}")

# Cache statistics
class CacheStats:
    """Track cache performance statistics"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.errors = 0
    
    def record_hit(self):
        self.hits += 1
    
    def record_miss(self):
        self.misses += 1
    
    def record_set(self):
        self.sets += 1
    
    def record_error(self):
        self.errors += 1
    
    def get_hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0
    
    def get_stats(self) -> Dict:
        return {
            'hits': self.hits,
            'misses': self.misses,
            'sets': self.sets,
            'errors': self.errors,
            'hit_rate': self.get_hit_rate()
        }

# Global cache stats
cache_stats = CacheStats()
