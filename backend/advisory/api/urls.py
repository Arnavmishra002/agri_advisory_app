from django.http import HttpResponse
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .monitoring_views import (
    MonitoringViewSet,
    RateLimitViewSet,
    liveness_check,
    readiness_check,
    simple_health_check,
)
from .viewsets import (
    ChatbotViewSet,
    CropAdvisoryViewSet,
    CropViewSet,
    DiagnosticViewSet,
    FarmerProfileViewSet,
    FieldAdvisoryViewSet,
    ForumPostViewSet,
    GovernmentSchemesViewSet,
    IoTBlockchainViewSet,
    LanguageViewSet,
    LocationRecommendationViewSet,
    MarketPricesViewSet,
    PestDetectionViewSet,
    RealTimeGovernmentDataViewSet,
    SMSIVRViewSet,
    TextToSpeechViewSet,
    TrendingCropsViewSet,
    UserViewSet,
    WeatherViewSet,
)

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="users")
router.register(r"advisories", CropAdvisoryViewSet, basename="advisories")
router.register(r"crops", CropViewSet, basename="crops")
router.register(r"weather", WeatherViewSet, basename="weather")
router.register(r"market-prices", MarketPricesViewSet, basename="market-prices")
router.register(r"trending-crops", TrendingCropsViewSet, basename="trending-crops")
router.register(r"sms-ivr", SMSIVRViewSet, basename="sms-ivr")
router.register(r"pest-detection", PestDetectionViewSet, basename="pest-detection")
router.register(r"tts", TextToSpeechViewSet, basename="tts")
router.register(r"forum", ForumPostViewSet, basename="forum")
router.register(r"schemes", GovernmentSchemesViewSet, basename="schemes")
router.register(r"chatbot", ChatbotViewSet, basename="chatbot")
router.register(r"locations", LocationRecommendationViewSet, basename="locations")
router.register(r"realtime-gov", RealTimeGovernmentDataViewSet, basename="realtime-gov")
router.register(r"field-advisory", FieldAdvisoryViewSet, basename="field-advisory")
router.register(r"languages", LanguageViewSet, basename="languages")
router.register(r"monitoring", MonitoringViewSet, basename="monitoring")
router.register(r"rate-limits", RateLimitViewSet, basename="rate-limits")
router.register(r"diagnostics", DiagnosticViewSet, basename="diagnostics")
router.register(r"iot-blockchain", IoTBlockchainViewSet, basename="iot-blockchain")
router.register(r"farmer-profile", FarmerProfileViewSet, basename="farmer-profile")

urlpatterns = [
    path("", include(router.urls)),
    path("health/", lambda request: HttpResponse("OK", status=200), name="health"),
    path("health/simple/", simple_health_check, name="simple_health"),
    path("health/liveness/", liveness_check, name="liveness_check"),
    path(
        "government-schemes/",
        GovernmentSchemesViewSet.as_view({"get": "list"}),
        name="government-schemes",
    ),
]
