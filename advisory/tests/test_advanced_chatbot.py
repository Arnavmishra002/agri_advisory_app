"""
Comprehensive test suite for Advanced Agricultural Chatbot
Tests all functionality including multilingual support, persistence, and security
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.core.cache import cache
import json
import tempfile
import os
from datetime import datetime, timedelta

from ..ml.advanced_chatbot import AdvancedAgriculturalChatbot
from ..models import ChatHistory, ChatSession, Crop, UserFeedback
from ..security_utils import SecurityValidator, RateLimiter
from ..cache_utils import CacheManager, cache_manager


class TestAdvancedChatbot(TestCase):
    """Test cases for Advanced Agricultural Chatbot"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.chatbot = AdvancedAgriculturalChatbot()
        self.test_user_id = "test_user_123"
        self.test_session_id = "test_session_456"
        
        # Mock external dependencies
        self.mock_weather_api = Mock()
        self.mock_market_api = Mock()
        self.mock_ml_system = Mock()
        
        # Set up test data
        self.sample_queries = {
            'english': "What crops should I plant in Delhi?",
            'hindi': "दिल्ली में मुझे कौन सी फसलें उगानी चाहिए?",
            'bengali': "দিল্লিতে আমার কী ফসল লাগানো উচিত?",
            'agricultural': "Tell me about wheat cultivation techniques",
            'weather': "What's the weather like today?",
            'market': "What are the current wheat prices?"
        }
    
    def tearDown(self):
        """Clean up after tests"""
        cache.clear()
    
    def test_chatbot_initialization(self):
        """Test chatbot initialization"""
        self.assertIsNotNone(self.chatbot)
        self.assertIsInstance(self.chatbot.conversation_context, dict)
        self.assertTrue(hasattr(self.chatbot, 'supported_languages'))
        self.assertGreater(len(self.chatbot.supported_languages), 20)
    
    def test_language_detection(self):
        """Test language detection functionality"""
        # Test English
        detected = self.chatbot._detect_language_advanced("Hello, how are you?")
        self.assertEqual(detected, 'en')
        
        # Test Hindi
        detected = self.chatbot._detect_language_advanced("नमस्ते, आप कैसे हैं?")
        self.assertEqual(detected, 'hi')
        
        # Test Bengali
        detected = self.chatbot._detect_language_advanced("নমস্কার, আপনি কেমন আছেন?")
        self.assertEqual(detected, 'bn')
        
        # Test auto-detection
        detected = self.chatbot._detect_language_advanced("Hello नमस्ते")
        self.assertIn(detected, ['en', 'hi'])
    
    @patch('advisory.ml.advanced_chatbot.ChatSession')
    @patch('advisory.ml.advanced_chatbot.ChatHistory')
    def test_chat_history_persistence(self, mock_chat_history, mock_chat_session):
        """Test chat history persistence"""
        # Mock database objects
        mock_session = Mock()
        mock_chat_session.objects.get_or_create.return_value = (mock_session, True)
        mock_chat_history.objects.create.return_value = Mock()
        
        # Test message persistence
        response = self.chatbot.get_response(
            self.sample_queries['english'],
            'en',
            self.test_user_id,
            self.test_session_id
        )
        
        # Verify session creation
        mock_chat_session.objects.get_or_create.assert_called_once()
        
        # Verify message creation
        self.assertTrue(mock_chat_history.objects.create.called)
    
    def test_english_conversation(self):
        """Test English conversation flow"""
        response = self.chatbot.get_response(
            self.sample_queries['english'],
            'en',
            self.test_user_id,
            self.test_session_id
        )
        
        self.assertIsInstance(response, dict)
        self.assertIn('response', response)
        self.assertIn('language', response)
        self.assertIn('confidence', response)
        self.assertEqual(response['language'], 'en')
        self.assertGreater(response['confidence'], 0.0)
    
    def test_hindi_conversation(self):
        """Test Hindi conversation flow"""
        response = self.chatbot.get_response(
            self.sample_queries['hindi'],
            'hi',
            self.test_user_id,
            self.test_session_id
        )
        
        self.assertIsInstance(response, dict)
        self.assertIn('response', response)
        self.assertIn('language', response)
        self.assertEqual(response['language'], 'hi')
    
    def test_bengali_conversation(self):
        """Test Bengali conversation flow"""
        response = self.chatbot.get_response(
            self.sample_queries['bengali'],
            'bn',
            self.test_user_id,
            self.test_session_id
        )
        
        self.assertIsInstance(response, dict)
        self.assertIn('response', response)
        self.assertIn('language', response)
        self.assertEqual(response['language'], 'bn')
    
    def test_agricultural_query_handling(self):
        """Test agricultural query handling"""
        response = self.chatbot.get_response(
            self.sample_queries['agricultural'],
            'en',
            self.test_user_id,
            self.test_session_id
        )
        
        self.assertIsInstance(response, dict)
        self.assertIn('response', response)
        self.assertIn('response_type', response)
        # Should be classified as agricultural
        self.assertIn(response['response_type'], ['agricultural', 'general'])
    
    def test_weather_query_handling(self):
        """Test weather query handling"""
        response = self.chatbot.get_response(
            self.sample_queries['weather'],
            'en',
            self.test_user_id,
            self.test_session_id
        )
        
        self.assertIsInstance(response, dict)
        self.assertIn('response', response)
        self.assertIn('response_type', response)
    
    def test_market_query_handling(self):
        """Test market query handling"""
        response = self.chatbot.get_response(
            self.sample_queries['market'],
            'en',
            self.test_user_id,
            self.test_session_id
        )
        
        self.assertIsInstance(response, dict)
        self.assertIn('response', response)
        self.assertIn('response_type', response)
    
    def test_conversation_context(self):
        """Test conversation context maintenance"""
        # First message
        response1 = self.chatbot.get_response(
            "Hello, I'm a farmer from Punjab",
            'en',
            self.test_user_id,
            self.test_session_id
        )
        
        # Second message (should maintain context)
        response2 = self.chatbot.get_response(
            "What crops grow well here?",
            'en',
            self.test_user_id,
            self.test_session_id
        )
        
        self.assertIsInstance(response1, dict)
        self.assertIsInstance(response2, dict)
        
        # Context should be maintained
        self.assertIsInstance(self.chatbot.conversation_context, dict)
    
    def test_error_handling(self):
        """Test error handling and graceful degradation"""
        # Test with invalid input
        response = self.chatbot.get_response(
            "",  # Empty query
            'en',
            self.test_user_id,
            self.test_session_id
        )
        
        self.assertIsInstance(response, dict)
        self.assertIn('response', response)
        # Should handle gracefully
    
    def test_fallback_mechanism(self):
        """Test fallback mechanism when advanced features fail"""
        with patch.object(self.chatbot, 'advanced_chatbot', None):
            response = self.chatbot.get_response(
                self.sample_queries['english'],
                'en',
                self.test_user_id,
                self.test_session_id
            )
            
            self.assertIsInstance(response, dict)
            self.assertIn('response', response)
    
    def test_multilingual_response_generation(self):
        """Test multilingual response generation"""
        languages = ['en', 'hi', 'bn', 'te', 'ta']
        
        for lang in languages:
            response = self.chatbot.get_response(
                "Hello",
                lang,
                self.test_user_id,
                self.test_session_id
            )
            
            self.assertIsInstance(response, dict)
            self.assertIn('response', response)
            self.assertIn('language', response)
    
    def test_session_management(self):
        """Test session management functionality"""
        # Test session creation
        session = self.chatbot._get_or_create_session(
            self.test_user_id,
            self.test_session_id
        )
        
        # Should return a session object (mocked)
        self.assertIsNotNone(session)
    
    def test_conversation_history_loading(self):
        """Test conversation history loading"""
        history = self.chatbot._load_conversation_history(self.test_session_id)
        
        self.assertIsInstance(history, list)
    
    def test_response_metadata(self):
        """Test response metadata generation"""
        response = self.chatbot.get_response(
            self.sample_queries['english'],
            'en',
            self.test_user_id,
            self.test_session_id
        )
        
        self.assertIn('timestamp', response)
        self.assertIn('metadata', response)
        self.assertIsInstance(response['metadata'], dict)


