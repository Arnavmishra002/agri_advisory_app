#!/usr/bin/env python3
"""
Comprehensive Test Suite for Consolidated Services
Tests the new consolidated AI and Government services
"""

import unittest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.conf import settings

# Import the consolidated services
from ..services.consolidated_ai_service import ConsolidatedAIService
from ..services.consolidated_government_service import ConsolidatedGovernmentService


class TestConsolidatedAIService(TestCase):
    """Test cases for ConsolidatedAIService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.ai_service = ConsolidatedAIService()
        
    def test_service_initialization(self):
        """Test that the service initializes correctly"""
        self.assertIsNotNone(self.ai_service)
        self.assertIsNotNone(self.ai_service.classification_system)
        self.assertIsNotNone(self.ai_service.response_templates)
        self.assertIn('farming_keywords', self.ai_service.classification_system)
        self.assertIn('farming_query', self.ai_service.response_templates)
    
    def test_language_detection(self):
        """Test language detection functionality"""
        # Test Hindi detection
        hindi_query = "मुझे फसल सुझाव चाहिए"
        detected_lang = self.ai_service._detect_language(hindi_query)
        self.assertEqual(detected_lang, 'hi')
        
        # Test English detection
        english_query = "I need crop recommendations"
        detected_lang = self.ai_service._detect_language(english_query)
        self.assertEqual(detected_lang, 'en')
        
        # Test mixed language
        mixed_query = "मुझे wheat की price चाहिए"
        detected_lang = self.ai_service._detect_language(mixed_query)
        self.assertIn(detected_lang, ['hi', 'en'])
    
    def test_farming_score_calculation(self):
        """Test farming score calculation"""
        farming_query = "मुझे गेहूं की खेती के लिए सुझाव चाहिए"
        score = self.ai_service._calculate_farming_score(farming_query)
        self.assertGreater(score, 0.3)  # Should be high for farming query
        
        non_farming_query = "hello how are you"
        score = self.ai_service._calculate_farming_score(non_farming_query)
        self.assertLess(score, 0.3)  # Should be low for non-farming query
    
    def test_weather_score_calculation(self):
        """Test weather score calculation"""
        weather_query = "आज का मौसम कैसा है"
        score = self.ai_service._calculate_weather_score(weather_query)
        self.assertGreater(score, 0.3)  # Should be high for weather query
        
        non_weather_query = "what is the capital of India"
        score = self.ai_service._calculate_weather_score(non_weather_query)
        self.assertLess(score, 0.3)  # Should be low for non-weather query
    
    def test_market_score_calculation(self):
        """Test market score calculation"""
        market_query = "गेहूं की कीमत क्या है"
        score = self.ai_service._calculate_market_score(market_query)
        self.assertGreater(score, 0.3)  # Should be high for market query
        
        non_market_query = "how to cook rice"
        score = self.ai_service._calculate_market_score(non_market_query)
        self.assertLess(score, 0.3)  # Should be low for non-market query
    
    def test_entity_extraction(self):
        """Test entity extraction functionality"""
        query = "मुझे दिल्ली में गेहूं की खेती के लिए सुझाव चाहिए"
        entities = self.ai_service._extract_entities(query)
        
        # Should extract location and crop entities
        self.assertGreater(len(entities), 0)
        # Check for common entities
        entity_string = ' '.join(entities)
        self.assertTrue(any(entity in entity_string for entity in ['delhi', 'दिल्ली', 'wheat', 'गेहूं']))
    
    def test_query_classification(self):
        """Test query classification functionality"""
        # Test farming query
        farming_query = "मुझे फसल सुझाव चाहिए"
        classification = self.ai_service.classify_query(farming_query)
        
        self.assertEqual(classification['category'], 'farming_agriculture')
        self.assertEqual(classification['language'], 'hi')
        self.assertGreater(classification['confidence'], 0.3)
        self.assertTrue(classification['requires_farming_expertise'])
        
        # Test weather query
        weather_query = "आज का मौसम कैसा है"
        classification = self.ai_service.classify_query(weather_query)
        
        self.assertEqual(classification['category'], 'weather_climate')
        self.assertGreater(classification['confidence'], 0.3)
        
        # Test market query
        market_query = "गेहूं की कीमत क्या है"
        classification = self.ai_service.classify_query(market_query)
        
        self.assertEqual(classification['category'], 'market_economics')
        self.assertGreater(classification['confidence'], 0.3)
    
    @patch('agri_advisory_app.advisory.services.consolidated_ai_service.ConsolidatedGovernmentService')
    def test_process_farming_query(self, mock_gov_service):
        """Test processing farming queries"""
        # Mock government service response
        mock_gov_instance = Mock()
        mock_gov_instance.get_farming_data.return_value = {
            'response': 'Test farming response',
            'crop_recommendations': [{'crop': 'Wheat', 'suitability': 'High'}]
        }
        mock_gov_service.return_value = mock_gov_instance
        
        farming_query = "मुझे फसल सुझाव चाहिए"
        result = self.ai_service.process_query(farming_query, 'hi', 'Delhi')
        
        self.assertEqual(result['data_source'], 'government_apis')
        self.assertIn('response', result)
        self.assertIn('classification', result)
        self.assertIn('farming_data', result)
    
    @patch('agri_advisory_app.advisory.services.consolidated_ai_service.ConsolidatedGovernmentService')
    def test_process_weather_query(self, mock_gov_service):
        """Test processing weather queries"""
        # Mock government service response
        mock_gov_instance = Mock()
        mock_gov_instance.get_weather_data.return_value = {
            'response': 'Test weather response',
            'temperature': 25.0,
            'condition': 'Sunny'
        }
        mock_gov_service.return_value = mock_gov_instance
        
        weather_query = "आज का मौसम कैसा है"
        result = self.ai_service.process_query(weather_query, 'hi', 'Delhi')
        
        self.assertEqual(result['data_source'], 'weather_apis')
        self.assertIn('response', result)
        self.assertIn('weather_data', result)
    
    def test_process_general_query(self):
        """Test processing general queries"""
        general_query = "what is the capital of India"
        result = self.ai_service.process_query(general_query, 'en')
        
        self.assertIn('response', result)
        self.assertIn('data_source', result)
        self.assertIn('classification', result)
        # Should fallback to general AI or fallback
        self.assertIn(result['data_source'], ['ollama_ai', 'google_ai', 'fallback', 'error_fallback'])
    
    def test_error_handling(self):
        """Test error handling in query processing"""
        # Test with empty query
        result = self.ai_service.process_query('')
        self.assertIn('response', result)
        self.assertIn('error', result)
        
        # Test with None query
        result = self.ai_service.process_query(None)
        self.assertIn('response', result)


class TestConsolidatedGovernmentService(TestCase):
    """Test cases for ConsolidatedGovernmentService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.gov_service = ConsolidatedGovernmentService()
    
    def test_service_initialization(self):
        """Test that the service initializes correctly"""
        self.assertIsNotNone(self.gov_service)
        self.assertIsNotNone(self.gov_service.api_endpoints)
        self.assertIsNotNone(self.gov_service.fallback_data)
        self.assertIsNotNone(self.gov_service.indian_locations)
        self.assertIn('imd_weather', self.gov_service.api_endpoints)
        self.assertIn('weather', self.gov_service.fallback_data)
    
    def test_cache_functionality(self):
        """Test cache functionality"""
        # Test cache validity
        self.assertFalse(self.gov_service._is_cache_valid('nonexistent_key'))
        
        # Test setting and getting cache
        test_data = {'test': 'data'}
        self.gov_service._set_cache_data('test_key', test_data)
        
        cached_data = self.gov_service._get_cached_data('test_key')
        self.assertEqual(cached_data, test_data)
        
        # Test cache validity after setting
        self.assertTrue(self.gov_service._is_cache_valid('test_key'))
    
    def test_location_coordinates(self):
        """Test location coordinate lookup"""
        # Test known locations
        lat, lon = self.gov_service._get_location_coordinates('Delhi')
        self.assertEqual(lat, 28.7041)
        self.assertEqual(lon, 77.1025)
        
        lat, lon = self.gov_service._get_location_coordinates('Mumbai')
        self.assertEqual(lat, 19.0760)
        self.assertEqual(lon, 72.8777)
        
        # Test unknown location (should default to Delhi)
        lat, lon = self.gov_service._get_location_coordinates('UnknownCity')
        self.assertEqual(lat, 28.7041)
        self.assertEqual(lon, 77.1025)
    
    def test_weather_data_retrieval(self):
        """Test weather data retrieval"""
        weather_data = self.gov_service.get_weather_data('Delhi')
        
        self.assertIsInstance(weather_data, dict)
        self.assertIn('temperature', weather_data)
        self.assertIn('humidity', weather_data)
        self.assertIn('condition', weather_data)
        self.assertIn('location', weather_data)
        self.assertIn('timestamp', weather_data)
    
    def test_market_data_retrieval(self):
        """Test market data retrieval"""
        market_data = self.gov_service.get_market_data('wheat', 'Delhi')
        
        self.assertIsInstance(market_data, dict)
        self.assertIn('wheat', market_data)
        self.assertIn('location', market_data)
        self.assertIn('timestamp', market_data)
    
    def test_farming_data_retrieval(self):
        """Test farming data retrieval"""
        farming_data = self.gov_service.get_farming_data('crop recommendations', 'Delhi')
        
        self.assertIsInstance(farming_data, dict)
        self.assertIn('response', farming_data)
        self.assertIn('crop_recommendations', farming_data)
        self.assertIn('weather', farming_data)
        self.assertIn('market', farming_data)
        self.assertIn('location', farming_data)
        self.assertIn('timestamp', farming_data)
    
    def test_government_schemes_retrieval(self):
        """Test government schemes retrieval"""
        schemes_data = self.gov_service.get_government_schemes('Delhi')
        
        self.assertIsInstance(schemes_data, dict)
        self.assertIn('schemes', schemes_data)
        self.assertIn('location', schemes_data)
        self.assertIn('timestamp', schemes_data)
        
        # Check that schemes is a list
        self.assertIsInstance(schemes_data['schemes'], list)
    
    def test_farming_response_generation(self):
        """Test farming response generation"""
        crop_recommendations = [
            {'crop': 'Wheat', 'suitability': 'High'},
            {'crop': 'Rice', 'suitability': 'Medium'}
        ]
        weather_data = {'condition': 'Sunny', 'temperature': 25.0}
        market_data = {'wheat': 2450, 'rice': 3200}
        
        response = self.gov_service._generate_farming_response(
            'test query', crop_recommendations, weather_data, market_data
        )
        
        self.assertIsInstance(response, str)
        self.assertIn('फसल सुझाव', response)
        self.assertIn('मौसम', response)
        self.assertIn('बाजार भाव', response)
    
    def test_cache_stats(self):
        """Test cache statistics"""
        # Add some test data to cache
        self.gov_service._set_cache_data('test1', {'data': 'test1'}, 'weather')
        self.gov_service._set_cache_data('test2', {'data': 'test2'}, 'prices')
        
        stats = self.gov_service.get_cache_stats()
        
        self.assertIn('total_entries', stats)
        self.assertIn('cache_types', stats)
        self.assertIn('oldest_entry', stats)
        self.assertIn('newest_entry', stats)
        
        self.assertGreaterEqual(stats['total_entries'], 2)
        self.assertIn('weather', stats['cache_types'])
        self.assertIn('prices', stats['cache_types'])
    
    def test_error_handling(self):
        """Test error handling"""
        # Test with invalid parameters
        weather_data = self.gov_service.get_weather_data('')
        self.assertIsInstance(weather_data, dict)
        
        market_data = self.gov_service.get_market_data('', '')
        self.assertIsInstance(market_data, dict)
        
        farming_data = self.gov_service.get_farming_data('', '')
        self.assertIsInstance(farming_data, dict)


