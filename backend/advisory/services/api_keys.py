"""One place that decides whether an API key is real.

Every provider key in this app arrives through the environment, and the
shipped `.env.example` fills each one with a placeholder such as
``your_groq_api_key_here``. A placeholder is a non-empty string, so a bare
``os.getenv("GROQ_API_KEY")`` check treats it as configured. The observed
consequence on a half-configured deployment is not a loud failure but a quiet
one: the app spends a network round trip on every request to be told 401, the
keyless provider that would have answered is never reached, and the safe
deterministic path that should have run is skipped. Two tests in
``test_chatbot_farmer_quality`` and ``test_chat_stream_source_order`` fail for
exactly this reason when a developer's `.env` still holds the samples.

`data_gov_mandi_client` already guarded against this for one key. This module
promotes that guard so every key read goes through the same rule.

The matching is deliberately anchored rather than substring-based. An earlier
version rejected any key containing ``test`` or ``api_key`` anywhere, which a
random 56-character provider key can satisfy by chance -- silently disabling a
key that works.
"""

from __future__ import annotations

import os
import re
from typing import Optional

# Shortest real provider key in use is a 32-character OpenWeatherMap key.
_MIN_KEY_LENGTH = 16

# Anchored placeholder shapes: a value has to *look* like a sample, not merely
# contain a common English fragment.
_PLACEHOLDER_PATTERNS = (
    re.compile(r"^(your|my|the|some|a)[_\-]", re.I),   # your_groq_api_key_here
    re.compile(r"[_\-]here$", re.I),                    # ..._api_key_here
    re.compile(r"^<.*>$"),                              # <paste key>
    re.compile(r"^(change[_\-]?me|placeholder|example|insert[_\-]key|demo[_\-]key|todo|none|null|n/?a)$", re.I),
    re.compile(r"^x{4,}$", re.I),                       # xxxx...
)


def is_real_key(value: Optional[str]) -> bool:
    """True when *value* looks like a credential rather than a sample."""
    if not value:
        return False
    key = value.strip()
    if len(key) < _MIN_KEY_LENGTH:
        return False
    return not any(p.search(key) for p in _PLACEHOLDER_PATTERNS)


def is_configured(value: Optional[str]) -> bool:
    """True when *value* is set and is not a shipped placeholder.

    Unlike :func:`is_real_key` this applies no length floor, because not every
    configured setting is a credential. ``TWILIO_FROM_NUMBER`` holds a sender
    number such as ``+911234567890``; running that through the credential rule
    would reject a perfectly valid deployment for being thirteen characters long.
    """
    if not value:
        return False
    v = value.strip()
    return bool(v) and not any(p.search(v) for p in _PLACEHOLDER_PATTERNS)


def env_setting(name: str) -> str:
    """The environment value for *name*, or "" when unset or a placeholder."""
    value = os.environ.get(name, "").strip()
    return value if is_configured(value) else ""


def env_key(name: str) -> str:
    """The environment value for *name*, or "" when it is unset or a placeholder.

    Returning "" rather than None keeps this a drop-in replacement for the
    ``os.getenv(name, "")`` calls it supersedes, so existing truthiness checks
    keep working and simply become correct.
    """
    value = os.environ.get(name, "").strip()
    return value if is_real_key(value) else ""
