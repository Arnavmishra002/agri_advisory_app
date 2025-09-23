from django.shortcuts import render
from rest_framework import viewsets
from .serializers import CropAdvisorySerializer
from .models import CropAdvisory
from rest_framework.decorators import action
from rest_framework.response import Response
from .ai_models import predict_yield, detect_pest_disease, get_chatbot_response
from .weather_api import MockWeatherAPI
from .market_api import get_mock_market_prices, get_mock_trending_crops

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
        latitude = request.query_params.get('lat', None)
        longitude = request.query_params.get('lon', None)
        language = request.query_params.get('lang', 'en')
        
        if not (latitude and longitude):
            return Response({"error": "Latitude and longitude parameters are required"}, status=400)
        
        # Convert latitude and longitude to float
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except ValueError:
            return Response({"error": "Latitude and longitude must be valid numbers"}, status=400)

        weather_api = MockWeatherAPI()
        weather_data = weather_api.get_current_weather(latitude, longitude, language)
        
        if weather_data:
            return Response(weather_data)
        return Response({"error": "Could not retrieve mock weather data"}, status=500)

    @action(detail=False, methods=['get'])
    def forecast(self, request):
        latitude = request.query_params.get('lat', None)
        longitude = request.query_params.get('lon', None)
        language = request.query_params.get('lang', 'en')
        days = request.query_params.get('days', 3) # Default to 3 days forecast
        
        if not (latitude and longitude):
            return Response({"error": "Latitude and longitude parameters are required"}, status=400)

        try:
            latitude = float(latitude)
            longitude = float(longitude)
            days = int(days)
        except ValueError:
            return Response({"error": "Latitude, longitude, and days parameters must be valid numbers"}, status=400)
        
        weather_api = MockWeatherAPI()
        forecast_data = weather_api.get_forecast_weather(latitude, longitude, language, days)
        
        if forecast_data:
            return Response(forecast_data)
        return Response({"error": "Could not retrieve mock forecast data"}, status=500)


# class TextToSpeechViewSet(viewsets.ViewSet):
#     """
#     A simple ViewSet for converting text to speech.
#     """
#     @action(detail=False, methods=['post'])
#     def speak(self, request):
#         text = request.data.get('text', None)
#         language = request.data.get('language', 'en') # Get language from request, default to English
#         if not text:
#             return Response({"error": "Text parameter is required"}, status=400)
        
#         audio_url = convert_text_to_speech(text, lang=language)

#         if audio_url:
#             return Response({"audio_url": request.build_absolute_uri(audio_url)})
#         return Response({"error": "Could not convert text to speech"}, status=500)


class MarketPricesViewSet(viewsets.ViewSet):
    """
    A simple ViewSet for retrieving real-time market prices.
    """
    @action(detail=False, methods=['get'])
    def prices(self, request):
        product_type = request.query_params.get('product', None)
        latitude = request.query_params.get('lat', None)
        longitude = request.query_params.get('lon', None)
        language = request.query_params.get('lang', 'en')
        print(f"MarketPricesViewSet: Received lat={latitude}, lon={longitude}, lang={language}, product_type={product_type}")

        market_data = get_mock_market_prices(latitude, longitude, language, product_type) # Using a combined string for location in mock
        
        if market_data:
            print(f"MarketPricesViewSet: Returning market_data = {market_data}")
            return Response(market_data)
        return Response({"error": "Could not retrieve mock market data"}, status=500)

class TrendingCropsViewSet(viewsets.ViewSet):
    """
    A simple ViewSet for retrieving trending crop data.
    """
    # @action(detail=False, methods=['get'])
    def list(self, request):
        latitude = request.query_params.get('lat', None)
        longitude = request.query_params.get('lon', None)
        language = request.query_params.get('lang', 'en')

        if not (latitude and longitude):
            return Response({"error": "Latitude and longitude parameters are required"}, status=400)
        
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except ValueError:
            return Response({"error": "Latitude and longitude must be valid numbers"}, status=400)

        trending_crops_data = get_mock_trending_crops(latitude, longitude, language)

        if trending_crops_data:
            return Response(trending_crops_data)
        return Response({"error": "Could not retrieve mock trending crops data"}, status=500)
