"""
Security utilities for input validation, sanitization, and protection
"""

import re
import html
import json
import logging
import functools
from typing import Any, Dict, List, Optional, Union
from django.utils.html import escape
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import bleach
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class SecurityValidator:
    """Comprehensive security validation class"""
    
    # Maximum lengths for different input types
    MAX_CHAT_MESSAGE_LENGTH = 2000
    MAX_USERNAME_LENGTH = 100
    MAX_LOCATION_LENGTH = 200
    MAX_SESSION_ID_LENGTH = 100
    
    # Allowed characters patterns
    ALLOWED_LANGUAGES = ['en', 'hi', 'hinglish', 'bn', 'te', 'ta', 'gu', 'mr', 'kn', 'ml', 'pa', 'or', 'as', 'ne', 'ur', 'ar', 'es', 'fr', 'de', 'zh', 'ja', 'ko', 'pt', 'ru', 'it', 'auto']
    
    # Dangerous patterns to detect
    DANGEROUS_PATTERNS = [
        r'<script.*?>.*?</script>',  # Script tags
        r'javascript:',              # JavaScript URLs
        r'vbscript:',               # VBScript URLs
        r'data:text/html',          # Data URLs
        r'<iframe.*?>',             # Iframe tags
        r'<object.*?>',             # Object tags
        r'<embed.*?>',              # Embed tags
        r'<link.*?>',               # Link tags
        r'<meta.*?>',               # Meta tags
        r'on\w+\s*=',               # Event handlers
        r'expression\s*\(',         # CSS expressions
    ]
    
    def __init__(self):
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.DANGEROUS_PATTERNS]
        
        # Enhanced error recovery patterns
        self.error_recovery_patterns = {
            'invalid_coordinates': {
                'pattern': r'^[-+]?[0-9]*\.?[0-9]+$',
                'message': 'Invalid coordinate format. Please use decimal numbers.'
            },
            'invalid_language': {
                'pattern': r'^[a-z]{2,10}$',
                'message': 'Invalid language code. Please use standard language codes.'
            },
            'invalid_crop_name': {
                'pattern': r'^[a-zA-Z\s\u0900-\u097F\u0A00-\u0A7F\u0B00-\u0B7F\u0C00-\u0C7F\u0D00-\u0D7F\u0E00-\u0E7F\u0F00-\u0F7F]+$',
                'message': 'Invalid crop name. Please use only letters and spaces.'
            }
        }
        
        # Fallback responses for different error types
        self.fallback_responses = {
            'invalid_input': {
                'en': 'I apologize, but I couldn\'t understand your input. Could you please rephrase your question?',
                'hi': 'मुझे खेद है, लेकिन मैं आपके इनपुट को समझ नहीं सका। क्या आप अपना प्रश्न दोबारा बता सकते हैं?',
                'hinglish': 'Sorry yaar, samajh nahi aaya. Could you please repeat your question?'
            },
            'api_error': {
                'en': 'I\'m experiencing some technical difficulties. Please try again in a moment.',
                'hi': 'मुझे कुछ तकनीकी समस्याएं आ रही हैं। कृपया कुछ देर बाद फिर से कोशिश करें।',
                'hinglish': 'Technical issue aa raha hai. Please try again after some time.'
            },
            'location_error': {
                'en': 'I couldn\'t find that location. Please provide a valid city or state name.',
                'hi': 'मुझे वह स्थान नहीं मिला। कृपया एक वैध शहर या राज्य का नाम दें।',
                'hinglish': 'Location nahi mili. Please valid city ya state name do.'
            }
        }
    
    def validate_chat_message(self, message: str) -> Dict[str, Any]:
        """Validate and sanitize chat message input"""
        result = {
            'valid': True,
            'sanitized': '',
            'errors': [],
            'warnings': []
        }
        
        try:
            # Check if message exists and is string
            if not isinstance(message, str):
                result['valid'] = False
                result['errors'].append("Message must be a string")
                return result
            
            # Check length
            if len(message) > self.MAX_CHAT_MESSAGE_LENGTH:
                result['valid'] = False
                result['errors'].append(f"Message too long. Maximum {self.MAX_CHAT_MESSAGE_LENGTH} characters allowed")
                return result
            
            # Check for empty or whitespace-only messages
            if not message.strip():
                result['valid'] = False
                result['errors'].append("Message cannot be empty")
                return result
            
            # Check for dangerous patterns
            for pattern in self.compiled_patterns:
                if pattern.search(message):
                    result['warnings'].append(f"Potentially dangerous content detected: {pattern.pattern}")
            
            # Sanitize HTML content
            sanitized = self.sanitize_html(message)
            
            # Additional XSS protection
            sanitized = html.escape(sanitized, quote=True)
            
            # Remove excessive whitespace
            sanitized = re.sub(r'\s+', ' ', sanitized).strip()
            
            result['sanitized'] = sanitized
            
            # Check for suspicious content
            if self.detect_suspicious_content(message):
                result['warnings'].append("Suspicious content detected")
            
        except Exception as e:
            logger.error(f"Error validating chat message: {e}")
            result['valid'] = False
            result['errors'].append("Validation error occurred")
        
        return result
    
    def validate_language_code(self, language: str) -> bool:
        """Validate language code"""
        return language in self.ALLOWED_LANGUAGES
    
    def validate_user_id(self, user_id: str) -> Dict[str, Any]:
        """Validate user ID"""
        result = {
            'valid': True,
            'sanitized': '',
            'errors': []
        }
        
        if not isinstance(user_id, str):
            result['valid'] = False
            result['errors'].append("User ID must be a string")
            return result
        
        if len(user_id) > self.MAX_USERNAME_LENGTH:
            result['valid'] = False
            result['errors'].append(f"User ID too long. Maximum {self.MAX_USERNAME_LENGTH} characters allowed")
            return result
        
        # Allow alphanumeric, underscore, and hyphen
        if not re.match(r'^[a-zA-Z0-9_-]+$', user_id):
            result['valid'] = False
            result['errors'].append("User ID contains invalid characters")
            return result
        
        result['sanitized'] = user_id.lower().strip()
        return result
    
    def validate_session_id(self, session_id: str) -> Dict[str, Any]:
        """Validate session ID"""
        result = {
            'valid': True,
            'sanitized': '',
            'errors': []
        }
        
        if not isinstance(session_id, str):
            result['valid'] = False
            result['errors'].append("Session ID must be a string")
            return result
        
        if len(session_id) > self.MAX_SESSION_ID_LENGTH:
            result['valid'] = False
            result['errors'].append(f"Session ID too long. Maximum {self.MAX_SESSION_ID_LENGTH} characters allowed")
            return result
        
        # Allow alphanumeric, underscore, and hyphen
        if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
            result['valid'] = False
            result['errors'].append("Session ID contains invalid characters")
            return result
        
        result['sanitized'] = session_id.strip()
        return result
    
    def validate_location(self, location: str) -> Dict[str, Any]:
        """Validate location input"""
        result = {
            'valid': True,
            'sanitized': '',
            'errors': []
        }
        
        if not isinstance(location, str):
            result['valid'] = False
            result['errors'].append("Location must be a string")
            return result
        
        if len(location) > self.MAX_LOCATION_LENGTH:
            result['valid'] = False
            result['errors'].append(f"Location too long. Maximum {self.MAX_LOCATION_LENGTH} characters allowed")
            return result
        
        # Sanitize location
        sanitized = self.sanitize_text(location)
        
        # Check for valid location characters (letters, numbers, spaces, commas, hyphens)
        if not re.match(r'^[a-zA-Z0-9\s,.-]+$', sanitized):
            result['valid'] = False
            result['errors'].append("Location contains invalid characters")
            return result
        
        result['sanitized'] = sanitized.strip()
        return result
    
    def validate_coordinates(self, lat: Union[float, str], lon: Union[float, str]) -> Dict[str, Any]:
        """Validate latitude and longitude coordinates"""
        result = {
            'valid': True,
            'sanitized_lat': None,
            'sanitized_lon': None,
            'errors': []
        }
        
        try:
            # Convert to float
            lat_float = float(lat)
            lon_float = float(lon)
            
            # Validate latitude range
            if not -90 <= lat_float <= 90:
                result['valid'] = False
                result['errors'].append("Latitude must be between -90 and 90 degrees")
                return result
            
            # Validate longitude range
            if not -180 <= lon_float <= 180:
                result['valid'] = False
                result['errors'].append("Longitude must be between -180 and 180 degrees")
                return result
            
            result['sanitized_lat'] = round(lat_float, 6)
            result['sanitized_lon'] = round(lon_float, 6)
            
        except (ValueError, TypeError):
            result['valid'] = False
            result['errors'].append("Invalid coordinate format")
        
        return result
    
    def sanitize_html(self, text: str) -> str:
        """Sanitize HTML content using bleach"""
        try:
            # Allowed tags and attributes
            allowed_tags = ['b', 'i', 'em', 'strong', 'p', 'br', 'ul', 'ol', 'li']
            allowed_attributes = {}
            
            # Clean the text
            cleaned = bleach.clean(text, tags=allowed_tags, attributes=allowed_attributes, strip=True)
            return cleaned
        except Exception as e:
            logger.warning(f"HTML sanitization failed: {e}")
            # Fallback to basic HTML escaping
            return html.escape(text, quote=True)
    
    def sanitize_text(self, text: str) -> str:
        """Basic text sanitization"""
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters except newlines and tabs
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        return text.strip()
    
    def detect_suspicious_content(self, text: str) -> bool:
        """Detect potentially suspicious content"""
        suspicious_patterns = [
            r'(password|pwd|pass)\s*[:=]',  # Password mentions
            r'(token|key|secret)\s*[:=]',   # Secret mentions
            r'admin\s*[:=]',                # Admin mentions
            r'root\s*[:=]',                 # Root mentions
            r'SELECT\s+.*FROM',             # SQL injection patterns
            r'UNION\s+SELECT',              # SQL injection patterns
            r'<script',                     # Script tags
            r'javascript:',                 # JavaScript URLs
        ]
        
        text_lower = text.lower()
        for pattern in suspicious_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        return False
    
    def validate_api_request(self, request_data: Dict) -> Dict[str, Any]:
        """Validate complete API request"""
        result = {
            'valid': True,
            'sanitized_data': {},
            'errors': [],
            'warnings': []
        }
        
        try:
            # Validate required fields
            if 'query' not in request_data:
                result['valid'] = False
                result['errors'].append("Query field is required")
                return result
            
            # Validate chat message
            message_validation = self.validate_chat_message(request_data['query'])
            if not message_validation['valid']:
                result['valid'] = False
                result['errors'].extend(message_validation['errors'])
                return result
            
            result['sanitized_data']['query'] = message_validation['sanitized']
            result['warnings'].extend(message_validation['warnings'])
            
            # Validate language
            language = request_data.get('language', 'auto')
            if not self.validate_language_code(language):
                result['valid'] = False
                result['errors'].append("Invalid language code")
                return result
            result['sanitized_data']['language'] = language
            
            # Validate user_id if provided
            if 'user_id' in request_data:
                user_validation = self.validate_user_id(request_data['user_id'])
                if not user_validation['valid']:
                    result['valid'] = False
                    result['errors'].extend(user_validation['errors'])
                    return result
                result['sanitized_data']['user_id'] = user_validation['sanitized']
            
            # Validate session_id if provided
            if 'session_id' in request_data:
                session_validation = self.validate_session_id(request_data['session_id'])
                if not session_validation['valid']:
                    result['valid'] = False
                    result['errors'].extend(session_validation['errors'])
                    return result
                result['sanitized_data']['session_id'] = session_validation['sanitized']
            
        except Exception as e:
            logger.error(f"API request validation error: {e}")
            result['valid'] = False
            result['errors'].append("Request validation error occurred")
        
        return result

