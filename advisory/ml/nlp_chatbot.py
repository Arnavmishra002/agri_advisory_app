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

    def _fallback_response(self, language: str) -> str:
        if language == 'hi':
            return "मुझे इसकी विशेष जानकारी नहीं है। क्या आप अपने प्रश्न को फिर से दोहरा सकते हैं या मौसम, मिट्टी, बाजार की कीमतों या फसल की सिफारिशों के बारे में पूछ सकते हैं?"
        return "I'm sorry, I don't have specific information on that. Could you please rephrase your question or ask about weather, soil, market prices, or crop recommendations?"