class TestServiceIntegration(TestCase):
    """Integration tests for consolidated services"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.ai_service = ConsolidatedAIService()
        self.gov_service = ConsolidatedGovernmentService()
    
    def test_ai_to_government_integration(self):
        """Test integration between AI and Government services"""
        # Test farming query flow
        farming_query = "मुझे दिल्ली में फसल सुझाव चाहिए"
        
        # Classify the query
        classification = self.ai_service.classify_query(farming_query)
        self.assertEqual(classification['category'], 'farming_agriculture')
        
        # Process the query (should route to government service)
        result = self.ai_service.process_query(farming_query, 'hi', 'Delhi')
        
        self.assertIn('response', result)
        self.assertIn('data_source', result)
        self.assertIn('classification', result)
    
    def test_service_consistency(self):
        """Test consistency between services"""
        # Test that both services handle the same location consistently
        location = 'Mumbai'
        
        # AI service should classify location-based queries consistently
        query = f"{location} में मौसम कैसा है"
        classification = self.ai_service.classify_query(query)
        
        # Government service should handle the same location
        weather_data = self.gov_service.get_weather_data(location)
        market_data = self.gov_service.get_market_data('wheat', location)
        
        self.assertIn('location', weather_data)
        self.assertIn('location', market_data)


if __name__ == '__main__':
    unittest.main()



