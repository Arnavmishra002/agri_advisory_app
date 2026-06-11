"""Shared API input validation limits."""

from typing import Optional, Tuple

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response

MAX_CHAT_QUERY_LENGTH = 2000
MAX_LOCATION_QUERY_LENGTH = 200
MAX_DIAGNOSTIC_CROP_LENGTH = 120
MAX_UPLOAD_BYTES = getattr(settings, "KRISHI_RAKSHA_MAX_UPLOAD_BYTES", 5 * 1024 * 1024)


def query_too_long(value: str, limit: int, field: str = "query") -> Optional[Response]:
    if value and len(value) > limit:
        return Response(
            {
                "error": f"{field} too long",
                "message": f"Maximum {limit} characters allowed",
                "max_length": limit,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None


def validate_upload_size(
    size_bytes: int,
    max_bytes: int = MAX_UPLOAD_BYTES,
) -> Optional[Response]:
    if size_bytes > max_bytes:
        return Response(
            {
                "error": "File too large",
                "message": f"Maximum upload size is {max_bytes // (1024 * 1024)} MB",
                "max_bytes": max_bytes,
            },
            status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )
    return None


def read_upload_with_limit(upload, max_bytes: int = MAX_UPLOAD_BYTES) -> Tuple[Optional[bytes], Optional[Response]]:
    """Read an uploaded file without loading more than max_bytes into memory."""
    size = getattr(upload, "size", None)
    if size is not None and size > max_bytes:
        return None, validate_upload_size(size, max_bytes)
    data = upload.read(max_bytes + 1)
    if len(data) > max_bytes:
        return None, validate_upload_size(len(data), max_bytes)
    return data, None
