"""Signed proof used when a guest session is attached to a new account."""

import hmac

from django.conf import settings
from django.core import signing


_SALT = "krishimitra.guest-session.v1"

# Session ids the server assigns to accounts and channels ("user:<id>" for a
# signed-in farmer, "wa_<phone>" for WhatsApp). A client can type any session
# id, so these must never be signed as a guest session; otherwise the token
# lets a new account adopt another farmer's profile on registration.
RESERVED_SESSION_PREFIXES = ("user:", "wa_")


def is_reserved_session_id(session_id: str) -> bool:
    return str(session_id or "").lower().startswith(RESERVED_SESSION_PREFIXES)


def make_guest_session_token(session_id: str) -> str:
    if not session_id or is_reserved_session_id(session_id):
        return ""
    return signing.dumps({"session_id": session_id}, salt=_SALT, compress=True)


def verify_guest_session_token(session_id: str, token: str) -> bool:
    if not session_id or not token or is_reserved_session_id(session_id):
        return False
    max_age = int(getattr(settings, "GUEST_SESSION_TOKEN_MAX_AGE_SECONDS", 2_592_000))
    try:
        payload = signing.loads(token, salt=_SALT, max_age=max_age)
    except signing.BadSignature:
        return False
    return hmac.compare_digest(str(payload.get("session_id") or ""), session_id)
