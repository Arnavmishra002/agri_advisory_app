#!/usr/bin/env python3
"""
Comprehensive Government API Integration
Uses government APIs for farming and other relevant queries
"""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

class ComprehensiveGovernmentAPI:
    """Comprehensive government API integration for various query types"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'KrisiMitra-AI-Assistant/1.0'
        })
        
        # Government API endpoints
        self.api_endpoints = {
            'weather': {
                'imd': 'https://mausam.imd.gov.in/api/weather',
                'openweather': 'https://api.openweathermap.org/data/2.5/weather'
            },
            'agriculture': {
                'agmarknet': 'https://agmarknet.gov.in/api/price',
                'icar': 'https://icar.org.in/api/crop-recommendations',
                'soil_health': 'https://soilhealth.dac.gov.in/api/soil-data'
            },
            'market': {
                'enam': 'https://enam.gov.in/api/market-prices',
                'fcidatacenter': 'https://fcidatacenter.gov.in/api/commodity-prices'
            },
            'government_schemes': {
                'pm_kisan': 'https://pmkisan.gov.in/api/scheme-details',
                'fasal_bima': 'https://pmfby.gov.in/api/scheme-info',
                'soil_health_card': 'https://soilhealth.dac.gov.in/api/scheme-details'
            },
            'general_government': {
                'india_gov': 'https://www.india.gov.in/api/data',
                'census': 'https://censusindia.gov.in/api/population',
                'education': 'https://education.gov.in/api/schemes',
                'health': 'https://mohfw.gov.in/api/health-data'
            }
        }
        
        # API keys (set as environment variables)
        self.api_keys = {
            'openweather': os.getenv('OPENWEATHER_API_KEY', ''),
            'agmarknet': os.getenv('AGMARKNET_API_KEY', ''),
            'enam': os.getenv('ENAM_API_KEY', '')
        }
        
        # Cache for API responses
        self.cache = {}
        self.cache_duration = timedelta(minutes=30)
    
    def get_government_response(self, query: str, language: str = 'en', 
                               query_type: str = 'general', context: Dict = None) -> Dict[str, Any]:
        """Get response using appropriate government APIs based on query type"""
        try:
            query_lower = query.lower().strip()
            
            # Determine which government APIs to use
            if query_type == 'agricultural' or self._is_agricultural_query(query_lower):
                return self._get_agricultural_government_response(query, language, context)
            elif query_type == 'weather' or self._is_weather_query(query_lower):
                return self._get_weather_government_response(query, language, context)
            elif query_type == 'market' or self._is_market_query(query_lower):
                return self._get_market_government_response(query, language, context)
            elif query_type == 'government_schemes' or self._is_government_query(query_lower):
                return self._get_government_schemes_response(query, language, context)
            elif query_type == 'general' or self._is_general_government_query(query_lower):
                return self._get_general_government_response(query, language, context)
            else:
                return self._get_fallback_response(query, language)
                
        except Exception as e:
            logger.error(f"Error in government API response: {e}")
            return self._get_fallback_response(query, language)
    
    def _is_agricultural_query(self, query: str) -> bool:
        """Check if query is agricultural"""
        agri_keywords = [
            'crop', 'फसल', 'farming', 'खेती', 'agriculture', 'कृषि', 'soil', 'मिट्टी',
            'fertilizer', 'उर्वरक', 'irrigation', 'सिंचाई', 'harvest', 'कटाई',
            'sow', 'बोना', 'plant', 'पौधा', 'seed', 'बीज', 'yield', 'उत्पादन',
            'lagayein', 'लगाएं', 'suggest', 'सुझाव', 'recommend', 'अनुशंसा',
            'pest', 'कीट', 'disease', 'रोग', 'weed', 'खरपतवार', 'organic', 'जैविक'
        ]
        return any(keyword in query for keyword in agri_keywords)
    
    def _is_weather_query(self, query: str) -> bool:
        """Check if query is weather-related"""
        weather_keywords = [
            'weather', 'मौसम', 'rain', 'बारिश', 'temperature', 'तापमान',
            'humidity', 'नमी', 'forecast', 'पूर्वानुमान', 'climate', 'जलवायु',
            'hot', 'cold', 'warm', 'cool', 'sunny', 'cloudy', 'storm'
        ]
        return any(keyword in query for keyword in weather_keywords)
    
    def _is_market_query(self, query: str) -> bool:
        """Check if query is market-related"""
        market_keywords = [
            'price', 'कीमत', 'rate', 'दर', 'market', 'बाजार', 'mandi', 'मंडी',
            'cost', 'लागत', 'msp', 'एमएसपी', 'selling', 'बेचना', 'buying', 'खरीदना',
            'stock', 'share', 'investment', 'trading', 'economy'
        ]
        return any(keyword in query for keyword in market_keywords)
    
    def _is_government_query(self, query: str) -> bool:
        """Check if query is about government schemes"""
        gov_keywords = [
            'government', 'सरकार', 'scheme', 'योजना', 'subsidy', 'सब्सिडी',
            'pm kisan', 'policy', 'नीति', 'loan', 'कर्ज', 'credit', 'क्रेडिट',
            'bima', 'बीमा', 'yojana', 'योजना', 'sarkari', 'सरकारी'
        ]
        return any(keyword in query for keyword in gov_keywords)
    
    def _is_general_government_query(self, query: str) -> bool:
        """Check if query can benefit from general government data"""
        general_gov_keywords = [
            'population', 'जनसंख्या', 'census', 'जनगणना', 'education', 'शिक्षा',
            'health', 'स्वास्थ्य', 'hospital', 'अस्पताल', 'school', 'स्कूल',
            'university', 'विश्वविद्यालय', 'college', 'कॉलेज', 'district', 'जिला',
            'state', 'राज्य', 'country', 'देश', 'india', 'भारत'
        ]
        return any(keyword in query for keyword in general_gov_keywords)
    
    def _get_agricultural_government_response(self, query: str, language: str, context: Dict) -> Dict[str, Any]:
        """Get agricultural response using government APIs"""
        try:
            # Try ICAR crop recommendations
            icar_response = self._call_icar_api(query, language, context)
            if icar_response:
                return icar_response
            
            # Try soil health data
            soil_response = self._call_soil_health_api(query, language, context)
            if soil_response:
                return soil_response
            
            # Fallback to general agricultural response
            return self._get_agricultural_fallback(query, language)
            
        except Exception as e:
            logger.error(f"Error in agricultural government response: {e}")
            return self._get_agricultural_fallback(query, language)
    
    def _get_weather_government_response(self, query: str, language: str, context: Dict) -> Dict[str, Any]:
        """Get weather response using government APIs"""
        try:
            # Try IMD weather API
            imd_response = self._call_imd_api(query, language, context)
            if imd_response:
                return imd_response
            
            # Try OpenWeather API as fallback
            openweather_response = self._call_openweather_api(query, language, context)
            if openweather_response:
                return openweather_response
            
            # Fallback response
            return self._get_weather_fallback(query, language)
            
        except Exception as e:
            logger.error(f"Error in weather government response: {e}")
            return self._get_weather_fallback(query, language)
    
    def _get_market_government_response(self, query: str, language: str, context: Dict) -> Dict[str, Any]:
        """Get market response using government APIs"""
        try:
            # Try Agmarknet API
            agmarknet_response = self._call_agmarknet_api(query, language, context)
            if agmarknet_response:
                return agmarknet_response
            
            # Try e-NAM API
            enam_response = self._call_enam_api(query, language, context)
            if enam_response:
                return enam_response
            
            # Try FCI Data Center API
            fci_response = self._call_fci_api(query, language, context)
            if fci_response:
                return fci_response
            
            # Fallback response
            return self._get_market_fallback(query, language)
            
        except Exception as e:
            logger.error(f"Error in market government response: {e}")
            return self._get_market_fallback(query, language)
    
    def _get_government_schemes_response(self, query: str, language: str, context: Dict) -> Dict[str, Any]:
        """Get government schemes response using government APIs"""
        try:
            # Try PM Kisan API
            pm_kisan_response = self._call_pm_kisan_api(query, language, context)
            if pm_kisan_response:
                return pm_kisan_response
            
            # Try Fasal Bima API
            fasal_bima_response = self._call_fasal_bima_api(query, language, context)
            if fasal_bima_response:
                return fasal_bima_response
            
            # Try Soil Health Card API
            soil_health_card_response = self._call_soil_health_card_api(query, language, context)
            if soil_health_card_response:
                return soil_health_card_response
            
            # Fallback response
            return self._get_government_schemes_fallback(query, language)
            
        except Exception as e:
            logger.error(f"Error in government schemes response: {e}")
            return self._get_government_schemes_fallback(query, language)
    
    def _get_general_government_response(self, query: str, language: str, context: Dict) -> Dict[str, Any]:
        """Get general government response using government APIs"""
        try:
            # Try India.gov.in API
            india_gov_response = self._call_india_gov_api(query, language, context)
            if india_gov_response:
                return india_gov_response
            
            # Try Census API
            census_response = self._call_census_api(query, language, context)
            if census_response:
                return census_response
            
            # Try Education API
            education_response = self._call_education_api(query, language, context)
            if education_response:
                return education_response
            
            # Try Health API
            health_response = self._call_health_api(query, language, context)
            if health_response:
                return health_response
            
            # Fallback response
            return self._get_general_government_fallback(query, language)
            
        except Exception as e:
            logger.error(f"Error in general government response: {e}")
            return self._get_general_government_fallback(query, language)
    
    def _call_icar_api(self, query: str, language: str, context: Dict) -> Optional[Dict[str, Any]]:
        """Call ICAR API for crop recommendations"""
        try:
            # Extract location and soil info from context
            location = context.get('location_name', 'Delhi') if context else 'Delhi'
            soil_type = context.get('soil_type', 'Loamy') if context else 'Loamy'
            
            # Prepare API request
            url = self.api_endpoints['agriculture']['icar']
            params = {
                'location': location,
                'soil_type': soil_type,
                'season': 'kharif',
                'language': language
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                recommendations = data.get('recommendations', [])
                
                if recommendations:
                    if language == 'hi':
                        response_text = f"भारतीय कृषि अनुसंधान परिषद (ICAR) के अनुसार {location} में सुझाई गई फसलें:\n\n"
                        for i, rec in enumerate(recommendations[:3], 1):
                            crop = rec.get('crop', 'Unknown')
                            score = rec.get('suitability_score', 0)
                            reason = rec.get('reason', '')
                            response_text += f"{i}. {crop} (उपयुक्तता: {score}%)\n   {reason}\n\n"
                    else:
                        response_text = f"Based on Indian Council of Agricultural Research (ICAR) guidelines for {location}:\n\n"
                        for i, rec in enumerate(recommendations[:3], 1):
                            crop = rec.get('crop', 'Unknown')
                            score = rec.get('suitability_score', 0)
                            reason = rec.get('reason', '')
                            response_text += f"{i}. {crop} (Suitability: {score}%)\n   {reason}\n\n"
                    
                    return {
                        'response': response_text,
                        'source': 'icar_api',
                        'confidence': 0.95,
                        'language': language,
                        'category': 'agricultural',
                        'timestamp': datetime.now().isoformat()
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error calling ICAR API: {e}")
            return None
    
    def _call_imd_api(self, query: str, language: str, context: Dict) -> Optional[Dict[str, Any]]:
        """Call IMD weather API"""
        try:
            location = context.get('location_name', 'Delhi') if context else 'Delhi'
            
            url = self.api_endpoints['weather']['imd']
            params = {
                'location': location,
                'language': language
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                weather_data = data.get('weather', {})
                
                if weather_data:
                    temp = weather_data.get('temperature', 'N/A')
                    humidity = weather_data.get('humidity', 'N/A')
                    condition = weather_data.get('condition', 'N/A')
                    
                    if language == 'hi':
                        response_text = f"{location} का मौसम:\n\n"
                        response_text += f"तापमान: {temp}°C\n"
                        response_text += f"नमी: {humidity}%\n"
                        response_text += f"स्थिति: {condition}\n\n"
                        response_text += "यह डेटा भारतीय मौसम विभाग (IMD) से प्राप्त है।"
                    else:
                        response_text = f"Weather in {location}:\n\n"
                        response_text += f"Temperature: {temp}°C\n"
                        response_text += f"Humidity: {humidity}%\n"
                        response_text += f"Condition: {condition}\n\n"
                        response_text += "This data is from Indian Meteorological Department (IMD)."
                    
                    return {
                        'response': response_text,
                        'source': 'imd_api',
                        'confidence': 0.9,
                        'language': language,
                        'category': 'weather',
                        'timestamp': datetime.now().isoformat()
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error calling IMD API: {e}")
            return None
    
    def _call_agmarknet_api(self, query: str, language: str, context: Dict) -> Optional[Dict[str, Any]]:
        """Call Agmarknet API for market prices"""
        try:
            location = context.get('location_name', 'Delhi') if context else 'Delhi'
            
            url = self.api_endpoints['market']['agmarknet']
            params = {
                'location': location,
                'language': language
            }
            
            if self.api_keys['agmarknet']:
                params['api_key'] = self.api_keys['agmarknet']
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                prices = data.get('prices', [])
                
                if prices:
                    if language == 'hi':
                        response_text = f"{location} में Agmarknet के अनुसार बाजार कीमतें:\n\n"
                        for price in prices[:5]:
                            commodity = price.get('commodity', 'Unknown')
                            rate = price.get('rate', 'N/A')
                            unit = price.get('unit', 'quintal')
                            response_text += f"• {commodity}: ₹{rate}/{unit}\n"
                    else:
                        response_text = f"Market prices in {location} according to Agmarknet:\n\n"
                        for price in prices[:5]:
                            commodity = price.get('commodity', 'Unknown')
                            rate = price.get('rate', 'N/A')
                            unit = price.get('unit', 'quintal')
                            response_text += f"• {commodity}: ₹{rate}/{unit}\n"
                    
                    return {
                        'response': response_text,
                        'source': 'agmarknet_api',
                        'confidence': 0.9,
                        'language': language,
                        'category': 'market',
                        'timestamp': datetime.now().isoformat()
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error calling Agmarknet API: {e}")
            return None
    
    def _call_pm_kisan_api(self, query: str, language: str, context: Dict) -> Optional[Dict[str, Any]]:
        """Call PM Kisan API for scheme information"""
        try:
            url = self.api_endpoints['government_schemes']['pm_kisan']
            params = {
                'language': language
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                scheme_info = data.get('scheme_info', {})
                
                if scheme_info:
                    if language == 'hi':
                        response_text = "पीएम किसान सम्मान निधि योजना:\n\n"
                        response_text += f"लाभ: ₹{scheme_info.get('benefit', '6000')} प्रति वर्ष\n"
                        response_text += f"पात्रता: {scheme_info.get('eligibility', 'सभी किसान')}\n"
                        response_text += f"आवेदन: {scheme_info.get('application_process', 'ऑनलाइन')}\n\n"
                        response_text += "अधिक जानकारी के लिए pmkisan.gov.in पर जाएं।"
                    else:
                        response_text = "PM Kisan Samman Nidhi Scheme:\n\n"
                        response_text += f"Benefit: ₹{scheme_info.get('benefit', '6000')} per year\n"
                        response_text += f"Eligibility: {scheme_info.get('eligibility', 'All farmers')}\n"
                        response_text += f"Application: {scheme_info.get('application_process', 'Online')}\n\n"
                        response_text += "Visit pmkisan.gov.in for more information."
                    
                    return {
                        'response': response_text,
                        'source': 'pm_kisan_api',
                        'confidence': 0.95,
                        'language': language,
                        'category': 'government_schemes',
                        'timestamp': datetime.now().isoformat()
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error calling PM Kisan API: {e}")
            return None
    
    def _call_india_gov_api(self, query: str, language: str, context: Dict) -> Optional[Dict[str, Any]]:
        """Call India.gov.in API for general government data"""
        try:
            url = self.api_endpoints['general_government']['india_gov']
            params = {
                'query': query,
                'language': language
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                gov_data = data.get('data', {})
                
                if gov_data:
                    if language == 'hi':
                        response_text = f"भारत सरकार के आधिकारिक डेटा के अनुसार:\n\n"
                        response_text += f"{gov_data.get('description', 'जानकारी उपलब्ध है')}\n\n"
                        response_text += f"स्रोत: {gov_data.get('source', 'india.gov.in')}"
                    else:
                        response_text = f"According to official Government of India data:\n\n"
                        response_text += f"{gov_data.get('description', 'Information available')}\n\n"
                        response_text += f"Source: {gov_data.get('source', 'india.gov.in')}"
                    
                    return {
                        'response': response_text,
                        'source': 'india_gov_api',
                        'confidence': 0.85,
                        'language': language,
                        'category': 'general_government',
                        'timestamp': datetime.now().isoformat()
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error calling India.gov.in API: {e}")
            return None
    
    # Additional API methods (simplified implementations)
    def _call_soil_health_api(self, query: str, language: str, context: Dict) -> Optional[Dict[str, Any]]:
        """Call soil health API"""
        return None  # Implement as needed
    
    def _call_openweather_api(self, query: str, language: str, context: Dict) -> Optional[Dict[str, Any]]:
        """Call OpenWeather API"""
        return None  # Implement as needed
    
    def _call_enam_api(self, query: str, language: str, context: Dict) -> Optional[Dict[str, Any]]:
        """Call e-NAM API"""
        return None  # Implement as needed
    
    def _call_fci_api(self, query: str, language: str, context: Dict) -> Optional[Dict[str, Any]]:
        """Call FCI API"""
        return None  # Implement as needed
    
    def _call_fasal_bima_api(self, query: str, language: str, context: Dict) -> Optional[Dict[str, Any]]:
        """Call Fasal Bima API"""
        return None  # Implement as needed
    
    def _call_soil_health_card_api(self, query: str, language: str, context: Dict) -> Optional[Dict[str, Any]]:
        """Call Soil Health Card API"""
        return None  # Implement as needed
    
    def _call_census_api(self, query: str, language: str, context: Dict) -> Optional[Dict[str, Any]]:
        """Call Census API"""
        return None  # Implement as needed
    
    def _call_education_api(self, query: str, language: str, context: Dict) -> Optional[Dict[str, Any]]:
        """Call Education API"""
        return None  # Implement as needed
    
    def _call_health_api(self, query: str, language: str, context: Dict) -> Optional[Dict[str, Any]]:
        """Call Health API"""
        return None  # Implement as needed
    
    # Fallback methods
    def _get_agricultural_fallback(self, query: str, language: str) -> Dict[str, Any]:
        """Agricultural fallback response"""
        if language == 'hi':
            response = "कृषि संबंधी जानकारी के लिए मैं आपकी मदद कर सकता हूं। कृपया अपना स्थान और मिट्टी का प्रकार बताएं।"
        else:
            response = "I can help you with agricultural information. Please share your location and soil type."
        
        return {
            'response': response,
            'source': 'agricultural_fallback',
            'confidence': 0.7,
            'language': language,
            'category': 'agricultural',
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_weather_fallback(self, query: str, language: str) -> Dict[str, Any]:
        """Weather fallback response"""
        if language == 'hi':
            response = "मौसम की जानकारी के लिए कृपया अपना स्थान बताएं।"
        else:
            response = "Please share your location for weather information."
        
        return {
            'response': response,
            'source': 'weather_fallback',
            'confidence': 0.7,
            'language': language,
            'category': 'weather',
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_market_fallback(self, query: str, language: str) -> Dict[str, Any]:
        """Market fallback response"""
        if language == 'hi':
            response = "बाजार कीमतों के लिए कृपया अपना स्थान और फसल का नाम बताएं।"
        else:
            response = "Please share your location and crop name for market prices."
        
        return {
            'response': response,
            'source': 'market_fallback',
            'confidence': 0.7,
            'language': language,
            'category': 'market',
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_government_schemes_fallback(self, query: str, language: str) -> Dict[str, Any]:
        """Government schemes fallback response"""
        if language == 'hi':
            response = "सरकारी योजनाओं के बारे में जानकारी के लिए मैं आपकी मदद कर सकता हूं।"
        else:
            response = "I can help you with information about government schemes."
        
        return {
            'response': response,
            'source': 'government_schemes_fallback',
            'confidence': 0.7,
            'language': language,
            'category': 'government_schemes',
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_general_government_fallback(self, query: str, language: str) -> Dict[str, Any]:
        """General government fallback response"""
        if language == 'hi':
            response = "सरकारी जानकारी के लिए मैं आपकी मदद कर सकता हूं।"
        else:
            response = "I can help you with government information."
        
        return {
            'response': response,
            'source': 'general_government_fallback',
            'confidence': 0.7,
            'language': language,
            'category': 'general_government',
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_fallback_response(self, query: str, language: str) -> Dict[str, Any]:
        """Ultimate fallback response"""
        if language == 'hi':
            response = "क्षमा करें, सरकारी API से जानकारी प्राप्त नहीं हो सकी। कृपया फिर से प्रयास करें।"
        else:
            response = "Sorry, couldn't retrieve information from government APIs. Please try again."
        
        return {
            'response': response,
            'source': 'error_fallback',
            'confidence': 0.3,
            'language': language,
            'category': 'error',
            'timestamp': datetime.now().isoformat()
        }
    
    def get_real_market_prices(self, commodity: str = 'wheat', latitude: float = None, longitude: float = None) -> List[Dict[str, Any]]:
        """Get real-time market prices with government data"""
        try:
            # Use the enhanced government API for market prices
            from ..services.enhanced_government_api import EnhancedGovernmentAPI
            enhanced_api = EnhancedGovernmentAPI()
            return enhanced_api.get_real_market_prices(commodity, latitude=latitude, longitude=longitude)
        except Exception as e:
            logger.error(f"Error getting market prices: {e}")
            return []

# Create global instance
comprehensive_government_api = ComprehensiveGovernmentAPI()

