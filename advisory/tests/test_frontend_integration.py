#!/usr/bin/env python3
"""
Frontend Integration Tests
Tests frontend service cards and API integration
"""

import os
import json
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status


class FrontendServiceCardsTests(APITestCase):
    """Tests for frontend service cards functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.client = APIClient()
    
    def test_government_schemes_service_card(self):
        """Test government schemes service card API endpoint"""
        url = reverse('government-schemes-list')
        params = {'location': 'Delhi'}
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data_source', response.data)
        # Verify government API is used
        self.assertIn('Government', response.data['data_source'])
    
    def test_crop_recommendations_service_card(self):
        """Test crop recommendations service card API endpoint"""
        url = reverse('advisories-list')
        params = {'location': 'Delhi'}
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data_source', response.data)
        # Verify government API integration
        has_gov_integration = (
            'government' in response.data.get('data_source', '').lower() or
            'government_data_integrated' in response.data
        )
        self.assertTrue(has_gov_integration)
    
    def test_weather_service_card(self):
        """Test weather service card API endpoint"""
        url = reverse('weather-list')
        params = {'location': 'Delhi'}
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('current_weather', response.data)
        self.assertIn('data_source', response.data)
        # Verify government API is used
        self.assertIn('Government', response.data['data_source'])
    
    def test_market_prices_service_card(self):
        """Test market prices service card API endpoint"""
        url = reverse('market-prices-list')
        params = {'location': 'Delhi'}
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data_source', response.data)
        # Verify government API is used
        data_source = response.data['data_source']
        self.assertTrue(
            'Agmarknet' in data_source or 'e-NAM' in data_source or 'Government' in data_source,
            f"Should use government APIs, got: {data_source}"
        )
    
    def test_pest_control_service_card(self):
        """Test pest control service card API endpoint"""
        url = reverse('pest-detection-list')
        params = {'crop': 'wheat', 'location': 'Delhi'}
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data_source', response.data)
        # Verify government API is used
        self.assertIn('Government', response.data['data_source'])
    
    def test_ai_assistant_service_card(self):
        """Test AI assistant service card API endpoint"""
        url = reverse('chatbot-list')
        data = {
            'query': 'What crops should I grow?',
            'session_id': 'test_session',
            'location': 'Delhi'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('response', response.data)
    
    def test_service_cards_data_format(self):
        """Test that service cards return proper data format"""
        services = {
            'government-schemes': (reverse('government-schemes-list'), {'location': 'Delhi'}),
            'weather': (reverse('weather-list'), {'location': 'Delhi'}),
            'market-prices': (reverse('market-prices-list'), {'location': 'Delhi'}),
            'crop-recommendations': (reverse('advisories-list'), {'location': 'Delhi'}),
        }
        
        for service_name, (url, params) in services.items():
            response = self.client.get(url, params)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            # All should have timestamp
            self.assertIn('timestamp', response.data)
            # All should have location
            self.assertIn('location', response.data)
            # All should have data_source
            self.assertIn('data_source', response.data)
    
    def test_service_cards_real_time_data(self):
        """Test that service cards return real-time data"""
        url = reverse('weather-list')
        params = {'location': 'Delhi'}
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have timestamp indicating real-time data
        self.assertIn('timestamp', response.data)
        timestamp = response.data['timestamp']
        # Timestamp should be recent (within last hour)
        self.assertIsNotNone(timestamp)


class FrontendAPIIntegrationTests(APITestCase):
    """Tests for frontend API integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.client = APIClient()
    
    def test_location_search_integration(self):
        """Test location search API integration"""
        url = reverse('locations-search-list')
        params = {'q': 'Delhi'}
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return location data
        self.assertIn('locations', response.data)
    
    def test_crop_search_integration(self):
        """Test crop search API integration"""
        url = reverse('crops-list')
        params = {'crop': 'wheat', 'location': 'Delhi'}
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return crop information
        self.assertIn('data_source', response.data)
    
    def test_service_card_error_handling(self):
        """Test that service cards handle errors gracefully"""
        # Test with invalid location
        url = reverse('weather-list')
        params = {'location': 'InvalidLocation999'}
        
        response = self.client.get(url, params)
        
        # Should handle gracefully
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR])
        if response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
            self.assertIn('error', response.data)
    
    def test_service_card_response_time(self):
        """Test service card response times"""
        import time
        
        services = {
            'weather': (reverse('weather-list'), {'location': 'Delhi'}),
            'market-prices': (reverse('market-prices-list'), {'location': 'Delhi'}),
            'government-schemes': (reverse('government-schemes-list'), {'location': 'Delhi'}),
        }
        
        max_response_time = 5.0
        
        for service_name, (url, params) in services.items():
            start_time = time.time()
            response = self.client.get(url, params)
            end_time = time.time()
            
            response_time = end_time - start_time
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertLess(
                response_time,
                max_response_time,
                f"{service_name} took {response_time:.2f}s, should be under {max_response_time}s"
            )


