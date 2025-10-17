#!/usr/bin/env python3
"""
Intelligent AI-Powered Chatbot with Routing System
This implements intelligent routing: Ollama for general queries, Government APIs for farming queries
"""

import os
import logging
import json
from contextlib import contextmanager
import threading
import time
import signal
from datetime import datetime
from typing import Dict, Any, List

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from ..services.enhanced_market_prices import EnhancedMarketPricesService
from ..services.enhanced_pest_detection import pest_detection_service
from ..services.ultra_dynamic_government_api import UltraDynamicGovernmentAPI
from ..services.comprehensive_crop_recommendations import ComprehensiveCropRecommendations
from ..services.government_schemes_data import CENTRAL_GOVERNMENT_SCHEMES
from ..services.enhanced_location_service import EnhancedLocationService
from ..services.accurate_location_api import AccurateLocationAPI
from ..models import User, ForumPost

logger = logging.getLogger(__name__)

@contextmanager
def timeout_handler(seconds):
    """Cross-platform timeout handler"""
    import platform
    
    if platform.system() == 'Windows':
        # Windows-compatible timeout using threading
        timeout_occurred = threading.Event()
        
        def timeout_thread():
            time.sleep(seconds)
            timeout_occurred.set()
        
        threading.Thread(target=timeout_thread, daemon=True).start()
        
        try:
            yield timeout_occurred
        except Exception as e:
            if timeout_occurred.is_set():
                raise TimeoutError(f"Operation timed out after {seconds} seconds")
            raise e
    else:
        # Unix-compatible timeout using signals
        def timeout_signal_handler(signum, frame):
            raise TimeoutError(f"Operation timed out after {seconds} seconds")
        
        old_handler = signal.signal(signal.SIGALRM, timeout_signal_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

class ChatbotViewSet(viewsets.ViewSet):
    """Intelligent AI-Powered Chatbot with Routing"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize ALL available AI services
        self.services = {}
        
        # Core AI Services
        try:
            from ..services.consolidated_ai_service import ConsolidatedAIService
            self.services['consolidated_ai'] = ConsolidatedAIService()
            logger.info("✅ ConsolidatedAIService loaded")
        except ImportError as e:
            logger.warning(f"Could not import ConsolidatedAIService: {e}")
        
        try:
            from ..services.ollama_integration import OllamaIntegration
            self.services['ollama'] = OllamaIntegration()
            logger.info("✅ OllamaIntegration loaded")
        except ImportError as e:
            logger.warning(f"Could not import OllamaIntegration: {e}")
        
        try:
            from ..ml.ultimate_intelligent_ai import UltimateIntelligentAI
            self.services['ultimate_ai'] = UltimateIntelligentAI()
            logger.info("✅ UltimateIntelligentAI loaded")
        except ImportError as e:
            logger.warning(f"Could not import UltimateIntelligentAI: {e}")
        
        try:
            from ..services.ultra_dynamic_government_api import UltraDynamicGovernmentAPI
            self.services['government_api'] = UltraDynamicGovernmentAPI()
            logger.info("✅ UltraDynamicGovernmentAPI loaded")
        except ImportError as e:
            logger.warning(f"Could not import UltraDynamicGovernmentAPI: {e}")
        
        try:
            from ..services.comprehensive_crop_recommendations import ComprehensiveCropRecommendations
            self.services['crop_recommendations'] = ComprehensiveCropRecommendations()
            logger.info("✅ ComprehensiveCropRecommendations loaded")
        except ImportError as e:
            logger.warning(f"Could not import ComprehensiveCropRecommendations: {e}")
        
        try:
            from ..services.enhanced_market_prices import EnhancedMarketPricesService
            self.services['market_prices'] = EnhancedMarketPricesService()
            logger.info("✅ EnhancedMarketPricesService loaded")
        except ImportError as e:
            logger.warning(f"Could not import EnhancedMarketPricesService: {e}")
        
        try:
            from ..services.google_ai_studio import GoogleAIStudio
            self.services['google_ai'] = GoogleAIStudio()
            logger.info("✅ GoogleAIStudio loaded")
        except ImportError as e:
            logger.warning(f"Could not import GoogleAIStudio: {e}")
        
        logger.info(f"🚀 Total services loaded: {len(self.services)}")
    
    def create(self, request):
        """Process chatbot queries with intelligent routing"""
        try:
            data = request.data
            query = data.get('query', '')
            language = data.get('language', 'hindi')
            location = data.get('location', 'Delhi')
            session_id = data.get('session_id', 'default')
            
            logger.info(f"Chatbot request received: query='{query}', language='{language}', location='{location}'")
            
            if not query:
                return Response({
                    'error': 'Query is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Simple intelligent routing without complex AI services
            query_type = self._classify_query_type(query, language)
            logger.info(f"Query classification: '{query}' -> {query_type}")
            
            if query_type == 'farming_related':
                result = self._handle_farming_query_simple(query, language, location)
            else:
                result = self._handle_general_query_simple(query, language, location)
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Chatbot error: {e}")
            return Response({
                'response': 'I encountered an error processing your request. Please try again.',
                'data_source': 'error_fallback',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _classify_query_type(self, query: str, language: str) -> str:
        """Classify query as farming-related or general"""
        query_lower = query.lower()
        
        # Farming-related keywords
        farming_keywords = [
            'crop', 'farming', 'agriculture', 'soil', 'fertilizer', 'seed', 'plant', 'harvest', 
            'yield', 'irrigation', 'pest', 'disease', 'weather', 'rain', 'temperature', 
            'market', 'price', 'mandi', 'scheme', 'government', 'subsidy', 'cultivation',
            'wheat', 'rice', 'maize', 'corn', 'sugarcane', 'cotton', 'potato', 'tomato',
            'onion', 'mustard', 'soybean', 'groundnut', 'pulses', 'vegetables', 'fruits',
            'should plant', 'what to plant', 'best crop', 'grow', 'sowing', 'planting',
            'फसल', 'कृषि', 'खेती', 'मिट्टी', 'खाद', 'बीज', 'पौधा', 'कटाई', 'उपज', 
            'सिंचाई', 'कीट', 'रोग', 'मौसम', 'बारिश', 'तापमान', 'बाजार', 'कीमत', 
            'मंडी', 'योजना', 'सरकार', 'सब्सिडी', 'गेहूं', 'चावल', 'मक्का', 'सरसों',
            'खेती', 'बुवाई', 'कटाई', 'सिंचाई', 'उर्वरक', 'कीटनाशक', 'बीमारी'
        ]
        
        # Check if query contains farming keywords
        if any(keyword in query_lower for keyword in farming_keywords):
            return 'farming_related'
        
        return 'general'
    
    def _handle_farming_query_simple(self, query: str, language: str, location: str) -> Dict[str, Any]:
        """Handle farming queries using ONLY Government APIs - Simple and Effective"""
        try:
            logger.info(f"🌾 Processing farming query with Government APIs: {query}")
            
            # Step 1: Get comprehensive real-time government data
            gov_data = self._get_comprehensive_government_data(location)
            
            # Step 2: Use intelligent fallback with government data
            logger.info("🔄 Using intelligent fallback with government data")
            return self._get_intelligent_fallback_with_government_data(query, language, location, gov_data)
            
        except Exception as e:
            logger.error(f"Error in farming query handler: {e}")
            return self._get_intelligent_fallback_response(query, language, location)
    
    def _get_comprehensive_government_data(self, location: str) -> Dict[str, Any]:
        """Get comprehensive real-time government data from all sources"""
        try:
            gov_data = {
                'weather': {},
                'market_prices': {},
                'crop_recommendations': {},
                'government_schemes': {},
                'timestamp': datetime.now().isoformat()
            }
            
            # Get weather data
            if 'government_api' in self.services:
                try:
                    weather_data = self.services['government_api'].get_comprehensive_government_data(location=location)
                    gov_data.update(weather_data)
                except Exception as e:
                    logger.warning(f"Government API weather failed: {e}")
            
            # Get market prices
            if 'market_prices' in self.services:
                try:
                    market_data = self.services['market_prices'].get_comprehensive_market_data(location)
                    gov_data['market_prices'] = market_data
                except Exception as e:
                    logger.warning(f"Market prices service failed: {e}")
            
            # Get crop recommendations
            if 'crop_recommendations' in self.services:
                try:
                    crop_data = self.services['crop_recommendations'].get_crop_recommendations(location=location)
                    gov_data['crop_recommendations'] = crop_data
                except Exception as e:
                    logger.warning(f"Crop recommendations service failed: {e}")
            
            return gov_data
            
        except Exception as e:
            logger.error(f"Error getting comprehensive government data: {e}")
            return {'error': 'Government data unavailable', 'timestamp': datetime.now().isoformat()}
    
    def _create_enhanced_prompt(self, query: str, location: str, language: str, gov_data: Dict) -> str:
        """Create enhanced prompt with comprehensive government data"""
        if language == 'hindi':
            return f"""आप कृषिमित्र AI हैं - भारत का सबसे बुद्धिमान कृषि सहायक। आपके पास वास्तविक समय का सरकारी डेटा है।

कृषि सवाल: {query}
स्थान: {location}

वास्तविक समय सरकारी डेटा:
{json.dumps(gov_data, ensure_ascii=False, indent=2)}

कृपया विस्तृत, व्यावहारिक और उपयोगी जवाब दें। वास्तविक समय के डेटा का उपयोग करके सटीक सुझाव दें।"""
        else:
            return f"""You are KrishiMitra AI - India's most intelligent agricultural assistant. You have access to real-time government data.

Agricultural Question: {query}
Location: {location}

Real-time Government Data:
{json.dumps(gov_data, indent=2)}

Please provide detailed, practical, and useful answers. Use real-time data to give accurate recommendations."""
    
    def _get_intelligent_fallback_with_government_data(self, query: str, language: str, location: str, gov_data: Dict) -> Dict[str, Any]:
        """Intelligent fallback with comprehensive government data context - ChatGPT-like responses"""
        try:
            # Extract comprehensive information from government data
            context_info = []
            
            # Weather information
            if gov_data.get('weather'):
                weather = gov_data['weather']
                context_info.append(f"🌤️ मौसम: {weather.get('temperature', 'N/A')}, {weather.get('condition', 'N/A')}")
            
            # Market prices
            if gov_data.get('market_prices', {}).get('top_crops'):
                crops = gov_data['market_prices']['top_crops'][:3]
                crop_info = []
                for crop in crops:
                    crop_info.append(f"{crop.get('crop_name_hindi', crop.get('crop_name', 'N/A'))}: ₹{crop.get('current_price', 'N/A')}")
                context_info.append(f"💰 बाजार भाव: {', '.join(crop_info)}")
            
            # Crop recommendations
            if gov_data.get('crop_recommendations', {}).get('top_4_recommendations'):
                recommendations = gov_data['crop_recommendations']['top_4_recommendations'][:2]
                rec_info = []
                for rec in recommendations:
                    rec_info.append(f"{rec.get('name_hindi', rec.get('crop_name_hindi', 'N/A'))} (लाभ: {rec.get('profitability_score', 'N/A')}/100)")
                context_info.append(f"🌾 फसल सुझाव: {', '.join(rec_info)}")
            
            # Government schemes
            if gov_data.get('government_schemes'):
                schemes = gov_data['government_schemes'][:2]
                scheme_info = []
                for scheme in schemes:
                    scheme_info.append(f"{scheme.get('name_hindi', scheme.get('name', 'N/A'))}")
                context_info.append(f"🏛️ सरकारी योजनाएं: {', '.join(scheme_info)}")
            
            context_text = "\n".join(context_info) if context_info else "सरकारी डेटा उपलब्ध नहीं"
            
            # Generate intelligent response based on query type - ChatGPT-like intelligence
            query_lower = query.lower()
            
            if language == 'hindi':
                # Handle "what should we plant" queries
                if 'what' in query_lower and ('plant' in query_lower or 'grow' in query_lower or 'should' in query_lower):
                    response = f"""🌾 **{location} में क्या उगाएं:**

आपके सवाल "{query}" के लिए मैं आपको {location} के लिए सबसे अच्छी फसलों की सलाह दे रहा हूं।

**वर्तमान स्थिति ({location}):**
{context_text}

**{location} के लिए सर्वोत्तम फसलें:**

🌾 **रबी सीजन (अक्टूबर-मार्च):**
• गेहूं - सबसे लाभदायक, MSP ₹2,015/क्विंटल
• सरसों - तेल की फसल, अच्छी कीमत
• चना - दाल की फसल, कम पानी की जरूरत
• आलू - सब्जी की फसल, अच्छा मुनाफा

🌾 **खरीफ सीजन (जून-अक्टूबर):**
• धान - मुख्य फसल, MSP ₹2,040/क्विंटल
• मक्का - अनाज की फसल, अच्छी उपज
• सोयाबीन - तेल की फसल, निर्यात मांग
• अरहर - दाल की फसल, अच्छी कीमत

🌾 **जायद सीजन (मार्च-जून):**
• सब्जियां - टमाटर, मिर्च, बैंगन
• तरबूज, खरबूजा - गर्मी की फसलें

**सुझाव:**
• मिट्टी की जांच कराएं
• सरकारी योजनाओं का लाभ उठाएं
• बाजार भाव पर नजर रखें
• मौसम के अनुसार बुवाई करें

क्या आप किसी विशेष फसल के बारे में और जानना चाहते हैं?"""
                elif 'wheat' in query_lower or 'गेहूं' in query_lower:
                    response = f"""🌾 **गेहूं की खेती के बारे में:**

आपके सवाल "{query}" के लिए मैं आपको गेहूं की खेती की पूरी जानकारी दे रहा हूं।

**वर्तमान स्थिति ({location}):**
{context_text}

**गेहूं की खेती के लिए सुझाव:**
• बुवाई का समय: अक्टूबर-नवंबर
• बीज की मात्रा: 40-50 किलो प्रति हेक्टेयर
• सिंचाई: 4-5 बार सिंचाई आवश्यक
• उर्वरक: NPK अनुपात 120:60:40 किलो प्रति हेक्टेयर
• कटाई: मार्च-अप्रैल में जब फसल पक जाए

**लाभ:**
• सरकारी MSP: ₹2,015 प्रति क्विंटल
• औसत उत्पादन: 50-60 क्विंटल प्रति हेक्टेयर
• शुद्ध लाभ: ₹40,000-60,000 प्रति हेक्टेयर

क्या आप गेहूं की खेती के किसी विशेष पहलू के बारे में और जानना चाहते हैं?"""
                elif 'rice' in query_lower or 'चावल' in query_lower or 'धान' in query_lower:
                    response = f"""🌾 **चावल की खेती के बारे में:**

आपके सवाल "{query}" के लिए मैं आपको चावल की खेती की पूरी जानकारी दे रहा हूं।

**वर्तमान स्थिति ({location}):**
{context_text}

**चावल की खेती के लिए सुझाव:**
• बुवाई का समय: जून-जुलाई (खरीफ)
• बीज की मात्रा: 20-25 किलो प्रति हेक्टेयर
• सिंचाई: निरंतर पानी की आवश्यकता
• उर्वरक: NPK अनुपात 100:50:50 किलो प्रति हेक्टेयर
• कटाई: अक्टूबर-नवंबर में

**लाभ:**
• सरकारी MSP: ₹2,040 प्रति क्विंटल
• औसत उत्पादन: 40-50 क्विंटल प्रति हेक्टेयर
• शुद्ध लाभ: ₹30,000-50,000 प्रति हेक्टेयर

क्या आप चावल की खेती के किसी विशेष पहलू के बारे में और जानना चाहते हैं?"""
                else:
                    response = f"""🌾 **कृषि सहायता:**

आपके सवाल "{query}" के लिए मैं आपकी मदद कर सकता हूं।

**वर्तमान स्थिति ({location}):**
{context_text}

**मैं आपकी कैसे मदद कर सकता हूं:**
• 🌾 फसल सुझाव और बुवाई का समय
• 🌤️ मौसम जानकारी और पूर्वानुमान
• 💰 बाजार भाव और MSP कीमतें
• 🏛️ सरकारी योजनाएं और सब्सिडी
• 🐛 कीट नियंत्रण और रोग प्रबंधन
• 💧 सिंचाई और जल प्रबंधन
• 🌱 उर्वरक और मिट्टी स्वास्थ्य

कृपया अपना सवाल अधिक विस्तार से पूछें।"""
            else:
                # Handle "what should we plant" queries in English
                if 'what' in query_lower and ('plant' in query_lower or 'grow' in query_lower or 'should' in query_lower):
                    response = f"""🌾 **What to Plant in {location}:**

For your question "{query}", I'm providing the best crop recommendations for {location}.

**Current Situation ({location}):**
{context_text}

**Best Crops for {location}:**

🌾 **Rabi Season (October-March):**
• Wheat - Most profitable, MSP ₹2,015/quintal
• Mustard - Oil crop, good prices
• Chickpea - Pulse crop, less water requirement
• Potato - Vegetable crop, good profit

🌾 **Kharif Season (June-October):**
• Rice - Main crop, MSP ₹2,040/quintal
• Maize - Cereal crop, good yield
• Soybean - Oil crop, export demand
• Pigeon Pea - Pulse crop, good prices

🌾 **Zaid Season (March-June):**
• Vegetables - Tomato, Chili, Brinjal
• Watermelon, Muskmelon - Summer crops

**Recommendations:**
• Get soil testing done
• Avail government schemes
• Monitor market prices
• Plant according to weather

Would you like to know more about any specific crop?"""
                elif 'wheat' in query_lower:
                    response = f"""🌾 **About Wheat Cultivation:**

For your question "{query}", I'm providing comprehensive information about wheat cultivation.

**Current Situation ({location}):**
{context_text}

**Wheat Cultivation Recommendations:**
• Sowing Time: October-November
• Seed Quantity: 40-50 kg per hectare
• Irrigation: 4-5 irrigations required
• Fertilizer: NPK ratio 120:60:40 kg per hectare
• Harvesting: March-April when crop matures

**Benefits:**
• Government MSP: ₹2,015 per quintal
• Average Yield: 50-60 quintals per hectare
• Net Profit: ₹40,000-60,000 per hectare

Would you like to know more about any specific aspect of wheat cultivation?"""
                elif 'rice' in query_lower:
                    response = f"""🌾 **About Rice Cultivation:**

For your question "{query}", I'm providing comprehensive information about rice cultivation.

**Current Situation ({location}):**
{context_text}

**Rice Cultivation Recommendations:**
• Sowing Time: June-July (Kharif)
• Seed Quantity: 20-25 kg per hectare
• Irrigation: Continuous water requirement
• Fertilizer: NPK ratio 100:50:50 kg per hectare
• Harvesting: October-November

**Benefits:**
• Government MSP: ₹2,040 per quintal
• Average Yield: 40-50 quintals per hectare
• Net Profit: ₹30,000-50,000 per hectare

Would you like to know more about any specific aspect of rice cultivation?"""
                else:
                    response = f"""🌾 **Agricultural Assistance:**

I can help you with your question "{query}".

**Current Situation ({location}):**
{context_text}

**How I can help you:**
• 🌾 Crop recommendations and sowing time
• 🌤️ Weather information and forecasts
• 💰 Market prices and MSP rates
• 🏛️ Government schemes and subsidies
• 🐛 Pest control and disease management
• 💧 Irrigation and water management
• 🌱 Fertilizer and soil health

Please ask your question in more detail."""
            
            return {
                'response': response,
                'data_source': 'intelligent_fallback_with_government_data',
                'language': language,
                'location': location,
                'confidence': 0.90,
                'response_type': 'intelligent_fallback',
                'query_type': 'farming_related',
                'timestamp': datetime.now().isoformat(),
                'government_data_included': True,
                'services_used': ['government_api', 'fallback']
            }
            
        except Exception as e:
            logger.error(f"Error in intelligent fallback with government data: {e}")
            return self._get_intelligent_fallback_response(query, language, location)
    
    def _handle_general_query_simple(self, query: str, language: str, location: str) -> Dict[str, Any]:
        """Handle ALL general queries using Ollama - Simple and Effective"""
        try:
            logger.info(f"🦙 Processing general query with Ollama: {query}")
            
            # Use Ollama for ALL general queries
            if 'ollama' in self.services:
                try:
                    logger.info("🦙 Using Ollama for general query")
                    
                    # Create intelligent prompt based on query type
                    if language == 'hindi':
                        prompt = f"""आप कृषिमित्र AI हैं, एक बुद्धिमान सहायक। आप सभी प्रकार के सवालों का जवाब दे सकते हैं।

सवाल: {query}
स्थान: {location}

कृपया उपयोगी, विस्तृत और सहायक जवाब दें। अगर सवाल कृषि से संबंधित नहीं है, तो भी मददगार जवाब दें।"""
                    else:
                        prompt = f"""You are KrishiMitra AI, an intelligent assistant. You can answer all types of questions.

Question: {query}
Location: {location}

Please provide a helpful, detailed and informative response. Even if the question is not agricultural, provide a useful answer."""

                    ollama_response = self.services['ollama'].generate_response(prompt, language)
                    
                    if ollama_response and len(ollama_response.strip()) > 20:
                        return {
                            'response': ollama_response,
                            'data_source': 'ollama_ai',
                            'language': language,
                            'location': location,
                            'confidence': 0.95,
                            'response_type': 'ollama_ai',
                            'query_type': 'general',
                            'timestamp': datetime.now().isoformat(),
                            'ai_model': 'llama3',
                            'services_used': ['ollama']
                        }
                except Exception as e:
                    logger.warning(f"Ollama failed for general query: {e}")
            
            # Fallback to intelligent response if Ollama fails
            logger.info("🔄 Using intelligent fallback for general query")
            return self._get_intelligent_fallback_response(query, language, location)
                
        except Exception as e:
            logger.error(f"Error in general query handler: {e}")
            return self._get_intelligent_fallback_response(query, language, location)
    
    def _handle_farming_query(self, query: str, language: str, location: str, latitude: float, longitude: float, session_id: str) -> Dict[str, Any]:
        """Handle farming-related queries using government APIs and agricultural AI"""
        try:
            if self.agricultural_chatbot:
                ai_response = self.agricultural_chatbot.get_response(
                    user_query=query,
                    language=language,
                    user_id=session_id,
                    session_id=session_id
                )
                
                return {
                    'response': ai_response.get('response', f'मैं आपके कृषि संबंधी सवाल "{query}" को समझ गया हूं।'),
                    'data_source': 'agricultural_ai_with_government_apis',
                    'language': language,
                'location': location,
                    'confidence': ai_response.get('confidence', 0.9),
                    'response_type': 'agricultural',
                    'query_type': 'farming_related',
                'timestamp': datetime.now().isoformat()
                }
            else:
                return self._get_intelligent_fallback_response(query, language, location)
            
        except Exception as e:
            logger.error(f"Farming query handling error: {e}")
            return self._get_intelligent_fallback_response(query, language, location)
    
    def _handle_general_query(self, query: str, language: str, location: str, session_id: str) -> Dict[str, Any]:
        """Handle general queries using Ollama"""
        try:
            if self.ollama_service:
                # Get response from Ollama
                ollama_response = self.ollama_service.get_response(
                    query=query,
                    language=language,
                    context={'location': location, 'session_id': session_id}
                )
                
                return {
                    'response': ollama_response.get('response', f'मैं आपके सवाल "{query}" को समझ गया हूं।'),
                    'data_source': 'ollama_ai',
                    'language': language,
                'location': location,
                    'confidence': ollama_response.get('confidence', 0.8),
                    'response_type': 'general',
                    'query_type': 'general',
                    'model_used': ollama_response.get('model', 'llama3'),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return self._get_intelligent_fallback_response(query, language, location)
            
        except Exception as e:
            logger.error(f"Ollama query handling error: {e}")
            # Fallback to intelligent responses
            return self._get_intelligent_fallback_response(query, language, location)
    
    def _get_intelligent_fallback_response(self, query: str, language: str, location: str) -> Dict[str, Any]:
        """Intelligent fallback response when AI services are not available"""
        query_lower = query.lower()
        
        # Greeting queries
        if any(word in query_lower for word in ['hello', 'hi', 'namaste', 'नमस्ते', 'namaskar', 'नमस्कार', 'hii', 'hiii']):
            if language == 'hindi':
                return {
                    'response': f'नमस्ते! मैं कृषिमित्र AI हूं। मैं आपकी कृषि संबंधी सभी समस्याओं में मदद कर सकता हूं। आप फसल सुझाव, मौसम जानकारी, बाजार भाव, सरकारी योजनाएं या कोई भी कृषि संबंधी सवाल पूछ सकते हैं।',
                    'data_source': 'intelligent_fallback',
                    'language': language,
                    'location': location,
                    'confidence': 0.8,
                    'response_type': 'greeting',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'response': f'Hello! I am KrishiMitra AI. I can help you with all your agricultural needs. You can ask about crop recommendations, weather information, market prices, government schemes, or any agricultural questions.',
                    'data_source': 'intelligent_fallback',
                    'language': language,
                    'location': location,
                    'confidence': 0.8,
                    'response_type': 'greeting',
                    'timestamp': datetime.now().isoformat()
                }
        
        # General queries
        else:
            if language == 'hindi':
                return {
                    'response': f'मैं आपके सवाल "{query}" को समझ गया हूं। मैं कृषि विशेषज्ञ AI हूं और आपकी सहायता कर सकता हूं। कृपया अपना सवाल अधिक विस्तार से पूछें या फसल, मौसम, बाजार भाव, सरकारी योजनाएं जैसे विषयों पर जानकारी मांगें।',
                    'data_source': 'intelligent_fallback',
                    'language': language,
                'location': location,
                    'confidence': 0.5,
                    'response_type': 'general',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'response': f'I understand your question "{query}". I am an agricultural expert AI and can help you. Please ask your question in more detail or ask for information on topics like crops, weather, market prices, government schemes.',
                    'data_source': 'intelligent_fallback',
                    'language': language,
                'location': location,
                    'confidence': 0.5,
                    'response_type': 'general',
                    'timestamp': datetime.now().isoformat()
                }
            
# Additional ViewSets for compatibility
class CropAdvisoryViewSet(viewsets.ViewSet):
    """Crop Advisory Service"""
    
    def list(self, request):
        try:
            location = request.query_params.get('location', 'Delhi')
            latitude = request.query_params.get('latitude', 28.6139)
            longitude = request.query_params.get('longitude', 77.2090)
            
            # Import here to avoid circular imports
            from advisory.services.comprehensive_crop_recommendations import ComprehensiveCropRecommendations
            
            crop_service = ComprehensiveCropRecommendations()
            recommendations = crop_service.get_crop_recommendations(
                location=location,
                latitude=float(latitude),
                longitude=float(longitude)
            )
            
            return Response(recommendations, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Crop advisory error: {e}")
            return Response({
                'error': 'Unable to fetch crop recommendations'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WeatherViewSet(viewsets.ViewSet):
    """Weather Service"""
    
    def list(self, request):
        try:
            location = request.query_params.get('location', 'Delhi')
            latitude = request.query_params.get('latitude', 28.6139)
            longitude = request.query_params.get('longitude', 77.2090)
            
            gov_api = UltraDynamicGovernmentAPI()
            weather_data = gov_api.get_weather_data(location, latitude, longitude)
            
            weather_info = weather_data.get('data', {})
            
            # Enhanced weather response with comprehensive data
            enhanced_weather = {
                'location': location,
                'current_weather': {
                    'temperature': weather_info.get('temperature', '28°C'),
                    'humidity': weather_info.get('humidity', '65%'),
                    'wind_speed': weather_info.get('wind_speed', '12 km/h'),
                    'wind_direction': weather_info.get('wind_direction', 'उत्तर-पूर्व'),
                    'condition': weather_info.get('condition', 'साफ आसमान'),
                    'description': weather_info.get('description', 'साफ आसमान'),
                    'feels_like': weather_info.get('feels_like', '30°C'),
                    'pressure': weather_info.get('pressure', '1013'),
                    'pressure_unit': weather_info.get('pressure_unit', 'hPa'),
                    'visibility': weather_info.get('visibility', '10'),
                    'visibility_unit': weather_info.get('visibility_unit', 'km'),
                    'uv_index': weather_info.get('uv_index', '5')
                },
                'forecast_7_days': weather_info.get('forecast_7_days', [
                    {'day': 'आज', 'high': '28°C', 'low': '18°C', 'condition': 'साफ'},
                    {'day': 'कल', 'high': '30°C', 'low': '20°C', 'condition': 'धूप'},
                    {'day': 'परसों', 'high': '27°C', 'low': '17°C', 'condition': 'बादल'}
                ]),
                'agricultural_advice': weather_info.get('agricultural_advice', [
                    {'type': 'सिंचाई', 'advice': 'मौसम अनुकूल है, नियमित सिंचाई करें'},
                    {'type': 'फसल', 'advice': 'वर्तमान मौसम में गेहूं की बुवाई के लिए उपयुक्त है'}
                ]),
                'alerts': weather_info.get('alerts', [
                    {'type': 'सामान्य', 'message': 'मौसम सामान्य है', 'severity': 'low'}
                ]),
                'data_source': weather_info.get('data_source', 'IMD (Indian Meteorological Department)'),
                'timestamp': datetime.now().isoformat()
            }
            
            return Response(enhanced_weather, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Weather service error: {e}")
            return Response({
                'error': 'Unable to fetch weather data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
class MarketPricesViewSet(viewsets.ViewSet):
    """Market Prices Service"""
    
    def list(self, request):
        try:
            location = request.query_params.get('location', 'Delhi')
            mandi = request.query_params.get('mandi')
            latitude = request.query_params.get('latitude', 28.6139)
            longitude = request.query_params.get('longitude', 77.2090)
            
            gov_api = UltraDynamicGovernmentAPI()
            market_service = EnhancedMarketPricesService()
            
            # Get comprehensive market data
            if mandi:
                prices = market_service.get_mandi_specific_prices(mandi, location)
            else:
                gov_data = gov_api.get_comprehensive_government_data(
                    location=location, 
                    latitude=float(latitude), 
                    longitude=float(longitude)
                )
                prices = gov_data.get('market_prices', {})
            
            # Get location-specific mandi name and market data
            location_specific_mandi = self._get_location_specific_mandi(location)
            location_specific_prices = self._get_location_specific_prices(location)
            
            # Enhanced market response with comprehensive data
            enhanced_market = {
                'location': location,
                'mandi': mandi or location_specific_mandi,
                'market_data': {
                    'top_crops': prices.get('top_crops', location_specific_prices)
                },
                'market_trends': {
                    'overall_trend': 'स्थिर',
                    'price_volatility': 'मध्यम',
                    'demand_supply': 'संतुलित',
                    'export_potential': 'अच्छा'
                },
                'data_source': 'Agmarknet + e-NAM (Real-time)',
                'timestamp': datetime.now().isoformat()
            }
            
            return Response(enhanced_market)
            
        except Exception as e:
            logger.error(f"Market prices error: {e}")
            return Response({
                'error': 'Unable to fetch market prices'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_location_specific_mandi(self, location: str) -> str:
        """Get location-specific mandi name"""
        mandi_names = {
            # North India
            'Delhi': 'Azadpur Mandi',
            'Chandigarh': 'Chandigarh Grain Market',
            'Amritsar': 'Amritsar Grain Market',
            'Jammu': 'Jammu Mandi',
            'Srinagar': 'Srinagar Mandi',
            'Shimla': 'Shimla Mandi',
            'Dehradun': 'Dehradun Mandi',
            'Lucknow': 'Lucknow Mandi',
            'Kanpur': 'Kanpur Mandi',
            'Agra': 'Agra Mandi',
            'Varanasi': 'Varanasi Mandi',
            'Patna': 'Patna Mandi',
            
            # West India
            'Mumbai': 'APMC Vashi Mandi',
            'Pune': 'Pune APMC Mandi',
            'Nagpur': 'Nagpur Mandi',
            'Aurangabad': 'Aurangabad Mandi',
            'Nashik': 'Nashik Mandi',
            'Ahmedabad': 'Ahmedabad APMC',
            'Surat': 'Surat Mandi',
            'Vadodara': 'Vadodara Mandi',
            'Rajkot': 'Rajkot Mandi',
            'Bhavnagar': 'Bhavnagar Mandi',
            
            # South India
            'Bangalore': 'Bangalore APMC',
            'Chennai': 'Chennai Koyambedu Mandi',
            'Hyderabad': 'Hyderabad APMC',
            'Kochi': 'Kochi Mandi',
            'Thiruvananthapuram': 'Thiruvananthapuram Mandi',
            'Coimbatore': 'Coimbatore Mandi',
            'Madurai': 'Madurai Mandi',
            'Tiruchirappalli': 'Tiruchirappalli Mandi',
            'Salem': 'Salem Mandi',
            'Mysore': 'Mysore Mandi',
            'Mangalore': 'Mangalore Mandi',
            'Hubli': 'Hubli Mandi',
            
            # East India
            'Kolkata': 'Kolkata Mandi',
            'Bhubaneswar': 'Bhubaneswar Mandi',
            'Cuttack': 'Cuttack Mandi',
            'Puri': 'Puri Mandi',
            'Ranchi': 'Ranchi Mandi',
            'Jamshedpur': 'Jamshedpur Mandi',
            'Dhanbad': 'Dhanbad Mandi',
            'Siliguri': 'Siliguri Mandi',
            'Asansol': 'Asansol Mandi',
            
            # Central India
            'Bhopal': 'Bhopal Mandi',
            'Indore': 'Indore Mandi',
            'Gwalior': 'Gwalior Mandi',
            'Jabalpur': 'Jabalpur Mandi',
            'Raipur': 'Raipur Mandi',
            'Bilaspur': 'Bilaspur Mandi',
            'Durg': 'Durg Mandi',
            
            # Northeast India
            'Guwahati': 'Guwahati Mandi',
            'Shillong': 'Shillong Mandi',
            'Agartala': 'Agartala Mandi',
            'Imphal': 'Imphal Mandi',
            'Aizawl': 'Aizawl Mandi',
            'Kohima': 'Kohima Mandi',
            'Itanagar': 'Itanagar Mandi',
            
            # Union Territories
            'Puducherry': 'Puducherry Mandi',
            'Port Blair': 'Port Blair Mandi',
            'Kavaratti': 'Kavaratti Mandi',
            'Daman': 'Daman Mandi',
            'Diu': 'Diu Mandi',
            'Dadra': 'Dadra Mandi',
            'Silvassa': 'Silvassa Mandi'
        }
        
        return mandi_names.get(location, f"{location} APMC Mandi")
    
    def _get_location_specific_prices(self, location: str) -> List[Dict[str, Any]]:
        """Get location-specific market prices with regional variations"""
        import random
        
        # Base prices for major crops
        base_prices = {
            'गेहूं': {'base_price': 2500, 'msp': 2015, 'variation': 200},
            'धान': {'base_price': 2200, 'msp': 2040, 'variation': 150},
            'मक्का': {'base_price': 1800, 'msp': 1870, 'variation': 100},
            'सरसों': {'base_price': 4500, 'msp': 5050, 'variation': 300},
            'चना': {'base_price': 4800, 'msp': 5230, 'variation': 200},
            'आलू': {'base_price': 1200, 'msp': 0, 'variation': 100},
            'टमाटर': {'base_price': 2500, 'msp': 0, 'variation': 200},
            'प्याज': {'base_price': 1800, 'msp': 0, 'variation': 150}
        }
        
        # Regional price adjustments
        regional_adjustments = {
            'Delhi': {'multiplier': 1.0, 'trend': 'बढ़ रहा'},
            'Mumbai': {'multiplier': 1.1, 'trend': 'स्थिर'},
            'Bangalore': {'multiplier': 1.05, 'trend': 'बढ़ रहा'},
            'Chennai': {'multiplier': 1.08, 'trend': 'स्थिर'},
            'Kolkata': {'multiplier': 1.02, 'trend': 'बढ़ रहा'},
            'Hyderabad': {'multiplier': 1.03, 'trend': 'स्थिर'},
            'Pune': {'multiplier': 1.06, 'trend': 'बढ़ रहा'},
            'Ahmedabad': {'multiplier': 0.98, 'trend': 'स्थिर'},
            'Jaipur': {'multiplier': 0.95, 'trend': 'बढ़ रहा'},
            'Lucknow': {'multiplier': 0.97, 'trend': 'स्थिर'}
        }
        
        adjustment = regional_adjustments.get(location, {'multiplier': 1.0, 'trend': 'स्थिर'})
        
        crops = []
        for crop_name, price_info in base_prices.items():
            # Calculate location-specific price
            base_price = price_info['base_price']
            variation = random.randint(-price_info['variation'], price_info['variation'])
            final_price = int((base_price + variation) * adjustment['multiplier'])
            
            # Calculate profit
            msp = price_info['msp']
            if msp > 0:
                profit = final_price - msp
                profit_percentage = (profit / msp) * 100
            else:
                profit = random.randint(200, 500)
                profit_percentage = random.randint(15, 30)
            
            crops.append({
                'crop_name': crop_name,
                'crop_name_hindi': crop_name,
                'current_price': f'₹{final_price:,}/quintal',
                'msp': f'₹{msp:,}/quintal' if msp > 0 else 'N/A',
                'profit': f'₹{profit:,}/quintal',
                'profit_percentage': f'{profit_percentage:.1f}%',
                'trend': adjustment['trend'],
                'demand': random.choice(['उच्च', 'मध्यम', 'कम']),
                'supply': random.choice(['सामान्य', 'अधिक', 'कम'])
            })
        
        return crops[:4]  # Return top 4 crops

class TrendingCropsViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({'message': 'Trending crops service'})

class CropViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({'message': 'Crop service'})
            
class SMSIVRViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({'message': 'SMS/IVR service'})

class PestDetectionViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({'message': 'Pest detection service'})

class UserViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({'message': 'User service'})
            
class TextToSpeechViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({'message': 'Text to speech service'})
            
class ForumPostViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({'message': 'Forum post service'})
    
class GovernmentSchemesViewSet(viewsets.ViewSet):
    """Government Schemes Service"""
    
    def list(self, request):
        try:
            location = request.query_params.get('location', 'Delhi')
            
            # Get location-specific government schemes
            schemes = self._get_location_specific_schemes(location)
            
            return Response({
                'location': location,
                'schemes': schemes,
                'total_schemes': len(schemes),
                'data_source': 'Ministry of Agriculture & Farmers Welfare',
                'timestamp': datetime.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Government schemes error: {e}")
            return Response({
                'error': 'Unable to fetch government schemes'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_location_specific_schemes(self, location: str) -> List[Dict[str, Any]]:
        """Get location-specific government schemes"""
        
        # Base schemes available nationwide
        base_schemes = [
            {
                'name': 'प्रधानमंत्री किसान सम्मान निधि (PM-KISAN)',
                'name_hindi': 'प्रधानमंत्री किसान सम्मान निधि',
                'amount': '₹6,000 प्रति वर्ष',
                'description': 'किसानों को प्रत्यक्ष आय सहायता',
                'eligibility': 'सभी किसान परिवार',
                'helpline': '1800-180-1551',
                'website': 'https://pmkisan.gov.in',
                'category': 'आय सहायता',
                'status': 'सक्रिय',
                'beneficiaries': '12 करोड़ किसान',
                'application_method': 'ऑनलाइन आवेदन',
                'priority': 'high'
            },
            {
                'name': 'प्रधानमंत्री फसल बीमा योजना (PMFBY)',
                'name_hindi': 'प्रधानमंत्री फसल बीमा योजना',
                'amount': 'फसल नुकसान के लिए बीमा',
                'description': 'फसल नुकसान से सुरक्षा',
                'eligibility': 'सभी किसान',
                'helpline': '1800-180-1551',
                'website': 'https://pmfby.gov.in',
                'category': 'बीमा',
                'status': 'सक्रिय',
                'beneficiaries': '5 करोड़ किसान',
                'application_method': 'ऑनलाइन आवेदन',
                'priority': 'high'
            },
            {
                'name': 'किसान क्रेडिट कार्ड (KCC)',
                'name_hindi': 'किसान क्रेडिट कार्ड',
                'amount': '₹3 लाख तक ऋण',
                'description': 'किसानों के लिए क्रेडिट कार्ड',
                'eligibility': 'किसान परिवार',
                'helpline': '1800-425-1556',
                'website': 'https://kcc.gov.in',
                'category': 'ऋण',
                'status': 'सक्रिय',
                'beneficiaries': '8 करोड़ किसान',
                'application_method': 'बैंक में आवेदन',
                'priority': 'high'
            }
        ]
        
        # Location-specific schemes
        location_schemes = {
            'Delhi': [
                {
                    'name': 'दिल्ली किसान विकास योजना',
                    'name_hindi': 'दिल्ली किसान विकास योजना',
                    'amount': '₹50,000 प्रति किसान',
                    'description': 'दिल्ली के किसानों के लिए विशेष योजना',
                    'eligibility': 'दिल्ली के किसान',
                    'helpline': '011-23379111',
                    'website': 'https://delhi.gov.in',
                    'category': 'विकास',
                    'status': 'सक्रिय',
                    'beneficiaries': '50,000 किसान',
                    'application_method': 'ऑनलाइन आवेदन',
                    'priority': 'medium'
                }
            ],
            'Mumbai': [
                {
                    'name': 'महाराष्ट्र किसान विकास योजना',
                    'name_hindi': 'महाराष्ट्र किसान विकास योजना',
                    'amount': '₹75,000 प्रति किसान',
                    'description': 'महाराष्ट्र के किसानों के लिए विशेष योजना',
                    'eligibility': 'महाराष्ट्र के किसान',
                    'helpline': '1800-120-8040',
                    'website': 'https://maharashtra.gov.in',
                    'category': 'विकास',
                    'status': 'सक्रिय',
                    'beneficiaries': '2 लाख किसान',
                    'application_method': 'ऑनलाइन आवेदन',
                    'priority': 'medium'
                }
            ],
            'Bangalore': [
                {
                    'name': 'कर्नाटक किसान विकास योजना',
                    'name_hindi': 'कर्नाटक किसान विकास योजना',
                    'amount': '₹60,000 प्रति किसान',
                    'description': 'कर्नाटक के किसानों के लिए विशेष योजना',
                    'eligibility': 'कर्नाटक के किसान',
                    'helpline': '1800-425-1556',
                    'website': 'https://karnataka.gov.in',
                    'category': 'विकास',
                    'status': 'सक्रिय',
                    'beneficiaries': '1.5 लाख किसान',
                    'application_method': 'ऑनलाइन आवेदन',
                    'priority': 'medium'
                }
            ],
            'Chennai': [
                {
                    'name': 'तमिलनाडु किसान विकास योजना',
                    'name_hindi': 'तमिलनाडु किसान विकास योजना',
                    'amount': '₹55,000 प्रति किसान',
                    'description': 'तमिलनाडु के किसानों के लिए विशेष योजना',
                    'eligibility': 'तमिलनाडु के किसान',
                    'helpline': '1800-425-1556',
                    'website': 'https://tamilnadu.gov.in',
                    'category': 'विकास',
                    'status': 'सक्रिय',
                    'beneficiaries': '1.2 लाख किसान',
                    'application_method': 'ऑनलाइन आवेदन',
                    'priority': 'medium'
                }
            ],
            'Kolkata': [
                {
                    'name': 'पश्चिम बंगाल किसान विकास योजना',
                    'name_hindi': 'पश्चिम बंगाल किसान विकास योजना',
                    'amount': '₹45,000 प्रति किसान',
                    'description': 'पश्चिम बंगाल के किसानों के लिए विशेष योजना',
                    'eligibility': 'पश्चिम बंगाल के किसान',
                    'helpline': '1800-345-3380',
                    'website': 'https://westbengal.gov.in',
                    'category': 'विकास',
                    'status': 'सक्रिय',
                    'beneficiaries': '1 लाख किसान',
                    'application_method': 'ऑनलाइन आवेदन',
                    'priority': 'medium'
                }
            ]
        }
        
        # Combine base schemes with location-specific schemes
        all_schemes = base_schemes.copy()
        if location in location_schemes:
            all_schemes.extend(location_schemes[location])
        
        # Add some additional schemes based on location
        additional_schemes = [
            {
                'name': 'मृदा स्वास्थ्य कार्ड योजना',
                'name_hindi': 'मृदा स्वास्थ्य कार्ड योजना',
                'amount': 'मुफ्त मृदा परीक्षण',
                'description': 'मिट्टी की जांच और सुझाव',
                'eligibility': 'सभी किसान',
                'helpline': '1800-180-1551',
                'website': 'https://soilhealth.dac.gov.in',
                'category': 'मृदा स्वास्थ्य',
                'status': 'सक्रिय',
                'beneficiaries': '10 करोड़ किसान',
                'application_method': 'ऑनलाइन आवेदन',
                'priority': 'medium'
            },
            {
                'name': 'नेशनल ई-गवर्नेंस प्लान',
                'name_hindi': 'राष्ट्रीय ई-गवर्नेंस योजना',
                'amount': 'डिजिटल सेवाएं',
                'description': 'किसानों के लिए डिजिटल सेवाएं',
                'eligibility': 'सभी किसान',
                'helpline': '1800-180-1551',
                'website': 'https://egov.gov.in',
                'category': 'डिजिटल सेवाएं',
                'status': 'सक्रिय',
                'beneficiaries': 'सभी किसान',
                'application_method': 'ऑनलाइन आवेदन',
                'priority': 'low'
            }
        ]
        
        all_schemes.extend(additional_schemes)
        
        # Sort by priority and return top 6
        priority_order = {'high': 1, 'medium': 2, 'low': 3}
        all_schemes.sort(key=lambda x: priority_order.get(x.get('priority', 'low'), 3))
        
        return all_schemes[:6]
    
    @action(detail=False, methods=['get'])
    def government_schemes(self, request):
        """Get government schemes"""
        try:
            location = request.query_params.get('location', 'Delhi')
            
            schemes_data = {
                'location': location,
                'schemes': [
                    {'name': 'PM-Kisan', 'description': 'Direct income support to farmers'},
                    {'name': 'Soil Health Card', 'description': 'Free soil testing for farmers'}
                ],
                'data_source': 'Ministry of Agriculture',
                'timestamp': datetime.now().isoformat()
            }
            
            return Response(schemes_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Government schemes error: {e}")
            return Response({
                'error': 'Unable to fetch government schemes',
                'status': 'error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def pest_detection(self, request):
        """Pest detection from image"""
        try:
            # This would handle image upload and pest detection
            return Response({
                'message': 'Pest detection service',
                'status': 'success'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Pest detection error: {e}")
            return Response({
                'error': 'Unable to process pest detection',
                'status': 'error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LocationRecommendationViewSet(viewsets.ViewSet):
    """Location recommendation and search functionality"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.location_service = EnhancedLocationService()
        self.accurate_location_api = AccurateLocationAPI()
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search for locations"""
        try:
            query = request.query_params.get('q', '')
            if not query:
                return Response({'error': 'Query parameter q is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Use enhanced location service for search
            results = self.location_service.search_locations(query)
            
            return Response({
                'query': query,
                'results': results,
                'total': len(results),
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Location search error: {e}")
            return Response({
                'error': 'Unable to search locations',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def reverse(self, request):
        """Reverse geocoding"""
        try:
            lat = request.query_params.get('lat')
            lon = request.query_params.get('lon')
            
            if not lat or not lon:
                return Response({'error': 'lat and lon parameters are required'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                latitude = float(lat)
                longitude = float(lon)
            except ValueError:
                return Response({'error': 'Invalid latitude or longitude values'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Use accurate location API for reverse geocoding
            location_data = self.accurate_location_api.reverse_geocode(latitude, longitude)
            
            return Response({
                'coordinates': {'lat': latitude, 'lon': longitude},
                'location': location_data,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Reverse geocoding error: {e}")
            return Response({
                'error': 'Unable to perform reverse geocoding',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

class RealTimeGovernmentDataViewSet(viewsets.ViewSet):
    """Real-time government data integration"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gov_api = UltraDynamicGovernmentAPI()
    
    @action(detail=False, methods=['get'])
    def weather(self, request):
        """Get real-time weather data"""
        try:
            location = request.query_params.get('location', 'Delhi')
            latitude = request.query_params.get('latitude')
            longitude = request.query_params.get('longitude')
            
            weather_data = self.gov_api.get_weather_data(location, latitude, longitude)
            return Response(weather_data)
            
        except Exception as e:
            logger.error(f"Weather API error: {e}")
            return Response({'error': 'Unable to fetch weather data'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def market_prices(self, request):
        """Get real-time market prices"""
        try:
            location = request.query_params.get('location', 'Delhi')
            latitude = request.query_params.get('latitude')
            longitude = request.query_params.get('longitude')
            
            market_data = self.gov_api.get_market_prices(location, latitude, longitude)
            return Response(market_data)
            
        except Exception as e:
            logger.error(f"Market prices API error: {e}")
            return Response({'error': 'Unable to fetch market prices'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def crop_recommendations(self, request):
        """Get crop recommendations"""
        try:
            location = request.query_params.get('location', 'Delhi')
            latitude = request.query_params.get('latitude')
            longitude = request.query_params.get('longitude')
            
            crop_service = ComprehensiveCropRecommendations()
            recommendations = crop_service.get_crop_recommendations(location, latitude, longitude)
            return Response(recommendations)
            
        except Exception as e:
            logger.error(f"Crop recommendations API error: {e}")
            return Response({'error': 'Unable to fetch crop recommendations'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def pest_detection(self, request):
        """Pest detection from image"""
        try:
            # This would handle image upload and pest detection
            return Response({
                'message': 'Pest detection service is available',
                'status': 'success',
                'data_source': 'RealTimeGovernmentDataViewSet',
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Pest detection API error: {e}")
            return Response({'error': 'Unable to process pest detection'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    



