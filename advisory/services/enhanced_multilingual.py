#!/usr/bin/env python3
"""
Enhanced Multilingual Support
Improves Hindi, English, and Hinglish language handling
"""

import re
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class EnhancedMultilingualSupport:
    """Enhanced multilingual support for better language handling"""
    
    def __init__(self):
        # Comprehensive language patterns
        self.language_patterns = {
            'hindi': {
                'script': r'[\u0900-\u097F]',  # Devanagari script
                'common_words': [
                    'क्या', 'कैसे', 'कब', 'कहां', 'कौन', 'क्यों', 'में', 'पर', 'से', 'को',
                    'है', 'हैं', 'था', 'थे', 'थी', 'होगा', 'होगी', 'होंगे', 'कर', 'करना',
                    'मैं', 'आप', 'हम', 'वे', 'यह', 'वह', 'इस', 'उस', 'कोई', 'कुछ',
                    'सब', 'सभी', 'हर', 'कई', 'कुछ', 'बहुत', 'थोड़ा', 'ज्यादा', 'कम'
                ],
                'agricultural_terms': [
                    'फसल', 'खेती', 'कृषि', 'किसान', 'बीज', 'उर्वरक', 'कीट', 'रोग',
                    'मौसम', 'बारिश', 'सिंचाई', 'मिट्टी', 'जमीन', 'खेत', 'मंडी', 'कीमत',
                    'लाभ', 'नुकसान', 'सरकार', 'योजना', 'सब्सिडी', 'कर्ज', 'मदद'
                ]
            },
            'english': {
                'common_words': [
                    'what', 'how', 'when', 'where', 'who', 'why', 'is', 'are', 'was', 'were',
                    'will', 'would', 'can', 'could', 'should', 'may', 'might', 'do', 'does', 'did',
                    'i', 'you', 'we', 'they', 'he', 'she', 'it', 'this', 'that', 'some', 'any',
                    'all', 'every', 'many', 'much', 'little', 'more', 'less', 'very', 'quite'
                ],
                'agricultural_terms': [
                    'crop', 'farming', 'agriculture', 'farmer', 'seed', 'fertilizer', 'pest', 'disease',
                    'weather', 'rain', 'irrigation', 'soil', 'land', 'field', 'market', 'price',
                    'profit', 'loss', 'government', 'scheme', 'subsidy', 'loan', 'help'
                ]
            },
            'hinglish': {
                'patterns': [
                    r'\b\w*[aeiouAEIOU]\w*\s+है\b',  # English word + है
                    r'\b\w*[aeiouAEIOU]\w*\s+कर\b',  # English word + कर
                    r'\b\w*[aeiouAEIOU]\w*\s+में\b',  # English word + में
                    r'\bक्या\s+\w*[aeiouAEIOU]\w*\b',  # क्या + English word
                    r'\b\w*[aeiouAEIOU]\w*\s+की\s+कीमत\b',  # English + की कीमत
                    r'\b\w*[aeiouAEIOU]\w*\s+की\s+फसल\b',  # English + की फसल
                ],
                'common_mixes': [
                    'crop की कीमत', 'weather कैसा है', 'fertilizer कौन सा', 'pest control कैसे',
                    'market price क्या है', 'government scheme कौन सी', 'loan कैसे मिलेगा',
                    'soil testing कहां होगा', 'irrigation कैसे करें', 'harvest कब करें'
                ]
            }
        }
        
        # Translation dictionaries
        self.translations = {
            'hindi_to_english': {
                'फसल': 'crop', 'खेती': 'farming', 'कृषि': 'agriculture', 'किसान': 'farmer',
                'बीज': 'seed', 'उर्वरक': 'fertilizer', 'कीट': 'pest', 'रोग': 'disease',
                'मौसम': 'weather', 'बारिश': 'rain', 'सिंचाई': 'irrigation', 'मिट्टी': 'soil',
                'जमीन': 'land', 'खेत': 'field', 'मंडी': 'market', 'कीमत': 'price',
                'लाभ': 'profit', 'नुकसान': 'loss', 'सरकार': 'government', 'योजना': 'scheme',
                'सब्सिडी': 'subsidy', 'कर्ज': 'loan', 'मदद': 'help', 'क्या': 'what',
                'कैसे': 'how', 'कब': 'when', 'कहां': 'where', 'कौन': 'who', 'क्यों': 'why'
            },
            'english_to_hindi': {
                'crop': 'फसल', 'farming': 'खेती', 'agriculture': 'कृषि', 'farmer': 'किसान',
                'seed': 'बीज', 'fertilizer': 'उर्वरक', 'pest': 'कीट', 'disease': 'रोग',
                'weather': 'मौसम', 'rain': 'बारिश', 'irrigation': 'सिंचाई', 'soil': 'मिट्टी',
                'land': 'जमीन', 'field': 'खेत', 'market': 'मंडी', 'price': 'कीमत',
                'profit': 'लाभ', 'loss': 'नुकसान', 'government': 'सरकार', 'scheme': 'योजना',
                'subsidy': 'सब्सिडी', 'loan': 'कर्ज', 'help': 'मदद', 'what': 'क्या',
                'how': 'कैसे', 'when': 'कब', 'where': 'कहां', 'who': 'कौन', 'why': 'क्यों'
            }
        }
        
        # Response templates for different languages
        self.response_templates = {
            'hindi': {
                'greeting': 'नमस्ते! मैं आपकी कृषि सहायक हूं।',
                'crop_recommendation': '🌱 {location} के लिए फसल सुझाव:',
                'market_price': '💰 {location} में {crop} की कीमत:',
                'weather_info': '🌤️ {location} का मौसम:',
                'government_scheme': '🏛️ सरकारी योजनाएं:',
                'error': 'क्षमा करें, मुझे आपकी बात समझ नहीं आई।',
                'help': 'मैं आपकी कृषि समस्याओं में मदद कर सकता हूं।'
            },
            'english': {
                'greeting': 'Hello! I am your agricultural assistant.',
                'crop_recommendation': '🌱 Crop recommendations for {location}:',
                'market_price': '💰 {crop} price in {location}:',
                'weather_info': '🌤️ Weather in {location}:',
                'government_scheme': '🏛️ Government schemes:',
                'error': 'Sorry, I could not understand your request.',
                'help': 'I can help you with agricultural problems.'
            },
            'hinglish': {
                'greeting': 'Hello! मैं आपकी agricultural assistant हूं।',
                'crop_recommendation': '🌱 {location} के लिए crop suggestions:',
                'market_price': '💰 {location} में {crop} का price:',
                'weather_info': '🌤️ {location} का weather:',
                'government_scheme': '🏛️ Government schemes:',
                'error': 'Sorry, मुझे समझ नहीं आया।',
                'help': 'मैं आपकी farming problems में help कर सकता हूं।'
            }
        }
    
    def detect_language(self, text: str) -> str:
        """Enhanced language detection"""
        
        text_lower = text.lower().strip()
        
        # Check for Devanagari script
        devanagari_count = len(re.findall(self.language_patterns['hindi']['script'], text))
        
        if devanagari_count > 0:
            # Check if it's pure Hindi or Hinglish
            english_word_count = self._count_english_words(text_lower)
            hindi_word_count = self._count_hindi_words(text_lower)
            
            if english_word_count > 0 and hindi_word_count > 0:
                return 'hinglish'
            else:
                return 'hindi'
        
        # Check for Hinglish patterns
        hinglish_patterns = self.language_patterns['hinglish']['patterns']
        for pattern in hinglish_patterns:
            if re.search(pattern, text):
                return 'hinglish'
        
        # Check for common Hinglish phrases
        for phrase in self.language_patterns['hinglish']['common_mixes']:
            if phrase in text_lower:
                return 'hinglish'
        
        # Default to English
        return 'en'
    
    def translate_query(self, query: str, target_language: str) -> str:
        """Translate query to target language"""
        
        source_language = self.detect_language(query)
        
        if source_language == target_language:
            return query
        
        if target_language == 'hindi':
            return self._translate_to_hindi(query)
        elif target_language == 'english':
            return self._translate_to_english(query)
        elif target_language == 'hinglish':
            return self._translate_to_hinglish(query)
        
        return query
    
    def format_response(self, response_data: Dict[str, Any], language: str) -> str:
        """Format response according to language preferences"""
        
        if language == 'hindi':
            return self._format_hindi_response(response_data)
        elif language == 'hinglish':
            return self._format_hinglish_response(response_data)
        else:
            return self._format_english_response(response_data)
    
    def get_localized_template(self, template_key: str, language: str, **kwargs) -> str:
        """Get localized template with parameters"""
        
        templates = self.response_templates.get(language, self.response_templates['english'])
        template = templates.get(template_key, templates['error'])
        
        try:
            return template.format(**kwargs)
        except KeyError:
            return template
    
    def _count_english_words(self, text: str) -> int:
        """Count English words in text"""
        
        english_words = self.language_patterns['english']['common_words']
        count = 0
        
        for word in english_words:
            if word in text:
                count += 1
        
        # Also count words with English patterns
        english_pattern = r'\b[a-zA-Z]+\b'
        english_matches = re.findall(english_pattern, text)
        count += len(english_matches)
        
        return count
    
    def _count_hindi_words(self, text: str) -> int:
        """Count Hindi words in text"""
        
        hindi_words = self.language_patterns['hindi']['common_words']
        count = 0
        
        for word in hindi_words:
            if word in text:
                count += 1
        
        # Also count Devanagari script words
        devanagari_words = re.findall(r'[\u0900-\u097F]+', text)
        count += len(devanagari_words)
        
        return count
    
    def _translate_to_hindi(self, text: str) -> str:
        """Translate text to Hindi"""
        
        translated = text
        translations = self.translations['english_to_hindi']
        
        for english_word, hindi_word in translations.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(english_word) + r'\b'
            translated = re.sub(pattern, hindi_word, translated, flags=re.IGNORECASE)
        
        return translated
    
    def _translate_to_english(self, text: str) -> str:
        """Translate text to English"""
        
        translated = text
        translations = self.translations['hindi_to_english']
        
        for hindi_word, english_word in translations.items():
            translated = translated.replace(hindi_word, english_word)
        
        return translated
    
    def _translate_to_hinglish(self, text: str) -> str:
        """Translate text to Hinglish (mixed Hindi-English)"""
        
        # For Hinglish, we keep some words in English and translate others to Hindi
        hinglish_translations = {
            'crop': 'crop', 'price': 'price', 'weather': 'weather', 'market': 'market',
            'fertilizer': 'fertilizer', 'pest': 'pest', 'disease': 'disease',
            'government': 'government', 'scheme': 'scheme', 'subsidy': 'subsidy',
            'loan': 'loan', 'help': 'help', 'soil': 'soil', 'irrigation': 'irrigation'
        }
        
        translated = text
        for english_word, hinglish_word in hinglish_translations.items():
            pattern = r'\b' + re.escape(english_word) + r'\b'
            translated = re.sub(pattern, hinglish_word, translated, flags=re.IGNORECASE)
        
        return translated
    
    def _format_hindi_response(self, response_data: Dict[str, Any]) -> str:
        """Format response in Hindi"""
        
        response_type = response_data.get('type', 'general')
        
        if response_type == 'crop_recommendation':
            location = response_data.get('location', 'आपका क्षेत्र')
            crops = response_data.get('crops', [])
            
            response = f"🌱 {location} के लिए फसल सुझाव:\n\n"
            
            for i, crop in enumerate(crops[:5], 1):
                crop_name = crop.get('crop', crop.get('name', 'फसल'))
                crop_score = crop.get('score', crop.get('suitability', 0))
                
                # Create clean, simple box for each crop in Hindi
                response += f"┌─────────────────────────────────────┐\n"
                response += f"│ 🌾 {i}. {crop_name}\n"
                response += f"├─────────────────────────────────────┤\n"
                response += f"│ 💰 MSP: ₹{crop.get('msp', 'N/A')}/क्विंटल\n"
                response += f"│ 📈 बाजार मूल्य: ₹{crop.get('market_price', 'N/A')}/क्विंटल\n"
                response += f"│ 💵 अपेक्षित उपज: {crop.get('expected_yield', 'N/A')}\n"
                response += f"│ 🏆 लाभ: {crop.get('profitability', 'N/A')}%\n"
                response += f"│ 📅 बुवाई समय: {crop.get('sowing_time', 'N/A')}\n"
                response += f"└─────────────────────────────────────┘\n\n"
            
            return response
        
        elif response_type == 'market_price':
            crop = response_data.get('crop', 'फसल')
            location = response_data.get('location', 'आपका क्षेत्र')
            price = response_data.get('price', 'जानकारी उपलब्ध नहीं')
            
            return f"💰 {location} में {crop} की कीमत:\n\n🌾 {crop}: {price}\n\n🏛️ सरकारी डेटा:\n• MSP: {response_data.get('msp', 'जानकारी उपलब्ध नहीं')}\n• बाजार कीमत: {price}\n• रुझान: {response_data.get('trend', 'स्थिर')}"
        
        elif response_type == 'weather':
            location = response_data.get('location', 'आपका क्षेत्र')
            temp = response_data.get('temperature', 'जानकारी उपलब्ध नहीं')
            humidity = response_data.get('humidity', 'जानकारी उपलब्ध नहीं')
            condition = response_data.get('condition', 'स्पष्ट')
            
            return f"🌤️ {location} का मौसम:\n\n🌡️ तापमान: {temp}\n💧 नमी: {humidity}\n☁️ स्थिति: {condition}\n\n📅 आज के लिए सुझाव: सुबह 6-8 बजे सिंचाई करें, दोपहर में खेत में काम न करें।"
        
        else:
            return response_data.get('message', 'मैं आपकी कृषि समस्याओं में मदद कर सकता हूं।')
    
    def _format_english_response(self, response_data: Dict[str, Any]) -> str:
        """Format response in English"""
        
        response_type = response_data.get('type', 'general')
        
        if response_type == 'crop_recommendation':
            location = response_data.get('location', 'your area')
            crops = response_data.get('crops', [])
            
            response = f"🌱 Crop recommendations for {location}:\n\n"
            
            for i, crop in enumerate(crops[:5], 1):
                crop_name = crop.get('crop', crop.get('name', 'Unknown Crop'))
                crop_score = crop.get('score', crop.get('suitability', 0))
                
                # Create clean, simple box for each crop
                response += f"┌─────────────────────────────────────┐\n"
                response += f"│ 🌾 {i}. {crop_name}\n"
                response += f"├─────────────────────────────────────┤\n"
                response += f"│ 💰 MSP: ₹{crop.get('msp', 'N/A')}/quintal\n"
                response += f"│ 📈 Market Price: ₹{crop.get('market_price', 'N/A')}/quintal\n"
                response += f"│ 💵 Expected Yield: {crop.get('expected_yield', 'N/A')}\n"
                response += f"│ 🏆 Profit: {crop.get('profitability', 'N/A')}%\n"
                response += f"│ 📅 Sowing Time: {crop.get('sowing_time', 'N/A')}\n"
                response += f"└─────────────────────────────────────┘\n\n"
            
            return response
        
        elif response_type == 'market_price':
            crop = response_data.get('crop', 'crop')
            location = response_data.get('location', 'your area')
            price = response_data.get('price', 'information not available')
            
            return f"💰 {crop} price in {location}:\n\n🌾 {crop}: {price}\n\n🏛️ Government data:\n• MSP: {response_data.get('msp', 'information not available')}\n• Market price: {price}\n• Trend: {response_data.get('trend', 'stable')}"
        
        elif response_type == 'weather':
            location = response_data.get('location', 'your area')
            temp = response_data.get('temperature', 'information not available')
            humidity = response_data.get('humidity', 'information not available')
            condition = response_data.get('condition', 'clear')
            
            return f"🌤️ Weather in {location}:\n\n🌡️ Temperature: {temp}\n💧 Humidity: {humidity}\n☁️ Condition: {condition}\n\n📅 Today's advice: Irrigate between 6-8 AM, avoid field work in afternoon."
        
        else:
            return response_data.get('message', 'I can help you with agricultural problems.')
    
    def _format_hinglish_response(self, response_data: Dict[str, Any]) -> str:
        """Format response in Hinglish"""
        
        response_type = response_data.get('type', 'general')
        
        if response_type == 'crop_recommendation':
            location = response_data.get('location', 'आपका area')
            crops = response_data.get('crops', [])
            
            response = f"🌱 {location} के लिए crop suggestions:\n\n"
            
            for i, crop in enumerate(crops[:3], 1):
                crop_name = crop.get('crop', crop.get('name', 'Unknown Crop'))
                crop_score = crop.get('score', crop.get('suitability', 0))
                response += f"{i}. 🌾 {crop_name} (suggestion: {crop_score}%)\n"
                if 'price' in crop:
                    response += f"   💰 MSP: {crop['price']}\n"
                if 'subsidy' in crop:
                    response += f"   🎁 subsidy: {crop['subsidy']}\n"
                response += "\n"
            
            return response
        
        elif response_type == 'market_price':
            crop = response_data.get('crop', 'crop')
            location = response_data.get('location', 'आपका area')
            price = response_data.get('price', 'जानकारी उपलब्ध नहीं')
            mandi = response_data.get('mandi', f'{location} मंडी')
            change = response_data.get('change', 'स्थिर')
            msp = response_data.get('msp', price)
            trend = response_data.get('trend', 'स्थिर')
            
            return f"💰 {location} में {crop} की बाजार स्थिति:\n\n🏪 मंडी: {mandi}\n🌾 {crop} कीमत: ₹{price}/quintal\n📈 बदलाव: {change}\n\n🏛️ सरकारी डेटा:\n• MSP: ₹{msp}/quintal\n• बाजार कीमत: ₹{price}/quintal\n• रुझान: {trend}\n• मांग स्तर: मध्यम"
        
        elif response_type == 'weather':
            location = response_data.get('location', 'आपका area')
            temp = response_data.get('temperature', 'information नहीं है')
            humidity = response_data.get('humidity', 'information नहीं है')
            condition = response_data.get('condition', 'clear')
            
            return f"🌤️ {location} का weather:\n\n🌡️ Temperature: {temp}\n💧 Humidity: {humidity}\n☁️ Condition: {condition}\n\n📅 आज के लिए advice: सुबह 6-8 बजे irrigation करें, दोपहर में field work न करें।"
        
        else:
            return response_data.get('message', 'मैं आपकी agricultural problems में help कर सकता हूं।')
    
    def get_language_specific_emojis(self, language: str) -> Dict[str, str]:
        """Get language-specific emoji preferences"""
        
        emoji_sets = {
            'hindi': {
                'crop': '🌾', 'price': '💰', 'weather': '🌤️', 'government': '🏛️',
                'fertilizer': '🌱', 'pest': '🐛', 'soil': '🌍', 'irrigation': '💧',
                'success': '✅', 'error': '❌', 'info': 'ℹ️', 'warning': '⚠️'
            },
            'english': {
                'crop': '🌾', 'price': '💰', 'weather': '🌤️', 'government': '🏛️',
                'fertilizer': '🌱', 'pest': '🐛', 'soil': '🌍', 'irrigation': '💧',
                'success': '✅', 'error': '❌', 'info': 'ℹ️', 'warning': '⚠️'
            },
            'hinglish': {
                'crop': '🌾', 'price': '💰', 'weather': '🌤️', 'government': '🏛️',
                'fertilizer': '🌱', 'pest': '🐛', 'soil': '🌍', 'irrigation': '💧',
                'success': '✅', 'error': '❌', 'info': 'ℹ️', 'warning': '⚠️'
            }
        }
        
        return emoji_sets.get(language, emoji_sets['english'])

# Create global instance
enhanced_multilingual = EnhancedMultilingualSupport()
