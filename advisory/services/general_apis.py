#!/usr/bin/env python3
"""
General APIs Service for Non-Agricultural Questions
Integrates free APIs for handling general questions
"""

import requests
import json
import random
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class GeneralAPIsService:
    """Service for handling general questions using free APIs"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'KrisiMitra-AI-Assistant/1.0'
        })
        
        # API configurations
        self.huggingface_token = None  # Set your token if you have one
        self.openai_token = None  # Set your token if you have one
        
    def handle_general_question(self, query: str, language: str = 'en') -> Dict[str, Any]:
        """Handle general questions using various free APIs"""
        try:
            query_lower = query.lower().strip()
            
            # Try different APIs based on query type
            if any(word in query_lower for word in ['trivia', 'quiz', 'question', 'random fact']):
                return self._handle_trivia_request(query, language)
            
            elif any(word in query_lower for word in ['number', 'date', 'year', 'fact']):
                return self._handle_numbers_api(query, language)
            
            elif any(word in query_lower for word in ['what is', 'who is', 'when was', 'where is', 'why', 'how']):
                return self._handle_wikipedia_search(query, language)
            
            elif any(word in query_lower for word in ['bored', 'activity', 'fun', 'entertainment']):
                return self._handle_bored_api(query, language)
            
            else:
                # Try general AI response
                return self._handle_ai_response(query, language)
        except Exception as e:
            logger.error(f"General APIs service error: {e}")
            return self._get_fallback_response(query, language)
    
    def _handle_ai_response(self, query: str, language: str) -> Dict[str, Any]:
        """Handle general AI response fallback"""
        if language == 'hi':
            return {
                "response": f"मैं आपके प्रश्न '{query}' को समझने की कोशिश कर रहा हूं, लेकिन मुझे इसकी जानकारी नहीं है।\n\nमैं एक कृषि सहायक हूं और मुख्य रूप से खेती, फसल, मौसम, बाजार भाव और कृषि से जुड़े सवालों में मदद कर सकता हूं।\n\nक्या आप कोई कृषि संबंधी प्रश्न पूछना चाहते हैं?",
                "source": "fallback",
                "confidence": 0.30,
                "language": language
            }
        else:
            return {
                "response": f"I'm trying to understand your question '{query}', but I don't have information about that.\n\nI'm an agricultural assistant and mainly help with farming, crops, weather, market prices, and agricultural questions.\n\nWould you like to ask any agricultural-related questions?",
                "source": "fallback",
                "confidence": 0.30,
                "language": language
            }
    
    def _handle_trivia_request(self, query: str, language: str) -> Dict[str, Any]:
        """Handle trivia questions using Open Trivia Database"""
        try:
            # Get random trivia question
            response = self.session.get('https://opentdb.com/api.php?amount=1&type=multiple', timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data['results']:
                    question_data = data['results'][0]
                    
                    if language == 'hi':
                        return {
                            "response": f"🎯 **सामान्य ज्ञान प्रश्न:**\n\n❓ {question_data['question']}\n\n📝 विकल्प:\n• {question_data['correct_answer']}\n• {question_data['incorrect_answers'][0]}\n• {question_data['incorrect_answers'][1]}\n• {question_data['incorrect_answers'][2]}\n\n💡 सही उत्तर: {question_data['correct_answer']}\n\n🏷️ श्रेणी: {question_data['category']} | 🔥 कठिनाई: {question_data['difficulty']}",
                            "source": "opentdb",
                            "confidence": 0.9,
                            "language": language
                        }
                    else:
                        return {
                            "response": f"🎯 **Trivia Question:**\n\n❓ {question_data['question']}\n\n📝 Options:\n• {question_data['correct_answer']}\n• {question_data['incorrect_answers'][0]}\n• {question_data['incorrect_answers'][1]}\n• {question_data['incorrect_answers'][2]}\n\n💡 Correct Answer: {question_data['correct_answer']}\n\n🏷️ Category: {question_data['category']} | 🔥 Difficulty: {question_data['difficulty']}",
                            "source": "opentdb",
                            "confidence": 0.9,
                            "language": language
                        }
        except Exception as e:
            logger.error(f"Trivia API error: {e}")
            return self._get_fallback_response(query, language)
    
    def _handle_numbers_api(self, query: str, language: str) -> Dict[str, Any]:
        """Handle number-related questions using Numbers API"""
        try:
            # Try to extract number from query
            import re
            numbers = re.findall(r'\d+', query)
            
            if numbers:
                number = numbers[0]
                response = self.session.get(f'http://numbersapi.com/{number}', timeout=5)
                
                if response.status_code == 200:
                    fact = response.text
                    
                    if language == 'hi':
                        return {
                            "response": f"🔢 **संख्या के बारे में रोचक तथ्य:**\n\n📊 संख्या: {number}\n\n💡 तथ्य: {fact}\n\n🌐 स्रोत: Numbers API",
                            "source": "numbers_api",
                            "confidence": 0.8,
                            "language": language
                        }
                    else:
                        return {
                            "response": f"🔢 **Interesting Number Fact:**\n\n📊 Number: {number}\n\n💡 Fact: {fact}\n\n🌐 Source: Numbers API",
                            "source": "numbers_api",
                            "confidence": 0.8,
                            "language": language
                        }
            else:
                # Get random number fact
                response = self.session.get('http://numbersapi.com/random/trivia', timeout=5)
                
                if response.status_code == 200:
                    fact = response.text
                    
                    if language == 'hi':
                        return {
                            "response": f"🔢 **यादृच्छिक संख्या तथ्य:**\n\n💡 {fact}\n\n🌐 स्रोत: Numbers API",
                            "source": "numbers_api",
                            "confidence": 0.8,
                            "language": language
                        }
                    else:
                        return {
                            "response": f"🔢 **Random Number Fact:**\n\n💡 {fact}\n\n🌐 Source: Numbers API",
                            "source": "numbers_api",
                            "confidence": 0.8,
                            "language": language
                        }
        except Exception as e:
            logger.error(f"Numbers API error: {e}")
            return self._get_fallback_response(query, language)
    
    def _handle_wikipedia_search(self, query: str, language: str) -> Dict[str, Any]:
        """Handle general knowledge questions using Wikipedia API"""
        try:
            # Clean query for Wikipedia search
            search_query = query.replace('what is', '').replace('who is', '').replace('when was', '').replace('where is', '').strip()
            
            # Search Wikipedia
            search_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{search_query.replace(' ', '_')}"
            response = self.session.get(search_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'extract' in data and data['extract']:
                    summary = data['extract'][:500] + "..." if len(data['extract']) > 500 else data['extract']
                    
                    if language == 'hi':
                        return {
                            "response": f"📚 **सामान्य ज्ञान:**\n\n🔍 **{data.get('title', search_query)}**\n\n📝 जानकारी: {summary}\n\n🌐 स्रोत: Wikipedia",
                            "source": "wikipedia",
                            "confidence": 0.7,
                            "language": language
                        }
                    else:
                        return {
                            "response": f"📚 **General Knowledge:**\n\n🔍 **{data.get('title', search_query)}**\n\n📝 Information: {summary}\n\n🌐 Source: Wikipedia",
                            "source": "wikipedia",
                            "confidence": 0.7,
                            "language": language
                        }
        except Exception as e:
            logger.error(f"Wikipedia API error: {e}")
            return self._get_fallback_response(query, language)
    
    def _handle_bored_api(self, query: str, language: str) -> Dict[str, Any]:
        """Handle boredom-related queries using Bored API"""
        try:
            response = self.session.get('https://www.boredapi.com/api/activity', timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                activity = data.get('activity', '')
                activity_type = data.get('type', '')
                participants = data.get('participants', 1)
                
                if language == 'hi':
                    return {
                        "response": f"🎲 **मनोरंजन सुझाव:**\n\n🎯 गतिविधि: {activity}\n\n👥 भागीदार: {participants} व्यक्ति\n\n🏷️ प्रकार: {activity_type.title()}\n\n🌐 स्रोत: Bored API",
                        "source": "bored_api",
                        "confidence": 0.8,
                        "language": language
                    }
                else:
                    return {
                        "response": f"🎲 **Entertainment Suggestion:**\n\n🎯 Activity: {activity}\n\n👥 Participants: {participants} person(s)\n\n🏷️ Type: {activity_type.title()}\n\n🌐 Source: Bored API",
                        "source": "bored_api",
                        "confidence": 0.8,
                        "language": language
                    }
        except Exception as e:
            logger.error(f"Bored API error: {e}")
            return self._get_fallback_response(query, language)
    
    def _handle_ai_response(self, query: str, language: str) -> Dict[str, Any]:
        """Handle general questions using AI APIs"""
        
        # Try Hugging Face first (free tier)
        if self.huggingface_token:
            try:
                return self._handle_huggingface_api(query, language)
            except Exception as e:
                logger.error(f"Hugging Face API error: {e}")
        
        # Fallback to simple response
        return self._get_fallback_response(query, language)
    
    def _handle_huggingface_api(self, query: str, language: str) -> Dict[str, Any]:
        """Handle questions using Hugging Face Inference API"""
        try:
            headers = {
                'Authorization': f'Bearer {self.huggingface_token}',
                'Content-Type': 'application/json'
            }
            
            # Use a simple text generation model
            payload = {
                "inputs": f"Question: {query}\nAnswer:",
                "parameters": {
                    "max_length": 150,
                    "temperature": 0.7
                }
            }
            
            response = self.session.post(
                'https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium',
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    answer = data[0].get('generated_text', '').replace(f"Question: {query}\nAnswer:", '').strip()
                    
                    if language == 'hi':
                        return {
                            "response": f"🤖 **AI उत्तर:**\n\n❓ प्रश्न: {query}\n\n💡 उत्तर: {answer}\n\n🌐 स्रोत: Hugging Face AI",
                            "source": "huggingface",
                            "confidence": 0.6,
                            "language": language
                        }
                    else:
                        return {
                            "response": f"🤖 **AI Answer:**\n\n❓ Question: {query}\n\n💡 Answer: {answer}\n\n🌐 Source: Hugging Face AI",
                            "source": "huggingface",
                            "confidence": 0.6,
                            "language": language
                        }
        except Exception as e:
            logger.error(f"Hugging Face API error: {e}")
            return self._get_fallback_response(query, language)
    
    def _get_fallback_response(self, query: str, language: str) -> Dict[str, Any]:
        """Fallback response when APIs fail"""
        if language == 'hi':
            return {
                "response": f"मैं आपके प्रश्न '{query}' को समझने की कोशिश कर रहा हूं, लेकिन मुझे इसकी जानकारी नहीं है।\n\nमैं एक कृषि सहायक हूं और मुख्य रूप से खेती, फसल, मौसम, बाजार भाव और कृषि से जुड़े सवालों में मदद कर सकता हूं।\n\nक्या आप कोई कृषि संबंधी प्रश्न पूछना चाहते हैं?",
                "source": "fallback",
                "confidence": 0.3,
                "language": language
            }
        else:
            return {
                "response": f"I'm trying to understand your question '{query}', but I don't have information about that.\n\nI'm an agricultural assistant and mainly help with farming, crops, weather, market prices, and agricultural questions.\n\nWould you like to ask any agricultural-related questions?",
                "source": "fallback",
                "confidence": 0.3,
                "language": language
            }

# Create global instance
general_apis_service = GeneralAPIsService()
