import logging
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)

def _cors_for_request(request) -> str:
    """
    Determine the Access-Control-Allow-Origin header value for a request
    based on CORS_ALLOWED_ORIGINS and CORS_ALLOW_ALL_ORIGINS settings.
    """
    origin = request.headers.get("Origin") or request.META.get("HTTP_ORIGIN") or ""
    if not origin:
        return "*"
    
    if getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False):
        return origin

    allowed_origins = getattr(settings, "CORS_ALLOWED_ORIGINS", [])
    if origin in allowed_origins:
        return origin

    return allowed_origins[0] if allowed_origins else "*"

def _resolve_user_id(request) -> str:
    """
    Resolve the user ID from the request using SimpleJWT token authentication.
    Falls back to request.user if already authenticated, or "anonymous".
    """
    try:
        res = JWTAuthentication().authenticate(request)
        if res:
            user, token = res
            if user and user.is_authenticated:
                return str(user.id)
    except Exception as exc:
        logger.debug("JWT authentication failed: %s", exc)

    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        return str(user.id)

    return "anonymous"
