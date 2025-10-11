#!/usr/bin/env python3
"""
Enhanced Google AI Studio Training System
Advanced training for understanding non-farming queries with improved accuracy
"""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import re
import random

logger = logging.getLogger(__name__)

class EnhancedGoogleAITraining:
    """Enhanced Google AI Studio training system for comprehensive query understanding"""
    
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_AI_API_KEY', '')
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.model = "gemini-1.5-flash"
        self.cache = {}
        self.cache_duration = timedelta(hours=2)
        
        # Enhanced training dataset with diverse examples
        self.training_dataset = self._load_comprehensive_training_data()
        
        # Advanced classification prompts
        self.advanced_classification_prompt = """
You are an advanced AI agricultural assistant with comprehensive knowledge across all domains. Your task is to classify and understand queries with high accuracy.

Query: "{query}"

Classification Categories:
1. farming_agriculture - Agricultural queries (crops, farming, soil, weather for farming, pest control, fertilizers)
2. general_knowledge - General information, facts, history, geography, science, trivia
3. weather_climate - Weather forecasts, climate data, seasonal information
4. market_economics - Market prices, economic data, financial information, trading
5. government_policies - Government schemes, policies, subsidies, programs, regulations
6. technology_ai - Technology, AI, software, programming, digital tools
7. education_learning - Educational content, tutorials, how-to guides, academic topics
8. entertainment_fun - Games, jokes, entertainment, casual conversation, activities
9. health_medical - Human health, medical information, wellness (NOT plant health)
10. business_finance - Business advice, financial planning, investment, entrepreneurship
11. lifestyle_culture - Lifestyle, culture, food, travel, personal development
12. news_current_events - Current events, news, recent developments
13. mixed_query - Combination of multiple categories

Response Format (JSON only):
{
    "category": "general_knowledge",
    "confidence": 0.95,
    "subcategory": "geography",
    "language": "en",
    "entities": ["india", "capital"],
    "intent": "User wants to know India's capital city",
    "response_type": "factual_answer",
    "requires_farming_expertise": false,
    "requires_general_knowledge": true,
    "context_hints": ["geographical", "factual"],
    "suggested_response": "New Delhi is the capital of India",
    "related_topics": ["geography", "india", "capitals"]
}

Guidelines:
- Analyze the query context carefully
- Consider both explicit and implicit meanings
- Use high confidence (0.8+) for clear classifications
- Use medium confidence (0.6-0.8) for ambiguous queries
- Use low confidence (0.4-0.6) for very unclear queries
- Always provide helpful suggested responses
- Include related topics for better context

Language Detection:
- "hi" for Hindi queries
- "hinglish" for Hinglish (Hindi-English mix)
- "en" for English queries
- "ta" for Tamil queries
- "te" for Telugu queries
- "bn" for Bengali queries
"""

        # Comprehensive training examples
        self.training_examples = [
            # Farming/Agriculture Examples
            {
                "query": "Delhi mein kya fasal lagayein",
                "category": "farming_agriculture",
                "confidence": 0.95,
                "subcategory": "crop_recommendation",
                "language": "hinglish",
                "intent": "User wants crop recommendations for Delhi",
                "suggested_response": "Delhi में आप wheat, rice, maize, और vegetables उगा सकते हैं।"
            },
            {
                "query": "Wheat ke liye kaun sa fertilizer use karein",
                "category": "farming_agriculture",
                "confidence": 0.92,
                "subcategory": "fertilizer_advice",
                "language": "hinglish",
                "intent": "User wants fertilizer recommendations for wheat",
                "suggested_response": "Wheat के लिए NPK 20:20:20 या urea, DAP, और potash का उपयोग करें।"
            },
            
            # General Knowledge Examples
            {
                "query": "What is the capital of India?",
                "category": "general_knowledge",
                "confidence": 0.98,
                "subcategory": "geography",
                "language": "en",
                "intent": "User wants to know India's capital",
                "suggested_response": "New Delhi is the capital of India."
            },
            {
                "query": "Who invented the telephone?",
                "category": "general_knowledge",
                "confidence": 0.95,
                "subcategory": "history",
                "language": "en",
                "intent": "User wants to know about telephone invention",
                "suggested_response": "Alexander Graham Bell is credited with inventing the telephone."
            },
            {
                "query": "भारत का राष्ट्रीय पक्षी क्या है?",
                "category": "general_knowledge",
                "confidence": 0.97,
                "subcategory": "facts",
                "language": "hi",
                "intent": "User wants to know India's national bird",
                "suggested_response": "भारत का राष्ट्रीय पक्षी मोर है।"
            },
            
            # Weather Examples
            {
                "query": "Mumbai mein mausam kaisa hai",
                "category": "weather_climate",
                "confidence": 0.90,
                "subcategory": "current_weather",
                "language": "hinglish",
                "intent": "User wants current weather in Mumbai",
                "suggested_response": "Mumbai का मौसम आज गर्म और आर्द्र है।"
            },
            {
                "query": "Will it rain tomorrow?",
                "category": "weather_climate",
                "confidence": 0.88,
                "subcategory": "forecast",
                "language": "en",
                "intent": "User wants tomorrow's weather forecast",
                "suggested_response": "Tomorrow's weather forecast shows a 60% chance of rain."
            },
            
            # Market/Economics Examples
            {
                "query": "Wheat ka price kya hai",
                "category": "market_economics",
                "confidence": 0.92,
                "subcategory": "commodity_price",
                "language": "hinglish",
                "intent": "User wants wheat price information",
                "suggested_response": "Wheat का current price ₹2,450 per quintal है।"
            },
            {
                "query": "Stock market today",
                "category": "market_economics",
                "confidence": 0.85,
                "subcategory": "market_trends",
                "language": "en",
                "intent": "User wants stock market information",
                "suggested_response": "Today's stock market is showing positive trends."
            },
            
            # Technology Examples
            {
                "query": "How to use artificial intelligence?",
                "category": "technology_ai",
                "confidence": 0.88,
                "subcategory": "ai_usage",
                "language": "en",
                "intent": "User wants to learn about AI usage",
                "suggested_response": "AI can be used for automation, data analysis, and decision making."
            },
            {
                "query": "Python programming tutorial",
                "category": "technology_ai",
                "confidence": 0.90,
                "subcategory": "programming",
                "language": "en",
                "intent": "User wants Python programming help",
                "suggested_response": "Python is a versatile programming language. Start with basic syntax and data types."
            },
            
            # Entertainment Examples
            {
                "query": "Tell me a joke",
                "category": "entertainment_fun",
                "confidence": 0.85,
                "subcategory": "humor",
                "language": "en",
                "intent": "User wants entertainment",
                "suggested_response": "Why don't scientists trust atoms? Because they make up everything!"
            },
            {
                "query": "Fun activities for kids",
                "category": "entertainment_fun",
                "confidence": 0.87,
                "subcategory": "activities",
                "language": "en",
                "intent": "User wants activity suggestions",
                "suggested_response": "Kids can enjoy drawing, puzzles, outdoor games, and reading."
            },
            
            # Education Examples
            {
                "query": "How to learn programming?",
                "category": "education_learning",
                "confidence": 0.90,
                "subcategory": "tutorial",
                "language": "en",
                "intent": "User wants programming education",
                "suggested_response": "Start with online courses, practice coding daily, and build projects."
            },
            {
                "query": "Math formulas for algebra",
                "category": "education_learning",
                "confidence": 0.92,
                "subcategory": "academic",
                "language": "en",
                "intent": "User wants math help",
                "suggested_response": "Common algebra formulas include quadratic formula, slope formula, and distance formula."
            },
            
            # Health Examples
            {
                "query": "What are the symptoms of diabetes?",
                "category": "health_medical",
                "confidence": 0.93,
                "subcategory": "medical_info",
                "language": "en",
                "intent": "User wants medical information",
                "suggested_response": "Diabetes symptoms include increased thirst, frequent urination, and fatigue."
            },
            {
                "query": "How to stay healthy?",
                "category": "health_medical",
                "confidence": 0.88,
                "subcategory": "wellness",
                "language": "en",
                "intent": "User wants health advice",
                "suggested_response": "Stay healthy by eating balanced meals, exercising regularly, and getting enough sleep."
            },
            
            # Business Examples
            {
                "query": "How to start a business?",
                "category": "business_finance",
                "confidence": 0.89,
                "subcategory": "entrepreneurship",
                "language": "en",
                "intent": "User wants business advice",
                "suggested_response": "Start a business by identifying a market need, creating a business plan, and securing funding."
            },
            {
                "query": "Investment tips for beginners",
                "category": "business_finance",
                "confidence": 0.87,
                "subcategory": "investment",
                "language": "en",
                "intent": "User wants investment advice",
                "suggested_response": "Begin with low-risk investments, diversify your portfolio, and invest for the long term."
            },
            
            # Mixed Query Examples
            {
                "query": "Crop prices and weather forecast",
                "category": "mixed_query",
                "confidence": 0.87,
                "subcategory": "agriculture_weather",
                "language": "en",
                "intent": "User wants both crop prices and weather information",
                "suggested_response": "I can help you with both crop prices and weather forecasts. Which specific crops and locations are you interested in?"
            }
        ]
    
    def _load_comprehensive_training_data(self) -> Dict[str, Any]:
        """Load comprehensive training data for better AI understanding"""
        return {
            "total_examples": len(self.training_examples),
            "categories": [
                "farming_agriculture", "general_knowledge", "weather_climate",
                "market_economics", "government_policies", "technology_ai",
                "education_learning", "entertainment_fun", "health_medical",
                "business_finance", "lifestyle_culture", "news_current_events", "mixed_query"
            ],
            "languages": ["en", "hi", "hinglish", "ta", "te", "bn"],
            "confidence_thresholds": {
                "high": 0.8,
                "medium": 0.6,
                "low": 0.4
            }
        }
    
    def train_ai_model(self, custom_examples: List[Dict] = None) -> Dict[str, Any]:
        """Train the AI model with comprehensive examples"""
        try:
            training_data = self.training_examples.copy()
            if custom_examples:
                training_data.extend(custom_examples)
            
            # Create training prompt
            training_prompt = self._create_training_prompt(training_data)
            
            # Call Google AI for training
            if self.api_key:
                response = self._call_google_ai_training(training_prompt)
                if response:
                    return {
                        "status": "success",
                        "message": "AI model trained successfully",
                        "training_examples": len(training_data),
                        "response": response
                    }
            
            # Fallback training
            return self._fallback_training(training_data)
            
        except Exception as e:
            logger.error(f"Error in AI training: {e}")
            return {
                "status": "error",
                "message": f"Training failed: {str(e)}",
                "training_examples": 0
            }
    
    def _create_training_prompt(self, examples: List[Dict]) -> str:
        """Create comprehensive training prompt"""
        prompt = self.advanced_classification_prompt + "\n\n"
        prompt += "Training Examples:\n\n"
        
        for i, example in enumerate(examples[:20], 1):  # Limit to 20 examples
            prompt += f"Example {i}:\n"
            prompt += f"Query: {example['query']}\n"
            prompt += f"Category: {example['category']}\n"
            prompt += f"Confidence: {example['confidence']}\n"
            prompt += f"Language: {example['language']}\n"
            prompt += f"Intent: {example['intent']}\n"
            prompt += f"Suggested Response: {example['suggested_response']}\n\n"
        
        prompt += "\nNow classify the following query using the same format:\n"
        return prompt
    
    def _call_google_ai_training(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call Google AI for training with enhanced error handling"""
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
                        max_output_tokens=2048,
                    )
                )
                
                if response.text:
                    return {
                        "training_completed": True,
                        "model_response": response.text,
                        "timestamp": datetime.now().isoformat()
                    }
                
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
                        "maxOutputTokens": 2048,
                    }
                }
                
                params = {"key": self.api_key}
                
                response = requests.post(url, headers=headers, json=data, params=params, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                
                if 'candidates' in result and len(result['candidates']) > 0:
                    content = result['candidates'][0]['content']['parts'][0]['text']
                    return {
                        "training_completed": True,
                        "model_response": content,
                        "timestamp": datetime.now().isoformat()
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error calling Google AI for training: {e}")
            return None
    
    def _fallback_training(self, examples: List[Dict]) -> Dict[str, Any]:
        """Fallback training when Google AI is not available"""
        return {
            "status": "fallback",
            "message": "Using fallback training system",
            "training_examples": len(examples),
            "categories_trained": list(set(ex['category'] for ex in examples)),
            "languages_trained": list(set(ex['language'] for ex in examples)),
            "timestamp": datetime.now().isoformat()
        }
    
    def classify_query_enhanced(self, query: str) -> Dict[str, Any]:
        """Enhanced query classification with training"""
        try:
            # Check cache first
            cache_key = f"enhanced_classification_{hash(query)}"
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                if datetime.now() - cached_data['timestamp'] < self.cache_duration:
                    return cached_data['data']
            
            # Use Google AI if available
            if self.api_key:
                classification = self._call_google_ai_classification(query)
                if classification:
                    # Cache the result
                    self.cache[cache_key] = {
                        'data': classification,
                        'timestamp': datetime.now()
                    }
                    return classification
            
            # Fallback to enhanced rule-based classification
            classification = self._enhanced_fallback_classification(query)
            
            # Cache the result
            self.cache[cache_key] = {
                'data': classification,
                'timestamp': datetime.now()
            }
            
            return classification
            
        except Exception as e:
            logger.error(f"Error in enhanced classification: {e}")
            return self._enhanced_fallback_classification(query)
    
    def _call_google_ai_classification(self, query: str) -> Optional[Dict[str, Any]]:
        """Call Google AI for classification"""
        try:
            prompt = self.advanced_classification_prompt.format(query=query)
            
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
            logger.error(f"Error calling Google AI for classification: {e}")
            return None
    
    def _enhanced_fallback_classification(self, query: str) -> Dict[str, Any]:
        """Enhanced fallback classification with comprehensive rules"""
        query_lower = query.lower().strip()
        
        # Comprehensive keyword mappings
        keyword_mappings = {
            'farming_agriculture': [
                'crop', 'फसल', 'farming', 'खेती', 'agriculture', 'कृषि', 'soil', 'मिट्टी',
                'fertilizer', 'उर्वरक', 'irrigation', 'सिंचाई', 'harvest', 'कटाई',
                'sow', 'बोना', 'plant', 'पौधा', 'seed', 'बीज', 'yield', 'उत्पादन',
                'lagayein', 'लगाएं', 'suggest', 'सुझाव', 'recommend', 'अनुशंसा',
                'pest', 'कीट', 'disease', 'रोग', 'weed', 'खरपतवार', 'organic', 'जैविक'
            ],
            'general_knowledge': [
                'what is', 'क्या है', 'who is', 'कौन है', 'when', 'कब', 'where', 'कहां',
                'how', 'कैसे', 'why', 'क्यों', 'capital', 'राजधानी', 'history', 'इतिहास',
                'invented', 'discovered', 'found', 'created', 'made', 'built'
            ],
            'weather_climate': [
                'weather', 'मौसम', 'rain', 'बारिश', 'temperature', 'तापमान',
                'humidity', 'नमी', 'forecast', 'पूर्वानुमान', 'climate', 'जलवायु',
                'hot', 'cold', 'warm', 'cool', 'sunny', 'cloudy', 'storm'
            ],
            'market_economics': [
                'price', 'कीमत', 'rate', 'दर', 'market', 'बाजार', 'mandi', 'मंडी',
                'cost', 'लागत', 'msp', 'एमएसपी', 'selling', 'बेचना', 'buying', 'खरीदना',
                'stock', 'share', 'investment', 'trading', 'economy'
            ],
            'technology_ai': [
                'technology', 'तकनीक', 'ai', 'artificial intelligence', 'computer',
                'software', 'programming', 'code', 'digital', 'online', 'app', 'website',
                'python', 'java', 'javascript', 'html', 'css', 'database'
            ],
            'entertainment_fun': [
                'joke', 'जोक', 'fun', 'मजा', 'game', 'खेल', 'entertainment', 'मनोरंजन',
                'bored', 'बोर', 'activity', 'गतिविधि', 'movie', 'music', 'song'
            ],
            'education_learning': [
                'learn', 'सीखना', 'study', 'पढ़ना', 'education', 'शिक्षा', 'tutorial',
                'course', 'class', 'school', 'college', 'university', 'degree'
            ],
            'health_medical': [
                'health', 'स्वास्थ्य', 'medical', 'चिकित्सा', 'doctor', 'डॉक्टर',
                'medicine', 'दवा', 'symptoms', 'लक्षण', 'treatment', 'उपचार',
                'diabetes', 'blood pressure', 'heart', 'cancer'
            ],
            'business_finance': [
                'business', 'व्यापार', 'finance', 'वित्त', 'money', 'पैसा',
                'investment', 'निवेश', 'loan', 'कर्ज', 'credit', 'क्रेडिट',
                'bank', 'बैंक', 'profit', 'लाभ', 'loss', 'हानि'
            ]
        }
        
        # Calculate scores for each category
        scores = {}
        for category, keywords in keyword_mappings.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            scores[category] = score
        
        # Determine the best category
        max_score = max(scores.values())
        if max_score == 0:
            category = 'general_knowledge'
            confidence = 0.5
        else:
            category = max(scores, key=scores.get)
            confidence = min(max_score / 3, 0.95)
        
        # Detect language
        language = self._detect_language_enhanced(query)
        
        # Extract entities
        entities = self._extract_entities_enhanced(query_lower)
        
        # Get context hints
        context_hints = self._get_context_hints_enhanced(category, query_lower)
        
        return {
            "category": category,
            "confidence": confidence,
            "subcategory": self._get_subcategory_enhanced(category, query_lower),
            "language": language,
            "entities": entities,
            "intent": f"User query classified as {category}",
            "response_type": "structured_data",
            "requires_farming_expertise": category == 'farming_agriculture',
            "requires_general_knowledge": category in ['general_knowledge', 'education_learning'],
            "context_hints": context_hints,
            "fallback": True,
            "suggested_response": self._generate_suggested_response(category, query, language),
            "related_topics": self._get_related_topics(category)
        }
    
    def _detect_language_enhanced(self, query: str) -> str:
        """Enhanced language detection"""
        devanagari_count = len(re.findall(r'[\u0900-\u097F]', query))
        tamil_count = len(re.findall(r'[\u0B80-\u0BFF]', query))
        telugu_count = len(re.findall(r'[\u0C00-\u0C7F]', query))
        bengali_count = len(re.findall(r'[\u0980-\u09FF]', query))
        
        if devanagari_count > 0:
            return 'hi'
        elif tamil_count > 0:
            return 'ta'
        elif telugu_count > 0:
            return 'te'
        elif bengali_count > 0:
            return 'bn'
        elif any(word in query.lower() for word in ['kya', 'kaise', 'kab', 'kahan', 'kaun', 'kyun']):
            return 'hinglish'
        else:
            return 'en'
    
    def _extract_entities_enhanced(self, query: str) -> List[str]:
        """Enhanced entity extraction"""
        entities = []
        
        # Locations
        locations = [
            'delhi', 'mumbai', 'bangalore', 'chennai', 'kolkata', 'hyderabad',
            'pune', 'ahmedabad', 'lucknow', 'kanpur', 'nagpur', 'indore',
            'thane', 'bhopal', 'visakhapatnam', 'patna', 'vadodara',
            'ludhiana', 'agra', 'nashik', 'punjab', 'maharashtra',
            'uttar pradesh', 'bihar', 'west bengal', 'tamil nadu',
            'karnataka', 'gujarat', 'rajasthan', 'madhya pradesh'
        ]
        
        # Crops
        crops = [
            'wheat', 'गेहूं', 'rice', 'चावल', 'maize', 'मक्का', 'cotton', 'कपास',
            'potato', 'आलू', 'onion', 'प्याज', 'tomato', 'टमाटर', 'groundnut', 'मूंगफली',
            'soybean', 'सोयाबीन', 'mustard', 'सरसों', 'barley', 'जौ',
            'chickpea', 'चना', 'lentil', 'मसूर', 'pigeon pea', 'अरहर'
        ]
        
        # Numbers
        numbers = re.findall(r'\d+', query)
        
        # Extract entities
        for location in locations:
            if location in query:
                entities.append(location)
        
        for crop in crops:
            if crop in query:
                entities.append(crop)
        
        entities.extend(numbers)
        
        return entities
    
    def _get_context_hints_enhanced(self, category: str, query: str) -> List[str]:
        """Enhanced context hints"""
        hints = []
        
        if 'delhi' in query or 'mumbai' in query:
            hints.append('location-based')
        
        if any(season in query for season in ['season', 'मौसम', 'rabi', 'खरीफ']):
            hints.append('seasonal')
        
        if category == 'farming_agriculture':
            hints.append('agricultural')
        
        if 'price' in query or 'कीमत' in query:
            hints.append('market-related')
        
        if 'today' in query or 'आज' in query:
            hints.append('time-sensitive')
        
        if 'how' in query or 'कैसे' in query:
            hints.append('instructional')
        
        return hints
    
    def _get_subcategory_enhanced(self, category: str, query: str) -> str:
        """Enhanced subcategory detection"""
        subcategories = {
            'farming_agriculture': ['crop_recommendation', 'soil_health', 'pest_control', 'fertilizer_advice', 'irrigation'],
            'general_knowledge': ['geography', 'history', 'science', 'facts', 'trivia'],
            'weather_climate': ['current_weather', 'forecast', 'seasonal_data', 'climate_info'],
            'market_economics': ['commodity_price', 'market_trends', 'trading_info', 'financial_data'],
            'government_policies': ['scheme_information', 'subsidy_details', 'policy_updates', 'regulations'],
            'technology_ai': ['ai_usage', 'software_help', 'technical_support', 'programming'],
            'entertainment_fun': ['humor', 'games', 'casual_chat', 'activities'],
            'education_learning': ['tutorial', 'academic', 'course_info', 'study_help'],
            'health_medical': ['medical_info', 'wellness', 'symptoms', 'treatment'],
            'business_finance': ['entrepreneurship', 'investment', 'financial_planning', 'business_advice']
        }
        
        if category in subcategories:
            for subcat in subcategories[category]:
                if subcat.replace('_', ' ') in query or any(word in query for word in subcat.split('_')):
                    return subcat
            return subcategories[category][0]
        
        return 'general'
    
    def _generate_suggested_response(self, category: str, query: str, language: str) -> str:
        """Generate suggested response based on category"""
        responses = {
            'farming_agriculture': {
                'en': "I'll provide detailed agricultural advice for your farming needs.",
                'hi': "मैं आपकी कृषि जरूरतों के लिए विस्तृत सलाह दूंगा।",
                'hinglish': "Main aapki farming needs ke liye detailed advice dunga."
            },
            'general_knowledge': {
                'en': "I'll help you with general knowledge and factual information.",
                'hi': "मैं आपकी सामान्य ज्ञान और तथ्यात्मक जानकारी में मदद करूंगा।",
                'hinglish': "Main aapki general knowledge mein help karunga."
            },
            'weather_climate': {
                'en': "I'll provide accurate weather information and forecasts.",
                'hi': "मैं आपको सटीक मौसम की जानकारी और पूर्वानुमान दूंगा।",
                'hinglish': "Main aapko accurate weather information dunga."
            },
            'market_economics': {
                'en': "I'll help you with market prices and economic information.",
                'hi': "मैं आपकी बाजार कीमतों और आर्थिक जानकारी में मदद करूंगा।",
                'hinglish': "Main aapki market prices mein help karunga."
            },
            'technology_ai': {
                'en': "I'll assist you with technology and AI-related questions.",
                'hi': "मैं आपकी तकनीक और AI से संबंधित प्रश्नों में मदद करूंगा।",
                'hinglish': "Main aapki technology aur AI questions mein help karunga."
            }
        }
        
        if category in responses and language in responses[category]:
            return responses[category][language]
        else:
            return "I'll help you with your query."
    
    def _get_related_topics(self, category: str) -> List[str]:
        """Get related topics for better context"""
        related_topics = {
            'farming_agriculture': ['crops', 'soil', 'weather', 'irrigation', 'fertilizers'],
            'general_knowledge': ['facts', 'history', 'geography', 'science'],
            'weather_climate': ['forecast', 'temperature', 'rainfall', 'seasons'],
            'market_economics': ['prices', 'trading', 'finance', 'economics'],
            'technology_ai': ['programming', 'software', 'digital', 'automation'],
            'entertainment_fun': ['games', 'humor', 'activities', 'leisure'],
            'education_learning': ['tutorials', 'courses', 'academic', 'study'],
            'health_medical': ['wellness', 'medicine', 'symptoms', 'treatment'],
            'business_finance': ['investment', 'entrepreneurship', 'finance', 'planning']
        }
        
        return related_topics.get(category, ['general'])
    
    def get_training_statistics(self) -> Dict[str, Any]:
        """Get training statistics and performance metrics"""
        return {
            "total_training_examples": len(self.training_examples),
            "categories_covered": len(set(ex['category'] for ex in self.training_examples)),
            "languages_supported": len(set(ex['language'] for ex in self.training_examples)),
            "average_confidence": sum(ex['confidence'] for ex in self.training_examples) / len(self.training_examples),
            "training_data": self.training_dataset,
            "last_updated": datetime.now().isoformat()
        }

# Create global instance
enhanced_google_ai_training = EnhancedGoogleAITraining()
