"""Rate-limit the direct Django chatbot stream endpoint.

Normal DRF API requests are throttled by ``ConfigurableRateThrottle`` after
authentication has run. This middleware remains for the SSE view, which is a
plain Django view and therefore bypasses DRF throttling.
"""

import logging

from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

from ..rate_limiters import AtomicWindowRateLimiter, client_ip_from_request

logger = logging.getLogger(__name__)

SKIP_PATHS = frozenset(
    {
        "/api/health/",
        "/api/health/simple/",
        "/api/health/liveness/",
        "/api/schema/",
    }
)


def _stream_limiter() -> AtomicWindowRateLimiter:
    return AtomicWindowRateLimiter(
        key_prefix="api:stream:public",
        capacity=int(getattr(settings, "RATE_LIMIT_PUBLIC_RPM", 100)),
        window_seconds=60,
    )


def reset_rate_limits(client_id: str) -> None:
    """Best-effort admin reset across configured throttle buckets."""
    for policy, prefix in (
        ("public", "RATE_LIMIT_PUBLIC"),
        ("authenticated", "RATE_LIMIT_AUTHENTICATED"),
        ("auth", "RATE_LIMIT_AUTH"),
        ("heavy", "RATE_LIMIT_HEAVY"),
    ):
        for window in ("rpm", "rph", "rpd"):
            capacity = int(getattr(settings, f"{prefix}_{window.upper()}"))
            AtomicWindowRateLimiter(
                key_prefix=f"api:{policy}:{window}",
                capacity=capacity,
                window_seconds={"rpm": 60, "rph": 3600, "rpd": 86400}[window],
            ).reset(client_id)
    _stream_limiter().reset(client_id)


def get_rate_limit_status(client_id: str):
    """Return safe, approximate status for the admin monitoring endpoint."""
    return {
        "policy": "configured",
        "client_id": client_id,
        "limits": {
            "public": {
                "rpm": int(getattr(settings, "RATE_LIMIT_PUBLIC_RPM", 0)),
                "rph": int(getattr(settings, "RATE_LIMIT_PUBLIC_RPH", 0)),
                "rpd": int(getattr(settings, "RATE_LIMIT_PUBLIC_RPD", 0)),
            },
            "authenticated": {
                "rpm": int(getattr(settings, "RATE_LIMIT_AUTHENTICATED_RPM", 0)),
                "rph": int(getattr(settings, "RATE_LIMIT_AUTHENTICATED_RPH", 0)),
                "rpd": int(getattr(settings, "RATE_LIMIT_AUTHENTICATED_RPD", 0)),
            },
        },
    }


class RateLimitMiddleware(MiddlewareMixin):
    """Protect the non-DRF SSE endpoint without double-counting DRF APIs."""

    def process_request(self, request):
        if not getattr(settings, "RATE_LIMIT_ENABLED", True):
            return None
        if request.path != "/api/chatbot/stream/" or request.path in SKIP_PATHS:
            return None

        client_ip = client_ip_from_request(request)
        if client_ip in getattr(settings, "RATE_LIMIT_WHITELIST", []):
            return None
        limiter = _stream_limiter()
        if limiter.is_allowed(f"ip:{client_ip}"):
            return None

        retry_after = max(1, int(round(limiter.wait_time(f"ip:{client_ip}"))))
        logger.warning("Chatbot stream rate limit exceeded for client=%s", client_ip)
        response = JsonResponse(
            {
                "error": "rate_limit_exceeded",
                "message": "Too many requests. Please wait and try again.",
                "error_hi": "बहुत अधिक अनुरोध। थोड़ी देर बाद फिर कोशिश करें।",
                "retry_after": retry_after,
            },
            status=429,
        )
        response["Retry-After"] = str(retry_after)
        return response


class IPWhitelistMiddleware(MiddlewareMixin):
    """Compatibility no-op; whitelist handling lives in the rate limiter."""

    def process_request(self, request):
        return None


class UserRateLimitMiddleware(MiddlewareMixin):
    """Compatibility no-op; DRF handles authenticated request limits."""

    def process_request(self, request):
        return None
