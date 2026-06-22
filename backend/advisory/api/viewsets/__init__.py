"""Domain viewsets grouped by feature."""

from .chatbot import ChatbotViewSet
from .crop import CropAdvisoryViewSet, CropViewSet, TrendingCropsViewSet
from .diagnostics import DiagnosticViewSet
from .farmer_profile import FarmerProfileViewSet
from .government import RealTimeGovernmentDataViewSet
from .iot import IoTBlockchainViewSet
from .field_advisory import FieldAdvisoryViewSet
from .languages import LanguageViewSet
from .location import LocationRecommendationViewSet
from .market import MarketPricesViewSet
from .auth_viewset import AuthViewSet
from .misc import ForumPostViewSet, SMSIVRViewSet, TextToSpeechViewSet
from .pest import PestDetectionViewSet
from .schemes import GovernmentSchemesViewSet
from .weather import WeatherViewSet

__all__ = [
    "AuthViewSet",
    "ChatbotViewSet",
    "CropAdvisoryViewSet",
    "CropViewSet",
    "DiagnosticViewSet",
    "FarmerProfileViewSet",
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
    "WeatherViewSet",
]
