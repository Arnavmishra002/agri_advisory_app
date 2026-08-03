"""Shared API input and upload validation limits."""

import base64
import binascii
from io import BytesIO
from typing import Optional, Tuple

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response

MAX_CHAT_QUERY_LENGTH = 2000
MAX_LOCATION_QUERY_LENGTH = 200
MAX_DIAGNOSTIC_CROP_LENGTH = 120
MAX_UPLOAD_BYTES = getattr(settings, "KRISHI_RAKSHA_MAX_UPLOAD_BYTES", 5 * 1024 * 1024)
MAX_IMAGE_PIXELS = 25_000_000
ALLOWED_IMAGE_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})


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
    """Read and validate an uploaded image without retaining it on disk."""
    size = getattr(upload, "size", None)
    if size is not None and size > max_bytes:
        return None, validate_upload_size(size, max_bytes)
    data = upload.read(max_bytes + 1)
    if len(data) > max_bytes:
        return None, validate_upload_size(len(data), max_bytes)
    return validate_image_bytes(data, content_type=getattr(upload, "content_type", ""))


def validate_image_bytes(
    data: bytes,
    *,
    content_type: str = "",
    max_bytes: int = MAX_UPLOAD_BYTES,
) -> Tuple[Optional[bytes], Optional[Response]]:
    """Verify image bytes by decoding them, not by trusting the file name/header."""
    if not isinstance(data, (bytes, bytearray)) or not data:
        return None, Response(
            {"error": "Invalid image", "error_code": "IMAGE_REQUIRED"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if len(data) > max_bytes:
        return None, validate_upload_size(len(data), max_bytes)

    try:
        from PIL import Image

        with Image.open(BytesIO(data)) as image:
            image.verify()
        with Image.open(BytesIO(data)) as image:
            image_format = (image.format or "").upper()
            width, height = image.size
            if width < 48 or height < 48:
                raise ValueError("image_dimensions")
            if width * height > MAX_IMAGE_PIXELS:
                raise ValueError("image_pixels")
            if getattr(image, "is_animated", False):
                raise ValueError("animated_image")
    except Exception:
        return None, Response(
            {"error": "Unsupported or invalid image", "error_code": "INVALID_IMAGE"},
            status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )

    if image_format not in ALLOWED_IMAGE_FORMATS:
        return None, Response(
            {
                "error": "Unsupported image format",
                "error_code": "UNSUPPORTED_IMAGE_FORMAT",
                "allowed_formats": ["jpeg", "png", "webp"],
            },
            status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )
    expected_content_types = {
        "JPEG": {"image/jpeg", "image/jpg"},
        "PNG": {"image/png"},
        "WEBP": {"image/webp"},
    }
    if content_type and content_type.lower() not in expected_content_types[image_format]:
        return None, Response(
            {"error": "Image content type does not match an allowed image", "error_code": "INVALID_CONTENT_TYPE"},
            status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )
    return bytes(data), None


def decode_base64_image(value: object) -> Tuple[Optional[bytes], Optional[Response]]:
    """Decode a raw/data-URL base64 image and apply the same content checks."""
    if not isinstance(value, str) or not value.strip():
        return None, Response(
            {"error": "Invalid image", "error_code": "IMAGE_REQUIRED"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    encoded = value.split(",", 1)[1] if value.startswith("data:") and "," in value else value
    if len(encoded) > ((MAX_UPLOAD_BYTES * 4) // 3) + 16:
        return None, validate_upload_size(MAX_UPLOAD_BYTES + 1)
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        return None, Response(
            {"error": "Invalid base64 image", "error_code": "INVALID_IMAGE_ENCODING"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return validate_image_bytes(raw)