class TestSecurityValidator(TestCase):
    """Test cases for Security Validator"""
    
    def setUp(self):
        self.validator = SecurityValidator()
    
    def test_chat_message_validation(self):
        """Test chat message validation"""
        # Valid message
        result = self.validator.validate_chat_message("Hello, how are you?")
        self.assertTrue(result['valid'])
        self.assertIn('sanitized', result)
        
        # Empty message
        result = self.validator.validate_chat_message("")
        self.assertFalse(result['valid'])
        self.assertIn('errors', result)
        
        # Too long message
        long_message = "a" * 3000
        result = self.validator.validate_chat_message(long_message)
        self.assertFalse(result['valid'])
    
    def test_xss_protection(self):
        """Test XSS protection"""
        malicious_message = "<script>alert('xss')</script>Hello"
        result = self.validator.validate_chat_message(malicious_message)
        
        # Should detect XSS attempt
        self.assertTrue(len(result['warnings']) > 0)
        self.assertIn('script', result['warnings'][0].lower())
    
    def test_language_validation(self):
        """Test language code validation"""
        # Valid languages
        self.assertTrue(self.validator.validate_language_code('en'))
        self.assertTrue(self.validator.validate_language_code('hi'))
        self.assertTrue(self.validator.validate_language_code('auto'))
        
        # Invalid languages
        self.assertFalse(self.validator.validate_language_code('invalid'))
        self.assertFalse(self.validator.validate_language_code(''))
    
    def test_user_id_validation(self):
        """Test user ID validation"""
        # Valid user ID
        result = self.validator.validate_user_id("user123")
        self.assertTrue(result['valid'])
        
        # Invalid user ID with special characters
        result = self.validator.validate_user_id("user@123")
        self.assertFalse(result['valid'])
    
    def test_coordinate_validation(self):
        """Test coordinate validation"""
        # Valid coordinates
        result = self.validator.validate_coordinates(28.6139, 77.2090)
        self.assertTrue(result['valid'])
        self.assertEqual(result['sanitized_lat'], 28.6139)
        self.assertEqual(result['sanitized_lon'], 77.2090)
        
        # Invalid coordinates
        result = self.validator.validate_coordinates(200, 200)
        self.assertFalse(result['valid'])
    
    def test_html_sanitization(self):
        """Test HTML sanitization"""
        html_content = "<b>Hello</b> <script>alert('xss')</script>"
        sanitized = self.validator.sanitize_html(html_content)
        
        self.assertIn("Hello", sanitized)
        self.assertNotIn("<script>", sanitized)
        self.assertNotIn("alert", sanitized)