# Rate limiting
class RateLimiter:
    """Simple rate limiter for API endpoints"""
    
    def __init__(self):
        self.requests = {}  # In production, use Redis or database
    
    def is_allowed(self, identifier: str, max_requests: int = 100, window_seconds: int = 3600) -> bool:
        """Check if request is allowed based on rate limit"""
        import time
        
        current_time = time.time()
        window_start = current_time - window_seconds
        
        # Clean old requests
        if identifier in self.requests:
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier] 
                if req_time > window_start
            ]
        else:
            self.requests[identifier] = []
        
        # Check rate limit
        if len(self.requests[identifier]) >= max_requests:
            return False
        
        # Add current request
        self.requests[identifier].append(current_time)
        return True

# Security headers
def add_security_headers(response):
    """Add security headers to response"""
    response['X-Content-Type-Options'] = 'nosniff'
    response['X-Frame-Options'] = 'DENY'
    response['X-XSS-Protection'] = '1; mode=block'
    response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    return response

# Global instances
security_validator = SecurityValidator()
rate_limiter = RateLimiter()

# Security decorators
def secure_api_endpoint(max_requests: int = 100, window_seconds: int = 3600):
    """Decorator for secure API endpoints"""
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Get client identifier
            client_ip = request.META.get('REMOTE_ADDR', 'unknown')
            user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')
            identifier = f"{client_ip}:{hash(user_agent)}"
            
            # Check rate limit
            if not rate_limiter.is_allowed(identifier, max_requests, window_seconds):
                from django.http import JsonResponse
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'message': 'Too many requests. Please try again later.'
                }, status=429)
            
            # Validate request data
            if request.method == 'POST':
                try:
                    request_data = json.loads(request.body) if request.body else {}
                except json.JSONDecodeError:
                    from django.http import JsonResponse
                    return JsonResponse({
                        'error': 'Invalid JSON',
                        'message': 'Request body must be valid JSON'
                    }, status=400)
                
                validation = security_validator.validate_api_request(request_data)
                if not validation['valid']:
                    from django.http import JsonResponse
                    return JsonResponse({
                        'error': 'Validation failed',
                        'errors': validation['errors']
                    }, status=400)
                
                # Add sanitized data to request
                request.sanitized_data = validation['sanitized_data']
                request.validation_warnings = validation['warnings']
            
            # Process request
            response = view_func(request, *args, **kwargs)
            
            # Add security headers
            response = add_security_headers(response)
            
            return response
        
        return wrapper
    return decorator

    def get_error_recovery_response(self, error_type: str, language: str = 'en') -> str:
        """Get appropriate error recovery response based on error type and language"""
        try:
            response = self.fallback_responses.get(error_type, self.fallback_responses['invalid_input'])
            return response.get(language, response['en'])
        except Exception as e:
            logger.error(f"Error getting recovery response: {e}")
            return "I apologize for the error. Please try again."

    def validate_with_recovery(self, input_data: Any, validation_type: str) -> Dict[str, Any]:
        """Validate input with automatic recovery suggestions"""
        result = {
            'valid': True,
            'data': input_data,
            'errors': [],
            'recovery_suggestions': []
        }
        
        try:
            if validation_type == 'coordinates':
                if isinstance(input_data, (int, float)):
                    if not (-90 <= input_data <= 90):
                        result['valid'] = False
                        result['errors'].append('Latitude must be between -90 and 90')
                        result['recovery_suggestions'].append('Please provide a valid latitude coordinate')
                elif isinstance(input_data, str):
                    try:
                        float_val = float(input_data)
                        if not (-90 <= float_val <= 90):
                            result['valid'] = False
                            result['errors'].append('Invalid coordinate range')
                            result['recovery_suggestions'].append('Please provide coordinates between -90 and 90')
                        else:
                            result['data'] = float_val
                    except ValueError:
                        result['valid'] = False
                        result['errors'].append('Invalid coordinate format')
                        result['recovery_suggestions'].append('Please provide a decimal number')
            
            elif validation_type == 'language':
                if input_data not in self.ALLOWED_LANGUAGES:
                    result['valid'] = False
                    result['errors'].append(f'Language "{input_data}" not supported')
                    result['recovery_suggestions'].append(f'Please use one of: {", ".join(self.ALLOWED_LANGUAGES[:5])}...')
                    # Auto-correct common mistakes
                    if input_data.lower() in ['hindi', 'hind']:
                        result['data'] = 'hi'
                        result['valid'] = True
                        result['recovery_suggestions'].append('Auto-corrected to "hi"')
                    elif input_data.lower() in ['english', 'eng']:
                        result['data'] = 'en'
                        result['valid'] = True
                        result['recovery_suggestions'].append('Auto-corrected to "en"')
            
            elif validation_type == 'crop_name':
                if not isinstance(input_data, str) or len(input_data.strip()) == 0:
                    result['valid'] = False
                    result['errors'].append('Crop name cannot be empty')
                    result['recovery_suggestions'].append('Please provide a valid crop name')
                else:
                    # Clean and normalize crop name
                    cleaned_name = input_data.strip().lower()
                    result['data'] = cleaned_name
                    
                    # Suggest corrections for common misspellings
                    crop_corrections = {
                        'wheet': 'wheat',
                        'rice': 'rice',
                        'maize': 'maize',
                        'corn': 'maize',
                        'chana': 'chickpea',
                        'dal': 'pulses',
                        'dal': 'lentil'
                    }
                    
                    if cleaned_name in crop_corrections:
                        result['data'] = crop_corrections[cleaned_name]
                        result['recovery_suggestions'].append(f'Corrected crop name to "{crop_corrections[cleaned_name]}"')
            
        except Exception as e:
            logger.error(f"Error in validation with recovery: {e}")
            result['valid'] = False
            result['errors'].append(f'Validation error: {str(e)}')
            result['recovery_suggestions'].append('Please check your input and try again')
        
        return result

    def create_graceful_error_response(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a graceful error response with recovery options"""
        context = context or {}
        language = context.get('language', 'en')
        
        error_response = {
            'success': False,
            'error_type': type(error).__name__,
            'message': self.get_error_recovery_response('api_error', language),
            'recovery_options': [],
            'timestamp': time.time()
        }
        
        # Add specific recovery options based on error type
        if 'connection' in str(error).lower():
            error_response['recovery_options'].append({
                'action': 'retry',
                'message': 'Try again in a few moments',
                'delay': 5
            })
            error_response['recovery_options'].append({
                'action': 'fallback',
                'message': 'Use cached data',
                'data_available': True
            })
        
        elif 'validation' in str(error).lower():
            error_response['recovery_options'].append({
                'action': 'correct_input',
                'message': 'Please check your input format',
                'examples': context.get('valid_examples', [])
            })
        
        elif 'permission' in str(error).lower():
            error_response['recovery_options'].append({
                'action': 'authenticate',
                'message': 'Please log in to continue',
                'redirect': '/login'
            })
        
        return error_response

# Enhanced global instances
security_validator = SecurityValidator()

# Add time import for error responses
import time
