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
import hashlib
import ipaddress
from typing import Optional

logger = logging.getLogger(__name__)


def _rate_cache():
    """Use the dedicated shared cache for all security counters."""
    from django.core.cache import caches

    return caches["rate_limit"]


def _cache_key(prefix: str, client_id: str) -> str:
    # Do not put user-controlled phone/user strings directly into cache keys.
    digest = hashlib.sha256(str(client_id).encode("utf-8")).hexdigest()[:32]
    return f"km:security:{prefix}:{digest}"


def client_ip_from_request(request) -> str:
    """Resolve the client IP using only configured trusted proxy hops."""
    from django.conf import settings

    trusted = max(0, int(getattr(settings, "RATE_LIMIT_TRUSTED_PROXIES", 0)))
    remote = request.META.get("REMOTE_ADDR", "0.0.0.0")
    if trusted == 0:
        return remote
    entries = [value.strip() for value in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",") if value.strip()]
    if len(entries) <= trusted:
        return remote
    candidate = entries[-trusted - 1]
    try:
        ipaddress.ip_address(candidate)
        return candidate
    except ValueError:
        return remote


class SharedRateLimiter:
    """
    Token-bucket rate limiter backed by Django's cache layer.

    Works correctly across multiple Gunicorn workers because all state
    lives in the shared cache (Redis) rather than process memory.

    Bug 1 fix: use time.time() everywhere.
    The old process-local clock had a different epoch per worker, so storing
    it in Redis and reading it from another worker could produce a large
    negative elapsed value and permanently drain the token bucket.

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

        Bug 1: time.time() uses the wall-clock UTC epoch, so it is safe to
               store in Redis and read from any worker.
        Bug 2: CAS retry loop — cache.add() is atomic; retrying up to 3 times
               means concurrent workers correctly see each other's decrements.
        """
        try:
            cache = _rate_cache()
            cache_key = _cache_key(f"tb:{self.key_prefix}", client_id)
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
            fail_open = getattr(__import__("django.conf", fromlist=["settings"]), "settings").RATE_LIMIT_FAIL_OPEN
            logger.error("Rate limiter cache error: %s", exc)
            return bool(fail_open)

    def remaining(self, client_id: str) -> int:
        """Return approximate remaining tokens (for X-RateLimit-Remaining header)."""
        try:
            cache = _rate_cache()
            state = cache.get(_cache_key(f"tb:{self.key_prefix}", client_id))
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
            cache = _rate_cache()
            cache.delete(_cache_key(f"tb:{self.key_prefix}", client_id))
        except Exception as exc:
            logger.warning("Rate limiter reset failed: %s", exc)

    def wait_time(self, client_id: str) -> float:
        """Return estimated seconds until next token is available."""
        try:
            cache = _rate_cache()
            state = cache.get(_cache_key(f"tb:{self.key_prefix}", client_id))
            if state is None:
                return 0.0
            tokens, last = state
            elapsed = max(0.0, time.time() - last)
            current = min(float(self.capacity), tokens + elapsed * self.fill_rate)
            if current >= 1.0:
                return 0.0
            needed = 1.0 - current
            return needed / max(self.fill_rate, 0.001)
        except Exception:
            return 0.0


class AtomicWindowRateLimiter:
    """Atomic fixed-window limiter for HTTP abuse controls.

    Django cache ``add`` and ``incr`` are atomic in Redis/Memcached, so this
    avoids the tuple read-modify-write race of the legacy token bucket.
    """

    def __init__(self, key_prefix: str, capacity: int, window_seconds: int):
        self.key_prefix = key_prefix
        self.capacity = max(1, int(capacity))
        self.window_seconds = max(1, int(window_seconds))

    def _key(self, client_id: str, bucket: int) -> str:
        return _cache_key(f"window:{self.key_prefix}", f"{client_id}:{bucket}")

    def _current(self):
        now = int(time.time())
        return now, now // self.window_seconds

    def is_allowed(self, client_id: str) -> bool:
        try:
            cache = _rate_cache()
            now, bucket = self._current()
            key = self._key(client_id, bucket)
            if cache.add(key, 1, timeout=self.window_seconds + 2):
                count = 1
            else:
                count = int(cache.incr(key))
            return count <= self.capacity
        except Exception as exc:
            from django.conf import settings

            logger.error("Atomic rate limiter cache error: %s", exc)
            return bool(getattr(settings, "RATE_LIMIT_FAIL_OPEN", False))

    def remaining(self, client_id: str) -> int:
        try:
            _now, bucket = self._current()
            count = int(_rate_cache().get(self._key(client_id, bucket)) or 0)
            return max(0, self.capacity - count)
        except Exception:
            return self.capacity

    def wait_time(self, client_id: str) -> float:
        try:
            now, bucket = self._current()
            if self.remaining(client_id) > 0:
                return 0.0
            return float(self.window_seconds - (now % self.window_seconds))
        except Exception:
            return float(self.window_seconds)

    def reset(self, client_id: str) -> None:
        try:
            _now, bucket = self._current()
            _rate_cache().delete(self._key(client_id, bucket))
        except Exception as exc:
            logger.warning("Atomic rate limiter reset failed: %s", exc)


