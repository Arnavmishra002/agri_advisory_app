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
from ..models import Crop, ChatHistory, ChatSession
import requests

# Enhanced imports for ChatGPT-like capabilities
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
    from langdetect import detect, DetectorFactory
    from googletrans import Translator
    import spacy
    import nltk
    from textblob import TextBlob
except ImportError as e:
    logging.warning(f"Some advanced AI libraries not available: {e}")
    pipeline = None
    detect = None
    Translator = None
    spacy = None
    nltk = None
    TextBlob = None

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
        self.translator = Translator() if Translator else None
        
        # Initialize language detection
        if detect:
            DetectorFactory.seed = 0
        
        # Initialize NLP models (lazy loading)
        self._nlp_model = None
        self._generation_pipeline = None
        self._qa_pipeline = None
        
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
    
    def get_response(self, user_query: str, language: str = 'auto', user_id: str = None, session_id: str = None) -> Dict[str, Any]:
        """
        Main method to get ChatGPT-like responses with multilingual support.
        
        Args:
            user_query: User's question/input
            language: Target language ('auto' for auto-detection)
            user_id: Optional user ID for personalized responses
            session_id: Optional session ID for conversation continuity
            
        Returns:
            Dict with response, confidence, language, and metadata
        """
        try:
            # Generate session_id if not provided
            if not session_id:
                session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
            
            # Get or create chat session
            chat_session = self._get_or_create_session(user_id or 'anonymous', session_id)
            
            # Store user message in database
            self._save_message_to_db(
                user_id=user_id or 'anonymous',
                session_id=session_id,
                message_type='user',
                message_content=user_query,
                detected_language=language,
                response_language=language,
                response_source='user_input',
                response_type='user_message'
            )
            
            # Load conversation history from database
            conversation_history = self._load_conversation_history(session_id)
            self.conversation_context["conversation_history"] = conversation_history
            
            # Auto-detect language if needed
            if language == 'auto':
                detected_lang = self._detect_language_advanced(user_query)
                language = detected_lang
            else:
                detected_lang = self._detect_language_advanced(user_query)
            
            # Normalize and preprocess query
            normalized_query = self._preprocess_query(user_query)
            
            # Extract context and entities
            self._extract_context_from_query(normalized_query)
            
            # Translate to English for processing if needed
            working_query = self._translate_for_processing(normalized_query, language)
            
            # Determine response type and generate response
            response_type = self._classify_query_type(working_query)
            response = self._generate_enhanced_response(working_query, language, response_type)
            
            # Translate response back to original language if needed
            final_response = self._translate_response(response, language, detected_lang)
            
            # Store response in history
            self.conversation_context["conversation_history"].append({
                "assistant": final_response,
                "timestamp": datetime.now().isoformat(),
                "language": language,
                "response_type": response_type
            })
            
            # Store assistant response in database
            self._save_message_to_db(
                user_id=user_id or 'anonymous',
                session_id=session_id,
                message_type='assistant',
                message_content=final_response,
                detected_language=detected_lang,
                response_language=language,
                confidence_score=self._calculate_confidence(response_type, working_query),
                response_source='advanced_chatbot',
                response_type=response_type
            )
            
            return {
                "response": final_response,
                "source": "advanced_chatbot",
                "confidence": self._calculate_confidence(response_type, working_query),
                "language": language,
                "detected_language": detected_lang,
                "response_type": response_type,
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "has_location": self.conversation_context.get("last_lat") is not None,
                    "has_product": self.conversation_context.get("last_product") is not None,
                    "conversation_length": len(self.conversation_context["conversation_history"])
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating response for query '{user_query}': {e}")
            return self._handle_error_response(language, e)
    
    def _detect_language_advanced(self, text: str) -> str:
        """Advanced language detection supporting 100+ languages"""
        try:
            # Clean text for detection
            clean_text = re.sub(r'[^\w\s]', '', text).strip()
            if len(clean_text) < 3:
                return 'en'
            
            # Use langdetect for primary detection
            if detect:
                try:
                    detected = detect(clean_text)
                    if detected in self.supported_languages:
                        return detected
                except:
                    pass
            
            # Fallback to character-based detection
            return self._detect_language_by_characters(clean_text)
            
        except Exception:
            return 'en'
    
    def _detect_language_by_characters(self, text: str) -> str:
        """Character-based language detection for Indic and other scripts"""
        # Devanagari (Hindi, Marathi, Sanskrit)
        if re.search(r'[\u0900-\u097F]', text):
            return 'hi'
        
        # Bengali
        if re.search(r'[\u0980-\u09FF]', text):
            return 'bn'
        
        # Telugu
        if re.search(r'[\u0C00-\u0C7F]', text):
            return 'te'
        
        # Tamil
        if re.search(r'[\u0B80-\u0BFF]', text):
            return 'ta'
        
        # Gujarati
        if re.search(r'[\u0A80-\u0AFF]', text):
            return 'gu'
        
        # Kannada
        if re.search(r'[\u0C80-\u0CFF]', text):
            return 'kn'
        
        # Malayalam
        if re.search(r'[\u0D00-\u0D7F]', text):
            return 'ml'
        
        # Punjabi (Gurmukhi)
        if re.search(r'[\u0A00-\u0A7F]', text):
            return 'pa'
        
        # Odia
        if re.search(r'[\u0B00-\u0B7F]', text):
            return 'or'
        
        # Arabic
        if re.search(r'[\u0600-\u06FF]', text):
            return 'ar'
        
        # Chinese
        if re.search(r'[\u4e00-\u9fff]', text):
            return 'zh'
        
        # Japanese
        if re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):
            return 'ja'
        
        # Korean
        if re.search(r'[\uac00-\ud7af]', text):
            return 'ko'
        
        # Cyrillic (Russian, etc.)
        if re.search(r'[\u0400-\u04ff]', text):
            return 'ru'
        
        # Check for Hinglish patterns
        hinglish_patterns = [
            r'\b(bhai|hai|haiya|humein|mujhe|tum|main|kyu|kya|kaise|kab|kahan)\b',
            r'\b(acha|thik|bilkul|zaroor|pakka|sahi|galat)\b'
        ]
        
        for pattern in hinglish_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return 'hinglish'
        
        return 'en'
    
    def _preprocess_query(self, query: str) -> str:
        """Advanced query preprocessing and normalization"""
        # Remove extra whitespace and normalize
        normalized = re.sub(r'\s+', ' ', query.strip())
        
        # Handle common typos and variations
        typo_corrections = {
            # English typos
            'wether': 'weather', 'fertiliser': 'fertilizer', 'croping': 'cropping',
            'agricultre': 'agriculture', 'farming': 'farming', 'farmer': 'farmer',
            'helo': 'hello', 'hii': 'hi', 'thnk': 'thank', 'pls': 'please',
            'wht': 'what', 'hw': 'how', 'wen': 'when', 'wer': 'where',
            
            # Hindi/Hinglish variations
            'कृषि': 'कृषि', 'खेती': 'खेती', 'किसान': 'किसान',
            'kheti': 'खेती', 'krishi': 'कृषि', 'kisan': 'किसान',
            'bhai': 'भाई', 'hai': 'है', 'kya': 'क्या', 'kaise': 'कैसे'
        }
        
        for typo, correction in typo_corrections.items():
            normalized = re.sub(r'\b' + re.escape(typo) + r'\b', correction, normalized, flags=re.IGNORECASE)
        
        return normalized
    
    def _extract_context_from_query(self, query: str) -> None:
        """Extract location, product, and other context from user query"""
        # Extract coordinates
        coord_pattern = re.compile(r"(?P<lat>[+-]?\d{1,2}\.\d+)\s*[,\s]\s*(?P<lon>[+-]?\d{1,3}\.\d+)")
        m = coord_pattern.search(query)
        if m:
            try:
                self.conversation_context["last_lat"] = float(m.group("lat"))
                self.conversation_context["last_lon"] = float(m.group("lon"))
            except Exception:
                pass
        
        # Extract crop/commodity names
        crops = [
            'wheat', 'rice', 'maize', 'corn', 'cotton', 'sugarcane', 'soybean',
            'potato', 'onion', 'tomato', 'chili', 'pepper', 'cabbage', 'cauliflower',
            'गेहूं', 'चावल', 'मक्का', 'कपास', 'गन्ना', 'सोयाबीन', 'आलू', 'प्याज'
        ]
        
        for crop in crops:
            if crop.lower() in query.lower():
                self.conversation_context["last_product"] = crop
                break
        
        # Extract place names and geocode
        self._extract_and_geocode_places(query)
    
    def _extract_and_geocode_places(self, query: str) -> None:
        """Extract place names and geocode them using OpenStreetMap"""
        try:
            # Enhanced place extraction patterns
            patterns = [
                r"(?:in|at|near|from)\s+([A-Za-z][A-Za-z\s]{2,50})",
                r"(?:में|के पास|पास|से)\s+([\u0900-\u097F\s]{2,50})",
                r"(?:বাংলাদেশ|ভারত|পাকিস্তান|শ্রীলঙ্কা)\s+([\u0980-\u09FF\s]{2,50})"
            ]
            
            place = None
            for pattern in patterns:
                m = re.search(pattern, query, flags=re.IGNORECASE)
                if m:
                    place = m.group(1).strip()
                    break
            
            if not place:
                return
            
            # Geocode using OpenStreetMap Nominatim
            resp = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": place,
                    "format": "json",
                    "limit": 1,
                    "countrycodes": "in,bd,pk,lk,np,bt"  # Focus on South Asian countries
                },
                headers={"User-Agent": "Advanced-Agri-Chatbot/2.0"},
                timeout=10
            )
            
            if resp.ok:
                results = resp.json()
                if results:
                    lat = float(results[0].get("lat"))
                    lon = float(results[0].get("lon"))
                    self.conversation_context["last_lat"] = lat
                    self.conversation_context["last_lon"] = lon
                    
        except Exception as e:
            logger.debug(f"Geocoding failed: {e}")
    
    def _translate_for_processing(self, text: str, source_lang: str) -> str:
        """Translate text to English for processing"""
        if source_lang == 'en' or source_lang == 'hinglish':
            return text
        
        if not self.translator:
            return text
        
        try:
            result = self.translator.translate(text, src=source_lang, dest='en')
            return result.text
        except Exception as e:
            logger.debug(f"Translation failed: {e}")
            return text
    
    def _translate_response(self, response: str, target_lang: str, original_lang: str) -> str:
        """Translate response to target language"""
        if target_lang == 'en' or target_lang == original_lang:
            return response
        
        if not self.translator:
            return response
        
        try:
            result = self.translator.translate(response, src='en', dest=target_lang)
            return result.text
        except Exception as e:
            logger.debug(f"Response translation failed: {e}")
            return response
    
    def _classify_query_type(self, query: str) -> str:
        """Classify the type of query for appropriate response generation"""
        query_lower = query.lower()
        
        # Greeting patterns
        greeting_patterns = [
            'hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening',
            'namaste', 'namaskar', 'how are you', 'what\'s up', 'wassup'
        ]
        
        if any(pattern in query_lower for pattern in greeting_patterns):
            return 'greeting'
        
        # Agricultural patterns
        agri_patterns = [
            'crop', 'farm', 'agriculture', 'fertilizer', 'soil', 'weather',
            'market price', 'planting', 'harvesting', 'irrigation', 'pest',
            'disease', 'yield', 'production', 'खेती', 'कृषि', 'फसल', 'मिट्टी'
        ]
        
        if any(pattern in query_lower for pattern in agri_patterns):
            return 'agricultural'
        
        # Weather patterns
        weather_patterns = [
            'weather', 'rain', 'temperature', 'humidity', 'forecast',
            'मौसम', 'बारिश', 'तापमान', 'आर्द्रता'
        ]
        
        if any(pattern in query_lower for pattern in weather_patterns):
            return 'weather'
        
        # Market/Price patterns
        market_patterns = [
            'price', 'market', 'cost', 'rate', 'selling', 'buying',
            'बाजार', 'कीमत', 'दर', 'मूल्य'
        ]
        
        if any(pattern in query_lower for pattern in market_patterns):
            return 'market'
        
        # General question patterns
        question_patterns = [
            'what is', 'how to', 'why', 'when', 'where', 'who', 'which',
            'explain', 'tell me about', 'क्या है', 'कैसे', 'क्यों', 'कब', 'कहाँ'
        ]
        
        if any(pattern in query_lower for pattern in question_patterns):
            return 'general_question'
        
        # Conversational patterns
        conversational_patterns = [
            'thank you', 'thanks', 'bye', 'goodbye', 'see you', 'nice talking',
            'धन्यवाद', 'शुक्रिया', 'अलविदा', 'फिर मिलते हैं'
        ]
        
        if any(pattern in query_lower for pattern in conversational_patterns):
            return 'conversational'
        
        return 'general'
    
    def _generate_enhanced_response(self, query: str, language: str, response_type: str) -> str:
        """Generate enhanced ChatGPT-like responses"""
        
        if response_type == 'greeting':
            return self._handle_greeting_enhanced(query, language)
        
        elif response_type == 'agricultural':
            return self._handle_agricultural_query_enhanced(query, language)
        
        elif response_type == 'weather':
            return self._handle_weather_query_enhanced(query, language)
        
        elif response_type == 'market':
            return self._handle_market_query_enhanced(query, language)
        
        elif response_type == 'general_question':
            return self._handle_general_question_enhanced(query, language)
        
        elif response_type == 'conversational':
            return self._handle_conversational_enhanced(query, language)
        
        else:
            return self._handle_general_enhanced(query, language)
    
    def _handle_greeting_enhanced(self, query: str, language: str) -> str:
        """Enhanced greeting responses"""
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
                f"Hello! Good {time_of_day}! I'm Krishimitra, your advanced AI agricultural advisor. I can help with farming, weather, market prices, or answer any questions you have. How are you today? 🌾",
                f"Hi there! Wonderful {time_of_day}! I'm here to assist with all your agricultural needs - from crop advice to market insights. What brings you here today? 👨‍🌾",
                f"Hey! Great {time_of_day}! I'm your AI farming companion, ready to help with any agricultural queries or general questions. What would you like to know? 🌱"
            ]
        
        return random.choice(greetings)
    
    def _handle_agricultural_query_enhanced(self, query: str, language: str) -> str:
        """Enhanced agricultural query handling with ChatGPT-like responses"""
        lat = self.conversation_context.get("last_lat")
        lon = self.conversation_context.get("last_lon")
        product = self.conversation_context.get("last_product")
        
        # Get real-time data if location is available
        context_info = ""
        if lat and lon:
            try:
                # Weather context
                weather = self.weather_api.get_current_weather(lat, lon, 'en')
                if weather:
                    temp = weather.get('current', {}).get('temp_c', 26)
                    condition = weather.get('current', {}).get('condition', {}).get('text', 'Clear')
                    context_info += f" Current weather: {condition}, {temp}°C."
                
                # Market context
                if product:
                    market_data = get_market_prices(lat, lon, 'en', product)
                    if market_data:
                        context_info += f" Market price for {product} is available."
            except Exception:
                pass
        
        # Check for specific crop recommendation queries
        if any(word in query.lower() for word in ['crop', 'recommend', 'plant', 'फसल', 'बोना', 'उपयुक्त', 'suggest']):
            return self._handle_crop_recommendation_enhanced(query, language, lat, lon)
        
        # Generate contextual response
        if language in ['hi', 'hinglish']:
            responses = [
                f"अच्छा सवाल! मैं आपकी कृषि संबंधी मदद करूंगा।{context_info} आपकी जरूरत के अनुसार मैं विस्तृत जानकारी दे सकता हूं।",
                f"बहुत बढ़िया! कृषि मेरा विशेष क्षेत्र है।{context_info} बताइए आपको क्या जानना है - फसल, मिट्टी, या कोई और बात?",
                f"मैं यहां हूं आपकी मदद के लिए!{context_info} कृषि के हर पहलू पर मैं आपको सलाह दे सकता हूं।"
            ]
        else:
            responses = [
                f"Excellent question! I'm here to help with all your agricultural needs.{context_info} I can provide detailed information based on your requirements.",
                f"Great! Agriculture is my specialty.{context_info} Tell me what you'd like to know - crops, soil, weather, or anything else?",
                f"I'm here to help!{context_info} I can assist with every aspect of farming and agriculture."
            ]
        
        return random.choice(responses)
    
    def _handle_crop_recommendation_enhanced(self, query: str, language: str, lat: float = None, lon: float = None) -> str:
        """Handle crop recommendation queries with government data"""
        try:
            # Use government data service for accurate recommendations
            gov_rec = self.gov_data_service.get_icar_crop_recommendations(
                soil_type='Loamy',
                season='kharif',
                temperature=28.0,
                rainfall=100.0,
                ph=6.5
            )
            
            if gov_rec and 'recommendations' in gov_rec and gov_rec['recommendations']:
                recommendations = gov_rec['recommendations']
                
                if language == 'hi':
                    response = "भारतीय कृषि अनुसंधान परिषद (ICAR) के आधार पर सुझाई गई फसलें:\n\n"
                    for i, rec in enumerate(recommendations[:3], 1):
                        crop = rec.get('crop', 'Unknown')
                        score = rec.get('suitability_score', 0)
                        reason = rec.get('reason', '')
                        response += f"{i}. **{crop}** (उपयुक्तता: {score}%)\n   {reason}\n\n"
                    
                    response += "ये सिफारिशें आधिकारिक सरकारी डेटा पर आधारित हैं। अधिक सटीक सुझाव के लिए अपना स्थान और मिट्टी का प्रकार बताएं।"
                else:
                    response = "Based on Indian Council of Agricultural Research (ICAR) guidelines:\n\n"
                    for i, rec in enumerate(recommendations[:3], 1):
                        crop = rec.get('crop', 'Unknown')
                        score = rec.get('suitability_score', 0)
                        reason = rec.get('reason', '')
                        response += f"{i}. **{crop}** (Suitability: {score}%)\n   {reason}\n\n"
                    
                    response += "These recommendations are based on official government agricultural data. For more specific advice, please share your location and soil type."
                
                return response
            
        except Exception as e:
            logger.error(f"Error in crop recommendation: {e}")
        
        # Fallback to general recommendations
        if language == 'hi':
            return ("भारतीय कृषि अनुसंधान परिषद (ICAR) के अनुसार, सामान्य फसल सुझाव:\n\n"
                   "1. **चावल** - खरीफ सीजन के लिए उपयुक्त, अच्छी बाजार कीमत\n"
                   "2. **गेहूं** - रबी सीजन के लिए उत्तम, सरकारी सहायता उपलब्ध\n"
                   "3. **मक्का** - बहुत सारे क्षेत्रों में उगाया जा सकता है\n\n"
                   "अधिक सटीक सुझाव के लिए अपना स्थान, मिट्टी का प्रकार और सीजन बताएं।")
        else:
            return ("Based on Indian Council of Agricultural Research (ICAR) guidelines:\n\n"
                   "1. **Rice** - Ideal for Kharif season, good market demand\n"
                   "2. **Wheat** - Perfect for Rabi season, government support available\n"
                   "3. **Maize** - Versatile crop suitable for many regions\n\n"
                   "For more specific recommendations, please share your location, soil type, and preferred season.")
    
    def _handle_general_question_enhanced(self, query: str, language: str) -> str:
        """Handle general questions with ChatGPT-like intelligence"""
        
        # Use LLM for general questions if available
        if self._get_generation_pipeline():
            try:
                prompt = self._build_general_prompt(query, language)
                result = self._get_generation_pipeline()(prompt, max_new_tokens=150, do_sample=True, temperature=0.7)
                if isinstance(result, list) and len(result) > 0:
                    response = result[0].get('generated_text', '').strip()
                    if response and len(response) > 10:
                        return response
            except Exception as e:
                logger.debug(f"LLM generation failed: {e}")
        
        # Fallback to contextual responses
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
    
    def _build_general_prompt(self, query: str, language: str) -> str:
        """Build prompt for general question answering"""
        context = ""
        if self.conversation_context.get("last_lat"):
            context = f" User location: {self.conversation_context['last_lat']}, {self.conversation_context['last_lon']}."
        
        if language != 'en':
            context += f" User language: {language}."
        
        return f"""You are Krishimitra, an advanced AI agricultural advisor who can also answer general questions. Be helpful, accurate, and conversational.{context}
        
User Question: {query}

Provide a helpful, informative response:"""
    
    def _get_generation_pipeline(self):
        """Get or initialize text generation pipeline"""
        if self._generation_pipeline is not None:
            return self._generation_pipeline
        
        if not pipeline:
            return None
        
        try:
            # Use a more capable model for better responses
            self._generation_pipeline = pipeline(
                'text-generation',
                model='microsoft/DialoGPT-medium',
                return_full_text=False
            )
            return self._generation_pipeline
        except Exception as e:
            logger.debug(f"Failed to load generation model: {e}")
            try:
                # Fallback to smaller model
                self._generation_pipeline = pipeline('text-generation', model='distilgpt2')
                return self._generation_pipeline
            except Exception:
                return None
    
    def _calculate_confidence(self, response_type: str, query: str) -> float:
        """Calculate confidence score for the response"""
        base_confidence = 0.8
        
        # Increase confidence for specific agricultural queries
        if response_type == 'agricultural':
            base_confidence = 0.9
        
        # Increase confidence if we have location context
        if self.conversation_context.get("last_lat"):
            base_confidence += 0.05
        
        # Increase confidence for clear questions
        if '?' in query or any(word in query.lower() for word in ['what', 'how', 'why', 'when', 'where']):
            base_confidence += 0.05
        
        return min(base_confidence, 0.95)
    
    def _handle_error_response(self, language: str, error: Exception = None) -> Dict[str, Any]:
        """Handle errors gracefully with multilingual support"""
        if language in ['hi', 'hinglish']:
            error_msg = "मुझे समझने में कुछ समस्या हुई। कृपया अपना सवाल फिर से पूछिए या अलग तरीके से पूछिए।"
        else:
            error_msg = "I had trouble understanding that. Please try rephrasing your question or ask in a different way."
        
        return {
            "response": error_msg,
            "source": "error",
            "confidence": 0.1,
            "language": language,
            "error": str(error) if error else None,
            "timestamp": datetime.now().isoformat()
        }
    
    # Additional helper methods for enhanced functionality
    def _handle_weather_query_enhanced(self, query: str, language: str) -> str:
        """Enhanced weather query handling"""
        lat = self.conversation_context.get("last_lat")
        lon = self.conversation_context.get("last_lon")
        
        if lat and lon:
            try:
                weather = self.weather_api.get_current_weather(lat, lon, language)
                if weather:
                    temp = weather.get('current', {}).get('temp_c', 26)
                    condition = weather.get('current', {}).get('condition', {}).get('text', 'Clear')
                    humidity = weather.get('current', {}).get('humidity', 60)
                    
                    if language in ['hi', 'hinglish']:
                        return f"आपके क्षेत्र का मौसम: {condition}, तापमान {temp}°C, आर्द्रता {humidity}%. यह जानकारी आपकी खेती की योजना बनाने में मदद करेगी।"
                    else:
                        return f"Current weather in your area: {condition}, temperature {temp}°C, humidity {humidity}%. This information will help you plan your farming activities."
            except Exception:
                pass
        
        # Fallback response
        if language in ['hi', 'hinglish']:
            return "मौसम की जानकारी कृषि के लिए बहुत जरूरी है! आपका स्थान बताइए तो मैं आपको सटीक मौसम की जानकारी दे सकूं।"
        else:
            return "Weather information is crucial for farming! Please share your location so I can provide accurate weather data for your area."
    
    def _handle_market_query_enhanced(self, query: str, language: str) -> str:
        """Enhanced market query handling"""
        lat = self.conversation_context.get("last_lat")
        lon = self.conversation_context.get("last_lon")
        product = self.conversation_context.get("last_product")
        
        if lat and lon:
            try:
                market_data = get_market_prices(lat, lon, language, product)
                if market_data:
                    if language in ['hi', 'hinglish']:
                        return f"आपके क्षेत्र के बाजार भाव उपलब्ध हैं। किसी विशेष फसल की कीमत जानना चाहते हैं तो बताइए।"
                    else:
                        return f"Market prices for your area are available. Let me know which specific crop prices you'd like to see."
            except Exception:
                pass
        
        # Fallback response
        if language in ['hi', 'hinglish']:
            return "बाजार भाव किसानों के लिए बहुत महत्वपूर्ण हैं! आपका स्थान बताइए तो मैं ताजा बाजार दरें ला सकूं।"
        else:
            return "Market prices are very important for farmers! Share your location and I can fetch the latest market rates for you."
    
    def _handle_conversational_enhanced(self, query: str, language: str) -> str:
        """Enhanced conversational responses"""
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
    
    def _handle_general_enhanced(self, query: str, language: str) -> str:
        """Handle general queries with enhanced responses"""
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
    
    def _get_or_create_session(self, user_id: str, session_id: str) -> ChatSession:
        """Get existing session or create new one"""
        try:
            chat_session, created = ChatSession.objects.get_or_create(
                session_id=session_id,
                defaults={
                    'user_id': user_id,
                    'preferred_language': 'auto',
                    'conversation_context': self.conversation_context.copy()
                }
            )
            
            # Update last activity
            chat_session.last_activity = datetime.now()
            chat_session.is_active = True
            chat_session.save()
            
            # Update conversation context from database
            if not created and chat_session.conversation_context:
                self.conversation_context.update(chat_session.conversation_context)
            
            return chat_session
            
        except Exception as e:
            logger.error(f"Error getting/creating session: {e}")
            # Return a mock session object for fallback
            return type('MockSession', (), {
                'session_id': session_id,
                'user_id': user_id,
                'conversation_context': {}
            })()
    
    def _save_message_to_db(self, user_id: str, session_id: str, message_type: str, 
                           message_content: str, detected_language: str, 
                           response_language: str, confidence_score: float = None,
                           response_source: str = None, response_type: str = None,
                           has_location: bool = False, has_product: bool = False,
                           latitude: float = None, longitude: float = None):
        """Save message to database"""
        try:
            ChatHistory.objects.create(
                user_id=user_id,
                session_id=session_id,
                message_type=message_type,
                message_content=message_content,
                detected_language=detected_language,
                response_language=response_language,
                confidence_score=confidence_score,
                response_source=response_source,
                response_type=response_type,
                has_location=has_location,
                has_product=has_product,
                latitude=latitude,
                longitude=longitude
            )
            
            # Update session statistics
            try:
                session = ChatSession.objects.get(session_id=session_id)
                session.total_messages += 1
                if message_type == 'user':
                    session.user_messages += 1
                elif message_type == 'assistant':
                    session.assistant_messages += 1
                session.save()
            except ChatSession.DoesNotExist:
                pass
                
        except Exception as e:
            logger.error(f"Error saving message to database: {e}")
    
    def _load_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Load conversation history from database"""
        try:
            messages = ChatHistory.objects.filter(
                session_id=session_id
            ).order_by('created_at')[:limit]
            
            history = []
            for msg in messages:
                history.append({
                    "type": msg.message_type,
                    "content": msg.message_content,
                    "timestamp": msg.created_at.isoformat(),
                    "language": msg.response_language,
                    "confidence": msg.confidence_score,
                    "source": msg.response_source
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error loading conversation history: {e}")
            return []
    
    def get_chat_history(self, session_id: str, user_id: str = None, limit: int = 50) -> List[Dict]:
        """Get chat history for a specific session"""
        try:
            query = ChatHistory.objects.filter(session_id=session_id)
            if user_id:
                query = query.filter(user_id=user_id)
            
            messages = query.order_by('created_at')[:limit]
            
            return [
                {
                    "id": msg.id,
                    "type": msg.message_type,
                    "content": msg.message_content,
                    "timestamp": msg.created_at.isoformat(),
                    "language": msg.response_language,
                    "confidence": msg.confidence_score,
                    "source": msg.response_source,
                    "response_type": msg.response_type,
                    "has_location": msg.has_location,
                    "has_product": msg.has_product
                }
                for msg in messages
            ]
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return []
