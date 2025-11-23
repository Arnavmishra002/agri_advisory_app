"""
API Rate Limiter for External Services
Prevents quota exhaustion and implements exponential backoff
"""

import time
from typing import Dict, Optional
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple rate limiter with token bucket algorithm"""
    
    def __init__(self, max_calls: int, time_window: int):
        """
        Args:
            max_calls: Maximum number of calls allowed
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self._calls: Dict[str, list] = {}
    
    def is_allowed(self, key: str) -> bool:
        """Check if call is allowed for given key"""
        now = time.time()
        
        # Initialize if first call
        if key not in self._calls:
            self._calls[key] = []
        
        # Remove old calls outside time window
        self._calls[key] = [
            call_time for call_time in self._calls[key]
            if now - call_time < self.time_window
        ]
        
        # Check if under limit
        if len(self._calls[key]) < self.max_calls:
            self._calls[key].append(now)
            return True
        
        return False
    
    def wait_time(self, key: str) -> float:
        """Get wait time in seconds before next call is allowed"""
        if key not in self._calls or not self._calls[key]:
            return 0.0
        
        oldest_call = min(self._calls[key])
        wait = self.time_window - (time.time() - oldest_call)
        return max(0.0, wait)

# Predefined rate limiters for external APIs
nominatim_limiter = RateLimiter(max_calls=1, time_window=1)  # 1 req/sec
open_meteo_limiter = RateLimiter(max_calls=10000, time_window=86400)  # 10k req/day
government_api_limiter = RateLimiter(max_calls=100, time_window=60)  # 100 req/min

def rate_limit(limiter: RateLimiter, key_func=None):
    """
    Decorator to apply rate limiting to functions
    
    Args:
        limiter: RateLimiter instance to use
        key_func: Function to generate rate limit key from args
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = func.__name__
            
            # Check rate limit
            if not limiter.is_allowed(key):
                wait = limiter.wait_time(key)
                logger.warning(
                    f"Rate limit exceeded for {func.__name__}. "
                    f"Waiting {wait:.2f}s"
                )
                time.sleep(wait)
                # Retry after waiting
                if not limiter.is_allowed(key):
                    raise Exception(f"Rate limit exceeded for {func.__name__}")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

def exponential_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """
    Decorator to implement exponential backoff for retries
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (doubles each retry)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}). "
                            f"Retrying in {delay}s. Error: {e}"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts. "
                            f"Error: {e}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator
