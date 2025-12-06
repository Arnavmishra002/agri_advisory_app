#!/usr/bin/env python3
"""
Service Unit Tests
Tests individual service components and their functionality
"""

from django.test import TestCase
from unittest.mock import patch, Mock, MagicMock
import json
import time
from datetime import datetime

from ..services.realtime_government_ai import RealTimeGovernmentAI
from ..services.enhanced_government_api import EnhancedGovernmentAPI
from ..services.comprehensive_crop_recommendations import ComprehensiveCropRecommendations
from ..services.enhanced_market_prices import market_prices_service
from ..services.enhanced_pest_detection import pest_detection_service
from ..services.ollama_integration import OllamaIntegration
from ..services.google_ai_studio import GoogleAIStudio
from ..services.enhanced_multilingual import enhanced_multilingual
from ..services.enhanced_classifier import enhanced_classifier


class RealTimeGovernmentAITests(TestCase):
    """Test cases for RealTimeGovernmentAI service"""
    
    def setUp(self):
        """Set up test data"""
        self.ai_service = RealTimeGovernmentAI()
    
    def test_service_initialization(self):
        """Test service initialization"""
        self.assertIsNotNone(self.ai_service)
        self.assertIsNotNone(self.ai_service.gov_api)
        self.assertIsNotNone(self.ai_service.ultra_gov_api)
        self.assertIsNotNone(self.ai_service.deep_ai)
        self.assertIsNotNone(self.ai_service.ollama)
        self.assertIsInstance(self.ai_service.real_time_cache, dict)
        self.assertEqual(self.ai_service.cache_duration, 300)
    
    def test_cache_functionality(self):
        """Test cache functionality"""
        cache_key = "test_query_en_Delhi"
        test_data = {'response': 'Test response', 'data_source': 'test'}
        
        # Test cache setting
        self.ai_service.real_time_cache[cache_key] = (test_data, time.time())
        
        # Test cache retrieval
        cached_data, timestamp = self.ai_service.real_time_cache[cache_key]
        self.assertEqual(cached_data, test_data)
        self.assertIsInstance(timestamp, float)
    
    def test_cache_expiry(self):
        """Test cache expiry functionality"""
        cache_key = "test_query_en_Delhi"
        test_data = {'response': 'Test response', 'data_source': 'test'}
        
        # Set cache with old timestamp
        old_timestamp = time.time() - 400  # 400 seconds ago (expired)
        self.ai_service.real_time_cache[cache_key] = (test_data, old_timestamp)
        
        # Check if cache is expired
        cached_data, timestamp = self.ai_service.real_time_cache[cache_key]
        is_expired = time.time() - timestamp > self.ai_service.cache_duration
        self.assertTrue(is_expired)
    
    @patch('advisory.services.realtime_government_ai.analyze_query_deeply')
    def test_farming_query_processing(self, mock_deep_ai):
        """Test farming query processing"""
        # Mock deep AI analysis
        mock_deep_ai.return_value = {
            'intent': 'crop_recommendation',
            'entities': {'location': 'Delhi', 'crop': 'wheat'},
            'confidence': 0.9,
            'is_farming_related': True
        }
        
        # Mock government data
        with patch.object(self.ai_service, '_get_ultra_real_time_government_data') as mock_gov:
            mock_gov.return_value = {
                'crop_recommendations': [{'crop': 'Wheat', 'suitability': 'High'}],
                'weather': {'temperature': 25, 'condition': 'Sunny'},
                'market_prices': {'wheat': 2450}
            }
            
            result = self.ai_service.process_farming_query(
                'What crops should I grow in Delhi?',
                'en',
                'Delhi',
                28.7041,
                77.1025
            )
            
            self.assertIn('response', result)
            self.assertIn('data_source', result)
            self.assertIn('confidence', result)
            self.assertIn('timestamp', result)
            self.assertIn('deep_analysis', result)
            self.assertIn('real_time_data', result)
            
            mock_deep_ai.assert_called_once()
            mock_gov.assert_called_once()
    
    @patch('advisory.services.realtime_government_ai.analyze_query_deeply')
    def test_non_farming_query_processing(self, mock_deep_ai):
        """Test non-farming query processing"""
        # Mock deep AI analysis for non-farming query
        mock_deep_ai.return_value = {
            'intent': 'general_question',
            'entities': {},
            'confidence': 0.8,
            'is_farming_related': False
        }
        
        # Mock Ollama response
        with patch.object(self.ai_service.ollama, 'generate_response') as mock_ollama:
            mock_ollama.return_value = 'This is a general response from Ollama'
            
            result = self.ai_service.process_farming_query(
                'What is artificial intelligence?',
                'en'
            )
            
            self.assertIn('response', result)
            self.assertIn('data_source', result)
            self.assertIn('ai_model', result)
            
            mock_deep_ai.assert_called_once()
            mock_ollama.assert_called_once()
    
    def test_error_handling(self):
        """Test error handling in query processing"""
        # Test with None query
        result = self.ai_service.process_farming_query(None)
        
        self.assertIn('response', result)
        self.assertIn('error', result)
        self.assertEqual(result['data_source'], 'error_fallback')
    
    def test_farming_related_query_detection(self):
        """Test farming-related query detection"""
        # Test farming queries
        farming_queries = [
            'What crops should I grow?',
            'मुझे फसल सुझाव चाहिए',
            'Weather forecast for farming',
            'Market prices for wheat',
            'Government schemes for farmers'
        ]
        
        for query in farming_queries:
            is_farming = self.ai_service._is_farming_related_query({
                'query': query,
                'intent': 'farming',
                'confidence': 0.8
            })
            self.assertTrue(is_farming)
        
        # Test non-farming queries
        non_farming_queries = [
            'What is the capital of India?',
            'How to cook rice?',
            'Tell me a joke',
            'What is artificial intelligence?'
        ]
        
        for query in non_farming_queries:
            is_farming = self.ai_service._is_farming_related_query({
                'query': query,
                'intent': 'general',
                'confidence': 0.8
            })
            self.assertFalse(is_farming)


