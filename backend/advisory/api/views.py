"""Backward-compatible re-exports; prefer `advisory.api.viewsets`."""

from .viewsets import (
    CropAdvisoryViewSet,
    CropViewSet,
    DiagnosticViewSet,
    ForumPostViewSet,
    LocationRecommendationViewSet,
    PestDetectionViewSet,
    RealTimeGovernmentDataViewSet,
    SMSIVRViewSet,
    TextToSpeechViewSet,
    TrendingCropsViewSet,
    UserViewSet,
)

__all__ = [
    "CropAdvisoryViewSet",
    "CropViewSet",
    "TrendingCropsViewSet",
    "DiagnosticViewSet",
    "ForumPostViewSet",
    "LocationRecommendationViewSet",
    "PestDetectionViewSet",
    "RealTimeGovernmentDataViewSet",
    "SMSIVRViewSet",
    "TextToSpeechViewSet",
    "UserViewSet",
]
