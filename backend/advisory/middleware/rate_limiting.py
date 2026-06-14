#!/usr/bin/env python3
"""
Rate Limiting Middleware — Production-Ready Rewrite
====================================================
Bug 1 fix: O(N) list-per-request replaced with O(1) Redis INCR + bucket counter.
Bug 3 fix: Three overlapping middleware classes collapsed into one.
           IPWhitelistMiddleware and UserRateLimitMiddleware are kept as
           compatibility no-op stubs so the MIDDLEWARE list in settings.py
           requires zero changes.
Arch:      Uses the dedicated 'rate_limit' cache alias. Configure it as Redis
           in production (see settings.py CACHES block).
"""

import ipaddress
import logging
import time
from typing import Dict, Optional, Tuple

from django.conf import settings
from django.core.cache import caches
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


# ── Cache backend ────────────────────────────────────────────────────────────
def _get_rate_cache():
    """Return the 'rate_limit' cache, falling back to 'default' with a warning."""
    try:
        return caches['rate_limit']
    except Exception:
        logger.warning(
            "No 'rate_limit' cache configured — falling back to 'default'. "
            "Rate limits will not be shared across workers in production. "
            "Add a Redis 'rate_limit' backend to settings.CACHES."
        )
        return caches['default']


# ── Per-endpoint limits ───────────────────────────────────────────────────────
# Key: URL prefix (longest-prefix wins). Values: per-window limits.
ENDPOINT_LIMITS: Dict[str, Dict[str, int]] = {
    '/api/chatbot/':     {'rpm': 60,  'rph': 1_000, 'rpd': 10_000},
    '/api/diagnostics/': {'rpm': 20,  'rph': 300,   'rpd': 3_000},
    '/api/locations/':   {'rpm': 30,  'rph': 500,   'rpd': 5_000},
    '/api/':             {'rpm': 100, 'rph': 2_000,  'rpd': 20_000},
}

_DEFAULT_LIMITS: Dict[str, int] = {'rpm': 100, 'rph': 1_000, 'rpd': 10_000}

WINDOW_SECONDS: Dict[str, int] = {'rpm': 60, 'rph': 3_600, 'rpd': 86_400}
WINDOW_LABEL:   Dict[str, str]  = {'rpm': 'minute', 'rph': 'hour', 'rpd': 'day'}

SKIP_PATHS = frozenset([
    '/api/health/',
    '/api/health/simple/',
    '/api/health/liveness/',
    '/api/schema/',
])