class EnhancedGovernmentAPITests(TestCase):
    """Test cases for EnhancedGovernmentAPI service"""
    
    def setUp(self):
        """Set up test data"""
        self.gov_api = EnhancedGovernmentAPI()
    
    def test_service_initialization(self):
        """Test service initialization"""
        self.assertIsNotNone(self.gov_api)
        self.assertIsNotNone(self.gov_api.api_endpoints)
        self.assertIsNotNone(self.gov_api.fallback_data)
        self.assertIsNotNone(self.gov_api.indian_locations)
        self.assertIsNotNone(self.gov_api.session)
        self.assertIsInstance(self.gov_api.cache, dict)
        self.assertEqual(self.gov_api.cache_timeout, 3600)
    
    def test_api_endpoints_configuration(self):
        """Test API endpoints configuration"""
        expected_endpoints = [
            'openweather', 'nominatim', 'agmarknet', 'imd',
            'data_gov', 'india_open_data', 'ip_api'
        ]
        
        for endpoint in expected_endpoints:
            self.assertIn(endpoint, self.gov_api.api_endpoints)
    
    def test_fallback_data_structure(self):
        """Test fallback data structure"""
        expected_keys = ['weather', 'market_prices', 'crop_data', 'schemes']
        
        for key in expected_keys:
            self.assertIn(key, self.gov_api.fallback_data)
    
    def test_indian_locations_structure(self):
        """Test Indian locations database structure"""
        self.assertIn('states', self.gov_api.indian_locations)
        self.assertIn('districts', self.gov_api.indian_locations)
        self.assertIn('cities', self.gov_api.indian_locations)
        
        # Test specific states
        self.assertIn('delhi', self.gov_api.indian_locations['states'])
        self.assertIn('mumbai', self.gov_api.indian_locations['states'])
        self.assertIn('bangalore', self.gov_api.indian_locations['states'])
    
    def test_location_coordinates_lookup(self):
        """Test location coordinates lookup"""
        # Test known locations
        lat, lon = self.gov_api._get_location_coordinates('Delhi')
        self.assertEqual(lat, 28.7041)
        self.assertEqual(lon, 77.1025)
        
        lat, lon = self.gov_api._get_location_coordinates('Mumbai')
        self.assertEqual(lat, 19.0760)
        self.assertEqual(lon, 72.8777)
        
        # Test unknown location (should default to Delhi)
        lat, lon = self.gov_api._get_location_coordinates('UnknownCity')
        self.assertEqual(lat, 28.7041)
        self.assertEqual(lon, 77.1025)
    
    def test_cache_functionality(self):
        """Test cache functionality"""
        cache_key = 'test_key'
        test_data = {'test': 'data'}
        
        # Test cache setting
        self.gov_api._set_cache_data(cache_key, test_data)
        
        # Test cache retrieval
        cached_data = self.gov_api._get_cached_data(cache_key)
        self.assertEqual(cached_data, test_data)
        
        # Test cache validity
        self.assertTrue(self.gov_api._is_cache_valid(cache_key))
    
    def test_cache_expiry(self):
        """Test cache expiry"""
        cache_key = 'test_key'
        test_data = {'test': 'data'}
        
        # Set cache with old timestamp
        self.gov_api.cache[cache_key] = {
            'data': test_data,
            'timestamp': time.time() - 4000  # 4000 seconds ago
        }
        
        # Should be expired
        self.assertFalse(self.gov_api._is_cache_valid(cache_key))
    
    @patch('requests.get')
    def test_weather_data_retrieval(self, mock_get):
        """Test weather data retrieval"""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'main': {'temp': 25.0, 'humidity': 60},
            'weather': [{'description': 'sunny'}],
            'name': 'Delhi'
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        weather_data = self.gov_api.get_weather_data('Delhi')
        
        self.assertIsInstance(weather_data, dict)
        self.assertIn('temperature', weather_data)
        self.assertIn('humidity', weather_data)
        self.assertIn('condition', weather_data)
        self.assertIn('location', weather_data)
        self.assertIn('timestamp', weather_data)
        
        mock_get.assert_called()
    
    @patch('requests.get')
    def test_market_data_retrieval(self, mock_get):
        """Test market data retrieval"""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': [
                {'commodity': 'Wheat', 'price': 2450, 'unit': 'Quintal'},
                {'commodity': 'Rice', 'price': 3200, 'unit': 'Quintal'}
            ]
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        market_data = self.gov_api.get_market_data('wheat', 'Delhi')
        
        self.assertIsInstance(market_data, dict)
        self.assertIn('wheat', market_data)
        self.assertIn('location', market_data)
        self.assertIn('timestamp', market_data)
        
        mock_get.assert_called()
    
    def test_api_failure_fallback(self):
        """Test fallback when API fails"""
        with patch('requests.get') as mock_get:
            # Mock API failure
            mock_get.side_effect = Exception('API Error')
            
            weather_data = self.gov_api.get_weather_data('Delhi')
            
            # Should return fallback data
            self.assertIsInstance(weather_data, dict)
            self.assertIn('temperature', weather_data)
            self.assertIn('location', weather_data)


