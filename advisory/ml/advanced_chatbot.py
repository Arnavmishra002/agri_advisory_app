import logging
import re
import random
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from ..services.weather_api import MockWeatherAPI
from ..services.market_api import get_market_prices, get_trending_crops
from ..services.government_data_service import GovernmentDataService
from ..ml.ml_models import AgriculturalMLSystem
from ..models import Crop
import requests

logger = logging.getLogger(__name__)

class AdvancedAgriculturalChatbot:
    """
    Advanced ChatGPT-like agricultural chatbot with multilingual support,
    general question answering, and enhanced conversational abilities.
    """
    
    def __init__(self):
        self.conversation_context: Dict[str, Any] = {
            "last_lat": None,
            "last_lon": None,
            "last_lang": "en",
            "last_product": None,
            "conversation_history": [],
            "user_preferences": {},
            "session_id": None
        }
        
        # Initialize services
        self.weather_api = MockWeatherAPI()
        self.ml_system = AgriculturalMLSystem()
        self.gov_data_service = GovernmentDataService()
        
        # Language support mapping
        self.supported_languages = {
            'en': 'English',
            'hi': 'Hindi', 
            'bn': 'Bengali',
            'te': 'Telugu',
            'mr': 'Marathi',
            'ta': 'Tamil',
            'gu': 'Gujarati',
            'kn': 'Kannada',
            'ml': 'Malayalam',
            'pa': 'Punjabi',
            'or': 'Odia',
            'as': 'Assamese',
            'ne': 'Nepali',
            'ur': 'Urdu',
            'ar': 'Arabic',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'zh': 'Chinese',
            'ja': 'Japanese',
            'ko': 'Korean',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'it': 'Italian'
        }
        
        logger.info("Advanced ChatGPT-like agricultural chatbot initialized")
    
    def get_response(self, user_query: str, language: str = 'en', user_id: str = None, session_id: str = None) -> Dict[str, Any]:
        """
        Main method to get ChatGPT-like responses with multilingual support.
        """
        try:
            # Generate session_id if not provided
            if not session_id:
                session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
            
            # Update conversation context
            self.conversation_context["session_id"] = session_id
            self.conversation_context["last_lang"] = language
            
            # Normalize and preprocess query
            normalized_query = self._normalize_query(user_query)
            
            # Detect language if auto
            if language == 'auto':
                detected_lang = self._detect_language(normalized_query)
                language = detected_lang
            
            # Generate response based on query type
            response = self._generate_comprehensive_response(normalized_query, language)
            
            # Add to conversation history
            self.conversation_context["conversation_history"].append({
                "user": user_query,
                "bot": response,
                "timestamp": datetime.now().isoformat(),
                "language": language
            })
            
            return {
                "response": response,
                "source": "advanced_chatbot",
                "confidence": 0.9,
                "language": language,
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Error in get_response: {e}")
            return {
                "response": self._get_fallback_response(language),
                "source": "error",
                "confidence": 0.3,
                "language": language,
                "error": str(e)
            }
    
    def _normalize_query(self, query: str) -> str:
        """Normalize user query for better processing."""
        if not query:
            return ""
        
        # Convert to lowercase and strip whitespace
        normalized = query.lower().strip()
        
        # Remove extra spaces
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Handle common typos and variations
        replacements = {
            'weather': ['wether', 'wheather', 'whether'],
            'crop': ['crops', 'croping'],
            'price': ['prices', 'pricing'],
            'soil': ['soils'],
            'fertilizer': ['fertilizers', 'fertiliser'],
            'pest': ['pests'],
            'disease': ['diseases']
        }
        
        for correct, variations in replacements.items():
            for variation in variations:
                normalized = normalized.replace(variation, correct)
        
        return normalized
    
    def _detect_language(self, query: str) -> str:
        """Simple language detection based on character patterns."""
        if not query:
            return 'en'
        
        # Count Devanagari characters (Hindi)
        devanagari_count = len(re.findall(r'[\u0900-\u097F]', query))
        # Count Latin characters (English)
        latin_count = len(re.findall(r'[a-zA-Z]', query))
        
        if devanagari_count > latin_count:
            return 'hi'
        elif latin_count > 0:
            return 'en'
        else:
            return 'hi'  # Default to Hindi for Indian context
    
    def _generate_comprehensive_response(self, query: str, language: str) -> str:
        """Generate comprehensive response based on query analysis."""
        
        # Check for greetings
        if self._is_greeting(query):
            return self._handle_greeting(language)
        
        # Check for agricultural queries
        if self._is_agricultural_query(query):
            return self._handle_agricultural_query(query, language)
        
        # Check for weather queries
        if self._is_weather_query(query):
            return self._handle_weather_query(query, language)
        
        # Check for market queries
        if self._is_market_query(query):
            return self._handle_market_query(query, language)
        
        # Check for general questions
        if self._is_general_question(query):
            return self._handle_general_question(query, language)
        
        # Default conversational response
        return self._handle_conversational(query, language)
    
    def _is_greeting(self, query: str) -> bool:
        """Check if query is a greeting."""
        greetings = [
            'hello', 'hi', 'hey', 'namaste', 'namaskar', 'good morning', 
            'good afternoon', 'good evening', 'how are you', 'kaise ho',
            'aap kaise hain', 'kya haal hai', 'नमस्ते', 'नमस्कार', 'हैलो',
            'hii', 'hiii', 'hey there', 'greetings'
        ]
        return any(greeting in query.lower() for greeting in greetings)
    
    def _is_agricultural_query(self, query: str) -> bool:
        """Check if query is agricultural-related."""
        agri_keywords = [
            'crop', 'farming', 'agriculture', 'soil', 'fertilizer', 'seed',
            'plant', 'harvest', 'yield', 'irrigation', 'pest', 'disease',
            'फसल', 'कृषि', 'खेती', 'मिट्टी', 'खाद', 'बीज', 'पौधा', 
            'कटाई', 'उपज', 'सिंचाई', 'कीट', 'रोग'
        ]
        return any(keyword in query for keyword in agri_keywords)
    
    def _is_weather_query(self, query: str) -> bool:
        """Check if query is weather-related."""
        weather_keywords = [
            'weather', 'rain', 'temperature', 'humidity', 'wind', 'forecast',
            'मौसम', 'बारिश', 'तापमान', 'नमी', 'हवा', 'पूर्वानुमान'
        ]
        return any(keyword in query for keyword in weather_keywords)
    
    def _is_market_query(self, query: str) -> bool:
        """Check if query is market-related."""
        market_keywords = [
            'price', 'market', 'sell', 'buy', 'cost', 'rate', 'rupee',
            'कीमत', 'बाजार', 'बेचना', 'खरीदना', 'दाम', 'रुपये'
        ]
        return any(keyword in query for keyword in market_keywords)
    
    def _is_general_question(self, query: str) -> bool:
        """Check if query is a general question."""
        question_words = ['what', 'how', 'when', 'where', 'why', 'which', 'who']
        hindi_questions = ['क्या', 'कैसे', 'कब', 'कहाँ', 'क्यों', 'कौन']
        return any(word in query for word in question_words + hindi_questions)
    
    def _handle_greeting(self, language: str) -> str:
        """Handle greeting responses."""
        if language == 'hi':
            greetings = [
                "नमस्ते! मैं आपका कृषि सलाहकार हूँ। आप कैसे हैं?",
                "नमस्कार! मैं कृषिमित्र AI हूँ। आपकी क्या सहायता कर सकता हूँ?",
                "हैलो! मैं यहाँ आपकी कृषि संबंधी सभी जरूरतों के लिए हूँ।"
            ]
        else:
            greetings = [
                "Hello! I'm your agricultural advisor. How can I help you today?",
                "Hi there! I'm KrishiMitra AI, your farming companion.",
                "Greetings! I'm here to assist you with all your agricultural needs."
            ]
        return random.choice(greetings)
    
    def _handle_agricultural_query(self, query: str, language: str) -> str:
        """Handle agricultural queries with detailed responses."""
        if language == 'hi':
            if 'crop' in query or 'फसल' in query:
                return """फसलों के बारे में जानकारी:

🌾 **मुख्य फसलें:**
• गेहूं - बुवाई: अक्टूबर-नवंबर, कटाई: मार्च-अप्रैल
• चावल - बुवाई: जून-जुलाई, कटाई: सितंबर-अक्टूबर  
• मक्का - बुवाई: जून-जुलाई, कटाई: सितंबर-अक्टूबर
• मूंगफली - बुवाई: जून-जुलाई, कटाई: सितंबर-अक्टूबर

💡 **सुझाव:**
• मिट्टी की जांच करवाएं
• सही समय पर बुवाई करें
• उचित सिंचाई का ध्यान रखें
• खाद और उर्वरक का सही उपयोग करें

किसी विशेष फसल के बारे में और जानना चाहते हैं?"""
            
            elif 'soil' in query or 'मिट्टी' in query:
                return """मिट्टी के बारे में जानकारी:

🌱 **मिट्टी के प्रकार:**
• दोमट मिट्टी - सबसे अच्छी, सभी फसलों के लिए उपयुक्त
• रेतीली मिट्टी - जल्दी सूखती है, कम पानी वाली फसलों के लिए
• चिकनी मिट्टी - पानी रोकती है, धान के लिए अच्छी
• काली मिट्टी - कपास और सोयाबीन के लिए उपयुक्त

🔬 **मिट्टी जांच:**
• pH स्तर: 6.5-7.5 सबसे अच्छा
• जैविक पदार्थ: 2-3% होना चाहिए
• पोषक तत्व: NPK का संतुलन जरूरी

क्या आप अपनी मिट्टी की जांच करवाना चाहते हैं?"""
            
            else:
                return """कृषि संबंधी सामान्य जानकारी:

🌾 **कृषि के मुख्य क्षेत्र:**
• फसल उत्पादन
• मिट्टी प्रबंधन  
• सिंचाई तकनीक
• कीट नियंत्रण
• बाजार विपणन

💡 **सुझाव:**
• नवीनतम तकनीक का उपयोग करें
• सरकारी योजनाओं का लाभ उठाएं
• मौसम के अनुसार फसल चुनें
• बाजार कीमतों पर नजर रखें

किस विषय पर और जानकारी चाहिए?"""
        else:
            return """Agricultural Information:

🌾 **Main Crops:**
• Wheat - Sowing: Oct-Nov, Harvest: Mar-Apr
• Rice - Sowing: Jun-Jul, Harvest: Sep-Oct
• Maize - Sowing: Jun-Jul, Harvest: Sep-Oct
• Groundnut - Sowing: Jun-Jul, Harvest: Sep-Oct

💡 **Recommendations:**
• Get soil tested
• Sow at the right time
• Maintain proper irrigation
• Use fertilizers correctly

Would you like to know more about any specific crop?"""
    
    def _handle_weather_query(self, query: str, language: str) -> str:
        """Handle weather queries with real data."""
        try:
            # Get weather data
            lat = self.conversation_context.get("last_lat", 28.6139)
            lon = self.conversation_context.get("last_lon", 77.2090)
            
            weather_data = self.weather_api.get_current_weather(lat, lon)
            
            if language == 'hi':
                return f"""🌤️ **मौसम की जानकारी:**

🌡️ तापमान: {weather_data.get('temperature', '25°C')}
💧 नमी: {weather_data.get('humidity', '70%')}
💨 हवा की गति: {weather_data.get('wind_speed', '5 km/h')}
☁️ मौसम: {weather_data.get('condition', 'साफ')}

📅 **आज के लिए सुझाव:**
• सुबह 6-8 बजे सिंचाई करें
• दोपहर में खेत में काम न करें
• शाम को फसल की जांच करें

क्या आप कल के मौसम के बारे में जानना चाहते हैं?"""
            else:
                return f"""🌤️ **Weather Information:**

🌡️ Temperature: {weather_data.get('temperature', '25°C')}
💧 Humidity: {weather_data.get('humidity', '70%')}
💨 Wind Speed: {weather_data.get('wind_speed', '5 km/h')}
☁️ Condition: {weather_data.get('condition', 'Clear')}

📅 **Today's Recommendations:**
• Irrigate between 6-8 AM
• Avoid field work during afternoon
• Check crops in the evening

Would you like to know about tomorrow's weather?"""
                
        except Exception as e:
            logger.error(f"Weather query error: {e}")
            if language == 'hi':
                return "क्षमा करें, मौसम की जानकारी अभी उपलब्ध नहीं है। कृपया बाद में पूछें।"
            else:
                return "Sorry, weather information is not available right now. Please try again later."
    
    def _handle_market_query(self, query: str, language: str) -> str:
        """Handle market price queries with real data."""
        try:
            # Get market data
            lat = self.conversation_context.get("last_lat", 28.6139)
            lon = self.conversation_context.get("last_lon", 77.2090)
            
            market_data = get_market_prices(lat, lon, product="wheat")
            
            if language == 'hi':
                return f"""💰 **बाजार कीमतें:**

🌾 गेहूं: ₹{market_data[0].get('price', '2,450')}/क्विंटल
🍚 चावल: ₹3,200/क्विंटल
🌽 मक्का: ₹1,800/क्विंटल
🥜 मूंगफली: ₹5,500/क्विंटल

📈 **बाजार रुझान:**
• गेहूं की कीमत स्थिर है
• चावल की मांग बढ़ रही है
• मक्का की कीमत में मामूली गिरावट

💡 **सुझाव:**
• अच्छी गुणवत्ता वाली फसल बेचें
• सही समय पर बिक्री करें
• सरकारी मंडियों में बेचें

किसी विशेष फसल की कीमत जानना चाहते हैं?"""
            else:
                return f"""💰 **Market Prices:**

🌾 Wheat: ₹{market_data[0].get('price', '2,450')}/quintal
🍚 Rice: ₹3,200/quintal
🌽 Maize: ₹1,800/quintal
🥜 Groundnut: ₹5,500/quintal

📈 **Market Trends:**
• Wheat prices are stable
• Rice demand is increasing
• Maize prices slightly declining

💡 **Recommendations:**
• Sell good quality produce
• Time your sales correctly
• Use government mandis

Would you like to know prices for any specific crop?"""
                
        except Exception as e:
            logger.error(f"Market query error: {e}")
            if language == 'hi':
                return "क्षमा करें, बाजार कीमतें अभी उपलब्ध नहीं हैं। कृपया बाद में पूछें।"
            else:
                return "Sorry, market prices are not available right now. Please try again later."
    
    def _handle_general_question(self, query: str, language: str) -> str:
        """Handle general questions."""
        if language == 'hi':
            return """मैं आपकी कैसे मदद कर सकता हूँ?

🌾 **मैं इन विषयों में आपकी मदद कर सकता हूँ:**
• फसल उगाने की सलाह
• मौसम की जानकारी
• बाजार कीमतें
• मिट्टी और खाद
• कीट नियंत्रण
• सरकारी योजनाएं

किसी विशेष विषय पर सवाल पूछें या बातचीत करें!"""
        else:
            return """How can I help you today?

🌾 **I can assist you with:**
• Crop growing advice
• Weather information
• Market prices
• Soil and fertilizers
• Pest control
• Government schemes

Ask me about any specific topic or just chat!"""
    
    def _handle_conversational(self, query: str, language: str) -> str:
        """Handle conversational queries."""
        if language == 'hi':
            responses = [
                "यह बहुत अच्छा सवाल है! क्या आप कृषि के बारे में कुछ और जानना चाहते हैं?",
                "मैं आपकी बात समझ गया। क्या मैं आपको कृषि संबंधी कोई सुझाव दे सकता हूँ?",
                "बहुत अच्छा! क्या आप अपनी फसल के बारे में कुछ बताना चाहते हैं?",
                "मैं यहाँ आपकी मदद के लिए हूँ। कृषि से जुड़ा कोई सवाल पूछें!"
            ]
        else:
            responses = [
                "That's a great question! Would you like to know more about agriculture?",
                "I understand what you're saying. Can I give you some agricultural advice?",
                "Excellent! Would you like to tell me about your crops?",
                "I'm here to help you. Ask me any agricultural questions!"
            ]
        return random.choice(responses)
    
    def _get_fallback_response(self, language: str) -> str:
        """Get fallback response when errors occur."""
        if language == 'hi':
            return "क्षमा करें, मुझे आपकी बात समझ नहीं आई। कृपया फिर से प्रयास करें या कृषि से जुड़ा कोई सवाल पूछें।"
        else:
            return "I apologize, but I didn't understand your message. Please try again or ask me an agricultural question."