from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CropAdvisoryViewSet, WeatherViewSet, TextToSpeechViewSet

router = DefaultRouter()
router.register(r'advisories', CropAdvisoryViewSet)
router.register(r'weather', WeatherViewSet, basename='weather')
router.register(r'text-to-speech', TextToSpeechViewSet, basename='text-to-speech')

urlpatterns = [
    path('', include(router.urls)),
]