class ComprehensiveCropRecommendationsTests(TestCase):
    """Test cases for ComprehensiveCropRecommendations service"""
    
    def setUp(self):
        """Set up test data"""
        self.crop_service = ComprehensiveCropRecommendations()
    
    def test_service_initialization(self):
        """Test service initialization"""
        self.assertIsNotNone(self.crop_service)
        self.assertIsNotNone(self.crop_service.session)
        self.assertIsNotNone(self.crop_service.crop_database)
        self.assertIsNotNone(self.crop_service.location_crops)
    
    def test_crop_database_structure(self):
        """Test crop database structure"""
        # Test that major crops are present
        major_crops = ['wheat', 'rice', 'maize', 'cotton', 'sugarcane']
        
        for crop in major_crops:
            self.assertIn(crop, self.crop_service.crop_database)
            
            crop_data = self.crop_service.crop_database[crop]
            self.assertIn('name_hindi', crop_data)
            self.assertIn('season', crop_data)
            self.assertIn('duration_days', crop_data)
            self.assertIn('yield_per_hectare', crop_data)
            self.assertIn('msp_per_quintal', crop_data)
            self.assertIn('profit_per_hectare', crop_data)
    
    def test_location_crops_mapping(self):
        """Test location-based crop mapping"""
        # Test major cities
        major_cities = ['delhi', 'mumbai', 'bangalore', 'kolkata', 'chennai']
        
        for city in major_cities:
            self.assertIn(city, self.crop_service.location_crops)
            
            crops = self.crop_service.location_crops[city]
            self.assertIsInstance(crops, list)
            self.assertGreater(len(crops), 0)
    
    def test_crop_recommendations_generation(self):
        """Test crop recommendations generation"""
        recommendations = self.crop_service.get_crop_recommendations(
            location='Delhi',
            latitude=28.7041,
            longitude=77.1025
        )
        
        self.assertIsInstance(recommendations, dict)
        self.assertIn('crop_recommendations', recommendations)
        self.assertIn('location', recommendations)
        self.assertIn('timestamp', recommendations)
        
        crop_recommendations = recommendations['crop_recommendations']
        self.assertIsInstance(crop_recommendations, list)
        self.assertGreater(len(crop_recommendations), 0)
        
        # Test recommendation structure
        for rec in crop_recommendations:
            self.assertIn('crop', rec)
            self.assertIn('suitability', rec)
            self.assertIn('profit', rec)
            self.assertIn('season', rec)
    
    def test_crop_recommendations_with_coordinates(self):
        """Test crop recommendations with coordinates only"""
        recommendations = self.crop_service.get_crop_recommendations(
            latitude=28.7041,
            longitude=77.1025
        )
        
        self.assertIsInstance(recommendations, dict)
        self.assertIn('crop_recommendations', recommendations)
    
    def test_crop_recommendations_without_location(self):
        """Test crop recommendations without location"""
        recommendations = self.crop_service.get_crop_recommendations()
        
        self.assertIsInstance(recommendations, dict)
        self.assertIn('crop_recommendations', recommendations)
        # Should use default location
    
    def test_crop_profitability_analysis(self):
        """Test crop profitability analysis"""
        crop_data = self.crop_service.crop_database['wheat']
        
        profitability = self.crop_service._analyze_crop_profitability(crop_data)
        
        self.assertIsInstance(profitability, dict)
        self.assertIn('profit_score', profitability)
        self.assertIn('risk_level', profitability)
        self.assertIn('recommendation', profitability)
    
    def test_seasonal_crop_filtering(self):
        """Test seasonal crop filtering"""
        # Test rabi season crops
        rabi_crops = self.crop_service._get_seasonal_crops('rabi')
        
        self.assertIsInstance(rabi_crops, list)
        self.assertGreater(len(rabi_crops), 0)
        
        # Test kharif season crops
        kharif_crops = self.crop_service._get_seasonal_crops('kharif')
        
        self.assertIsInstance(kharif_crops, list)
        self.assertGreater(len(kharif_crops), 0)
    
    def test_crop_search_functionality(self):
        """Test crop search functionality"""
        # Test exact crop search
        wheat_info = self.crop_service.search_crop('wheat')
        
        self.assertIsInstance(wheat_info, dict)
        self.assertIn('crop_info', wheat_info)
        self.assertIn('location', wheat_info)
        
        # Test partial crop search
        partial_results = self.crop_service.search_crop('whe')
        
        self.assertIsInstance(partial_results, dict)
        self.assertIn('crop_info', partial_results)


