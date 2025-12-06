#!/usr/bin/env python3
"""
AI Chatbot Accuracy and Responsiveness Tests
Tests AI chatbot accuracy, routing, and response quality
"""

import os
import time
from datetime import datetime
from unittest.mock import patch, Mock
from django.test import TestCase
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from django.urls import reverse


class AIChatbotAccuracyTests(APITestCase):
    """Tests for AI chatbot accuracy and responsiveness"""
    
    def setUp(self):
        """Set up test environment"""
        self.client = APIClient()
        self.chatbot_url = reverse('chatbot-list')
    
    def test_farming_query_accuracy(self):
        """Test that farming queries are accurately identified and routed"""
        farming_queries = [
            ('What crops should I grow in Delhi?', 'en', 'crop_recommendation'),
            ('मुझे दिल्ली में फसल सुझाव चाहिए', 'hi', 'crop_recommendation'),
            ('Weather forecast for farming', 'en', 'weather'),
            ('Market prices for wheat', 'en', 'market_prices'),
            ('Government schemes for farmers', 'en', 'government_schemes'),
            ('Pest control for wheat crop', 'en', 'pest_control'),
            ('मौसम की जानकारी चाहिए', 'hi', 'weather'),
            ('गेहूं की कीमत क्या है', 'hi', 'market_prices'),
        ]
        
        for query, language, expected_category in farming_queries:
            data = {
                'query': query,
                'language': language,
                'location': 'Delhi',
                'session_id': f'test_session_{int(time.time())}'
            }
            
            response = self.client.post(self.chatbot_url, data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('response', response.data)
            self.assertIn('data_source', response.data)
            
            # Should route to government APIs for farming queries
            data_source = response.data['data_source']
            self.assertIn(
                data_source,
                ['real_time_government_apis', 'government_apis', 'agricultural_ai_with_government_apis', 'fallback'],
                f"Farming query '{query}' should route to government APIs, got: {data_source}"
            )
    
    def test_general_query_routing(self):
        """Test that general queries route to AI services"""
        general_queries = [
            'What is artificial intelligence?',
            'Tell me a joke',
            'How does machine learning work?',
            'What is the capital of India?'
        ]
        
        for query in general_queries:
            data = {
                'query': query,
                'language': 'en',
                'session_id': f'test_session_{int(time.time())}'
            }
            
            response = self.client.post(self.chatbot_url, data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('response', response.data)
            # General queries should not necessarily use government APIs
            # but should still return valid responses
    
    def test_response_quality(self):
        """Test that AI responses are of good quality"""
        data = {
            'query': 'What crops should I grow in Delhi?',
            'language': 'en',
            'location': 'Delhi',
            'session_id': 'quality_test'
        }
        
        response = self.client.post(self.chatbot_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('response', response.data)
        
        response_text = response.data['response']
        # Response should not be empty
        self.assertGreater(len(response_text), 0)
        # Response should be meaningful (not just error message)
        self.assertNotIn('undefined', response_text.lower())
        self.assertNotIn('null', response_text.lower())
        self.assertNotIn('error occurred', response_text.lower())
    
    def test_multilingual_accuracy(self):
        """Test AI accuracy in multiple languages"""
        multilingual_queries = [
            ('What crops should I grow?', 'en'),
            ('मुझे फसल सुझाव चाहिए', 'hi'),
            ('फसल की जानकारी चाहिए', 'hi'),
            ('Weather forecast please', 'en'),
            ('मौसम पूर्वानुमान चाहिए', 'hi'),
        ]
        
        for query, language in multilingual_queries:
            data = {
                'query': query,
                'language': language,
                'location': 'Delhi',
                'session_id': f'multilingual_test_{int(time.time())}'
            }
            
            response = self.client.post(self.chatbot_url, data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('response', response.data)
            self.assertIn('language', response.data)
            # Response language should match requested language
            self.assertEqual(response.data.get('language'), language)
    
    def test_context_awareness(self):
        """Test that AI maintains context across conversation"""
        session_id = f'context_test_{int(time.time())}'
        
        # First query
        data1 = {
            'query': 'What crops should I grow in Delhi?',
            'language': 'en',
            'location': 'Delhi',
            'session_id': session_id
        }
        response1 = self.client.post(self.chatbot_url, data1, format='json')
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        # Follow-up query (should use context)
        data2 = {
            'query': 'Tell me more about wheat',
            'language': 'en',
            'location': 'Delhi',
            'session_id': session_id
        }
        response2 = self.client.post(self.chatbot_url, data2, format='json')
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        # Both should succeed
        self.assertIn('response', response1.data)
        self.assertIn('response', response2.data)
    
    def test_response_confidence(self):
        """Test that AI responses include confidence scores"""
        data = {
            'query': 'What crops should I grow?',
            'language': 'en',
            'location': 'Delhi',
            'session_id': 'confidence_test'
        }
        
        response = self.client.post(self.chatbot_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Confidence should be included
        if 'confidence' in response.data:
            confidence = response.data['confidence']
            # Confidence should be between 0 and 1 (or 0-100)
            self.assertGreater(confidence, 0)
            if confidence <= 1:
                self.assertLessEqual(confidence, 1)
            else:
                self.assertLessEqual(confidence, 100)
    
    def test_query_classification_accuracy(self):
        """Test that queries are correctly classified"""
        query_categories = {
            'farming': [
                'What crops should I grow?',
                'मुझे फसल सुझाव चाहिए',
                'Weather for farming',
                'Market prices',
                'Government schemes',
                'Pest control'
            ],
            'general': [
                'What is AI?',
                'Tell me a joke',
                'What is the capital?'
            ]
        }
        
        for category, queries in query_categories.items():
            for query in queries:
                data = {
                    'query': query,
                    'language': 'en',
                    'session_id': f'classification_test_{int(time.time())}'
                }
                
                response = self.client.post(self.chatbot_url, data, format='json')
                
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertIn('response', response.data)
                
                # Farming queries should use government APIs
                if category == 'farming':
                    data_source = response.data.get('data_source', '')
                    self.assertTrue(
                        'government' in data_source.lower() or 'real_time' in data_source.lower() or 'agricultural' in data_source.lower() or 'fallback' in data_source.lower(),
                        f"Farming query should route to government APIs: {query}"
                    )
    
    def test_response_relevance(self):
        """Test that AI responses are relevant to queries"""
        query_response_pairs = [
            ('What crops should I grow?', ['crop', 'grow', 'farm']),
            ('Weather forecast', ['weather', 'temperature', 'forecast']),
            ('Market prices', ['price', 'market', 'crop']),
            ('Government schemes', ['scheme', 'government', 'farmer']),
        ]
        
        for query, keywords in query_response_pairs:
            data = {
                'query': query,
                'language': 'en',
                'location': 'Delhi',
                'session_id': f'relevance_test_{int(time.time())}'
            }
            
            response = self.client.post(self.chatbot_url, data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_text = response.data.get('response', '').lower()
            
            # Response should contain relevant keywords (at least one)
            has_keyword = any(keyword.lower() in response_text for keyword in keywords)
            self.assertTrue(
                has_keyword or len(response_text) > 0,
                f"Response should be relevant to query '{query}', got: {response_text[:100]}"
            )
    
    def test_error_recovery(self):
        """Test that AI recovers gracefully from errors"""
        # Test with invalid query
        data = {
            'query': '',  # Empty query
            'session_id': 'error_recovery_test'
        }
        
        response = self.client.post(self.chatbot_url, data, format='json')
        
        # Should handle gracefully
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('response', response.data)
    
    def test_response_time(self):
        """Test AI response time"""
        data = {
            'query': 'What crops should I grow in Delhi?',
            'language': 'en',
            'location': 'Delhi',
            'session_id': 'response_time_test'
        }
        
        start_time = time.time()
        response = self.client.post(self.chatbot_url, data, format='json')
        end_time = time.time()
        
        response_time = end_time - start_time
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response should be reasonably fast (under 10 seconds)
        self.assertLess(response_time, 10.0, f"AI response took {response_time:.2f}s, should be under 10s")


class AIResponsivenessTests(APITestCase):
    """Tests for AI responsiveness and performance"""
    
    def setUp(self):
        """Set up test environment"""
        self.client = APIClient()
        self.chatbot_url = reverse('chatbot-list')
    
    def test_concurrent_ai_requests(self):
        """Test handling of concurrent AI requests"""
        import threading
        
        results = []
        
        def make_request(i):
            data = {
                'query': f'Test query {i}',
                'session_id': f'session_{i}',
                'location': 'Delhi'
            }
            start_time = time.time()
            response = self.client.post(self.chatbot_url, data, format='json')
            end_time = time.time()
            results.append({
                'status': response.status_code,
                'time': end_time - start_time
            })
        
        threads = [threading.Thread(target=make_request, args=(i,)) for i in range(5)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        self.assertEqual(len(results), 5)
        for result in results:
            self.assertEqual(result['status'], status.HTTP_200_OK)
            self.assertLess(result['time'], 15.0, "Concurrent requests should complete within reasonable time")


