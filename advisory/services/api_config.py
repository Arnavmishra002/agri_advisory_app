#!/usr/bin/env python3
"""
API Configuration for General APIs
Set your API keys here for enhanced functionality
"""

import os
from typing import Optional

class APIConfig:
    """Configuration for external APIs"""
    
    # Hugging Face API (FREE - 30,000 requests/month)
    HUGGINGFACE_TOKEN: Optional[str] = os.environ.get('HUGGINGFACE_TOKEN', None)
    
    # OpenAI API (FREE - $5 credit monthly)
    OPENAI_API_KEY: Optional[str] = os.environ.get('OPENAI_API_KEY', None)
    
    # News API (FREE - 100 requests/day)
    NEWS_API_KEY: Optional[str] = os.environ.get('NEWS_API_KEY', None)
    
    # Weather API (FREE - 1000 requests/day)
    WEATHER_API_KEY: Optional[str] = os.environ.get('WEATHER_API_KEY', None)
    
    @classmethod
    def get_huggingface_token(cls) -> Optional[str]:
        """Get Hugging Face token"""
        return cls.HUGGINGFACE_TOKEN
    
    @classmethod
    def get_openai_token(cls) -> Optional[str]:
        """Get OpenAI API key"""
        return cls.OPENAI_API_KEY
    
    @classmethod
    def get_news_api_key(cls) -> Optional[str]:
        """Get News API key"""
        return cls.NEWS_API_KEY
    
    @classmethod
    def get_weather_api_key(cls) -> Optional[str]:
        """Get Weather API key"""
        return cls.WEATHER_API_KEY
    
    @classmethod
    def is_huggingface_enabled(cls) -> bool:
        """Check if Hugging Face is enabled"""
        return cls.HUGGINGFACE_TOKEN is not None
    
    @classmethod
    def is_openai_enabled(cls) -> bool:
        """Check if OpenAI is enabled"""
        return cls.OPENAI_API_KEY is not None
    
    @classmethod
    def is_news_api_enabled(cls) -> bool:
        """Check if News API is enabled"""
        return cls.NEWS_API_KEY is not None
    
    @classmethod
    def is_weather_api_enabled(cls) -> bool:
        """Check if Weather API is enabled"""
        return cls.WEATHER_API_KEY is not None

# Create global instance
api_config = APIConfig()