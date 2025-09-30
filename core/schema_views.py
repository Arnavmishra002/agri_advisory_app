"""
Custom schema views with caching for faster Swagger UI loading
"""
from django.core.cache import cache
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.response import Response
import json
import hashlib


class CachedSpectacularAPIView(SpectacularAPIView):
    """
    Cached version of SpectacularAPIView for faster schema generation
    """
    cache_timeout = 60 * 60 * 24  # 24 hours
    
    def get(self, request, *args, **kwargs):
        # Create cache key based on request parameters
        cache_key = f"schema_{hashlib.md5(str(request.GET).encode()).hexdigest()}"
        
        # Try to get from cache first
        cached_schema = cache.get(cache_key)
        if cached_schema:
            return Response(cached_schema)
        
        # Generate schema if not in cache
        response = super().get(request, *args, **kwargs)
        
        # Cache the schema
        if response.status_code == 200:
            cache.set(cache_key, response.data, self.cache_timeout)
        
        return response


class OptimizedSpectacularSwaggerView(SpectacularSwaggerView):
    """
    Optimized Swagger UI view with faster loading
    """
    template_name = 'swagger-ui-optimized.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add optimization settings
        context.update({
            'swagger_ui_settings': {
                'docExpansion': 'none',
                'defaultModelsExpandDepth': 0,
                'defaultModelExpandDepth': 0,
                'displayRequestDuration': True,
                'filter': True,
                'showExtensions': False,
                'showCommonExtensions': False,
                'tryItOutEnabled': True,
                'requestSnippetsEnabled': True,
                'persistAuthorization': True,
                'deepLinking': True,
                'displayOperationId': False,
            }
        })
        
        return context