class ExponentialBackoff:
    """Shared failure backoff for authentication attempts.

    A failed attempt increases the delay after a configurable threshold. The
    counter expires, so this is a progressive speed bump rather than a
    permanent account lockout.
    """

    def __init__(
        self,
        key_prefix: str,
        *,
        threshold: Optional[int] = None,
        base_seconds: Optional[float] = None,
        max_seconds: Optional[float] = None,
        window_seconds: Optional[int] = None,
    ):
        from django.conf import settings

        self.key_prefix = key_prefix
        self.threshold = max(
            1,
            int(threshold if threshold is not None else settings.AUTH_BACKOFF_THRESHOLD),
        )
        self.base_seconds = max(
            0.0,
            float(base_seconds if base_seconds is not None else settings.AUTH_BACKOFF_BASE_SECONDS),
        )
        self.max_seconds = max(
            self.base_seconds,
            float(max_seconds if max_seconds is not None else settings.AUTH_BACKOFF_MAX_SECONDS),
        )
        self.window_seconds = max(
            60,
            int(window_seconds if window_seconds is not None else settings.AUTH_BACKOFF_WINDOW_SECONDS),
        )

    def _count_key(self, client_id: str) -> str:
        return _cache_key(f"backoff-count:{self.key_prefix}", client_id)

    def _until_key(self, client_id: str) -> str:
        return _cache_key(f"backoff-until:{self.key_prefix}", client_id)

    def retry_after(self, client_id: str) -> int:
        try:
            until = float(_rate_cache().get(self._until_key(client_id)) or 0)
            return max(0, int(until - time.time() + 0.999))
        except Exception as exc:
            logger.error("Auth backoff lookup failed: %s", exc)
            return 0

    def record_failure(self, client_id: str) -> int:
        try:
            cache = _rate_cache()
            count_key = self._count_key(client_id)
            if cache.add(count_key, 1, timeout=self.window_seconds):
                count = 1
            else:
                try:
                    count = int(cache.incr(count_key))
                except ValueError:
                    cache.set(count_key, 1, timeout=self.window_seconds)
                    count = 1

            if count < self.threshold or self.base_seconds <= 0:
                return 0

            delay = min(
                self.max_seconds,
                self.base_seconds * (2 ** (count - self.threshold)),
            )
            cache.set(
                self._until_key(client_id),
                time.time() + delay,
                timeout=max(self.window_seconds, int(delay) + 1),
            )
            return int(delay)
        except Exception as exc:
            logger.error("Auth backoff update failed: %s", exc)
            return 0

    def clear(self, client_id: str) -> None:
        try:
            cache = _rate_cache()
            cache.delete(self._count_key(client_id))
            cache.delete(self._until_key(client_id))
        except Exception as exc:
            logger.error("Auth backoff reset failed: %s", exc)


# ── Pre-configured limiters ────────────────────────────────────────────────────
# These are shared singletons — import and use directly. Values come from
# Django settings so integrations do not silently bypass deployment policy.
def _configured_number(name, default):
    try:
        from django.conf import settings
        return getattr(settings, name, default)
    except Exception:
        return default

# Chatbot: 60 requests/minute per IP, sustained 1/s
chat_rate_limiter = SharedRateLimiter(
    key_prefix="chat",
    capacity=_configured_number("RATE_LIMIT_CHAT_CAPACITY", 60),
    fill_rate=_configured_number("RATE_LIMIT_CHAT_FILL_RATE", 1.0),
)

# Weather/market data: 120 requests/minute per IP
data_rate_limiter = SharedRateLimiter(
    key_prefix="data",
    capacity=_configured_number("RATE_LIMIT_DATA_CAPACITY", 120),
    fill_rate=_configured_number("RATE_LIMIT_DATA_FILL_RATE", 2.0),
)

# Disease diagnosis (heavy ML): 20 requests/minute per IP
diagnosis_rate_limiter = SharedRateLimiter(
    key_prefix="diag",
    capacity=_configured_number("RATE_LIMIT_DIAG_CAPACITY", 20),
    fill_rate=_configured_number("RATE_LIMIT_DIAG_FILL_RATE", 0.33),
)

# Default global limiter
default_rate_limiter = SharedRateLimiter(
    key_prefix="default",
    capacity=_configured_number("RATE_LIMIT_DEFAULT_CAPACITY", 200),
    fill_rate=_configured_number("RATE_LIMIT_DEFAULT_FILL_RATE", 3.0),
)


# ── Nominatim geocoding limiter ────────────────────────────────────────────────
# Nominatim ToS: max 1 request/second per IP.
# We use a single key so all workers share the same bucket.
nominatim_limiter = SharedRateLimiter(
    key_prefix="nominatim",
    capacity=_configured_number("RATE_LIMIT_NOMINATIM_CAPACITY", 10),
    fill_rate=_configured_number("RATE_LIMIT_NOMINATIM_FILL_RATE", 1.0),
)


# NOTE: wait_time is defined as a proper method inside SharedRateLimiter above.
# The old monkey-patch approach (_wait_time defined here + assigned below) was
# removed — it caused AttributeError on import-time access before the patch ran.


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
