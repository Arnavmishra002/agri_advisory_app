"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (TokenObtainPairView,TokenRefreshView,)
from .schema_views import CachedSpectacularAPIView, OptimizedSpectacularSwaggerView
from .fast_docs import FastAPIDocsView, FastAPIDocsHTMLView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('advisory.api.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/schema/', CachedSpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', OptimizedSpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # Fast API documentation
    path('api/docs/', FastAPIDocsView.as_view(), name='fast-docs'),
    path('api/docs/html/', FastAPIDocsHTMLView.as_view(), name='fast-docs-html'),
    # Alternative fast schema endpoint
    path('api/schema/fast/', CachedSpectacularAPIView.as_view(), name='schema-fast'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
