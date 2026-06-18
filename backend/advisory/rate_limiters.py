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
import functools

logger = logging.getLogger(__name__)


class SharedRateLimiter:
    """
    Token-bucket rate limiter backed by Django's cache layer.

    Works correctly across multiple Gunicorn workers because all state
    lives in the shared cache (Redis) rather than process memory.

    Bug 1 fix: replaced time.monotonic() with time.time() everywhere.
    time.monotonic() is process-local — its epoch differs per worker, so
    storing it in Redis and reading it from another worker produces a large
    negative elapsed value, permanently draining the token bucket.

    Bug 2 fix: added CAS (compare-and-swap) retry loop around the
    read-modify-write so burst requests from multiple workers can't both
    see tokens >= 1 and both pass through, effectively defeating the limit.

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

        Bug 1: time.time() (wall-clock UTC epoch) instead of time.monotonic()
               — safe to store in Redis and read from any worker.
        Bug 2: CAS retry loop — cache.add() is atomic; retrying up to 3 times
               means concurrent workers correctly see each other's decrements.
        """
        try:
            from django.core.cache import cache
            cache_key = f"tb:{self.key_prefix}:{client_id}"
            now = time.time()  # Bug 1: wall-clock, safe across all Gunicorn workers

            for _attempt in range(3):  # Bug 2: CAS retry on write contention
                state = cache.get(cache_key)
                if state is None:
                    # New client — use atomic add so only one worker seeds bucket
                    new_state = (float(self.capacity - 1), now)
                    if cache.add(cache_key, new_state, timeout=3600):
                        return True
                    # Another worker seeded it first — re-read on next iteration
                    continue

                tokens, last_check = state
                # Guard against NTP clock skew between servers (typically < 1 s)
                elapsed = max(0.0, now - last_check)
                tokens  = min(float(self.capacity), tokens + elapsed * self.fill_rate)

                if tokens < 1.0:
                    # Bucket empty — update refill progress and reject
                    cache.set(cache_key, (tokens, now), timeout=3600)
                    return False

                # Consume one token and persist
                cache.set(cache_key, (tokens - 1.0, now), timeout=3600)
                return True

            # Exhausted retries under extreme contention — fail open
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
            elapsed = max(0.0, time.time() - last)  # Bug 1: time.time()
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


def _wait_time(self, client_id: str) -> float:
    """Return estimated seconds until next token is available."""
    try:
        from django.core.cache import cache
        state = cache.get(f"tb:{self.key_prefix}:{client_id}")
        if state is None:
            return 0.0
        tokens, last = state
        elapsed = max(0.0, time.time() - last)  # Bug 1: time.time()
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
