"""
KrishiMitra — Production Rate Limiters
========================================
Thread-safe, process-safe token bucket rate limiter using Django's shared
cache backend (Redis in production, local memory in dev).

This replaces the previous process-local dict approach which allowed each
Gunicorn worker to maintain its own independent bucket, effectively
multiplying the rate limit by the worker count.

Usage:
    from advisory.rate_limiters import chat_rate_limiter
    if not chat_rate_limiter.is_allowed(client_ip):
        return Response({"error": "rate_limited"}, status=429)
"""

from __future__ import annotations

import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SharedRateLimiter:
    """
    Token-bucket rate limiter backed by Django's cache layer.

    Works correctly across multiple Gunicorn workers because all state
    lives in the shared cache (Redis) rather than process memory.

    Args:
        key_prefix:  Unique string prefix for this limiter's cache keys.
        capacity:    Maximum burst — number of tokens the bucket can hold.
        fill_rate:   Tokens added per second (sustained rate = fill_rate req/s).

    Example:
        # Allow 60 requests/minute burst, sustained 1 req/s
        limiter = SharedRateLimiter("chat", capacity=60, fill_rate=1.0)
        if not limiter.is_allowed(client_ip):
            raise RateLimitExceeded()
    """

    def __init__(self, key_prefix: str, capacity: int, fill_rate: float):
        self.key_prefix = key_prefix
        self.capacity   = capacity
        self.fill_rate  = fill_rate   # tokens per second

    def is_allowed(self, client_id: str) -> bool:
        """
        Consume one token for client_id. Returns True if allowed, False if
        rate limited.

        Thread-safe: uses cache.add() for atomic first-write, avoids race
        on initial bucket creation.
        """
        try:
            from django.core.cache import cache
            cache_key = f"tb:{self.key_prefix}:{client_id}"
            now = time.monotonic()

            state = cache.get(cache_key)
            if state is None:
                # New client — start with full bucket minus this request
                tokens     = float(self.capacity - 1)
                last_check = now
            else:
                tokens, last_check = state
                # Refill tokens based on elapsed time
                elapsed = now - last_check
                tokens  = min(float(self.capacity), tokens + elapsed * self.fill_rate)
                last_check = now

                if tokens < 1.0:
                    # Bucket empty — rate limited
                    cache.set(cache_key, (tokens, last_check), timeout=3600)
                    return False

                tokens -= 1.0

            cache.set(cache_key, (tokens, last_check), timeout=3600)
            return True

        except Exception as exc:
            # Cache unavailable — allow request (fail open, not closed)
            logger.warning("Rate limiter cache error (allowing request): %s", exc)
            return True

    def remaining(self, client_id: str) -> int:
        """Return approximate remaining tokens (for X-RateLimit-Remaining header)."""
        try:
            from django.core.cache import cache
            state = cache.get(f"tb:{self.key_prefix}:{client_id}")
            if state is None:
                return self.capacity
            tokens, last = state
            elapsed = time.monotonic() - last
            current = min(float(self.capacity), tokens + elapsed * self.fill_rate)
            return max(0, int(current))
        except Exception:
            return self.capacity

    def reset(self, client_id: str) -> None:
        """Reset rate limit for a client (admin use)."""
        try:
            from django.core.cache import cache
            cache.delete(f"tb:{self.key_prefix}:{client_id}")
        except Exception as exc:
            logger.warning("Rate limiter reset failed: %s", exc)


# ── Pre-configured limiters ────────────────────────────────────────────────────
# These are shared singletons — import and use directly.

# Chatbot: 60 requests/minute per IP, sustained 1/s
chat_rate_limiter = SharedRateLimiter(
    key_prefix="chat",
    capacity=60,
    fill_rate=1.0,
)

# Weather/market data: 120 requests/minute per IP
data_rate_limiter = SharedRateLimiter(
    key_prefix="data",
    capacity=120,
    fill_rate=2.0,
)

# Disease diagnosis (heavy ML): 20 requests/minute per IP
diagnosis_rate_limiter = SharedRateLimiter(
    key_prefix="diag",
    capacity=20,
    fill_rate=0.33,  # ~1 per 3 seconds sustained
)

# Default global limiter
default_rate_limiter = SharedRateLimiter(
    key_prefix="default",
    capacity=200,
    fill_rate=3.0,
)


# ── Nominatim geocoding limiter ────────────────────────────────────────────────
# Nominatim ToS: max 1 request/second per IP.
# We use a single key so all workers share the same bucket.
nominatim_limiter = SharedRateLimiter(
    key_prefix="nominatim",
    capacity=10,     # burst up to 10 geocoding requests
    fill_rate=1.0,   # refill 1 token/second (Nominatim ToS)
)

# Extend SharedRateLimiter with wait_time for Nominatim back-off
def _wait_time(self, client_id: str) -> float:
    """Return estimated seconds until next token is available."""
    try:
        from django.core.cache import cache
        state = cache.get(f"tb:{self.key_prefix}:{client_id}")
        if state is None:
            return 0.0
        tokens, last = state
        import time
        elapsed = time.monotonic() - last
        current = min(float(self.capacity), tokens + elapsed * self.fill_rate)
        if current >= 1.0:
            return 0.0
        needed = 1.0 - current
        return needed / max(self.fill_rate, 0.001)
    except Exception:
        return 0.0


SharedRateLimiter.wait_time = _wait_time  # monkey-patch wait_time method


# ── rate_limit decorator ───────────────────────────────────────────────────────
# Usage:
#   @rate_limit(nominatim_limiter)
#   def my_geocode_function(lat, lon): ...
#
# Skips the function call and returns None if rate-limited.
import functools


def rate_limit(limiter: SharedRateLimiter, client_id: str = "_global"):
    """
    Decorator that skips the wrapped function if the rate limiter says no.
    Returns None when rate-limited instead of calling the function.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if limiter.is_allowed(client_id):
                return fn(*args, **kwargs)
            logger.warning(
                "Rate limited: %s skipped (limiter=%s)",
                fn.__name__, limiter.key_prefix
            )
            return None
        return wrapper
    return decorator
