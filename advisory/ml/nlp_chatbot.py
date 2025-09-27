import logging
from transformers import pipeline
from typing import Dict, Any

logger = logging.getLogger(__name__)

class NLPAgriculturalChatbot:
    def __init__(self, model_name="distilbert-base-uncased-distilled-squad"):
        try:
            # Initialize a question-answering pipeline from HuggingFace transformers
            self.qa_pipeline = pipeline("question-answering", model=model_name)
            logger.info(f"NLP Chatbot initialized with HuggingFace model: {model_name}")
        except Exception as e:
            logger.error(f"Error initializing HuggingFace NLP model: {e}")
            self.qa_pipeline = None # Fallback if model fails to load
    
    def get_response(self, user_query: str, language: str = 'en') -> Dict[str, Any]:
        """
        Generates a response to the user query using the NLP model.
        Currently supports basic question-answering. 
        For multi-turn conversations, integration with a dialogue system (e.g., Dialogflow) 
        or a more complex conversational AI framework would be needed.
        """
        if not self.qa_pipeline:
            return {"response": self._fallback_response(language), "source": "fallback"}

        try:
            # For a simple QA model, we need a context. This context would ideally come from
            # a knowledge base (e.g., retrieved from a database based on query intent).
            # For this placeholder, let's use a very general agricultural context.
            context = self._get_dynamic_context(user_query, language)
            
            if not context:
                return {"response": self._fallback_response(language), "source": "no_context"}

            # Use the QA pipeline to get an answer
            result = self.qa_pipeline(question=user_query, context=context)
            
            response_text = result['answer']
            # Add some simple logic to make the response more conversational if needed
            if len(response_text) < 10 or result['score'] < 0.3: # Low confidence
                response_text = f"I found this: '{response_text}'. Could you provide more details?"

            return {"response": response_text, "source": "nlp_model", "confidence": result['score']}

        except Exception as e:
            logger.error(f"Error generating NLP response for query '{user_query}': {e}")
            return {"response": self._fallback_response(language), "source": "error"}

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
