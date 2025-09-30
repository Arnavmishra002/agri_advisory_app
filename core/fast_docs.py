"""
Fast API documentation view for quick access
"""
from django.http import JsonResponse
from django.views import View
from django.shortcuts import render
from django.core.cache import cache
import json


class FastAPIDocsView(View):
    """
    Lightweight API documentation that loads instantly
    """
    
    def get(self, request):
        cache_key = "fast_api_docs"
        cached_docs = cache.get(cache_key)
        
        if cached_docs:
            return JsonResponse(cached_docs)
        
        # Generate lightweight API docs
        api_docs = {
            "title": "Krishimitra Agri-Advisory API",
            "version": "1.0.0",
            "description": "AI-powered agricultural advisory system for Indian farmers",
            "base_url": request.build_absolute_uri('/api/'),
            "endpoints": {
                "Authentication": {
                    "POST /api/token/": "Get JWT token",
                    "POST /api/token/refresh/": "Refresh JWT token"
                },
                "Core Advisory": {
                    "GET /api/advisories/": "List crop advisories",
                    "POST /api/advisories/": "Create advisory",
                    "GET /api/advisories/{id}/": "Get specific advisory",
                    "PUT /api/advisories/{id}/": "Update advisory",
                    "DELETE /api/advisories/{id}/": "Delete advisory"
                },
                "AI/ML Predictions": {
                    "POST /api/advisories/predict_yield/": "Predict crop yield",
                    "POST /api/advisories/chatbot/": "NLP chatbot interaction",
                    "POST /api/advisories/fertilizer_recommendation/": "Fertilizer recommendations",
                    "POST /api/advisories/ml_crop_recommendation/": "ML crop recommendations",
                    "POST /api/advisories/ml_fertilizer_recommendation/": "ML fertilizer recommendations"
                },
                "External Data": {
                    "GET /api/weather/current/": "Current weather data",
                    "GET /api/weather/forecast/": "Weather forecast",
                    "GET /api/market-prices/prices/": "Market prices",
                    "GET /api/trending-crops/": "Trending crops"
                },
                "Advanced Features": {
                    "POST /api/sms-ivr/receive-sms/": "SMS integration",
                    "POST /api/sms-ivr/ivr-input/": "IVR integration",
                    "POST /api/pest-detection/detect/": "Pest detection",
                    "POST /api/tts/speak/": "Text-to-speech",
                    "GET /api/forum/": "Community forum"
                },
                "Analytics": {
                    "POST /api/advisories/collect_feedback/": "Collect user feedback",
                    "GET /api/advisories/feedback_analytics/": "Feedback analytics",
                    "GET /api/advisories/model_performance/": "ML model performance",
                    "GET /api/advisories/user_feedback_history/": "User feedback history"
                }
            },
            "authentication": {
                "type": "Bearer Token (JWT)",
                "header": "Authorization: Bearer <token>"
            },
            "rate_limits": {
                "general": "100 requests/minute",
                "ml_endpoints": "10 requests/minute",
                "file_upload": "5 requests/minute"
            },
            "quick_start": {
                "1": "Get token: POST /api/token/ with username/password",
                "2": "Use token in Authorization header",
                "3": "Make API calls to desired endpoints"
            }
        }
        
        # Cache for 1 hour
        cache.set(cache_key, api_docs, 3600)
        
        return JsonResponse(api_docs)


class FastAPIDocsHTMLView(View):
    """
    HTML version of fast API documentation
    """
    
    def get(self, request):
        return render(request, 'fast_docs.html')
