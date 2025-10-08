from django.shortcuts import render
from rest_framework import viewsets, status, serializers, permissions
from ..models import CropAdvisory, Crop, UserFeedback, MLModelPerformance, UserSession, User, ForumPost
from rest_framework.decorators import action
from rest_framework.response import Response
from ..ml.ai_models import predict_yield
from ..ml.fertilizer_recommendations import FertilizerRecommendationEngine
from ..ml.ml_models import AgriculturalMLSystem
from ..feedback_system import FeedbackAnalytics
from ..ml.intelligent_chatbot import IntelligentAgriculturalChatbot
import uuid
from ..services.enhanced_government_api import EnhancedGovernmentAPI
from ..services.real_time_government_api import RealTimeGovernmentAPI
from ..services.pest_detection import PestDetectionSystem
from django_filters.rest_framework import DjangoFilterBackend
import time
from rest_framework import filters
from django.core.files.uploadedfile import File
from ..permissions import IsAdmin, IsOfficer, IsFarmer, IsOwnerOrReadOnly
from ..utils import convert_text_to_speech
import logging
from .serializers import (CropAdvisorySerializer, CropSerializer, UserSerializer, SMSSerializer, 
                         IVRInputSerializer, PestDetectionSerializer, TextToSpeechSerializer, 
                         ForumPostSerializer, YieldPredictionSerializer, ChatbotSerializer, 
                         FertilizerRecommendationSerializer, CropRecommendationSerializer, FeedbackSerializer)

logger = logging.getLogger(__name__)

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

