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
from django.urls import path, include, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve as static_serve
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views
# from .schema_views import CachedSpectacularAPIView, OptimizedSpectacularSwaggerView
# from .fast_docs import FastAPIDocsView, FastAPIDocsHTMLView

urlpatterns = [
    path('', views.api_root, name='api_root'),
    path('admin/', admin.site.urls),
    path('api/', include('advisory.api.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

if getattr(settings, 'SERVE_FRONTEND', False):
    dist = settings.FRONTEND_DIST
    urlpatterns += [
        # Serve Vite-built assets (hashed filenames: /assets/index-abc123.js)
        re_path(
            r'^assets/(?P<path>.*)$',
            static_serve,
            {'document_root': str(dist / 'assets')},
        ),
        # Serve /js/* and /css/* static files from dist/
        # NOTE: Django serve() only accepts 'path' kwarg — both dir + filename
        # must be captured in a single group so serve() gets e.g. path=js/app.js
        re_path(
            r'^(?P<path>(?:css|js)/.*)$',
            static_serve,
            {'document_root': str(dist)},
        ),
    ]
    # Serve SPA at root — this must be LAST (catch-all)
    if settings.FRONTEND_AT_ROOT:
        # Replace the api_root with the actual HTML frontend
        urlpatterns[0] = path('', views.serve_frontend_index, name='frontend_root')
        # Also catch all non-API paths so React/Vite router works
        urlpatterns += [
            re_path(r'^(?!api/|admin/|static/|media/).*$',
                    views.serve_frontend_index, name='frontend_spa'),
        ]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
