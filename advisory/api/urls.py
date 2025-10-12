from django.urls import path, include
from django.http import HttpResponse
from rest_framework.routers import DefaultRouter
from .views import CropAdvisoryViewSet, WeatherViewSet, MarketPricesViewSet, TrendingCropsViewSet, CropViewSet, SMSIVRViewSet, PestDetectionViewSet, UserViewSet, TextToSpeechViewSet, ForumPostViewSet, GovernmentSchemesViewSet, ChatbotViewSet, LocationRecommendationViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')
router.register(r'advisories', CropAdvisoryViewSet, basename='advisories')
router.register(r'crops', CropViewSet, basename='crops')
router.register(r'weather', WeatherViewSet, basename='weather')
router.register(r'market-prices', MarketPricesViewSet, basename='market-prices')
router.register(r'trending-crops', TrendingCropsViewSet, basename='trending-crops')
router.register(r'sms-ivr', SMSIVRViewSet, basename='sms-ivr')
router.register(r'pest-detection', PestDetectionViewSet, basename='pest-detection')
router.register(r'tts', TextToSpeechViewSet, basename='tts')
router.register(r'forum', ForumPostViewSet, basename='forum')
router.register(r'government-schemes', GovernmentSchemesViewSet, basename='government-schemes')
router.register(r'chatbot', ChatbotViewSet, basename='chatbot')
router.register(r'locations', LocationRecommendationViewSet, basename='locations')

urlpatterns = [
    path('', include(router.urls)),
    # Health check endpoint
    path('health/', lambda request: HttpResponse('OK', status=200), name='health'),
]