class OllamaIntegrationTests(TestCase):
    """Test cases for OllamaIntegration service"""
    
    def setUp(self):
        """Set up test data"""
        self.ollama = OllamaIntegration()
    
    def test_service_initialization(self):
        """Test service initialization"""
        self.assertIsNotNone(self.ollama)
        self.assertIsNotNone(self.ollama.api_url)
        self.assertIsNotNone(self.ollama.model_name)
        self.assertIsNotNone(self.ollama.session)
    
    @patch('requests.post')
    def test_response_generation(self, mock_post):
        """Test response generation"""
        # Mock Ollama API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'response': 'This is a test response from Ollama',
            'model': 'llama3',
            'done': True
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        response = self.ollama.generate_response('What is artificial intelligence?')
        
        self.assertIsInstance(response, dict)
        self.assertIn('response', response)
        self.assertIn('model', response)
        self.assertIn('timestamp', response)
        
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_api_failure_handling(self, mock_post):
        """Test API failure handling"""
        # Mock API failure
        mock_post.side_effect = Exception('API Error')
        
        response = self.ollama.generate_response('Test query')
        
        # Should return fallback response
        self.assertIsInstance(response, dict)
        self.assertIn('response', response)
        self.assertIn('error', response)
    
    def test_prompt_generation(self):
        """Test prompt generation"""
        query = 'What crops should I grow?'
        language = 'en'
        
        prompt = self.ollama._generate_prompt(query, language)
        
        self.assertIsInstance(prompt, str)
        self.assertIn(query, prompt)
        self.assertGreater(len(prompt), len(query))
    
    def test_language_specific_prompts(self):
        """Test language-specific prompt generation"""
        # Test English prompt
        en_prompt = self.ollama._generate_prompt('Hello', 'en')
        
        # Test Hindi prompt
        hi_prompt = self.ollama._generate_prompt('नमस्ते', 'hi')
        
        self.assertIsInstance(en_prompt, str)
        self.assertIsInstance(hi_prompt, str)
        self.assertNotEqual(en_prompt, hi_prompt)


class GoogleAIStudioTests(TestCase):
    """Test cases for GoogleAIStudio service"""
    
    def setUp(self):
        """Set up test data"""
        self.google_ai = GoogleAIStudio()
    
    def test_service_initialization(self):
        """Test service initialization"""
        self.assertIsNotNone(self.google_ai)
        # Note: Google AI Studio might not be initialized if API key is not available
        # This is expected behavior
    
    def test_fallback_response(self):
        """Test fallback response when Google AI is not available"""
        response = self.google_ai.generate_response('Test query')
        
        self.assertIsInstance(response, dict)
        self.assertIn('response', response)
        # Should return a fallback response


