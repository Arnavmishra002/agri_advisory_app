"""Backward-compatible re-exports; prefer `advisory.api.viewsets`."""

from .viewsets import (
    ChatbotViewSet,
    GovernmentSchemesViewSet,
    IoTBlockchainViewSet,
    MarketPricesViewSet,
    WeatherViewSet,
)

__all__ = [
    "WeatherViewSet",
    "MarketPricesViewSet",
    "GovernmentSchemesViewSet",
    "ChatbotViewSet",
    "IoTBlockchainViewSet",
]
