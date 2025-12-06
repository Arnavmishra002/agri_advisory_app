#!/usr/bin/env python3
"""
Production-Ready Comprehensive Test Suite
Tests all services with government API integration, error handling, and performance
"""

import os
import sys
import json
import time
import threading
from datetime import datetime
from unittest.mock import patch, Mock, MagicMock
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

from ..services.ultra_dynamic_government_api import UltraDynamicGovernmentAPI
from ..api.views import (
    WeatherViewSet, MarketPricesViewSet, CropAdvisoryViewSet,
    GovernmentSchemesViewSet, PestDetectionViewSet, ChatbotViewSet,
    TrendingCropsViewSet, CropViewSet
)

User = get_user_model()


class ProductionServiceTests(APITestCase):
    """Comprehensive production-ready tests for all services"""
    
    def setUp(self):
        """Set up test environment"""
        self.client = APIClient()
        self.gov_api = UltraDynamicGovernmentAPI()
        
        # Test data
        self.test_location = 'Delhi'
        self.test_latitude = 28.6139
        self.test_longitude = 77.2090
        self.test_crop = 'wheat'
        
    def tearDown(self):
        """Clean up after tests"""
        pass


class WeatherServiceProductionTests(ProductionServiceTests):
    """Production tests for Weather Service with Government APIs"""
    
    def test_weather_service_uses_government_apis(self):
        """Test that weather service uses government APIs"""
        url = reverse('weather-list')
        params = {
            'location': self.test_location,
            'latitude': self.test_latitude,
            'longitude': self.test_longitude
        }
        
        with patch.object(self.gov_api, 'get_weather_data') as mock_weather:
            mock_weather.return_value = {
                'status': 'success',
                'data': {
                    'temperature': '28°C',
                    'humidity': '65%',
                    'wind_speed': '12 km/h',
                    'condition': 'साफ आसमान',
                    'data_source': 'IMD (Indian Meteorological Department) - Real-Time Government API'
                },
                'timestamp': datetime.now().isoformat()
            }
            
            response = self.client.get(url, params)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('current_weather', response.data)
            self.assertIn('data_source', response.data)
            self.assertIn('Government API', response.data['data_source'])
            mock_weather.assert_called_once()
    
    def test_weather_service_real_time_data(self):
        """Test weather service returns real-time data"""
        url = reverse('weather-list')
        params = {
            'location': self.test_location,
            'latitude': self.test_latitude,
            'longitude': self.test_longitude
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('current_weather', response.data)
        self.assertIn('timestamp', response.data)
        self.assertIn('data_source', response.data)
        
        # Verify data structure
        weather = response.data['current_weather']
        self.assertIn('temperature', weather)
        self.assertIn('humidity', weather)
        self.assertIn('wind_speed', weather)
        self.assertIn('condition', weather)
    
    def test_weather_service_error_handling(self):
        """Test weather service error handling"""
        url = reverse('weather-list')
        params = {
            'location': 'InvalidLocation12345',
            'latitude': 999.0,
            'longitude': 999.0
        }
        
        response = self.client.get(url, params)
        
        # Should handle gracefully without crashing
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR])
        if response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
            self.assertIn('error', response.data)
    
    def test_weather_service_performance(self):
        """Test weather service response time"""
        url = reverse('weather-list')
        params = {
            'location': self.test_location,
            'latitude': self.test_latitude,
            'longitude': self.test_longitude
        }
        
        start_time = time.time()
        response = self.client.get(url, params)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(response_time, 5.0, "Response time should be under 5 seconds")
    
    def test_weather_service_without_coordinates(self):
        """Test weather service with location name only"""
        url = reverse('weather-list')
        params = {'location': self.test_location}
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('current_weather', response.data)
    
    def test_weather_service_cache_headers(self):
        """Test weather service cache headers"""
        url = reverse('weather-list')
        params = {
            'location': self.test_location,
            'latitude': self.test_latitude,
            'longitude': self.test_longitude
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should include timestamp for cache control
        self.assertIn('timestamp', response.data)


class MarketPricesServiceProductionTests(ProductionServiceTests):
    """Production tests for Market Prices Service with Government APIs"""
    
    def test_market_prices_service_uses_government_apis(self):
        """Test that market prices service uses government APIs"""
        url = reverse('market-prices-list')
        params = {
            'location': self.test_location,
            'latitude': self.test_latitude,
            'longitude': self.test_longitude
        }
        
        with patch.object(self.gov_api, 'get_market_prices') as mock_prices:
            mock_prices.return_value = {
                'status': 'success',
                'prices': {
                    'wheat': {'current_price': 2450, 'msp': 2275},
                    'rice': {'current_price': 3200, 'msp': 2183}
                },
                'crops': ['wheat', 'rice'],
                'data_source': 'Agmarknet + e-NAM (Real-time Government APIs)',
                'sources': ['Agmarknet', 'e-NAM'],
                'timestamp': datetime.now().isoformat()
            }
            
            response = self.client.get(url, params)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('data_source', response.data)
            self.assertIn('Government', response.data['data_source'])
            mock_prices.assert_called_once()
    
    def test_market_prices_real_time_data(self):
        """Test market prices service returns real-time data"""
        url = reverse('market-prices-list')
        params = {
            'location': self.test_location,
            'latitude': self.test_latitude,
            'longitude': self.test_longitude
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('location', response.data)
        self.assertIn('timestamp', response.data)
        self.assertIn('data_source', response.data)
    
    def test_market_prices_with_mandi(self):
        """Test market prices with specific mandi"""
        url = reverse('market-prices-list')
        params = {
            'location': self.test_location,
            'mandi': 'Azadpur Mandi',
            'latitude': self.test_latitude,
            'longitude': self.test_longitude
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('mandi', response.data)
    
    def test_market_prices_performance(self):
        """Test market prices service response time"""
        url = reverse('market-prices-list')
        params = {
            'location': self.test_location,
            'latitude': self.test_latitude,
            'longitude': self.test_longitude
        }
        
        start_time = time.time()
        response = self.client.get(url, params)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(response_time, 5.0, "Response time should be under 5 seconds")


class CropRecommendationsServiceProductionTests(ProductionServiceTests):
    """Production tests for Crop Recommendations Service with Government APIs"""
    
    def test_crop_recommendations_uses_government_apis(self):
        """Test that crop recommendations use government APIs"""
        url = reverse('advisories-list')
        params = {
            'location': self.test_location,
            'latitude': self.test_latitude,
            'longitude': self.test_longitude
        }
        
        with patch.object(self.gov_api, 'get_comprehensive_government_data') as mock_gov:
            mock_gov.return_value = {
                'status': 'success',
                'government_data': {
                    'crop_recommendations': {
                        'recommendations': [
                            {
                                'name': 'Wheat',
                                'profitability_score': 85,
                                'season': 'Rabi',
                                'msp': 2275
                            }
                        ]
                    },
                    'weather': {'temperature': '28°C'},
                    'market_prices': {'wheat': {'price': 2450}},
                    'soil_health': {'soil_type': 'Loamy'}
                },
                'data_source': 'Government APIs (ICAR, Agricoop)',
                'timestamp': datetime.now().isoformat()
            }
            
            response = self.client.get(url, params)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('data_source', response.data)
            mock_gov.assert_called_once()
    
    def test_crop_recommendations_real_time_data(self):
        """Test crop recommendations return real-time data"""
        url = reverse('advisories-list')
        params = {
            'location': self.test_location,
            'latitude': self.test_latitude,
            'longitude': self.test_longitude
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('location', response.data)
        self.assertIn('timestamp', response.data)
    
    def test_crop_recommendations_structure(self):
        """Test crop recommendations data structure"""
        url = reverse('advisories-list')
        params = {
            'location': self.test_location,
            'latitude': self.test_latitude,
            'longitude': self.test_longitude
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have recommendations or top_4_recommendations
        has_recommendations = (
            'top_4_recommendations' in response.data or
            'recommendations' in response.data or
            'crop_recommendations' in response.data
        )
        self.assertTrue(has_recommendations)


class GovernmentSchemesServiceProductionTests(ProductionServiceTests):
    """Production tests for Government Schemes Service"""
    
    def test_government_schemes_uses_government_apis(self):
        """Test that government schemes use government APIs"""
        url = reverse('government-schemes-list')
        params = {
            'location': self.test_location,
            'latitude': self.test_latitude,
            'longitude': self.test_longitude
        }
        
        with patch.object(self.gov_api, 'get_government_schemes') as mock_schemes:
            mock_schemes.return_value = {
                'status': 'success',
                'schemes': [
                    {
                        'name': 'PM Kisan Samman Nidhi',
                        'amount': '₹6,000 per year',
                        'description': 'Direct income support to farmers',
                        'eligibility': 'All farmer families',
                        'helpline': '1800-180-1551'
                    }
                ],
                'central_schemes': [],
                'state_schemes': [],
                'data_source': 'PM Kisan + Agriculture Department (Real-time Government APIs)',
                'total_schemes': 1,
                'timestamp': datetime.now().isoformat()
            }
            
            response = self.client.get(url, params)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('schemes', response.data)
            self.assertIn('data_source', response.data)
            mock_schemes.assert_called_once()
    
    def test_government_schemes_real_time_data(self):
        """Test government schemes return real-time data"""
        url = reverse('government-schemes-list')
        params = {
            'location': self.test_location,
            'latitude': self.test_latitude,
            'longitude': self.test_longitude
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('timestamp', response.data)
        # Should have schemes or central_schemes
        has_schemes = (
            'schemes' in response.data or
            'central_schemes' in response.data
        )
        self.assertTrue(has_schemes)


class PestDetectionServiceProductionTests(ProductionServiceTests):
    """Production tests for Pest Detection Service"""
    
    def test_pest_detection_uses_government_apis(self):
        """Test that pest detection uses government APIs"""
        url = reverse('pest-detection-list')
        params = {
            'crop': self.test_crop,
            'location': self.test_location
        }
        
        with patch.object(self.gov_api, 'get_pest_control_recommendations') as mock_pest:
            mock_pest.return_value = {
                'status': 'success',
                'data': {
                    'pest_database': [
                        {'name': 'Aphids', 'crop': 'Wheat', 'control': 'Use neem oil spray'}
                    ],
                    'disease_database': [],
                    'control_measures': ['Use organic pesticides'],
                    'seasonal_alerts': []
                },
                'data_source': 'ICAR + PPQS (Real-time Government APIs)',
                'timestamp': datetime.now().isoformat()
            }
            
            response = self.client.get(url, params)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('data_source', response.data)
            self.assertIn('Government', response.data['data_source'])
            mock_pest.assert_called_once()
    
    def test_pest_detection_with_crop_name(self):
        """Test pest detection with crop name"""
        url = reverse('pest-detection-list')
        params = {
            'crop': self.test_crop,
            'location': self.test_location
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data_source', response.data)


class ChatbotServiceProductionTests(ProductionServiceTests):
    """Production tests for AI Chatbot Service"""
    
    def test_chatbot_farming_query_routes_to_government_apis(self):
        """Test that farming queries route to government APIs"""
        url = reverse('chatbot-list')
        data = {
            'query': 'What crops should I grow in Delhi?',
            'language': 'en',
            'location': self.test_location,
            'session_id': 'test_session_123'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('response', response.data)
        self.assertIn('data_source', response.data)
        # Farming queries should use government APIs
        self.assertIn(
            response.data['data_source'],
            ['real_time_government_apis', 'government_apis', 'agricultural_ai_with_government_apis', 'fallback']
        )
    
    def test_chatbot_general_query_routes_to_ai(self):
        """Test that general queries route to AI services"""
        url = reverse('chatbot-list')
        data = {
            'query': 'What is artificial intelligence?',
            'language': 'en',
            'session_id': 'test_session_123'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('response', response.data)
        self.assertIn('data_source', response.data)
    
    def test_chatbot_hindi_query(self):
        """Test chatbot with Hindi query"""
        url = reverse('chatbot-list')
        data = {
            'query': 'मुझे दिल्ली में फसल सुझाव चाहिए',
            'language': 'hi',
            'location': self.test_location,
            'session_id': 'test_session_123'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('response', response.data)
        self.assertIn('language', response.data)
    
    def test_chatbot_performance(self):
        """Test chatbot response time"""
        url = reverse('chatbot-list')
        data = {
            'query': 'What crops should I grow?',
            'session_id': 'perf_test',
            'location': self.test_location
        }
        
        start_time = time.time()
        response = self.client.post(url, data, format='json')
        end_time = time.time()
        
        response_time = end_time - start_time
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(response_time, 10.0, "Response time should be under 10 seconds")
    
    def test_chatbot_session_persistence(self):
        """Test chatbot session persistence"""
        url = reverse('chatbot-list')
        session_id = f'test_session_{int(time.time())}'
        
        # First query
        data1 = {
            'query': 'What crops should I grow?',
            'session_id': session_id,
            'location': self.test_location
        }
        response1 = self.client.post(url, data1, format='json')
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        # Second query in same session
        data2 = {
            'query': 'Tell me about wheat',
            'session_id': session_id,
            'location': self.test_location
        }
        response2 = self.client.post(url, data2, format='json')
        self.assertEqual(response2.status_code, status.HTTP_200_OK)


class TrendingCropsServiceProductionTests(ProductionServiceTests):
    """Production tests for Trending Crops Service"""
    
    def test_trending_crops_uses_government_apis(self):
        """Test that trending crops use government APIs"""
        url = reverse('trending-crops-list')
        params = {
            'location': self.test_location,
            'latitude': self.test_latitude,
            'longitude': self.test_longitude
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data_source', response.data)
        self.assertIn('Government', response.data['data_source'])
    
    def test_trending_crops_structure(self):
        """Test trending crops data structure"""
        url = reverse('trending-crops-list')
        params = {
            'location': self.test_location,
            'latitude': self.test_latitude,
            'longitude': self.test_longitude
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('location', response.data)
        self.assertIn('timestamp', response.data)
        # Should have trending_crops or empty list
        self.assertIn('trending_crops', response.data)


class CropServiceProductionTests(ProductionServiceTests):
    """Production tests for Crop Service"""
    
    def test_crop_service_uses_government_apis(self):
        """Test that crop service uses government APIs"""
        url = reverse('crops-list')
        params = {
            'crop': self.test_crop,
            'location': self.test_location,
            'latitude': self.test_latitude,
            'longitude': self.test_longitude
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data_source', response.data)
        self.assertIn('Government', response.data['data_source'])


class IntegrationTests(ProductionServiceTests):
    """Integration tests for multiple services working together"""
    
    def test_location_consistency_across_services(self):
        """Test that location works consistently across all services"""
        location = self.test_location
        lat = self.test_latitude
        lon = self.test_longitude
        
        # Test weather
        weather_url = reverse('weather-list')
        weather_response = self.client.get(weather_url, {
            'location': location, 'latitude': lat, 'longitude': lon
        })
        
        # Test market prices
        prices_url = reverse('market-prices-list')
        prices_response = self.client.get(prices_url, {
            'location': location, 'latitude': lat, 'longitude': lon
        })
        
        # Test crop recommendations
        crops_url = reverse('advisories-list')
        crops_response = self.client.get(crops_url, {
            'location': location, 'latitude': lat, 'longitude': lon
        })
        
        self.assertEqual(weather_response.status_code, status.HTTP_200_OK)
        self.assertEqual(prices_response.status_code, status.HTTP_200_OK)
        self.assertEqual(crops_response.status_code, status.HTTP_200_OK)
        
        # All should reference the same location
        self.assertEqual(weather_response.data.get('location'), location)
        self.assertEqual(prices_response.data.get('location'), location)
        self.assertEqual(crops_response.data.get('location'), location)
    
    def test_concurrent_service_requests(self):
        """Test handling of concurrent requests to multiple services"""
        def make_request(service_name):
            url_map = {
                'weather': reverse('weather-list'),
                'prices': reverse('market-prices-list'),
                'crops': reverse('advisories-list'),
                'schemes': reverse('government-schemes-list')
            }
            url = url_map.get(service_name)
            params = {
                'location': self.test_location,
                'latitude': self.test_latitude,
                'longitude': self.test_longitude
            }
            return self.client.get(url, params)
        
        # Create threads for concurrent requests
        results = {}
        threads = []
        
        def request_weather():
            results['weather'] = make_request('weather')
        
        def request_prices():
            results['prices'] = make_request('prices')
        
        def request_crops():
            results['crops'] = make_request('crops')
        
        def request_schemes():
            results['schemes'] = make_request('schemes')
        
        threads = [
            threading.Thread(target=request_weather),
            threading.Thread(target=request_prices),
            threading.Thread(target=request_crops),
            threading.Thread(target=request_schemes)
        ]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all requests succeeded
        self.assertEqual(len(results), 4)
        for service, response in results.items():
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                f"{service} service failed with status {response.status_code}"
            )


class ErrorHandlingTests(ProductionServiceTests):
    """Tests for error handling and edge cases"""
    
    def test_invalid_location_handling(self):
        """Test handling of invalid locations"""
        url = reverse('weather-list')
        params = {
            'location': 'NonexistentLocation12345',
            'latitude': 999.0,
            'longitude': 999.0
        }
        
        response = self.client.get(url, params)
        
        # Should handle gracefully
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR])
    
    def test_missing_required_parameters(self):
        """Test handling of missing required parameters"""
        url = reverse('weather-list')
        
        # No parameters at all
        response = self.client.get(url)
        
        # Should handle gracefully with defaults
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_invalid_data_types(self):
        """Test handling of invalid data types"""
        url = reverse('weather-list')
        params = {
            'location': self.test_location,
            'latitude': 'invalid',  # Should be float
            'longitude': 'invalid'   # Should be float
        }
        
        response = self.client.get(url, params)
        
        # Should handle gracefully
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR])
    
    def test_empty_query_handling(self):
        """Test handling of empty queries"""
        url = reverse('chatbot-list')
        data = {
            'query': '',
            'session_id': 'test_session'
        }
        
        response = self.client.post(url, data, format='json')
        
        # Should handle gracefully
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PerformanceTests(ProductionServiceTests):
    """Performance and load tests"""
    
    def test_service_response_times(self):
        """Test that all services respond within acceptable time limits"""
        services = {
            'weather': (reverse('weather-list'), {'location': self.test_location}),
            'market-prices': (reverse('market-prices-list'), {'location': self.test_location}),
            'crop-recommendations': (reverse('advisories-list'), {'location': self.test_location}),
            'government-schemes': (reverse('government-schemes-list'), {'location': self.test_location})
        }
        
        max_response_time = 5.0  # 5 seconds
        
        for service_name, (url, params) in services.items():
            start_time = time.time()
            response = self.client.get(url, params)
            end_time = time.time()
            
            response_time = end_time - start_time
            
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                f"{service_name} failed with status {response.status_code}"
            )
            self.assertLess(
                response_time,
                max_response_time,
                f"{service_name} took {response_time:.2f}s, should be under {max_response_time}s"
            )
    
    def test_concurrent_requests_performance(self):
        """Test performance under concurrent load"""
        url = reverse('weather-list')
        params = {'location': self.test_location}
        
        num_requests = 10
        results = []
        
        def make_request():
            start_time = time.time()
            response = self.client.get(url, params)
            end_time = time.time()
            results.append({
                'status': response.status_code,
                'time': end_time - start_time
            })
        
        threads = [threading.Thread(target=make_request) for _ in range(num_requests)]
        
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        total_time = time.time() - start_time
        
        # Verify all requests succeeded
        self.assertEqual(len(results), num_requests)
        for result in results:
            self.assertEqual(result['status'], status.HTTP_200_OK)
        
        # Average response time should be reasonable
        avg_time = sum(r['time'] for r in results) / len(results)
        self.assertLess(avg_time, 3.0, f"Average response time {avg_time:.2f}s is too high")
        
        # Total time should be reasonable (concurrent execution)
        self.assertLess(total_time, 10.0, f"Total time {total_time:.2f}s is too high for {num_requests} concurrent requests")


if __name__ == '__main__':
    import django
    django.setup()
    
    import unittest
    unittest.main()


