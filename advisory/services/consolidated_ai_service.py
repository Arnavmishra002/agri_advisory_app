#!/usr/bin/env python3
"""
Consolidated AI Service
Combines all AI-related functionality into a single, well-organized service
Replaces: google_ai_studio.py, ollama_integration.py, deep_ai_understanding.py, 
          realtime_government_ai.py, ultimate_realtime_system.py
"""

import os
import json
import logging
import requests
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class ConsolidatedAIService:
    """
    Consolidated AI Service that handles all AI-related functionality:
    - Google AI Studio integration
    - Ollama integration
    - Query understanding and classification
    - Response generation
    - Government data integration
    """
    
    def __init__(self):
        """Initialize the consolidated AI service with all components"""
        self.google_ai_key = os.getenv('GOOGLE_AI_API_KEY', '')
        self.ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        
        # Initialize components
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Krishimitra AI - Consolidated Service',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Cache for responses
        self.cache = {}
        self.cache_duration = timedelta(hours=1)
        
        # Initialize AI models
        self.models = {
            'llama3': 'llama3:8b',
            'mistral': 'mistral:7b',
            'gemini': 'gemini-1.5-flash'
        }
        
        # Query classification system
        self.classification_system = self._initialize_classification_system()
        
        # Response templates
        self.response_templates = self._initialize_response_templates()
    
    def _initialize_classification_system(self) -> Dict[str, Any]:
        """Initialize query classification system"""
        return {
            'farming_keywords': [
                'crop', 'फसल', 'farming', 'खेती', 'agriculture', 'कृषि',
                'soil', 'मिट्टी', 'weather', 'मौसम', 'price', 'कीमत',
                'market', 'बाजार', 'fertilizer', 'खाद', 'pest', 'कीट',
                'disease', 'रोग', 'irrigation', 'सिंचाई', 'harvest', 'फसल कटाई'
            ],
            'general_keywords': [
                'hello', 'नमस्ते', 'help', 'मदद', 'what', 'क्या', 'how', 'कैसे',
                'when', 'कब', 'where', 'कहाँ', 'why', 'क्यों'
            ],
            'weather_keywords': [
                'weather', 'मौसम', 'rain', 'बारिश', 'temperature', 'तापमान',
                'forecast', 'पूर्वानुमान', 'climate', 'जलवायु'
            ],
            'market_keywords': [
                'price', 'कीमत', 'market', 'बाजार', 'rate', 'दर', 'cost', 'लागत',
                'selling', 'बेचना', 'buying', 'खरीदना', 'profit', 'लाभ'
            ]
        }
    
    def _initialize_response_templates(self) -> Dict[str, str]:
        """Initialize response templates for different query types"""
        return {
            'farming_query': """
            मैं आपकी कृषि संबंधी जानकारी के लिए यहाँ हूँ। आप क्या जानना चाहते हैं?
            """,
            'general_query': """
            मैं आपकी सामान्य जानकारी के लिए यहाँ हूँ। कृपया अपना प्रश्न पूछें।
            """,
            'weather_query': """
            मैं आपको मौसम की जानकारी प्रदान कर सकता हूँ।
            """,
            'market_query': """
            मैं आपको बाजार कीमतों की जानकारी प्रदान कर सकता हूँ।
            """
        }
    
    def classify_query(self, query: str, language: str = 'auto') -> Dict[str, Any]:
        """
        Classify the user query to determine the appropriate response type
        
        Args:
            query: User's query string
            language: Language of the query
            
        Returns:
            Dictionary containing classification results
        """
        try:
            query_lower = query.lower()
            
            # Determine language if auto
            if language == 'auto':
                language = self._detect_language(query)
            
            # Initialize classification result
            classification = {
                'query': query,
                'language': language,
                'category': 'general',
                'subcategory': 'unknown',
                'confidence': 0.5,
                'entities': [],
                'intent': 'unknown',
                'requires_farming_expertise': False,
                'requires_general_knowledge': True,
                'context_hints': []
            }
            
            # Check for farming-related content
            farming_score = self._calculate_farming_score(query_lower)
            weather_score = self._calculate_weather_score(query_lower)
            market_score = self._calculate_market_score(query_lower)
            
            # Determine primary category
            max_score = max(farming_score, weather_score, market_score)
            
            if farming_score == max_score and farming_score > 0.3:
                classification.update({
                    'category': 'farming_agriculture',
                    'subcategory': 'crop_recommendation',
                    'confidence': farming_score,
                    'requires_farming_expertise': True,
                    'requires_general_knowledge': False,
                    'context_hints': ['agricultural', 'location-based']
                })
            elif weather_score == max_score and weather_score > 0.3:
                classification.update({
                    'category': 'weather_climate',
                    'subcategory': 'weather_forecast',
                    'confidence': weather_score,
                    'context_hints': ['location-based', 'temporal']
                })
            elif market_score == max_score and market_score > 0.3:
                classification.update({
                    'category': 'market_economics',
                    'subcategory': 'price_inquiry',
                    'confidence': market_score,
                    'context_hints': ['location-based', 'commodity-specific']
                })
            
            # Extract entities
            classification['entities'] = self._extract_entities(query)
            
            # Determine intent
            classification['intent'] = self._determine_intent(query, classification['category'])
            
            logger.info(f"Query classified: {classification}")
            return classification
            
        except Exception as e:
            logger.error(f"Error classifying query: {e}")
            return {
                'query': query,
                'language': language,
                'category': 'general',
                'confidence': 0.1,
                'error': str(e)
            }
    
    def _detect_language(self, query: str) -> str:
        """Detect the language of the query"""
        hindi_chars = sum(1 for char in query if '\u0900' <= char <= '\u097F')
        total_chars = len([char for char in query if char.isalpha()])
        
        if total_chars == 0:
            return 'en'
        
        hindi_ratio = hindi_chars / total_chars
        return 'hi' if hindi_ratio > 0.3 else 'en'
    
    def _calculate_farming_score(self, query: str) -> float:
        """Calculate farming-related score for the query"""
        farming_keywords = self.classification_system['farming_keywords']
        matches = sum(1 for keyword in farming_keywords if keyword in query)
        return min(matches / len(farming_keywords) * 2, 1.0)
    
    def _calculate_weather_score(self, query: str) -> float:
        """Calculate weather-related score for the query"""
        weather_keywords = self.classification_system['weather_keywords']
        matches = sum(1 for keyword in weather_keywords if keyword in query)
        return min(matches / len(weather_keywords) * 2, 1.0)
    
    def _calculate_market_score(self, query: str) -> float:
        """Calculate market-related score for the query"""
        market_keywords = self.classification_system['market_keywords']
        matches = sum(1 for keyword in market_keywords if keyword in query)
        return min(matches / len(market_keywords) * 2, 1.0)
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract entities from the query"""
        entities = []
        
        # Simple entity extraction (in production, use NER)
        common_entities = {
            'crops': ['wheat', 'गेहूं', 'rice', 'चावल', 'corn', 'मक्का', 'potato', 'आलू'],
            'locations': ['delhi', 'दिल्ली', 'mumbai', 'मुंबई', 'bangalore', 'बैंगलोर'],
            'seasons': ['kharif', 'खरीफ', 'rabi', 'रबी', 'zaid', 'जायद']
        }
        
        query_lower = query.lower()
        for category, items in common_entities.items():
            for item in items:
                if item in query_lower:
                    entities.append(item)
        
        return entities
    
    def _determine_intent(self, query: str, category: str) -> str:
        """Determine the user's intent based on query and category"""
        intent_mapping = {
            'farming_agriculture': 'crop_recommendation',
            'weather_climate': 'weather_inquiry',
            'market_economics': 'price_inquiry',
            'general': 'information_request'
        }
        
        return intent_mapping.get(category, 'information_request')
    
    def process_query(self, query: str, language: str = 'auto', 
                     location: str = '', context: Dict = None) -> Dict[str, Any]:
        """
        Main method to process any user query
        
        Args:
            query: User's query
            language: Language preference
            location: User's location
            context: Additional context
            
        Returns:
            Response dictionary
        """
        try:
            # Classify the query
            classification = self.classify_query(query, language)
            
            # Route to appropriate handler
            if classification['category'] == 'farming_agriculture':
                return self._handle_farming_query(query, classification, location, context)
            elif classification['category'] == 'weather_climate':
                return self._handle_weather_query(query, classification, location, context)
            elif classification['category'] == 'market_economics':
                return self._handle_market_query(query, classification, location, context)
            else:
                return self._handle_general_query(query, classification, context)
                
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                'response': 'Sorry, I encountered an error processing your query. Please try again.',
                'error': str(e),
                'data_source': 'error_fallback'
            }
    
    def _handle_farming_query(self, query: str, classification: Dict, 
                            location: str, context: Dict) -> Dict[str, Any]:
        """Handle farming-related queries"""
        try:
            # Use government data for farming queries
            from .consolidated_government_service import ConsolidatedGovernmentService
            gov_service = ConsolidatedGovernmentService()
            
            # Get real-time farming data
            farming_data = gov_service.get_farming_data(query, location)
            
            return {
                'response': farming_data.get('response', self.response_templates['farming_query']),
                'data_source': 'government_apis',
                'confidence': classification['confidence'],
                'classification': classification,
                'farming_data': farming_data
            }
            
        except Exception as e:
            logger.error(f"Error handling farming query: {e}")
            return self._handle_general_query(query, classification, context)
    
    def _handle_weather_query(self, query: str, classification: Dict, 
                            location: str, context: Dict) -> Dict[str, Any]:
        """Handle weather-related queries"""
        try:
            from .consolidated_government_service import ConsolidatedGovernmentService
            gov_service = ConsolidatedGovernmentService()
            
            weather_data = gov_service.get_weather_data(location)
            
            return {
                'response': weather_data.get('response', self.response_templates['weather_query']),
                'data_source': 'weather_apis',
                'confidence': classification['confidence'],
                'classification': classification,
                'weather_data': weather_data
            }
            
        except Exception as e:
            logger.error(f"Error handling weather query: {e}")
            return self._handle_general_query(query, classification, context)
    
    def _handle_market_query(self, query: str, classification: Dict, 
                           location: str, context: Dict) -> Dict[str, Any]:
        """Handle market-related queries"""
        try:
            from .consolidated_government_service import ConsolidatedGovernmentService
            gov_service = ConsolidatedGovernmentService()
            
            market_data = gov_service.get_market_data(query, location)
            
            return {
                'response': market_data.get('response', self.response_templates['market_query']),
                'data_source': 'market_apis',
                'confidence': classification['confidence'],
                'classification': classification,
                'market_data': market_data
            }
            
        except Exception as e:
            logger.error(f"Error handling market query: {e}")
            return self._handle_general_query(query, classification, context)
    
    def _handle_general_query(self, query: str, classification: Dict, 
                            context: Dict) -> Dict[str, Any]:
        """Handle general queries using AI"""
        try:
            # Try Ollama first (local AI)
            response = self._get_ollama_response(query, classification)
            
            if response and len(response) > 50:
                return {
                    'response': response,
                    'data_source': 'ollama_ai',
                    'confidence': classification['confidence'],
                    'classification': classification
                }
            
            # Fallback to Google AI if available
            if self.google_ai_key:
                response = self._get_google_ai_response(query, classification)
                if response:
                    return {
                        'response': response,
                        'data_source': 'google_ai',
                        'confidence': classification['confidence'],
                        'classification': classification
                    }
            
            # Final fallback
            return {
                'response': self.response_templates['general_query'],
                'data_source': 'fallback',
                'confidence': 0.1,
                'classification': classification
            }
            
        except Exception as e:
            logger.error(f"Error handling general query: {e}")
            return {
                'response': self.response_templates['general_query'],
                'data_source': 'error_fallback',
                'error': str(e)
            }
    
    def _get_ollama_response(self, query: str, classification: Dict) -> Optional[str]:
        """Get response from Ollama (local AI)"""
        try:
            url = f"{self.ollama_base_url}/api/generate"
            data = {
                "model": self.models['llama3'],
                "prompt": f"You are a helpful AI assistant. Respond to this query: {query}",
                "stream": False
            }
            
            response = self.session.post(url, json=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
        
        return None
    
    def _get_google_ai_response(self, query: str, classification: Dict) -> Optional[str]:
        """Get response from Google AI Studio"""
        try:
            if not self.google_ai_key:
                return None
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.models['gemini']}:generateContent"
            headers = {
                'Content-Type': 'application/json',
                'x-goog-api-key': self.google_ai_key
            }
            
            data = {
                "contents": [{
                    "parts": [{"text": f"You are a helpful AI assistant. Respond to this query: {query}"}]
                }]
            }
            
            response = self.session.post(url, headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '').strip()
            
        except Exception as e:
            logger.warning(f"Google AI not available: {e}")
        
        return None


# Convenience function for backward compatibility
def get_ai_response(query: str, language: str = 'auto', location: str = '') -> Dict[str, Any]:
    """Convenience function to get AI response"""
    ai_service = ConsolidatedAIService()
    return ai_service.process_query(query, language, location)