# ── Main unified middleware ───────────────────────────────────────────────────
class RateLimitMiddleware(MiddlewareMixin):
    """
    Single, unified rate-limiting middleware.

    Processing order per request:
      1. Skip non-API paths.
      2. Skip health/schema paths.
      3. Extract client IP (first entry of X-Forwarded-For only).
      4. Check IP whitelist → pass through immediately.
      5. Build client_id (authenticated user-id preferred, else IP).
      6. For each window (minute, hour, day): INCR an atomic counter.
         If any counter exceeds its limit → 429.
      7. Attach X-RateLimit-Limit header for observability.

    Counter key format:
        rl:{client_id}:{window}:{bucket}
    where bucket = floor(unix_ts / window_seconds) — resets at natural boundaries.
    """

    def process_request(self, request):
        if not getattr(settings, 'RATE_LIMIT_ENABLED', True):
            return None

        path = request.path
        if not path.startswith('/api/'):
            return None
        if any(path.startswith(p) for p in SKIP_PATHS):
            return None

        client_ip = self._client_ip(request)
        if self._is_whitelisted(client_ip):
            return None

        client_id = self._client_id(request, client_ip)
        limits     = self._limits_for_path(path)
        cache      = _get_rate_cache()

        for window, limit in limits.items():
            exceeded, _ = self._check_window(cache, client_id, window, limit)
            if exceeded:
                logger.warning(
                    "Rate limit exceeded: client=%s path=%s window=%s limit=%d",
                    client_id, path, window, limit,
                )
                return self._rate_limit_response(window, limit)

        # Informational header — views may forward this to clients
        request.META['HTTP_X_RATELIMIT_LIMIT'] = str(limits.get('rpm', 0))
        return None

    # ── O(1) counter logic ────────────────────────────────────────────────────
    @staticmethod
    def _check_window(cache, client_id: str, window: str, limit: int) -> Tuple[bool, int]:
        """
        Atomic bucket counter — O(1) per window.

        Uses natural-boundary buckets (floor(unix_ts / window_secs)) so the
        counter for the current minute/hour/day resets cleanly at the top of
        each period with no background cleanup needed.

        No timestamp lists, no filter operations, no unbounded memory growth.
        """
        window_secs = WINDOW_SECONDS[window]
        bucket      = int(time.time()) // window_secs
        key         = f"rl:{client_id}:{window}:{bucket}"

        try:
            # Bug C fix: atomic add+incr — avoids TOCTOU race under multi-worker load.
            # cache.add() atomically sets key=1 only if absent (returns True on first set).
            # cache.incr() is atomic in both Redis and Memcached backends.
            if not cache.add(key, 1, timeout=window_secs * 2):
                # Key already exists — atomically increment it
                try:
                    count = cache.incr(key)
                except ValueError:
                    # Key expired between add() and incr() — treat as new bucket
                    cache.set(key, 1, timeout=window_secs * 2)
                    count = 1
            else:
                count = 1
        except Exception as exc:
            # Cache unavailable — allow request rather than block all users
            logger.error("Rate-limit cache error (allowing request): %s", exc)
            return False, limit

        exceeded  = count > limit
        remaining = max(0, limit - count)
        return exceeded, remaining

    # ── Helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def _client_ip(request) -> str:
        """Bug 1 fix: read XFF right-to-left — left entries are attacker-controlled.
        Render.com appends the real client IP at the rightmost position.
        RATE_LIMIT_TRUSTED_PROXIES (default 1) controls how many rightmost
        entries are infrastructure-added and therefore trustworthy.
        Set to 0 in local dev (no proxy, REMOTE_ADDR is authoritative).
        """
        trusted = int(getattr(settings, 'RATE_LIMIT_TRUSTED_PROXIES', 1))

        if trusted == 0:
            return request.META.get('REMOTE_ADDR', '0.0.0.0')

        xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if not xff:
            return request.META.get('REMOTE_ADDR', '0.0.0.0')

        ips = [ip.strip() for ip in xff.split(',') if ip.strip()]
        if not ips:
            return request.META.get('REMOTE_ADDR', '0.0.0.0')

        # [attacker_controlled..., real_client, infra_proxy_1, ..., infra_proxy_N]
        # The real client is at index: len(ips) - trusted - 1
        real_idx = len(ips) - trusted - 1
        if real_idx < 0:
            # Fewer IPs than expected proxy hops — suspicious, fall back to REMOTE_ADDR
            logger.debug(
                "XFF has fewer entries (%d) than RATE_LIMIT_TRUSTED_PROXIES (%d); "
                "using REMOTE_ADDR", len(ips), trusted
            )
            return request.META.get('REMOTE_ADDR', '0.0.0.0')

        candidate = ips[real_idx]
        try:
            ipaddress.ip_address(candidate)
            return candidate
        except ValueError:
            logger.warning("Unparseable IP in XFF position %d: %r", real_idx, candidate)
            return request.META.get('REMOTE_ADDR', '0.0.0.0')

    @staticmethod
    def _is_whitelisted(ip: str) -> bool:
        if ip in getattr(settings, 'RATE_LIMIT_WHITELIST', []):
            return True
        for cidr in getattr(settings, 'RATE_LIMIT_WHITELIST_NETWORKS', []):
            try:
                if ipaddress.ip_address(ip) in ipaddress.ip_network(cidr, strict=False):
                    return True
            except ValueError:
                pass
        return False

    @staticmethod
    def _client_id(request, ip: str) -> str:
        if hasattr(request, 'user') and request.user.is_authenticated:
            return f"u:{request.user.id}"
        return f"i:{ip}"

    @staticmethod
    def _limits_for_path(path: str) -> Dict[str, int]:
        """Longest-prefix match across ENDPOINT_LIMITS."""
        best_prefix = ''
        best_limits  = _DEFAULT_LIMITS
        for prefix, limits in ENDPOINT_LIMITS.items():
            if path.startswith(prefix) and len(prefix) > len(best_prefix):
                best_prefix = prefix
                best_limits = limits
        return best_limits

    @staticmethod
    def _rate_limit_response(window: str, limit: int) -> JsonResponse:
        label       = WINDOW_LABEL.get(window, 'minute')
        window_secs = WINDOW_SECONDS.get(window, 60)
        resp = JsonResponse(
            {
                'error':       'rate_limit_exceeded',
                'message':     f'Too many requests — limit is {limit} per {label}.',
                'limit':       limit,
                'window':      label,
                'retry_after': window_secs,
            },
            status=429,
        )
        resp['Retry-After']      = str(window_secs)
        resp['X-RateLimit-Limit']  = str(limit)
        resp['X-RateLimit-Window'] = label
        return resp


# ── Compatibility no-op stubs (Bug 3 fix) ────────────────────────────────────
# These classes are still listed in settings.MIDDLEWARE to avoid a deployment
# outage while rolling the fix. They are now pure no-ops; all logic lives in
# RateLimitMiddleware above.

class IPWhitelistMiddleware(MiddlewareMixin):
    """
    Deprecated — whitelist logic is now inside RateLimitMiddleware.
    Kept as a no-op stub so settings.MIDDLEWARE requires no changes.
    """
    def process_request(self, request):
        return None


class UserRateLimitMiddleware(MiddlewareMixin):
    """
    Deprecated — user-tier awareness is handled inside RateLimitMiddleware.
    Kept as a no-op stub so settings.MIDDLEWARE requires no changes.
    """
    def process_request(self, request):
        return None


# ── Admin utilities ───────────────────────────────────────────────────────────
def reset_rate_limits(client_id: str) -> None:
    """Remove all current-bucket rate-limit counters for a client (admin use)."""
    cache = _get_rate_cache()
    now   = int(time.time())
    for window, secs in WINDOW_SECONDS.items():
        bucket = now // secs
        key    = f"rl:{client_id}:{window}:{bucket}"
        cache.delete(key)
    logger.info("Rate limits cleared for client: %s", client_id)


def get_rate_limit_status(client_id: str) -> Dict[str, Dict]:
    """Return current counter values for a client (admin/debug use)."""
    cache  = _get_rate_cache()
    now    = int(time.time())
    status = {}
    for window, secs in WINDOW_SECONDS.items():
        bucket = now // secs
        key    = f"rl:{client_id}:{window}:{bucket}"
        count  = int(cache.get(key) or 0)
        status[window] = {
            'count':   count,
            'limit':   _DEFAULT_LIMITS.get(window, 0),
            'bucket':  bucket,
            'resets_in': secs - (now % secs),
        }
    return status
