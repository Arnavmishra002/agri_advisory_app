#!/usr/bin/env python3
"""
Comprehensive API Tests
Tests all API endpoints, authentication, and response formats
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from unittest.mock import patch, Mock
import json

from ..models import Crop, CropAdvisory, UserFeedback, ChatHistory, ChatSession, ForumPost

User = get_user_model()


class AuthenticationAPITests(APITestCase):
    """Test authentication endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='farmer'
        )
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            role='admin'
        )
    
    def test_token_obtain_pair(self):
        """Test JWT token obtain pair endpoint"""
        url = reverse('token_obtain_pair')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
    
    def test_token_obtain_pair_invalid_credentials(self):
        """Test JWT token obtain pair with invalid credentials"""
        url = reverse('token_obtain_pair')
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_token_refresh(self):
        """Test JWT token refresh endpoint"""
        # First get tokens
        token_url = reverse('token_obtain_pair')
        token_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        token_response = self.client.post(token_url, token_data, format='json')
        refresh_token = token_response.data['refresh']
        
        # Now refresh
        refresh_url = reverse('token_refresh')
        refresh_data = {'refresh': refresh_token}
        
        response = self.client.post(refresh_url, refresh_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)


class ChatbotAPITests(APITestCase):
    """Test chatbot API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.chatbot_url = reverse('chatbot-list')
    
    def test_chatbot_post_request(self):
        """Test chatbot POST request"""
        data = {
            'query': 'What crops should I grow in Delhi?',
            'session_id': 'test_session_123'
        }
        
        response = self.client.post(self.chatbot_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('response', response.data)
        self.assertIn('data_source', response.data)
        self.assertIn('confidence', response.data)
        self.assertIn('timestamp', response.data)
    
    def test_chatbot_farming_query(self):
        """Test chatbot with farming query"""
        data = {
            'query': 'मुझे दिल्ली में फसल सुझाव चाहिए',
            'session_id': 'test_session_123',
            'language': 'hi',
            'location': 'Delhi'
        }
        
        response = self.client.post(self.chatbot_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('response', response.data)
        # Should route to government APIs for farming query
        self.assertIn(response.data['data_source'], [
            'real_time_government_apis', 'government_apis', 'fallback'
        ])
    
    def test_chatbot_general_query(self):
        """Test chatbot with general query"""
        data = {
            'query': 'What is artificial intelligence?',
            'session_id': 'test_session_123'
        }
        
        response = self.client.post(self.chatbot_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('response', response.data)
        # Should route to AI for general query
        self.assertIn(response.data['data_source'], [
            'open_source_ai', 'general_ai', 'fallback'
        ])
    
    def test_chatbot_empty_query(self):
        """Test chatbot with empty query"""
        data = {
            'query': '',
            'session_id': 'test_session_123'
        }
        
        response = self.client.post(self.chatbot_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('response', response.data)
    
    def test_chatbot_missing_session_id(self):
        """Test chatbot without session_id"""
        data = {
            'query': 'Hello'
        }
        
        response = self.client.post(self.chatbot_url, data, format='json')
        
        # Should still work but might generate a session_id
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    @patch('advisory.services.realtime_government_ai.RealTimeGovernmentAI')
    def test_chatbot_with_mocked_service(self, mock_ai_service):
        """Test chatbot with mocked AI service"""
        # Mock the AI service response
        mock_instance = Mock()
        mock_instance.process_farming_query.return_value = {
            'response': 'Mocked response',
            'data_source': 'mocked_service',
            'confidence': 0.9,
            'timestamp': '2023-01-01T00:00:00Z'
        }
        mock_ai_service.return_value = mock_instance
        
        data = {
            'query': 'Test query',
            'session_id': 'test_session_123'
        }
        
        response = self.client.post(self.chatbot_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['response'], 'Mocked response')


class CropRecommendationsAPITests(APITestCase):
    """Test crop recommendations API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.crop_recommendations_url = reverse('realtime-gov-crop_recommendations-list')
    
    def test_crop_recommendations_get(self):
        """Test crop recommendations GET request"""
        params = {
            'location': 'Delhi',
            'latitude': 28.7041,
            'longitude': 77.1025
        }
        
        response = self.client.get(self.crop_recommendations_url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('crop_recommendations', response.data)
        self.assertIn('location', response.data)
        self.assertIn('timestamp', response.data)
    
    def test_crop_recommendations_without_location(self):
        """Test crop recommendations without location"""
        response = self.client.get(self.crop_recommendations_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should still return recommendations with default location
    
    def test_crop_recommendations_with_coordinates(self):
        """Test crop recommendations with coordinates only"""
        params = {
            'latitude': 28.7041,
            'longitude': 77.1025
        }
        
        response = self.client.get(self.crop_recommendations_url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('crop_recommendations', response.data)
    
    @patch('advisory.services.comprehensive_crop_recommendations.ComprehensiveCropRecommendations')
    def test_crop_recommendations_with_mocked_service(self, mock_service):
        """Test crop recommendations with mocked service"""
        # Mock the service response
        mock_instance = Mock()
        mock_instance.get_crop_recommendations.return_value = {
            'crop_recommendations': [
                {'crop': 'Wheat', 'suitability': 'High', 'profit': 50000},
                {'crop': 'Rice', 'suitability': 'Medium', 'profit': 45000}
            ],
            'location': 'Delhi',
            'timestamp': '2023-01-01T00:00:00Z'
        }
        mock_service.return_value = mock_instance
        
        params = {
            'location': 'Delhi',
            'latitude': 28.7041,
            'longitude': 77.1025
        }
        
        response = self.client.get(self.crop_recommendations_url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['crop_recommendations']), 2)


class WeatherAPITests(APITestCase):
    """Test weather API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.weather_url = reverse('realtime-gov-weather-list')
    
    def test_weather_get(self):
        """Test weather GET request"""
        params = {
            'location': 'Delhi',
            'latitude': 28.7041,
            'longitude': 77.1025
        }
        
        response = self.client.get(self.weather_url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('weather', response.data)
        self.assertIn('location', response.data)
        self.assertIn('timestamp', response.data)
    
    def test_weather_without_location(self):
        """Test weather without location"""
        response = self.client.get(self.weather_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should still return weather data with default location


class MarketPricesAPITests(APITestCase):
    """Test market prices API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.market_prices_url = reverse('realtime-gov-market_prices-list')
    
    def test_market_prices_get(self):
        """Test market prices GET request"""
        params = {
            'location': 'Delhi',
            'latitude': 28.7041,
            'longitude': 77.1025
        }
        
        response = self.client.get(self.market_prices_url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('market_prices', response.data)
        self.assertIn('location', response.data)
        self.assertIn('timestamp', response.data)
    
    def test_market_prices_with_crop(self):
        """Test market prices with specific crop"""
        params = {
            'location': 'Delhi',
            'crop': 'wheat',
            'latitude': 28.7041,
            'longitude': 77.1025
        }
        
        response = self.client.get(self.market_prices_url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('market_prices', response.data)


class GovernmentSchemesAPITests(APITestCase):
    """Test government schemes API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.schemes_url = reverse('realtime-gov-government_schemes-list')
    
    def test_government_schemes_get(self):
        """Test government schemes GET request"""
        params = {
            'location': 'Delhi',
            'latitude': 28.7041,
            'longitude': 77.1025
        }
        
        response = self.client.get(self.schemes_url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('schemes', response.data)
        self.assertIn('location', response.data)
        self.assertIn('timestamp', response.data)
    
    def test_government_schemes_without_location(self):
        """Test government schemes without location"""
        response = self.client.get(self.schemes_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should still return schemes


class PestDetectionAPITests(APITestCase):
    """Test pest detection API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.pest_detection_url = reverse('realtime-gov-pest_detection-list')
    
    def test_pest_detection_post(self):
        """Test pest detection POST request"""
        data = {
            'crop': 'wheat',
            'location': 'Delhi',
            'latitude': 28.7041,
            'longitude': 77.1025,
            'symptoms': 'Yellow spots on leaves'
        }
        
        response = self.client.post(self.pest_detection_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('pest_analysis', response.data)
        self.assertIn('recommendations', response.data)
        self.assertIn('location', response.data)
        self.assertIn('timestamp', response.data)
    
    def test_pest_detection_without_symptoms(self):
        """Test pest detection without symptoms"""
        data = {
            'crop': 'wheat',
            'location': 'Delhi'
        }
        
        response = self.client.post(self.pest_detection_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should still return general pest information


class LocationAPITests(APITestCase):
    """Test location API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.location_search_url = reverse('locations-search-list')
        self.reverse_geocoding_url = reverse('locations-reverse-list')
    
    def test_location_search(self):
        """Test location search"""
        params = {'q': 'Delhi'}
        
        response = self.client.get(self.location_search_url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('locations', response.data)
    
    def test_location_search_empty_query(self):
        """Test location search with empty query"""
        params = {'q': ''}
        
        response = self.client.get(self.location_search_url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_reverse_geocoding(self):
        """Test reverse geocoding"""
        params = {
            'lat': 28.7041,
            'lon': 77.1025
        }
        
        response = self.client.get(self.reverse_geocoding_url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('location', response.data)
        self.assertIn('coordinates', response.data)
    
    def test_reverse_geocoding_invalid_coordinates(self):
        """Test reverse geocoding with invalid coordinates"""
        params = {
            'lat': 999.0,  # Invalid latitude
            'lon': 999.0   # Invalid longitude
        }
        
        response = self.client.get(self.reverse_geocoding_url, params)
        
        # Should handle gracefully
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CropSearchAPITests(APITestCase):
    """Test crop search API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.crop_search_url = reverse('realtime-gov-crop_search-list')
    
    def test_crop_search(self):
        """Test crop search"""
        params = {
            'crop': 'wheat',
            'location': 'Delhi'
        }
        
        response = self.client.get(self.crop_search_url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('crop_info', response.data)
        self.assertIn('location', response.data)
    
    def test_crop_search_without_location(self):
        """Test crop search without location"""
        params = {'crop': 'wheat'}
        
        response = self.client.get(self.crop_search_url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class HealthCheckAPITests(APITestCase):
    """Test health check endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
    
    def test_health_check(self):
        """Test basic health check"""
        url = reverse('health')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content.decode(), 'OK')
    
    def test_simple_health_check(self):
        """Test simple health check"""
        url = reverse('simple_health')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('status', response.data)
    
    def test_readiness_check(self):
        """Test readiness check"""
        url = reverse('readiness_check')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('status', response.data)
    
    def test_liveness_check(self):
        """Test liveness check"""
        url = reverse('liveness_check')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('status', response.data)


class APIPerformanceTests(APITestCase):
    """Test API performance and response times"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
    
    def test_chatbot_response_time(self):
        """Test chatbot response time"""
        import time
        
        data = {
            'query': 'What crops should I grow?',
            'session_id': 'perf_test'
        }
        
        start_time = time.time()
        response = self.client.post(reverse('chatbot-list'), data, format='json')
        end_time = time.time()
        
        response_time = end_time - start_time
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response should be under 5 seconds
        self.assertLess(response_time, 5.0)
    
    def test_crop_recommendations_response_time(self):
        """Test crop recommendations response time"""
        import time
        
        params = {
            'location': 'Delhi',
            'latitude': 28.7041,
            'longitude': 77.1025
        }
        
        start_time = time.time()
        response = self.client.get(reverse('realtime-gov-crop_recommendations-list'), params)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response should be under 3 seconds
        self.assertLess(response_time, 3.0)
    
    def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        import threading
        import time
        
        results = []
        
        def make_request():
            data = {
                'query': f'Test query {threading.current_thread().ident}',
                'session_id': f'session_{threading.current_thread().ident}'
            }
            
            start_time = time.time()
            response = self.client.post(reverse('chatbot-list'), data, format='json')
            end_time = time.time()
            
            results.append({
                'status_code': response.status_code,
                'response_time': end_time - start_time
            })
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check all requests succeeded
        self.assertEqual(len(results), 5)
        for result in results:
            self.assertEqual(result['status_code'], status.HTTP_200_OK)
            self.assertLess(result['response_time'], 10.0)  # Should complete within 10 seconds

