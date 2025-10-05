from django.shortcuts import render
from rest_framework import viewsets, status, serializers, permissions
from ..models import CropAdvisory, Crop, UserFeedback, MLModelPerformance, UserSession, User, ForumPost
from rest_framework.decorators import action
from rest_framework.response import Response
from ..ml.ai_models import predict_yield
from ..ml.fertilizer_recommendations import FertilizerRecommendationEngine
from ..ml.ml_models import AgriculturalMLSystem
from ..feedback_system import FeedbackAnalytics
from ..ml.conversational_chatbot import ConversationalAgriculturalChatbot
import uuid
from ..services.weather_api import MockWeatherAPI
from ..services.market_api import get_market_prices, get_trending_crops
from ..services.pest_detection import PestDetectionSystem
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.core.files.uploadedfile import File
from ..permissions import IsAdmin, IsOfficer, IsFarmer, IsOwnerOrReadOnly
from ..utils import convert_text_to_speech
from .serializers import (CropAdvisorySerializer, CropSerializer, UserSerializer, SMSSerializer, 
                         IVRInputSerializer, PestDetectionSerializer, TextToSpeechSerializer, 
                         ForumPostSerializer, YieldPredictionSerializer, ChatbotSerializer, 
                         FertilizerRecommendationSerializer, CropRecommendationSerializer, FeedbackSerializer)

# Enhanced imports for security and caching
try:
    from ..cache_utils import cache_result, cache_api_response, cache_manager
    from ..security_utils import secure_api_endpoint, security_validator
    ENHANCED_FEATURES = True
except ImportError:
    ENHANCED_FEATURES = False
    cache_result = lambda *args, **kwargs: lambda func: func
    cache_api_response = lambda *args, **kwargs: lambda func: func
    secure_api_endpoint = lambda *args, **kwargs: lambda func: func

# Create your views here.

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin] # Only admins can manage users directly

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action == 'create':
            # Allow any user to register, but role will be default to 'farmer'
            self.permission_classes = [] 
        elif self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            # Admins can manage any user, users can view/update their own profile
            self.permission_classes = [IsAdmin | (IsFarmer & self.is_owner)] 
        return [permission() for permission in self.permission_classes]

    def is_owner(self):
        user_id = self.kwargs.get('pk') # For retrieve, update, partial_update, destroy
        return str(self.request.user.id) == user_id

class CropViewSet(viewsets.ModelViewSet):
    queryset = Crop.objects.all()
    serializer_class = CropSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['ideal_soil_type', 'min_temperature_c', 'max_temperature_c', 'min_rainfall_mm_per_month', 'max_rainfall_mm_per_month', 'duration_days']
    search_fields = ['name', 'description']