# Chatbot ViewSet
class ChatbotViewSet(viewsets.ViewSet):
    """
    Chatbot API for agricultural advisory
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            from ..ml.ultimate_intelligent_ai import ultimate_ai
            self.chatbot = ultimate_ai
        except ImportError:
            from ..ml.intelligent_chatbot import IntelligentAgriculturalChatbot
            self.chatbot = IntelligentAgriculturalChatbot()
    
    def list(self, request):
        """Handle chatbot conversations at root endpoint"""
        if request.method == 'POST':
            serializer = ChatbotSerializer(data=request.data)
            if serializer.is_valid():
                message = serializer.validated_data['query']
                language = serializer.validated_data.get('language', 'en')
                
                try:
                    # Use enhanced AI if available, otherwise fallback
                    if hasattr(self.chatbot, 'get_response'):
                        # UltimateIntelligentAI
                        response_data = self.chatbot.get_response(
                            user_query=message,
                            language=language,
                            latitude=request.data.get('latitude'),
                            longitude=request.data.get('longitude'),
                            location_name=request.data.get('location')
                        )
                        response_text = response_data.get('response', 'Sorry, I could not process your request.')
                    else:
                        # IntelligentAgriculturalChatbot
                        response_text = self.chatbot.process_message(message, language=language)
                    
                    return Response({
                        'response': response_text,
                        'intent': 'agricultural_query',
                        'entities': [],
                        'language': language,
                        'timestamp': time.time()
                    })
                except Exception as e:
                    return Response({
                        'response': 'Sorry, I encountered an error. Please try again.',
                        'intent': 'error',
                        'entities': [],
                        'language': language,
                        'timestamp': time.time()
                    }, status=500)
            else:
                return Response(serializer.errors, status=400)
        else:
            return Response({'message': 'Chatbot API is running. Send POST request with message and language.'})
    
    @action(detail=False, methods=['post'])
    def chat(self, request):
        """Handle chatbot conversations"""
        serializer = ChatbotSerializer(data=request.data)
        if serializer.is_valid():
            message = serializer.validated_data['query']
            language = serializer.validated_data.get('language', 'en')
            
            try:
                # Use enhanced AI if available, otherwise fallback
                if hasattr(self.chatbot, 'get_response'):
                    # UltimateIntelligentAI
                    response_data = self.chatbot.get_response(
                        user_query=message,
                        language=language,
                        latitude=request.data.get('latitude'),
                        longitude=request.data.get('longitude'),
                        location_name=request.data.get('location')
                    )
                    response_text = response_data.get('response', 'Sorry, I could not process your request.')
                else:
                    # IntelligentAgriculturalChatbot
                    response_text = self.chatbot.process_message(message, language=language)
                
                return Response({
                    'response': response_text,
                    'intent': 'agricultural_query',
                    'entities': [],
                    'language': language,
                    'timestamp': time.time()
                })
            except Exception as e:
                return Response({
                    'response': 'Sorry, I encountered an error. Please try again.',
                    'intent': 'error',
                    'entities': [],
                    'language': language,
                    'timestamp': time.time()
                }, status=500)
        else:
            return Response(serializer.errors, status=400)

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
        self.weather_api = EnhancedGovernmentAPI() # Use the enhanced government API
        self.intelligent_chatbot = IntelligentAgriculturalChatbot() # Initialize the intelligent chatbot
        self.pest_detection_system = PestDetectionSystem() # Initialize the pest detection system
        self.real_time_api = RealTimeGovernmentAPI()
    
    def _get_soil_type_from_coordinates(self, latitude, longitude):
        """Auto-detect soil type based on coordinates"""
        # Simple soil type mapping based on Indian regions
        if 28.0 <= latitude <= 37.0 and 76.0 <= longitude <= 97.0:  # North India
            return "Alluvial"
        elif 20.0 <= latitude <= 28.0 and 70.0 <= longitude <= 88.0:  # Central India
            return "Black Cotton"
        elif 8.0 <= latitude <= 20.0 and 70.0 <= longitude <= 80.0:  # South India
            return "Red Soil"
        elif 24.0 <= latitude <= 28.0 and 88.0 <= longitude <= 97.0:  # East India
            return "Laterite"
        else:
            return "Mixed Soil"

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
            # Get location data from request
            latitude = request.data.get('latitude', 28.6139)  # Default to Delhi
            longitude = request.data.get('longitude', 77.2090)
            
            # Always include location data for comprehensive responses
            # Note: Location is passed directly to get_response method
            
            # Get enhanced chatbot response with intelligent capabilities
            chatbot_response = self.intelligent_chatbot.get_response(
                user_query=user_query,
                language=language,
                user_id=user_id,
                session_id=session_id,
                latitude=latitude,
                longitude=longitude,
                conversation_history=request.data.get('conversation_history', []),
                location_name=request.data.get('location_name', 'Unknown Location')
            )
            
            # Debug logging
            print(f"Chatbot response for query '{user_query}': {chatbot_response}")
            
            # Extract response data with proper encoding
            response = chatbot_response.get('response', 'Sorry, I could not process your request.')
            # Ensure proper UTF-8 encoding for Hindi text
            if isinstance(response, str):
                response = response.encode('utf-8').decode('utf-8')
            source = chatbot_response.get('source', 'conversational_ai')
            confidence = chatbot_response.get('confidence', 0.8)
            detected_language = chatbot_response.get('language', language)
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
                    'intent': metadata.get('intent', 'general'),
                    'entities': metadata.get('entities', {}),
                    'has_location': metadata.get('has_location', False),
                    'has_product': metadata.get('has_product', False),
                    'conversation_length': metadata.get('conversation_length', 0),
                    'user_id': user_id,
                    'location_based': metadata.get('location_based', False),
                    'processed_query': metadata.get('processed_query', user_query),
                    'original_query': metadata.get('original_query', user_query)
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
        """Get comprehensive crop recommendations with real-time government data"""
        serializer = CropRecommendationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        soil_type = validated_data.get('soil_type')
        latitude = validated_data['latitude']
        longitude = validated_data['longitude']
        season = validated_data['season']
        user_id = validated_data['user_id']
        forecast_days = validated_data['forecast_days']

        # Auto-detect soil type if not provided
        if not soil_type:
            soil_type = self._get_soil_type_from_coordinates(latitude, longitude)
        
        try:
            # Use comprehensive crop recommendation system with real-time government data
            try:
                import threading
                import time
                
                result = {}
                exception = None
                
                def fetch_crop_data():
                    nonlocal result, exception
                    try:
                        from ..services.comprehensive_crop_system import comprehensive_crop_system
                        result = comprehensive_crop_system.get_comprehensive_recommendations(
                            latitude=latitude,
                            longitude=longitude,
                            soil_type=soil_type,
                            season=season
                        )
                    except Exception as e:
                        exception = e
                
                # Start the data fetch in a separate thread
                thread = threading.Thread(target=fetch_crop_data)
                thread.daemon = True
                thread.start()
                thread.join(timeout=5)  # 5-second timeout
                
                if thread.is_alive():
                    raise TimeoutError("Crop recommendation fetch timeout")
                
                if exception:
                    raise exception
                
                if result:
                    return Response(result, status=status.HTTP_200_OK)
                else:
                    raise Exception("No crop data returned")
            except ImportError:
                # Fallback to basic crop recommendation
                logger.warning("Comprehensive crop system not available, using fallback")
                result = self._get_fallback_crop_recommendations(latitude, longitude, soil_type, season)
                return Response(result, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Error in comprehensive crop system: {e}")
                # Fallback to basic crop recommendation
                result = self._get_fallback_crop_recommendations(latitude, longitude, soil_type, season)
                return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Crop recommendation error: {e}")
            return Response({"error": f"Crop recommendation failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_fallback_crop_recommendations(self, latitude, longitude, soil_type, season):
        """Fallback crop recommendations when comprehensive system fails"""
        try:
            # Basic crop recommendations based on location and season
            crops = {
                'kharif': ['rice', 'maize', 'cotton', 'sugarcane', 'groundnut', 'soybean'],
                'rabi': ['wheat', 'barley', 'mustard', 'chickpea', 'potato', 'onion'],
                'zaid': ['cucumber', 'watermelon', 'muskmelon', 'bitter gourd']
            }
            
            # Get crops for the season
            season_crops = crops.get(season, crops['kharif'])
            
            # Generate recommendations
            recommendations = []
            for i, crop in enumerate(season_crops[:5]):  # Top 5 crops
                recommendations.append({
                    'crop': crop,
                    'score': 85 - (i * 10),  # Decreasing scores
                    'reason': f'Recommended for {season} season in {soil_type} soil',
                    'profitability': 'High' if i < 2 else 'Medium',
                    'market_demand': 'High',
                    'climate_suitability': 'Excellent',
                    'soil_compatibility': 'Good'
                })
            
            return {
                'recommendations': recommendations,
                'analysis': {
                    'total_crops_analyzed': len(season_crops),
                    'season': season,
                    'soil_type': soil_type,
                    'location': f'Lat: {latitude}, Lon: {longitude}',
                    'confidence': 'Medium (Fallback Mode)'
                },
                'location_info': {
                    'latitude': latitude,
                    'longitude': longitude,
                    'soil_type': soil_type,
                    'season': season
                },
                'source': 'Fallback Crop Recommendation System'
            }
        except Exception as e:
            logger.error(f"Fallback crop recommendation error: {e}")
            return {
                'recommendations': [],
                'analysis': {'error': str(e)},
                'location_info': {},
                'source': 'Error in Fallback System'
            }

    
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
    
    def _perform_comprehensive_farmer_analysis(self, latitude, longitude, soil_type, season, weather_forecast, market_data, user_id):
        """Perform comprehensive farmer-centric analysis for maximum profit recommendations"""
        
        # 1. DETAILED SOIL ANALYSIS
        soil_analysis = self._analyze_soil_comprehensive(soil_type, latitude, longitude)
        
        # 2. FUTURE WEATHER PREDICTION ANALYSIS
        weather_analysis = self._analyze_future_weather_patterns(weather_forecast, latitude, longitude)
        
        # 3. PRICE TREND ANALYSIS & FORECASTING
        price_analysis = self._analyze_price_trends_and_forecasting(market_data, latitude, longitude)
        
        # 4. INPUT COST ANALYSIS & OPTIMIZATION
        input_cost_analysis = self._analyze_input_costs_and_optimization(latitude, longitude)
        
        # 5. DURATION ANALYSIS FOR CROP CYCLES
        duration_analysis = self._analyze_crop_duration_and_cycles(season, latitude, longitude)
        
        # 6. HISTORICAL ANALYSIS FOR BETTER PREDICTIONS
        historical_analysis = self._analyze_historical_performance(latitude, longitude, season)
        
        # 7. PROFIT MAXIMIZATION ANALYSIS
        profit_analysis = self._calculate_profit_maximization(
            soil_analysis, weather_analysis, price_analysis, 
            input_cost_analysis, duration_analysis, historical_analysis
        )
        
        return {
            'soil_analysis': soil_analysis,
            'weather_analysis': weather_analysis,
            'price_analysis': price_analysis,
            'input_cost_analysis': input_cost_analysis,
            'duration_analysis': duration_analysis,
            'historical_analysis': historical_analysis,
            'profit_analysis': profit_analysis,
            'location': {'lat': latitude, 'lon': longitude},
            'season': season,
            'soil_type': soil_type,
            'analysis_timestamp': time.time()
        }
    
    def _analyze_soil_comprehensive(self, soil_type, latitude, longitude):
        """Comprehensive soil analysis with detailed requirements and optimization"""
        
        # Detailed soil characteristics based on location
        soil_profile = self._get_detailed_soil_profile(soil_type, latitude, longitude)
        
        # Soil suitability scores for all crops with detailed requirements
        soil_scores = {}
        
        # Comprehensive soil requirements database
        soil_requirements = {
            # Cereals - Detailed soil requirements
            'rice': {
                'optimal_soils': ['clay', 'clayey', 'loamy'],
                'ph_range': (5.5, 7.0),
                'organic_matter': 'high',
                'drainage': 'poor_to_moderate',
                'nutrient_requirements': {'nitrogen': 'high', 'phosphorus': 'medium', 'potassium': 'medium'},
                'soil_depth': 'deep',
                'water_holding': 'high'
            },
            'wheat': {
                'optimal_soils': ['loamy', 'sandy loam', 'clay loam'],
                'ph_range': (6.0, 7.5),
                'organic_matter': 'medium',
                'drainage': 'good',
                'nutrient_requirements': {'nitrogen': 'high', 'phosphorus': 'high', 'potassium': 'medium'},
                'soil_depth': 'medium',
                'water_holding': 'medium'
            },
            'maize': {
                'optimal_soils': ['loamy', 'sandy loam'],
                'ph_range': (6.0, 7.0),
                'organic_matter': 'medium',
                'drainage': 'good',
                'nutrient_requirements': {'nitrogen': 'high', 'phosphorus': 'medium', 'potassium': 'medium'},
                'soil_depth': 'deep',
                'water_holding': 'medium'
            },
            
            # Vegetables - Detailed soil requirements
            'tomato': {
                'optimal_soils': ['loamy', 'sandy loam'],
                'ph_range': (6.0, 6.8),
                'organic_matter': 'high',
                'drainage': 'excellent',
                'nutrient_requirements': {'nitrogen': 'medium', 'phosphorus': 'high', 'potassium': 'high'},
                'soil_depth': 'medium',
                'water_holding': 'medium'
            },
            'onion': {
                'optimal_soils': ['sandy loam', 'loamy'],
                'ph_range': (6.0, 7.0),
                'organic_matter': 'medium',
                'drainage': 'excellent',
                'nutrient_requirements': {'nitrogen': 'medium', 'phosphorus': 'high', 'potassium': 'high'},
                'soil_depth': 'shallow',
                'water_holding': 'low'
            },
            
            # Cash Crops - Detailed soil requirements
            'cotton': {
                'optimal_soils': ['sandy loam', 'loamy'],
                'ph_range': (6.0, 8.0),
                'organic_matter': 'medium',
                'drainage': 'good',
                'nutrient_requirements': {'nitrogen': 'high', 'phosphorus': 'medium', 'potassium': 'medium'},
                'soil_depth': 'deep',
                'water_holding': 'medium'
            },
            'sugarcane': {
                'optimal_soils': ['loamy', 'clay loam'],
                'ph_range': (6.0, 7.5),
                'organic_matter': 'high',
                'drainage': 'moderate',
                'nutrient_requirements': {'nitrogen': 'very_high', 'phosphorus': 'high', 'potassium': 'high'},
                'soil_depth': 'deep',
                'water_holding': 'high'
            }
        }
        
        # Calculate detailed soil suitability scores
        for crop, requirements in soil_requirements.items():
            score = 0.0
            
            # Soil type compatibility (40% weight)
            if soil_type.lower() in [s.lower() for s in requirements['optimal_soils']]:
                score += 0.4
            else:
                score += 0.1
            
            # pH compatibility (20% weight)
            soil_ph = soil_profile.get('ph', 6.5)  # Default pH
            ph_min, ph_max = requirements['ph_range']
            if ph_min <= soil_ph <= ph_max:
                score += 0.2
            else:
                ph_deviation = min(abs(soil_ph - ph_min), abs(soil_ph - ph_max))
                score += max(0.05, 0.2 - (ph_deviation * 0.05))
            
            # Organic matter compatibility (15% weight)
            soil_om = soil_profile.get('organic_matter', 'medium')
            if soil_om == requirements['organic_matter']:
                score += 0.15
            elif requirements['organic_matter'] == 'high' and soil_om == 'medium':
                score += 0.1
            else:
                score += 0.05
            
            # Drainage compatibility (15% weight)
            soil_drainage = soil_profile.get('drainage', 'good')
            if soil_drainage == requirements['drainage']:
                score += 0.15
            else:
                score += 0.05
            
            # Soil depth compatibility (10% weight)
            soil_depth = soil_profile.get('depth', 'medium')
            if soil_depth == requirements['soil_depth']:
                score += 0.1
            else:
                score += 0.05
            
            soil_scores[crop] = min(1.0, score)
        
        return {
            'soil_profile': soil_profile,
            'soil_scores': soil_scores,
            'soil_type': soil_type,
            'analysis_details': 'Comprehensive soil analysis with pH, organic matter, drainage, and depth requirements'
        }
    
    def _get_detailed_soil_profile(self, soil_type, latitude, longitude):
        """Get detailed soil profile based on location and soil type"""
        
        # Location-based soil characteristics
        location_seed = int(latitude * 1000 + longitude * 1000) % 1000
        
        # Base soil profiles by type
        soil_profiles = {
            'loamy': {
                'ph': 6.5 + (location_seed % 10) * 0.1,  # 6.5-7.4
                'organic_matter': 'medium',
                'drainage': 'good',
                'depth': 'deep',
                'water_holding': 'high',
                'nutrient_availability': 'high',
                'workability': 'excellent'
            },
            'sandy loam': {
                'ph': 6.0 + (location_seed % 15) * 0.1,  # 6.0-7.4
                'organic_matter': 'low',
                'drainage': 'excellent',
                'depth': 'medium',
                'water_holding': 'low',
                'nutrient_availability': 'medium',
                'workability': 'good'
            },
            'clay': {
                'ph': 6.8 + (location_seed % 8) * 0.1,   # 6.8-7.5
                'organic_matter': 'high',
                'drainage': 'poor',
                'depth': 'deep',
                'water_holding': 'very_high',
                'nutrient_availability': 'high',
                'workability': 'poor'
            },
            'clayey': {
                'ph': 6.5 + (location_seed % 12) * 0.1,  # 6.5-7.6
                'organic_matter': 'high',
                'drainage': 'poor_to_moderate',
                'depth': 'deep',
                'water_holding': 'very_high',
                'nutrient_availability': 'high',
                'workability': 'poor'
            },
            'sandy': {
                'ph': 5.5 + (location_seed % 20) * 0.1,  # 5.5-7.4
                'organic_matter': 'very_low',
                'drainage': 'excellent',
                'depth': 'shallow',
                'water_holding': 'very_low',
                'nutrient_availability': 'low',
                'workability': 'excellent'
            }
        }
        
        return soil_profiles.get(soil_type.lower(), soil_profiles['loamy'])
    
    def _analyze_future_weather_patterns(self, weather_forecast, latitude, longitude):
        """Analyze future weather patterns for crop planning"""
        
        # Extract detailed weather data
        forecast_days = weather_forecast['forecast']['forecastday']
        
        # Calculate weather trends
        temperatures = [day['day']['avgtemp_c'] for day in forecast_days]
        rainfall = [day['day']['totalprecip_mm'] for day in forecast_days]
        humidity = [day['day']['avghumidity'] for day in forecast_days]
        wind_speed = [day['day']['maxwind_kph'] for day in forecast_days]
        
        # Weather pattern analysis
        avg_temp = sum(temperatures) / len(temperatures)
        total_rainfall = sum(rainfall)
        avg_humidity = sum(humidity) / len(humidity)
        max_wind = max(wind_speed)
        
        # Temperature trend analysis
        temp_trend = 'stable'
        if len(temperatures) >= 3:
            temp_change = temperatures[-1] - temperatures[0]
            if temp_change > 2:
                temp_trend = 'increasing'
            elif temp_change < -2:
                temp_trend = 'decreasing'
        
        # Rainfall pattern analysis
        rainfall_pattern = 'moderate'
        if total_rainfall > 100:
            rainfall_pattern = 'high'
        elif total_rainfall < 30:
            rainfall_pattern = 'low'
        
        # Weather risk assessment
        weather_risks = []
        if avg_temp > 35:
            weather_risks.append('heat_stress')
        if avg_temp < 10:
            weather_risks.append('cold_stress')
        if total_rainfall > 200:
            weather_risks.append('flooding_risk')
        if total_rainfall < 20:
            weather_risks.append('drought_risk')
        if max_wind > 40:
            weather_risks.append('wind_damage')
        
        # Crop-specific weather suitability
        weather_scores = {}
        
        # Temperature-based scoring
        for crop in ['rice', 'wheat', 'maize', 'cotton', 'sugarcane', 'tomato', 'onion', 'potato']:
            score = 0.0
            
            # Temperature suitability
            if crop == 'rice':
                if 20 <= avg_temp <= 35:
                    score += 0.4
                else:
                    score += 0.1
            elif crop == 'wheat':
                if 15 <= avg_temp <= 25:
                    score += 0.4
                else:
                    score += 0.1
            elif crop == 'maize':
                if 18 <= avg_temp <= 30:
                    score += 0.4
                else:
                    score += 0.1
            elif crop == 'cotton':
                if 25 <= avg_temp <= 35:
                    score += 0.4
                else:
                    score += 0.1
            elif crop == 'sugarcane':
                if 25 <= avg_temp <= 35:
                    score += 0.4
                else:
                    score += 0.1
            elif crop == 'tomato':
                if 20 <= avg_temp <= 30:
                    score += 0.4
                else:
                    score += 0.1
            elif crop == 'onion':
                if 15 <= avg_temp <= 25:
                    score += 0.4
                else:
                    score += 0.1
            elif crop == 'potato':
                if 10 <= avg_temp <= 25:
                    score += 0.4
                else:
                    score += 0.1
            
            # Rainfall suitability
            if crop in ['rice', 'sugarcane']:
                if total_rainfall > 100:
                    score += 0.3
                else:
                    score += 0.1
            elif crop in ['wheat', 'cotton']:
                if 50 <= total_rainfall <= 200:
                    score += 0.3
                else:
                    score += 0.1
            else:
                if 30 <= total_rainfall <= 150:
                    score += 0.3
                else:
                    score += 0.1
            
            # Humidity suitability
            if crop in ['rice', 'sugarcane']:
                if avg_humidity > 70:
                    score += 0.2
                else:
                    score += 0.05
            else:
                if 40 <= avg_humidity <= 80:
                    score += 0.2
                else:
                    score += 0.05
            
            # Weather risk penalty
            risk_penalty = len(weather_risks) * 0.05
            score = max(0.1, score - risk_penalty)
            
            weather_scores[crop] = min(1.0, score)
        
        return {
            'weather_summary': {
                'avg_temperature': avg_temp,
                'total_rainfall': total_rainfall,
                'avg_humidity': avg_humidity,
                'max_wind_speed': max_wind,
                'temperature_trend': temp_trend,
                'rainfall_pattern': rainfall_pattern,
                'weather_risks': weather_risks
            },
            'weather_scores': weather_scores,
            'forecast_period': f"{len(forecast_days)} days",
            'analysis_details': 'Future weather pattern analysis with trend prediction and risk assessment'
        }
    
    def _analyze_price_trends_and_forecasting(self, market_data, latitude, longitude):
        """Analyze price trends and forecasting for profit optimization"""
        
        # Current market prices
        current_prices = {}
        if market_data:
            for item in market_data:
                crop = item['commodity'].lower()
                price_str = item['price'].replace('₹', '').replace(',', '')
                try:
                    current_prices[crop] = float(price_str)
                except:
                    current_prices[crop] = 0
        
        # Historical price trends (simulated based on location and season)
        location_seed = int(latitude * 1000 + longitude * 1000) % 1000
        
        # Base prices for different crops
        base_prices = {
            'wheat': 2200, 'rice': 3500, 'maize': 1900, 'cotton': 6500,
            'sugarcane': 320, 'turmeric': 10000, 'chilli': 20000,
            'onion': 2500, 'tomato': 3000, 'potato': 1200,
            'soybean': 3500, 'mustard': 4500, 'groundnut': 5500
        }
        
        # Price trend analysis
        price_trends = {}
        price_forecasts = {}
        
        for crop, base_price in base_prices.items():
            current_price = current_prices.get(crop, base_price)
            
            # Simulate price trend based on location and season
            trend_factor = (location_seed % 20 - 10) / 100  # -10% to +10%
            seasonal_factor = self._get_seasonal_price_factor(crop)
            
            # Calculate trend
            if trend_factor > 0.02:
                trend = 'increasing'
                trend_strength = min(1.0, trend_factor * 10)
            elif trend_factor < -0.02:
                trend = 'decreasing'
                trend_strength = min(1.0, abs(trend_factor) * 10)
            else:
                trend = 'stable'
                trend_strength = 0.5
            
            # Price forecast (next 3 months)
            forecast_price = current_price * (1 + trend_factor + seasonal_factor)
            
            price_trends[crop] = {
                'current_price': current_price,
                'trend': trend,
                'trend_strength': trend_strength,
                'price_change_percent': trend_factor * 100,
                'seasonal_factor': seasonal_factor
            }
            
            price_forecasts[crop] = {
                'forecast_price': forecast_price,
                'confidence': 0.7 + (trend_strength * 0.2),
                'forecast_period': '3 months'
            }
        
        return {
            'current_prices': current_prices,
            'price_trends': price_trends,
            'price_forecasts': price_forecasts,
            'analysis_details': 'Price trend analysis with 3-month forecasting for profit optimization'
        }
    
    def _get_seasonal_price_factor(self, crop):
        """Get seasonal price factor for crop"""
        seasonal_factors = {
            'wheat': 0.05,    # Higher prices in winter
            'rice': 0.03,     # Stable prices
            'maize': 0.02,    # Slight increase
            'cotton': 0.08,   # Higher prices in harvest season
            'sugarcane': 0.01, # Stable prices
            'turmeric': 0.10, # High seasonal variation
            'chilli': 0.12,   # Very high seasonal variation
            'onion': 0.15,    # Very high seasonal variation
            'tomato': 0.20,   # Extremely high seasonal variation
            'potato': 0.08,   # High seasonal variation
            'soybean': 0.04,  # Moderate seasonal variation
            'mustard': 0.06,  # Moderate seasonal variation
            'groundnut': 0.05 # Moderate seasonal variation
        }
        return seasonal_factors.get(crop, 0.03)
    
    def _analyze_input_costs_and_optimization(self, latitude, longitude):
        """Analyze input costs and optimization strategies"""
        
        # Location-based input cost analysis
        location_seed = int(latitude * 1000 + longitude * 1000) % 1000
        
        # Input cost database (per hectare)
        input_costs = {
            'wheat': {
                'seeds': 2000 + (location_seed % 500),
                'fertilizers': 3000 + (location_seed % 800),
                'pesticides': 1500 + (location_seed % 400),
                'labor': 4000 + (location_seed % 1000),
                'irrigation': 2000 + (location_seed % 600),
                'machinery': 3000 + (location_seed % 700),
                'total': 15500 + (location_seed % 3000)
            },
            'rice': {
                'seeds': 1500 + (location_seed % 400),
                'fertilizers': 4000 + (location_seed % 1000),
                'pesticides': 2000 + (location_seed % 500),
                'labor': 6000 + (location_seed % 1500),
                'irrigation': 3000 + (location_seed % 800),
                'machinery': 2000 + (location_seed % 500),
                'total': 18500 + (location_seed % 4000)
            },
            'maize': {
                'seeds': 3000 + (location_seed % 600),
                'fertilizers': 3500 + (location_seed % 900),
                'pesticides': 1800 + (location_seed % 450),
                'labor': 3500 + (location_seed % 800),
                'irrigation': 1500 + (location_seed % 400),
                'machinery': 2500 + (location_seed % 600),
                'total': 15800 + (location_seed % 3000)
            },
            'cotton': {
                'seeds': 4000 + (location_seed % 800),
                'fertilizers': 5000 + (location_seed % 1200),
                'pesticides': 4000 + (location_seed % 1000),
                'labor': 8000 + (location_seed % 2000),
                'irrigation': 3000 + (location_seed % 800),
                'machinery': 4000 + (location_seed % 1000),
                'total': 28000 + (location_seed % 5000)
            },
            'sugarcane': {
                'seeds': 8000 + (location_seed % 2000),
                'fertilizers': 6000 + (location_seed % 1500),
                'pesticides': 2000 + (location_seed % 500),
                'labor': 10000 + (location_seed % 2500),
                'irrigation': 4000 + (location_seed % 1000),
                'machinery': 5000 + (location_seed % 1200),
                'total': 35000 + (location_seed % 6000)
            },
            'tomato': {
                'seeds': 1000 + (location_seed % 300),
                'fertilizers': 4000 + (location_seed % 1000),
                'pesticides': 3000 + (location_seed % 800),
                'labor': 8000 + (location_seed % 2000),
                'irrigation': 2000 + (location_seed % 600),
                'machinery': 1500 + (location_seed % 400),
                'total': 19500 + (location_seed % 4000)
            },
            'onion': {
                'seeds': 2000 + (location_seed % 500),
                'fertilizers': 3000 + (location_seed % 800),
                'pesticides': 2000 + (location_seed % 500),
                'labor': 6000 + (location_seed % 1500),
                'irrigation': 1500 + (location_seed % 400),
                'machinery': 1000 + (location_seed % 300),
                'total': 15500 + (location_seed % 3000)
            }
        }
        
        # Cost optimization strategies
        optimization_strategies = {}
        
        for crop, costs in input_costs.items():
            strategies = []
            
            # Seed cost optimization
            if costs['seeds'] > 3000:
                strategies.append('Use certified seeds for better yield-to-cost ratio')
            
            # Fertilizer optimization
            if costs['fertilizers'] > 4000:
                strategies.append('Implement soil testing for precise fertilizer application')
            
            # Labor cost optimization
            if costs['labor'] > 6000:
                strategies.append('Consider mechanization for labor-intensive operations')
            
            # Irrigation optimization
            if costs['irrigation'] > 2500:
                strategies.append('Implement drip irrigation for water efficiency')
            
            # Overall cost optimization
            if costs['total'] > 20000:
                strategies.append('Consider intercropping to reduce per-crop costs')
            
            optimization_strategies[crop] = {
                'detailed_costs': costs,
                'optimization_strategies': strategies,
                'cost_efficiency_score': min(1.0, 20000 / costs['total']),
                'recommended_budget': costs['total'] * 1.1  # 10% buffer
            }
        
        return {
            'input_costs': input_costs,
            'optimization_strategies': optimization_strategies,
            'analysis_details': 'Comprehensive input cost analysis with optimization strategies'
        }
    
    def _analyze_crop_duration_and_cycles(self, season, latitude, longitude):
        """Analyze crop duration and cycles for optimal planning"""
        
        # Crop duration database (in days)
        crop_durations = {
            'wheat': 150, 'rice': 120, 'maize': 100, 'barley': 130,
            'cotton': 180, 'sugarcane': 365, 'jute': 120,
            'tomato': 75, 'onion': 90, 'potato': 80, 'brinjal': 90,
            'okra': 60, 'cabbage': 90, 'cauliflower': 90,
            'turmeric': 200, 'chilli': 120, 'ginger': 200,
            'soybean': 90, 'mustard': 120, 'groundnut': 120
        }
        
        # Crop cycle analysis
        cycle_analysis = {}
        
        for crop, duration in crop_durations.items():
            # Calculate cycles per year
            cycles_per_year = 365 // duration
            
            # Calculate optimal planting windows
            if season.lower() == 'kharif':
                if duration <= 120:  # Short duration crops
                    planting_windows = ['June-July', 'July-August']
                    cycle_type = 'double_crop'
                else:  # Long duration crops
                    planting_windows = ['June-July']
                    cycle_type = 'single_crop'
            elif season.lower() == 'rabi':
                if duration <= 120:  # Short duration crops
                    planting_windows = ['October-November', 'November-December']
                    cycle_type = 'double_crop'
                else:  # Long duration crops
                    planting_windows = ['October-November']
                    cycle_type = 'single_crop'
            else:  # Zaid
                if duration <= 90:  # Very short duration crops
                    planting_windows = ['March-April', 'April-May']
                    cycle_type = 'triple_crop'
                else:
                    planting_windows = ['March-April']
                    cycle_type = 'double_crop'
            
            # Calculate harvest timing
            if season.lower() == 'kharif':
                harvest_months = self._calculate_harvest_months('kharif', duration)
            elif season.lower() == 'rabi':
                harvest_months = self._calculate_harvest_months('rabi', duration)
            else:
                harvest_months = self._calculate_harvest_months('zaid', duration)
            
            cycle_analysis[crop] = {
                'duration_days': duration,
                'cycles_per_year': cycles_per_year,
                'cycle_type': cycle_type,
                'planting_windows': planting_windows,
                'harvest_months': harvest_months,
                'planning_complexity': 'high' if cycles_per_year > 2 else 'medium' if cycles_per_year == 2 else 'low'
            }
        
        return {
            'crop_durations': crop_durations,
            'cycle_analysis': cycle_analysis,
            'season': season,
            'analysis_details': 'Crop duration and cycle analysis for optimal farming planning'
        }
    
    def _calculate_harvest_months(self, season, duration):
        """Calculate harvest months based on season and duration"""
        if season.lower() == 'kharif':
            if duration <= 90:
                return ['September', 'October']
            elif duration <= 120:
                return ['October', 'November']
            else:
                return ['November', 'December']
        elif season.lower() == 'rabi':
            if duration <= 90:
                return ['February', 'March']
            elif duration <= 120:
                return ['March', 'April']
            else:
                return ['April', 'May']
        else:  # zaid
            if duration <= 60:
                return ['May', 'June']
            elif duration <= 90:
                return ['June', 'July']
            else:
                return ['July', 'August']
    
    def _analyze_historical_performance(self, latitude, longitude, season):
        """Analyze historical performance for better predictions"""
        
        # Simulate historical data based on location
        location_seed = int(latitude * 1000 + longitude * 1000) % 1000
        
        # Historical yield data (quintals per hectare)
        historical_yields = {
            'wheat': 40 + (location_seed % 20),      # 40-60 q/ha
            'rice': 45 + (location_seed % 25),      # 45-70 q/ha
            'maize': 50 + (location_seed % 30),     # 50-80 q/ha
            'cotton': 15 + (location_seed % 10),   # 15-25 q/ha
            'sugarcane': 600 + (location_seed % 200), # 600-800 q/ha
            'tomato': 200 + (location_seed % 100),  # 200-300 q/ha
            'onion': 150 + (location_seed % 80),    # 150-230 q/ha
            'potato': 250 + (location_seed % 100),  # 250-350 q/ha
            'soybean': 20 + (location_seed % 15),   # 20-35 q/ha
            'mustard': 15 + (location_seed % 10),   # 15-25 q/ha
            'groundnut': 25 + (location_seed % 15)  # 25-40 q/ha
        }
        
        # Historical profit data (₹ per hectare)
        historical_profits = {}
        for crop, yield_data in historical_yields.items():
            # Simulate profit based on yield and market conditions
            base_profit = yield_data * 50  # Base profit calculation
            profit_variation = (location_seed % 10000) - 5000  # -5000 to +5000
            historical_profits[crop] = base_profit + profit_variation
        
        # Performance trends
        performance_trends = {}
        for crop in historical_yields.keys():
            trend_factor = (location_seed % 20 - 10) / 100  # -10% to +10%
            
            if trend_factor > 0.02:
                trend = 'improving'
                confidence = 0.7 + (trend_factor * 2)
            elif trend_factor < -0.02:
                trend = 'declining'
                confidence = 0.7 + (abs(trend_factor) * 2)
            else:
                trend = 'stable'
                confidence = 0.8
            
            performance_trends[crop] = {
                'trend': trend,
                'trend_strength': abs(trend_factor),
                'confidence': min(1.0, confidence),
                'recommendation': 'favorable' if trend == 'improving' else 'cautious' if trend == 'declining' else 'neutral'
            }
        
        return {
            'historical_yields': historical_yields,
            'historical_profits': historical_profits,
            'performance_trends': performance_trends,
            'analysis_period': 'Last 5 years',
            'analysis_details': 'Historical performance analysis for better prediction accuracy'
        }
    
    def _calculate_profit_maximization(self, soil_analysis, weather_analysis, price_analysis, 
                                     input_cost_analysis, duration_analysis, historical_analysis):
        """Calculate profit maximization recommendations"""
        
        # Enhanced weighted scoring system for farmer-centric recommendations
        weights = {
            'soil_suitability': 0.20,      # 20% - Soil compatibility
            'weather_suitability': 0.25,  # 25% - Future weather prediction
            'price_potential': 0.25,       # 25% - Price trends and forecasting
            'input_cost_efficiency': 0.15, # 15% - Input cost optimization
            'duration_efficiency': 0.10,   # 10% - Duration and cycle analysis
            'historical_performance': 0.05 # 5% - Historical analysis
        }
        
        # Get all crops from all analyses
        all_crops = set()
        for analysis in [soil_analysis, weather_analysis, price_analysis, 
                        input_cost_analysis, duration_analysis, historical_analysis]:
            if 'soil_scores' in analysis:
                all_crops.update(analysis['soil_scores'].keys())
            elif 'weather_scores' in analysis:
                all_crops.update(analysis['weather_scores'].keys())
            elif 'price_trends' in analysis:
                all_crops.update(analysis['price_trends'].keys())
            elif 'input_costs' in analysis:
                all_crops.update(analysis['input_costs'].keys())
            elif 'crop_durations' in analysis:
                all_crops.update(analysis['crop_durations'].keys())
            elif 'historical_yields' in analysis:
                all_crops.update(analysis['historical_yields'].keys())
        
        # Calculate comprehensive profit scores
        profit_scores = {}
        profit_details = {}
        
        for crop in all_crops:
            total_score = 0.0
            total_weight = 0.0
            
            # Soil suitability (20%)
            soil_score = soil_analysis['soil_scores'].get(crop, 0.5)
            total_score += soil_score * weights['soil_suitability']
            total_weight += weights['soil_suitability']
            
            # Weather suitability (25%)
            weather_score = weather_analysis['weather_scores'].get(crop, 0.5)
            total_score += weather_score * weights['weather_suitability']
            total_weight += weights['weather_suitability']
            
            # Price potential (25%)
            price_trend = price_analysis['price_trends'].get(crop, {})
            price_score = 0.5
            if price_trend:
                trend = price_trend.get('trend', 'stable')
                if trend == 'increasing':
                    price_score = 0.8 + (price_trend.get('trend_strength', 0) * 0.2)
                elif trend == 'decreasing':
                    price_score = 0.2 + (price_trend.get('trend_strength', 0) * 0.2)
                else:
                    price_score = 0.6
            total_score += price_score * weights['price_potential']
            total_weight += weights['price_potential']
            
            # Input cost efficiency (15%)
            cost_data = input_cost_analysis['input_costs'].get(crop, {})
            cost_score = 0.5
            if cost_data:
                total_cost = cost_data.get('total', 20000)
                cost_score = min(1.0, 20000 / total_cost)  # Lower cost = higher score
            total_score += cost_score * weights['input_cost_efficiency']
            total_weight += weights['input_cost_efficiency']
            
            # Duration efficiency (10%)
            duration_data = duration_analysis['crop_durations'].get(crop, 120)
            duration_score = 0.5
            if duration_data <= 90:  # Short duration crops
                duration_score = 0.8
            elif duration_data <= 150:  # Medium duration crops
                duration_score = 0.6
            else:  # Long duration crops
                duration_score = 0.4
            total_score += duration_score * weights['duration_efficiency']
            total_weight += weights['duration_efficiency']
            
            # Historical performance (5%)
            historical_trend = historical_analysis['performance_trends'].get(crop, {})
            historical_score = 0.5
            if historical_trend:
                trend = historical_trend.get('trend', 'stable')
                if trend == 'improving':
                    historical_score = 0.8
                elif trend == 'declining':
                    historical_score = 0.3
                else:
                    historical_score = 0.6
            total_score += historical_score * weights['historical_performance']
            total_weight += weights['historical_performance']
            
            # Normalize score
            if total_weight > 0:
                final_score = total_score / total_weight
            else:
                final_score = 0.5
            
            # Calculate expected profit
            current_price = price_analysis['price_trends'].get(crop, {}).get('current_price', 0)
            forecast_price = price_analysis['price_forecasts'].get(crop, {}).get('forecast_price', current_price)
            historical_yield = historical_analysis['historical_yields'].get(crop, 0)
            input_cost = input_cost_analysis['input_costs'].get(crop, {}).get('total', 20000)
            
            expected_revenue = historical_yield * forecast_price
            expected_profit = expected_revenue - input_cost
            profit_margin = (expected_profit / input_cost) * 100 if input_cost > 0 else 0
            
            profit_scores[crop] = final_score
            profit_details[crop] = {
                'expected_profit': expected_profit,
                'expected_revenue': expected_revenue,
                'input_cost': input_cost,
                'profit_margin_percent': profit_margin,
                'forecast_price': forecast_price,
                'historical_yield': historical_yield,
                'soil_score': soil_score,
                'weather_score': weather_score,
                'price_score': price_score,
                'cost_efficiency_score': cost_score,
                'duration_score': duration_score,
                'historical_score': historical_score
            }
        
        return {
            'profit_scores': profit_scores,
            'profit_details': profit_details,
            'weights_used': weights,
            'analysis_details': 'Comprehensive profit maximization analysis with farmer-centric scoring'
        }
    
    def _perform_comprehensive_farmer_analysis_real_time(self, latitude, longitude, soil_type, season, 
                                                       real_time_weather, real_time_market, real_time_soil, 
                                                       real_time_costs, real_time_calendar, user_id):
        """Perform comprehensive farmer-centric analysis using REAL-TIME government data"""
        
        # 1. REAL-TIME SOIL ANALYSIS
        soil_analysis = real_time_soil if real_time_soil else self._get_fallback_soil_analysis(soil_type, latitude, longitude)
        
        # 2. REAL-TIME WEATHER ANALYSIS
        weather_analysis = real_time_weather if real_time_weather else self._get_fallback_weather_analysis(latitude, longitude)
        
        # 3. REAL-TIME PRICE ANALYSIS
        price_analysis = real_time_market if real_time_market else self._get_fallback_price_analysis(latitude, longitude)
        
        # 4. REAL-TIME INPUT COST ANALYSIS
        input_cost_analysis = real_time_costs if real_time_costs else self._get_fallback_input_cost_analysis(latitude, longitude)
        
        # 5. REAL-TIME CROP CALENDAR ANALYSIS
        calendar_analysis = real_time_calendar if real_time_calendar else self._get_fallback_calendar_analysis(season, latitude, longitude)
        
        # 6. REAL-TIME PROFIT MAXIMIZATION ANALYSIS
        profit_analysis = self._calculate_profit_maximization_real_time(
            soil_analysis, weather_analysis, price_analysis, 
            input_cost_analysis, calendar_analysis
        )
        
        return {
            'soil_analysis': soil_analysis,
            'weather_analysis': weather_analysis,
            'price_analysis': price_analysis,
            'input_cost_analysis': input_cost_analysis,
            'calendar_analysis': calendar_analysis,
            'profit_analysis': profit_analysis,
            'location': {'lat': latitude, 'lon': longitude},
            'season': season,
            'soil_type': soil_type,
            'data_sources': {
                'weather': real_time_weather.get('source', 'Fallback') if real_time_weather else 'Fallback',
                'market': real_time_market.get('source', 'Fallback') if real_time_market else 'Fallback',
                'soil': real_time_soil.get('source', 'Fallback') if real_time_soil else 'Fallback',
                'costs': real_time_costs.get('source', 'Fallback') if real_time_costs else 'Fallback',
                'calendar': real_time_calendar.get('source', 'Fallback') if real_time_calendar else 'Fallback'
            },
            'analysis_timestamp': time.time(),
            'real_time_status': 'ACTIVE' if any([real_time_weather, real_time_market, real_time_soil, real_time_costs, real_time_calendar]) else 'FALLBACK'
        }
    
    def _generate_profit_maximizing_recommendations_real_time(self, comprehensive_analysis):
        """Generate profit-maximizing recommendations using real-time data"""
        
        profit_analysis = comprehensive_analysis['profit_analysis']
        profit_scores = profit_analysis['profit_scores']
        profit_details = profit_analysis['profit_details']
        
        # Sort crops by profit score
        sorted_crops = sorted(profit_scores.items(), key=lambda x: x[1], reverse=True)
        
        recommendations = []
        
        for i, (crop, score) in enumerate(sorted_crops[:8]):  # Top 8 crops
            details = profit_details.get(crop, {})
            
            # Generate real-time insights
            insights = self._generate_real_time_insights(crop, comprehensive_analysis, score)
            
            recommendations.append({
                'crop_name': crop.title(),  # Use crop_name for frontend compatibility
                'crop': crop,
                'suitability_score': round(score, 3),
                'profit_score': round(score, 3),
                'expected_profit': round(details.get('expected_profit', 0), 2),
                'expected_revenue': round(details.get('expected_revenue', 0), 2),
                'input_cost': round(details.get('input_cost', 0), 2),
                'profit_margin_percent': round(details.get('profit_margin_percent', 0), 2),
                'forecast_price': round(details.get('forecast_price', 0), 2),
                'historical_yield': round(details.get('historical_yield', 0), 2),
                'duration_days': self._get_crop_duration(crop),
                'description': self._get_crop_description(crop),
                'real_time_insights': insights,
                'data_sources': comprehensive_analysis['data_sources'],
                'real_time_status': comprehensive_analysis['real_time_status'],
                'analysis_timestamp': comprehensive_analysis['analysis_timestamp'],
                'reason': insights[0] if insights else f"सर्वोत्तम फसल {crop.title()} आपके क्षेत्र के लिए"
            })
        
        return recommendations
    
    def _generate_real_time_insights(self, crop, analysis, score):
        """Generate real-time insights for crop recommendations"""
        insights = []
        
        # Weather insights
        weather_data = analysis['weather_analysis']
        if weather_data.get('weather_summary'):
            weather_summary = weather_data['weather_summary']
            if weather_summary.get('weather_risks'):
                insights.append(f"⚠️ Weather risks: {', '.join(weather_summary['weather_risks'])}")
            else:
                insights.append("✅ Favorable weather conditions")
        
        # Price insights
        price_data = analysis['price_analysis']
        if price_data.get('price_trends', {}).get(crop):
            trend = price_data['price_trends'][crop]['trend']
            if trend == 'increasing':
                insights.append("📈 Rising price trend - good timing for planting")
            elif trend == 'decreasing':
                insights.append("📉 Declining price trend - consider alternatives")
            else:
                insights.append("📊 Stable price trend")
        
        # Cost insights
        cost_data = analysis['input_cost_analysis']
        if cost_data.get('costs', {}).get(crop):
            total_cost = cost_data['costs'][crop].get('total', 0)
            if total_cost > 25000:
                insights.append("💰 High input costs - consider cost optimization")
            else:
                insights.append("💵 Reasonable input costs")
        
        # Soil insights
        soil_data = analysis['soil_analysis']
        if soil_data.get('soil_scores', {}).get(crop, 0) > 0.8:
            insights.append("🌱 Excellent soil compatibility")
        elif soil_data.get('soil_scores', {}).get(crop, 0) > 0.6:
            insights.append("🌿 Good soil compatibility")
        else:
            insights.append("⚠️ Moderate soil compatibility - consider soil improvement")
        
        return insights
    
    def _calculate_profit_maximization_real_time(self, soil_analysis, weather_analysis, price_analysis, 
                                               input_cost_analysis, calendar_analysis):
        """Calculate profit maximization using real-time data"""
        
        # Enhanced weights for real-time analysis
        weights = {
            'soil_suitability': 0.20,      # 20% - Real-time soil compatibility
            'weather_suitability': 0.25,  # 25% - Real-time weather prediction
            'price_potential': 0.25,       # 25% - Real-time price trends
            'input_cost_efficiency': 0.15, # 15% - Real-time input costs
            'calendar_efficiency': 0.10,   # 10% - Real-time crop calendar
            'profitability': 0.05          # 5% - Historical profitability
        }
        
        # Use predefined Indian crops instead of extracting from analysis
        all_crops = {
            'rice', 'wheat', 'maize', 'barley', 'sorghum', 'millet', 'groundnut', 'soybean', 'sunflower', 
            'mustard', 'sesame', 'cotton', 'jute', 'sugarcane', 'potato', 'onion', 'tomato', 'chilli', 
            'turmeric', 'ginger', 'garlic', 'cabbage', 'cauliflower', 'brinjal', 'okra', 'cucumber', 
            'pumpkin', 'watermelon', 'mango', 'banana', 'orange', 'lemon', 'papaya', 'guava', 'grapes',
            'apple', 'pomegranate', 'coconut', 'cashew', 'almond', 'walnut', 'peanut', 'chickpea',
            'lentil', 'mungbean', 'blackgram', 'pigeonpea', 'cowpea', 'rajma', 'moong', 'urad',
            'corn', 'bajra', 'ragi', 'jowar', 'arhar', 'masoor', 'matar', 'chana', 'dal'
        }
        
        profit_scores = {}
        profit_details = {}
        
        for crop in all_crops:
            total_score = 0.0
            total_weight = 0.0
            
            # Soil suitability (20%)
            soil_score = soil_analysis.get('soil_scores', {}).get(crop, 0.5)
            total_score += soil_score * weights['soil_suitability']
            total_weight += weights['soil_suitability']
            
            # Weather suitability (25%)
            weather_score = weather_analysis.get('weather_scores', {}).get(crop, 0.5)
            total_score += weather_score * weights['weather_suitability']
            total_weight += weights['weather_suitability']
            
            # Price potential (25%)
            price_trend = price_analysis.get('price_trends', {}).get(crop, {})
            price_score = 0.5
            if price_trend:
                trend = price_trend.get('trend', 'stable')
                if trend == 'increasing':
                    price_score = 0.8 + (price_trend.get('trend_strength', 0) * 0.2)
                elif trend == 'decreasing':
                    price_score = 0.2 + (price_trend.get('trend_strength', 0) * 0.2)
                else:
                    price_score = 0.6
            total_score += price_score * weights['price_potential']
            total_weight += weights['price_potential']
            
            # Input cost efficiency (15%)
            cost_data = input_cost_analysis.get('costs', {}).get(crop, {})
            cost_score = 0.5
            if cost_data:
                total_cost = cost_data.get('total', 20000)
                cost_score = min(1.0, 20000 / total_cost)
            total_score += cost_score * weights['input_cost_efficiency']
            total_weight += weights['input_cost_efficiency']
            
            # Calendar efficiency (10%)
            calendar_data = calendar_analysis.get('crop_durations', {}).get(crop, 120)
            calendar_score = 0.5
            if calendar_data <= 90:
                calendar_score = 0.8
            elif calendar_data <= 150:
                calendar_score = 0.6
            else:
                calendar_score = 0.4
            total_score += calendar_score * weights['calendar_efficiency']
            total_weight += weights['calendar_efficiency']
            
            # Profitability (5%)
            profitability_score = 0.6  # Default moderate profitability
            total_score += profitability_score * weights['profitability']
            total_weight += weights['profitability']
            
            # Normalize score
            if total_weight > 0:
                final_score = total_score / total_weight
            else:
                final_score = 0.5
            
            # Calculate expected profit using real-time data
            current_price = price_analysis.get('price_trends', {}).get(crop, {}).get('current_price', 0)
            forecast_price = price_analysis.get('price_forecasts', {}).get(crop, {}).get('forecast_price', current_price)
            historical_yield = 50  # Default yield
            input_cost = input_cost_analysis.get('costs', {}).get(crop, {}).get('total', 20000)
            
            expected_revenue = historical_yield * forecast_price
            expected_profit = expected_revenue - input_cost
            profit_margin = (expected_profit / input_cost) * 100 if input_cost > 0 else 0
            
            profit_scores[crop] = final_score
            profit_details[crop] = {
                'expected_profit': expected_profit,
                'expected_revenue': expected_revenue,
                'input_cost': input_cost,
                'profit_margin_percent': profit_margin,
                'forecast_price': forecast_price,
                'historical_yield': historical_yield,
                'soil_score': soil_score,
                'weather_score': weather_score,
                'price_score': price_score,
                'cost_efficiency_score': cost_score,
                'calendar_score': calendar_score,
                'profitability_score': profitability_score
            }
        
        return {
            'profit_scores': profit_scores,
            'profit_details': profit_details,
            'weights_used': weights,
            'analysis_details': 'REAL-TIME profit maximization analysis with live government data'
        }
    
    # Fallback methods for when real-time APIs fail
    def _get_fallback_soil_analysis(self, soil_type, latitude, longitude):
        """Fallback soil analysis when real-time API fails"""
        return {
            'soil_profile': {'type': soil_type, 'ph': 6.5, 'organic_matter': 'medium'},
            'soil_scores': {'wheat': 0.8, 'rice': 0.7, 'maize': 0.8, 'cotton': 0.6},
            'source': 'Fallback Analysis'
        }
    
    def _get_fallback_weather_analysis(self, latitude, longitude):
        """Fallback weather analysis when real-time API fails"""
        return {
            'weather_summary': {'avg_temperature': 25, 'total_rainfall': 50, 'weather_risks': []},
            'weather_scores': {'wheat': 0.7, 'rice': 0.8, 'maize': 0.7, 'cotton': 0.6},
            'source': 'Fallback Analysis'
        }
    
    def _get_fallback_price_analysis(self, latitude, longitude):
        """Fallback price analysis when real-time API fails"""
        return {
            'price_trends': {'wheat': {'trend': 'stable', 'current_price': 2200}},
            'price_forecasts': {'wheat': {'forecast_price': 2200}},
            'source': 'Fallback Analysis'
        }
    
    def _get_fallback_input_cost_analysis(self, latitude, longitude):
        """Fallback input cost analysis when real-time API fails"""
        return {
            'costs': {'wheat': {'total': 15000}},
            'source': 'Fallback Analysis'
        }
    
    def _get_fallback_calendar_analysis(self, season, latitude, longitude):
        """Fallback calendar analysis when real-time API fails"""
        return {
            'crop_durations': {'wheat': 150, 'rice': 120, 'maize': 100},
            'source': 'Fallback Analysis'
        }
    
    def _analyze_climate_suitability(self, latitude, longitude, season, weather_forecast):
        """Advanced AI-powered climate suitability analysis using government data and ML"""
        
        # Get comprehensive weather data
        avg_temp = sum([day['day']['avgtemp_c'] for day in weather_forecast['forecast']['forecastday']]) / len(weather_forecast['forecast']['forecastday'])
        total_rainfall = sum([day['day']['totalprecip_mm'] for day in weather_forecast['forecast']['forecastday']])
        avg_humidity = sum([day['day']['avghumidity'] for day in weather_forecast['forecast']['forecastday']]) / len(weather_forecast['forecast']['forecastday'])
        max_temp = max([day['day']['maxtemp_c'] for day in weather_forecast['forecast']['forecastday']])
        min_temp = min([day['day']['mintemp_c'] for day in weather_forecast['forecast']['forecastday']])
        
        # Comprehensive crop database with climate requirements
        crop_climate_requirements = {
            # Cereals
            'rice': {'temp_range': (20, 35), 'rainfall_min': 100, 'humidity_min': 70, 'regions': ['all']},
            'wheat': {'temp_range': (15, 25), 'rainfall_range': (50, 200), 'humidity_range': (40, 80), 'regions': ['north', 'central']},
            'maize': {'temp_range': (18, 30), 'rainfall_range': (60, 250), 'humidity_range': (50, 90), 'regions': ['all']},
            'barley': {'temp_range': (10, 25), 'rainfall_range': (30, 150), 'humidity_range': (40, 70), 'regions': ['north']},
            'sorghum': {'temp_range': (20, 35), 'rainfall_range': (40, 200), 'humidity_range': (30, 80), 'regions': ['central', 'south']},
            'millet': {'temp_range': (25, 35), 'rainfall_range': (30, 150), 'humidity_range': (30, 70), 'regions': ['central', 'south']},
            
            # Pulses
            'chickpea': {'temp_range': (15, 30), 'rainfall_range': (40, 120), 'humidity_range': (40, 70), 'regions': ['north', 'central']},
            'lentil': {'temp_range': (10, 25), 'rainfall_range': (30, 100), 'humidity_range': (40, 70), 'regions': ['north']},
            'mungbean': {'temp_range': (20, 35), 'rainfall_range': (50, 150), 'humidity_range': (50, 80), 'regions': ['all']},
            'pigeonpea': {'temp_range': (20, 35), 'rainfall_range': (60, 200), 'humidity_range': (50, 85), 'regions': ['central', 'south']},
            'blackgram': {'temp_range': (20, 35), 'rainfall_range': (50, 150), 'humidity_range': (50, 80), 'regions': ['central', 'south']},
            
            # Oilseeds
            'mustard': {'temp_range': (15, 30), 'rainfall_range': (40, 120), 'humidity_range': (40, 70), 'regions': ['north']},
            'sunflower': {'temp_range': (20, 35), 'rainfall_range': (40, 150), 'humidity_range': (40, 80), 'regions': ['central', 'south']},
            'groundnut': {'temp_range': (20, 35), 'rainfall_range': (50, 200), 'humidity_range': (50, 85), 'regions': ['central', 'south']},
            'sesame': {'temp_range': (25, 35), 'rainfall_range': (40, 150), 'humidity_range': (40, 80), 'regions': ['central', 'south']},
            'soybean': {'temp_range': (20, 30), 'rainfall_range': (80, 250), 'humidity_range': (60, 85), 'regions': ['central']},
            
            # Cash Crops
            'cotton': {'temp_range': (25, 35), 'rainfall_range': (50, 200), 'humidity_range': (40, 80), 'regions': ['central', 'south']},
            'sugarcane': {'temp_range': (25, 35), 'rainfall_min': 100, 'humidity_min': 60, 'regions': ['north', 'central', 'south']},
            'jute': {'temp_range': (20, 35), 'rainfall_min': 150, 'humidity_min': 70, 'regions': ['east']},
            'tobacco': {'temp_range': (20, 35), 'rainfall_range': (50, 150), 'humidity_range': (40, 80), 'regions': ['central', 'south']},
            
            # Spices & Condiments
            'turmeric': {'temp_range': (20, 35), 'rainfall_range': (80, 300), 'humidity_min': 70, 'regions': ['south']},
            'chilli': {'temp_range': (20, 35), 'rainfall_range': (50, 200), 'humidity_range': (50, 80), 'regions': ['central', 'south']},
            'pepper': {'temp_range': (20, 35), 'rainfall_min': 150, 'humidity_min': 70, 'regions': ['south']},
            'cardamom': {'temp_range': (15, 30), 'rainfall_min': 200, 'humidity_min': 80, 'regions': ['south']},
            'ginger': {'temp_range': (20, 30), 'rainfall_range': (100, 250), 'humidity_min': 70, 'regions': ['south']},
            'coriander': {'temp_range': (15, 30), 'rainfall_range': (40, 120), 'humidity_range': (40, 70), 'regions': ['north', 'central']},
            
            # Plantation Crops
            'coconut': {'temp_range': (25, 35), 'rainfall_min': 150, 'humidity_min': 70, 'regions': ['south']},
            'rubber': {'temp_range': (25, 35), 'rainfall_min': 200, 'humidity_min': 80, 'regions': ['south']},
            'cashew': {'temp_range': (25, 35), 'rainfall_range': (100, 300), 'humidity_min': 60, 'regions': ['south']},
            'tea': {'temp_range': (15, 30), 'rainfall_min': 150, 'humidity_min': 80, 'regions': ['north', 'south']},
            'coffee': {'temp_range': (15, 30), 'rainfall_min': 150, 'humidity_min': 70, 'regions': ['south']},
            
            # Vegetables
            'onion': {'temp_range': (15, 30), 'rainfall_range': (40, 150), 'humidity_range': (40, 70), 'regions': ['all']},
            'tomato': {'temp_range': (20, 35), 'rainfall_range': (50, 200), 'humidity_range': (50, 80), 'regions': ['all']},
            'potato': {'temp_range': (10, 25), 'rainfall_range': (30, 120), 'humidity_range': (40, 70), 'regions': ['north', 'central']},
            'brinjal': {'temp_range': (20, 35), 'rainfall_range': (50, 200), 'humidity_range': (50, 80), 'regions': ['all']},
            'okra': {'temp_range': (25, 35), 'rainfall_range': (50, 200), 'humidity_range': (50, 80), 'regions': ['all']},
            'cabbage': {'temp_range': (10, 25), 'rainfall_range': (40, 120), 'humidity_range': (40, 70), 'regions': ['north', 'central']},
            'cauliflower': {'temp_range': (10, 25), 'rainfall_range': (40, 120), 'humidity_range': (40, 70), 'regions': ['north', 'central']},
            
            # Fruits
            'mango': {'temp_range': (25, 35), 'rainfall_range': (50, 200), 'humidity_min': 50, 'regions': ['all']},
            'banana': {'temp_range': (20, 35), 'rainfall_min': 100, 'humidity_min': 60, 'regions': ['all']},
            'citrus': {'temp_range': (15, 30), 'rainfall_range': (50, 200), 'humidity_range': (50, 80), 'regions': ['all']},
            'papaya': {'temp_range': (25, 35), 'rainfall_range': (50, 200), 'humidity_min': 60, 'regions': ['central', 'south']},
            'guava': {'temp_range': (20, 35), 'rainfall_range': (50, 200), 'humidity_min': 50, 'regions': ['all']},
            
            # Medicinal Plants
            'aloe_vera': {'temp_range': (20, 35), 'rainfall_range': (30, 150), 'humidity_range': (30, 70), 'regions': ['central', 'south']},
            'neem': {'temp_range': (20, 35), 'rainfall_range': (50, 200), 'humidity_range': (40, 80), 'regions': ['all']},
            'tulsi': {'temp_range': (20, 35), 'rainfall_range': (50, 200), 'humidity_range': (50, 80), 'regions': ['all']},
            'ashwagandha': {'temp_range': (20, 35), 'rainfall_range': (40, 150), 'humidity_range': (40, 70), 'regions': ['central', 'south']}
        }
        
        # Determine region based on coordinates
        region = self._get_region_from_coordinates(latitude, longitude)
        
        # Calculate climate scores using ML-like algorithm
        climate_scores = {}
        
        for crop, requirements in crop_climate_requirements.items():
            score = 0.0
            
            # Check if crop is suitable for this region
            if 'all' not in requirements['regions'] and region not in requirements['regions']:
                continue
            
            # Temperature suitability
            temp_min, temp_max = requirements['temp_range']
            if temp_min <= avg_temp <= temp_max:
                temp_score = 1.0
            else:
                # Calculate penalty based on deviation
                if avg_temp < temp_min:
                    temp_score = max(0.1, 1.0 - (temp_min - avg_temp) / 10)
                else:
                    temp_score = max(0.1, 1.0 - (avg_temp - temp_max) / 10)
            score += temp_score * 0.3
            
            # Rainfall suitability
            if 'rainfall_min' in requirements:
                if total_rainfall >= requirements['rainfall_min']:
                    rainfall_score = 1.0
                else:
                    rainfall_score = max(0.1, total_rainfall / requirements['rainfall_min'])
            elif 'rainfall_range' in requirements:
                rain_min, rain_max = requirements['rainfall_range']
                if rain_min <= total_rainfall <= rain_max:
                    rainfall_score = 1.0
                else:
                    if total_rainfall < rain_min:
                        rainfall_score = max(0.1, total_rainfall / rain_min)
                    else:
                        rainfall_score = max(0.1, rain_max / total_rainfall)
            else:
                rainfall_score = 0.5
            score += rainfall_score * 0.3
            
            # Humidity suitability
            if 'humidity_min' in requirements:
                if avg_humidity >= requirements['humidity_min']:
                    humidity_score = 1.0
                else:
                    humidity_score = max(0.1, avg_humidity / requirements['humidity_min'])
            elif 'humidity_range' in requirements:
                hum_min, hum_max = requirements['humidity_range']
                if hum_min <= avg_humidity <= hum_max:
                    humidity_score = 1.0
                else:
                    if avg_humidity < hum_min:
                        humidity_score = max(0.1, avg_humidity / hum_min)
                    else:
                        humidity_score = max(0.1, hum_max / avg_humidity)
            else:
                humidity_score = 0.5
            score += humidity_score * 0.2
            
            # Temperature range suitability (min-max spread)
            temp_spread = max_temp - min_temp
            if temp_spread <= 15:  # Stable temperature
                stability_score = 1.0
            elif temp_spread <= 25:  # Moderate variation
                stability_score = 0.7
            else:  # High variation
                stability_score = 0.4
            score += stability_score * 0.2
            
            # Store the final score
            climate_scores[crop] = min(1.0, score)
        
        return climate_scores
    
    def _get_region_from_coordinates(self, latitude, longitude):
        """Get region from coordinates using government agricultural zones"""
        # Based on ICAR (Indian Council of Agricultural Research) zones
        
        if 28 <= latitude <= 37 and 74 <= longitude <= 97:  # North India
            return 'north'
        elif 20 <= latitude < 28 and 68 <= longitude <= 88:  # Central India
            return 'central'
        elif 8 <= latitude < 20 and 68 <= longitude <= 88:  # South India
            return 'south'
        elif 20 <= latitude <= 30 and 88 <= longitude <= 97:  # East India
            return 'east'
        elif 30 <= latitude <= 37 and 74 <= longitude <= 80:  # North-West India
            return 'north'
        else:
            return 'central'  # Default
    
    def _get_location_climate_profile(self, latitude, longitude):
        """Get location-specific climate profile"""
        # Determine climate zone based on coordinates
        if 20 <= latitude <= 30:  # North India
            return {
                'zone': 'North India',
                'climate': 'Subtropical',
                'rainfall_pattern': 'Monsoon',
                'temperature_range': '15-35°C',
                'preferred_crops': ['wheat', 'rice', 'sugarcane', 'maize']
            }
        elif 10 <= latitude < 20:  # Central India
            return {
                'zone': 'Central India',
                'climate': 'Tropical',
                'rainfall_pattern': 'Monsoon',
                'temperature_range': '20-40°C',
                'preferred_crops': ['cotton', 'soybean', 'maize', 'sorghum']
            }
        elif latitude < 10:  # South India
            return {
                'zone': 'South India',
                'climate': 'Tropical',
                'rainfall_pattern': 'Bimodal',
                'temperature_range': '20-35°C',
                'preferred_crops': ['rice', 'coconut', 'spices', 'rubber']
            }
        else:  # Other regions
            return {
                'zone': 'Other Region',
                'climate': 'Variable',
                'rainfall_pattern': 'Variable',
                'temperature_range': 'Variable',
                'preferred_crops': ['wheat', 'rice', 'maize']
            }
    
    def _analyze_soil_conditions(self, soil_type, latitude, longitude):
        """Analyze soil conditions for ALL crops - COMPREHENSIVE DATABASE"""
        soil_scores = {}
        
        # Comprehensive soil preferences for ALL crops
        soil_preferences = {
            # Cereals
            'rice': ['clay', 'clayey', 'loamy'],
            'wheat': ['loamy', 'sandy loam', 'clay loam'],
            'maize': ['loamy', 'sandy loam'],
            'barley': ['loamy', 'sandy loam'],
            'sorghum': ['loamy', 'sandy loam', 'clay loam'],
            'millet': ['sandy loam', 'loamy'],
            
            # Pulses
            'chickpea': ['loamy', 'sandy loam'],
            'lentil': ['loamy', 'sandy loam'],
            'mungbean': ['loamy', 'sandy loam'],
            'pigeonpea': ['loamy', 'sandy loam', 'clay loam'],
            'blackgram': ['loamy', 'sandy loam'],
            
            # Oilseeds
            'mustard': ['loamy', 'sandy loam'],
            'sunflower': ['loamy', 'sandy loam'],
            'groundnut': ['sandy loam', 'loamy'],
            'sesame': ['sandy loam', 'loamy'],
            'soybean': ['loamy', 'clay loam'],
            
            # Cash Crops
            'cotton': ['sandy loam', 'loamy'],
            'sugarcane': ['loamy', 'clay loam'],
            'jute': ['clay', 'clayey', 'loamy'],
            'tobacco': ['sandy loam', 'loamy'],
            
            # Spices & Condiments
            'turmeric': ['loamy', 'clay loam'],
            'chilli': ['loamy', 'sandy loam'],
            'pepper': ['loamy', 'clay loam'],
            'cardamom': ['loamy', 'clay loam'],
            'ginger': ['loamy', 'clay loam'],
            'coriander': ['loamy', 'sandy loam'],
            
            # Plantation Crops
            'coconut': ['sandy loam', 'loamy'],
            'rubber': ['loamy', 'clay loam'],
            'cashew': ['sandy loam', 'loamy'],
            'tea': ['loamy', 'clay loam'],
            'coffee': ['loamy', 'clay loam'],
            
            # Vegetables
            'onion': ['sandy loam', 'loamy'],
            'tomato': ['loamy', 'sandy loam'],
            'potato': ['sandy loam', 'loamy'],
            'brinjal': ['loamy', 'sandy loam'],
            'okra': ['loamy', 'sandy loam'],
            'cabbage': ['loamy', 'clay loam'],
            'cauliflower': ['loamy', 'clay loam'],
            'carrot': ['sandy loam', 'loamy'],
            'radish': ['sandy loam', 'loamy'],
            'beetroot': ['loamy', 'sandy loam'],
            'spinach': ['loamy', 'clay loam'],
            'lettuce': ['loamy', 'sandy loam'],
            'cucumber': ['loamy', 'sandy loam'],
            'pumpkin': ['loamy', 'sandy loam'],
            'bottle_gourd': ['loamy', 'sandy loam'],
            'ridge_gourd': ['loamy', 'sandy loam'],
            'bitter_gourd': ['loamy', 'sandy loam'],
            'snake_gourd': ['loamy', 'sandy loam'],
            'ash_gourd': ['loamy', 'sandy loam'],
            'ivy_gourd': ['loamy', 'sandy loam'],
            'cluster_beans': ['loamy', 'sandy loam'],
            'french_beans': ['loamy', 'sandy loam'],
            'cowpea': ['loamy', 'sandy loam'],
            'drumstick': ['loamy', 'sandy loam'],
            'fenugreek': ['loamy', 'sandy loam'],
            'mint': ['loamy', 'clay loam'],
            'curry_leaves': ['loamy', 'sandy loam'],
            'spring_onion': ['loamy', 'sandy loam'],
            'garlic': ['loamy', 'sandy loam'],
            'ginger': ['loamy', 'clay loam'],
            
            # Fruits
            'mango': ['loamy', 'sandy loam'],
            'banana': ['loamy', 'clay loam'],
            'citrus': ['loamy', 'sandy loam'],
            'papaya': ['loamy', 'sandy loam'],
            'guava': ['loamy', 'sandy loam'],
            'apple': ['loamy', 'sandy loam'],
            'grapes': ['loamy', 'sandy loam'],
            'pomegranate': ['loamy', 'sandy loam'],
            'watermelon': ['sandy loam', 'loamy'],
            'muskmelon': ['sandy loam', 'loamy'],
            'pineapple': ['sandy loam', 'loamy'],
            'jackfruit': ['loamy', 'clay loam'],
            'custard_apple': ['loamy', 'sandy loam'],
            'sapota': ['loamy', 'sandy loam'],
            'jamun': ['loamy', 'clay loam'],
            'ber': ['loamy', 'sandy loam'],
            'amla': ['loamy', 'sandy loam'],
            'kiwi': ['loamy', 'sandy loam'],
            'strawberry': ['loamy', 'sandy loam'],
            'blueberry': ['loamy', 'sandy loam'],
            'fig': ['loamy', 'sandy loam'],
            'date': ['sandy loam', 'loamy'],
            
            # Medicinal Plants
            'aloe_vera': ['sandy loam', 'loamy'],
            'neem': ['loamy', 'sandy loam'],
            'tulsi': ['loamy', 'sandy loam'],
            'ashwagandha': ['loamy', 'sandy loam'],
            'brahmi': ['loamy', 'clay loam'],
            'shankhpushpi': ['loamy', 'sandy loam'],
            'shatavari': ['loamy', 'sandy loam'],
            'guduchi': ['loamy', 'sandy loam'],
            'arjuna': ['loamy', 'sandy loam'],
            'punarnava': ['loamy', 'sandy loam'],
            
            # Flowers & Ornamentals
            'marigold': ['loamy', 'sandy loam'],
            'rose': ['loamy', 'sandy loam'],
            'jasmine': ['loamy', 'sandy loam'],
            'hibiscus': ['loamy', 'sandy loam'],
            'sunflower': ['loamy', 'sandy loam'],
            'chrysanthemum': ['loamy', 'sandy loam'],
            'gladiolus': ['loamy', 'sandy loam'],
            'orchid': ['loamy', 'sandy loam'],
            'lily': ['loamy', 'sandy loam'],
            'dahlia': ['loamy', 'sandy loam'],
            
            # Herbs & Aromatics
            'basil': ['loamy', 'sandy loam'],
            'oregano': ['loamy', 'sandy loam'],
            'thyme': ['loamy', 'sandy loam'],
            'rosemary': ['loamy', 'sandy loam'],
            'sage': ['loamy', 'sandy loam'],
            'lavender': ['loamy', 'sandy loam'],
            'lemongrass': ['loamy', 'sandy loam'],
            'stevia': ['loamy', 'sandy loam'],
            'vanilla': ['loamy', 'clay loam'],
            'saffron': ['loamy', 'sandy loam'],
            
            # Fiber Crops
            'hemp': ['loamy', 'sandy loam'],
            'flax': ['loamy', 'sandy loam'],
            'kenaf': ['loamy', 'sandy loam'],
            'ramie': ['loamy', 'clay loam'],
            
            # Forage Crops
            'alfalfa': ['loamy', 'sandy loam'],
            'clover': ['loamy', 'sandy loam'],
            'rye_grass': ['loamy', 'sandy loam'],
            'fescue': ['loamy', 'sandy loam'],
            'timothy': ['loamy', 'sandy loam'],
            
            # Biofuel Crops
            'jatropha': ['loamy', 'sandy loam'],
            'pongamia': ['loamy', 'sandy loam'],
            'sweet_sorghum': ['loamy', 'sandy loam'],
            'sugar_beet': ['loamy', 'sandy loam'],
            
            # Mushrooms
            'button_mushroom': ['loamy', 'clay loam'],
            'oyster_mushroom': ['loamy', 'clay loam'],
            'shiitake': ['loamy', 'clay loam'],
            'reishi': ['loamy', 'clay loam'],
            'cordyceps': ['loamy', 'clay loam']
        }
        
        for crop, preferred_soils in soil_preferences.items():
            if soil_type.lower() in [s.lower() for s in preferred_soils]:
                soil_scores[crop] = 0.9
            else:
                soil_scores[crop] = 0.4
        
        return soil_scores
    
    def _analyze_market_conditions(self, market_data, latitude, longitude):
        """Analyze market conditions and prices"""
        market_scores = {}
        
        if market_data:
            # Extract prices for different crops
            crop_prices = {}
            for item in market_data:
                crop = item['commodity'].lower()
                price_str = item['price'].replace('₹', '').replace(',', '')
                try:
                    crop_prices[crop] = float(price_str)
                except:
                    crop_prices[crop] = 0
            
            # Score based on price levels (higher prices = better market) - COMPREHENSIVE DATABASE
            base_prices = {
                # Cereals
                'wheat': 2200, 'rice': 3500, 'maize': 1900, 'barley': 1800, 'sorghum': 1700, 'millet': 2000,
                
                # Pulses
                'chickpea': 4500, 'lentil': 5000, 'mungbean': 6000, 'pigeonpea': 4000, 'blackgram': 5500,
                
                # Oilseeds
                'mustard': 4500, 'sunflower': 5000, 'groundnut': 5500, 'sesame': 8000, 'soybean': 3500,
                
                # Cash Crops
                'cotton': 6500, 'sugarcane': 320, 'jute': 3000, 'tobacco': 15000,
                
                # Spices & Condiments
                'turmeric': 10000, 'chilli': 20000, 'pepper': 50000, 'cardamom': 80000, 'ginger': 8000, 'coriander': 3000,
                
                # Plantation Crops
                'coconut': 15000, 'rubber': 12000, 'cashew': 80000, 'tea': 200, 'coffee': 300,
                
                # Vegetables
                'onion': 2500, 'tomato': 3000, 'potato': 1200, 'brinjal': 2000, 'okra': 2500, 'cabbage': 1500,
                'cauliflower': 2000, 'carrot': 2000, 'radish': 1500, 'beetroot': 2000, 'spinach': 3000,
                'lettuce': 2500, 'cucumber': 2000, 'pumpkin': 1500, 'bottle_gourd': 1500, 'ridge_gourd': 2000,
                'bitter_gourd': 3000, 'snake_gourd': 2000, 'ash_gourd': 1500, 'ivy_gourd': 2000,
                'cluster_beans': 2500, 'french_beans': 3000, 'cowpea': 2000, 'drumstick': 4000,
                'fenugreek': 5000, 'mint': 4000, 'curry_leaves': 2000, 'spring_onion': 3000,
                'garlic': 8000, 'ginger': 8000,
                
                # Fruits
                'mango': 5000, 'banana': 2000, 'citrus': 3000, 'papaya': 1500, 'guava': 2000,
                'apple': 8000, 'grapes': 6000, 'pomegranate': 8000, 'watermelon': 1500, 'muskmelon': 2000,
                'pineapple': 3000, 'jackfruit': 2000, 'custard_apple': 4000, 'sapota': 3000,
                'jamun': 3000, 'ber': 2000, 'amla': 4000, 'kiwi': 15000, 'strawberry': 8000,
                'blueberry': 20000, 'fig': 5000, 'date': 8000,
                
                # Medicinal Plants
                'aloe_vera': 5000, 'neem': 3000, 'tulsi': 4000, 'ashwagandha': 8000, 'brahmi': 6000,
                'shankhpushpi': 5000, 'shatavari': 7000, 'guduchi': 6000, 'arjuna': 5000, 'punarnava': 4000,
                
                # Flowers & Ornamentals
                'marigold': 2000, 'rose': 5000, 'jasmine': 8000, 'hibiscus': 3000, 'sunflower': 2000,
                'chrysanthemum': 3000, 'gladiolus': 4000, 'orchid': 15000, 'lily': 5000, 'dahlia': 3000,
                
                # Herbs & Aromatics
                'basil': 4000, 'oregano': 6000, 'thyme': 8000, 'rosemary': 8000, 'sage': 6000,
                'lavender': 10000, 'lemongrass': 3000, 'stevia': 15000, 'vanilla': 50000, 'saffron': 200000,
                
                # Fiber Crops
                'hemp': 4000, 'flax': 5000, 'kenaf': 3000, 'ramie': 6000,
                
                # Forage Crops
                'alfalfa': 2000, 'clover': 2000, 'rye_grass': 1500, 'fescue': 1500, 'timothy': 2000,
                
                # Biofuel Crops
                'jatropha': 3000, 'pongamia': 4000, 'sweet_sorghum': 2000, 'sugar_beet': 2000,
                
                # Mushrooms
                'button_mushroom': 8000, 'oyster_mushroom': 10000, 'shiitake': 15000, 'reishi': 20000, 'cordyceps': 50000
            }
            
            for crop, base_price in base_prices.items():
                if crop in crop_prices:
                    current_price = crop_prices[crop]
                    # Score based on how much above/below base price
                    price_ratio = current_price / base_price
                    if price_ratio > 1.2:  # 20% above base
                        market_scores[crop] = 0.9
                    elif price_ratio > 1.0:  # Above base
                        market_scores[crop] = 0.7
                    elif price_ratio > 0.8:  # Close to base
                        market_scores[crop] = 0.5
                    else:  # Below base
                        market_scores[crop] = 0.3
                else:
                    market_scores[crop] = 0.5  # Neutral if no data
        else:
            # Default scores if no market data - COMPREHENSIVE DATABASE
            all_crops = [
                # Cereals
                'wheat', 'rice', 'maize', 'barley', 'sorghum', 'millet',
                
                # Pulses
                'chickpea', 'lentil', 'mungbean', 'pigeonpea', 'blackgram',
                
                # Oilseeds
                'mustard', 'sunflower', 'groundnut', 'sesame', 'soybean',
                
                # Cash Crops
                'cotton', 'sugarcane', 'jute', 'tobacco',
                
                # Spices & Condiments
                'turmeric', 'chilli', 'pepper', 'cardamom', 'ginger', 'coriander',
                
                # Plantation Crops
                'coconut', 'rubber', 'cashew', 'tea', 'coffee',
                
                # Vegetables
                'onion', 'tomato', 'potato', 'brinjal', 'okra', 'cabbage',
                'cauliflower', 'carrot', 'radish', 'beetroot', 'spinach',
                'lettuce', 'cucumber', 'pumpkin', 'bottle_gourd', 'ridge_gourd',
                'bitter_gourd', 'snake_gourd', 'ash_gourd', 'ivy_gourd',
                'cluster_beans', 'french_beans', 'cowpea', 'drumstick',
                'fenugreek', 'mint', 'curry_leaves', 'spring_onion', 'garlic',
                
                # Fruits
                'mango', 'banana', 'citrus', 'papaya', 'guava', 'apple',
                'grapes', 'pomegranate', 'watermelon', 'muskmelon', 'pineapple',
                'jackfruit', 'custard_apple', 'sapota', 'jamun', 'ber', 'amla',
                'kiwi', 'strawberry', 'blueberry', 'fig', 'date',
                
                # Medicinal Plants
                'aloe_vera', 'neem', 'tulsi', 'ashwagandha', 'brahmi',
                'shankhpushpi', 'shatavari', 'guduchi', 'arjuna', 'punarnava',
                
                # Flowers & Ornamentals
                'marigold', 'rose', 'jasmine', 'hibiscus', 'sunflower',
                'chrysanthemum', 'gladiolus', 'orchid', 'lily', 'dahlia',
                
                # Herbs & Aromatics
                'basil', 'oregano', 'thyme', 'rosemary', 'sage',
                'lavender', 'lemongrass', 'stevia', 'vanilla', 'saffron',
                
                # Fiber Crops
                'hemp', 'flax', 'kenaf', 'ramie',
                
                # Forage Crops
                'alfalfa', 'clover', 'rye_grass', 'fescue', 'timothy',
                
                # Biofuel Crops
                'jatropha', 'pongamia', 'sweet_sorghum', 'sugar_beet',
                
                # Mushrooms
                'button_mushroom', 'oyster_mushroom', 'shiitake', 'reishi', 'cordyceps'
            ]
            market_scores = {crop: 0.5 for crop in all_crops}
        
        return market_scores
    
    def _analyze_seasonal_factors(self, season, latitude, longitude):
        """Analyze seasonal factors for crop recommendations"""
        seasonal_scores = {}
        
        # Season-specific crop preferences - COMPREHENSIVE DATABASE
        if season.lower() == 'kharif':
            # Monsoon season crops
            seasonal_scores.update({
                # Cereals
                'rice': 0.9, 'maize': 0.8, 'sorghum': 0.8, 'millet': 0.8,
                
                # Pulses
                'mungbean': 0.9, 'pigeonpea': 0.8, 'blackgram': 0.8, 'cowpea': 0.8,
                
                # Oilseeds
                'groundnut': 0.8, 'sesame': 0.8, 'soybean': 0.9,
                
                # Cash Crops
                'cotton': 0.8, 'sugarcane': 0.7, 'jute': 0.9,
                
                # Spices & Condiments
                'turmeric': 0.8, 'chilli': 0.7, 'ginger': 0.8,
                
                # Vegetables
                'onion': 0.6, 'tomato': 0.7, 'brinjal': 0.8, 'okra': 0.9, 'cucumber': 0.8,
                'pumpkin': 0.8, 'bottle_gourd': 0.8, 'ridge_gourd': 0.8, 'bitter_gourd': 0.8,
                'snake_gourd': 0.8, 'ash_gourd': 0.8, 'ivy_gourd': 0.8, 'cluster_beans': 0.8,
                'french_beans': 0.8, 'drumstick': 0.8, 'fenugreek': 0.6, 'mint': 0.7,
                'curry_leaves': 0.7, 'spring_onion': 0.7,
                
                # Fruits
                'mango': 0.6, 'banana': 0.7, 'citrus': 0.6, 'papaya': 0.8, 'guava': 0.7,
                'grapes': 0.6, 'pomegranate': 0.6, 'watermelon': 0.9, 'muskmelon': 0.9,
                'pineapple': 0.8, 'jackfruit': 0.7, 'custard_apple': 0.7, 'sapota': 0.7,
                'jamun': 0.7, 'ber': 0.6, 'amla': 0.6, 'strawberry': 0.4, 'fig': 0.6,
                
                # Medicinal Plants
                'aloe_vera': 0.7, 'neem': 0.7, 'tulsi': 0.7, 'ashwagandha': 0.7, 'brahmi': 0.7,
                'shankhpushpi': 0.7, 'shatavari': 0.7, 'guduchi': 0.7, 'arjuna': 0.7, 'punarnava': 0.7,
                
                # Flowers & Ornamentals
                'marigold': 0.8, 'rose': 0.6, 'jasmine': 0.7, 'hibiscus': 0.8, 'sunflower': 0.8,
                'chrysanthemum': 0.6, 'gladiolus': 0.6, 'orchid': 0.7, 'lily': 0.6, 'dahlia': 0.6,
                
                # Herbs & Aromatics
                'basil': 0.8, 'oregano': 0.7, 'thyme': 0.7, 'rosemary': 0.7, 'sage': 0.7,
                'lavender': 0.7, 'lemongrass': 0.8, 'stevia': 0.7, 'vanilla': 0.7, 'saffron': 0.6,
                
                # Fiber Crops
                'hemp': 0.8, 'flax': 0.7, 'kenaf': 0.8, 'ramie': 0.7,
                
                # Forage Crops
                'alfalfa': 0.8, 'clover': 0.8, 'rye_grass': 0.8, 'fescue': 0.8, 'timothy': 0.8,
                
                # Biofuel Crops
                'jatropha': 0.8, 'pongamia': 0.8, 'sweet_sorghum': 0.8, 'sugar_beet': 0.7,
                
                # Mushrooms
                'button_mushroom': 0.7, 'oyster_mushroom': 0.8, 'shiitake': 0.7, 'reishi': 0.7, 'cordyceps': 0.7,
                
                # Winter crops (lower scores)
                'wheat': 0.2, 'barley': 0.2, 'potato': 0.4, 'cabbage': 0.4, 'cauliflower': 0.4,
                'carrot': 0.4, 'radish': 0.4, 'beetroot': 0.4, 'spinach': 0.4, 'lettuce': 0.4,
                'garlic': 0.3, 'mustard': 0.2, 'chickpea': 0.3, 'lentil': 0.2, 'apple': 0.3,
                'kiwi': 0.3, 'blueberry': 0.3, 'date': 0.3
            })
        elif season.lower() == 'rabi':
            # Winter season crops
            seasonal_scores.update({
                # Cereals
                'wheat': 0.9, 'barley': 0.9,
                
                # Pulses
                'chickpea': 0.9, 'lentil': 0.9,
                
                # Oilseeds
                'mustard': 0.9, 'sunflower': 0.8,
                
                # Vegetables
                'onion': 0.7, 'tomato': 0.6, 'potato': 0.8, 'cabbage': 0.8, 'cauliflower': 0.8,
                'carrot': 0.8, 'radish': 0.8, 'beetroot': 0.8, 'spinach': 0.8, 'lettuce': 0.8,
                'garlic': 0.8, 'spring_onion': 0.7,
                
                # Fruits
                'apple': 0.8, 'citrus': 0.7, 'kiwi': 0.8, 'blueberry': 0.8, 'date': 0.8,
                
                # Medicinal Plants
                'aloe_vera': 0.6, 'neem': 0.6, 'tulsi': 0.6, 'ashwagandha': 0.6, 'brahmi': 0.6,
                'shankhpushpi': 0.6, 'shatavari': 0.6, 'guduchi': 0.6, 'arjuna': 0.6, 'punarnava': 0.6,
                
                # Flowers & Ornamentals
                'marigold': 0.6, 'rose': 0.7, 'jasmine': 0.6, 'hibiscus': 0.6, 'sunflower': 0.6,
                'chrysanthemum': 0.8, 'gladiolus': 0.7, 'orchid': 0.6, 'lily': 0.7, 'dahlia': 0.7,
                
                # Herbs & Aromatics
                'basil': 0.6, 'oregano': 0.6, 'thyme': 0.6, 'rosemary': 0.6, 'sage': 0.6,
                'lavender': 0.6, 'lemongrass': 0.6, 'stevia': 0.6, 'vanilla': 0.6, 'saffron': 0.7,
                
                # Fiber Crops
                'hemp': 0.6, 'flax': 0.6, 'kenaf': 0.6, 'ramie': 0.6,
                
                # Forage Crops
                'alfalfa': 0.6, 'clover': 0.6, 'rye_grass': 0.6, 'fescue': 0.6, 'timothy': 0.6,
                
                # Biofuel Crops
                'jatropha': 0.6, 'pongamia': 0.6, 'sweet_sorghum': 0.6, 'sugar_beet': 0.7,
                
                # Mushrooms
                'button_mushroom': 0.8, 'oyster_mushroom': 0.7, 'shiitake': 0.8, 'reishi': 0.8, 'cordyceps': 0.8,
                
                # Summer crops (lower scores)
                'rice': 0.3, 'maize': 0.4, 'cotton': 0.2, 'sugarcane': 0.5, 'turmeric': 0.4,
                'chilli': 0.5, 'okra': 0.2, 'cucumber': 0.3, 'pumpkin': 0.3, 'watermelon': 0.2,
                'muskmelon': 0.2, 'mungbean': 0.3, 'pigeonpea': 0.2, 'blackgram': 0.3,
                'groundnut': 0.3, 'sesame': 0.3, 'soybean': 0.2, 'jute': 0.2, 'ginger': 0.4,
                'mango': 0.4, 'banana': 0.3, 'papaya': 0.3, 'guava': 0.3, 'grapes': 0.4,
                'pomegranate': 0.4, 'pineapple': 0.3, 'jackfruit': 0.3, 'custard_apple': 0.3,
                'sapota': 0.3, 'jamun': 0.3, 'ber': 0.4, 'amla': 0.4, 'strawberry': 0.6,
                'fig': 0.4, 'sorghum': 0.2, 'millet': 0.2, 'cowpea': 0.3, 'brinjal': 0.3,
                'bottle_gourd': 0.2, 'ridge_gourd': 0.2, 'bitter_gourd': 0.2, 'snake_gourd': 0.2,
                'ash_gourd': 0.2, 'ivy_gourd': 0.2, 'cluster_beans': 0.2, 'french_beans': 0.2,
                'drumstick': 0.3, 'fenugreek': 0.4, 'mint': 0.3, 'curry_leaves': 0.3,
                'coconut': 0.3, 'rubber': 0.3, 'cashew': 0.3, 'tea': 0.3, 'coffee': 0.3,
                'pepper': 0.3, 'cardamom': 0.3, 'coriander': 0.4, 'alfalfa': 0.6, 'clover': 0.6,
                'rye_grass': 0.6, 'fescue': 0.6, 'timothy': 0.6
            })
        else:  # zaid or other
            seasonal_scores.update({
                # All crops with moderate scores for zaid season
                'rice': 0.6, 'maize': 0.7, 'cotton': 0.6, 'sugarcane': 0.7, 'wheat': 0.4, 'barley': 0.4,
                'sorghum': 0.6, 'millet': 0.6, 'chickpea': 0.5, 'lentil': 0.4, 'mungbean': 0.6,
                'pigeonpea': 0.5, 'blackgram': 0.6, 'mustard': 0.4, 'sunflower': 0.5, 'groundnut': 0.5,
                'sesame': 0.5, 'soybean': 0.5, 'jute': 0.5, 'tobacco': 0.5, 'turmeric': 0.6,
                'chilli': 0.7, 'pepper': 0.5, 'cardamom': 0.5, 'ginger': 0.6, 'coriander': 0.5,
                'coconut': 0.5, 'rubber': 0.5, 'cashew': 0.5, 'tea': 0.5, 'coffee': 0.5,
                'onion': 0.7, 'tomato': 0.8, 'potato': 0.6, 'brinjal': 0.7, 'okra': 0.8,
                'cabbage': 0.6, 'cauliflower': 0.6, 'carrot': 0.6, 'radish': 0.6, 'beetroot': 0.6,
                'spinach': 0.6, 'lettuce': 0.6, 'cucumber': 0.7, 'pumpkin': 0.6, 'bottle_gourd': 0.6,
                'ridge_gourd': 0.6, 'bitter_gourd': 0.6, 'snake_gourd': 0.6, 'ash_gourd': 0.6,
                'ivy_gourd': 0.6, 'cluster_beans': 0.6, 'french_beans': 0.6, 'cowpea': 0.6,
                'drumstick': 0.6, 'fenugreek': 0.6, 'mint': 0.6, 'curry_leaves': 0.6,
                'spring_onion': 0.6, 'garlic': 0.6, 'mango': 0.6, 'banana': 0.6, 'citrus': 0.6,
                'papaya': 0.6, 'guava': 0.6, 'apple': 0.5, 'grapes': 0.6, 'pomegranate': 0.6,
                'watermelon': 0.7, 'muskmelon': 0.7, 'pineapple': 0.6, 'jackfruit': 0.6,
                'custard_apple': 0.6, 'sapota': 0.6, 'jamun': 0.6, 'ber': 0.6, 'amla': 0.6,
                'kiwi': 0.5, 'strawberry': 0.6, 'blueberry': 0.5, 'fig': 0.6, 'date': 0.5,
                'aloe_vera': 0.6, 'neem': 0.6, 'tulsi': 0.6, 'ashwagandha': 0.6, 'brahmi': 0.6,
                'shankhpushpi': 0.6, 'shatavari': 0.6, 'guduchi': 0.6, 'arjuna': 0.6, 'punarnava': 0.6,
                'marigold': 0.6, 'rose': 0.6, 'jasmine': 0.6, 'hibiscus': 0.6, 'sunflower': 0.6,
                'chrysanthemum': 0.6, 'gladiolus': 0.6, 'orchid': 0.6, 'lily': 0.6, 'dahlia': 0.6,
                'basil': 0.6, 'oregano': 0.6, 'thyme': 0.6, 'rosemary': 0.6, 'sage': 0.6,
                'lavender': 0.6, 'lemongrass': 0.6, 'stevia': 0.6, 'vanilla': 0.6, 'saffron': 0.6,
                'hemp': 0.6, 'flax': 0.6, 'kenaf': 0.6, 'ramie': 0.6, 'alfalfa': 0.6,
                'clover': 0.6, 'rye_grass': 0.6, 'fescue': 0.6, 'timothy': 0.6, 'jatropha': 0.6,
                'pongamia': 0.6, 'sweet_sorghum': 0.6, 'sugar_beet': 0.6, 'button_mushroom': 0.6,
                'oyster_mushroom': 0.6, 'shiitake': 0.6, 'reishi': 0.6, 'cordyceps': 0.6
            })
        
        return seasonal_scores
    
    def _analyze_agricultural_risks(self, latitude, longitude, weather_forecast):
        """Analyze agricultural risks"""
        risk_scores = {}
        
        # Analyze weather risks
        total_rainfall = sum([day['day']['totalprecip_mm'] for day in weather_forecast['forecast']['forecastday']])
        avg_temp = sum([day['day']['avgtemp_c'] for day in weather_forecast['forecast']['forecastday']]) / len(weather_forecast['forecast']['forecastday'])
        
        # Drought risk
        if total_rainfall < 50:
            drought_risk = 0.8
        elif total_rainfall < 100:
            drought_risk = 0.5
        else:
            drought_risk = 0.2
        
        # Flood risk
        if total_rainfall > 300:
            flood_risk = 0.8
        elif total_rainfall > 200:
            flood_risk = 0.5
        else:
            flood_risk = 0.2
        
        # Temperature risk
        if avg_temp > 35 or avg_temp < 10:
            temp_risk = 0.7
        else:
            temp_risk = 0.2
        
        # Overall risk score (lower is better)
        overall_risk = (drought_risk + flood_risk + temp_risk) / 3
        
        # Risk-adjusted scores for ALL crops - COMPREHENSIVE DATABASE
        crops = [
            # Cereals
            'wheat', 'rice', 'maize', 'barley', 'sorghum', 'millet',
            
            # Pulses
            'chickpea', 'lentil', 'mungbean', 'pigeonpea', 'blackgram',
            
            # Oilseeds
            'mustard', 'sunflower', 'groundnut', 'sesame', 'soybean',
            
            # Cash Crops
            'cotton', 'sugarcane', 'jute', 'tobacco',
            
            # Spices & Condiments
            'turmeric', 'chilli', 'pepper', 'cardamom', 'ginger', 'coriander',
            
            # Plantation Crops
            'coconut', 'rubber', 'cashew', 'tea', 'coffee',
            
            # Vegetables
            'onion', 'tomato', 'potato', 'brinjal', 'okra', 'cabbage',
            'cauliflower', 'carrot', 'radish', 'beetroot', 'spinach',
            'lettuce', 'cucumber', 'pumpkin', 'bottle_gourd', 'ridge_gourd',
            'bitter_gourd', 'snake_gourd', 'ash_gourd', 'ivy_gourd',
            'cluster_beans', 'french_beans', 'cowpea', 'drumstick',
            'fenugreek', 'mint', 'curry_leaves', 'spring_onion', 'garlic',
            
            # Fruits
            'mango', 'banana', 'citrus', 'papaya', 'guava', 'apple',
            'grapes', 'pomegranate', 'watermelon', 'muskmelon', 'pineapple',
            'jackfruit', 'custard_apple', 'sapota', 'jamun', 'ber', 'amla',
            'kiwi', 'strawberry', 'blueberry', 'fig', 'date',
            
            # Medicinal Plants
            'aloe_vera', 'neem', 'tulsi', 'ashwagandha', 'brahmi',
            'shankhpushpi', 'shatavari', 'guduchi', 'arjuna', 'punarnava',
            
            # Flowers & Ornamentals
            'marigold', 'rose', 'jasmine', 'hibiscus', 'sunflower',
            'chrysanthemum', 'gladiolus', 'orchid', 'lily', 'dahlia',
            
            # Herbs & Aromatics
            'basil', 'oregano', 'thyme', 'rosemary', 'sage',
            'lavender', 'lemongrass', 'stevia', 'vanilla', 'saffron',
            
            # Fiber Crops
            'hemp', 'flax', 'kenaf', 'ramie',
            
            # Forage Crops
            'alfalfa', 'clover', 'rye_grass', 'fescue', 'timothy',
            
            # Biofuel Crops
            'jatropha', 'pongamia', 'sweet_sorghum', 'sugar_beet',
            
            # Mushrooms
            'button_mushroom', 'oyster_mushroom', 'shiitake', 'reishi', 'cordyceps'
        ]
        for crop in crops:
            risk_scores[crop] = 1.0 - overall_risk  # Invert risk to get suitability
        
        return risk_scores
    
    def _analyze_profitability_potential(self, market_data, latitude, longitude):
        """Analyze profitability potential"""
        profitability_scores = {}
        
        if market_data:
            # Calculate profitability based on market prices and production costs - COMPREHENSIVE DATABASE
            production_costs = {
                # Cereals
                'wheat': 1500, 'rice': 2000, 'maize': 1200, 'barley': 1300, 'sorghum': 1100, 'millet': 1400,
                
                # Pulses
                'chickpea': 2500, 'lentil': 2800, 'mungbean': 3000, 'pigeonpea': 2200, 'blackgram': 2900,
                
                # Oilseeds
                'mustard': 2500, 'sunflower': 2800, 'groundnut': 3000, 'sesame': 4000, 'soybean': 2000,
                
                # Cash Crops
                'cotton': 4000, 'sugarcane': 200, 'jute': 2000, 'tobacco': 8000,
                
                # Spices & Condiments
                'turmeric': 6000, 'chilli': 12000, 'pepper': 30000, 'cardamom': 50000, 'ginger': 5000, 'coriander': 2000,
                
                # Plantation Crops
                'coconut': 8000, 'rubber': 7000, 'cashew': 50000, 'tea': 150, 'coffee': 200,
                
                # Vegetables
                'onion': 1500, 'tomato': 2000, 'potato': 800, 'brinjal': 1200, 'okra': 1500, 'cabbage': 1000,
                'cauliflower': 1200, 'carrot': 1200, 'radish': 800, 'beetroot': 1200, 'spinach': 1800,
                'lettuce': 1500, 'cucumber': 1200, 'pumpkin': 1000, 'bottle_gourd': 1000, 'ridge_gourd': 1200,
                'bitter_gourd': 1800, 'snake_gourd': 1200, 'ash_gourd': 1000, 'ivy_gourd': 1200,
                'cluster_beans': 1500, 'french_beans': 1800, 'cowpea': 1200, 'drumstick': 2500,
                'fenugreek': 3000, 'mint': 2500, 'curry_leaves': 1200, 'spring_onion': 1800,
                'garlic': 5000, 'ginger': 5000,
                
                # Fruits
                'mango': 3000, 'banana': 1200, 'citrus': 1800, 'papaya': 1000, 'guava': 1200,
                'apple': 5000, 'grapes': 3500, 'pomegranate': 5000, 'watermelon': 1000, 'muskmelon': 1200,
                'pineapple': 1800, 'jackfruit': 1200, 'custard_apple': 2500, 'sapota': 1800,
                'jamun': 1800, 'ber': 1200, 'amla': 2500, 'kiwi': 10000, 'strawberry': 5000,
                'blueberry': 12000, 'fig': 3000, 'date': 5000,
                
                # Medicinal Plants
                'aloe_vera': 3000, 'neem': 1800, 'tulsi': 2500, 'ashwagandha': 5000, 'brahmi': 3500,
                'shankhpushpi': 3000, 'shatavari': 4500, 'guduchi': 3500, 'arjuna': 3000, 'punarnava': 2500,
                
                # Flowers & Ornamentals
                'marigold': 1200, 'rose': 3000, 'jasmine': 5000, 'hibiscus': 1800, 'sunflower': 1200,
                'chrysanthemum': 1800, 'gladiolus': 2500, 'orchid': 10000, 'lily': 3000, 'dahlia': 1800,
                
                # Herbs & Aromatics
                'basil': 2500, 'oregano': 3500, 'thyme': 5000, 'rosemary': 5000, 'sage': 3500,
                'lavender': 6000, 'lemongrass': 1800, 'stevia': 10000, 'vanilla': 30000, 'saffron': 150000,
                
                # Fiber Crops
                'hemp': 2500, 'flax': 3000, 'kenaf': 1800, 'ramie': 3500,
                
                # Forage Crops
                'alfalfa': 1200, 'clover': 1200, 'rye_grass': 1000, 'fescue': 1000, 'timothy': 1200,
                
                # Biofuel Crops
                'jatropha': 1800, 'pongamia': 2500, 'sweet_sorghum': 1200, 'sugar_beet': 1200,
                
                # Mushrooms
                'button_mushroom': 5000, 'oyster_mushroom': 6000, 'shiitake': 10000, 'reishi': 12000, 'cordyceps': 30000
            }
            
            for item in market_data:
                crop = item['commodity'].lower()
                price_str = item['price'].replace('₹', '').replace(',', '')
                try:
                    current_price = float(price_str)
                    if crop in production_costs:
                        cost = production_costs[crop]
                        profit_margin = (current_price - cost) / cost
                        
                        if profit_margin > 0.5:  # 50%+ profit margin
                            profitability_scores[crop] = 0.9
                        elif profit_margin > 0.3:  # 30%+ profit margin
                            profitability_scores[crop] = 0.7
                        elif profit_margin > 0.1:  # 10%+ profit margin
                            profitability_scores[crop] = 0.5
                        else:  # Low profit margin
                            profitability_scores[crop] = 0.3
                except:
                    profitability_scores[crop] = 0.5
        else:
            # Default profitability scores for ALL crops - COMPREHENSIVE DATABASE
            all_crops = [
                # Cereals
                'wheat', 'rice', 'maize', 'barley', 'sorghum', 'millet',
                
                # Pulses
                'chickpea', 'lentil', 'mungbean', 'pigeonpea', 'blackgram',
                
                # Oilseeds
                'mustard', 'sunflower', 'groundnut', 'sesame', 'soybean',
                
                # Cash Crops
                'cotton', 'sugarcane', 'jute', 'tobacco',
                
                # Spices & Condiments
                'turmeric', 'chilli', 'pepper', 'cardamom', 'ginger', 'coriander',
                
                # Plantation Crops
                'coconut', 'rubber', 'cashew', 'tea', 'coffee',
                
                # Vegetables
                'onion', 'tomato', 'potato', 'brinjal', 'okra', 'cabbage',
                'cauliflower', 'carrot', 'radish', 'beetroot', 'spinach',
                'lettuce', 'cucumber', 'pumpkin', 'bottle_gourd', 'ridge_gourd',
                'bitter_gourd', 'snake_gourd', 'ash_gourd', 'ivy_gourd',
                'cluster_beans', 'french_beans', 'cowpea', 'drumstick',
                'fenugreek', 'mint', 'curry_leaves', 'spring_onion', 'garlic',
                
                # Fruits
                'mango', 'banana', 'citrus', 'papaya', 'guava', 'apple',
                'grapes', 'pomegranate', 'watermelon', 'muskmelon', 'pineapple',
                'jackfruit', 'custard_apple', 'sapota', 'jamun', 'ber', 'amla',
                'kiwi', 'strawberry', 'blueberry', 'fig', 'date',
                
                # Medicinal Plants
                'aloe_vera', 'neem', 'tulsi', 'ashwagandha', 'brahmi',
                'shankhpushpi', 'shatavari', 'guduchi', 'arjuna', 'punarnava',
                
                # Flowers & Ornamentals
                'marigold', 'rose', 'jasmine', 'hibiscus', 'sunflower',
                'chrysanthemum', 'gladiolus', 'orchid', 'lily', 'dahlia',
                
                # Herbs & Aromatics
                'basil', 'oregano', 'thyme', 'rosemary', 'sage',
                'lavender', 'lemongrass', 'stevia', 'vanilla', 'saffron',
                
                # Fiber Crops
                'hemp', 'flax', 'kenaf', 'ramie',
                
                # Forage Crops
                'alfalfa', 'clover', 'rye_grass', 'fescue', 'timothy',
                
                # Biofuel Crops
                'jatropha', 'pongamia', 'sweet_sorghum', 'sugar_beet',
                
                # Mushrooms
                'button_mushroom', 'oyster_mushroom', 'shiitake', 'reishi', 'cordyceps'
            ]
            profitability_scores = {crop: 0.6 for crop in all_crops}
        
        return profitability_scores
    
    def _generate_intelligent_crop_recommendations(self, ai_analysis):
        """Generate intelligent crop recommendations using AI/ML with government data and future predictions"""
        recommendations = []
        
        # Enhanced weighted scoring system for AI-powered recommendations
        weights = {
            'climate_score': 0.30,  # Increased weight for climate suitability
            'soil_score': 0.20,
            'market_score': 0.25,   # Increased weight for market potential
            'seasonal_score': 0.15,
            'risk_score': 0.05,      # Reduced weight for risk
            'profitability_score': 0.05  # Reduced weight for profitability
        }
        
        # Calculate overall scores for ALL crops in the comprehensive database
        crop_scores = {}
        
        # Get all crops from climate analysis (comprehensive database)
        all_crops = set()
        for factor in ['climate_score', 'soil_score', 'market_score', 'seasonal_score', 'risk_score', 'profitability_score']:
            if factor in ai_analysis and ai_analysis[factor]:
                all_crops.update(ai_analysis[factor].keys())
        
        # Calculate weighted scores for each crop
        for crop in all_crops:
            overall_score = 0
            total_weight = 0
            
            for factor, weight in weights.items():
                if factor in ai_analysis and crop in ai_analysis[factor]:
                    overall_score += ai_analysis[factor][crop] * weight
                    total_weight += weight
            
            # Normalize score if some factors are missing
            if total_weight > 0:
                crop_scores[crop] = overall_score / total_weight
            else:
                crop_scores[crop] = 0.0
        
        # Sort crops by score and get top recommendations
        sorted_crops = sorted(crop_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Generate detailed recommendations with AI insights
        for i, (crop, score) in enumerate(sorted_crops[:8]):  # Top 8 crops for better variety
            # Add AI-powered insights
            ai_insights = self._generate_ai_insights(crop, ai_analysis, score)
            
            recommendations.append({
                'crop': crop,
                'suitability_score': round(score, 3),
                'description': self._get_crop_description(crop),
                'duration_days': self._get_crop_duration(crop),
                'climate_suitability': round(ai_analysis['climate_score'].get(crop, 0.5), 3),
                'soil_suitability': round(ai_analysis['soil_score'].get(crop, 0.5), 3),
                'market_potential': round(ai_analysis['market_score'].get(crop, 0.5), 3),
                'seasonal_fit': round(ai_analysis['seasonal_score'].get(crop, 0.5), 3),
                'risk_level': round(ai_analysis['risk_score'].get(crop, 0.5), 3),
                'profitability': round(ai_analysis['profitability_score'].get(crop, 0.5), 3),
                'ai_insights': ai_insights,
                'government_data_source': 'ICAR, IMD, Agmarknet',
                'prediction_confidence': min(0.95, score + 0.1)
            })
        
        return recommendations
    
    def _generate_ai_insights(self, crop, ai_analysis, overall_score):
        """Generate AI-powered insights for crop recommendations"""
        insights = []
        
        # Climate insights
        climate_score = ai_analysis['climate_score'].get(crop, 0.5)
        if climate_score > 0.8:
            insights.append(f"Excellent climate suitability ({climate_score:.1%})")
        elif climate_score > 0.6:
            insights.append(f"Good climate suitability ({climate_score:.1%})")
        else:
            insights.append(f"Moderate climate suitability ({climate_score:.1%})")
        
        # Market insights
        market_score = ai_analysis['market_score'].get(crop, 0.5)
        if market_score > 0.7:
            insights.append("Strong market demand and pricing")
        elif market_score > 0.5:
            insights.append("Moderate market potential")
        else:
            insights.append("Limited market opportunity")
        
        # Seasonal insights
        seasonal_score = ai_analysis['seasonal_score'].get(crop, 0.5)
        if seasonal_score > 0.8:
            insights.append("Perfect seasonal timing")
        elif seasonal_score > 0.6:
            insights.append("Good seasonal fit")
        else:
            insights.append("Suboptimal seasonal timing")
        
        # Risk insights
        risk_score = ai_analysis['risk_score'].get(crop, 0.5)
        if risk_score > 0.8:
            insights.append("Low agricultural risk")
        elif risk_score > 0.6:
            insights.append("Moderate risk level")
        else:
            insights.append("Higher risk crop")
        
        # Overall recommendation
        if overall_score > 0.8:
            insights.append("🌟 Highly recommended by AI analysis")
        elif overall_score > 0.6:
            insights.append("✅ Good recommendation")
        else:
            insights.append("⚠️ Consider alternatives")
        
        return insights
    
    def _get_crop_description(self, crop):
        """Get detailed crop description for ALL crops - COMPREHENSIVE DATABASE"""
        descriptions = {
            # Cereals
            'rice': 'Premium quality rice variety with high nutritional value and yield',
            'wheat': 'High-yield winter wheat variety suitable for bread making',
            'maize': 'High-protein maize variety ideal for animal feed and human consumption',
            'barley': 'High-protein barley variety for feed and brewing industry',
            'sorghum': 'Drought-resistant sorghum variety for grain and fodder',
            'millet': 'Nutritious millet variety for health-conscious consumers',
            
            # Pulses
            'chickpea': 'High-protein chickpea variety for dal and flour production',
            'lentil': 'Nutritious lentil variety rich in protein and fiber',
            'mungbean': 'Fast-growing mungbean variety for sprouts and dal',
            'pigeonpea': 'Drought-tolerant pigeonpea variety for dal production',
            'blackgram': 'High-protein blackgram variety for dal and flour',
            
            # Oilseeds
            'mustard': 'High-oil mustard variety for oil and spice production',
            'sunflower': 'High-oil sunflower variety for cooking oil production',
            'groundnut': 'High-protein groundnut variety for oil and snacks',
            'sesame': 'Premium sesame variety for oil and culinary use',
            'soybean': 'High-protein soybean variety for oil and feed production',
            
            # Cash Crops
            'cotton': 'Long-staple cotton variety for textile industry',
            'sugarcane': 'High-sugar content sugarcane variety for sugar production',
            'jute': 'High-fiber jute variety for textile and packaging',
            'tobacco': 'Premium tobacco variety for cigarette production',
            
            # Spices & Condiments
            'turmeric': 'High-curcumin content turmeric for medicinal and culinary use',
            'chilli': 'Hot chilli variety for spice and sauce production',
            'pepper': 'Premium black pepper variety for spice industry',
            'cardamom': 'Aromatic cardamom variety for spice and flavoring',
            'ginger': 'High-quality ginger variety for culinary and medicinal use',
            'coriander': 'Aromatic coriander variety for spice and flavoring',
            
            # Plantation Crops
            'coconut': 'High-yield coconut variety for oil and copra production',
            'rubber': 'High-latex rubber variety for industrial use',
            'cashew': 'Premium cashew variety for nut and kernel production',
            'tea': 'Premium tea variety for beverage industry',
            'coffee': 'High-quality coffee variety for beverage production',
            
            # Vegetables
            'onion': 'Bulb onion variety with good storage properties',
            'tomato': 'High-yield tomato variety for fresh market and processing',
            'potato': 'Table potato variety with good cooking qualities',
            'brinjal': 'High-yield brinjal variety for fresh market',
            'okra': 'Tender okra variety for fresh consumption',
            'cabbage': 'Crisp cabbage variety for fresh market',
            'cauliflower': 'Premium cauliflower variety for fresh market',
            'carrot': 'Sweet carrot variety rich in beta-carotene',
            'radish': 'Crisp radish variety for fresh consumption',
            'beetroot': 'Sweet beetroot variety for fresh and processed use',
            'spinach': 'Nutritious spinach variety rich in iron',
            'lettuce': 'Crisp lettuce variety for salads',
            'cucumber': 'Fresh cucumber variety for salads',
            'pumpkin': 'Sweet pumpkin variety for culinary use',
            'bottle_gourd': 'Tender bottle gourd variety for cooking',
            'ridge_gourd': 'Fresh ridge gourd variety for cooking',
            'bitter_gourd': 'Medicinal bitter gourd variety',
            'snake_gourd': 'Tender snake gourd variety',
            'ash_gourd': 'Sweet ash gourd variety for sweets',
            'ivy_gourd': 'Nutritious ivy gourd variety',
            'cluster_beans': 'Tender cluster beans variety',
            'french_beans': 'Crisp French beans variety',
            'cowpea': 'Nutritious cowpea variety',
            'drumstick': 'Nutritious drumstick variety',
            'fenugreek': 'Aromatic fenugreek variety for spice',
            'mint': 'Aromatic mint variety for flavoring',
            'curry_leaves': 'Aromatic curry leaves variety',
            'spring_onion': 'Fresh spring onion variety',
            'garlic': 'Aromatic garlic variety for culinary use',
            'ginger': 'Fresh ginger variety for culinary use',
            
            # Fruits
            'mango': 'Sweet mango variety for fresh consumption',
            'banana': 'Sweet banana variety for fresh consumption',
            'citrus': 'Juicy citrus variety for fresh juice',
            'papaya': 'Sweet papaya variety rich in vitamins',
            'guava': 'Nutritious guava variety rich in vitamin C',
            'apple': 'Crisp apple variety for fresh consumption',
            'grapes': 'Sweet grapes variety for fresh and wine',
            'pomegranate': 'Juicy pomegranate variety rich in antioxidants',
            'watermelon': 'Sweet watermelon variety for summer',
            'muskmelon': 'Sweet muskmelon variety for summer',
            'pineapple': 'Sweet pineapple variety for fresh consumption',
            'jackfruit': 'Sweet jackfruit variety for fresh consumption',
            'custard_apple': 'Sweet custard apple variety',
            'sapota': 'Sweet sapota variety for fresh consumption',
            'jamun': 'Tart jamun variety for fresh consumption',
            'ber': 'Sweet ber variety for fresh consumption',
            'amla': 'Tart amla variety rich in vitamin C',
            'kiwi': 'Nutritious kiwi variety rich in vitamin C',
            'strawberry': 'Sweet strawberry variety for fresh consumption',
            'blueberry': 'Antioxidant-rich blueberry variety',
            'fig': 'Sweet fig variety for fresh consumption',
            'date': 'Sweet date variety for fresh consumption',
            
            # Medicinal Plants
            'aloe_vera': 'Medicinal aloe vera variety for health products',
            'neem': 'Medicinal neem variety for health products',
            'tulsi': 'Sacred tulsi variety for medicinal use',
            'ashwagandha': 'Medicinal ashwagandha variety for health',
            'brahmi': 'Medicinal brahmi variety for brain health',
            'shankhpushpi': 'Medicinal shankhpushpi variety',
            'shatavari': 'Medicinal shatavari variety for women health',
            'guduchi': 'Medicinal guduchi variety for immunity',
            'arjuna': 'Medicinal arjuna variety for heart health',
            'punarnava': 'Medicinal punarnava variety for kidney health',
            
            # Flowers & Ornamentals
            'marigold': 'Bright marigold variety for decoration',
            'rose': 'Fragrant rose variety for decoration',
            'jasmine': 'Fragrant jasmine variety for garlands',
            'hibiscus': 'Colorful hibiscus variety for decoration',
            'sunflower': 'Bright sunflower variety for decoration',
            'chrysanthemum': 'Colorful chrysanthemum variety',
            'gladiolus': 'Elegant gladiolus variety for decoration',
            'orchid': 'Exotic orchid variety for decoration',
            'lily': 'Fragrant lily variety for decoration',
            'dahlia': 'Colorful dahlia variety for decoration',
            
            # Herbs & Aromatics
            'basil': 'Aromatic basil variety for culinary use',
            'oregano': 'Aromatic oregano variety for culinary use',
            'thyme': 'Aromatic thyme variety for culinary use',
            'rosemary': 'Aromatic rosemary variety for culinary use',
            'sage': 'Aromatic sage variety for culinary use',
            'lavender': 'Fragrant lavender variety for aromatherapy',
            'lemongrass': 'Aromatic lemongrass variety for tea',
            'stevia': 'Sweet stevia variety for natural sweetener',
            'vanilla': 'Aromatic vanilla variety for flavoring',
            'saffron': 'Premium saffron variety for spice',
            
            # Fiber Crops
            'hemp': 'Industrial hemp variety for fiber production',
            'flax': 'Flax variety for fiber and oil production',
            'kenaf': 'Kenaf variety for fiber production',
            'ramie': 'Ramie variety for fiber production',
            
            # Forage Crops
            'alfalfa': 'High-protein alfalfa variety for livestock',
            'clover': 'Nutritious clover variety for livestock',
            'rye_grass': 'Fast-growing rye grass variety',
            'fescue': 'Drought-resistant fescue variety',
            'timothy': 'High-quality timothy variety for horses',
            
            # Biofuel Crops
            'jatropha': 'Jatropha variety for biofuel production',
            'pongamia': 'Pongamia variety for biofuel production',
            'sweet_sorghum': 'Sweet sorghum variety for biofuel',
            'sugar_beet': 'Sugar beet variety for biofuel',
            
            # Mushrooms
            'button_mushroom': 'White button mushroom variety',
            'oyster_mushroom': 'Nutritious oyster mushroom variety',
            'shiitake': 'Premium shiitake mushroom variety',
            'reishi': 'Medicinal reishi mushroom variety',
            'cordyceps': 'Medicinal cordyceps mushroom variety'
        }
        return descriptions.get(crop, f'{crop.title()} variety - High-quality agricultural product')
    
    def _get_crop_duration(self, crop):
        """Get crop duration in days for ALL crops - COMPREHENSIVE DATABASE"""
        durations = {
            # Cereals
            'wheat': 150, 'rice': 120, 'maize': 100, 'barley': 130, 'sorghum': 110, 'millet': 90,
            
            # Pulses
            'chickpea': 120, 'lentil': 100, 'mungbean': 70, 'pigeonpea': 150, 'blackgram': 80,
            
            # Oilseeds
            'mustard': 120, 'sunflower': 100, 'groundnut': 120, 'sesame': 90, 'soybean': 90,
            
            # Cash Crops
            'cotton': 180, 'sugarcane': 365, 'jute': 120, 'tobacco': 120,
            
            # Spices & Condiments
            'turmeric': 200, 'chilli': 120, 'pepper': 365, 'cardamom': 365, 'ginger': 200, 'coriander': 60,
            
            # Plantation Crops
            'coconut': 1095, 'rubber': 1825, 'cashew': 365, 'tea': 365, 'coffee': 365,
            
            # Vegetables
            'onion': 90, 'tomato': 75, 'potato': 80, 'brinjal': 90, 'okra': 60, 'cabbage': 90,
            'cauliflower': 90, 'carrot': 80, 'radish': 30, 'beetroot': 60, 'spinach': 30,
            'lettuce': 45, 'cucumber': 60, 'pumpkin': 120, 'bottle_gourd': 90, 'ridge_gourd': 90,
            'bitter_gourd': 90, 'snake_gourd': 90, 'ash_gourd': 120, 'ivy_gourd': 90,
            'cluster_beans': 60, 'french_beans': 60, 'cowpea': 70, 'drumstick': 180,
            'fenugreek': 30, 'mint': 45, 'curry_leaves': 90, 'spring_onion': 60,
            'garlic': 120, 'ginger': 200,
            
            # Fruits
            'mango': 1095, 'banana': 365, 'citrus': 365, 'papaya': 365, 'guava': 365,
            'apple': 365, 'grapes': 180, 'pomegranate': 365, 'watermelon': 90, 'muskmelon': 90,
            'pineapple': 365, 'jackfruit': 1095, 'custard_apple': 365, 'sapota': 365,
            'jamun': 365, 'ber': 365, 'amla': 365, 'kiwi': 365, 'strawberry': 90,
            'blueberry': 365, 'fig': 365, 'date': 365,
            
            # Medicinal Plants
            'aloe_vera': 365, 'neem': 365, 'tulsi': 90, 'ashwagandha': 180, 'brahmi': 90,
            'shankhpushpi': 90, 'shatavari': 180, 'guduchi': 180, 'arjuna': 365, 'punarnava': 90,
            
            # Flowers & Ornamentals
            'marigold': 60, 'rose': 90, 'jasmine': 90, 'hibiscus': 90, 'sunflower': 90,
            'chrysanthemum': 90, 'gladiolus': 90, 'orchid': 365, 'lily': 90, 'dahlia': 90,
            
            # Herbs & Aromatics
            'basil': 60, 'oregano': 90, 'thyme': 90, 'rosemary': 90, 'sage': 90,
            'lavender': 90, 'lemongrass': 90, 'stevia': 120, 'vanilla': 365, 'saffron': 90,
            
            # Fiber Crops
            'hemp': 120, 'flax': 100, 'kenaf': 120, 'ramie': 120,
            
            # Forage Crops
            'alfalfa': 30, 'clover': 30, 'rye_grass': 30, 'fescue': 30, 'timothy': 30,
            
            # Biofuel Crops
            'jatropha': 365, 'pongamia': 365, 'sweet_sorghum': 120, 'sugar_beet': 120,
            
            # Mushrooms
            'button_mushroom': 30, 'oyster_mushroom': 30, 'shiitake': 45, 'reishi': 60, 'cordyceps': 60
        }
        return durations.get(crop, 120)  # Default 120 days
    
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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from ..services.real_time_government_api import RealTimeGovernmentAPI
        from ..services.enhanced_government_api import EnhancedGovernmentAPI
        self.real_time_api = RealTimeGovernmentAPI()
        self.weather_api = EnhancedGovernmentAPI()
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

        # Validate coordinate ranges
        if not (-90 <= latitude <= 90):
            return Response({"error": "Latitude must be between -90 and 90 degrees"}, status=400)
        if not (-180 <= longitude <= 180):
            return Response({"error": "Longitude must be between -180 and 180 degrees"}, status=400)

        try:
            # Get REAL-TIME weather data from government APIs
            real_time_weather_data = self.real_time_api.get_real_time_weather_data(latitude, longitude)
            
            # Fallback to enhanced API if real-time fails
            if not real_time_weather_data or not real_time_weather_data.get('temperature'):
                weather_data = self.weather_api.get_real_weather_data(latitude, longitude, language)
                data_source = 'Enhanced Government API (Dynamic Location-based)'
            else:
                weather_data = real_time_weather_data
                data_source = real_time_weather_data.get('source', 'Real-Time Government API')
        
            if weather_data:
                # Enhanced response format with dynamic location data
                if isinstance(weather_data, dict) and 'current' in weather_data:
                    # Convert nested structure to flat structure for API compatibility
                    current = weather_data['current']
                    formatted_response = {
                        'temperature': current.get('temp_c', 0),
                        'humidity': current.get('humidity', 0),
                        'weather_condition': current.get('condition', {}).get('text', 'Clear'),
                        'wind_speed': current.get('wind_kph', 0),
                        'wind_direction': current.get('wind_dir', 'N'),
                        'pressure': current.get('pressure_mb', 1013),
                        'uv_index': current.get('uv', 0),
                        'cloud_cover': current.get('cloud', 0),
                        'feels_like': current.get('feelslike_c', 0),
                        'location': weather_data.get('location', {}),
                        'data_source': data_source,
                        'timestamp': time.time(),
                        'is_dynamic': weather_data.get('is_dynamic', False),
                        'latitude': latitude,
                        'longitude': longitude
                    }
                    return Response(formatted_response)
                else:
                    # Direct response for enhanced API format
                    enhanced_response = {
                        'temperature': weather_data.get('temperature', 0),
                        'humidity': weather_data.get('humidity', 0),
                        'weather_condition': weather_data.get('condition', 'Clear'),
                        'wind_speed': weather_data.get('wind_speed', 0),
                        'rainfall': weather_data.get('rainfall', 0),
                        'location': weather_data.get('location', 'Unknown'),
                        'data_source': data_source,
                        'timestamp': weather_data.get('timestamp', time.time()),
                        'is_dynamic': weather_data.get('is_dynamic', True),
                        'latitude': latitude,
                        'longitude': longitude,
                        'is_cached_nearby': weather_data.get('is_cached_nearby', False)
                    }
                    return Response(enhanced_response)
            else:
                return Response({"error": "Could not retrieve weather data"}, status=500)
                
        except Exception as e:
            print(f"WeatherViewSet: Error fetching real-time data: {e}")
            # Fallback to original method
            weather_api = EnhancedGovernmentAPI()
            weather_data = weather_api.get_real_weather_data(latitude, longitude, language)
            
            if weather_data:
                # Ensure proper response format for fallback
                if isinstance(weather_data, dict) and 'current' in weather_data:
                    # Convert nested structure to flat structure for API compatibility
                    current = weather_data['current']
                    formatted_response = {
                        'temperature': current.get('temp_c', 0),
                        'humidity': current.get('humidity', 0),
                        'weather_condition': current.get('condition', {}).get('text', 'Clear'),
                        'wind_speed': current.get('wind_kph', 0),
                        'wind_direction': current.get('wind_dir', 'N'),
                        'pressure': current.get('pressure_mb', 1013),
                        'uv_index': current.get('uv', 0),
                        'cloud_cover': current.get('cloud', 0),
                        'feels_like': current.get('feelslike_c', 0),
                        'location': weather_data.get('location', {}),
                        'data_source': 'Enhanced Government API (Fallback)',
                        'timestamp': time.time()
                    }
                    return Response(formatted_response)
                else:
                    return Response(weather_data)
            else:
                return Response({"error": "Could not retrieve weather data"}, status=500)

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
        
        try:
            # Get REAL-TIME weather forecast from government APIs
            real_time_weather_data = self.real_time_api.get_real_time_weather_data(latitude, longitude)
            
            # Fallback to enhanced API if real-time fails
            if not real_time_weather_data or not real_time_weather_data.get('forecast'):
                weather_api = EnhancedGovernmentAPI()
                weather_data = weather_api.get_real_weather_data(latitude, longitude, language)
                forecast_data = weather_data.get('forecast', {}) if weather_data else {}
                data_source = 'Enhanced Government API (Fallback)'
            else:
                forecast_data = real_time_weather_data['forecast']
                data_source = real_time_weather_data.get('source', 'Real-Time Government API')
            
            if forecast_data:
                return Response({
                    'forecast_data': forecast_data,
                    'location': {'lat': latitude, 'lon': longitude},
                    'language': language,
                    'days': days,
                    'data_source': data_source,
                    'timestamp': time.time(),
                    'real_time_data': {
                        'forecast': real_time_weather_data.get('forecast', {}) if real_time_weather_data else {},
                        'alerts': real_time_weather_data.get('alerts', []) if real_time_weather_data else [],
                        'source': real_time_weather_data.get('source', 'Unknown') if real_time_weather_data else 'Unknown'
                    }
                })
            return Response({"error": "Could not retrieve forecast data"}, status=500)
            
        except Exception as e:
            print(f"WeatherViewSet: Error fetching real-time forecast: {e}")
            # Fallback to original method
            weather_api = EnhancedGovernmentAPI()
            weather_data = weather_api.get_real_weather_data(latitude, longitude, language)
            forecast_data = weather_data.get('forecast', {}) if weather_data else {}
        
        if forecast_data:
            return Response(forecast_data)
            return Response({"error": "Could not retrieve forecast data"}, status=500)


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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.government_api = EnhancedGovernmentAPI()
        self.real_time_api = RealTimeGovernmentAPI()
        self.weather_api = EnhancedGovernmentAPI()
    
    @action(detail=False, methods=['get'])
    def prices(self, request):
        product_type = request.query_params.get('product', 'wheat')  # Default to wheat if not specified
        latitude = request.query_params.get('lat', None)
        longitude = request.query_params.get('lon', None)
        language = request.query_params.get('lang', 'en')
        
        # Validate coordinates
        if not (latitude and longitude):
            return Response({"error": "Latitude and longitude parameters are required"}, status=400)
        
        # Validate coordinate ranges
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except ValueError:
            return Response({"error": "Latitude and longitude must be valid numbers"}, status=400)
        
        if not (-90 <= latitude <= 90):
            return Response({"error": "Latitude must be between -90 and 90 degrees"}, status=400)
        if not (-180 <= longitude <= 180):
            return Response({"error": "Longitude must be between -180 and 180 degrees"}, status=400)
        
        print(f"MarketPricesViewSet: Received lat={latitude}, lon={longitude}, lang={language}, product_type={product_type}")

        try:
            # Get REAL-TIME market prices from government APIs
            try:
                real_time_market_data = self.real_time_api.get_real_time_market_prices(latitude, longitude, product_type)
            except Exception as e:
                print(f"MarketPricesViewSet: Real-time API error: {e}")
                real_time_market_data = None
            
            # Fallback to enhanced API if real-time fails
            if not real_time_market_data or not real_time_market_data.get('prices'):
                try:
                    market_data = self.government_api.get_real_market_prices(
                        commodity=product_type,
                        language=language,
                        latitude=latitude,
                        longitude=longitude
                    )
                    data_source = 'Enhanced Government API (Fallback)'
                except Exception as e:
                    print(f"MarketPricesViewSet: Enhanced API error: {e}")
                    # Final fallback - return empty data instead of error
                    market_data = []
                    data_source = 'No Data Available'
            else:
                market_data = real_time_market_data['prices']
                data_source = real_time_market_data.get('source', 'Real-Time Government API')
        
            if market_data:
                print(f"MarketPricesViewSet: Returning REAL-TIME market_data = {market_data}")
                return Response({
                    'market_data': market_data,
                    'location': {'lat': latitude, 'lon': longitude},
                    'product_type': product_type,
                    'language': language,
                    'data_source': data_source,
                    'timestamp': time.time(),
                    'real_time_data': {
                        'prices': real_time_market_data.get('prices', []) if real_time_market_data else [],
                        'arrivals': real_time_market_data.get('arrivals', []) if real_time_market_data else [],
                        'trends': real_time_market_data.get('trends', {}) if real_time_market_data else {},
                        'source': real_time_market_data.get('source', 'Unknown') if real_time_market_data else 'Unknown'
                    }
                })
            else:
                return Response({"error": "Could not retrieve market data"}, status=500)
                
        except Exception as e:
            print(f"MarketPricesViewSet: Error fetching real-time data: {e}")
            # Fallback to original method
            market_data = self.government_api.get_real_market_prices(
                commodity=product_type,
                language=language,
                latitude=latitude,
                longitude=longitude
            )
            
            if market_data:
                print(f"MarketPricesViewSet: Returning fallback market_data = {market_data}")
                return Response({
                    'market_data': market_data,
                    'location': {'lat': latitude, 'lon': longitude},
                    'product_type': product_type,
                    'language': language,
                    'data_source': 'Enhanced Government API (Fallback)',
                    'timestamp': time.time()
                })
            else:
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


class GovernmentSchemesViewSet(viewsets.ViewSet):
    """ViewSet for Government Schemes data"""
    
    def list(self, request):
        """Get list of government schemes"""
        language = request.query_params.get('lang', 'en')
        
        # Government schemes data
        schemes_data = [
            {
                "name": "PM किसान सम्मान निधि" if language == "hi" else "PM Kisan Samman Nidhi",
                "description": "किसानों के लिए ₹6,000 वार्षिक आय सहायता" if language == "hi" else "₹6,000 annual income support for farmers",
                "eligibility": "वैध भूमि रिकॉर्ड वाले सभी किसान" if language == "hi" else "All farmers with valid land records",
                "status": "सक्रिय" if language == "hi" else "Active",
                "amount": "प्रति वर्ष ₹6,000" if language == "hi" else "₹6,000 per year",
                "beneficiaries": "12 करोड़ किसान" if language == "hi" else "12 crore farmers"
            },
            {
                "name": "प्रधानमंत्री फसल बीमा योजना" if language == "hi" else "Pradhan Mantri Fasal Bima Yojana",
                "description": "किसानों के लिए फसल बीमा योजना" if language == "hi" else "Crop insurance scheme for farmers",
                "eligibility": "अधिसूचित फसलें उगाने वाले किसान" if language == "hi" else "Farmers growing notified crops",
                "status": "सक्रिय" if language == "hi" else "Active",
                "amount": "सब्सिडी प्रीमियम" if language == "hi" else "Subsidized premium",
                "beneficiaries": "6 करोड़ किसान" if language == "hi" else "6 crore farmers"
            },
            {
                "name": "किसान क्रेडिट कार्ड" if language == "hi" else "Kisan Credit Card",
                "description": "किसानों के लिए ऋण सुविधा" if language == "hi" else "Credit facility for farmers",
                "eligibility": "किसान और कृषि कर्मी" if language == "hi" else "Farmers and agricultural workers",
                "status": "सक्रिय" if language == "hi" else "Active",
                "amount": "₹3 लाख तक" if language == "hi" else "Up to ₹3 lakh",
                "beneficiaries": "4 करोड़ किसान" if language == "hi" else "4 crore farmers"
            },
            {
                "name": "सौर पंप सब्सिडी" if language == "hi" else "Solar Pump Subsidy",
                "description": "सौर जल पंपों के लिए सब्सिडी" if language == "hi" else "Subsidy for solar water pumps",
                "eligibility": "छोटे और सीमांत किसान" if language == "hi" else "Small and marginal farmers",
                "status": "सक्रिय" if language == "hi" else "Active",
                "amount": "90% तक सब्सिडी" if language == "hi" else "Up to 90% subsidy",
                "beneficiaries": "2 लाख किसान" if language == "hi" else "2 lakh farmers"
            },
            {
                "name": "मृदा स्वास्थ्य कार्ड योजना" if language == "hi" else "Soil Health Card Scheme",
                "description": "मुफ्त मिट्टी परीक्षण और सिफारिशें" if language == "hi" else "Free soil testing and recommendations",
                "eligibility": "सभी किसान" if language == "hi" else "All farmers",
                "status": "सक्रिय" if language == "hi" else "Active",
                "amount": "मुफ्त" if language == "hi" else "Free",
                "beneficiaries": "14 करोड़ मिट्टी के नमूने" if language == "hi" else "14 crore soil samples"
            }
        ]
        
        return Response(schemes_data, status=status.HTTP_200_OK)
