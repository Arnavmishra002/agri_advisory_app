#!/usr/bin/env python3
"""
KrishiMitra Unified API Views v3.0
All endpoints using the new unified service architecture.
Drop this file into advisory/api/views_v3.py and update urls.py
"""

import logging
from datetime import datetime
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from ..services.unified_realtime_service import (
    weather_service, market_service, gemini_service,
    schemes_service, iot_blockchain, GOVERNMENT_SCHEMES
)
from ..models import User, ForumPost

logger = logging.getLogger(__name__)


class WeatherViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=["get"])
    def current(self, request):
        location = request.GET.get("location", "Delhi")
        lat = request.GET.get("latitude")
        lon = request.GET.get("longitude")
        try:
            lat = float(lat) if lat else None
            lon = float(lon) if lon else None
        except ValueError:
            lat, lon = None, None
        data = weather_service.get_weather(location, lat, lon)
        return Response(data)

    def list(self, request):
        return self.current(request)


class MarketPricesViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        location = request.GET.get("location", "Delhi")
        mandi = request.GET.get("mandi")
        crop = request.GET.get("crop")
        data = market_service.get_prices(location, mandi, crop)
        return Response(data)


class GovernmentSchemesViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        location = request.GET.get("location", "")
        category = request.GET.get("category")
        data = schemes_service.get_schemes(location, category)
        return Response(data)

    @action(detail=False, methods=["post"])
    def eligibility(self, request):
        profile = request.data.get("farmer_profile", {})
        data = schemes_service.check_eligibility(profile)
        return Response(data)


class ChatbotViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    SYSTEM_PROMPT = """You are KrishiMitra AI (कृषिमित्र), India's most trusted agricultural assistant.
You help Indian farmers with:
- Crop recommendations based on soil, season, location
- Real-time mandi prices and market trends
- Government schemes (PM-Kisan, PMFBY, KCC, etc.)
- Weather-based farming advisories
- Pest and disease management
- Soil health and fertilizer guidance

Always respond in the same language as the question (Hindi or English).
Be specific, practical, and cite real government schemes/MSP prices when relevant.
If you don't have real-time data, clearly say so and direct to official websites."""

    def create(self, request):
        return self._handle_query(request)

    @action(detail=False, methods=["post"])
    def query(self, request):
        return self._handle_query(request)

    def _handle_query(self, request):
        query = request.data.get("query", "")
        location = request.data.get("location", "Delhi")
        language = request.data.get("language", "en")

        if not query:
            return Response({"error": "Query required"}, status=status.HTTP_400_BAD_REQUEST)

        # Enrich prompt with real-time context
        weather = weather_service.get_weather(location)
        prices = market_service.get_prices(location)

        enriched_prompt = f"""
Location: {location}
Language: {"Hindi" if language in ("hi", "hindi") else "English"}

Current Weather: {weather.get("current", {}).get("temperature")}°C, 
  {weather.get("current", {}).get("condition")}, 
  Humidity: {weather.get("current", {}).get("humidity")}%

Top 3 Market Prices Today:
{chr(10).join([f"- {c['crop_name']}: ₹{c['modal_price']}/q" for c in prices.get("top_crops", [])[:3]])}

User Question: {query}
"""
        response_text = gemini_service.generate(enriched_prompt, self.SYSTEM_PROMPT)

        return Response({
            "status": "success",
            "query": query,
            "response": response_text,
            "location": location,
            "data_source": "Gemini AI + Real-time Gov Data",
            "timestamp": datetime.now().isoformat(),
            "context": {
                "weather": weather.get("current"),
                "top_prices": prices.get("top_crops", [])[:3],
            }
        })


class IoTBlockchainViewSet(viewsets.ViewSet):
    """IoT + Blockchain simulation endpoint"""
    permission_classes = [AllowAny]

    @action(detail=False, methods=["get"])
    def sensor_data(self, request):
        location = request.GET.get("location", "Delhi")
        data = iot_blockchain.get_iot_sensor_data(location)
        return Response(data)

    def list(self, request):
        return self.sensor_data(request)
