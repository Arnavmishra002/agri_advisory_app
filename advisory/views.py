from django.shortcuts import render
from rest_framework import viewsets
from .serializers import CropAdvisorySerializer
from .models import CropAdvisory
from rest_framework.decorators import action
from rest_framework.response import Response
from .ai_models import predict_yield, detect_pest_disease, get_chatbot_response
from .weather_api import WeatherAPI
from .text_to_speech import convert_text_to_speech
from .market_api import get_mock_market_prices

# Create your views here.

class CropAdvisoryViewSet(viewsets.ModelViewSet):
    queryset = CropAdvisory.objects.all()
    serializer_class = CropAdvisorySerializer

    @action(detail=False, methods=['post'])
    def predict_yield(self, request):
        crop_type = request.data.get('crop_type')
        soil_type = request.data.get('soil_type')
        weather_data = request.data.get('weather_data')
        result = predict_yield(crop_type, soil_type, weather_data)
        return Response(result)

    @action(detail=False, methods=['post'])
    def detect_pest_disease(self, request):
        image_upload = request.data.get('image')
        latitude = request.data.get('latitude', None)
        longitude = request.data.get('longitude', None)
        
        result = detect_pest_disease(image_upload, latitude, longitude)
        return Response(result)

    @action(detail=False, methods=['post'])
    def chatbot(self, request):
        user_query = request.data.get('query')
        language = request.data.get('language', 'en')
        response = get_chatbot_response(user_query, language)
        return Response({'response': response})


class WeatherViewSet(viewsets.ViewSet):
    """
    A simple ViewSet for retrieving weather data.
    """
    @action(detail=False, methods=['get'])
    def current(self, request):
        location = request.query_params.get('location', None)
        if not location:
            return Response({"error": "Location parameter is required"}, status=400)
        
        weather_api = WeatherAPI()
        weather_data = weather_api.get_current_weather(location)
        
        if weather_data:
            return Response(weather_data)
        return Response({"error": "Could not retrieve weather data"}, status=500)

    @action(detail=False, methods=['get'])
    def forecast(self, request):
        location = request.query_params.get('location', None)
        days = request.query_params.get('days', 3) # Default to 3 days forecast
        
        if not location:
            return Response({"error": "Location parameter is required"}, status=400)

        try:
            days = int(days)
        except ValueError:
            return Response({"error": "Days parameter must be an integer"}, status=400)
        
        weather_api = WeatherAPI()
        forecast_data = weather_api.get_forecast_weather(location, days)
        
        if forecast_data:
            return Response(forecast_data)
        return Response({"error": "Could not retrieve forecast data"}, status=500)


class TextToSpeechViewSet(viewsets.ViewSet):
    """
    A simple ViewSet for converting text to speech.
    """
    @action(detail=False, methods=['post'])
    def speak(self, request):
        text = request.data.get('text', None)
        language = request.data.get('language', 'en') # Get language from request, default to English
        if not text:
            return Response({"error": "Text parameter is required"}, status=400)
        
        audio_url = convert_text_to_speech(text, lang=language)

        if audio_url:
            return Response({"audio_url": request.build_absolute_uri(audio_url)})
        return Response({"error": "Could not convert text to speech"}, status=500)


class MarketPricesViewSet(viewsets.ViewSet):
    """
    A simple ViewSet for retrieving real-time market prices.
    """
    @action(detail=False, methods=['get'])
    def prices(self, request):
        product_type = request.query_params.get('product', None)
        location = request.query_params.get('location', None)
        
        market_data = get_mock_market_prices(product_type, location)
        
        if market_data:
            return Response(market_data)
        return Response({"error": "Could not retrieve market data"}, status=500)