class TestCacheManager(TestCase):
    """Test cases for Cache Manager"""
    
    def setUp(self):
        self.cache_manager = CacheManager()
        cache.clear()
    
    def tearDown(self):
        cache.clear()
    
    def test_cache_set_and_get(self):
        """Test basic cache set and get operations"""
        key = "test_key"
        value = {"test": "data"}
        
        # Set value
        result = self.cache_manager.set(key, value)
        self.assertTrue(result)
        
        # Get value
        retrieved = self.cache_manager.get(key)
        self.assertEqual(retrieved, value)
    
    def test_cache_key_generation(self):
        """Test cache key generation"""
        key1 = self.cache_manager._generate_cache_key("test", "arg1", param="value1")
        key2 = self.cache_manager._generate_cache_key("test", "arg1", param="value1")
        key3 = self.cache_manager._generate_cache_key("test", "arg2", param="value1")
        
        self.assertEqual(key1, key2)  # Same parameters should generate same key
        self.assertNotEqual(key1, key3)  # Different parameters should generate different keys
    
    def test_cache_get_or_set(self):
        """Test cache get_or_set functionality"""
        key = "test_get_or_set"
        callable_func = lambda: {"generated": "data"}
        
        # First call should execute function
        result1 = self.cache_manager.get_or_set(key, callable_func)
        self.assertEqual(result1, {"generated": "data"})
        
        # Second call should return cached value
        result2 = self.cache_manager.get_or_set(key, callable_func)
        self.assertEqual(result2, {"generated": "data"})
    
    def test_cache_delete(self):
        """Test cache delete operation"""
        key = "test_delete"
        value = {"test": "data"}
        
        # Set value
        self.cache_manager.set(key, value)
        self.assertEqual(self.cache_manager.get(key), value)
        
        # Delete value
        result = self.cache_manager.delete(key)
        self.assertTrue(result)
        
        # Verify deletion
        self.assertIsNone(self.cache_manager.get(key))


