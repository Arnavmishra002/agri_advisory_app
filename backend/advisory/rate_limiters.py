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
    """Simple rate limiter with token bucket algorithm, cache-backed for multi-process safety."""
    
    def __init__(self, max_calls: int, time_window: int):
        """
        Args:
            max_calls: Maximum number of calls allowed
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self._calls: Dict[str, list] = {}
    
    def _get_history(self, key: str) -> list:
        try:
            from django.core.cache import cache
            cache_key = f"rate_limit:{key}"
            history = cache.get(cache_key)
            if history is not None:
                return history
        except Exception:
            pass
        return self._calls.get(key, [])
        
    def _save_history(self, key: str, history: list) -> None:
        try:
            from django.core.cache import cache
            cache_key = f"rate_limit:{key}"
            cache.set(cache_key, history, timeout=self.time_window)
        except Exception:
            pass
        self._calls[key] = history

    def is_allowed(self, key: str) -> bool:
        """Check if call is allowed for given key"""
        now = time.time()
        history = self._get_history(key)
        
        # Remove old calls outside time window
        history = [
            call_time for call_time in history
            if now - call_time < self.time_window
        ]
        
        # Check if under limit
        if len(history) < self.max_calls:
            history.append(now)
            self._save_history(key, history)
            return True
        
        return False
    
    def wait_time(self, key: str) -> float:
        """Get wait time in seconds before next call is allowed"""
        history = self._get_history(key)
        if not history:
            return 0.0
        
        oldest_call = min(history)
        wait = self.time_window - (time.time() - oldest_call)
        return max(0.0, wait)

# Predefined rate limiters for external APIs
nominatim_limiter = RateLimiter(max_calls=1, time_window=1)  # 1 req/sec
open_meteo_limiter = RateLimiter(max_calls=10000, time_window=86400)  # 10k req/day
government_api_limiter = RateLimiter(max_calls=100, time_window=60)  # 100 req/min

def rate_limit(limiter: RateLimiter, key_func=None):
    """
    Decorator to apply rate limiting to functions.

    If the rate limit is exceeded the function is skipped and a RateLimitError
    is raised immediately — the decorator NEVER sleeps a thread, which would
    block gunicorn workers for up to the full time-window.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = func.__name__

            # Check rate limit — fail fast, never sleep
            if not limiter.is_allowed(key):
                wait = limiter.wait_time(key)
                logger.warning(
                    f"Rate limit exceeded for {func.__name__}. "
                    f"Next slot in {wait:.2f}s"
                )
                raise Exception(
                    f"Rate limit exceeded for {func.__name__}. "
                    f"Retry after {wait:.2f}s"
                )

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
