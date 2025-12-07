#!/usr/bin/env python3
"""
Google AI Studio Integration for Enhanced Query Understanding
Uses Google's Generative AI to understand diverse queries beyond farming
"""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

class GoogleAIStudio:
    """Google AI Studio integration for advanced query understanding"""
    
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_AI_API_KEY', '')
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.model = "gemini-1.5-flash"
        self.cache = {}
        self.cache_duration = timedelta(hours=1)
        
        # Training prompts for query classification
        self.classification_prompt = """
You are an intelligent agricultural assistant that can understand both farming and general queries.

Classify the following query and provide a structured response in JSON format:

Query: "{query}"

Classification Categories:
1. farming_agriculture - Questions about crops, farming, agriculture, soil, weather for farming
2. general_knowledge - General information, trivia, facts, history, science
3. weather_climate - Weather forecasts, climate information, seasonal data
4. market_economics - Market prices, economic data, financial information
5. government_policies - Government schemes, policies, subsidies, programs
6. technology_ai - Technology questions, AI, software, technical support
7. education_learning - Educational content, how-to guides, tutorials
8. entertainment_fun - Games, jokes, entertainment, casual conversation
9. health_medical - Health advice, medical information (NOT for plants/crops)
10. mixed_query - Combination of multiple categories

Response Format (JSON only):
{
    "category": "farming_agriculture",
    "confidence": 0.95,
    "subcategory": "crop_recommendation",
    "language": "hi",
    "entities": ["wheat", "delhi", "season"],
    "intent": "User wants crop recommendations for wheat in Delhi",
    "response_type": "structured_data",
    "requires_farming_expertise": true,
    "requires_general_knowledge": false,
    "context_hints": ["location-based", "seasonal", "agricultural"]
}

Guidelines:
- If query contains agricultural terms (crops, farming, soil, etc.), classify as farming_agriculture
- If query is about general knowledge, classify as general_knowledge
- If query asks for weather/climate info, classify as weather_climate
- If query asks about prices/markets, classify as market_economics
- If query mentions government schemes/policies, classify as government_policies
- If query is about technology/AI, classify as technology_ai
- If query is educational, classify as education_learning
- If query is for entertainment, classify as entertainment_fun
- If query is about human health (not plant health), classify as health_medical
- If query combines multiple categories, classify as mixed_query

Language Detection:
- "hi" for Hindi or Hinglish queries
- "en" for English queries

Confidence should be between 0.0 and 1.0
"""

        self.training_examples = [
            {
                "query": "Delhi mein kya fasal lagayein",
                "category": "farming_agriculture",
                "confidence": 0.95,
                "subcategory": "crop_recommendation",
                "language": "hinglish",
                "intent": "User wants crop recommendations for Delhi"
            },
            {
                "query": "What is the capital of India?",
                "category": "general_knowledge",
                "confidence": 0.98,
                "subcategory": "geography",
                "language": "en",
                "intent": "User wants to know India's capital"
            },
            {
                "query": "Mumbai mein mausam kaisa hai",
                "category": "weather_climate",
                "confidence": 0.90,
                "subcategory": "current_weather",
                "language": "hinglish",
                "intent": "User wants current weather in Mumbai"
            },
            {
                "query": "Wheat ka price kya hai",
                "category": "market_economics",
                "confidence": 0.92,
                "subcategory": "commodity_price",
                "language": "hinglish",
                "intent": "User wants wheat price information"
            },
            {
                "query": "PM Kisan scheme kaise apply kare",
                "category": "government_policies",
                "confidence": 0.95,
                "subcategory": "scheme_information",
                "language": "hinglish",
                "intent": "User wants to know how to apply for PM Kisan scheme"
            },
            {
                "query": "How to use artificial intelligence?",
                "category": "technology_ai",
                "confidence": 0.88,
                "subcategory": "ai_usage",
                "language": "en",
                "intent": "User wants to learn about AI usage"
            },
            {
                "query": "Tell me a joke",
                "category": "entertainment_fun",
                "confidence": 0.85,
                "subcategory": "humor",
                "language": "en",
                "intent": "User wants entertainment"
            },
            {
                "query": "How to learn programming?",
                "category": "education_learning",
                "confidence": 0.90,
                "subcategory": "tutorial",
                "language": "en",
                "intent": "User wants programming education"
            },
            {
                "query": "What are the symptoms of diabetes?",
                "category": "health_medical",
                "confidence": 0.93,
                "subcategory": "medical_info",
                "language": "en",
                "intent": "User wants medical information"
            },
            {
                "query": "Crop prices and weather forecast",
                "category": "mixed_query",
                "confidence": 0.87,
                "subcategory": "agriculture_weather",
                "language": "en",
                "intent": "User wants both crop prices and weather information"
            }
        ]
    
    def classify_query(self, query: str) -> Dict[str, Any]:
        """Classify query using Google AI Studio"""
        try:
            # Check cache first
            cache_key = f"classification_{hash(query)}"
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                if datetime.now() - cached_data['timestamp'] < self.cache_duration:
                    return cached_data['data']
            
            # If no API key, use fallback classification
            if not self.api_key:
                return self._fallback_classification(query)
            
            # Prepare the prompt
            prompt = self.classification_prompt.format(query=query)
            
            # Call Google AI Studio
            response = self._call_google_ai(prompt)
            
            if response:
                # Cache the result
                self.cache[cache_key] = {
                    'data': response,
                    'timestamp': datetime.now()
                }
                return response
            else:
                return self._fallback_classification(query)
                
        except Exception as e:
            logger.error(f"Error in Google AI classification: {e}")
            return self._fallback_classification(query)
    
    def _call_google_ai_text(self, prompt: str) -> str:
        """Call Google AI to get raw text response (Conversational Mode)"""
        try:
            # Use Google Generative AI library if available
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                response = model.generate_content(prompt)
                return response.text if response.text else "I am unable to process that right now."
                
            except ImportError:
                 # Fallback to direct API call
                url = f"{self.base_url}/models/{self.model}:generateContent"
                headers = {"Content-Type": "application/json"}
                data = {"contents": [{"parts": [{"text": prompt}]}]}
                params = {"key": self.api_key}
                
                response = requests.post(url, headers=headers, json=data, params=params, timeout=30)
                if response.status_code == 200:
                    result = response.json()
                    if 'candidates' in result and result['candidates']:
                         return result['candidates'][0]['content']['parts'][0]['text']
                return "AI Service Unavailable (Direct)"
                
        except Exception as e:
            logger.error(f"Error calling Google AI Text: {e}")
            return "I am currently experiencing connection issues."
            
    def _call_google_ai(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call Google AI Studio API with enhanced error handling"""
        try:
            # Use Google Generative AI library if available
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.1,
                        top_k=1,
                        top_p=0.8,
                        max_output_tokens=1024,
                    )
                )
                
                if response.text:
                    # Extract JSON from response
                    json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        return json.loads(json_str)
                
                return None
                
            except ImportError:
                # Fallback to direct API call
                url = f"{self.base_url}/models/{self.model}:generateContent"
                
                headers = {
                    "Content-Type": "application/json",
                }
                
                data = {
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }],
                    "generationConfig": {
                        "temperature": 0.1,
                        "topK": 1,
                        "topP": 0.8,
                        "maxOutputTokens": 1024,
                    }
                }
                
                params = {"key": self.api_key}
                
                response = requests.post(url, headers=headers, json=data, params=params, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                
                if 'candidates' in result and len(result['candidates']) > 0:
                    content = result['candidates'][0]['content']['parts'][0]['text']
                    
                    # Extract JSON from response
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        return json.loads(json_str)
                
                return None
            
        except Exception as e:
            logger.error(f"Error calling Google AI: {e}")
            return None
    
    def _fallback_classification(self, query: str) -> Dict[str, Any]:
        """Fallback classification when Google AI is not available"""
        query_lower = query.lower().strip()
        
        # Enhanced keyword-based classification
        farming_keywords = [
            'crop', 'फसल', 'farming', 'खेती', 'agriculture', 'कृषि', 'soil', 'मिट्टी',
            'fertilizer', 'उर्वरक', 'irrigation', 'सिंचाई', 'harvest', 'कटाई',
            'sow', 'बोना', 'plant', 'पौधा', 'seed', 'बीज', 'yield', 'उत्पादन',
            'lagayein', 'लगाएं', 'suggest', 'सुझाव', 'recommend', 'अनुशंसा'
        ]
        
        weather_keywords = [
            'weather', 'मौसम', 'rain', 'बारिश', 'temperature', 'तापमान',
            'humidity', 'नमी', 'forecast', 'पूर्वानुमान', 'climate', 'जलवायु'
        ]
        
        market_keywords = [
            'price', 'कीमत', 'rate', 'दर', 'market', 'बाजार', 'mandi', 'मंडी',
            'cost', 'लागत', 'msp', 'एमएसपी', 'selling', 'बेचना'
        ]
        
        government_keywords = [
            'government', 'सरकार', 'scheme', 'योजना', 'subsidy', 'सब्सिडी',
            'pm kisan', 'policy', 'नीति', 'loan', 'कर्ज', 'credit', 'क्रेडिट'
        ]
        
        general_keywords = [
            'what is', 'क्या है', 'who is', 'कौन है', 'when', 'कब', 'where', 'कहां',
            'how', 'कैसे', 'why', 'क्यों', 'capital', 'राजधानी', 'history', 'इतिहास'
        ]
        
        tech_keywords = [
            'technology', 'तकनीक', 'ai', 'artificial intelligence', 'computer',
            'software', 'programming', 'code', 'digital', 'online'
        ]
        
        entertainment_keywords = [
            'joke', 'जोक', 'fun', 'मजा', 'game', 'खेल', 'entertainment', 'मनोरंजन',
            'bored', 'बोर', 'activity', 'गतिविधि'
        ]
        
        # Calculate scores
        farming_score = sum(1 for kw in farming_keywords if kw in query_lower)
        weather_score = sum(1 for kw in weather_keywords if kw in query_lower)
        market_score = sum(1 for kw in market_keywords if kw in query_lower)
        government_score = sum(1 for kw in government_keywords if kw in query_lower)
        general_score = sum(1 for kw in general_keywords if kw in query_lower)
        tech_score = sum(1 for kw in tech_keywords if kw in query_lower)
        entertainment_score = sum(1 for kw in entertainment_keywords if kw in query_lower)
        
        # Determine category
        scores = {
            'farming_agriculture': farming_score,
            'weather_climate': weather_score,
            'market_economics': market_score,
            'government_policies': government_score,
            'general_knowledge': general_score,
            'technology_ai': tech_score,
            'entertainment_fun': entertainment_score
        }
        
        max_score = max(scores.values())
        if max_score == 0:
            category = 'general_knowledge'
            confidence = 0.5
        else:
            category = max(scores, key=scores.get)
            confidence = min(max_score / 3, 0.95)  # Normalize confidence
        
        # Detect language
        language = self._detect_language(query)
        
        return {
            "category": category,
            "confidence": confidence,
            "subcategory": self._get_subcategory(category, query_lower),
            "language": language,
            "entities": self._extract_entities(query_lower),
            "intent": f"User query classified as {category}",
            "response_type": "structured_data",
            "requires_farming_expertise": category == 'farming_agriculture',
            "requires_general_knowledge": category in ['general_knowledge', 'education_learning'],
            "context_hints": self._get_context_hints(category, query_lower),
            "fallback": True
        }
    
    def _detect_language(self, query: str) -> str:
        """Detect language of the query"""
        devanagari_count = len(re.findall(r'[\u0900-\u097F]', query))
        if devanagari_count > 0:
            return 'hi'
        elif any(word in query.lower() for word in ['kya', 'kaise', 'kab', 'kahan', 'kaun', 'kyun']):
            return 'hinglish'
        else:
            return 'en'
    
    def _get_subcategory(self, category: str, query: str) -> str:
        """Get subcategory based on category and query"""
        subcategories = {
            'farming_agriculture': ['crop_recommendation', 'soil_health', 'pest_control', 'fertilizer_advice'],
            'weather_climate': ['current_weather', 'forecast', 'seasonal_data'],
            'market_economics': ['commodity_price', 'market_trends', 'trading_info'],
            'government_policies': ['scheme_information', 'subsidy_details', 'policy_updates'],
            'general_knowledge': ['geography', 'history', 'science', 'facts'],
            'technology_ai': ['ai_usage', 'software_help', 'technical_support'],
            'entertainment_fun': ['humor', 'games', 'casual_chat']
        }
        
        if category in subcategories:
            # Simple keyword-based subcategory selection
            for subcat in subcategories[category]:
                if subcat.replace('_', ' ') in query or any(word in query for word in subcat.split('_')):
                    return subcat
            return subcategories[category][0]
        
        return 'general'
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract entities from query"""
        entities = []
        
        # Common entities
        locations = ['delhi', 'mumbai', 'bangalore', 'chennai', 'kolkata', 'hyderabad']
        crops = ['wheat', 'गेहूं', 'rice', 'चावल', 'maize', 'मक्का', 'cotton', 'कपास']
        numbers = re.findall(r'\d+', query)
        
        for location in locations:
            if location in query:
                entities.append(location)
        
        for crop in crops:
            if crop in query:
                entities.append(crop)
        
        entities.extend(numbers)
        
        return entities
    
    def _get_context_hints(self, category: str, query: str) -> List[str]:
        """Get context hints for the query"""
        hints = []
        
        if 'delhi' in query or 'mumbai' in query:
            hints.append('location-based')
        
        if any(season in query for season in ['season', 'मौसम', 'rabi', 'खरीफ']):
            hints.append('seasonal')
        
        if category == 'farming_agriculture':
            hints.append('agricultural')
        
        if 'price' in query or 'कीमत' in query:
            hints.append('market-related')
        
        return hints
    
    def generate_enhanced_response(self, query: str, classification: Dict[str, Any]) -> str:
        """Generate enhanced response based on classification"""
        category = classification.get('category', 'general_knowledge')
        language = classification.get('language', 'en')
        
        if category == 'farming_agriculture':
            return self._generate_farming_response(query, classification)
        elif category == 'general_knowledge':
            return self._generate_general_response(query, classification)
        elif category == 'weather_climate':
            return self._generate_weather_response(query, classification)
        elif category == 'market_economics':
            return self._generate_market_response(query, classification)
        elif category == 'government_policies':
            return self._generate_government_response(query, classification)
        elif category == 'technology_ai':
            return self._generate_tech_response(query, classification)
        elif category == 'entertainment_fun':
            return self._generate_entertainment_response(query, classification)
        elif category == 'education_learning':
            return self._generate_education_response(query, classification)
        elif category == 'health_medical':
            return self._generate_health_response(query, classification)
        else:
            return self._generate_mixed_response(query, classification)
    
    def _generate_farming_response(self, query: str, classification: Dict[str, Any]) -> str:
        """Generate farming-related response"""
        if classification.get('language') == 'hi':
            return f"🌾 आपका प्रश्न कृषि से संबंधित है। मैं आपको विस्तृत कृषि सलाह दूंगा।"
        else:
            return f"🌾 Your query is related to agriculture. I'll provide detailed farming advice."
    
    def _generate_general_response(self, query: str, classification: Dict[str, Any]) -> str:
        """Generate general knowledge response"""
        if classification.get('language') == 'hi':
            return f"🌍 यह एक सामान्य ज्ञान का प्रश्न है। मैं आपकी मदद करूंगा।"
        else:
            return f"🌍 This is a general knowledge question. I'll help you with that."
    
    def _generate_weather_response(self, query: str, classification: Dict[str, Any]) -> str:
        """Generate weather-related response"""
        if classification.get('language') == 'hi':
            return f"🌤️ मौसम की जानकारी के लिए मैं आपकी मदद करूंगा।"
        else:
            return f"🌤️ I'll help you with weather information."
    
    def _generate_market_response(self, query: str, classification: Dict[str, Any]) -> str:
        """Generate market-related response"""
        if classification.get('language') == 'hi':
            return f"💰 बाजार की जानकारी के लिए मैं आपकी मदद करूंगा।"
        else:
            return f"💰 I'll help you with market information."
    
    def _generate_government_response(self, query: str, classification: Dict[str, Any]) -> str:
        """Generate government-related response"""
        if classification.get('language') == 'hi':
            return f"🏛️ सरकारी योजनाओं के बारे में मैं आपकी मदद करूंगा।"
        else:
            return f"🏛️ I'll help you with government schemes and policies."
    
    def _generate_tech_response(self, query: str, classification: Dict[str, Any]) -> str:
        """Generate technology-related response"""
        if classification.get('language') == 'hi':
            return f"💻 तकनीक के बारे में मैं आपकी मदद करूंगा।"
        else:
            return f"💻 I'll help you with technology-related questions."
    
    def _generate_entertainment_response(self, query: str, classification: Dict[str, Any]) -> str:
        """Generate entertainment-related response"""
        if classification.get('language') == 'hi':
            return f"😄 मनोरंजन के लिए मैं आपकी मदद करूंगा।"
        else:
            return f"😄 I'll help you with entertainment and fun activities."
    
    def _generate_education_response(self, query: str, classification: Dict[str, Any]) -> str:
        """Generate education-related response"""
        if classification.get('language') == 'hi':
            return f"📚 शिक्षा के बारे में मैं आपकी मदद करूंगा।"
        else:
            return f"📚 I'll help you with educational content."
    
    def _generate_health_response(self, query: str, classification: Dict[str, Any]) -> str:
        """Generate health-related response"""
        if classification.get('language') == 'hi':
            return f"🏥 स्वास्थ्य के बारे में मैं आपकी मदद करूंगा।"
        else:
            return f"🏥 I'll help you with health-related information."
    
    def _generate_mixed_response(self, query: str, classification: Dict[str, Any]) -> str:
        """Generate mixed query response"""
        if classification.get('language') == 'hi':
            return f"🔄 आपका प्रश्न कई विषयों को कवर करता है। मैं आपकी मदद करूंगा।"
        else:
            return f"🔄 Your query covers multiple topics. I'll help you with that."

    def process_query(self, query: str) -> str:
        """Process query and generate conversational response"""
        # 1. Classify first
        classification = self.classify_query(query)
        category = classification.get('category', 'general_knowledge')
        
        # 2. If general/tech/fun/education, use LLM directly for conversation
        conversational_categories = ['general_knowledge', 'technology_ai', 'entertainment_fun', 'education_learning', 'mixed_query']
        
        if category in conversational_categories or classification.get('confidence') < 0.6:
            system_prompt = """
            You are KrishiMitra, a helpful and friendly AI assistant for Indian farmers.
            While your primary focus is agriculture, you are knowledgeable about the world and can engage in general conversation.
            
            Guidelines:
            - Be polite, respectful, and helpful.
            - If the query is about general knowledge (history, science, etc.), answer it accurately like a smart assistant.
            - If the query is about farming, answer with expert agricultural knowledge.
            - Keep answers concise and easy to understand.
            - If the query is in Hindi/Hinglish, reply in the same language.
            """
            
            full_prompt = f"{system_prompt}\n\nUser Query: {query}"
            # Use text-specific method
            return self._call_google_ai_text(full_prompt)

        return self.generate_enhanced_response(query, classification)

    def generate_response(self, query: str) -> str:
        """Generate response - method expected by tests"""
        try:
            return self.process_query(query)
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I'm KrishiMitra AI. I can help with agriculture, crops, weather, and general questions. What would you like to know?"

# Create global instance
google_ai_studio = GoogleAIStudio()
