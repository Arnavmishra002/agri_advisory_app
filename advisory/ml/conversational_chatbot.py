import logging
import re
import random
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from ..services.weather_api import MockWeatherAPI
from ..services.market_api import get_market_prices, get_trending_crops
from ..ml.ml_models import AgriculturalMLSystem
from ..models import Crop
from .advanced_chatbot import AdvancedAgriculturalChatbot
import requests

try:
    from transformers import pipeline
except Exception:
    pipeline = None  # transformers optional at runtime

logger = logging.getLogger(__name__)

class ConversationalAgriculturalChatbot:
    def __init__(self):
        # Enhanced conversational chatbot like ChatGPT
        self.conversation_context: Dict[str, Any] = {
            "last_lat": None,
            "last_lon": None,
            "last_lang": "en",
            "last_product": None,
        }
        self.weather_api = MockWeatherAPI()
        self.ml_system = AgriculturalMLSystem()
        self._gen_pipeline = None  # lazy init
        
        # Initialize advanced chatbot for enhanced capabilities
        try:
            self.advanced_chatbot = AdvancedAgriculturalChatbot()
            self.use_advanced = True
            logger.info("Advanced chatbot initialized successfully")
        except Exception as e:
            self.advanced_chatbot = None
            self.use_advanced = False
            logger.warning(f"Advanced chatbot initialization failed, using fallback: {e}")
        
        logger.info("Enhanced conversational chatbot initialized")
    
    def _format_government_recommendations(self, gov_rec: Dict, language: str) -> str:
        """Format government recommendations for user display"""
        try:
            recommendations = gov_rec.get('recommendations', [])
            if not recommendations:
                return "No specific crop recommendations available from government sources."
            
            if language == 'hi':
                response = "भारतीय कृषि अनुसंधान परिषद (ICAR) के आधार पर सुझाई गई फसलें:\n\n"
                for i, rec in enumerate(recommendations[:3], 1):
                    crop = rec.get('crop', 'Unknown')
                    score = rec.get('suitability_score', 0)
                    reason = rec.get('reason', '')
                    response += f"{i}. {crop} (उपयुक्तता: {score}%)\n   {reason}\n\n"
                
                response += "ये सिफारिशें आधिकारिक सरकारी डेटा पर आधारित हैं।"
            else:
                response = "Based on Indian Council of Agricultural Research (ICAR) guidelines:\n\n"
                for i, rec in enumerate(recommendations[:3], 1):
                    crop = rec.get('crop', 'Unknown')
                    score = rec.get('suitability_score', 0)
                    reason = rec.get('reason', '')
                    response += f"{i}. {crop} (Suitability: {score}%)\n   {reason}\n\n"
                
                response += "These recommendations are based on official government agricultural data."
            
            return response
            
        except Exception as e:
            logger.error(f"Error formatting government recommendations: {e}")
            return "Government crop recommendations are temporarily unavailable. Please try again later."
    
    def _get_crop_recommendation_response(self, language: str) -> str:
        """Get crop recommendation response when location is not available"""
        try:
            # Use government data service for general recommendations
            if hasattr(self, 'advanced_chatbot') and self.advanced_chatbot:
                gov_rec = self.advanced_chatbot.gov_data_service.get_icar_crop_recommendations(
                    soil_type='Loamy',
                    season='kharif',
                    temperature=28.0,
                    rainfall=100.0,
                    ph=6.5
                )
                if gov_rec and 'recommendations' in gov_rec:
                    return self._format_government_recommendations(gov_rec, language)
            
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
                       
        except Exception as e:
            logger.error(f"Error in crop recommendation fallback: {e}")
            if language == 'hi':
                return "फसल सुझाव अस्थायी रूप से उपलब्ध नहीं है। कृपया बाद में पुनः प्रयास करें।"
            else:
                return "Crop recommendations are temporarily unavailable. Please try again later."
    
    def _get_weather_response(self, language: str) -> str:
        """Get weather response when location is not available"""
        if language == 'hi':
            return ("मौसम की जानकारी के लिए कृपया अपना स्थान बताएं (जैसे: दिल्ली, मुंबई, कोलकाता)। "
                   "मैं आपको वर्तमान मौसम और 5-दिन का पूर्वानुमान प्रदान कर सकूंगा।")
        else:
            return ("Please share your location (e.g., Delhi, Mumbai, Kolkata) for weather information. "
                   "I can provide current weather and 5-day forecast for your area.")
    
    def _get_market_price_response(self, language: str) -> str:
        """Get market price response when location is not available"""
        if language == 'hi':
            return ("बाजार की कीमतों के लिए कृपया अपना स्थान या मंडी का नाम बताएं। "
                   "मैं आपको Agmarknet से वास्तविक समय की कीमतें दिखा सकूंगा।")
        else:
            return ("Please share your location or mandi name for market prices. "
                   "I can show you real-time prices from Agmarknet.")
    
    def get_response(self, user_query: str, language: str = 'en') -> Dict[str, Any]:
        """
        Generates a conversational response like ChatGPT.
        Supports multiple languages, grammatic errors, and casual conversations.
        """
        try:
            # Use advanced chatbot if available for better ChatGPT-like responses
            if self.use_advanced and self.advanced_chatbot:
                return self.advanced_chatbot.get_response(user_query, language)
            
            # Fallback to original implementation
            # Normalize input and try to learn context (location/product)
            normalized_query = self._normalize_query(user_query)
            self._maybe_update_context_from_query(normalized_query)
            
            # Detect language (auto-detect if not specified)
            detected_language = self._detect_language_extended(normalized_query)
            if detected_language != language:
                logger.info(f"Language detected: {detected_language}, using instead of {language}")
                language = detected_language
            
            # If not English, translate to English for intent handling
            working_query = normalized_query
            if language not in ['en', 'hinglish']:
                translated = self._translate_to_en(normalized_query, source_lang=language)
                if translated:
                    working_query = translated

            # Try to extract location from user query and geocode to lat/lon
            self._maybe_update_context_from_query(working_query)
            self._maybe_extract_place_and_geocode(normalized_query, language)

            # Get response based on intent
            response = self._generate_response(working_query, language)
            
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

    def _maybe_update_context_from_query(self, query: str) -> None:
        """Extract lat/lon and simple product tokens from free text and store in context"""
        # Extract coordinates like: 28.6, 77.2 or lat 28.6 lon 77.2
        coord_pattern = re.compile(r"(?P<lat>[+-]?\d{1,2}\.\d+)\s*[,\s]\s*(?P<lon>[+-]?\d{1,3}\.\d+)")
        m = coord_pattern.search(query)
        if m:
            try:
                self.conversation_context["last_lat"] = float(m.group("lat"))
                self.conversation_context["last_lon"] = float(m.group("lon"))
            except Exception:
                pass

        # Simple product extraction (single word commodity names)
        for token in ["wheat", "rice", "corn", "cotton", "soybean", "onion", "sugarcane"]:
            if token in query:
                self.conversation_context["last_product"] = token.capitalize()
                break

    def _maybe_extract_place_and_geocode(self, original_query: str, language: str) -> None:
        """Heuristic place extraction and geocoding using OpenStreetMap Nominatim."""
        try:
            # Very simple heuristics for place extraction; improve with NER later
            # Look for words after 'in/at/near' or Hindi equivalents
            patterns = [
                r"(?:in|at|near)\s+([A-Za-z][A-Za-z\s]{2,40})",
                r"(?:में|के पास|पास)\s+([\u0900-\u097F\s]{2,40})",
            ]
            place: Optional[str] = None
            for pat in patterns:
                m = re.search(pat, original_query, flags=re.IGNORECASE)
                if m:
                    place = m.group(1).strip()
                    break
            if not place:
                return
            # Geocode
            resp = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": place, "format": "json", "limit": 1},
                headers={"User-Agent": "agri-advisory-app/1.0"}, timeout=8
            )
            if resp.ok:
                arr = resp.json()
                if arr:
                    lat = float(arr[0].get("lat"))
                    lon = float(arr[0].get("lon"))
                    self.conversation_context["last_lat"] = lat
                    self.conversation_context["last_lon"] = lon
        except Exception:
            pass

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
        # Try live answers when possible (location/product available)
        lat = self.conversation_context.get("last_lat")
        lon = self.conversation_context.get("last_lon")
        product = self.conversation_context.get("last_product")

        # Crop recommendations
        if any(word in query.lower() for word in ['crop', 'recommend', 'plant', 'फसल', 'बोना', 'उपयुक्त', 'suggest']):
            # Provide crop recommendations even without specific location
            if lat is not None and lon is not None:
                # Use a lightweight heuristic + ML system if available
                try:
                    # Use default soil/season if not known
                    soil_type = 'Loamy'
                    season = 'kharif'
                    forecast = self.weather_api.get_forecast_weather(lat, lon, 'en', days=3)
                    avg_max = 28.0
                    total_rain = 60.0
                    if forecast and 'forecast' in forecast and forecast['forecast']['forecastday']:
                        days = len(forecast['forecast']['forecastday'])
                        avg_max = sum([d['day'].get('maxtemp_c', 28.0) for d in forecast['forecast']['forecastday']]) / days
                        total_rain = sum([d['day'].get('totalprecip_mm', 20.0) for d in forecast['forecast']['forecastday']])

                    # Use government data service for accurate recommendations
                    if hasattr(self, 'advanced_chatbot') and self.advanced_chatbot:
                        gov_rec = self.advanced_chatbot.gov_data_service.get_icar_crop_recommendations(
                            soil_type=soil_type,
                            season=season,
                            temperature=avg_max,
                            rainfall=total_rain,
                            ph=6.5
                        )
                        if gov_rec and 'recommendations' in gov_rec:
                            return self._format_government_recommendations(gov_rec, language)
                    
                    # Fallback to ML system
                    ml_rec = self.ml_system.predict_crop_recommendation(
                        soil_type=soil_type,
                        season=season,
                        temperature=avg_max,
                        rainfall=total_rain,
                        humidity=60.0,
                        ph=6.5,
                        organic_matter=2.0
                    )
                    if ml_rec and 'recommendations' in ml_rec:
                        top = ml_rec['recommendations'][:3]
                        names = ", ".join([r['crop'] for r in top])
                        return (f"Based on your location and short-term forecast, recommended crops are: {names}. "
                                f"Share your soil type/season for more precise advice.") if language != 'hi' else (
                                f"आपके स्थान और निकट भविष्य के मौसम के आधार पर सुझाई गई फसलें: {names}. "
                                f"अधिक सटीक सलाह हेतु मिट्टी का प्रकार/सीजन बताएं।")
                except Exception:
                    pass
            return self._get_crop_recommendation_response(language)
        
        # Weather queries
        elif any(word in query.lower() for word in ['weather', 'rain', 'temperature', 'मौसम', 'बारिश', 'तापमान']):
            if lat is not None and lon is not None:
                try:
                    current = self.weather_api.get_current_weather(lat, lon, 'en')
                    if current and 'current' in current:
                        temp = current['current'].get('temp_c', 26)
                        cond = current['current'].get('condition', {}).get('text', 'Clear')
                        city = current['location'].get('name', 'your area')
                        return (f"Weather in {city}: {cond}, {temp}°C. Ask for forecast to plan sowing/harvest.") if language != 'hi' else (
                                f"{city} का मौसम: {cond}, {temp}°C. बोआई/कटाई योजना हेतु पूर्वानुमान पूछें।")
                except Exception:
                    pass
            return self._get_weather_response(language)
        
        # Market prices
        elif any(word in query.lower() for word in ['price', 'market', 'cost', 'बाजार', 'कीमत', 'मूल्य']):
            if lat is not None and lon is not None:
                try:
                    data = get_market_prices(lat, lon, 'en', product)
                    if isinstance(data, dict) and data:
                        # Pick up to 3 items
                        items = [(k, v) for k, v in data.items() if isinstance(v, dict) and 'price' in v][:3]
                        if items:
                            msg = ", ".join([f"{k}: {v['price']} {v.get('unit','')}" for k, v in items])
                            return (f"Latest market prices near you: {msg}.") if language != 'hi' else (
                                    f"आपके पास के बाजार भाव: {msg}.")
                except Exception:
                    pass
            return self._get_market_response(language)
        
        # Soil/Fertilizer
        elif any(word in query.lower() for word in ['soil', 'fertilizer', 'nutrient', 'मिट्टी', 'खाद', 'उर्वरक']):
            return self._get_soil_response(language)
        
        # General agricultural advice
        else:
            # Route via lightweight LLM if available, else fallback
            llm = self._get_generation_pipeline()
            if llm is not None:
                try:
                    prompt = self._build_llm_prompt(query, language)
                    out = llm(prompt, max_new_tokens=128, do_sample=False)
                    text = out[0]['generated_text'] if isinstance(out, list) else str(out)
                    return text.strip()
                except Exception:
                    pass
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

    def _detect_language_extended(self, query: str) -> str:
        """Lightweight language detection for major Indic languages and Hinglish/English."""
        # Devanagari
        if re.search(r'[\u0900-\u097F]', query):
            return 'hi'
        # Gurmukhi (Punjabi)
        if re.search(r'[\u0A00-\u0A7F]', query):
            return 'pa'
        # Gujarati
        if re.search(r'[\u0A80-\u0AFF]', query):
            return 'gu'
        # Oriya (Odia)
        if re.search(r'[\u0B00-\u0B7F]', query):
            return 'or'
        # Bengali
        if re.search(r'[\u0980-\u09FF]', query):
            return 'bn'
        # Tamil
        if re.search(r'[\u0B80-\u0BFF]', query):
            return 'ta'
        # Telugu
        if re.search(r'[\u0C00-\u0C7F]', query):
            return 'te'
        # Kannada
        if re.search(r'[\u0C80-\u0CFF]', query):
            return 'kn'
        # Malayalam
        if re.search(r'[\u0D00-\u0D7F]', query):
            return 'ml'
        # Hinglish heuristics
        if any(tok in query.lower() for tok in ['bhai', 'kya', 'kaise', 'kab', 'kahan', 'krishi', 'kheti']):
            return 'hinglish'
        return 'en'

    def _translate_to_en(self, text: str, source_lang: str) -> Optional[str]:
        """Translate Indic language to English using transformers if available; fallback returns original."""
        if pipeline is None:
            return text
        try:
            model_map = {
                'hi': 'facebook/nllb-200-distilled-600M',
                'bn': 'facebook/nllb-200-distilled-600M',
                'pa': 'facebook/nllb-200-distilled-600M',
                'ta': 'facebook/nllb-200-distilled-600M',
                'te': 'facebook/nllb-200-distilled-600M',
                'kn': 'facebook/nllb-200-distilled-600M',
                'ml': 'facebook/nllb-200-distilled-600M',
                'gu': 'facebook/nllb-200-distilled-600M',
                'or': 'facebook/nllb-200-distilled-600M',
            }
            model = model_map.get(source_lang)
            if not model:
                return text
            translator = pipeline('translation', model=model, src_lang=source_lang, tgt_lang='en')
            out = translator(text, max_length=256)
            if out and isinstance(out, list) and 'translation_text' in out[0]:
                return out[0]['translation_text']
        except Exception:
            pass
        return text

    def _get_generation_pipeline(self):
        """Lazy initialize a small text generation pipeline for general responses."""
        if self._gen_pipeline is not None:
            return self._gen_pipeline
        if pipeline is None:
            return None
        try:
            # A small seq2seq model works better for instruction-like prompts
            self._gen_pipeline = pipeline('text2text-generation', model='google/flan-t5-base')
            return self._gen_pipeline
        except Exception:
            try:
                self._gen_pipeline = pipeline('text-generation', model='distilgpt2')
                return self._gen_pipeline
            except Exception:
                return None

    def _build_llm_prompt(self, query: str, language: str) -> str:
        """Construct a concise prompt for the LLM while keeping agricultural context."""
        lat = self.conversation_context.get('last_lat')
        lon = self.conversation_context.get('last_lon')
        loc = f"Location: {lat},{lon}. " if (lat is not None and lon is not None) else ""
        if language != 'en':
            # Keep user's language note; generation model might still output English
            lang_note = f"User language: {language}. "
        else:
            lang_note = ""
        return (
            f"You are Krishimitra, an agricultural advisor for Indian farmers. {loc}{lang_note}"
            f"Answer helpfully and concisely with practical steps. Question: {query}"
        )

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
