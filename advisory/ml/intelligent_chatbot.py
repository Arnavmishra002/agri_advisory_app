#!/usr/bin/env python3
"""
INTELLIGENT AGRICULTURAL CHATBOT
Clean, working version with super intelligence
"""

from .ultimate_intelligent_ai import ultimate_ai
import logging
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class IntelligentAgriculturalChatbot:
    """Intelligent Agricultural Chatbot with super AI capabilities"""
    
    def __init__(self):
        pass
    
    def get_response(self, user_query: str, language: str = 'en', user_id: str = None, 
                    session_id: str = None, latitude: float = None, longitude: float = None,
                    conversation_history: List = None, location_name: str = None) -> Dict[str, Any]:
        """Generate ChatGPT-level intelligent, contextual responses"""
        try:
            # Use the ultimate intelligent AI
            return ultimate_ai.get_response(
                user_query=user_query,
                language=language,
                user_id=user_id,
                session_id=session_id,
                latitude=latitude,
                longitude=longitude,
                conversation_history=conversation_history,
                location_name=location_name
            )
            
        except Exception as e:
            logger.error(f"Error in intelligent chatbot: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "response": "Sorry, I couldn't understand your request. Please try again.",
                "source": "error",
                "confidence": 0.1,
                "language": language,
                "error": str(e)
            }
