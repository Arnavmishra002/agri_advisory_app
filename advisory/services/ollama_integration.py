#!/usr/bin/env python3
"""
Ollama Integration for ChatGPT-level Intelligence
Uses Ollama Studio and other open source APIs for comprehensive query understanding
"""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import re
import random

logger = logging.getLogger(__name__)

class OllamaIntegration:
    """Ollama integration for ChatGPT-level intelligence across all domains"""
    
    def __init__(self):
        self.ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.models = {
            'llama3': 'llama3:8b',
            'mistral': 'mistral:7b',
            'codellama': 'codellama:7b',
            'phi3': 'phi3:3.8b',
            'gemma': 'gemma:7b'
        }
        self.current_model = self.models['llama3']
        self.cache = {}
        self.cache_duration = timedelta(hours=1)
        
        # Comprehensive knowledge base for all domains
        self.knowledge_base = self._initialize_knowledge_base()
        
        # Enhanced prompt templates
        self.system_prompts = {
            'general': """You are an advanced AI assistant with comprehensive knowledge across all domains. You can help with:
- General knowledge questions (history, geography, science, facts)
- Technology and programming
- Business and finance
- Health and wellness
- Education and learning
- Entertainment and fun
- Current events and news
- Creative writing and problem solving

Always provide helpful, accurate, and detailed responses. If you don't know something, say so honestly.""",
            
            'agricultural': """You are an expert agricultural advisor with deep knowledge of:
- Crop cultivation and farming techniques
- Soil health and fertilizers
- Weather patterns and climate
- Market prices and economics
- Government schemes and policies
- Pest control and disease management
- Irrigation and water management

Provide practical, actionable advice for farmers.""",
            
            'technical': """You are a technical expert who can help with:
- Programming and software development
- System administration
- Database management
- Web development
- Mobile app development
- DevOps and cloud computing
- AI and machine learning

Provide clear, step-by-step solutions.""",
            
            'creative': """You are a creative assistant who excels at:
- Creative writing and storytelling
- Poetry and literature
- Art and design concepts
- Music and entertainment
- Games and puzzles
- Humor and jokes
- Brainstorming and ideation

Be imaginative, engaging, and entertaining."""
        }
    
    def _initialize_knowledge_base(self) -> Dict[str, Any]:
        """Initialize comprehensive knowledge base"""
        return {
            'domains': [
                'agriculture', 'technology', 'science', 'history', 'geography',
                'business', 'health', 'education', 'entertainment', 'sports',
                'politics', 'culture', 'arts', 'literature', 'philosophy'
            ],
            'languages': ['en', 'hi', 'hinglish', 'ta', 'te', 'bn', 'gu', 'mr'],
            'response_types': [
                'factual', 'explanatory', 'instructional', 'creative',
                'analytical', 'comparative', 'predictive', 'humorous'
            ]
        }
    
    def get_response(self, query: str, language: str = 'en', context: Dict = None) -> Dict[str, Any]:
        """Get ChatGPT-level response for any query"""
        try:
            # Analyze query to determine best approach
            analysis = self._analyze_query(query, language)
            
            # Check cache first
            cache_key = f"ollama_response_{hash(query)}_{language}"
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                if datetime.now() - cached_data['timestamp'] < self.cache_duration:
                    return cached_data['data']
            
            # Determine response strategy
            if analysis['category'] == 'agricultural':
                response = self._get_agricultural_response(query, language, context)
            elif analysis['category'] == 'technical':
                response = self._get_technical_response(query, language, context)
            elif analysis['category'] == 'creative':
                response = self._get_creative_response(query, language, context)
            else:
                response = self._get_general_response(query, language, context)
            
            # Cache the response
            self.cache[cache_key] = {
                'data': response,
                'timestamp': datetime.now()
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error in Ollama integration: {e}")
            return self._get_fallback_response(query, language)
    
    def _analyze_query(self, query: str, language: str) -> Dict[str, Any]:
        """Analyze query to determine category and approach"""
        query_lower = query.lower().strip()
        
        # Agricultural keywords
        agri_keywords = [
            'crop', 'फसल', 'farming', 'खेती', 'agriculture', 'कृषि', 'soil', 'मिट्टी',
            'fertilizer', 'उर्वरक', 'irrigation', 'सिंचाई', 'harvest', 'कटाई',
            'sow', 'बोना', 'plant', 'पौधा', 'seed', 'बीज', 'yield', 'उत्पादन',
            'lagayein', 'लगाएं', 'suggest', 'सुझाव', 'recommend', 'अनुशंसा',
            'pest', 'कीट', 'disease', 'रोग', 'weed', 'खरपतवार', 'organic', 'जैविक',
            'weather', 'मौसम', 'price', 'कीमत', 'market', 'बाजार', 'mandi', 'मंडी'
        ]
        
        # Technical keywords
        tech_keywords = [
            'programming', 'code', 'python', 'javascript', 'java', 'html', 'css',
            'database', 'sql', 'api', 'software', 'app', 'website', 'development',
            'algorithm', 'data structure', 'machine learning', 'ai', 'artificial intelligence',
            'server', 'cloud', 'docker', 'kubernetes', 'git', 'github'
        ]
        
        # Creative keywords
        creative_keywords = [
            'joke', 'जोक', 'fun', 'मजा', 'story', 'कहानी', 'poem', 'कविता',
            'creative', 'imagine', 'write', 'लिखना', 'draw', 'design', 'art',
            'music', 'song', 'game', 'खेल', 'entertainment', 'मनोरंजन'
        ]
        
        # Calculate scores
        agri_score = sum(1 for kw in agri_keywords if kw in query_lower)
        tech_score = sum(1 for kw in tech_keywords if kw in query_lower)
        creative_score = sum(1 for kw in creative_keywords if kw in query_lower)
        
        # Determine category
        if agri_score > tech_score and agri_score > creative_score:
            category = 'agricultural'
            confidence = min(agri_score / 3, 0.95)
        elif tech_score > creative_score:
            category = 'technical'
            confidence = min(tech_score / 3, 0.95)
        elif creative_score > 0:
            category = 'creative'
            confidence = min(creative_score / 3, 0.95)
        else:
            category = 'general'
            confidence = 0.7
        
        return {
            'category': category,
            'confidence': confidence,
            'language': language,
            'query_type': self._get_query_type(query_lower),
            'entities': self._extract_entities(query_lower),
            'intent': self._get_intent(query_lower)
        }
    
    def _get_query_type(self, query: str) -> str:
        """Determine the type of query"""
        if any(word in query for word in ['what', 'क्या', 'what is', 'क्या है']):
            return 'factual'
        elif any(word in query for word in ['how', 'कैसे', 'how to', 'कैसे करें']):
            return 'instructional'
        elif any(word in query for word in ['why', 'क्यों', 'why is', 'क्यों है']):
            return 'explanatory'
        elif any(word in query for word in ['when', 'कब', 'when is', 'कब है']):
            return 'temporal'
        elif any(word in query for word in ['where', 'कहां', 'where is', 'कहां है']):
            return 'locational'
        elif any(word in query for word in ['who', 'कौन', 'who is', 'कौन है']):
            return 'personal'
        else:
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
    
    def _get_intent(self, query: str) -> str:
        """Determine user intent"""
        if any(word in query for word in ['help', 'मदद', 'assist', 'सहायता']):
            return 'help_request'
        elif any(word in query for word in ['explain', 'समझाएं', 'describe', 'वर्णन']):
            return 'explanation_request'
        elif any(word in query for word in ['solve', 'हल', 'fix', 'ठीक']):
            return 'problem_solving'
        elif any(word in query for word in ['create', 'बनाएं', 'make', 'बनाना']):
            return 'creation_request'
        else:
            return 'information_request'
    
    def _get_general_response(self, query: str, language: str, context: Dict = None) -> Dict[str, Any]:
        """Get general response using Ollama"""
        try:
            # Try Ollama first
            ollama_response = self._call_ollama(query, 'general', language)
            if ollama_response:
                return {
                    'response': ollama_response,
                    'source': 'ollama',
                    'confidence': 0.9,
                    'language': language,
                    'category': 'general',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Fallback to other open source APIs
            return self._call_open_source_apis(query, language)
            
        except Exception as e:
            logger.error(f"Error in general response: {e}")
            return self._get_fallback_response(query, language)
    
    def _get_agricultural_response(self, query: str, language: str, context: Dict = None) -> Dict[str, Any]:
        """Get agricultural response using Ollama"""
        try:
            # Try Ollama with agricultural context
            ollama_response = self._call_ollama(query, 'agricultural', language)
            if ollama_response:
                return {
                    'response': ollama_response,
                    'source': 'ollama_agricultural',
                    'confidence': 0.95,
                    'language': language,
                    'category': 'agricultural',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Fallback to agricultural knowledge base
            return self._get_agricultural_fallback(query, language)
            
        except Exception as e:
            logger.error(f"Error in agricultural response: {e}")
            return self._get_agricultural_fallback(query, language)
    
    def _get_technical_response(self, query: str, language: str, context: Dict = None) -> Dict[str, Any]:
        """Get technical response using Ollama"""
        try:
            # Try Ollama with technical context
            ollama_response = self._call_ollama(query, 'technical', language)
            if ollama_response:
                return {
                    'response': ollama_response,
                    'source': 'ollama_technical',
                    'confidence': 0.9,
                    'language': language,
                    'category': 'technical',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Fallback to technical knowledge base
            return self._get_technical_fallback(query, language)
            
        except Exception as e:
            logger.error(f"Error in technical response: {e}")
            return self._get_technical_fallback(query, language)
    
    def _get_creative_response(self, query: str, language: str, context: Dict = None) -> Dict[str, Any]:
        """Get creative response using Ollama"""
        try:
            # Try Ollama with creative context
            ollama_response = self._call_ollama(query, 'creative', language)
            if ollama_response:
                return {
                    'response': ollama_response,
                    'source': 'ollama_creative',
                    'confidence': 0.85,
                    'language': language,
                    'category': 'creative',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Fallback to creative responses
            return self._get_creative_fallback(query, language)
            
        except Exception as e:
            logger.error(f"Error in creative response: {e}")
            return self._get_creative_fallback(query, language)
    
    def _call_ollama(self, query: str, context_type: str, language: str) -> Optional[str]:
        """Call Ollama API for response"""
        try:
            # Check if Ollama is available
            health_check = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
            if health_check.status_code != 200:
                logger.warning("Ollama not available, using fallback")
                return None
            
            # Prepare the prompt
            system_prompt = self.system_prompts.get(context_type, self.system_prompts['general'])
            
            if language == 'hi':
                system_prompt += "\n\nPlease respond in Hindi (हिंदी) unless specifically asked otherwise."
            elif language == 'hinglish':
                system_prompt += "\n\nPlease respond in Hinglish (Hindi-English mix) unless specifically asked otherwise."
            
            # Prepare the request
            url = f"{self.ollama_base_url}/api/generate"
            data = {
                "model": self.current_model,
                "prompt": f"{system_prompt}\n\nUser Query: {query}",
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 1000
                }
            }
            
            response = requests.post(url, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if 'response' in result:
                return result['response'].strip()
            
            return None
            
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return None
    
    def _call_open_source_apis(self, query: str, language: str) -> Dict[str, Any]:
        """Call other open source APIs as fallback"""
        try:
            # Try Hugging Face Inference API
            hf_response = self._call_huggingface(query, language)
            if hf_response:
                return {
                    'response': hf_response,
                    'source': 'huggingface',
                    'confidence': 0.8,
                    'language': language,
                    'category': 'general',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Try other APIs
            return self._get_comprehensive_fallback(query, language)
            
        except Exception as e:
            logger.error(f"Error in open source APIs: {e}")
            return self._get_comprehensive_fallback(query, language)
    
    def _call_huggingface(self, query: str, language: str) -> Optional[str]:
        """Call Hugging Face Inference API"""
        try:
            # Use a free model from Hugging Face
            url = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"
            headers = {
                "Authorization": f"Bearer {os.getenv('HUGGINGFACE_TOKEN', '')}"
            }
            
            data = {
                "inputs": query,
                "parameters": {
                    "max_length": 200,
                    "temperature": 0.7
                }
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get('generated_text', '').strip()
            
            return None
            
        except Exception as e:
            logger.error(f"Error calling Hugging Face: {e}")
            return None
    
    def _get_comprehensive_fallback(self, query: str, language: str) -> Dict[str, Any]:
        """Comprehensive fallback response system"""
        query_lower = query.lower().strip()
        
        # General knowledge responses
        if any(word in query_lower for word in ['what is', 'क्या है', 'what are', 'क्या हैं']):
            return self._handle_what_is_query(query, language)
        elif any(word in query_lower for word in ['how to', 'कैसे करें', 'how do', 'कैसे करते हैं']):
            return self._handle_how_to_query(query, language)
        elif any(word in query_lower for word in ['who is', 'कौन है', 'who are', 'कौन हैं']):
            return self._handle_who_is_query(query, language)
        elif any(word in query_lower for word in ['when is', 'कब है', 'when was', 'कब था']):
            return self._handle_when_query(query, language)
        elif any(word in query_lower for word in ['where is', 'कहां है', 'where are', 'कहां हैं']):
            return self._handle_where_query(query, language)
        elif any(word in query_lower for word in ['why is', 'क्यों है', 'why are', 'क्यों हैं']):
            return self._handle_why_query(query, language)
        else:
            return self._get_general_fallback(query, language)
    
    def _handle_what_is_query(self, query: str, language: str) -> Dict[str, Any]:
        """Handle 'what is' queries"""
        query_lower = query.lower().strip()
        
        # Common knowledge responses
        responses = {
            'artificial intelligence': {
                'en': "Artificial Intelligence (AI) is a branch of computer science that aims to create machines that can perform tasks that typically require human intelligence, such as learning, reasoning, and problem-solving.",
                'hi': "कृत्रिम बुद्धिमत्ता (AI) कंप्यूटर विज्ञान की एक शाखा है जो ऐसी मशीनें बनाने का लक्ष्य रखती है जो मानव बुद्धिमत्ता की आवश्यकता वाले कार्य कर सकें।"
            },
            'machine learning': {
                'en': "Machine Learning is a subset of AI that enables computers to learn and improve from experience without being explicitly programmed for every task.",
                'hi': "मशीन लर्निंग AI का एक उपसमूह है जो कंप्यूटर को अनुभव से सीखने और सुधारने में सक्षम बनाता है।"
            },
            'python': {
                'en': "Python is a high-level, interpreted programming language known for its simplicity and readability. It's widely used in web development, data science, AI, and automation.",
                'hi': "Python एक उच्च-स्तरीय, व्याख्या की गई प्रोग्रामिंग भाषा है जो अपनी सरलता और पठनीयता के लिए जानी जाती है।"
            }
        }
        
        for key, response in responses.items():
            if key in query_lower:
                return {
                    'response': response.get(language, response['en']),
                    'source': 'knowledge_base',
                    'confidence': 0.9,
                    'language': language,
                    'category': 'general_knowledge',
                    'timestamp': datetime.now().isoformat()
                }
        
        return self._get_general_fallback(query, language)
    
    def _handle_how_to_query(self, query: str, language: str) -> Dict[str, Any]:
        """Handle 'how to' queries"""
        query_lower = query.lower().strip()
        
        if 'learn programming' in query_lower or 'programming सीखें' in query_lower:
            response = {
                'en': "To learn programming:\n1. Choose a language (Python recommended for beginners)\n2. Start with basic syntax and concepts\n3. Practice coding daily\n4. Build small projects\n5. Join coding communities\n6. Read code written by others\n7. Take online courses or tutorials",
                'hi': "प्रोग्रामिंग सीखने के लिए:\n1. एक भाषा चुनें (शुरुआती के लिए Python सुझाव)\n2. बुनियादी सिंटैक्स और अवधारणाओं से शुरू करें\n3. रोजाना कोडिंग का अभ्यास करें\n4. छोटे प्रोजेक्ट बनाएं\n5. कोडिंग समुदायों में शामिल हों\n6. दूसरों द्वारा लिखे गए कोड पढ़ें\n7. ऑनलाइन कोर्स या ट्यूटोरियल लें"
            }
        elif 'start business' in query_lower or 'व्यापार शुरू करें' in query_lower:
            response = {
                'en': "To start a business:\n1. Identify a market need\n2. Research your target audience\n3. Create a business plan\n4. Secure funding\n5. Register your business\n6. Build your product/service\n7. Market your business\n8. Launch and iterate",
                'hi': "व्यापार शुरू करने के लिए:\n1. बाजार की जरूरत की पहचान करें\n2. अपने लक्षित दर्शकों पर शोध करें\n3. व्यापार योजना बनाएं\n4. धन सुरक्षित करें\n5. अपना व्यापार पंजीकृत करें\n6. अपना उत्पाद/सेवा बनाएं\n7. अपने व्यापार का विपणन करें\n8. लॉन्च करें और सुधार करें"
            }
        else:
            return self._get_general_fallback(query, language)
        
        return {
            'response': response.get(language, response['en']),
            'source': 'knowledge_base',
            'confidence': 0.85,
            'language': language,
            'category': 'instructional',
            'timestamp': datetime.now().isoformat()
        }
    
    def _handle_who_is_query(self, query: str, language: str) -> Dict[str, Any]:
        """Handle 'who is' queries"""
        query_lower = query.lower().strip()
        
        responses = {
            'elon musk': {
                'en': "Elon Musk is a South African-born American entrepreneur and business magnate. He is the CEO of Tesla and SpaceX, and has been involved in various other ventures including Neuralink and The Boring Company.",
                'hi': "एलन मस्क एक दक्षिण अफ्रीकी मूल के अमेरिकी उद्यमी और व्यापारिक प्रतिभा हैं। वे Tesla और SpaceX के CEO हैं।"
            },
            'bill gates': {
                'en': "Bill Gates is an American business magnate, software developer, and philanthropist. He co-founded Microsoft Corporation and is known for his philanthropic work through the Bill & Melinda Gates Foundation.",
                'hi': "बिल गेट्स एक अमेरिकी व्यापारिक प्रतिभा, सॉफ्टवेयर डेवलपर और परोपकारी हैं। उन्होंने Microsoft Corporation की सह-स्थापना की।"
            }
        }
        
        for key, response in responses.items():
            if key in query_lower:
                return {
                    'response': response.get(language, response['en']),
                    'source': 'knowledge_base',
                    'confidence': 0.9,
                    'language': language,
                    'category': 'biographical',
                    'timestamp': datetime.now().isoformat()
                }
        
        return self._get_general_fallback(query, language)
    
    def _handle_when_query(self, query: str, language: str) -> Dict[str, Any]:
        """Handle 'when' queries"""
        return self._get_general_fallback(query, language)
    
    def _handle_where_query(self, query: str, language: str) -> Dict[str, Any]:
        """Handle 'where' queries"""
        return self._get_general_fallback(query, language)
    
    def _handle_why_query(self, query: str, language: str) -> Dict[str, Any]:
        """Handle 'why' queries"""
        return self._get_general_fallback(query, language)
    
    def _get_general_fallback(self, query: str, language: str) -> Dict[str, Any]:
        """General fallback response"""
        if language in ['hi', 'hindi']:
            response = f"मैं आपके प्रश्न '{query}' को समझने की कोशिश कर रहा हूं। मैं एक बहु-क्षेत्रीय AI सहायक हूं जो कृषि, तकनीक, सामान्य ज्ञान और कई अन्य विषयों में मदद कर सकता हूं। कृपया अपना प्रश्न और विस्तार से पूछें।"
        elif language == 'hinglish':
            response = f"Main aapke question '{query}' ko samajhne ki koshish kar raha hun. Main ek multi-domain AI assistant hun jo agriculture, technology, general knowledge aur kai aur subjects mein help kar sakta hun. Please apna question detail mein pucho."
        else:
            response = f"I'm trying to understand your question '{query}'. I'm a multi-domain AI assistant that can help with agriculture, technology, general knowledge, and many other subjects. Please ask your question in more detail."
        
        return {
            'response': response,
            'source': 'fallback',
            'confidence': 0.6,
            'language': language,
            'category': 'general',
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_agricultural_fallback(self, query: str, language: str) -> Dict[str, Any]:
        """Agricultural fallback response"""
        if language == 'hi':
            response = f"आपका प्रश्न कृषि से संबंधित है। मैं आपको विस्तृत कृषि सलाह दूंगा। कृपया अपना स्थान, मिट्टी का प्रकार और सीजन बताएं ताकि मैं आपको सटीक सलाह दे सकूं।"
        else:
            response = f"Your query is related to agriculture. I'll provide detailed farming advice. Please share your location, soil type, and season so I can give you accurate recommendations."
        
        return {
            'response': response,
            'source': 'agricultural_fallback',
            'confidence': 0.8,
            'language': language,
            'category': 'agricultural',
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_technical_fallback(self, query: str, language: str) -> Dict[str, Any]:
        """Technical fallback response"""
        if language == 'hi':
            response = f"आपका प्रश्न तकनीकी है। मैं आपकी तकनीकी समस्याओं में मदद कर सकता हूं। कृपया अपनी समस्या को और विस्तार से बताएं।"
        else:
            response = f"Your query is technical. I can help you with technical problems. Please provide more details about your issue."
        
        return {
            'response': response,
            'source': 'technical_fallback',
            'confidence': 0.8,
            'language': language,
            'category': 'technical',
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_creative_fallback(self, query: str, language: str) -> Dict[str, Any]:
        """Creative fallback response"""
        if language == 'hi':
            response = f"आपका प्रश्न रचनात्मक है। मैं आपकी रचनात्मक जरूरतों में मदद कर सकता हूं। कृपया बताएं कि आप क्या चाहते हैं।"
        else:
            response = f"Your query is creative. I can help you with creative needs. Please tell me what you're looking for."
        
        return {
            'response': response,
            'source': 'creative_fallback',
            'confidence': 0.8,
            'language': language,
            'category': 'creative',
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_fallback_response(self, query: str, language: str) -> Dict[str, Any]:
        """Ultimate fallback response"""
        if language in ['hi', 'hindi']:
            response = "क्षमा करें, मुझे आपकी बात समझ नहीं आई। कृपया फिर से प्रयास करें।"
        elif language == 'hinglish':
            response = "Sorry bhai, main aapki baat samajh nahi paya. Please phir se try karo."
        else:
            response = "Sorry, I couldn't understand your request. Please try again."
        
        return {
            'response': response,
            'source': 'error_fallback',
            'confidence': 0.3,
            'language': language,
            'category': 'error',
            'timestamp': datetime.now().isoformat()
        }
    
    def get_available_models(self) -> List[str]:
        """Get list of available Ollama models"""
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return []
    
    def set_model(self, model_name: str) -> bool:
        """Set the current model"""
        try:
            available_models = self.get_available_models()
            if model_name in available_models:
                self.current_model = model_name
                return True
            return False
        except Exception as e:
            logger.error(f"Error setting model: {e}")
            return False
    
    def generate_response(self, query: str, language: str = 'en') -> str:
        """Generate response using Ollama for general queries with improved fallback"""
        try:
            # Quick check if Ollama is available (reduced timeout)
            response = self._call_ollama_api(query, language, timeout=5)
            if response and len(response) > 50:
                logger.info("Using Ollama for response")
                return response
            
            # Fallback to enhanced knowledge base
            logger.info("Ollama not available, using enhanced fallback")
            return self._get_enhanced_knowledge_base_response(query, language)
            
        except Exception as e:
            logger.warning(f"Ollama failed, using fallback: {e}")
            return self._get_enhanced_knowledge_base_response(query, language)
    
    def _call_ollama_api(self, query: str, language: str, timeout: int = 10) -> str:
        """Call Ollama API directly with ChatGPT-like intelligence"""
        try:
            # Enhanced ChatGPT-like system prompts for ALL types of queries
            if language in ['hi', 'hinglish']:
                system_prompt = """आप कृषिमित्र AI हैं - एक बहुत ही बुद्धिमान और सहायक AI सहायक। आपके पास व्यापक ज्ञान है और आप सभी विषयों पर सही, विस्तृत और उपयोगी जवाब दे सकते हैं:

🌍 सामान्य ज्ञान: इतिहास, भूगोल, विज्ञान, गणित, साहित्य
💻 तकनीक: प्रोग्रामिंग, कंप्यूटर, सॉफ्टवेयर, AI/ML
🏥 स्वास्थ्य: चिकित्सा, पोषण, फिटनेस
💰 व्यापार: अर्थशास्त्र, वित्त, निवेश, मार्केटिंग
🎭 मनोरंजन: फिल्में, संगीत, खेल, कला
📚 शिक्षा: शिक्षण, सीखना, शोध
🌾 कृषि: खेती, फसलें, मौसम, बाजार भाव

आप बातचीत में प्राकृतिक, मैत्रीपूर्ण और सहायक हैं। हिंदी में उत्तर दें और जब भी संभव हो उदाहरण और विस्तृत जानकारी प्रदान करें।"""
            else:
                system_prompt = """You are Krishimitra AI - a highly intelligent and helpful AI assistant. You have extensive knowledge across all domains and can provide accurate, detailed, and useful responses on any topic:

🌍 General Knowledge: History, Geography, Science, Mathematics, Literature
💻 Technology: Programming, Computers, Software, AI/ML, Web Development
🏥 Health: Medicine, Nutrition, Fitness, Wellness
💰 Business: Economics, Finance, Investment, Marketing
🎭 Entertainment: Movies, Music, Sports, Arts
📚 Education: Teaching, Learning, Research
🌾 Agriculture: Farming, Crops, Weather, Market Prices

You are natural, friendly, and helpful in conversation. Provide detailed explanations with examples whenever possible. Be conversational and engaging like ChatGPT."""
            
            payload = {
                "model": self.current_model,
                "prompt": f"{system_prompt}\n\nUser: {query}\n\nAssistant:",
                "stream": False,
                "options": {
                    "temperature": 0.8,
                    "top_p": 0.95,
                    "max_tokens": 800,
                    "repeat_penalty": 1.1,
                    "stop": ["User:", "Human:", "Human"]
                }
            }
            
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json=payload,
                timeout=timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('response', '').strip()
            else:
                logger.warning(f"Ollama API returned status {response.status_code}")
                return ""
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Ollama API request failed: {e}")
            return ""
        except Exception as e:
            logger.error(f"Error calling Ollama API: {e}")
            return ""
    
    def _get_knowledge_base_response(self, query: str, language: str) -> str:
        """Get response from knowledge base"""
        query_lower = query.lower()
        
        # AI and technology queries
        if any(keyword in query_lower for keyword in ['artificial intelligence', 'ai', 'machine learning', 'technology']):
            if language in ['hi', 'hinglish']:
                return """🤖 कृत्रिम बुद्धिमत्ता (AI) के बारे में:

AI एक ऐसी तकनीक है जो कंप्यूटर को मानव की तरह सोचने और सीखने की क्षमता देती है।

🌟 **AI के मुख्य प्रकार**:
• Machine Learning - डेटा से सीखना
• Deep Learning - मानव मस्तिष्क की नकल
• Natural Language Processing - भाषा समझना

💡 **AI के उपयोग**:
• Agriculture - फसल निगरानी और पूर्वानुमान
• Healthcare - रोग निदान
• Finance - धोखाधड़ी का पता लगाना
• Education - व्यक्तिगत सीखने की सुविधा

🚀 **भविष्य**: AI तेजी से विकसित हो रहा है और हमारे जीवन को बेहतर बना रहा है।"""
            else:
                return """🤖 Artificial Intelligence (AI) Overview:

Artificial Intelligence is technology that enables computers to think and learn like humans. It's based on machine learning, deep learning, and neural networks.

🌟 **Main Types of AI**:
• Machine Learning - Learning from data
• Deep Learning - Mimicking human brain
• Natural Language Processing - Understanding language

💡 **AI Applications**:
• Agriculture - Crop monitoring and forecasting
• Healthcare - Disease diagnosis
• Finance - Fraud detection
• Education - Personalized learning

🚀 **Future**: AI is rapidly evolving and improving our lives across all sectors."""
        
        # Geography queries
        elif any(keyword in query_lower for keyword in ['capital', 'राजधानी', 'country', 'देश']):
            if language in ['hi', 'hinglish']:
                return """🗺️ भारत की राजधानी के बारे में:

भारत की राजधानी **नई दिल्ली** है।

📍 **मुख्य तथ्य**:
• राजधानी: नई दिल्ली
• राज्य: दिल्ली (केंद्र शासित प्रदेश)
• जनसंख्या: लगभग 3.3 करोड़
• क्षेत्रफल: 1,484 वर्ग किमी

🏛️ **महत्वपूर्ण स्थान**:
• राष्ट्रपति भवन
• संसद भवन
• सुप्रीम कोर्ट
• रेड फोर्ट

🌟 **इतिहास**: 1911 में ब्रिटिश राज में राजधानी बनी।"""
            else:
                return """🗺️ About India's Capital:

India's capital is **New Delhi**.

📍 **Key Facts**:
• Capital: New Delhi
• State: Delhi (Union Territory)
• Population: Approximately 33 million
• Area: 1,484 sq km

🏛️ **Important Places**:
• Rashtrapati Bhavan
• Parliament House
• Supreme Court
• Red Fort

🌟 **History**: Became capital in 1911 during British rule."""
        
        # Default response
        else:
            if language in ['hi', 'hinglish']:
                return "मैं एक AI सहायक हूं। मैं आपकी सहायता कर सकता हूं। कृपया अपना प्रश्न स्पष्ट रूप से पूछें।"
            else:
                return "I am an AI assistant. I can help you with various questions. Please ask your question clearly."
    
    def _get_enhanced_knowledge_base_response(self, query: str, language: str) -> str:
        """Get enhanced ChatGPT-like response from comprehensive knowledge base"""
        query_lower = query.lower()
        
        # Enhanced comprehensive responses with ChatGPT-like intelligence
        responses = {
            # General greetings and introductions
            'hello': {
                'en': "Hello! 👋 I'm Krishimitra AI, your intelligent agricultural assistant. I'm here to help you with everything related to farming, crops, weather, market prices, government schemes, and much more! I can provide real-time data and expert advice. What would you like to know today?",
                'hi': "नमस्ते! 👋 मैं कृषिमित्र AI हूं, आपका बुद्धिमान कृषि सहायक। मैं यहां खेती, फसल, मौसम, बाजार भाव, सरकारी योजनाओं और बहुत कुछ में आपकी मदद के लिए हूं! मैं वास्तविक समय का डेटा और विशेषज्ञ सलाह प्रदान कर सकता हूं। आज आप क्या जानना चाहते हैं?"
            },
            'hi': {
                'en': "Hi there! 😊 I'm Krishimitra AI, your friendly agricultural assistant. I'm excited to help you with farming questions, crop advice, weather updates, market prices, and any other agricultural information you need. How can I assist you today?",
                'hi': "हाय! 😊 मैं कृषिमित्र AI हूं, आपका मैत्रीपूर्ण कृषि सहायक। मैं खेती के सवालों, फसल सलाह, मौसम अपडेट, बाजार भाव और आपके लिए आवश्यक किसी भी अन्य कृषि जानकारी में आपकी मदद करने के लिए उत्साहित हूं। आज मैं आपकी कैसे मदद कर सकता हूं?"
            },
            'who are you': {
                'en': "I'm Krishimitra AI! 🤖✨ I'm your intelligent agricultural assistant powered by advanced AI technology. I specialize in providing real-time farming advice, crop recommendations, weather forecasts, market prices, and government scheme information. I can help with everything from basic farming questions to complex agricultural strategies. Think of me as your personal farming consultant available 24/7!",
                'hi': "मैं कृषिमित्र AI हूं! 🤖✨ मैं उन्नत AI तकनीक से संचालित आपका बुद्धिमान कृषि सहायक हूं। मैं वास्तविक समय की खेती सलाह, फसल सुझाव, मौसम पूर्वानुमान, बाजार भाव और सरकारी योजना की जानकारी प्रदान करने में विशेषज्ञ हूं। मैं बुनियादी खेती के सवालों से लेकर जटिल कृषि रणनीतियों तक सब में मदद कर सकता हूं। मुझे अपना व्यक्तिगत खेती सलाहकार समझें जो 24/7 उपलब्ध है!"
            },
            # Technology questions with ChatGPT-like depth
            'artificial intelligence': {
                'en': "Artificial Intelligence (AI) is fascinating! 🤖 It's technology that enables computers to think, learn, and make decisions like humans. In agriculture, AI is revolutionizing farming through:\n\n• **Crop Prediction**: Analyzing weather patterns and soil conditions to predict optimal planting times\n• **Pest Detection**: Using computer vision to identify diseases and pests early\n• **Weather Forecasting**: Providing hyper-local weather predictions for better farming decisions\n• **Precision Agriculture**: Optimizing water, fertilizer, and pesticide usage\n• **Yield Optimization**: Maximizing crop production while minimizing environmental impact\n\nAI is making farming smarter, more sustainable, and more profitable! 🌱",
                'hi': "कृत्रिम बुद्धिमत्ता (AI) बहुत रोमांचक है! 🤖 यह एक तकनीक है जो कंप्यूटर को मानव की तरह सोचने, सीखने और निर्णय लेने में सक्षम बनाती है। कृषि में, AI निम्नलिखित तरीकों से खेती में क्रांति ला रहा है:\n\n• **फसल भविष्यवाणी**: मौसम पैटर्न और मिट्टी की स्थिति का विश्लेषण करके इष्टतम बुवाई समय की भविष्यवाणी\n• **कीट पहचान**: रोगों और कीटों की जल्दी पहचान के लिए कंप्यूटर विजन का उपयोग\n• **मौसम पूर्वानुमान**: बेहतर खेती निर्णयों के लिए हाइपर-स्थानीय मौसम पूर्वानुमान\n• **सटीक कृषि**: पानी, उर्वरक और कीटनाशक के उपयोग को अनुकूलित करना\n• **उपज अनुकूलन**: पर्यावरणीय प्रभाव को कम करते हुए फसल उत्पादन को अधिकतम करना\n\nAI खेती को अधिक स्मार्ट, टिकाऊ और लाभदायक बना रहा है! 🌱"
            },
            'machine learning': {
                'en': "Machine Learning is incredible! 🧠 It's a subset of AI that enables systems to automatically learn and improve from experience without being explicitly programmed. In agriculture, ML is transforming farming:\n\n• **Predictive Analytics**: Forecasting crop yields based on historical data and current conditions\n• **Soil Analysis**: Analyzing soil composition and recommending optimal nutrients\n• **Disease Detection**: Identifying plant diseases from images with high accuracy\n• **Precision Farming**: Optimizing irrigation, fertilization, and pest control\n• **Market Prediction**: Predicting crop prices and market trends\n\nMachine Learning is like having a farming expert that never stops learning and improving! 📈",
                'hi': "मशीन लर्निंग अविश्वसनीय है! 🧠 यह AI का एक उपसमुच्चय है जो सिस्टम को स्पष्ट रूप से प्रोग्राम किए बिना अनुभव से स्वचालित रूप से सीखने और सुधारने में सक्षम बनाता है। कृषि में, ML खेती को बदल रहा है:\n\n• **भविष्यवाणी विश्लेषण**: ऐतिहासिक डेटा और वर्तमान स्थितियों के आधार पर फसल उपज की भविष्यवाणी\n• **मिट्टी विश्लेषण**: मिट्टी की संरचना का विश्लेषण और इष्टतम पोषक तत्वों की सिफारिश\n• **रोग पहचान**: उच्च सटीकता के साथ छवियों से पौधों के रोगों की पहचान\n• **सटीक खेती**: सिंचाई, उर्वरीकरण और कीट नियंत्रण को अनुकूलित करना\n• **बाजार भविष्यवाणी**: फसल कीमतों और बाजार रुझानों की भविष्यवाणी\n\nमशीन लर्निंग एक खेती विशेषज्ञ की तरह है जो कभी सीखना और सुधारना बंद नहीं करता! 📈"
            },
            # Geography questions
            'capital of india': {
                'en': "The capital of India is New Delhi. It's located in the National Capital Territory of Delhi and serves as the political and administrative center of India.",
                'hi': "भारत की राजधानी नई दिल्ली है। यह दिल्ली के राष्ट्रीय राजधानी क्षेत्र में स्थित है और भारत के राजनीतिक और प्रशासनिक केंद्र के रूप में कार्य करता है।"
            },
            'prime minister': {
                'en': "The current Prime Minister of India is Narendra Modi. He has been serving as Prime Minister since 2014 and is a member of the Bharatiya Janata Party (BJP).",
                'hi': "भारत के वर्तमान प्रधानमंत्री नरेंद्र मोदी हैं। वह 2014 से प्रधानमंत्री के रूप में सेवा कर रहे हैं और भारतीय जनता पार्टी (भाजपा) के सदस्य हैं।"
            },
            # Programming questions
            'programming': {
                'en': "Programming is the process of creating instructions for computers to follow. Popular languages include Python (great for beginners), JavaScript (for web development), Java (for enterprise applications), and C++ (for system programming). Start with Python for agriculture-related applications!",
                'hi': "प्रोग्रामिंग कंप्यूटर के लिए निर्देश बनाने की प्रक्रिया है। लोकप्रिय भाषाओं में Python (शुरुआती के लिए बेहतरीन), JavaScript (वेब डेवलपमेंट के लिए), Java (एंटरप्राइज एप्लिकेशन के लिए), और C++ (सिस्टम प्रोग्रामिंग के लिए) शामिल हैं। कृषि संबंधी एप्लिकेशन के लिए Python से शुरुआत करें!"
            },
            # Science questions
            'photosynthesis': {
                'en': "Photosynthesis is the process by which plants convert light energy from the sun into chemical energy (glucose). Plants use carbon dioxide from air, water from soil, and sunlight to produce glucose and release oxygen. This is essential for plant growth and our oxygen supply.",
                'hi': "प्रकाश संश्लेषण वह प्रक्रिया है जिसके द्वारा पौधे सूर्य से प्रकाश ऊर्जा को रासायनिक ऊर्जा (ग्लूकोज) में परिवर्तित करते हैं। पौधे हवा से कार्बन डाइऑक्साइड, मिट्टी से पानी, और सूर्य के प्रकाश का उपयोग करके ग्लूकोज का उत्पादन करते हैं और ऑक्सीजन छोड़ते हैं। यह पौधों के विकास और हमारी ऑक्सीजन आपूर्ति के लिए आवश्यक है।"
            }
        }
        
        # Check for specific keywords and return appropriate response
        for key, response in responses.items():
            if key in query_lower:
                return response.get(language, response.get('en', ""))
        
        # Check for partial matches
        if any(word in query_lower for word in ['who is', 'कौन है']):
            if language in ['hi', 'hinglish']:
                return "कृपया विशिष्ट व्यक्ति या विषय का नाम बताएं। मैं आपको उसके बारे में जानकारी दे सकूंगा।"
            else:
                return "Please specify the person or subject you're asking about. I can provide information about them."
        
        if any(word in query_lower for word in ['what is', 'क्या है']):
            if language in ['hi', 'hinglish']:
                return "कृपया विशिष्ट विषय या अवधारणा का नाम बताएं। मैं आपको उसके बारे में विस्तृत जानकारी दे सकूंगा।"
            else:
                return "Please specify the subject or concept you're asking about. I can provide detailed information about it."
        
        # Default intelligent response
        if language in ['hi', 'hinglish']:
            return "मैं कृषिमित्र AI हूं, आपका बुद्धिमान कृषि सहायक। मैं कृषि, फसल, मौसम, सरकारी योजनाओं के साथ-साथ सामान्य ज्ञान के प्रश्नों का भी उत्तर दे सकता हूं। आप क्या जानना चाहते हैं?"
        else:
            return "I'm Krishimitra AI, your intelligent agricultural assistant. I can help with agriculture, crops, weather, government schemes, and also answer general knowledge questions. What would you like to know?"

    @property
    def api_url(self) -> str:
        """Get API URL - property expected by tests"""
        return self.ollama_base_url
    
    def _generate_prompt(self, query: str, language: str = 'en') -> str:
        """Generate prompt for query - method expected by tests"""
        try:
            if language == 'hi':
                return f"कृपया इस प्रश्न का उत्तर दें: {query}"
            else:
                return f"Please answer this question: {query}"
        except Exception as e:
            logger.error(f"Error generating prompt: {e}")
            return f"Answer: {query}"

# Create global instance
ollama_integration = OllamaIntegration()



#!/usr/bin/env python3
"""
Ollama Integration for ChatGPT-level Intelligence
Uses Ollama Studio and other open source APIs for comprehensive query understanding
"""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import re
import random

logger = logging.getLogger(__name__)

class OllamaIntegration:
    """Ollama integration for ChatGPT-level intelligence across all domains"""
    
    def __init__(self):
        self.ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.models = {
            'llama3': 'llama3:8b',
            'mistral': 'mistral:7b',
            'codellama': 'codellama:7b',
            'phi3': 'phi3:3.8b',
            'gemma': 'gemma:7b'
        }
        self.current_model = self.models['llama3']
        self.cache = {}
        self.cache_duration = timedelta(hours=1)
        
        # Comprehensive knowledge base for all domains
        self.knowledge_base = self._initialize_knowledge_base()
        
        # Enhanced prompt templates
        self.system_prompts = {
            'general': """You are an advanced AI assistant with comprehensive knowledge across all domains. You can help with:
- General knowledge questions (history, geography, science, facts)
- Technology and programming
- Business and finance
- Health and wellness
- Education and learning
- Entertainment and fun
- Current events and news
- Creative writing and problem solving

Always provide helpful, accurate, and detailed responses. If you don't know something, say so honestly.""",
            
            'agricultural': """You are an expert agricultural advisor with deep knowledge of:
- Crop cultivation and farming techniques
- Soil health and fertilizers
- Weather patterns and climate
- Market prices and economics
- Government schemes and policies
- Pest control and disease management
- Irrigation and water management

Provide practical, actionable advice for farmers.""",
            
            'technical': """You are a technical expert who can help with:
- Programming and software development
- System administration
- Database management
- Web development
- Mobile app development
- DevOps and cloud computing
- AI and machine learning

Provide clear, step-by-step solutions.""",
            
            'creative': """You are a creative assistant who excels at:
- Creative writing and storytelling
- Poetry and literature
- Art and design concepts
- Music and entertainment
- Games and puzzles
- Humor and jokes
- Brainstorming and ideation

Be imaginative, engaging, and entertaining."""
        }
    
    def _initialize_knowledge_base(self) -> Dict[str, Any]:
        """Initialize comprehensive knowledge base"""
        return {
            'domains': [
                'agriculture', 'technology', 'science', 'history', 'geography',
                'business', 'health', 'education', 'entertainment', 'sports',
                'politics', 'culture', 'arts', 'literature', 'philosophy'
            ],
            'languages': ['en', 'hi', 'hinglish', 'ta', 'te', 'bn', 'gu', 'mr'],
            'response_types': [
                'factual', 'explanatory', 'instructional', 'creative',
                'analytical', 'comparative', 'predictive', 'humorous'
            ]
        }
    
    def get_response(self, query: str, language: str = 'en', context: Dict = None) -> Dict[str, Any]:
        """Get ChatGPT-level response for any query"""
        try:
            # Analyze query to determine best approach
            analysis = self._analyze_query(query, language)
            
            # Check cache first
            cache_key = f"ollama_response_{hash(query)}_{language}"
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                if datetime.now() - cached_data['timestamp'] < self.cache_duration:
                    return cached_data['data']
            
            # Determine response strategy
            if analysis['category'] == 'agricultural':
                response = self._get_agricultural_response(query, language, context)
            elif analysis['category'] == 'technical':
                response = self._get_technical_response(query, language, context)
            elif analysis['category'] == 'creative':
                response = self._get_creative_response(query, language, context)
            else:
                response = self._get_general_response(query, language, context)
            
            # Cache the response
            self.cache[cache_key] = {
                'data': response,
                'timestamp': datetime.now()
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error in Ollama integration: {e}")
            return self._get_fallback_response(query, language)
    
    def _analyze_query(self, query: str, language: str) -> Dict[str, Any]:
        """Analyze query to determine category and approach"""
        query_lower = query.lower().strip()
        
        # Agricultural keywords
        agri_keywords = [
            'crop', 'फसल', 'farming', 'खेती', 'agriculture', 'कृषि', 'soil', 'मिट्टी',
            'fertilizer', 'उर्वरक', 'irrigation', 'सिंचाई', 'harvest', 'कटाई',
            'sow', 'बोना', 'plant', 'पौधा', 'seed', 'बीज', 'yield', 'उत्पादन',
            'lagayein', 'लगाएं', 'suggest', 'सुझाव', 'recommend', 'अनुशंसा',
            'pest', 'कीट', 'disease', 'रोग', 'weed', 'खरपतवार', 'organic', 'जैविक',
            'weather', 'मौसम', 'price', 'कीमत', 'market', 'बाजार', 'mandi', 'मंडी'
        ]
        
        # Technical keywords
        tech_keywords = [
            'programming', 'code', 'python', 'javascript', 'java', 'html', 'css',
            'database', 'sql', 'api', 'software', 'app', 'website', 'development',
            'algorithm', 'data structure', 'machine learning', 'ai', 'artificial intelligence',
            'server', 'cloud', 'docker', 'kubernetes', 'git', 'github'
        ]
        
        # Creative keywords
        creative_keywords = [
            'joke', 'जोक', 'fun', 'मजा', 'story', 'कहानी', 'poem', 'कविता',
            'creative', 'imagine', 'write', 'लिखना', 'draw', 'design', 'art',
            'music', 'song', 'game', 'खेल', 'entertainment', 'मनोरंजन'
        ]
        
        # Calculate scores
        agri_score = sum(1 for kw in agri_keywords if kw in query_lower)
        tech_score = sum(1 for kw in tech_keywords if kw in query_lower)
        creative_score = sum(1 for kw in creative_keywords if kw in query_lower)
        
        # Determine category
        if agri_score > tech_score and agri_score > creative_score:
            category = 'agricultural'
            confidence = min(agri_score / 3, 0.95)
        elif tech_score > creative_score:
            category = 'technical'
            confidence = min(tech_score / 3, 0.95)
        elif creative_score > 0:
            category = 'creative'
            confidence = min(creative_score / 3, 0.95)
        else:
            category = 'general'
            confidence = 0.7
        
        return {
            'category': category,
            'confidence': confidence,
            'language': language,
            'query_type': self._get_query_type(query_lower),
            'entities': self._extract_entities(query_lower),
            'intent': self._get_intent(query_lower)
        }
    
    def _get_query_type(self, query: str) -> str:
        """Determine the type of query"""
        if any(word in query for word in ['what', 'क्या', 'what is', 'क्या है']):
            return 'factual'
        elif any(word in query for word in ['how', 'कैसे', 'how to', 'कैसे करें']):
            return 'instructional'
        elif any(word in query for word in ['why', 'क्यों', 'why is', 'क्यों है']):
            return 'explanatory'
        elif any(word in query for word in ['when', 'कब', 'when is', 'कब है']):
            return 'temporal'
        elif any(word in query for word in ['where', 'कहां', 'where is', 'कहां है']):
            return 'locational'
        elif any(word in query for word in ['who', 'कौन', 'who is', 'कौन है']):
            return 'personal'
        else:
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
    
    def _get_intent(self, query: str) -> str:
        """Determine user intent"""
        if any(word in query for word in ['help', 'मदद', 'assist', 'सहायता']):
            return 'help_request'
        elif any(word in query for word in ['explain', 'समझाएं', 'describe', 'वर्णन']):
            return 'explanation_request'
        elif any(word in query for word in ['solve', 'हल', 'fix', 'ठीक']):
            return 'problem_solving'
        elif any(word in query for word in ['create', 'बनाएं', 'make', 'बनाना']):
            return 'creation_request'
        else:
            return 'information_request'
    
    def _get_general_response(self, query: str, language: str, context: Dict = None) -> Dict[str, Any]:
        """Get general response using Ollama"""
        try:
            # Try Ollama first
            ollama_response = self._call_ollama(query, 'general', language)
            if ollama_response:
                return {
                    'response': ollama_response,
                    'source': 'ollama',
                    'confidence': 0.9,
                    'language': language,
                    'category': 'general',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Fallback to other open source APIs
            return self._call_open_source_apis(query, language)
            
        except Exception as e:
            logger.error(f"Error in general response: {e}")
            return self._get_fallback_response(query, language)
    
    def _get_agricultural_response(self, query: str, language: str, context: Dict = None) -> Dict[str, Any]:
        """Get agricultural response using Ollama"""
        try:
            # Try Ollama with agricultural context
            ollama_response = self._call_ollama(query, 'agricultural', language)
            if ollama_response:
                return {
                    'response': ollama_response,
                    'source': 'ollama_agricultural',
                    'confidence': 0.95,
                    'language': language,
                    'category': 'agricultural',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Fallback to agricultural knowledge base
            return self._get_agricultural_fallback(query, language)
            
        except Exception as e:
            logger.error(f"Error in agricultural response: {e}")
            return self._get_agricultural_fallback(query, language)
    
    def _get_technical_response(self, query: str, language: str, context: Dict = None) -> Dict[str, Any]:
        """Get technical response using Ollama"""
        try:
            # Try Ollama with technical context
            ollama_response = self._call_ollama(query, 'technical', language)
            if ollama_response:
                return {
                    'response': ollama_response,
                    'source': 'ollama_technical',
                    'confidence': 0.9,
                    'language': language,
                    'category': 'technical',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Fallback to technical knowledge base
            return self._get_technical_fallback(query, language)
            
        except Exception as e:
            logger.error(f"Error in technical response: {e}")
            return self._get_technical_fallback(query, language)
    
    def _get_creative_response(self, query: str, language: str, context: Dict = None) -> Dict[str, Any]:
        """Get creative response using Ollama"""
        try:
            # Try Ollama with creative context
            ollama_response = self._call_ollama(query, 'creative', language)
            if ollama_response:
                return {
                    'response': ollama_response,
                    'source': 'ollama_creative',
                    'confidence': 0.85,
                    'language': language,
                    'category': 'creative',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Fallback to creative responses
            return self._get_creative_fallback(query, language)
            
        except Exception as e:
            logger.error(f"Error in creative response: {e}")
            return self._get_creative_fallback(query, language)
    
    def _call_ollama(self, query: str, context_type: str, language: str) -> Optional[str]:
        """Call Ollama API for response"""
        try:
            # Check if Ollama is available
            health_check = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
            if health_check.status_code != 200:
                logger.warning("Ollama not available, using fallback")
                return None
            
            # Prepare the prompt
            system_prompt = self.system_prompts.get(context_type, self.system_prompts['general'])
            
            if language == 'hi':
                system_prompt += "\n\nPlease respond in Hindi (हिंदी) unless specifically asked otherwise."
            elif language == 'hinglish':
                system_prompt += "\n\nPlease respond in Hinglish (Hindi-English mix) unless specifically asked otherwise."
            
            # Prepare the request
            url = f"{self.ollama_base_url}/api/generate"
            data = {
                "model": self.current_model,
                "prompt": f"{system_prompt}\n\nUser Query: {query}",
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 1000
                }
            }
            
            response = requests.post(url, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if 'response' in result:
                return result['response'].strip()
            
            return None
            
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return None
    
    def _call_open_source_apis(self, query: str, language: str) -> Dict[str, Any]:
        """Call other open source APIs as fallback"""
        try:
            # Try Hugging Face Inference API
            hf_response = self._call_huggingface(query, language)
            if hf_response:
                return {
                    'response': hf_response,
                    'source': 'huggingface',
                    'confidence': 0.8,
                    'language': language,
                    'category': 'general',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Try other APIs
            return self._get_comprehensive_fallback(query, language)
            
        except Exception as e:
            logger.error(f"Error in open source APIs: {e}")
            return self._get_comprehensive_fallback(query, language)
    
    def _call_huggingface(self, query: str, language: str) -> Optional[str]:
        """Call Hugging Face Inference API"""
        try:
            # Use a free model from Hugging Face
            url = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"
            headers = {
                "Authorization": f"Bearer {os.getenv('HUGGINGFACE_TOKEN', '')}"
            }
            
            data = {
                "inputs": query,
                "parameters": {
                    "max_length": 200,
                    "temperature": 0.7
                }
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get('generated_text', '').strip()
            
            return None
            
        except Exception as e:
            logger.error(f"Error calling Hugging Face: {e}")
            return None
    
    def _get_comprehensive_fallback(self, query: str, language: str) -> Dict[str, Any]:
        """Comprehensive fallback response system"""
        query_lower = query.lower().strip()
        
        # General knowledge responses
        if any(word in query_lower for word in ['what is', 'क्या है', 'what are', 'क्या हैं']):
            return self._handle_what_is_query(query, language)
        elif any(word in query_lower for word in ['how to', 'कैसे करें', 'how do', 'कैसे करते हैं']):
            return self._handle_how_to_query(query, language)
        elif any(word in query_lower for word in ['who is', 'कौन है', 'who are', 'कौन हैं']):
            return self._handle_who_is_query(query, language)
        elif any(word in query_lower for word in ['when is', 'कब है', 'when was', 'कब था']):
            return self._handle_when_query(query, language)
        elif any(word in query_lower for word in ['where is', 'कहां है', 'where are', 'कहां हैं']):
            return self._handle_where_query(query, language)
        elif any(word in query_lower for word in ['why is', 'क्यों है', 'why are', 'क्यों हैं']):
            return self._handle_why_query(query, language)
        else:
            return self._get_general_fallback(query, language)
    
    def _handle_what_is_query(self, query: str, language: str) -> Dict[str, Any]:
        """Handle 'what is' queries"""
        query_lower = query.lower().strip()
        
        # Common knowledge responses
        responses = {
            'artificial intelligence': {
                'en': "Artificial Intelligence (AI) is a branch of computer science that aims to create machines that can perform tasks that typically require human intelligence, such as learning, reasoning, and problem-solving.",
                'hi': "कृत्रिम बुद्धिमत्ता (AI) कंप्यूटर विज्ञान की एक शाखा है जो ऐसी मशीनें बनाने का लक्ष्य रखती है जो मानव बुद्धिमत्ता की आवश्यकता वाले कार्य कर सकें।"
            },
            'machine learning': {
                'en': "Machine Learning is a subset of AI that enables computers to learn and improve from experience without being explicitly programmed for every task.",
                'hi': "मशीन लर्निंग AI का एक उपसमूह है जो कंप्यूटर को अनुभव से सीखने और सुधारने में सक्षम बनाता है।"
            },
            'python': {
                'en': "Python is a high-level, interpreted programming language known for its simplicity and readability. It's widely used in web development, data science, AI, and automation.",
                'hi': "Python एक उच्च-स्तरीय, व्याख्या की गई प्रोग्रामिंग भाषा है जो अपनी सरलता और पठनीयता के लिए जानी जाती है।"
            }
        }
        
        for key, response in responses.items():
            if key in query_lower:
                return {
                    'response': response.get(language, response['en']),
                    'source': 'knowledge_base',
                    'confidence': 0.9,
                    'language': language,
                    'category': 'general_knowledge',
                    'timestamp': datetime.now().isoformat()
                }
        
        return self._get_general_fallback(query, language)
    
    def _handle_how_to_query(self, query: str, language: str) -> Dict[str, Any]:
        """Handle 'how to' queries"""
        query_lower = query.lower().strip()
        
        if 'learn programming' in query_lower or 'programming सीखें' in query_lower:
            response = {
                'en': "To learn programming:\n1. Choose a language (Python recommended for beginners)\n2. Start with basic syntax and concepts\n3. Practice coding daily\n4. Build small projects\n5. Join coding communities\n6. Read code written by others\n7. Take online courses or tutorials",
                'hi': "प्रोग्रामिंग सीखने के लिए:\n1. एक भाषा चुनें (शुरुआती के लिए Python सुझाव)\n2. बुनियादी सिंटैक्स और अवधारणाओं से शुरू करें\n3. रोजाना कोडिंग का अभ्यास करें\n4. छोटे प्रोजेक्ट बनाएं\n5. कोडिंग समुदायों में शामिल हों\n6. दूसरों द्वारा लिखे गए कोड पढ़ें\n7. ऑनलाइन कोर्स या ट्यूटोरियल लें"
            }
        elif 'start business' in query_lower or 'व्यापार शुरू करें' in query_lower:
            response = {
                'en': "To start a business:\n1. Identify a market need\n2. Research your target audience\n3. Create a business plan\n4. Secure funding\n5. Register your business\n6. Build your product/service\n7. Market your business\n8. Launch and iterate",
                'hi': "व्यापार शुरू करने के लिए:\n1. बाजार की जरूरत की पहचान करें\n2. अपने लक्षित दर्शकों पर शोध करें\n3. व्यापार योजना बनाएं\n4. धन सुरक्षित करें\n5. अपना व्यापार पंजीकृत करें\n6. अपना उत्पाद/सेवा बनाएं\n7. अपने व्यापार का विपणन करें\n8. लॉन्च करें और सुधार करें"
            }
        else:
            return self._get_general_fallback(query, language)
        
        return {
            'response': response.get(language, response['en']),
            'source': 'knowledge_base',
            'confidence': 0.85,
            'language': language,
            'category': 'instructional',
            'timestamp': datetime.now().isoformat()
        }
    
    def _handle_who_is_query(self, query: str, language: str) -> Dict[str, Any]:
        """Handle 'who is' queries"""
        query_lower = query.lower().strip()
        
        responses = {
            'elon musk': {
                'en': "Elon Musk is a South African-born American entrepreneur and business magnate. He is the CEO of Tesla and SpaceX, and has been involved in various other ventures including Neuralink and The Boring Company.",
                'hi': "एलन मस्क एक दक्षिण अफ्रीकी मूल के अमेरिकी उद्यमी और व्यापारिक प्रतिभा हैं। वे Tesla और SpaceX के CEO हैं।"
            },
            'bill gates': {
                'en': "Bill Gates is an American business magnate, software developer, and philanthropist. He co-founded Microsoft Corporation and is known for his philanthropic work through the Bill & Melinda Gates Foundation.",
                'hi': "बिल गेट्स एक अमेरिकी व्यापारिक प्रतिभा, सॉफ्टवेयर डेवलपर और परोपकारी हैं। उन्होंने Microsoft Corporation की सह-स्थापना की।"
            }
        }
        
        for key, response in responses.items():
            if key in query_lower:
                return {
                    'response': response.get(language, response['en']),
                    'source': 'knowledge_base',
                    'confidence': 0.9,
                    'language': language,
                    'category': 'biographical',
                    'timestamp': datetime.now().isoformat()
                }
        
        return self._get_general_fallback(query, language)
    
    def _handle_when_query(self, query: str, language: str) -> Dict[str, Any]:
        """Handle 'when' queries"""
        return self._get_general_fallback(query, language)
    
    def _handle_where_query(self, query: str, language: str) -> Dict[str, Any]:
        """Handle 'where' queries"""
        return self._get_general_fallback(query, language)
    
    def _handle_why_query(self, query: str, language: str) -> Dict[str, Any]:
        """Handle 'why' queries"""
        return self._get_general_fallback(query, language)
    
    def _get_general_fallback(self, query: str, language: str) -> Dict[str, Any]:
        """General fallback response"""
        if language == 'hi':
            response = f"मैं आपके प्रश्न '{query}' को समझने की कोशिश कर रहा हूं। मैं एक बहु-क्षेत्रीय AI सहायक हूं जो कृषि, तकनीक, सामान्य ज्ञान और कई अन्य विषयों में मदद कर सकता हूं। कृपया अपना प्रश्न और विस्तार से पूछें।"
        elif language == 'hinglish':
            response = f"Main aapke question '{query}' ko samajhne ki koshish kar raha hun. Main ek multi-domain AI assistant hun jo agriculture, technology, general knowledge aur kai aur subjects mein help kar sakta hun. Please apna question detail mein pucho."
        else:
            response = f"I'm trying to understand your question '{query}'. I'm a multi-domain AI assistant that can help with agriculture, technology, general knowledge, and many other subjects. Please ask your question in more detail."
        
        return {
            'response': response,
            'source': 'fallback',
            'confidence': 0.6,
            'language': language,
            'category': 'general',
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_agricultural_fallback(self, query: str, language: str) -> Dict[str, Any]:
        """Agricultural fallback response"""
        if language == 'hi':
            response = f"आपका प्रश्न कृषि से संबंधित है। मैं आपको विस्तृत कृषि सलाह दूंगा। कृपया अपना स्थान, मिट्टी का प्रकार और सीजन बताएं ताकि मैं आपको सटीक सलाह दे सकूं।"
        else:
            response = f"Your query is related to agriculture. I'll provide detailed farming advice. Please share your location, soil type, and season so I can give you accurate recommendations."
        
        return {
            'response': response,
            'source': 'agricultural_fallback',
            'confidence': 0.8,
            'language': language,
            'category': 'agricultural',
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_technical_fallback(self, query: str, language: str) -> Dict[str, Any]:
        """Technical fallback response"""
        if language == 'hi':
            response = f"आपका प्रश्न तकनीकी है। मैं आपकी तकनीकी समस्याओं में मदद कर सकता हूं। कृपया अपनी समस्या को और विस्तार से बताएं।"
        else:
            response = f"Your query is technical. I can help you with technical problems. Please provide more details about your issue."
        
        return {
            'response': response,
            'source': 'technical_fallback',
            'confidence': 0.8,
            'language': language,
            'category': 'technical',
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_creative_fallback(self, query: str, language: str) -> Dict[str, Any]:
        """Creative fallback response"""
        if language == 'hi':
            response = f"आपका प्रश्न रचनात्मक है। मैं आपकी रचनात्मक जरूरतों में मदद कर सकता हूं। कृपया बताएं कि आप क्या चाहते हैं।"
        else:
            response = f"Your query is creative. I can help you with creative needs. Please tell me what you're looking for."
        
        return {
            'response': response,
            'source': 'creative_fallback',
            'confidence': 0.8,
            'language': language,
            'category': 'creative',
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_fallback_response(self, query: str, language: str) -> Dict[str, Any]:
        """Ultimate fallback response"""
        if language == 'hi':
            response = "क्षमा करें, मुझे आपकी बात समझ नहीं आई। कृपया फिर से प्रयास करें।"
        elif language == 'hinglish':
            response = "Sorry bhai, main aapki baat samajh nahi paya. Please phir se try karo."
        else:
            response = "Sorry, I couldn't understand your request. Please try again."
        
        return {
            'response': response,
            'source': 'error_fallback',
            'confidence': 0.3,
            'language': language,
            'category': 'error',
            'timestamp': datetime.now().isoformat()
        }
    
    def get_available_models(self) -> List[str]:
        """Get list of available Ollama models"""
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return []
    
    def set_model(self, model_name: str) -> bool:
        """Set the current model"""
        try:
            available_models = self.get_available_models()
            if model_name in available_models:
                self.current_model = model_name
                return True
            return False
        except Exception as e:
            logger.error(f"Error setting model: {e}")
            return False
    
    def generate_response(self, query: str, language: str = 'en') -> str:
        """Generate response using Ollama for general queries with improved fallback"""
        try:
            # Quick check if Ollama is available (reduced timeout)
            response = self._call_ollama_api(query, language, timeout=5)
            if response and len(response) > 50:
                logger.info("Using Ollama for response")
                return response
            
            # Fallback to enhanced knowledge base
            logger.info("Ollama not available, using enhanced fallback")
            return self._get_enhanced_knowledge_base_response(query, language)
            
        except Exception as e:
            logger.warning(f"Ollama failed, using fallback: {e}")
            return self._get_enhanced_knowledge_base_response(query, language)
    
    def _call_ollama_api(self, query: str, language: str, timeout: int = 10) -> str:
        """Call Ollama API directly with ChatGPT-like intelligence"""
        try:
            # Enhanced ChatGPT-like system prompts for ALL types of queries
            if language in ['hi', 'hinglish']:
                system_prompt = """आप कृषिमित्र AI हैं - एक बहुत ही बुद्धिमान और सहायक AI सहायक। आपके पास व्यापक ज्ञान है और आप सभी विषयों पर सही, विस्तृत और उपयोगी जवाब दे सकते हैं:

🌍 सामान्य ज्ञान: इतिहास, भूगोल, विज्ञान, गणित, साहित्य
💻 तकनीक: प्रोग्रामिंग, कंप्यूटर, सॉफ्टवेयर, AI/ML
🏥 स्वास्थ्य: चिकित्सा, पोषण, फिटनेस
💰 व्यापार: अर्थशास्त्र, वित्त, निवेश, मार्केटिंग
🎭 मनोरंजन: फिल्में, संगीत, खेल, कला
📚 शिक्षा: शिक्षण, सीखना, शोध
🌾 कृषि: खेती, फसलें, मौसम, बाजार भाव

आप बातचीत में प्राकृतिक, मैत्रीपूर्ण और सहायक हैं। हिंदी में उत्तर दें और जब भी संभव हो उदाहरण और विस्तृत जानकारी प्रदान करें।"""
            else:
                system_prompt = """You are Krishimitra AI - a highly intelligent and helpful AI assistant. You have extensive knowledge across all domains and can provide accurate, detailed, and useful responses on any topic:

🌍 General Knowledge: History, Geography, Science, Mathematics, Literature
💻 Technology: Programming, Computers, Software, AI/ML, Web Development
🏥 Health: Medicine, Nutrition, Fitness, Wellness
💰 Business: Economics, Finance, Investment, Marketing
🎭 Entertainment: Movies, Music, Sports, Arts
📚 Education: Teaching, Learning, Research
🌾 Agriculture: Farming, Crops, Weather, Market Prices

You are natural, friendly, and helpful in conversation. Provide detailed explanations with examples whenever possible. Be conversational and engaging like ChatGPT."""
            
            payload = {
                "model": self.current_model,
                "prompt": f"{system_prompt}\n\nUser: {query}\n\nAssistant:",
                "stream": False,
                "options": {
                    "temperature": 0.8,
                    "top_p": 0.95,
                    "max_tokens": 800,
                    "repeat_penalty": 1.1,
                    "stop": ["User:", "Human:", "Human"]
                }
            }
            
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json=payload,
                timeout=timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('response', '').strip()
            else:
                logger.warning(f"Ollama API returned status {response.status_code}")
                return ""
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Ollama API request failed: {e}")
            return ""
        except Exception as e:
            logger.error(f"Error calling Ollama API: {e}")
            return ""
    
    def _get_knowledge_base_response(self, query: str, language: str) -> str:
        """Get response from knowledge base"""
        query_lower = query.lower()
        
        # AI and technology queries
        if any(keyword in query_lower for keyword in ['artificial intelligence', 'ai', 'machine learning', 'technology']):
            if language in ['hi', 'hinglish']:
                return """🤖 कृत्रिम बुद्धिमत्ता (AI) के बारे में:

AI एक ऐसी तकनीक है जो कंप्यूटर को मानव की तरह सोचने और सीखने की क्षमता देती है।

🌟 **AI के मुख्य प्रकार**:
• Machine Learning - डेटा से सीखना
• Deep Learning - मानव मस्तिष्क की नकल
• Natural Language Processing - भाषा समझना

💡 **AI के उपयोग**:
• Agriculture - फसल निगरानी और पूर्वानुमान
• Healthcare - रोग निदान
• Finance - धोखाधड़ी का पता लगाना
• Education - व्यक्तिगत सीखने की सुविधा

🚀 **भविष्य**: AI तेजी से विकसित हो रहा है और हमारे जीवन को बेहतर बना रहा है।"""
            else:
                return """🤖 Artificial Intelligence (AI) Overview:

Artificial Intelligence is technology that enables computers to think and learn like humans. It's based on machine learning, deep learning, and neural networks.

🌟 **Main Types of AI**:
• Machine Learning - Learning from data
• Deep Learning - Mimicking human brain
• Natural Language Processing - Understanding language

💡 **AI Applications**:
• Agriculture - Crop monitoring and forecasting
• Healthcare - Disease diagnosis
• Finance - Fraud detection
• Education - Personalized learning

🚀 **Future**: AI is rapidly evolving and improving our lives across all sectors."""
        
        # Geography queries
        elif any(keyword in query_lower for keyword in ['capital', 'राजधानी', 'country', 'देश']):
            if language in ['hi', 'hinglish']:
                return """🗺️ भारत की राजधानी के बारे में:

भारत की राजधानी **नई दिल्ली** है।

📍 **मुख्य तथ्य**:
• राजधानी: नई दिल्ली
• राज्य: दिल्ली (केंद्र शासित प्रदेश)
• जनसंख्या: लगभग 3.3 करोड़
• क्षेत्रफल: 1,484 वर्ग किमी

🏛️ **महत्वपूर्ण स्थान**:
• राष्ट्रपति भवन
• संसद भवन
• सुप्रीम कोर्ट
• रेड फोर्ट

🌟 **इतिहास**: 1911 में ब्रिटिश राज में राजधानी बनी।"""
            else:
                return """🗺️ About India's Capital:

India's capital is **New Delhi**.

📍 **Key Facts**:
• Capital: New Delhi
• State: Delhi (Union Territory)
• Population: Approximately 33 million
• Area: 1,484 sq km

🏛️ **Important Places**:
• Rashtrapati Bhavan
• Parliament House
• Supreme Court
• Red Fort

🌟 **History**: Became capital in 1911 during British rule."""
        
        # Default response
        else:
            if language in ['hi', 'hinglish']:
                return "मैं एक AI सहायक हूं। मैं आपकी सहायता कर सकता हूं। कृपया अपना प्रश्न स्पष्ट रूप से पूछें।"
            else:
                return "I am an AI assistant. I can help you with various questions. Please ask your question clearly."
    
    def _get_enhanced_knowledge_base_response(self, query: str, language: str) -> str:
        """Get enhanced ChatGPT-like response from comprehensive knowledge base"""
        query_lower = query.lower()
        
        # Enhanced comprehensive responses with ChatGPT-like intelligence
        responses = {
            # General greetings and introductions
            'hello': {
                'en': "Hello! 👋 I'm Krishimitra AI, your intelligent agricultural assistant. I'm here to help you with everything related to farming, crops, weather, market prices, government schemes, and much more! I can provide real-time data and expert advice. What would you like to know today?",
                'hi': "नमस्ते! 👋 मैं कृषिमित्र AI हूं, आपका बुद्धिमान कृषि सहायक। मैं यहां खेती, फसल, मौसम, बाजार भाव, सरकारी योजनाओं और बहुत कुछ में आपकी मदद के लिए हूं! मैं वास्तविक समय का डेटा और विशेषज्ञ सलाह प्रदान कर सकता हूं। आज आप क्या जानना चाहते हैं?"
            },
            'hi': {
                'en': "Hi there! 😊 I'm Krishimitra AI, your friendly agricultural assistant. I'm excited to help you with farming questions, crop advice, weather updates, market prices, and any other agricultural information you need. How can I assist you today?",
                'hi': "हाय! 😊 मैं कृषिमित्र AI हूं, आपका मैत्रीपूर्ण कृषि सहायक। मैं खेती के सवालों, फसल सलाह, मौसम अपडेट, बाजार भाव और आपके लिए आवश्यक किसी भी अन्य कृषि जानकारी में आपकी मदद करने के लिए उत्साहित हूं। आज मैं आपकी कैसे मदद कर सकता हूं?"
            },
            'who are you': {
                'en': "I'm Krishimitra AI! 🤖✨ I'm your intelligent agricultural assistant powered by advanced AI technology. I specialize in providing real-time farming advice, crop recommendations, weather forecasts, market prices, and government scheme information. I can help with everything from basic farming questions to complex agricultural strategies. Think of me as your personal farming consultant available 24/7!",
                'hi': "मैं कृषिमित्र AI हूं! 🤖✨ मैं उन्नत AI तकनीक से संचालित आपका बुद्धिमान कृषि सहायक हूं। मैं वास्तविक समय की खेती सलाह, फसल सुझाव, मौसम पूर्वानुमान, बाजार भाव और सरकारी योजना की जानकारी प्रदान करने में विशेषज्ञ हूं। मैं बुनियादी खेती के सवालों से लेकर जटिल कृषि रणनीतियों तक सब में मदद कर सकता हूं। मुझे अपना व्यक्तिगत खेती सलाहकार समझें जो 24/7 उपलब्ध है!"
            },
            # Technology questions with ChatGPT-like depth
            'artificial intelligence': {
                'en': "Artificial Intelligence (AI) is fascinating! 🤖 It's technology that enables computers to think, learn, and make decisions like humans. In agriculture, AI is revolutionizing farming through:\n\n• **Crop Prediction**: Analyzing weather patterns and soil conditions to predict optimal planting times\n• **Pest Detection**: Using computer vision to identify diseases and pests early\n• **Weather Forecasting**: Providing hyper-local weather predictions for better farming decisions\n• **Precision Agriculture**: Optimizing water, fertilizer, and pesticide usage\n• **Yield Optimization**: Maximizing crop production while minimizing environmental impact\n\nAI is making farming smarter, more sustainable, and more profitable! 🌱",
                'hi': "कृत्रिम बुद्धिमत्ता (AI) बहुत रोमांचक है! 🤖 यह एक तकनीक है जो कंप्यूटर को मानव की तरह सोचने, सीखने और निर्णय लेने में सक्षम बनाती है। कृषि में, AI निम्नलिखित तरीकों से खेती में क्रांति ला रहा है:\n\n• **फसल भविष्यवाणी**: मौसम पैटर्न और मिट्टी की स्थिति का विश्लेषण करके इष्टतम बुवाई समय की भविष्यवाणी\n• **कीट पहचान**: रोगों और कीटों की जल्दी पहचान के लिए कंप्यूटर विजन का उपयोग\n• **मौसम पूर्वानुमान**: बेहतर खेती निर्णयों के लिए हाइपर-स्थानीय मौसम पूर्वानुमान\n• **सटीक कृषि**: पानी, उर्वरक और कीटनाशक के उपयोग को अनुकूलित करना\n• **उपज अनुकूलन**: पर्यावरणीय प्रभाव को कम करते हुए फसल उत्पादन को अधिकतम करना\n\nAI खेती को अधिक स्मार्ट, टिकाऊ और लाभदायक बना रहा है! 🌱"
            },
            'machine learning': {
                'en': "Machine Learning is incredible! 🧠 It's a subset of AI that enables systems to automatically learn and improve from experience without being explicitly programmed. In agriculture, ML is transforming farming:\n\n• **Predictive Analytics**: Forecasting crop yields based on historical data and current conditions\n• **Soil Analysis**: Analyzing soil composition and recommending optimal nutrients\n• **Disease Detection**: Identifying plant diseases from images with high accuracy\n• **Precision Farming**: Optimizing irrigation, fertilization, and pest control\n• **Market Prediction**: Predicting crop prices and market trends\n\nMachine Learning is like having a farming expert that never stops learning and improving! 📈",
                'hi': "मशीन लर्निंग अविश्वसनीय है! 🧠 यह AI का एक उपसमुच्चय है जो सिस्टम को स्पष्ट रूप से प्रोग्राम किए बिना अनुभव से स्वचालित रूप से सीखने और सुधारने में सक्षम बनाता है। कृषि में, ML खेती को बदल रहा है:\n\n• **भविष्यवाणी विश्लेषण**: ऐतिहासिक डेटा और वर्तमान स्थितियों के आधार पर फसल उपज की भविष्यवाणी\n• **मिट्टी विश्लेषण**: मिट्टी की संरचना का विश्लेषण और इष्टतम पोषक तत्वों की सिफारिश\n• **रोग पहचान**: उच्च सटीकता के साथ छवियों से पौधों के रोगों की पहचान\n• **सटीक खेती**: सिंचाई, उर्वरीकरण और कीट नियंत्रण को अनुकूलित करना\n• **बाजार भविष्यवाणी**: फसल कीमतों और बाजार रुझानों की भविष्यवाणी\n\nमशीन लर्निंग एक खेती विशेषज्ञ की तरह है जो कभी सीखना और सुधारना बंद नहीं करता! 📈"
            },
            # Geography questions
            'capital of india': {
                'en': "The capital of India is New Delhi. It's located in the National Capital Territory of Delhi and serves as the political and administrative center of India.",
                'hi': "भारत की राजधानी नई दिल्ली है। यह दिल्ली के राष्ट्रीय राजधानी क्षेत्र में स्थित है और भारत के राजनीतिक और प्रशासनिक केंद्र के रूप में कार्य करता है।"
            },
            'prime minister': {
                'en': "The current Prime Minister of India is Narendra Modi. He has been serving as Prime Minister since 2014 and is a member of the Bharatiya Janata Party (BJP).",
                'hi': "भारत के वर्तमान प्रधानमंत्री नरेंद्र मोदी हैं। वह 2014 से प्रधानमंत्री के रूप में सेवा कर रहे हैं और भारतीय जनता पार्टी (भाजपा) के सदस्य हैं।"
            },
            # Programming questions
            'programming': {
                'en': "Programming is the process of creating instructions for computers to follow. Popular languages include Python (great for beginners), JavaScript (for web development), Java (for enterprise applications), and C++ (for system programming). Start with Python for agriculture-related applications!",
                'hi': "प्रोग्रामिंग कंप्यूटर के लिए निर्देश बनाने की प्रक्रिया है। लोकप्रिय भाषाओं में Python (शुरुआती के लिए बेहतरीन), JavaScript (वेब डेवलपमेंट के लिए), Java (एंटरप्राइज एप्लिकेशन के लिए), और C++ (सिस्टम प्रोग्रामिंग के लिए) शामिल हैं। कृषि संबंधी एप्लिकेशन के लिए Python से शुरुआत करें!"
            },
            # Science questions
            'photosynthesis': {
                'en': "Photosynthesis is the process by which plants convert light energy from the sun into chemical energy (glucose). Plants use carbon dioxide from air, water from soil, and sunlight to produce glucose and release oxygen. This is essential for plant growth and our oxygen supply.",
                'hi': "प्रकाश संश्लेषण वह प्रक्रिया है जिसके द्वारा पौधे सूर्य से प्रकाश ऊर्जा को रासायनिक ऊर्जा (ग्लूकोज) में परिवर्तित करते हैं। पौधे हवा से कार्बन डाइऑक्साइड, मिट्टी से पानी, और सूर्य के प्रकाश का उपयोग करके ग्लूकोज का उत्पादन करते हैं और ऑक्सीजन छोड़ते हैं। यह पौधों के विकास और हमारी ऑक्सीजन आपूर्ति के लिए आवश्यक है।"
            }
        }
        
        # Check for specific keywords and return appropriate response
        for key, response in responses.items():
            if key in query_lower:
                return response.get(language, response.get('en', ""))
        
        # Check for partial matches
        if any(word in query_lower for word in ['who is', 'कौन है']):
            if language in ['hi', 'hinglish']:
                return "कृपया विशिष्ट व्यक्ति या विषय का नाम बताएं। मैं आपको उसके बारे में जानकारी दे सकूंगा।"
            else:
                return "Please specify the person or subject you're asking about. I can provide information about them."
        
        if any(word in query_lower for word in ['what is', 'क्या है']):
            if language in ['hi', 'hinglish']:
                return "कृपया विशिष्ट विषय या अवधारणा का नाम बताएं। मैं आपको उसके बारे में विस्तृत जानकारी दे सकूंगा।"
            else:
                return "Please specify the subject or concept you're asking about. I can provide detailed information about it."
        
        # Default intelligent response
        if language in ['hi', 'hinglish']:
            return "मैं कृषिमित्र AI हूं, आपका बुद्धिमान कृषि सहायक। मैं कृषि, फसल, मौसम, सरकारी योजनाओं के साथ-साथ सामान्य ज्ञान के प्रश्नों का भी उत्तर दे सकता हूं। आप क्या जानना चाहते हैं?"
        else:
            return "I'm Krishimitra AI, your intelligent agricultural assistant. I can help with agriculture, crops, weather, government schemes, and also answer general knowledge questions. What would you like to know?"

# Create global instance
ollama_integration = OllamaIntegration()