class CropAdvisoryViewSet(viewsets.ModelViewSet):
    queryset = CropAdvisory.objects.all()
    serializer_class = CropAdvisorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['crop__name', 'soil_type', 'weather_condition', 'created_at']
    search_fields = ['recommendation', 'crop__name']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ml_system = AgriculturalMLSystem()
        self.feedback_analytics = FeedbackAnalytics()
        self.weather_api = MockWeatherAPI() # Use the actual weather API
        self.nlp_chatbot = ConversationalAgriculturalChatbot() # Initialize the conversational chatbot
        self.pest_detection_system = PestDetectionSystem() # Initialize the pest detection system

    @action(detail=False, methods=['post'], serializer_class=YieldPredictionSerializer)
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


    @action(detail=False, methods=['post'], serializer_class=ChatbotSerializer)
    def chatbot(self, request):
        # Enhanced security validation
        if ENHANCED_FEATURES:
            request_data = {
                'query': request.data.get('query'),
                'language': request.data.get('language', 'auto'),
                'user_id': request.data.get('user_id', 'anonymous'),
                'session_id': request.data.get('session_id', str(uuid.uuid4()))
            }
            
            validation = security_validator.validate_api_request(request_data)
            if not validation['valid']:
                return Response({
                    'error': 'Validation failed',
                    'errors': validation['errors']
                }, status=400)
            
            # Use sanitized data
            user_query = validation['sanitized_data']['query']
            language = validation['sanitized_data']['language']
            user_id = validation['sanitized_data'].get('user_id', 'anonymous')
            session_id = validation['sanitized_data'].get('session_id', str(uuid.uuid4()))
        else:
            # Fallback for basic validation
            user_query = request.data.get('query')
            language = request.data.get('language', 'auto')
            user_id = request.data.get('user_id', 'anonymous')
            session_id = request.data.get('session_id', str(uuid.uuid4()))
            
            if not user_query or not user_query.strip():
                return Response({
                    'error': 'Query is required and cannot be empty'
                }, status=400)
        
        try:
            # Get enhanced chatbot response with ChatGPT-like capabilities
        chatbot_response = self.nlp_chatbot.get_response(user_query, language)
            
            # Extract response data
            response = chatbot_response.get('response', 'Sorry, I could not process your request.')
            source = chatbot_response.get('source', 'conversational_ai')
        confidence = chatbot_response.get('confidence', 0.8)
            detected_language = chatbot_response.get('detected_language', language)
            response_type = chatbot_response.get('response_type', 'general')
            
            # Enhanced metadata
            metadata = chatbot_response.get('metadata', {})
            
            # Determine if ML enhancement was used
            ml_enhanced = (
                source in ['advanced_chatbot', 'nlp_model'] and 
                confidence > 0.5 and
                response_type in ['agricultural', 'weather', 'market']
            )
        
        return Response({
            'response': response,
            'session_id': session_id,
            'source': source,
            'confidence': confidence,
                'language': detected_language,
                'response_type': response_type,
                'ml_enhanced': ml_enhanced,
                'timestamp': chatbot_response.get('timestamp'),
                'metadata': {
                    'has_location': metadata.get('has_location', False),
                    'has_product': metadata.get('has_product', False),
                    'conversation_length': metadata.get('conversation_length', 0),
                    'user_id': user_id
                }
            })
            
        except Exception as e:
            # Handle errors gracefully
            return Response({
                'response': f"I apologize, but I encountered an error processing your request. Please try again or rephrase your question.",
                'session_id': session_id,
                'source': 'error',
                'confidence': 0.1,
                'error': str(e),
                'ml_enhanced': False
            }, status=500)
    
    @action(detail=False, methods=['post'], serializer_class=FertilizerRecommendationSerializer)
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
    
    @action(detail=False, methods=['post'], serializer_class=CropRecommendationSerializer)
    def ml_crop_recommendation(self, request):
        """Get ML-enhanced crop recommendations"""
        serializer = CropRecommendationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        soil_type = validated_data['soil_type']
        latitude = validated_data['latitude']
        longitude = validated_data['longitude']
        season = validated_data['season']
        user_id = validated_data['user_id']
        forecast_days = validated_data['forecast_days']

        try:
            # Fetch future weather data
            forecast = self.weather_api.get_forecast_weather(latitude, longitude, language='en', days=forecast_days)

            if not forecast or 'forecast' not in forecast or not forecast['forecast']['forecastday']:
                return Response({"error": "Could not retrieve valid weather forecast data"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Extract average forecast conditions
            avg_min_temp = sum([day['day']['mintemp_c'] for day in forecast['forecast']['forecastday']]) / forecast_days
            avg_max_temp = sum([day['day']['maxtemp_c'] for day in forecast['forecast']['forecastday']]) / forecast_days
            total_rainfall_mm = sum([day['day']['totalprecip_mm'] for day in forecast['forecast']['forecastday']]) if 'totalprecip_mm' in forecast['forecast']['forecastday'][0]['day'] else 0
            # Assuming humidity from current or an average; for simplicity, let's use a default if not available
            avg_humidity = sum([day['day']['avghumidity'] for day in forecast['forecast']['forecastday']]) / forecast_days if 'avghumidity' in forecast['forecast']['forecastday'][0]['day'] else 60.0

            # Get all crops
            all_crops = Crop.objects.all()

            # Filter suitable crops based on soil, weather forecast, and duration
            suitable_crops = []
            for crop in all_crops:
                is_suitable_soil = crop.ideal_soil_type.lower() == soil_type.lower()
                is_suitable_temp = (crop.min_temperature_c <= avg_max_temp and
                                    crop.max_temperature_c >= avg_min_temp)
                is_suitable_rainfall = (crop.min_rainfall_mm_per_month <= (total_rainfall_mm / forecast_days * 30) and # Approx monthly rainfall
                                        crop.max_rainfall_mm_per_month >= (total_rainfall_mm / forecast_days * 30))

                if is_suitable_soil and is_suitable_temp and is_suitable_rainfall:
                    suitable_crops.append({
                        'crop': crop.name,
                        'description': crop.description,
                        'duration_days': crop.duration_days,
                        'suitability_score': 1.0 # Placeholder
                    })
            
            ml_predictions = self.ml_system.predict_crop_recommendation(
                soil_type=soil_type,
                season=season,
                temperature=avg_max_temp,
                rainfall=total_rainfall_mm,
                humidity=avg_humidity,
                ph=6.5, # Placeholder, will need actual soil pH
                organic_matter=2.0 # Placeholder
            )

            final_recommendations = suitable_crops
            if 'error' not in ml_predictions and 'recommendations' in ml_predictions:
                for ml_rec in ml_predictions['recommendations']:
                    if not any(crop['crop'] == ml_rec['crop'] for crop in final_recommendations):
                        final_recommendations.append({
                            'crop': ml_rec['crop'],
                            'description': 'ML-suggested crop',
                            'duration_days': 'N/A', 
                            'suitability_score': ml_rec['probability']
                        })
            
            final_recommendations.sort(key=lambda x: x.get('suitability_score', 0), reverse=True)

            return Response({
                "recommendations": final_recommendations,
                "weather_forecast_summary": {
                    "avg_min_temp_c": avg_min_temp,
                    "avg_max_temp_c": avg_max_temp,
                    "total_rainfall_mm": total_rainfall_mm,
                    "forecast_days": forecast_days,
                    "avg_humidity": avg_humidity
                }
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"An internal server error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
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
    
    @action(detail=False, methods=['post'], serializer_class=FeedbackSerializer)
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
    
    # Removed _enhance_chatbot_with_ml method


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


class TextToSpeechViewSet(viewsets.ViewSet):
    """
    A simple ViewSet for converting text to speech.
    """
    @action(detail=False, methods=['post'])
    def speak(self, request):
        serializer = TextToSpeechSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        text = serializer.validated_data['text']
        language = serializer.validated_data['language']
        
        audio_url = convert_text_to_speech(text, lang=language)

        if audio_url:
            return Response({"audio_url": request.build_absolute_uri(audio_url)}, status=status.HTTP_200_OK)
        return Response({"error": "Could not convert text to speech"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ForumPostViewSet(viewsets.ModelViewSet):
    queryset = ForumPost.objects.all()
    serializer_class = ForumPostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly] # Only authenticated users can create, owner can edit/delete
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

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

        market_data = get_market_prices(latitude, longitude, language, product_type) # Updated function call
        
        if market_data:
            print(f"MarketPricesViewSet: Returning market_data = {market_data}")
            return Response(market_data)
        return Response({"error": "Could not retrieve market data"}, status=500)

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

        trending_crops_data = get_trending_crops(latitude, longitude, language) # Updated function call

        if trending_crops_data:
            return Response(trending_crops_data)
        return Response({"error": "Could not retrieve trending crops data"}, status=500)

class SMSIVRViewSet(viewsets.ViewSet):
    """
    A simple ViewSet for SMS and IVR integration hooks.
    """

    @action(detail=False, methods=['post'])
    def receive_sms(self, request):
        serializer = SMSSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        phone_number = serializer.validated_data['phone_number']
        message = serializer.validated_data['message']

        # Process the incoming SMS (e.g., integrate with chatbot, trigger alerts)
        response_message = f"SMS from {phone_number} received: '{message}'. Thank you."
        # In a real scenario, you'd call a function from sms_ivr.py to process and respond
        # Example: handle_incoming_sms(phone_number, message)

        return Response({"status": "success", "response": response_message}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def ivr_input(self, request):
        serializer = IVRInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        phone_number = serializer.validated_data['phone_number']
        user_input = serializer.validated_data['user_input']

        # Process IVR input (e.g., call a function from sms_ivr.py)
        # Example: ivr_response = handle_ivr_input(phone_number, user_input)
        response_message = f"IVR input from {phone_number} received: '{user_input}'."

        return Response({"status": "success", "response": response_message}, status=status.HTTP_200_OK)

class PestDetectionViewSet(viewsets.ViewSet):
    """
    A simple ViewSet for uploading images and detecting pests.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pest_detection_system = PestDetectionSystem()

    @action(detail=False, methods=['post'])
    def detect(self, request):
        serializer = PestDetectionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        image_file: File = serializer.validated_data['image']
        
        # Read image data
        image_data = image_file.read()

        # Perform pest detection
        detection_results = self.pest_detection_system.detect_pests(image_data)

        if not detection_results:
            return Response({"message": "No pests detected or an error occurred.", "detections": []}, status=status.HTTP_200_OK)

        return Response({"message": "Pest detection complete", "detections": detection_results}, status=status.HTTP_200_OK)
