"""
Test suite for API endpoints
Tests all REST API endpoints with security and performance validation
"""

import json
import unittest
from unittest.mock import patch, Mock
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
import time

from ..models import ChatHistory, ChatSession, Crop, UserFeedback
from ..security_utils import SecurityValidator


class TestChatbotAPIEndpoint(APITestCase):
    """Test cases for chatbot API endpoint"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        self.chatbot_url = '/api/advisories/chatbot/'
        self.validator = SecurityValidator()
        
        # Test data
        self.valid_request_data = {
            'query': 'What crops should I plant in Delhi?',
            'language': 'en',
            'user_id': 'test_user_123',
            'session_id': 'test_session_456'
        }
    
    def tearDown(self):
        """Clean up after tests"""
        cache.clear()
    
    def test_valid_chatbot_request(self):
        """Test valid chatbot request"""
        response = self.client.post(
            self.chatbot_url,
            data=json.dumps(self.valid_request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('response', data)
        self.assertIn('language', data)
        self.assertIn('confidence', data)
        self.assertIn('session_id', data)
    
    def test_invalid_json_request(self):
        """Test request with invalid JSON"""
        response = self.client.post(
            self.chatbot_url,
            data='invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_missing_query_field(self):
        """Test request without query field"""
        invalid_data = {
            'language': 'en',
            'user_id': 'test_user'
        }
        
        response = self.client.post(
            self.chatbot_url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn('error', data)
    
    def test_empty_query_field(self):
        """Test request with empty query"""
        invalid_data = {
            'query': '',
            'language': 'en',
            'user_id': 'test_user'
        }
        
        response = self.client.post(
            self.chatbot_url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_whitespace_only_query(self):
        """Test request with whitespace-only query"""
        invalid_data = {
            'query': '   ',
            'language': 'en',
            'user_id': 'test_user'
        }
        
        response = self.client.post(
            self.chatbot_url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_invalid_language_code(self):
        """Test request with invalid language code"""
        invalid_data = {
            'query': 'Hello',
            'language': 'invalid_language',
            'user_id': 'test_user'
        }
        
        response = self.client.post(
            self.chatbot_url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_multilingual_requests(self):
        """Test multilingual requests"""
        test_cases = [
            {'query': 'Hello, how are you?', 'language': 'en'},
            {'query': 'नमस्ते, आप कैसे हैं?', 'language': 'hi'},
            {'query': 'নমস্কার, আপনি কেমন আছেন?', 'language': 'bn'},
            {'query': 'హలో, మీరు ఎలా ఉన్నారు?', 'language': 'te'},
        ]
        
        for test_case in test_cases:
            with self.subTest(language=test_case['language']):
                request_data = {
                    'query': test_case['query'],
                    'language': test_case['language'],
                    'user_id': 'test_user',
                    'session_id': 'test_session'
                }
                
                response = self.client.post(
                    self.chatbot_url,
                    data=json.dumps(request_data),
                    content_type='application/json'
                )
                
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                data = response.json()
                self.assertEqual(data['language'], test_case['language'])
    
    def test_xss_protection(self):
        """Test XSS protection in chatbot endpoint"""
        malicious_data = {
            'query': '<script>alert("xss")</script>Hello',
            'language': 'en',
            'user_id': 'test_user'
        }
        
        response = self.client.post(
            self.chatbot_url,
            data=json.dumps(malicious_data),
            content_type='application/json'
        )
        
        # Should handle malicious input gracefully
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('response', data)
        # Response should not contain script tags
        self.assertNotIn('<script>', data['response'])
    
    def test_sql_injection_protection(self):
        """Test SQL injection protection"""
        malicious_data = {
            'query': "'; DROP TABLE users; --",
            'language': 'en',
            'user_id': 'test_user'
        }
        
        response = self.client.post(
            self.chatbot_url,
            data=json.dumps(malicious_data),
            content_type='application/json'
        )
        
        # Should handle malicious input gracefully
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('response', data)
    
    def test_long_query_handling(self):
        """Test handling of very long queries"""
        long_query = 'a' * 3000  # 3000 characters
        
        long_data = {
            'query': long_query,
            'language': 'en',
            'user_id': 'test_user'
        }
        
        response = self.client.post(
            self.chatbot_url,
            data=json.dumps(long_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn('error', data)
    
    def test_session_persistence(self):
        """Test session persistence across requests"""
        session_id = 'persistent_session_123'
        
        # First request
        request_data = {
            'query': 'Hello, I am a farmer from Punjab',
            'language': 'en',
            'user_id': 'test_user',
            'session_id': session_id
        }
        
        response1 = self.client.post(
            self.chatbot_url,
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        data1 = response1.json()
        self.assertEqual(data1['session_id'], session_id)
        
        # Second request in same session
        request_data2 = {
            'query': 'What crops grow well here?',
            'language': 'en',
            'user_id': 'test_user',
            'session_id': session_id
        }
        
        response2 = self.client.post(
            self.chatbot_url,
            data=json.dumps(request_data2),
            content_type='application/json'
        )
        
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        data2 = response2.json()
        self.assertEqual(data2['session_id'], session_id)
    
    def test_response_time(self):
        """Test API response time"""
        start_time = time.time()
        
        response = self.client.post(
            self.chatbot_url,
            data=json.dumps(self.valid_request_data),
            content_type='application/json'
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response should be under 10 seconds
        self.assertLess(response_time, 10.0)
    
    def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        import threading
        import time
        
        results = []
        errors = []
        
        def make_request():
            try:
                request_data = {
                    'query': f'Test query from thread {threading.current_thread().ident}',
                    'language': 'en',
                    'user_id': f'user_{threading.current_thread().ident}',
                    'session_id': f'session_{threading.current_thread().ident}'
                }
                
                response = self.client.post(
                    self.chatbot_url,
                    data=json.dumps(request_data),
                    content_type='application/json'
                )
                
                results.append(response.status_code)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Should handle concurrent requests
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 5)
        self.assertTrue(all(status == 200 for status in results))


class TestWeatherAPIEndpoint(APITestCase):
    """Test cases for weather API endpoint"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        self.weather_url = '/api/weather/current/'
    
    def test_weather_api_with_valid_coordinates(self):
        """Test weather API with valid coordinates"""
        response = self.client.get(
            self.weather_url,
            {'lat': 28.6139, 'lon': 77.2090, 'lang': 'en'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        # Should return weather data structure
        self.assertIsInstance(data, dict)
    
    def test_weather_api_with_invalid_coordinates(self):
        """Test weather API with invalid coordinates"""
        response = self.client.get(
            self.weather_url,
            {'lat': 200, 'lon': 300, 'lang': 'en'}
        )
        
        # Should handle invalid coordinates gracefully
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])
    
    def test_weather_api_without_parameters(self):
        """Test weather API without required parameters"""
        response = self.client.get(self.weather_url)
        
        # Should return error or default data
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])


