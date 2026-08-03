"""Request throttling with separate public, authenticated, and auth policies."""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from django.conf import settings
from rest_framework.throttling import BaseThrottle

from ..rate_limiters import AtomicWindowRateLimiter, client_ip_from_request


WINDOWS = {
    "rpm": 60,
    "rph": 60 * 60,
    "rpd": 24 * 60 * 60,
}


@lru_cache(maxsize=32)
def _limiter(policy: str, window: str, capacity: int) -> AtomicWindowRateLimiter:
    return AtomicWindowRateLimiter(
        key_prefix=f"api:{policy}:{window}",
        capacity=capacity,
        window_seconds=WINDOWS[window],
    )


def _policy_for_request(request) -> str:
    path = request.path.rstrip("/")
    if path.startswith("/api/users") or path == "/api/token":
        return "auth"
    if path.startswith("/api/diagnostics") or path.startswith("/api/pest") or path.startswith("/api/tts"):
        return "heavy"
    if getattr(request.user, "is_authenticated", False):
        return "authenticated"
    return "public"


def _limits(policy: str) -> dict[str, int]:
    prefix = {
        "public": "RATE_LIMIT_PUBLIC",
        "authenticated": "RATE_LIMIT_AUTHENTICATED",
        "auth": "RATE_LIMIT_AUTH",
        "heavy": "RATE_LIMIT_HEAVY",
    }[policy]
    return {
        window: int(getattr(settings, f"{prefix}_{window.upper()}"))
        for window in WINDOWS
    }


def _account_identifier(request) -> Optional[str]:
    user = getattr(request, "user", None)
    if getattr(user, "is_authenticated", False):
        return f"user:{user.pk}"

    data = getattr(request, "data", {}) or {}
    for field in ("phone_number", "username", "email"):
        value = data.get(field)
        if isinstance(value, str) and value.strip():
            return f"account:{field}:{value.strip().lower()}"
    return None


class ConfigurableRateThrottle(BaseThrottle):
    """Apply endpoint-appropriate limits to IP and authenticated account."""

    def __init__(self):
        self._wait = 0.0

    def allow_request(self, request, view) -> bool:
        if not getattr(settings, "RATE_LIMIT_ENABLED", True):
            return True

        policy = _policy_for_request(request)
        limits = _limits(policy)
        identifiers = [f"ip:{client_ip_from_request(request)}"]
        account = _account_identifier(request)
        if account:
            identifiers.append(account)

        for identifier in identifiers:
            for window, capacity in limits.items():
                limiter = _limiter(policy, window, capacity)
                if not limiter.is_allowed(identifier):
                    self._wait = max(self._wait, limiter.wait_time(identifier), 1.0)
                    return False
        return True

    def wait(self) -> Optional[float]:
        return self._wait or None
