from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CropAdvisoryViewSet

router = DefaultRouter()
router.register(r'advisories', CropAdvisoryViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
