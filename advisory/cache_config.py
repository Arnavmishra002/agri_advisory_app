"""
Simple In-Memory Cache for Agri Advisory App
Provides caching for expensive operations without external dependencies
"""

import time
from typing import Any, Optional
from functools import wraps
import hashlib
import json

class SimpleCache:
    """Thread-safe in-memory cache with TTL support"""
    
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key in self._cache:
            timestamp = self._timestamps.get(key, 0)
            if time.time() < timestamp:
                return self._cache[key]
            else:
                # Expired, remove
                self._cache.pop(key, None)
                self._timestamps.pop(key, None)
        return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """Set value in cache with TTL in seconds"""
        self._cache[key] = value
        self._timestamps[key] = time.time() + ttl
    
    def delete(self, key: str):
        """Delete value from cache"""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
    
    def clear(self):
        """Clear all cache"""
        self._cache.clear()
        self._timestamps.clear()

# Global cache instance
cache = SimpleCache()

def cache_result(ttl: int = 3600, key_prefix: str = ""):
    """
    Decorator to cache function results
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [key_prefix or func.__name__]
            
            # Add args to key
            for arg in args:
                if isinstance(arg, (str, int, float, bool)):
                    key_parts.append(str(arg))
            
            # Add kwargs to key
            for k, v in sorted(kwargs.items()):
                if isinstance(v, (str, int, float, bool)):
                    key_parts.append(f"{k}={v}")
            
            # Create hash for cache key
            cache_key = hashlib.md5(
                json.dumps(key_parts, sort_keys=True).encode()
            ).hexdigest()
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator

# Predefined TTL constants
TTL_WEATHER = 30 * 60  # 30 minutes
TTL_MARKET_PRICES = 60 * 60  # 1 hour
TTL_CROP_RECOMMENDATIONS = 24 * 60 * 60  # 24 hours
TTL_LOCATION = 7 * 24 * 60 * 60  # 7 days
