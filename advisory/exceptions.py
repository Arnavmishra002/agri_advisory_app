"""
Custom Exception Classes for Agri Advisory App
Provides specific exceptions for better error handling and debugging
"""

class AgriAdvisoryError(Exception):
    """Base exception for all Agri Advisory errors"""
    pass

class LocationDetectionError(AgriAdvisoryError):
    """Raised when location detection fails"""
    pass

class WeatherAPIError(AgriAdvisoryError):
    """Raised when weather API calls fail"""
    pass

class MarketPriceError(AgriAdvisoryError):
    """Raised when market price fetching fails"""
    pass

class CropRecommendationError(AgriAdvisoryError):
    """Raised when crop recommendation generation fails"""
    pass

class ChatbotError(AgriAdvisoryError):
    """Raised when chatbot processing fails"""
    pass

class APIRateLimitError(AgriAdvisoryError):
    """Raised when API rate limit is exceeded"""
    pass

class CacheError(AgriAdvisoryError):
    """Raised when cache operations fail"""
    pass