class EnhancedMultilingualTests(TestCase):
    """Test cases for enhanced multilingual support"""
    
    def test_language_detection(self):
        """Test language detection functionality"""
        # Test Hindi detection
        hindi_text = "मुझे फसल सुझाव चाहिए"
        detected_lang = enhanced_multilingual.detect_language(hindi_text)
        self.assertEqual(detected_lang, 'hi')
        
        # Test English detection
        english_text = "I need crop recommendations"
        detected_lang = enhanced_multilingual.detect_language(english_text)
        self.assertEqual(detected_lang, 'en')
        
        # Test mixed language
        mixed_text = "मुझे wheat की price चाहिए"
        detected_lang = enhanced_multilingual.detect_language(mixed_text)
        self.assertIn(detected_lang, ['hi', 'en'])
    
    def test_text_translation(self):
        """Test text translation functionality"""
        # Test Hindi to English
        hindi_text = "मुझे फसल सुझाव चाहिए"
        english_text = enhanced_multilingual.translate_text(hindi_text, 'hi', 'en')
        
        self.assertIsInstance(english_text, str)
        self.assertGreater(len(english_text), 0)
        
        # Test English to Hindi
        english_text = "I need crop recommendations"
        hindi_text = enhanced_multilingual.translate_text(english_text, 'en', 'hi')
        
        self.assertIsInstance(hindi_text, str)
        self.assertGreater(len(hindi_text), 0)
    
    def test_response_generation(self):
        """Test multilingual response generation"""
        # Test Hindi response
        hindi_response = enhanced_multilingual.generate_response(
            'मुझे फसल सुझाव चाहिए',
            'hi'
        )
        
        self.assertIsInstance(hindi_response, dict)
        self.assertIn('response', hindi_response)
        self.assertIn('language', hindi_response)
        
        # Test English response
        english_response = enhanced_multilingual.generate_response(
            'I need crop recommendations',
            'en'
        )
        
        self.assertIsInstance(english_response, dict)
        self.assertIn('response', english_response)
        self.assertIn('language', english_response)


class EnhancedClassifierTests(TestCase):
    """Test cases for enhanced classifier"""
    
    def test_query_classification(self):
        """Test query classification functionality"""
        # Test farming query
        farming_query = "मुझे फसल सुझाव चाहिए"
        classification = enhanced_classifier.classify_query(farming_query)
        
        self.assertIsInstance(classification, dict)
        self.assertIn('category', classification)
        self.assertIn('confidence', classification)
        self.assertIn('entities', classification)
        
        # Test weather query
        weather_query = "आज का मौसम कैसा है"
        classification = enhanced_classifier.classify_query(weather_query)
        
        self.assertIsInstance(classification, dict)
        self.assertIn('category', classification)
        
        # Test market query
        market_query = "गेहूं की कीमत क्या है"
        classification = enhanced_classifier.classify_query(market_query)
        
        self.assertIsInstance(classification, dict)
        self.assertIn('category', classification)
    
    def test_entity_extraction(self):
        """Test entity extraction functionality"""
        query = "मुझे दिल्ली में गेहूं की खेती के लिए सुझाव चाहिए"
        entities = enhanced_classifier.extract_entities(query)
        
        self.assertIsInstance(entities, list)
        self.assertGreater(len(entities), 0)
        
        # Check for common entities
        entity_string = ' '.join(entities)
        self.assertTrue(any(entity in entity_string for entity in ['delhi', 'दिल्ली', 'wheat', 'गेहूं']))
    
    def test_intent_classification(self):
        """Test intent classification functionality"""
        # Test crop recommendation intent
        crop_query = "What crops should I grow?"
        intent = enhanced_classifier.classify_intent(crop_query)
        
        self.assertIsInstance(intent, dict)
        self.assertIn('intent', intent)
        self.assertIn('confidence', intent)
        
        # Test weather intent
        weather_query = "What's the weather like?"
        intent = enhanced_classifier.classify_intent(weather_query)
        
        self.assertIsInstance(intent, dict)
        self.assertIn('intent', intent)
        
        # Test market price intent
        market_query = "What's the price of wheat?"
        intent = enhanced_classifier.classify_intent(market_query)
        
        self.assertIsInstance(intent, dict)
        self.assertIn('intent', intent)

