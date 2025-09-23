from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CropAdvisoryViewSet, WeatherViewSet

router = DefaultRouter()
router.register(r'advisories', CropAdvisoryViewSet)
router.register(r'weather', WeatherViewSet, basename='weather')

urlpatterns = [
    path('', include(router.urls)),
]
