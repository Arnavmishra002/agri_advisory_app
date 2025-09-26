from django.shortcuts import render
from rest_framework import viewsets
from .serializers import CropAdvisorySerializer
from .models import CropAdvisory
from rest_framework.decorators import action
from rest_framework.response import Response
from .ai_models import predict_yield, get_chatbot_response
from .fertilizer_recommendations import FertilizerRecommendationEngine
from .ml_models import AgriculturalMLSystem
from .feedback_system import FeedbackAnalytics
from .models import UserFeedback, MLModelPerformance, UserSession
import uuid
from .weather_api import MockWeatherAPI
from .market_api import get_mock_market_prices, get_mock_trending_crops

# Create your views here.

class CropAdvisoryViewSet(viewsets.ModelViewSet):
    queryset = CropAdvisory.objects.all()
    serializer_class = CropAdvisorySerializer
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ml_system = AgriculturalMLSystem()
        self.feedback_analytics = FeedbackAnalytics()

    @action(detail=False, methods=['post'])
    def predict_yield(self, request):
        crop_type = request.data.get('crop_type')
        soil_type = request.data.get('soil_type')
        weather_data = request.data.get('weather_data')
        
        # Get additional parameters for ML prediction
        temperature = request.data.get('temperature', 25.0)
        rainfall = request.data.get('rainfall', 800.0)
        humidity = request.data.get('humidity', 60.0)
        ph = request.data.get('ph', 6.5)
        organic_matter = request.data.get('organic_matter', 2.0)
        season = request.data.get('season', 'kharif')
        
        # Use ML system for prediction
        ml_result = self.ml_system.predict_yield(
            crop_type=crop_type,
            soil_type=soil_type,
            season=season,
            temperature=float(temperature),
            rainfall=float(rainfall),
            humidity=float(humidity),
            ph=float(ph),
            organic_matter=float(organic_matter)
        )
        
        # Fallback to original prediction if ML fails
        if 'error' in ml_result:
            result = predict_yield(crop_type, soil_type, weather_data)
            result['ml_enhanced'] = False
        else:
            result = ml_result
            result['ml_enhanced'] = True
        
        return Response(result)


    @action(detail=False, methods=['post'])
    def chatbot(self, request):
        user_query = request.data.get('query')
        language = request.data.get('language', 'en')
        user_id = request.data.get('user_id', 'anonymous')
        session_id = request.data.get('session_id', str(uuid.uuid4()))
        
        # Get chatbot response
        response = get_chatbot_response(user_query, language)
        
        # Check if this is a prediction request that can be enhanced with ML
        if any(keyword in user_query.lower() for keyword in ['crop recommendation', 'fertilizer', 'yield prediction']):
            # Extract parameters for ML enhancement
            ml_enhanced_response = self._enhance_chatbot_with_ml(user_query, language, user_id)
            if ml_enhanced_response:
                response = ml_enhanced_response
        
        return Response({
            'response': response,
            'session_id': session_id,
            'ml_enhanced': 'ml_enhanced' in response if isinstance(response, str) else False
        })
    
    @action(detail=False, methods=['post'])
    def fertilizer_recommendation(self, request):
        crop_type = request.data.get('crop_type')
        soil_type = request.data.get('soil_type')
        season = request.data.get('season', 'kharif')
        area_hectares = request.data.get('area_hectares', 1.0)
        language = request.data.get('language', 'en')
        
        if not crop_type or not soil_type:
            return Response({"error": "crop_type and soil_type are required"}, status=400)
        
        fertilizer_engine = FertilizerRecommendationEngine()
        recommendation = fertilizer_engine.get_fertilizer_recommendation(
            crop_type, soil_type, season, area_hectares, language
        )
        
        return Response(recommendation)
    
    @action(detail=False, methods=['post'])
    def ml_crop_recommendation(self, request):
        """Get ML-enhanced crop recommendations"""
        soil_type = request.data.get('soil_type')
        season = request.data.get('season', 'kharif')
        temperature = request.data.get('temperature', 25.0)
        rainfall = request.data.get('rainfall', 800.0)
        humidity = request.data.get('humidity', 60.0)
        ph = request.data.get('ph', 6.5)
        organic_matter = request.data.get('organic_matter', 2.0)
        user_id = request.data.get('user_id', 'anonymous')
        
        # Get ML prediction
        result = self.ml_system.predict_crop_recommendation(
            soil_type=soil_type,
            season=season,
            temperature=float(temperature),
            rainfall=float(rainfall),
            humidity=float(humidity),
            ph=float(ph),
            organic_matter=float(organic_matter)
        )
        
        # Add personalized recommendations if user_id provided
        if user_id != 'anonymous':
            personalized_result = self.ml_system.get_personalized_recommendations(
                user_id=user_id,
                input_data={
                    'soil_type': soil_type,
                    'season': season,
                    'temperature': temperature,
                    'rainfall': rainfall,
                    'humidity': humidity,
                    'ph': ph,
                    'organic_matter': organic_matter
                }
            )
            if 'error' not in personalized_result:
                result = personalized_result
        
        return Response(result)
    
    @action(detail=False, methods=['post'])
    def ml_fertilizer_recommendation(self, request):
        """Get ML-enhanced fertilizer recommendations"""
        crop_type = request.data.get('crop_type')
        soil_type = request.data.get('soil_type')
        season = request.data.get('season', 'kharif')
        temperature = request.data.get('temperature', 25.0)
        rainfall = request.data.get('rainfall', 800.0)
        humidity = request.data.get('humidity', 60.0)
        ph = request.data.get('ph', 6.5)
        organic_matter = request.data.get('organic_matter', 2.0)
        
        # Get ML prediction
        result = self.ml_system.predict_fertilizer_needs(
            crop_type=crop_type,
            soil_type=soil_type,
            season=season,
            temperature=float(temperature),
            rainfall=float(rainfall),
            humidity=float(humidity),
            ph=float(ph),
            organic_matter=float(organic_matter)
        )
        
        return Response(result)
    
    @action(detail=False, methods=['post'])
    def collect_feedback(self, request):
        """Collect user feedback for ML model improvement"""
        user_id = request.data.get('user_id')
        session_id = request.data.get('session_id')
        prediction_type = request.data.get('prediction_type')
        input_data = request.data.get('input_data')
        system_prediction = request.data.get('system_prediction')
        actual_result = request.data.get('actual_result')
        feedback_rating = request.data.get('feedback_rating')
        feedback_text = request.data.get('feedback_text', '')
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        
        if not all([user_id, session_id, prediction_type, input_data, system_prediction, actual_result, feedback_rating]):
            return Response({"error": "Missing required fields"}, status=400)
        
        # Collect feedback
        success = self.feedback_analytics.collect_feedback(
            user_id=user_id,
            session_id=session_id,
            prediction_type=prediction_type,
            input_data=input_data,
            system_prediction=system_prediction,
            actual_result=actual_result,
            feedback_rating=int(feedback_rating),
            feedback_text=feedback_text,
            latitude=latitude,
            longitude=longitude
        )
        
        if success:
            # Also collect feedback in ML system
            self.ml_system.collect_feedback(
                user_id=user_id,
                prediction_type=prediction_type,
                input_data=input_data,
                prediction=system_prediction,
                actual_result=actual_result,
                feedback_rating=int(feedback_rating)
            )
            
            return Response({"message": "Feedback collected successfully"})
        else:
            return Response({"error": "Failed to collect feedback"}, status=500)
    
    @action(detail=False, methods=['get'])
    def feedback_analytics(self, request):
        """Get feedback analytics"""
        days = int(request.query_params.get('days', 30))
        analytics = self.feedback_analytics.get_feedback_analytics(days=days)
        return Response(analytics)
    
    @action(detail=False, methods=['get'])
    def model_performance(self, request):
        """Get ML model performance metrics"""
        performance = self.ml_system.get_model_performance()
        return Response(performance)
    
    @action(detail=False, methods=['get'])
    def user_feedback_history(self, request):
        """Get user feedback history"""
        user_id = request.query_params.get('user_id')
        limit = int(request.query_params.get('limit', 50))
        
        if not user_id:
            return Response({"error": "user_id is required"}, status=400)
        
        history = self.feedback_analytics.get_user_feedback_history(user_id, limit)
        return Response(history)
    
    def _enhance_chatbot_with_ml(self, user_query: str, language: str, user_id: str) -> str:
        """Enhance chatbot response with ML predictions"""
        try:
            user_query_lower = user_query.lower()
            
            # Extract parameters from query
            soil_type = "loamy"  # default
            season = "kharif"  # default
            temperature = 25.0
            rainfall = 800.0
            humidity = 60.0
            ph = 6.5
            organic_matter = 2.0
            
            # Extract soil type
            if "clayey" in user_query_lower or "clay" in user_query_lower:
                soil_type = "clayey"
            elif "sandy" in user_query_lower:
                soil_type = "sandy"
            elif "silty" in user_query_lower or "silt" in user_query_lower:
                soil_type = "silty"
            
            # Extract season
            if "rabi" in user_query_lower:
                season = "rabi"
            elif "zaid" in user_query_lower:
                season = "zaid"
            
            # Check if this is a crop recommendation query
            if any(keyword in user_query_lower for keyword in ['crop recommendation', 'what to plant', 'crop suggestion']):
                result = self.ml_system.predict_crop_recommendation(
                    soil_type=soil_type,
                    season=season,
                    temperature=temperature,
                    rainfall=rainfall,
                    humidity=humidity,
                    ph=ph,
                    organic_matter=organic_matter
                )
                
                if 'error' not in result:
                    recommendations = result['recommendations']
                    response = f"Based on ML analysis of your {soil_type} soil in {season} season, here are my recommendations:\n\n"
                    
                    for i, rec in enumerate(recommendations[:3], 1):
                        confidence = "High" if rec['probability'] > 0.7 else "Medium" if rec['probability'] > 0.4 else "Low"
                        response += f"{i}. {rec['crop']} (Confidence: {confidence})\n"
                    
                    response += f"\nModel Accuracy: {result['model_accuracy']:.2%}"
                    return response
            
            # Check if this is a fertilizer query
            elif "fertilizer" in user_query_lower:
                # Extract crop type
                crops = ["wheat", "rice", "maize", "sugarcane", "cotton", "tomato"]
                crop_type = None
                for crop in crops:
                    if crop in user_query_lower:
                        crop_type = crop
                        break
                
                if crop_type:
                    result = self.ml_system.predict_fertilizer_needs(
                        crop_type=crop_type,
                        soil_type=soil_type,
                        season=season,
                        temperature=temperature,
                        rainfall=rainfall,
                        humidity=humidity,
                        ph=ph,
                        organic_matter=organic_matter
                    )
                    
                    if 'error' not in result:
                        response = f"ML-based fertilizer recommendation for {crop_type} in {soil_type} soil:\n\n"
                        response += f"Nitrogen: {result['nitrogen']:.1f} kg/hectare\n"
                        response += f"Phosphorus: {result['phosphorus']:.1f} kg/hectare\n"
                        response += f"Potassium: {result['potassium']:.1f} kg/hectare\n"
                        response += f"\nModel R² Score: {result['model_r2']:.3f}"
                        return response
            
            return None
            
        except Exception as e:
            logger.error(f"Error enhancing chatbot with ML: {e}")
            return None


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
