#!/usr/bin/env python3
"""
Unified Service Architecture for Krishimitra AI
Consolidates all services into a clean, maintainable architecture
"""

import os
import json
import logging
import requests
import time
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from abc import ABC, abstractmethod
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import LabelEncoder, StandardScaler
import joblib

logger = logging.getLogger(__name__)


@dataclass
class ServiceConfig:
    """Configuration for services"""
    cache_duration: int = 300  # 5 minutes default
    timeout: int = 30
    retry_count: int = 3
    max_workers: int = 5


class BaseService(ABC):
    """Base service class with common functionality"""
    
    def __init__(self, config: ServiceConfig = None):
        self.config = config or ServiceConfig()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Krishimitra AI - Unified Service',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        self.cache = {}
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging for the service"""
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def _get_cached_data(self, key: str) -> Optional[Any]:
        """Get data from cache if valid"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.config.cache_duration:
                return data
            else:
                del self.cache[key]
        return None
    
    def _set_cached_data(self, key: str, data: Any):
        """Set data in cache"""
        self.cache[key] = (data, time.time())
    
    def _make_request(self, url: str, method: str = 'GET', **kwargs) -> Optional[Dict]:
        """Make HTTP request with retry logic"""
        for attempt in range(self.config.retry_count):
            try:
                response = self.session.request(
                    method, url, 
                    timeout=self.config.timeout,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                self.logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                if attempt == self.config.retry_count - 1:
                    self.logger.error(f"All request attempts failed for {url}")
                    return None
                time.sleep(2 ** attempt)  # Exponential backoff
        return None
    
    @abstractmethod
    def get_service_name(self) -> str:
        """Return the name of the service"""
        pass


class AIService(BaseService):
    """Unified AI Service - Consolidates all AI functionality"""
    
    def __init__(self, config: ServiceConfig = None):
        super().__init__(config)
        self.google_ai_key = os.getenv('GOOGLE_AI_API_KEY', '')
        self.ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self._initialize_ai_models()
    
    def get_service_name(self) -> str:
        return "AI Service"
    
    def _initialize_ai_models(self):
        """Initialize AI models and configurations"""
        self.ai_models = {
            'google_ai': {
                'enabled': bool(self.google_ai_key),
                'base_url': 'https://generativelanguage.googleapis.com/v1beta',
                'model': 'gemini-pro'
            },
            'ollama': {
                'enabled': True,
                'base_url': self.ollama_base_url,
                'model': 'llama3'
            }
        }
        
        # Query classification system
        self.classification_system = {
            'farming_keywords': [
                'crop', 'farming', 'agriculture', 'field', 'harvest', 'plant',
                'soil', 'fertilizer', 'pest', 'disease', 'weather', 'rain',
                'irrigation', 'yield', 'profit', 'market', 'price', 'mandi',
                'फसल', 'खेती', 'कृषि', 'मौसम', 'बारिश', 'सिंचाई', 'उपज', 'लाभ'
            ],
            'weather_keywords': [
                'weather', 'temperature', 'rain', 'humidity', 'wind', 'forecast',
                'मौसम', 'तापमान', 'बारिश', 'नमी', 'हवा', 'पूर्वानुमान'
            ],
            'market_keywords': [
                'price', 'market', 'mandi', 'cost', 'profit', 'loss', 'buy', 'sell',
                'कीमत', 'बाजार', 'मंडी', 'लागत', 'लाभ', 'हानि', 'खरीद', 'बिक्री'
            ]
        }
        
        # Response templates
        self.response_templates = {
            'farming_query': {
                'en': "Based on your farming query, I'll provide comprehensive agricultural guidance...",
                'hi': "आपके कृषि प्रश्न के आधार पर, मैं व्यापक कृषि मार्गदर्शन प्रदान करूंगा..."
            },
            'weather_query': {
                'en': "Let me get the latest weather information for your location...",
                'hi': "मैं आपके स्थान के लिए नवीनतम मौसम की जानकारी प्राप्त करता हूं..."
            },
            'market_query': {
                'en': "I'll fetch the current market prices for you...",
                'hi': "मैं आपके लिए वर्तमान बाजार भाव प्राप्त करूंगा..."
            },
            'general_query': {
                'en': "I'm Krishimitra AI, your intelligent agricultural assistant...",
                'hi': "मैं कृषिमित्र AI हूं, आपका बुद्धिमान कृषि सहायक..."
            }
        }
    
    def detect_language(self, text: str) -> str:
        """Detect language of the input text"""
        hindi_chars = sum(1 for char in text if '\u0900' <= char <= '\u097F')
        total_chars = len([c for c in text if c.isalpha()])
        
        if total_chars == 0:
            return 'en'
        
        hindi_ratio = hindi_chars / total_chars
        return 'hi' if hindi_ratio > 0.3 else 'en'
    
    def classify_query(self, query: str) -> Dict[str, Any]:
        """Classify the type of query"""
        query_lower = query.lower()
        
        # Calculate scores for different categories
        farming_score = self._calculate_farming_score(query_lower)
        weather_score = self._calculate_weather_score(query_lower)
        market_score = self._calculate_market_score(query_lower)
        
        # Determine primary category
        scores = {
            'farming_agriculture': farming_score,
            'weather_climate': weather_score,
            'market_economics': market_score,
            'general': 0.1
        }
        
        primary_category = max(scores, key=scores.get)
        confidence = scores[primary_category]
        
        return {
            'category': primary_category,
            'confidence': confidence,
            'language': self.detect_language(query),
            'requires_farming_expertise': farming_score > 0.3,
            'entities': self._extract_entities(query)
        }
    
    def _calculate_farming_score(self, query: str) -> float:
        """Calculate farming-related score"""
        farming_keywords = self.classification_system['farming_keywords']
        matches = sum(1 for keyword in farming_keywords if keyword in query)
        return min(matches / len(farming_keywords) * 10, 1.0)
    
    def _calculate_weather_score(self, query: str) -> float:
        """Calculate weather-related score"""
        weather_keywords = self.classification_system['weather_keywords']
        matches = sum(1 for keyword in weather_keywords if keyword in query)
        return min(matches / len(weather_keywords) * 10, 1.0)
    
    def _calculate_market_score(self, query: str) -> float:
        """Calculate market-related score"""
        market_keywords = self.classification_system['market_keywords']
        matches = sum(1 for keyword in market_keywords if keyword in query)
        return min(matches / len(market_keywords) * 10, 1.0)
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract entities from query"""
        entities = []
        
        # Common Indian locations
        locations = ['delhi', 'mumbai', 'bangalore', 'kolkata', 'chennai', 'hyderabad', 'pune', 'ahmedabad', 'jaipur', 'lucknow']
        for location in locations:
            if location in query.lower():
                entities.append(location)
        
        # Common crops
        crops = ['wheat', 'rice', 'maize', 'cotton', 'sugarcane', 'potato', 'onion', 'tomato']
        for crop in crops:
            if crop in query.lower():
                entities.append(crop)
        
        return entities
    
    def generate_response(self, query: str, classification: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate AI response based on query classification"""
        language = classification['language']
        category = classification['category']
        
        # Get appropriate template
        template_key = category.replace('_', '_query') if category != 'general' else 'general_query'
        template = self.response_templates.get(template_key, {}).get(language, "I'll help you with that.")
        
        # Try different AI services
        response = None
        data_source = 'fallback'
        
        # Try Google AI first if available
        if self.ai_models['google_ai']['enabled']:
            response = self._generate_google_ai_response(query, language, context)
            if response:
                data_source = 'google_ai'
        
        # Fallback to Ollama
        if not response and self.ai_models['ollama']['enabled']:
            response = self._generate_ollama_response(query, language, context)
            if response:
                data_source = 'ollama_ai'
        
        # Final fallback
        if not response:
            response = self._generate_fallback_response(query, classification, context)
            data_source = 'fallback'
        
        return {
            'response': response,
            'data_source': data_source,
            'confidence': classification['confidence'],
            'timestamp': datetime.now().isoformat(),
            'classification': classification,
            'context': context or {}
        }
    
    def _generate_google_ai_response(self, query: str, language: str, context: Dict[str, Any]) -> Optional[str]:
        """Generate response using Google AI"""
        try:
            url = f"{self.ai_models['google_ai']['base_url']}/models/{self.ai_models['google_ai']['model']}:generateContent"
            
            prompt = self._build_prompt(query, language, context)
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            
            headers = {
                'Authorization': f'Bearer {self.google_ai_key}',
                'Content-Type': 'application/json'
            }
            
            response = self._make_request(url, 'POST', json=payload, headers=headers)
            
            if response and 'candidates' in response:
                return response['candidates'][0]['content']['parts'][0]['text']
            
        except Exception as e:
            self.logger.error(f"Google AI error: {e}")
        
        return None
    
    def _generate_ollama_response(self, query: str, language: str, context: Dict[str, Any]) -> Optional[str]:
        """Generate response using Ollama"""
        try:
            url = f"{self.ai_models['ollama']['base_url']}/api/generate"
            
            prompt = self._build_prompt(query, language, context)
            
            payload = {
                "model": self.ai_models['ollama']['model'],
                "prompt": prompt,
                "stream": False
            }
            
            response = self._make_request(url, 'POST', json=payload)
            
            if response and 'response' in response:
                return response['response']
            
        except Exception as e:
            self.logger.error(f"Ollama error: {e}")
        
        return None
    
    def _build_prompt(self, query: str, language: str, context: Dict[str, Any]) -> str:
        """Build prompt for AI services"""
        base_prompt = f"""
You are Krishimitra AI, an intelligent agricultural assistant for Indian farmers.
You provide expert advice on farming, crops, weather, market prices, and government schemes.

User Query: {query}
Language: {language}
Context: {json.dumps(context, indent=2)}

Please provide a helpful, accurate, and detailed response in {language}.
Focus on practical, actionable advice for Indian farmers.
"""
        return base_prompt.strip()
    
    def _generate_fallback_response(self, query: str, classification: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Generate fallback response when AI services are unavailable"""
        language = classification['language']
        category = classification['category']
        
        if category == 'farming_agriculture':
            if language == 'hi':
                return "मैं आपके कृषि प्रश्न की सहायता करने के लिए यहां हूं। कृपया अधिक विशिष्ट जानकारी प्रदान करें।"
            else:
                return "I'm here to help with your farming question. Please provide more specific information."
        
        elif category == 'weather_climate':
            if language == 'hi':
                return "मैं आपके लिए मौसम की जानकारी प्राप्त करने का प्रयास कर रहा हूं।"
            else:
                return "I'm trying to get weather information for you."
        
        elif category == 'market_economics':
            if language == 'hi':
                return "मैं आपके लिए बाजार भाव प्राप्त करने का प्रयास कर रहा हूं।"
            else:
                return "I'm trying to get market prices for you."
        
        else:
            if language == 'hi':
                return "मैं कृषिमित्र AI हूं, आपका कृषि सहायक। मैं आपकी कैसे सहायता कर सकता हूं?"
            else:
                return "I'm Krishimitra AI, your agricultural assistant. How can I help you?"


class GovernmentService(BaseService):
    """Unified Government Service - Consolidates all government API integrations"""
    
    def __init__(self, config: ServiceConfig = None):
        super().__init__(config)
        self._initialize_apis()
    
    def get_service_name(self) -> str:
        return "Government Service"
    
    def _initialize_apis(self):
        """Initialize government API configurations"""
        self.api_endpoints = {
            'weather': {
                'imd': 'https://mausam.imd.gov.in/api/weather',
                'openweather': 'https://api.openweathermap.org/data/2.5/weather',
                'fallback': True
            },
            'market_prices': {
                'agmarknet': 'https://agmarknet.gov.in/PriceAndArrivals/CommodityDailyPriceAndArrivals.aspx',
                'enam': 'https://enam.gov.in/api/market-data',
                'fallback': True
            },
            'schemes': {
                'pm_kisan': 'https://pmkisan.gov.in/api/schemes',
                'soil_health': 'https://soilhealth.dac.gov.in/api/cards',
                'fallback': True
            }
        }
        
        # Fallback data
        self.fallback_data = {
            'weather': {
                'temperature': 25.0,
                'humidity': 60,
                'condition': 'Sunny',
                'wind_speed': 10,
                'pressure': 1013
            },
            'market_prices': {
                'wheat': {'price': 2450, 'unit': 'Quintal'},
                'rice': {'price': 3200, 'unit': 'Quintal'},
                'maize': {'price': 1870, 'unit': 'Quintal'}
            },
            'schemes': [
                {
                    'name': 'PM-Kisan',
                    'description': 'Direct income support to farmers',
                    'benefit': 'Rs. 6000 per year'
                }
            ]
        }
        
        # Indian locations database
        self.locations = {
            'delhi': {'lat': 28.7041, 'lon': 77.1025, 'state': 'Delhi'},
            'mumbai': {'lat': 19.0760, 'lon': 72.8777, 'state': 'Maharashtra'},
            'bangalore': {'lat': 12.9716, 'lon': 77.5946, 'state': 'Karnataka'},
            'kolkata': {'lat': 22.5726, 'lon': 88.3639, 'state': 'West Bengal'},
            'chennai': {'lat': 13.0827, 'lon': 80.2707, 'state': 'Tamil Nadu'}
        }
    
    def get_weather_data(self, location: str, latitude: float = None, longitude: float = None) -> Dict[str, Any]:
        """Get weather data for a location"""
        cache_key = f"weather_{location}_{latitude}_{longitude}"
        
        # Check cache first
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
        
        # Get coordinates if not provided
        if not latitude or not longitude:
            coords = self._get_location_coordinates(location)
            latitude, longitude = coords['lat'], coords['lon']
        
        # Try to get real weather data
        weather_data = self._fetch_weather_data(latitude, longitude)
        
        if not weather_data:
            weather_data = self.fallback_data['weather'].copy()
        
        weather_data.update({
            'location': location,
            'latitude': latitude,
            'longitude': longitude,
            'timestamp': datetime.now().isoformat(),
            'source': 'government_api' if weather_data != self.fallback_data['weather'] else 'fallback'
        })
        
        # Cache the result
        self._set_cached_data(cache_key, weather_data)
        
        return weather_data
    
    def get_market_prices(self, crop: str = None, location: str = None) -> Dict[str, Any]:
        """Get market prices for crops"""
        cache_key = f"prices_{crop}_{location}"
        
        # Check cache first
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
        
        # Try to get real market data
        market_data = self._fetch_market_prices(crop, location)
        
        if not market_data:
            market_data = self.fallback_data['market_prices'].copy()
        
        market_data.update({
            'crop': crop,
            'location': location,
            'timestamp': datetime.now().isoformat(),
            'source': 'government_api' if market_data != self.fallback_data['market_prices'] else 'fallback'
        })
        
        # Cache the result
        self._set_cached_data(cache_key, market_data)
        
        return market_data
    
    def get_government_schemes(self, location: str = None) -> Dict[str, Any]:
        """Get government schemes"""
        cache_key = f"schemes_{location}"
        
        # Check cache first
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
        
        # Try to get real scheme data
        schemes_data = self._fetch_government_schemes(location)
        
        if not schemes_data:
            schemes_data = self.fallback_data['schemes'].copy()
        
        schemes_data.update({
            'location': location,
            'timestamp': datetime.now().isoformat(),
            'source': 'government_api' if schemes_data != self.fallback_data['schemes'] else 'fallback'
        })
        
        # Cache the result
        self._set_cached_data(cache_key, schemes_data)
        
        return schemes_data
    
    def _get_location_coordinates(self, location: str) -> Dict[str, float]:
        """Get coordinates for a location"""
        location_lower = location.lower()
        
        # Check known locations
        for loc_name, coords in self.locations.items():
            if loc_name in location_lower:
                return coords
        
        # Default to Delhi
        return self.locations['delhi']
    
    def _fetch_weather_data(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """Fetch weather data from APIs"""
        # Try OpenWeather API first
        api_key = os.getenv('OPENWEATHER_API_KEY')
        if api_key:
            url = f"{self.api_endpoints['weather']['openweather']}?lat={latitude}&lon={longitude}&appid={api_key}"
            response = self._make_request(url)
            
            if response:
                return {
                    'temperature': response['main']['temp'] - 273.15,  # Convert from Kelvin
                    'humidity': response['main']['humidity'],
                    'condition': response['weather'][0]['description'],
                    'wind_speed': response['wind']['speed'],
                    'pressure': response['main']['pressure']
                }
        
        return None
    
    def _fetch_market_prices(self, crop: str, location: str) -> Optional[Dict[str, Any]]:
        """Fetch market prices from APIs"""
        # This would implement actual API calls to government services
        # For now, return None to use fallback data
        return None
    
    def _fetch_government_schemes(self, location: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch government schemes from APIs"""
        # This would implement actual API calls to government services
        # For now, return None to use fallback data
        return None


class CropService(BaseService):
    """Unified Crop Service - Consolidates all crop-related functionality"""
    
    def __init__(self, config: ServiceConfig = None):
        super().__init__(config)
        self._initialize_crop_database()
        self._initialize_ml_models()
    
    def get_service_name(self) -> str:
        return "Crop Service"
    
    def _initialize_crop_database(self):
        """Initialize comprehensive crop database"""
        self.crop_database = {
            'wheat': {
                'name_hindi': 'गेहूं',
                'season': 'rabi',
                'duration_days': 150,
                'yield_per_hectare': 45,
                'msp_per_quintal': 2125,
                'soil_type': 'loamy',
                'water_requirement': 'moderate',
                'temperature_range': '15-25°C',
                'profitability': 'high'
            },
            'rice': {
                'name_hindi': 'धान',
                'season': 'kharif',
                'duration_days': 120,
                'yield_per_hectare': 40,
                'msp_per_quintal': 1940,
                'soil_type': 'clayey',
                'water_requirement': 'high',
                'temperature_range': '20-35°C',
                'profitability': 'high'
            },
            'maize': {
                'name_hindi': 'मक्का',
                'season': 'kharif',
                'duration_days': 100,
                'yield_per_hectare': 35,
                'msp_per_quintal': 1870,
                'soil_type': 'loamy',
                'water_requirement': 'moderate',
                'temperature_range': '18-30°C',
                'profitability': 'high'
            }
        }
        
        # Location-based crop suitability
        self.location_crops = {
            'delhi': ['wheat', 'rice', 'maize', 'mustard', 'potato'],
            'mumbai': ['rice', 'sugarcane', 'cotton', 'turmeric', 'chili'],
            'bangalore': ['rice', 'ragi', 'maize', 'sugarcane', 'cotton'],
            'kolkata': ['rice', 'jute', 'potato', 'mustard', 'wheat'],
            'chennai': ['rice', 'sugarcane', 'cotton', 'groundnut', 'coconut']
        }
    
    def _initialize_ml_models(self):
        """Initialize ML models for crop recommendations"""
        self.models = {
            'crop_recommendation': None,
            'yield_prediction': None,
            'pest_detection': None
        }
        
        # Load pre-trained models if available
        self._load_models()
    
    def _load_models(self):
        """Load pre-trained ML models"""
        models_dir = 'models'
        
        for model_name in self.models:
            model_path = os.path.join(models_dir, f'{model_name}_model.pkl')
            if os.path.exists(model_path):
                try:
                    self.models[model_name] = joblib.load(model_path)
                    self.logger.info(f"Loaded {model_name} model")
                except Exception as e:
                    self.logger.error(f"Failed to load {model_name} model: {e}")
    
    def get_crop_recommendations(self, location: str, latitude: float = None, longitude: float = None, 
                                soil_type: str = None, season: str = None) -> Dict[str, Any]:
        """Get crop recommendations for a location"""
        cache_key = f"crops_{location}_{soil_type}_{season}"
        
        # Check cache first
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
        
        # Get suitable crops for location
        suitable_crops = self._get_suitable_crops(location, soil_type, season)
        
        # Analyze profitability and suitability
        recommendations = []
        for crop_name in suitable_crops:
            crop_data = self.crop_database[crop_name]
            
            recommendation = {
                'crop': crop_name,
                'crop_hindi': crop_data['name_hindi'],
                'season': crop_data['season'],
                'duration_days': crop_data['duration_days'],
                'yield_per_hectare': crop_data['yield_per_hectare'],
                'msp_per_quintal': crop_data['msp_per_quintal'],
                'soil_type': crop_data['soil_type'],
                'water_requirement': crop_data['water_requirement'],
                'temperature_range': crop_data['temperature_range'],
                'profitability': crop_data['profitability'],
                'suitability_score': self._calculate_suitability_score(crop_data, location, soil_type),
                'profit_score': self._calculate_profit_score(crop_data)
            }
            
            recommendations.append(recommendation)
        
        # Sort by suitability and profit
        recommendations.sort(key=lambda x: (x['suitability_score'], x['profit_score']), reverse=True)
        
        result = {
            'crop_recommendations': recommendations[:5],  # Top 5 recommendations
            'location': location,
            'latitude': latitude,
            'longitude': longitude,
            'soil_type': soil_type,
            'season': season,
            'timestamp': datetime.now().isoformat(),
            'total_crops_analyzed': len(recommendations)
        }
        
        # Cache the result
        self._set_cached_data(cache_key, result)
        
        return result
    
    def _get_suitable_crops(self, location: str, soil_type: str, season: str) -> List[str]:
        """Get suitable crops for location and conditions"""
        location_lower = location.lower()
        
        # Get crops suitable for location
        suitable_crops = []
        for loc_name, crops in self.location_crops.items():
            if loc_name in location_lower:
                suitable_crops.extend(crops)
                break
        
        # If no specific location match, use all crops
        if not suitable_crops:
            suitable_crops = list(self.crop_database.keys())
        
        # Filter by soil type if specified
        if soil_type:
            filtered_crops = []
            for crop in suitable_crops:
                crop_data = self.crop_database[crop]
                if soil_type.lower() in crop_data['soil_type'].lower():
                    filtered_crops.append(crop)
            suitable_crops = filtered_crops
        
        # Filter by season if specified
        if season:
            filtered_crops = []
            for crop in suitable_crops:
                crop_data = self.crop_database[crop]
                if season.lower() in crop_data['season'].lower():
                    filtered_crops.append(crop)
            suitable_crops = filtered_crops
        
        return suitable_crops
    
    def _calculate_suitability_score(self, crop_data: Dict[str, Any], location: str, soil_type: str) -> float:
        """Calculate crop suitability score"""
        score = 0.5  # Base score
        
        # Soil type match
        if soil_type and soil_type.lower() in crop_data['soil_type'].lower():
            score += 0.3
        
        # Location suitability (simplified)
        score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_profit_score(self, crop_data: Dict[str, Any]) -> float:
        """Calculate crop profit score"""
        # Based on MSP and yield
        msp = crop_data.get('msp_per_quintal', 0)
        yield_per_hectare = crop_data.get('yield_per_hectare', 0)
        
        # Simple profit calculation
        estimated_revenue = (msp * yield_per_hectare) / 10  # Convert quintal to tons
        estimated_cost = estimated_revenue * 0.6  # Assume 60% cost
        profit = estimated_revenue - estimated_cost
        
        # Normalize to 0-1 scale
        return min(profit / 50000, 1.0)  # Assume max profit of 50k per hectare
    
    def detect_pest_disease(self, crop: str, symptoms: str, location: str = None) -> Dict[str, Any]:
        """Detect pest or disease based on symptoms"""
        cache_key = f"pest_{crop}_{symptoms}"
        
        # Check cache first
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
        
        # Simple symptom-based detection
        pest_database = {
            'wheat': {
                'yellow_spots': {'pest': 'Yellow Rust', 'treatment': 'Fungicide spray'},
                'brown_patches': {'pest': 'Brown Rust', 'treatment': 'Fungicide spray'},
                'holes_in_leaves': {'pest': 'Army Worm', 'treatment': 'Insecticide spray'}
            },
            'rice': {
                'yellow_spots': {'pest': 'Bacterial Blight', 'treatment': 'Copper fungicide'},
                'white_powder': {'pest': 'Powdery Mildew', 'treatment': 'Sulfur spray'},
                'holes_in_leaves': {'pest': 'Rice Leaf Folder', 'treatment': 'Neem oil spray'}
            }
        }
        
        symptoms_lower = symptoms.lower()
        crop_pests = pest_database.get(crop.lower(), {})
        
        detected_pests = []
        for symptom, pest_info in crop_pests.items():
            if symptom in symptoms_lower:
                detected_pests.append({
                    'symptom': symptom,
                    'pest': pest_info['pest'],
                    'treatment': pest_info['treatment'],
                    'confidence': 0.8
                })
        
        result = {
            'crop': crop,
            'symptoms': symptoms,
            'location': location,
            'detected_pests': detected_pests,
            'recommendations': self._generate_pest_recommendations(detected_pests),
            'timestamp': datetime.now().isoformat()
        }
        
        # Cache the result
        self._set_cached_data(cache_key, result)
        
        return result
    
    def _generate_pest_recommendations(self, detected_pests: List[Dict[str, Any]]) -> List[str]:
        """Generate pest treatment recommendations"""
        recommendations = []
        
        for pest in detected_pests:
            recommendations.append(f"Treat {pest['pest']} with {pest['treatment']}")
        
        if not recommendations:
            recommendations.append("Monitor crop regularly for any signs of pests or diseases")
            recommendations.append("Maintain proper field hygiene and crop rotation")
        
        return recommendations


class UnifiedServiceManager:
    """Manager for all unified services"""
    
    def __init__(self):
        self.config = ServiceConfig()
        self.services = {
            'ai': AIService(self.config),
            'government': GovernmentService(self.config),
            'crop': CropService(self.config)
        }
        self.logger = logging.getLogger('UnifiedServiceManager')
    
    def process_query(self, query: str, session_id: str = None, location: str = None, 
                     latitude: float = None, longitude: float = None) -> Dict[str, Any]:
        """Process a query using the unified service architecture"""
        try:
            # Step 1: Classify the query using AI service
            classification = self.services['ai'].classify_query(query)
            
            # Step 2: Generate response based on classification
            if classification['category'] == 'farming_agriculture':
                # Get farming data from government and crop services
                weather_data = self.services['government'].get_weather_data(location, latitude, longitude)
                crop_recommendations = self.services['crop'].get_crop_recommendations(location, latitude, longitude)
                market_prices = self.services['government'].get_market_prices()
                
                context = {
                    'weather': weather_data,
                    'crop_recommendations': crop_recommendations,
                    'market_prices': market_prices,
                    'location': location
                }
                
                response = self.services['ai'].generate_response(query, classification, context)
                response['data_source'] = 'unified_farming_service'
                
            elif classification['category'] == 'weather_climate':
                weather_data = self.services['government'].get_weather_data(location, latitude, longitude)
                context = {'weather': weather_data, 'location': location}
                
                response = self.services['ai'].generate_response(query, classification, context)
                response['data_source'] = 'unified_weather_service'
                
            elif classification['category'] == 'market_economics':
                market_prices = self.services['government'].get_market_prices()
                context = {'market_prices': market_prices, 'location': location}
                
                response = self.services['ai'].generate_response(query, classification, context)
                response['data_source'] = 'unified_market_service'
                
            else:
                # General query
                response = self.services['ai'].generate_response(query, classification)
                response['data_source'] = 'unified_ai_service'
            
            # Add session information
            response['session_id'] = session_id
            response['service_manager'] = 'unified'
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            return {
                'response': 'I apologize, but I encountered an error processing your query. Please try again.',
                'data_source': 'error_fallback',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'session_id': session_id
            }
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all services"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'services': {}
        }
        
        for service_name, service in self.services.items():
            try:
                status['services'][service_name] = {
                    'name': service.get_service_name(),
                    'status': 'healthy',
                    'cache_size': len(service.cache),
                    'config': {
                        'cache_duration': service.config.cache_duration,
                        'timeout': service.config.timeout,
                        'retry_count': service.config.retry_count
                    }
                }
            except Exception as e:
                status['services'][service_name] = {
                    'name': service.get_service_name(),
                    'status': 'error',
                    'error': str(e)
                }
        
        return status
    
    def clear_cache(self, service_name: str = None):
        """Clear cache for specific service or all services"""
        if service_name and service_name in self.services:
            self.services[service_name].cache.clear()
            self.logger.info(f"Cleared cache for {service_name} service")
        else:
            for service in self.services.values():
                service.cache.clear()
            self.logger.info("Cleared cache for all services")


# Global instance
unified_service_manager = UnifiedServiceManager()







