#!/usr/bin/env python3
"""
Comprehensive Integration Tests
Tests integration between different components and services
"""

from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from unittest.mock import patch, Mock, MagicMock
import json
import time

from ..models import User, Crop, CropAdvisory, UserFeedback, ChatHistory, ChatSession
from ..services.realtime_government_ai import RealTimeGovernmentAI
from ..services.enhanced_government_api import EnhancedGovernmentAPI
from ..services.comprehensive_crop_recommendations import ComprehensiveCropRecommendations

User = get_user_model()


class ServiceIntegrationTests(TestCase):
    """Test integration between different services"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_ai_to_government_service_integration(self):
        """Test integration between AI and Government services"""
        # Test that AI service properly routes to government service
        ai_service = RealTimeGovernmentAI()
        
        # Mock government service
        with patch.object(ai_service, '_get_ultra_real_time_government_data') as mock_gov:
            mock_gov.return_value = {
                'crop_recommendations': [{'crop': 'Wheat', 'suitability': 'High'}],
                'weather': {'temperature': 25, 'condition': 'Sunny'},
                'market_prices': {'wheat': 2450}
            }
            
            result = ai_service.process_farming_query(
                'What crops should I grow in Delhi?',
                'en',
                'Delhi',
                28.7041,
                77.1025
            )
            
            self.assertIn('response', result)
            self.assertIn('data_source', result)
            self.assertIn('real_time_data', result)
            mock_gov.assert_called_once()
    
    def test_government_api_to_crop_service_integration(self):
        """Test integration between Government API and Crop service"""
        gov_api = EnhancedGovernmentAPI()
        crop_service = ComprehensiveCropRecommendations()
        
        # Test that government API can provide data to crop service
        location = 'Delhi'
        
        # Mock weather data
        with patch.object(gov_api, 'get_weather_data') as mock_weather:
            mock_weather.return_value = {
                'temperature': 25,
                'humidity': 60,
                'condition': 'Sunny',
                'location': location
            }
            
            weather_data = gov_api.get_weather_data(location)
            
            # Test crop service can use this weather data
            crop_recommendations = crop_service.get_crop_recommendations(
                location=location,
                latitude=28.7041,
                longitude=77.1025
            )
            
            self.assertIn('crop_recommendations', crop_recommendations)
            self.assertIn('weather', crop_recommendations)
            mock_weather.assert_called_once_with(location)
    
    def test_database_to_service_integration(self):
        """Test integration between database models and services"""
        # Create test data
        crop = Crop.objects.create(
            name='Wheat',
            description='Winter cereal crop',
            ideal_soil_type='Loamy',
            min_temperature_c=10.0,
            max_temperature_c=25.0,
            min_rainfall_mm_per_month=50.0,
            max_rainfall_mm_per_month=100.0,
            duration_days=150
        )
        
        advisory = CropAdvisory.objects.create(
            crop=crop,
            soil_type='Loamy',
            weather_condition='Normal',
            recommendation='Plant wheat in October'
        )
        
        # Test that services can access database data
        crop_service = ComprehensiveCropRecommendations()
        
        # Mock the service to use database data
        with patch.object(crop_service, '_load_crop_database') as mock_db:
            mock_db.return_value = {
                'wheat': {
                    'name_hindi': 'गेहूं',
                    'season': 'rabi',
                    'duration_days': 150,
                    'yield_per_hectare': 45,
                    'msp_per_quintal': 2125
                }
            }
            
            recommendations = crop_service.get_crop_recommendations('Delhi')
            
            self.assertIn('crop_recommendations', recommendations)
            mock_db.assert_called_once()


class APIToServiceIntegrationTests(TestCase):
    """Test integration between API endpoints and services"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
    
    def test_chatbot_api_to_ai_service_integration(self):
        """Test integration between chatbot API and AI service"""
        with patch('advisory.api.views.RealTimeGovernmentAI') as mock_ai:
            mock_instance = Mock()
            mock_instance.process_farming_query.return_value = {
                'response': 'Test response',
                'data_source': 'test_service',
                'confidence': 0.9,
                'timestamp': '2023-01-01T00:00:00Z'
            }
            mock_ai.return_value = mock_instance
            
            data = {
                'query': 'What crops should I grow?',
                'session_id': 'test_session'
            }
            
            response = self.client.post(reverse('chatbot-list'), data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['response'], 'Test response')
            mock_ai.assert_called_once()
    
    def test_crop_recommendations_api_to_service_integration(self):
        """Test integration between crop recommendations API and service"""
        with patch('advisory.api.views.ComprehensiveCropRecommendations') as mock_service:
            mock_instance = Mock()
            mock_instance.get_crop_recommendations.return_value = {
                'crop_recommendations': [
                    {'crop': 'Wheat', 'suitability': 'High'},
                    {'crop': 'Rice', 'suitability': 'Medium'}
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
            
            response = self.client.get(reverse('realtime-gov-crop_recommendations-list'), params)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data['crop_recommendations']), 2)
            mock_service.assert_called_once()
    
    def test_weather_api_to_service_integration(self):
        """Test integration between weather API and service"""
        with patch('advisory.api.views.EnhancedGovernmentAPI') as mock_service:
            mock_instance = Mock()
            mock_instance.get_weather_data.return_value = {
                'temperature': 25.0,
                'humidity': 60,
                'condition': 'Sunny',
                'location': 'Delhi',
                'timestamp': '2023-01-01T00:00:00Z'
            }
            mock_service.return_value = mock_instance
            
            params = {
                'location': 'Delhi',
                'latitude': 28.7041,
                'longitude': 77.1025
            }
            
            response = self.client.get(reverse('realtime-gov-weather-list'), params)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['weather']['temperature'], 25.0)
            mock_service.assert_called_once()


