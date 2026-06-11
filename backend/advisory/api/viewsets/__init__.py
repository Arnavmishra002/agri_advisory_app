"""Domain viewsets grouped by feature."""

from .chatbot import ChatbotViewSet
from .crop import CropAdvisoryViewSet, CropViewSet, TrendingCropsViewSet
from .diagnostics import DiagnosticViewSet
from .government import RealTimeGovernmentDataViewSet
from .iot import IoTBlockchainViewSet
from .field_advisory import FieldAdvisoryViewSet
from .languages import LanguageViewSet
from .location import LocationRecommendationViewSet
from .market import MarketPricesViewSet
from .misc import ForumPostViewSet, SMSIVRViewSet, TextToSpeechViewSet, UserViewSet
from .pest import PestDetectionViewSet
from .schemes import GovernmentSchemesViewSet
from .weather import WeatherViewSet

__all__ = [
    "ChatbotViewSet",
    "CropAdvisoryViewSet",
    "CropViewSet",
    "DiagnosticViewSet",
    "FieldAdvisoryViewSet",
    "ForumPostViewSet",
    "GovernmentSchemesViewSet",
    "IoTBlockchainViewSet",
    "LanguageViewSet",
    "LocationRecommendationViewSet",
    "MarketPricesViewSet",
    "PestDetectionViewSet",
    "RealTimeGovernmentDataViewSet",
    "SMSIVRViewSet",
    "TextToSpeechViewSet",
    "TrendingCropsViewSet",
    "UserViewSet",
    "WeatherViewSet",
]

__all__ = [
    "ChatbotViewSet",
    "CropAdvisoryViewSet",
    "CropViewSet",
    "TrendingCropsViewSet",
    "DiagnosticViewSet",
    "ForumPostViewSet",
    "GovernmentSchemesViewSet",
    "IoTBlockchainViewSet",
    "LocationRecommendationViewSet",
    "MarketPricesViewSet",
    "PestDetectionViewSet",
    "RealTimeGovernmentDataViewSet",
    "SMSIVRViewSet",
    "TextToSpeechViewSet",
    "UserViewSet",
    "WeatherViewSet",
]