class TestRateLimiter(TestCase):
    """Test cases for Rate Limiter"""
    
    def setUp(self):
        self.rate_limiter = RateLimiter()
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        identifier = "test_user"
        max_requests = 5
        
        # Should allow first 5 requests
        for i in range(max_requests):
            self.assertTrue(self.rate_limiter.is_allowed(identifier, max_requests, 60))
        
        # 6th request should be blocked
        self.assertFalse(self.rate_limiter.is_allowed(identifier, max_requests, 60))


class TestIntegration(TransactionTestCase):
    """Integration tests for the complete system"""
    
    def setUp(self):
        self.chatbot = AdvancedAgriculturalChatbot()
        self.validator = SecurityValidator()
        self.cache_manager = CacheManager()
    
    def test_complete_chat_flow(self):
        """Test complete chat flow with security and caching"""
        # Test data
        user_query = "What crops should I plant in Delhi?"
        user_id = "integration_test_user"
        session_id = "integration_test_session"
        
        # Validate input
        validation = self.validator.validate_api_request({
            'query': user_query,
            'language': 'en',
            'user_id': user_id,
            'session_id': session_id
        })
        
        self.assertTrue(validation['valid'])
        
        # Get chatbot response
        response = self.chatbot.get_response(
            validation['sanitized_data']['query'],
            validation['sanitized_data']['language'],
            validation['sanitized_data']['user_id'],
            validation['sanitized_data']['session_id']
        )
        
        self.assertIsInstance(response, dict)
        self.assertIn('response', response)
        self.assertIn('language', response)
        self.assertEqual(response['language'], 'en')
    
    def test_multilingual_integration(self):
        """Test multilingual integration"""
        test_cases = [
            ("Hello, how are you?", "en"),
            ("नमस्ते, आप कैसे हैं?", "hi"),
            ("নমস্কার, আপনি কেমন আছেন?", "bn"),
        ]
        
        for query, expected_lang in test_cases:
            # Validate
            validation = self.validator.validate_api_request({
                'query': query,
                'language': 'auto',
                'user_id': 'test_user',
                'session_id': 'test_session'
            })
            
            self.assertTrue(validation['valid'])
            
            # Get response
            response = self.chatbot.get_response(
                validation['sanitized_data']['query'],
                validation['sanitized_data']['language'],
                validation['sanitized_data']['user_id'],
                validation['sanitized_data']['session_id']
            )
            
            self.assertIsInstance(response, dict)
            self.assertIn('response', response)


class TestPerformance(TestCase):
    """Performance tests"""
    
    def setUp(self):
        self.chatbot = AdvancedAgriculturalChatbot()
        self.validator = SecurityValidator()
    
    def test_response_time(self):
        """Test response time for chatbot"""
        import time
        
        start_time = time.time()
        response = self.chatbot.get_response(
            "What crops should I plant in Delhi?",
            'en',
            'perf_test_user',
            'perf_test_session'
        )
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Response should be under 5 seconds
        self.assertLess(response_time, 5.0)
        self.assertIsInstance(response, dict)
    
    def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        import threading
        import time
        
        results = []
        errors = []
        
        def make_request():
            try:
                response = self.chatbot.get_response(
                    "Test query",
                    'en',
                    f'user_{threading.current_thread().ident}',
                    f'session_{threading.current_thread().ident}'
                )
                results.append(response)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Should handle concurrent requests without errors
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 10)


if __name__ == '__main__':
    unittest.main()