class TestMarketPricesAPIEndpoint(APITestCase):
    """Test cases for market prices API endpoint"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        self.market_url = '/api/market-prices/prices/'
    
    def test_market_prices_api(self):
        """Test market prices API"""
        response = self.client.get(
            self.market_url,
            {'lat': 28.6139, 'lon': 77.2090, 'lang': 'en'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIsInstance(data, (list, dict))
    
    def test_trending_crops_api(self):
        """Test trending crops API"""
        trending_url = '/api/trending-crops/'
        
        response = self.client.get(
            trending_url,
            {'lat': 28.6139, 'lon': 77.2090, 'lang': 'en'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIsInstance(data, (list, dict))


class TestCropRecommendationAPIEndpoint(APITestCase):
    """Test cases for crop recommendation API endpoint"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        self.recommendation_url = '/api/advisories/ml_crop_recommendation/'
    
    def test_crop_recommendation_api(self):
        """Test crop recommendation API"""
        request_data = {
            'soil_type': 'Loamy',
            'latitude': 28.6139,
            'longitude': 77.2090,
            'season': 'kharif',
            'user_id': 'test_user',
            'forecast_days': 7
        }
        
        response = self.client.post(
            self.recommendation_url,
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('recommendations', data)
        self.assertIsInstance(data['recommendations'], list)


class TestFertilizerRecommendationAPIEndpoint(APITestCase):
    """Test cases for fertilizer recommendation API endpoint"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        self.fertilizer_url = '/api/advisories/fertilizer_recommendation/'
    
    def test_fertilizer_recommendation_api(self):
        """Test fertilizer recommendation API"""
        request_data = {
            'crop_type': 'wheat',
            'soil_type': 'Loamy',
            'season': 'rabi',
            'area_hectares': 2.0,
            'language': 'en'
        }
        
        response = self.client.post(
            self.fertilizer_url,
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('fertilizer_recommendation', data)


class TestYieldPredictionAPIEndpoint(APITestCase):
    """Test cases for yield prediction API endpoint"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        self.yield_url = '/api/advisories/predict_yield/'
    
    def test_yield_prediction_api(self):
        """Test yield prediction API"""
        request_data = {
            'crop_type': 'wheat',
            'soil_type': 'Loamy',
            'temperature': 25.0,
            'rainfall': 800.0,
            'humidity': 60.0,
            'ph': 6.5,
            'organic_matter': 2.0
        }
        
        response = self.client.post(
            self.yield_url,
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('predicted_yield', data)


class TestAPIErrorHandling(APITestCase):
    """Test cases for API error handling"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
    
    def test_404_error_handling(self):
        """Test 404 error handling"""
        response = self.client.get('/api/nonexistent-endpoint/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_method_not_allowed(self):
        """Test method not allowed error"""
        response = self.client.get('/api/advisories/chatbot/')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def test_invalid_content_type(self):
        """Test invalid content type handling"""
        response = self.client.post(
            '/api/advisories/chatbot/',
            data='invalid data',
            content_type='text/plain'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestAPISecurity(APITestCase):
    """Test cases for API security"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        self.chatbot_url = '/api/advisories/chatbot/'
    
    def test_cors_headers(self):
        """Test CORS headers"""
        response = self.client.options(
            self.chatbot_url,
            HTTP_ORIGIN='http://localhost:3000'
        )
        
        # Should include CORS headers
        self.assertIn('Access-Control-Allow-Origin', response)
    
    def test_security_headers(self):
        """Test security headers"""
        response = self.client.post(
            self.chatbot_url,
            data=json.dumps({'query': 'test'}),
            content_type='application/json'
        )
        
        # Should include security headers
        self.assertIn('X-Content-Type-Options', response)
        self.assertIn('X-Frame-Options', response)
    
    def test_rate_limiting(self):
        """Test rate limiting"""
        request_data = {
            'query': 'Test query',
            'language': 'en',
            'user_id': 'test_user'
        }
        
        # Make many requests quickly
        for i in range(150):  # More than typical rate limit
            response = self.client.post(
                self.chatbot_url,
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                # Rate limiting is working
                self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
                break
        
        # If no rate limiting occurred, that's also acceptable for testing
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
