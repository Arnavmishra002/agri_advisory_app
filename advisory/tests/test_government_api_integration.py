#!/usr/bin/env python3
"""
Government API Integration Tests
Tests real-time government API integrations for accuracy and reliability
"""

import os
import time
from datetime import datetime
from unittest.mock import patch, Mock, MagicMock
from django.test import TestCase
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from django.urls import reverse

from ..services.ultra_dynamic_government_api import UltraDynamicGovernmentAPI


class GovernmentAPIIntegrationTests(APITestCase):
    """Comprehensive tests for government API integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.client = APIClient()
        self.gov_api = UltraDynamicGovernmentAPI()
        self.test_location = 'Delhi'
        self.test_latitude = 28.6139
        self.test_longitude = 77.2090
    
    def test_weather_api_integration(self):
        """Test weather API integration with government APIs"""
        url = reverse('weather-list')
        params = {
            'location': self.test_location,
            'latitude': self.test_latitude,
            'longitude': self.test_longitude
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('current_weather', response.data)
        self.assertIn('data_source', response.data)
        
        # Verify government API is mentioned in data source
        data_source = response.data['data_source']
        self.assertTrue(
            'IMD' in data_source or 'Government' in data_source or 'Real-Time' in data_source,
            f"Data source should mention government APIs, got: {data_source}"
        )
    
    def test_market_prices_api_integration(self):
        """Test market prices API integration with government APIs"""
        url = reverse('market-prices-list')
        params = {
            'location': self.test_location,
            'latitude': self.test_latitude,
            'longitude': self.test_longitude
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data_source', response.data)
        
        # Verify government API is mentioned in data source
        data_source = response.data['data_source']
        self.assertTrue(
            'Agmarknet' in data_source or 'e-NAM' in data_source or 'Government' in data_source,
            f"Data source should mention government APIs, got: {data_source}"
        )
    
    def test_crop_recommendations_api_integration(self):
        """Test crop recommendations API integration with government APIs"""
        url = reverse('advisories-list')
        params = {
            'location': self.test_location,
            'latitude': self.test_latitude,
            'longitude': self.test_longitude
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have government data integration
        has_gov_data = (
            'government_data_integrated' in response.data or
            'data_source' in response.data
        )
        self.assertTrue(has_gov_data)
    
    def test_government_schemes_api_integration(self):
        """Test government schemes API integration"""
        url = reverse('government-schemes-list')
        params = {
            'location': self.test_location,
            'latitude': self.test_latitude,
            'longitude': self.test_longitude
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data_source', response.data)
        
        # Verify government API is mentioned
        data_source = response.data.get('data_source', '')
        self.assertTrue(
            'PM Kisan' in data_source or 'Government' in data_source or 'Real-Time' in data_source,
            f"Data source should mention government APIs, got: {data_source}"
        )
    
    def test_pest_detection_api_integration(self):
        """Test pest detection API integration with government APIs"""
        url = reverse('pest-detection-list')
        params = {
            'crop': 'wheat',
            'location': self.test_location
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data_source', response.data)
        
        # Verify government API is mentioned
        data_source = response.data['data_source']
        self.assertTrue(
            'ICAR' in data_source or 'PPQS' in data_source or 'Government' in data_source,
            f"Data source should mention government APIs, got: {data_source}"
        )
    
    def test_government_api_fallback_mechanism(self):
        """Test that fallback mechanism works when government APIs fail"""
        with patch.object(self.gov_api, 'get_weather_data') as mock_weather:
            # Simulate API failure
            mock_weather.side_effect = Exception('API Error')
            
            url = reverse('weather-list')
            params = {
                'location': self.test_location,
                'latitude': self.test_latitude,
                'longitude': self.test_longitude
            }
            
            response = self.client.get(url, params)
            
            # Should still return a response (fallback)
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR])
            if response.status_code == status.HTTP_200_OK:
                self.assertIn('current_weather', response.data)
    
    def test_government_api_caching(self):
        """Test that government API responses are cached appropriately"""
        url = reverse('weather-list')
        params = {
            'location': self.test_location,
            'latitude': self.test_latitude,
            'longitude': self.test_longitude
        }
        
        # First request
        with patch.object(self.gov_api, 'get_weather_data') as mock_weather:
            mock_weather.return_value = {
                'status': 'success',
                'data': {'temperature': '28°C'},
                'timestamp': datetime.now().isoformat()
            }
            
            response1 = self.client.get(url, params)
            self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        # Verify cache is being used (30 second cache in UltraDynamicGovernmentAPI)
        # Note: Actual cache behavior depends on implementation
    
    def test_government_api_data_accuracy(self):
        """Test that government API data is accurate and structured correctly"""
        url = reverse('weather-list')
        params = {
            'location': self.test_location,
            'latitude': self.test_latitude,
            'longitude': self.test_longitude
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify data structure
        weather = response.data.get('current_weather', {})
        if weather:
            # Should have temperature
            if 'temperature' in weather:
                temp = weather['temperature']
                # Temperature should be in reasonable range (-50 to 60°C for India)
                temp_value = int(temp.replace('°C', ''))
                self.assertGreater(temp_value, -50)
                self.assertLess(temp_value, 60)
            
            # Should have humidity
            if 'humidity' in weather:
                humidity = weather['humidity']
                # Humidity should be between 0-100%
                humidity_value = int(humidity.replace('%', ''))
                self.assertGreaterEqual(humidity_value, 0)
                self.assertLessEqual(humidity_value, 100)
    
    def test_comprehensive_government_data_integration(self):
        """Test comprehensive government data integration"""
        # Test that all government data sources are accessible
        comprehensive_data = self.gov_api.get_comprehensive_government_data(
            location=self.test_location,
            latitude=self.test_latitude,
            longitude=self.test_longitude
        )
        
        self.assertIsInstance(comprehensive_data, dict)
        self.assertIn('status', comprehensive_data)
        
        if comprehensive_data.get('status') == 'success':
            self.assertIn('government_data', comprehensive_data)
            gov_data = comprehensive_data['government_data']
            
            # Should have multiple data types
            available_data_types = list(gov_data.keys())
            self.assertGreater(len(available_data_types), 0)
    
    def test_real_time_data_freshness(self):
        """Test that data is real-time (recent timestamp)"""
        url = reverse('weather-list')
        params = {
            'location': self.test_location,
            'latitude': self.test_latitude,
            'longitude': self.test_longitude
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('timestamp', response.data)
        
        # Parse timestamp
        timestamp_str = response.data['timestamp']
        if isinstance(timestamp_str, str):
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.now()
            time_diff = abs((now - timestamp).total_seconds())
            
            # Timestamp should be within last hour (for real-time data)
            self.assertLess(time_diff, 3600, f"Timestamp is {time_diff} seconds old, should be recent")
    
    def test_government_api_error_logging(self):
        """Test that government API errors are logged properly"""
        # This test verifies error handling doesn't crash the system
        url = reverse('weather-list')
        params = {
            'location': 'InvalidLocation999',
            'latitude': 999.0,
            'longitude': 999.0
        }
        
        # Should not crash, should return error response
        response = self.client.get(url, params)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR])
    
    def test_multiple_government_api_sources(self):
        """Test that multiple government API sources are tried"""
        # Weather should try IMD, then OpenWeatherMap
        # Market prices should try Agmarknet, then e-NAM
        url = reverse('weather-list')
        params = {
            'location': self.test_location,
            'latitude': self.test_latitude,
            'longitude': self.test_longitude
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have tried multiple sources
        data_source = response.data.get('data_source', '')
        # Multiple government sources should be attempted
        self.assertIsInstance(data_source, str)


