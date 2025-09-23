from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CropAdvisoryViewSet, WeatherViewSet, MarketPricesViewSet, TrendingCropsViewSet

router = DefaultRouter()
router.register(r'advisories', CropAdvisoryViewSet)
router.register(r'weather', WeatherViewSet, basename='weather')
router.register(r'market-prices', MarketPricesViewSet, basename='market-prices')
router.register(r'trending-crops', TrendingCropsViewSet, basename='trending-crops')

urlpatterns = [
    path('', include(router.urls)),
]
