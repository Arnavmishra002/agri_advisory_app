import logging
import re
import random
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class ConversationalAgriculturalChatbot:
    def __init__(self):
        # Enhanced conversational chatbot like ChatGPT
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

    def _normalize_query(self, query: str) -> str:
        """Normalize query by handling typos, casing, and punctuation"""
        # Common typos and fixes
        typo_fixes = {
            'hello': ['hi', 'hey', 'hallo', 'helo', 'hii', 'hiiii'],
            'crop': ['crops', 'krop', 'croping'],
            'weather': ['wether', 'weatherr', 'weathering'],
            'fertilizer': ['fertilisers', 'fertilize', 'fertilizing'],
            'soil': ['soils', 'dirt', 'mud'],
            'price': ['prices', 'cost', 'prize']
        }
        
        normalized = query.lower().strip()
        
        # Apply typo fixes
        for correct_word, typos in typo_fixes.items():
            for typo in typos:
                normalized = normalized.replace(typo, correct_word)
        
        # Remove extra spaces and normalize punctuation
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = re.sub(r'[!]+', '!', normalized)
        normalized = re.sub(r'[?]+', '?', normalized)
        
        return normalized

    def _detect_language(self, query: str) -> str:
        """Detect language based on characters and common words"""
        # Check for Hindi/Devanagari characters
        if re.search(r'[\u0900-\u097F]', query):
            return 'hi'
        
        # Check for Hindi Roman English (Hinglish) patterns
        hinglish_patterns = [
            r'\bhai\b', r'\bhaiya\b', r'\bhumein\b', r'\bmujhe\b', r'\btum\b', r'\bmain\b',
            r'\bkyu\b', r'\bkya\b', r'\bkaise\b', r'\bkab\b', r'\bkahan\b', r'\bkya\b',
            r'\bhindi\b', r'\bundniya\b', r'\bhelp\b.*\kbhai\b', r'\bhello\b.*\bbhai\b'
        ]
        
        for pattern in hinglish_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return 'hinglish'
        
        return 'en'

    def _generate_response(self, query: str, language: str) -> str:
        """Generate conversational response based on intent"""
        
        # Greetings and casual conversation
        if self._is_greeting(query):
            return self._handle_greeting(query, language)
        
        # Agricultural queries
        elif self._is_agricultural_query(query):
            return self._handle_agricultural_query(query, language)
        
        # General conversation
        else:
            return self._handle_general_conversation(query, language)

    def _is_greeting(self, query: str) -> bool:
        """Check if query is a greeting"""
        greetings = [
            'hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening',
            'namaste', 'namaskar', 'aapka swagat hai', 'kaise ho', 'how are you',
            'what up', 'wassup', 'hiiiii', 'hiiii', 'byee', 'thank you', 'thanks',
            'bye', 'goodbye', 'see you', 'take care'
        ]
        
        query_lower = query.lower()
        return any(greeting in query_lower for greeting in greetings)

    def _is_agricultural_query(self, query: str) -> bool:
        """Check if query is agricultural in nature"""
        agri_keywords = [
            'crop', 'crops', 'farm', 'farming', 'agriculture', 'farmer', 'plant', 'plants',
            'soil', 'weather', 'fertilizer', 'fertilise', 'fertilizer', 'seed', 'seeds',
            'harvest', 'sowing', 'rice', 'wheat', 'maize', 'cotton', 'sugarcane', 'vegetables',
            'disease', 'pest', 'irrigation', 'water', 'market', 'price', 'yield', 'production',
            'खेती', 'कृषि', 'किसान', 'फॉर्म', 'फसल', 'बुवाई', 'फल', 'फूल', 'पेड़','पौधे',
            'मिट्टी', 'पानी', 'खाद', 'बाजार', 'कीमत', 'उत्पादन', 'मुनाफा'
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in agri_keywords)

    def _handle_greeting(self, query: str, language: str) -> str:
        """Handle greeting responses"""
        current_time = datetime.now().hour
        
        if language in ['hi', 'hinglish']:
            if 6 <= current_time < 12:
                return "नमस्ते! सुप्रभात! मैं आपकी कृषि से जुड़ी मदद के लिए यहां हूं। आप कैसे हैं?"
            elif 12 <= current_time < 18:
                return "नमस्ते! शुभ दिन! कृषि सलाहकार के रूप में मैं आपकी सेवा में हूं। कैसी मदद चाहिए?"
            else:
                return "नमस्ते! शुभ संध्या! आपका स्वागत है कृषि सलाहकार में। क्या आज कोई अच्छी बात है?"
        else:
            greetings = [
                "Hello! Good day! I'm Krishimitra, your agricultural advisor. How are you today? 🌱",
                "Hi there! Welcome to your farming companion. What brings you here today? 🌾",
                "Hey! Nice to meet you! I'm here to help with all your agricultural queries. 👨‍🌾",
                "Hello! Hope you're having a great day! Ready to discuss some farming? 🌿"
            ]
            return random.choice(greetings)

    def _handle_agricultural_query(self, query: str, language: str) -> str:
        """Handle agricultural queries with enhanced responses"""
        
        # Crop recommendations
        if any(word in query.lower() for word in ['crop', 'recommend', 'plant', 'फसल', 'बोना', 'उपयुक्त']):
            return self._get_crop_recommendation_response(language)
        
        # Weather queries
        elif any(word in query.lower() for word in ['weather', 'rain', 'temperature', 'मौसम', 'बारिश', 'तापमान']):
            return self._get_weather_response(language)
        
        # Market prices
        elif any(word in query.lower() for word in ['price', 'market', 'cost', 'बाजार', 'कीमत', 'मूल्य']):
            return self._get_market_response(language)
        
        # Soil/Fertilizer
        elif any(word in query.lower() for word in ['soil', 'fertilizer', 'nutrient', 'मिट्टी', 'खाद', 'उर्वरक']):
            return self._get_soil_response(language)
        
        # General agricultural advice
        else:
            return self._get_general_agri_response(language)

    def _get_crop_recommendation_response(self, language: str) -> str:
        if language in ['hi', 'hinglish']:
            responses = [
                "अच्छा सवाल! फसल सिफारिश के लिए मुझे आपके क्षेत्र की मिट्टी और मौसम की जानकारी चाहिए। क्या आप अपना स्थान बता सकते हैं?",
                "बेहतरीन सवाल! फसल चुनने के लिए कई कारकों को समझना जरूरी है। कौन सा मौसम है और आपके क्षेत्र की मिट्टी कैसी है?",
                "फसल सिफारिश के लिए मैं आपकी मदद करूंगा! बताइए कि आप कहां से हैं और आपको कैसी फसल पसंद है?"
            ]
        else:
            responses = [
                "Great question! For crop recommendations, I need to know about your soil type and weather conditions. Could you tell me your location? 🌾",
                "Excellent! To suggest the best crops, I need to understand your local conditions - soil type, season, and water availability. Where are you farming? 🌱",
                "I'd love to help with crop recommendations! Tell me about your region and what kind of crops you're interested in! 👨‍🍑"
            ]
        return random.choice(responses)

    def _get_weather_response(self, language: str) -> str:
        if language in ['hi', 'hinglish']:
            responses = [
                "मौसम की जानकारी बहुत जरूरी है कृषि के लिए! मैं आपको बता सकता हूं मौसम का हाल। आपका क्षेत्र कौन सा है?",
                "अच्छी बात! मौसम किसानों के लिए बहुत महत्वपूर्ण है। बताइए आप कहां से हैं, मैं आपको मौसम का पूरा ब्योरा दूंगा।",
                "मौसम की चर्चा करते हैं! आपके क्षेत्र में कैसा मौसम है और क्या आपकी फसलों को कुछ जरूरत है?"
            ]
        else:
            responses = [
                "Weather is crucial for farming! I can help you with current conditions and forecasts. What's your location? 🌤️",
                "Great query! Weather plays a vital role in agricultural decisions. Let me know your area for accurate weather information! ⛅",
                "Let's talk weather! Current conditions and forecasts are essential for farming. Where are you located? 🌦️"
            ]
        return random.choice(responses)

    def _get_market_response(self, language: str) -> str:
        if language in ['hi', 'hinglish']:
            responses = [
                "बाजार की कीमतें जानना बहुत जरूरी है! मैं आपके लिए ताजा बाजार दरें ला सकता हूं। कौन सी फसल के बारे में जानना चाहते हैं?",
                "अच्छी बात! बाजार के भाव समझना किसानों के लिए बहुत महत्वपूर्ण है। कहिए तो मैं आपको नवीनतम दरें दिखाऊं।",
                "बाजार की जानकारी हमारी ताकत है! आपको किस फसल की कीमत चाहिए? मैं तुरंत ताजा दरें ला सकता हूं।"
            ]
        else:
            responses = [
                "Market prices are so important! I can get you the latest rates for your crops. Which commodity are you interested in? 📈",
                "Excellent query! Understanding market trends is key for farmers. Let me fetch current prices for you! 💰",
                "Market insights help optimize your profits! What crop prices would you like to know? I can get real-time data! 📊"
            ]
        return random.choice(responses)

    def _get_soil_response(self, language: str) -> str:
        if language in ['hi', 'hinglish']:
            responses = [
                "मिट्टी और खर्प हमारी खेती की जड़ हैं! मैं आपकी मिट्टी का विश्लेषण करने में मदद करूंगा। कैसी मिट्टी है आपके पास?",
                "बहुत अच्छी बात! मिट्टी की स्वास्थ्य से ही अच्छी फसल मिलती है। बताइए आपकी मिट्टी कैसी है और क्या समस्या है?",
                "खर्प और मिट्टी के बारे में जानकारी जरूरी है! मैं आपको सही सुझाव दूंगा। आपके मौसम और मिट्टी का प्रकार क्या है?"
            ]
        else:
            responses = [
                "Soil and fertilizer are the foundation of good farming! Let me help analyze your soil conditions. What type of soil do you have? 🌱",
                "Great question! Soil health determines crop success. Tell me about your soil type and any issues you're facing! 🌾",
                "Fertilizer and soil management is crucial! I can provide tailored advice. What's your soil type and growing conditions? 🌿"
            ]
        return random.choice(responses)

    def _get_general_agri_response(self, language: str) -> str:
        if language in ['hi', 'hinglish']:
            responses = [
                "कृषि के बारे में कोई भी सवाल पूछ सकते हैं! मैं आपकी मदद करने के लिए यहां हूं। विशेष जरूरत क्या है?",
                "मजेदार सवाल! किसान भाइयों की मदद करना मेरा धर्म रहाता है। और बताइए क्या जानना चाहते हैं?",
                "कृषि मुझे बहुत भाती है! आपके कौन से कृषि संबंधी सवाल का जवाब चाहिए?"
            ]
        else:
            responses = [
                "I'm passionate about agriculture! Feel free to ask me anything about farming, crops, or rural life. What would you like to know? 🌾",
                "Great to chat about agriculture! I'm here to help with all farming queries. What's on your mind? 👨‍🌾",
                "Love discussing farming topics! I can help with crop advice, soil health, weather, market trends - anything agricultural! 🌱"
            ]
        return random.choice(responses)

    def _handle_general_conversation(self, query: str, language: str) -> str:
        """Handle general non-agricultural conversations"""
        if language in ['hi', 'hinglish']:
            responses = [
                "मैं कृषि सलाहकार हूं, लेकिन मैं आपसे बात करने में खुश हूं! क्या आप कुछ खेती के बारे में जानना चाहते हैं?",
                "हैलो! मैं मुख्य रूप से कृषि में मदद करता हूं। क्या आपको कोई कृषि संबंधी सवाल है?",
                "नमस्ते! मैं कृषि विशेषज्ञ हूं लेकिन सामान्य बातचीत भी कर सकता हूं। क्या आप खेतिहर जीवन के बारे में जानना चाहते हैं?"
            ]
        else:
            responses = [
                "Hi there! I'm your agricultural advisor, but I love chatting too! Would you like to talk about farming or agriculture? 🌾",
                "Hello! I specialize in farming advice, but I'm happy to chat about other things too. Any agricultural questions? 👨‍🌾",
                "Hey! I'm mainly here for farming help, but I can chat about rural life and agriculture. What interests you? 🌱"
            ]
        return random.choice(responses)

    def _handle_error_response(self, language: str) -> str:
        """Handle error cases gracefully"""
        if language in ['hi', 'hinglish']:
            return "मुझे समझने में कुछ समस्या हुई। कृपया अपना सवाल फिर से पूछिए या कृषि से जुड़ी कुछ बात पूछिए!"
        return "Sorry, I had trouble understanding that. Please ask again or try asking about farming and agriculture!"
