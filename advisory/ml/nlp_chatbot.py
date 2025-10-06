import logging
import re
import random
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class NLPAgriculturalChatbot:
    def __init__(self):
        # Simple pattern matching chatbot - no heavy ML models for now
        self.conversation_context = {}
        logger.info("Enhanced conversational chatbot initialized")
    
    def get_response(self, user_query: str, language: str = 'en') -> Dict[str, Any]:
        """
        Generates a conversational response like ChatGPT.
        Supports multiple languages, grammatic errors, and casual conversations.
        """
        try:
            # Normalize the input (handle casing, punctuation, common typos)
            normalized_query = self._normalize_query(user_query)
            
            # Detect language (auto-detect if not specified)
            detected_language = self._detect_language(normalized_query)
            if detected_language != language:
                logger.info(f"Language detected: {detected_language}, using instead of {language}")
                language = detected_language
            
            # Get response based on intent
            response = self._generate_response(normalized_query, language)
            
            return {
                "response": response,
                "source": "conversational_ai",
                "confidence": 0.9,
                "language": language
            }

        except Exception as e:
            logger.error(f"Error generating response for query '{user_query}': {e}")
            return {
                "response": self._handle_error_response(language),
                "source": "error",
                "confidence": 0.3,
                "language": language
            }

    def _get_dynamic_context(self, user_query: str, language: str) -> str:
        """
        This function would dynamically fetch context relevant to the user's query.
        For example, if the user asks about "wheat diseases", this would fetch
        information about wheat diseases from a database or external knowledge source.
        For now, it returns a generic agricultural context or a more specific one based on keywords.
        """
        if "weather" in user_query.lower():
            return "Current and forecast weather conditions are important for agriculture. Farmers often need information about rainfall, temperature, and humidity for planting and harvesting decisions."
        elif "soil" in user_query.lower() or "fertilizer" in user_query.lower():
            return "Soil health and fertility are crucial. Different crops require different soil types (loamy, sandy, clayey) and nutrient levels (Nitrogen, Phosphorus, Potassium). Fertilizers are used to replenish soil nutrients."
        elif "crop recommendation" in user_query.lower() or "what to plant" in user_query.lower():
            return "Crop recommendations depend on various factors like soil type, weather conditions, season (Kharif, Rabi, Zaid), water availability, and market demand. Some common crops include wheat, rice, maize, cotton, and sugarcane."
        elif "market price" in user_query.lower() or "price" in user_query.lower():
            return "Market prices for agricultural commodities fluctuate based on supply, demand, government policies, and seasonality. Platforms like Agmarknet and e-NAM provide real-time market price data for various crops."
        
        # Generic agricultural context if no specific keyword is found
        return "Agriculture is the science and art of cultivating plants and livestock. It is the key development in the rise of sedentary human civilization, whereby farming of domesticated species created food surpluses that enabled people to live in cities. Agricultural development and sustainable practices are essential for food security."

    def _normalize_query(self, query: str) -> str:
        """Normalize and clean the user query"""
        if not query:
            return ""
        
        # Remove extra whitespace and normalize
        normalized = re.sub(r'\s+', ' ', query.strip())
        
        # Handle common typos and variations
        typo_corrections = {
            'wether': 'weather', 'fertiliser': 'fertilizer', 'croping': 'cropping',
            'agricultre': 'agriculture', 'helo': 'hello', 'hii': 'hi', 
            'thnk': 'thank', 'pls': 'please', 'wht': 'what', 'hw': 'how'
        }
        
        for typo, correction in typo_corrections.items():
            normalized = re.sub(r'\b' + re.escape(typo) + r'\b', correction, normalized, flags=re.IGNORECASE)
        
        return normalized
    
    def _detect_language(self, text: str) -> str:
        """Detect language of the input text"""
        if not text:
            return 'en'
        
        # Check for Hindi/Devanagari script
        if re.search(r'[\u0900-\u097F]', text):
            return 'hi'
        
        # Check for Bengali
        if re.search(r'[\u0980-\u09FF]', text):
            return 'bn'
        
        # Check for Telugu
        if re.search(r'[\u0C00-\u0C7F]', text):
            return 'te'
        
        # Check for Tamil
        if re.search(r'[\u0B80-\u0BFF]', text):
            return 'ta'
        
        # Check for Gujarati
        if re.search(r'[\u0A80-\u0AFF]', text):
            return 'gu'
        
        # Check for Kannada
        if re.search(r'[\u0C80-\u0CFF]', text):
            return 'kn'
        
        # Check for Malayalam
        if re.search(r'[\u0D00-\u0D7F]', text):
            return 'ml'
        
        # Check for Hinglish patterns
        hinglish_patterns = [
            r'\b(bhai|hai|haiya|humein|mujhe|tum|main|kyu|kya|kaise|kab|kahan)\b',
            r'\b(acha|thik|bilkul|zaroor|pakka|sahi|galat)\b'
        ]
        
        for pattern in hinglish_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return 'hinglish'
        
        return 'en'
    
    def _generate_response(self, query: str, language: str) -> str:
        """Generate appropriate response based on query type"""
        query_lower = query.lower()
        
        # Greeting patterns
        greeting_patterns = [
            'hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening',
            'namaste', 'namaskar', 'how are you', 'what\'s up', 'wassup'
        ]
        
        if any(pattern in query_lower for pattern in greeting_patterns):
            return self._handle_greeting(query, language)
        
        # Agricultural patterns
        agri_patterns = [
            'crop', 'farm', 'agriculture', 'fertilizer', 'soil', 'weather',
            'market price', 'planting', 'harvesting', 'irrigation', 'pest',
            'disease', 'yield', 'production', 'खेती', 'कृषि', 'फसल', 'मिट्टी'
        ]
        
        if any(pattern in query_lower for pattern in agri_patterns):
            return self._handle_agricultural_query(query, language)
        
        # Weather patterns
        weather_patterns = [
            'weather', 'rain', 'temperature', 'humidity', 'forecast',
            'मौसम', 'बारिश', 'तापमान', 'आर्द्रता'
        ]
        
        if any(pattern in query_lower for pattern in weather_patterns):
            return self._handle_weather_query(query, language)
        
        # Market/Price patterns
        market_patterns = [
            'price', 'market', 'cost', 'rate', 'selling', 'buying',
            'बाजार', 'कीमत', 'दर', 'मूल्य'
        ]
        
        if any(pattern in query_lower for pattern in market_patterns):
            return self._handle_market_query(query, language)
        
        # General question patterns
        question_patterns = [
            'what is', 'how to', 'why', 'when', 'where', 'who', 'which',
            'explain', 'tell me about', 'क्या है', 'कैसे', 'क्यों', 'कब', 'कहाँ'
        ]
        
        if any(pattern in query_lower for pattern in question_patterns):
            return self._handle_general_question(query, language)
        
        # Conversational patterns
        conversational_patterns = [
            'thank you', 'thanks', 'bye', 'goodbye', 'see you', 'nice talking',
            'धन्यवाद', 'शुक्रिया', 'अलविदा', 'फिर मिलते हैं'
        ]
        
        if any(pattern in query_lower for pattern in conversational_patterns):
            return self._handle_conversational(query, language)
        
        return self._handle_general(query, language)
    
    def _handle_greeting(self, query: str, language: str) -> str:
        """Handle greeting responses"""
        current_time = datetime.now().hour
        time_of_day = "morning" if 6 <= current_time < 12 else "afternoon" if 12 <= current_time < 18 else "evening"
        
        if language in ['hi', 'hinglish']:
            greetings = [
                f"नमस्ते! शुभ {time_of_day}! मैं कृषिमित्र हूं, आपका AI कृषि सलाहकार। मैं आपकी हर तरह की मदद कर सकता हूं - खेती, मौसम, बाजार भाव, या कोई भी सवाल। आप कैसे हैं? 🌾",
                f"हैलो भाई! {time_of_day} का नमस्कार! मैं यहां हूं आपकी कृषि संबंधी सभी जरूरतों के लिए। बताइए कैसी मदद चाहिए? 👨‍🌾",
                f"नमस्ते! शुभ {time_of_day}! मैं आपका AI साथी हूं जो खेती के बारे में सब कुछ जानता है। क्या आज कोई अच्छी बात करते हैं? 🌱"
            ]
        else:
            greetings = [
                f"Hello! Good {time_of_day}! I'm Krishimitra, your AI agricultural advisor. I can help with farming, weather, market prices, or answer any questions you have. How are you today? 🌾",
                f"Hi there! Wonderful {time_of_day}! I'm here to assist with all your agricultural needs - from crop advice to market insights. What brings you here today? 👨‍🌾",
                f"Hey! Great {time_of_day}! I'm your AI farming companion, ready to help with any agricultural queries or general questions. What would you like to know? 🌱"
            ]
        
        return random.choice(greetings)
    
    def _handle_agricultural_query(self, query: str, language: str) -> str:
        """Handle agricultural queries"""
        if language in ['hi', 'hinglish']:
            responses = [
                "अच्छा सवाल! मैं आपकी कृषि संबंधी मदद करूंगा। आपकी जरूरत के अनुसार मैं विस्तृत जानकारी दे सकता हूं।",
                "बहुत बढ़िया! कृषि मेरा विशेष क्षेत्र है। बताइए आपको क्या जानना है - फसल, मिट्टी, या कोई और बात?",
                "मैं यहां हूं आपकी मदद के लिए! कृषि के हर पहलू पर मैं आपको सलाह दे सकता हूं।"
            ]
        else:
            responses = [
                "Excellent question! I'm here to help with all your agricultural needs. I can provide detailed information based on your requirements.",
                "Great! Agriculture is my specialty. Tell me what you'd like to know - crops, soil, weather, or anything else?",
                "I'm here to help! I can assist with every aspect of farming and agriculture."
            ]
        
        return random.choice(responses)
    
    def _handle_weather_query(self, query: str, language: str) -> str:
        """Handle weather queries"""
        if language in ['hi', 'hinglish']:
            return "मौसम की जानकारी कृषि के लिए बहुत जरूरी है! आपका स्थान बताइए तो मैं आपको सटीक मौसम की जानकारी दे सकूं।"
        else:
            return "Weather information is crucial for farming! Please share your location so I can provide accurate weather data for your area."
    
    def _handle_market_query(self, query: str, language: str) -> str:
        """Handle market queries"""
        if language in ['hi', 'hinglish']:
            return "बाजार भाव किसानों के लिए बहुत महत्वपूर्ण हैं! आपका स्थान बताइए तो मैं ताजा बाजार दरें ला सकूं।"
        else:
            return "Market prices are very important for farmers! Share your location and I can fetch the latest market rates for you."
    
    def _handle_general_question(self, query: str, language: str) -> str:
        """Handle general questions"""
        if language in ['hi', 'hinglish']:
            responses = [
                "यह एक बहुत अच्छा सवाल है! मैं आपकी मदद करने की कोशिश करूंगा। मैं कृषि के बारे में विस्तृत जानकारी दे सकता हूं, और सामान्य ज्ञान के सवालों के लिए भी मैं यहां हूं।",
                "मजेदार सवाल! मैं कृषि विशेषज्ञ हूं लेकिन सामान्य ज्ञान के बारे में भी बात कर सकता हूं। आपका सवाल किस विषय से संबंधित है?",
                "अच्छी बात! मैं आपके सवाल का जवाब देने की कोशिश करूंगा। कृषि के अलावा भी मैं कई विषयों पर मदद कर सकता हूं।"
            ]
        else:
            responses = [
                "That's a great question! I'd be happy to help you with that. While I specialize in agriculture, I can also assist with general knowledge questions.",
                "Interesting question! I'm primarily an agricultural expert, but I can discuss various topics. What specific area would you like to know about?",
                "Good question! I'll do my best to provide you with a helpful answer. I can assist with agricultural topics as well as general knowledge."
            ]
        
        return random.choice(responses)
    
    def _handle_conversational(self, query: str, language: str) -> str:
        """Handle conversational responses"""
        if language in ['hi', 'hinglish']:
            responses = [
                "आपसे बात करके बहुत अच्छा लगा! कृषि या कोई और विषय पर बात करना चाहते हैं तो मैं यहां हूं।",
                "धन्यवाद! मैं हमेशा आपकी मदद के लिए तैयार हूं। कृषि संबंधी कोई सवाल हो तो बताइए।",
                "आपका दिन शुभ रहे! कृषि के बारे में कोई जानकारी चाहिए तो मैं यहां हूं।"
            ]
        else:
            responses = [
                "It was great talking with you! Feel free to ask me anything about agriculture or any other topic.",
                "Thank you! I'm always here to help. If you have any agricultural questions, just ask!",
                "Have a wonderful day! I'm here whenever you need agricultural advice or information."
            ]
        
        return random.choice(responses)
    
    def _handle_general(self, query: str, language: str) -> str:
        """Handle general queries"""
        if language in ['hi', 'hinglish']:
            responses = [
                "मैं कृषिमित्र हूं, आपका AI साथी। मैं कृषि, मौसम, बाजार भाव और सामान्य ज्ञान के बारे में बात कर सकता हूं। क्या जानना चाहते हैं?",
                "हैलो! मैं यहां हूं आपकी मदद के लिए। कृषि विशेषज्ञ होने के साथ-साथ मैं आम सवालों के जवाब भी दे सकता हूं।",
                "नमस्ते! मैं एक उन्नत AI हूं जो कृषि और सामान्य विषयों पर मदद कर सकता है। क्या आपको कोई सवाल है?"
            ]
        else:
            responses = [
                "I'm Krishimitra, your AI companion. I can discuss agriculture, weather, market prices, and general knowledge. What would you like to know?",
                "Hello! I'm here to help. As an agricultural expert, I can also answer general questions and have conversations on various topics.",
                "Hi there! I'm an advanced AI that can assist with agricultural topics and general questions. Is there anything you'd like to ask?"
            ]
        
        return random.choice(responses)
    
    def _handle_error_response(self, language: str) -> str:
        """Handle error responses"""
        if language in ['hi', 'hinglish']:
            return "मुझे समझने में कुछ समस्या हुई। कृपया अपना सवाल फिर से पूछिए या अलग तरीके से पूछिए।"
        else:
            return "I had trouble understanding that. Please try rephrasing your question or ask in a different way."
    
    def _fallback_response(self, language: str) -> str:
        if language == 'hi':
            return "मुझे इसकी विशेष जानकारी नहीं है। क्या आप अपने प्रश्न को फिर से दोहरा सकते हैं या मौसम, मिट्टी, बाजार की कीमतों या फसल की सिफारिशों के बारे में पूछ सकते हैं?"
        return "I'm sorry, I don't have specific information on that. Could you please rephrase your question or ask about weather, soil, market prices, or crop recommendations?"
