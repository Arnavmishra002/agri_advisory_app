"""Signed proof used when a guest session is attached to a new account."""

import hmac

from django.conf import settings
from django.core import signing


_SALT = "krishimitra.guest-session.v1"


def make_guest_session_token(session_id: str) -> str:
    if not session_id:
        return ""
    return signing.dumps({"session_id": session_id}, salt=_SALT, compress=True)


def verify_guest_session_token(session_id: str, token: str) -> bool:
    if not session_id or not token:
        return False
    max_age = int(getattr(settings, "GUEST_SESSION_TOKEN_MAX_AGE_SECONDS", 2_592_000))
    try:
        payload = signing.loads(token, salt=_SALT, max_age=max_age)
    except signing.BadSignature:
        return False
    return hmac.compare_digest(str(payload.get("session_id") or ""), session_id)
