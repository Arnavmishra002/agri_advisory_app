"""Strict JWT views used by the public API token endpoints."""

from collections.abc import Mapping

from rest_framework import serializers, status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from advisory.rate_limiters import ExponentialBackoff, client_ip_from_request


class _RejectUnknownFieldsMixin:
    allowed_fields = frozenset()

    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            raise serializers.ValidationError("Request body must be a JSON object.")
        unknown = set(data) - self.allowed_fields
        if unknown:
            raise serializers.ValidationError(
                {"non_field_errors": [f"Unexpected field: {field}" for field in sorted(unknown)]}
            )
        return super().to_internal_value(data)


class StrictTokenObtainPairSerializer(_RejectUnknownFieldsMixin, TokenObtainPairSerializer):
    allowed_fields = frozenset(("username", "password"))


class StrictTokenRefreshSerializer(_RejectUnknownFieldsMixin, TokenRefreshSerializer):
    allowed_fields = frozenset(("refresh",))


class StrictTokenObtainPairView(TokenObtainPairView):
    serializer_class = StrictTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        username = request.data.get("username", "")
        identifiers = [f"ip:{client_ip_from_request(request)}"]
        if isinstance(username, str) and username.strip():
            identifiers.append(f"account:{username.strip().lower()[:254]}")

        retry_after = max((login_backoff.retry_after(identifier) for identifier in identifiers), default=0)
        if retry_after:
            return Response(
                {
                    "detail": "Too many failed login attempts. Please try again later.",
                    "error_code": "AUTH_BACKOFF",
                    "retry_after_seconds": retry_after,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(retry_after)},
            )

        try:
            response = super().post(request, *args, **kwargs)
        except (AuthenticationFailed, ValidationError):
            for identifier in identifiers:
                login_backoff.record_failure(identifier)
            raise
        if response.status_code < 400:
            for identifier in identifiers:
                login_backoff.clear(identifier)
        else:
            for identifier in identifiers:
                login_backoff.record_failure(identifier)
        return response


class StrictTokenRefreshView(TokenRefreshView):
    serializer_class = StrictTokenRefreshSerializer


login_backoff = ExponentialBackoff("login")
