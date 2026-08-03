"""Safe API error messages (no stack traces in production)."""

import logging

logger = logging.getLogger(__name__)


def safe_error_message(exc: Exception, *, context: str = "request") -> str:
    logger.exception("%s failed: %s", context, exc)
    return "An internal error occurred. Please try again later."