class DatabaseIntegrationTests(TransactionTestCase):
    """Test database integration and transactions"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_user_session_to_chat_history_integration(self):
        """Test integration between UserSession and ChatHistory models"""
        # Create a chat session
        session = ChatSession.objects.create(
            user_id='testuser',
            session_id='test_session_123',
            conversation_context={'location': 'Delhi'},
            preferred_language='en',
            location_name='Delhi',
            latitude=28.7041,
            longitude=77.1025
        )
        
        # Create chat history entries
        user_message = ChatHistory.objects.create(
            user_id='testuser',
            session_id='test_session_123',
            message_type='user',
            message_content='What crops should I grow?',
            detected_language='en',
            response_language='en',
            has_location=True,
            latitude=28.7041,
            longitude=77.1025
        )
        
        assistant_message = ChatHistory.objects.create(
            user_id='testuser',
            session_id='test_session_123',
            message_type='assistant',
            message_content='You should grow wheat and rice.',
            detected_language='en',
            response_language='en',
            response_source='ai_assistant',
            response_type='agricultural'
        )
        
        # Test that session and chat history are properly linked
        self.assertEqual(session.session_id, user_message.session_id)
        self.assertEqual(session.session_id, assistant_message.session_id)
        
        # Test session statistics update
        session.total_messages = 2
        session.user_messages = 1
        session.assistant_messages = 1
        session.save()
        
        self.assertEqual(session.total_messages, 2)
        self.assertEqual(session.user_messages, 1)
        self.assertEqual(session.assistant_messages, 1)
    
    def test_crop_to_advisory_integration(self):
        """Test integration between Crop and CropAdvisory models"""
        # Create a crop
        crop = Crop.objects.create(
            name='Wheat',
            description='Winter cereal crop',
            ideal_soil_type='Loamy',
            min_temperature_c=10.0,
            max_temperature_c=25.0,
            min_rainfall_mm_per_month=50.0,
            max_rainfall_mm_per_month=100.0,
            duration_days=150
        )
        
        # Create multiple advisories for the crop
        advisory1 = CropAdvisory.objects.create(
            crop=crop,
            soil_type='Loamy',
            weather_condition='Normal',
            recommendation='Plant wheat in October for best yield'
        )
        
        advisory2 = CropAdvisory.objects.create(
            crop=crop,
            soil_type='Clayey',
            weather_condition='Dry',
            recommendation='Ensure proper irrigation for wheat cultivation'
        )
        
        # Test that advisories are properly linked to crop
        self.assertEqual(advisory1.crop, crop)
        self.assertEqual(advisory2.crop, crop)
        
        # Test reverse relationship
        advisories = crop.advisories.all()
        self.assertEqual(advisories.count(), 2)
        self.assertIn(advisory1, advisories)
        self.assertIn(advisory2, advisories)
    
    def test_user_feedback_integration(self):
        """Test integration of user feedback with other models"""
        # Create a chat session
        session = ChatSession.objects.create(
            user_id='testuser',
            session_id='feedback_session_123'
        )
        
        # Create chat history
        chat_history = ChatHistory.objects.create(
            user_id='testuser',
            session_id='feedback_session_123',
            message_type='assistant',
            message_content='You should grow wheat.',
            response_source='ai_assistant',
            response_type='agricultural'
        )
        
        # Create user feedback
        feedback = UserFeedback.objects.create(
            user_id='testuser',
            session_id='feedback_session_123',
            prediction_type='crop_recommendation',
            input_data={'location': 'Delhi', 'soil_type': 'Loamy'},
            system_prediction={'crop': 'Wheat', 'confidence': 0.8},
            actual_result={'crop': 'Rice', 'yield': 'Good'},
            feedback_rating=4,
            feedback_text='Good recommendation but I chose rice instead',
            latitude=28.7041,
            longitude=77.1025
        )
        
        # Test that all models are properly linked
        self.assertEqual(session.user_id, feedback.user_id)
        self.assertEqual(session.session_id, feedback.session_id)
        self.assertEqual(chat_history.user_id, feedback.user_id)
        self.assertEqual(chat_history.session_id, feedback.session_id)


class ExternalServiceIntegrationTests(TestCase):
    """Test integration with external services"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
    
    @patch('requests.get')
    def test_weather_api_integration(self, mock_get):
        """Test integration with external weather API"""
        # Mock external API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'main': {'temp': 25.0, 'humidity': 60},
            'weather': [{'description': 'sunny'}],
            'name': 'Delhi'
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Test through our API
        params = {
            'location': 'Delhi',
            'latitude': 28.7041,
            'longitude': 77.1025
        }
        
        response = self.client.get(reverse('realtime-gov-weather-list'), params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('weather', response.data)
        mock_get.assert_called()
    
    @patch('requests.get')
    def test_market_prices_api_integration(self, mock_get):
        """Test integration with external market prices API"""
        # Mock external API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': [
                {'commodity': 'Wheat', 'price': 2450, 'unit': 'Quintal'},
                {'commodity': 'Rice', 'price': 3200, 'unit': 'Quintal'}
            ]
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Test through our API
        params = {
            'location': 'Delhi',
            'latitude': 28.7041,
            'longitude': 77.1025
        }
        
        response = self.client.get(reverse('realtime-gov-market_prices-list'), params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('market_prices', response.data)
        mock_get.assert_called()
    
    def test_ollama_integration(self):
        """Test integration with Ollama AI service"""
        with patch('advisory.services.ollama_integration.OllamaIntegration') as mock_ollama:
            mock_instance = Mock()
            mock_instance.generate_response.return_value = {
                'response': 'This is a test response from Ollama',
                'model': 'llama3',
                'timestamp': '2023-01-01T00:00:00Z'
            }
            mock_ollama.return_value = mock_instance
            
            # Test through chatbot API
            data = {
                'query': 'What is artificial intelligence?',
                'session_id': 'ollama_test'
            }
            
            response = self.client.post(reverse('chatbot-list'), data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('response', response.data)


class PerformanceIntegrationTests(TestCase):
    """Test performance integration between components"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
    
    def test_caching_integration(self):
        """Test caching integration across services"""
        # First request - should hit external API
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {'main': {'temp': 25.0}}
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            params = {
                'location': 'Delhi',
                'latitude': 28.7041,
                'longitude': 77.1025
            }
            
            response1 = self.client.get(reverse('realtime-gov-weather-list'), params)
            self.assertEqual(response1.status_code, status.HTTP_200_OK)
            mock_get.assert_called()
        
        # Second request - should use cache
        with patch('requests.get') as mock_get:
            response2 = self.client.get(reverse('realtime-gov-weather-list'), params)
            self.assertEqual(response2.status_code, status.HTTP_200_OK)
            # Should not call external API if cached
            mock_get.assert_not_called()
    
    def test_database_performance_integration(self):
        """Test database performance with multiple operations"""
        import time
        
        start_time = time.time()
        
        # Create multiple users and sessions
        users = []
        sessions = []
        
        for i in range(10):
            user = User.objects.create_user(
                username=f'testuser{i}',
                email=f'test{i}@example.com',
                password='testpass123'
            )
            users.append(user)
            
            session = ChatSession.objects.create(
                user_id=f'testuser{i}',
                session_id=f'session_{i}',
                conversation_context={'test': 'data'}
            )
            sessions.append(session)
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Should create 10 users and sessions quickly
        self.assertLess(creation_time, 2.0)  # Under 2 seconds
        self.assertEqual(User.objects.count(), 10)
        self.assertEqual(ChatSession.objects.count(), 10)
        
        # Test query performance
        start_time = time.time()
        
        # Query all sessions for a specific user
        user_sessions = ChatSession.objects.filter(user_id='testuser0')
        
        end_time = time.time()
        query_time = end_time - start_time
        
        # Should query quickly
        self.assertLess(query_time, 0.1)  # Under 100ms
        self.assertEqual(user_sessions.count(), 1)
    
    def test_api_response_time_integration(self):
        """Test API response time integration"""
        import time
        
        # Test multiple API calls
        endpoints = [
            ('chatbot-list', 'POST', {'query': 'Test query', 'session_id': 'test'}),
            ('realtime-gov-crop_recommendations-list', 'GET', {'location': 'Delhi'}),
            ('realtime-gov-weather-list', 'GET', {'location': 'Delhi'}),
            ('realtime-gov-market_prices-list', 'GET', {'location': 'Delhi'}),
        ]
        
        total_time = 0
        
        for endpoint, method, data in endpoints:
            start_time = time.time()
            
            if method == 'POST':
                response = self.client.post(reverse(endpoint), data, format='json')
            else:
                response = self.client.get(reverse(endpoint), data)
            
            end_time = time.time()
            response_time = end_time - start_time
            total_time += response_time
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            # Each endpoint should respond quickly
            self.assertLess(response_time, 3.0)
        
        # Total time for all endpoints should be reasonable
        self.assertLess(total_time, 10.0)  # Under 10 seconds total


class ErrorHandlingIntegrationTests(TestCase):
    """Test error handling integration across components"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
    
    def test_external_api_failure_integration(self):
        """Test handling of external API failures"""
        with patch('requests.get') as mock_get:
            # Mock API failure
            mock_get.side_effect = Exception('API Error')
            
            params = {
                'location': 'Delhi',
                'latitude': 28.7041,
                'longitude': 77.1025
            }
            
            response = self.client.get(reverse('realtime-gov-weather-list'), params)
            
            # Should still return a response (fallback data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('weather', response.data)
    
    def test_database_error_integration(self):
        """Test handling of database errors"""
        # Test with invalid data that might cause database errors
        data = {
            'query': 'Test query',
            'session_id': 'test_session'
        }
        
        # This should not cause database errors
        response = self.client.post(reverse('chatbot-list'), data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_service_error_propagation(self):
        """Test that service errors are properly handled"""
        with patch('advisory.services.realtime_government_ai.RealTimeGovernmentAI') as mock_ai:
            # Mock service error
            mock_instance = Mock()
            mock_instance.process_farming_query.side_effect = Exception('Service Error')
            mock_ai.return_value = mock_instance
            
            data = {
                'query': 'What crops should I grow?',
                'session_id': 'error_test'
            }
            
            response = self.client.post(reverse('chatbot-list'), data, format='json')
            
            # Should handle error gracefully
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('response', response.data)
            # Should have error fallback
            self.assertIn(response.data['data_source'], ['error_fallback', 'fallback'])

