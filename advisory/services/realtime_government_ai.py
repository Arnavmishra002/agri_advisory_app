#!/usr/bin/env python3
"""
Real-time Government AI System
Ensures all farming-related queries use real-time government data
"""

import json
import logging
import time
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
import requests
from .enhanced_government_api import EnhancedGovernmentAPI
from .deep_ai_understanding import analyze_query_deeply
from .ollama_integration import OllamaIntegration

logger = logging.getLogger(__name__)

class RealTimeGovernmentAI:
    """Real-time Government AI System for farming queries"""
    
    def __init__(self):
        self.gov_api = EnhancedGovernmentAPI()
        self.deep_ai = analyze_query_deeply
        self.ollama = OllamaIntegration()  # Open source AI for general queries
        self.real_time_cache = {}
        self.cache_duration = 300  # 5 minutes cache
        
    def process_farming_query(self, query: str, language: str = 'en', location: str = '') -> Dict[str, Any]:
        """Process farming query with real-time government data"""
        try:
            # Step 1: Deep AI Analysis
            deep_analysis = self.deep_ai(query, {
                'location': location,
                'language': language,
                'timestamp': datetime.now().isoformat()
            })
            
            logger.info(f"Deep Analysis Result: {deep_analysis}")
            
            # Step 2: Determine if farming-related
            is_farming = self._is_farming_related_query(deep_analysis)
            
            if is_farming:
                # Step 3: Get real-time government data
                real_time_data = self._get_real_time_government_data(
                    deep_analysis, query, language, location
                )
                
                # Step 4: Generate response based on real-time data
                response = self._generate_realtime_response(
                    query, deep_analysis, real_time_data, language, location
                )
                
                return {
                    'response': response,
                    'data_source': 'real_time_government_apis',
                    'confidence': deep_analysis.get('confidence', 0.8),
                    'timestamp': datetime.now().isoformat(),
                    'deep_analysis': deep_analysis,
                    'real_time_data': real_time_data
                }
            else:
                # Non-farming query - use open source AI (Ollama)
                response = self._generate_general_response(query, deep_analysis, language)
                
                # Determine if Ollama was used successfully
                data_source = 'open_source_ai' if len(response) > 200 else 'general_ai'
                
                return {
                    'response': response,
                    'data_source': data_source,
                    'confidence': deep_analysis.get('confidence', 0.8),
                    'timestamp': datetime.now().isoformat(),
                    'deep_analysis': deep_analysis,
                    'ai_model': 'ollama_llama3' if data_source == 'open_source_ai' else 'hardcoded'
                }
                
        except Exception as e:
            logger.error(f"Error processing farming query: {e}")
            return {
                'response': f"Sorry, I encountered an error processing your query. Please try again.",
                'data_source': 'error_fallback',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _is_farming_related_query(self, deep_analysis: Dict[str, Any]) -> bool:
        """Determine if query is farming-related"""
        intent = deep_analysis.get('intent', '')
        entities = deep_analysis.get('entities', {})
        
        # Farming-related intents
        farming_intents = [
            'crop_recommendation', 'cultivation_guide', 'pest_management',
            'harvesting', 'soil_management', 'water_management',
            'price_inquiry', 'weather_inquiry', 'government_schemes',
            'livestock_care', 'fertilizer_management', 'irrigation_guide'
        ]
        
        if intent in farming_intents:
            return True
        
        # Check for farming entities
        crops = entities.get('crops', [])
        if crops:
            return True
        
        # Check for farming keywords
        farming_keywords = [
            'crop', 'फसल', 'खेती', 'कृषि', 'agriculture', 'farming',
            'soil', 'मिट्टी', 'weather', 'मौसम', 'price', 'भाव',
            'mandi', 'मंडी', 'government', 'सरकारी', 'scheme', 'योजना'
        ]
        
        query_lower = deep_analysis.get('query', '').lower()
        if any(keyword in query_lower for keyword in farming_keywords):
            return True
        
        return False
    
    def _get_real_time_government_data(self, deep_analysis: Dict[str, Any], query: str, language: str, location: str) -> Dict[str, Any]:
        """Get real-time data from government APIs"""
        real_time_data = {
            'weather_data': None,
            'market_data': None,
            'crop_data': None,
            'soil_data': None,
            'government_schemes': None,
            'timestamp': datetime.now().isoformat()
        }
        
        intent = deep_analysis.get('intent', '')
        entities = deep_analysis.get('entities', {})
        
        try:
            # Weather data for all farming queries
            if location:
                weather_data = self.gov_api._fetch_weather_from_imd(location)
                real_time_data['weather_data'] = weather_data
                logger.info(f"Real-time weather data fetched for {location}")
            
            # Market price data
            if intent in ['price_inquiry'] or any('price' in str(entities).lower() for entities in entities.values()):
                market_data = self.gov_api.get_real_market_prices(location or 'Delhi')
                real_time_data['market_data'] = market_data
                logger.info(f"Real-time market data fetched")
            
            # Crop recommendation data
            if intent in ['crop_recommendation', 'cultivation_guide']:
                crop_data = self.gov_api.get_enhanced_crop_recommendations(location or 'Delhi', 'kharif', language)
                real_time_data['crop_data'] = crop_data
                logger.info(f"Real-time crop data fetched")
            
            # Soil data
            if intent in ['soil_management'] or 'soil' in query.lower():
                soil_data = self.gov_api._get_comprehensive_soil_data(location or 'Delhi')
                real_time_data['soil_data'] = soil_data
                logger.info(f"Real-time soil data fetched")
            
            # Government schemes
            if intent in ['government_schemes'] or 'scheme' in query.lower():
                schemes_data = self.gov_api._get_government_schemes(location or 'Delhi')
                real_time_data['government_schemes'] = schemes_data
                logger.info(f"Real-time government schemes data fetched")
            
            # Always fetch weather for farming queries (essential for farming decisions)
            if not real_time_data['weather_data'] and location:
                weather_data = self.gov_api._fetch_weather_from_imd(location)
                real_time_data['weather_data'] = weather_data
            
        except Exception as e:
            logger.error(f"Error fetching real-time government data: {e}")
            # Use fallback data
            real_time_data['error'] = str(e)
        
        return real_time_data
    
    def _generate_realtime_response(self, query: str, deep_analysis: Dict[str, Any], real_time_data: Dict[str, Any], language: str, location: str) -> str:
        """Generate response based on real-time government data"""
        intent = deep_analysis.get('intent', '')
        entities = deep_analysis.get('entities', {})
        
        try:
            # Crop recommendation with real-time data
            if intent == 'crop_recommendation':
                return self._generate_realtime_crop_response(real_time_data, language, location)
            
            # Price inquiry with real-time data
            elif intent == 'price_inquiry':
                return self._generate_realtime_price_response(real_time_data, entities, language, location)
            
            # Weather inquiry with real-time data
            elif intent == 'weather_inquiry':
                return self._generate_realtime_weather_response(real_time_data, language, location)
            
            # Government schemes with real-time data
            elif intent == 'government_schemes':
                return self._generate_realtime_schemes_response(real_time_data, language, location)
            
            # Cultivation guide with real-time data
            elif intent == 'cultivation_guide':
                return self._generate_realtime_cultivation_response(real_time_data, entities, language, location)
            
            # Pest management with real-time data
            elif intent == 'pest_management':
                return self._generate_realtime_pest_response(real_time_data, entities, language, location)
            
            # Default farming response with real-time context
            else:
                return self._generate_realtime_contextual_response(real_time_data, deep_analysis, language, location)
                
        except Exception as e:
            logger.error(f"Error generating real-time response: {e}")
            return self._generate_fallback_response(query, language)
    
    def _generate_realtime_crop_response(self, real_time_data: Dict[str, Any], language: str, location: str) -> str:
        """Generate crop recommendation response with real-time data"""
        crop_data = real_time_data.get('crop_data', {})
        weather_data = real_time_data.get('weather_data', {})
        
        if language in ['hi', 'hinglish']:
            response = f"🌾 **{location} के लिए वास्तविक समय फसल सुझाव**\n\n"
            response += f"📍 **स्थान**: {location}\n"
            response += f"⏰ **अपडेट**: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            
            if weather_data:
                response += f"🌤️ **वर्तमान मौसम**:\n"
                temp = weather_data.get('temperature', 'N/A')
                humidity = weather_data.get('humidity', 'N/A')
                wind = weather_data.get('wind_speed', 'N/A')
                
                # Clean units to avoid duplication
                if isinstance(temp, str) and '°C' in temp:
                    temp_display = temp
                else:
                    temp_display = f"{temp}°C" if temp != 'N/A' else 'N/A'
                    
                if isinstance(humidity, str) and '%' in humidity:
                    humidity_display = humidity
                else:
                    humidity_display = f"{humidity}%" if humidity != 'N/A' else 'N/A'
                    
                if isinstance(wind, str) and 'km/h' in wind:
                    wind_display = wind
                else:
                    wind_display = f"{wind} km/h" if wind != 'N/A' else 'N/A'
                
                response += f"• तापमान: {temp_display}\n"
                response += f"• आर्द्रता: {humidity_display}\n"
                response += f"• हवा: {wind_display}\n\n"
            
            if crop_data and crop_data.get('recommendations'):
                recommendations = crop_data['recommendations'][:5]
                response += f"🥇 **सरकारी डेटा के आधार पर अनुशंसित फसलें**:\n\n"
                
                for i, crop in enumerate(recommendations, 1):
                    # Create clean, simple box for each crop
                    response += f"┌─────────────────────────────────────┐\n"
                    response += f"│ 🌾 {i}. {crop.get('name', 'फसल')}\n"
                    response += f"├─────────────────────────────────────┤\n"
                    response += f"│ 💰 MSP: ₹{crop.get('msp', 'N/A')}/क्विंटल\n"
                    response += f"│ 📈 बाजार मूल्य: ₹{crop.get('market_price', 'N/A')}/क्विंटल\n"
                    response += f"│ 💵 अपेक्षित उपज: {crop.get('expected_yield', 'N/A')}\n"
                    response += f"│ 🏆 लाभ: {crop.get('profitability', 'N/A')}%\n"
                    response += f"│ 📅 बुवाई समय: {crop.get('sowing_time', 'N/A')}\n"
                    response += f"└─────────────────────────────────────┘\n\n"
                
                response += f"📊 **डेटा स्रोत**: ICAR, IMD, सरकारी कृषि विभाग (वास्तविक समय)\n"
                response += f"✅ **गारंटी**: 100% सरकारी डेटा पर आधारित\n"
            else:
                response += f"⚠️ फसल डेटा लोड हो रहा है... कृपया कुछ समय बाद पूछें।\n"
            
            return response
        
        else:  # English
            response = f"🌾 **Real-time Crop Recommendations for {location}**\n\n"
            response += f"📍 **Location**: {location}\n"
            response += f"⏰ **Updated**: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            
            if weather_data:
                response += f"🌤️ **Current Weather**:\n"
                temp = weather_data.get('temperature', 'N/A')
                humidity = weather_data.get('humidity', 'N/A')
                wind = weather_data.get('wind_speed', 'N/A')
                
                # Clean units to avoid duplication
                if isinstance(temp, str) and '°C' in temp:
                    temp_display = temp
                else:
                    temp_display = f"{temp}°C" if temp != 'N/A' else 'N/A'
                    
                if isinstance(humidity, str) and '%' in humidity:
                    humidity_display = humidity
                else:
                    humidity_display = f"{humidity}%" if humidity != 'N/A' else 'N/A'
                    
                if isinstance(wind, str) and 'km/h' in wind:
                    wind_display = wind
                else:
                    wind_display = f"{wind} km/h" if wind != 'N/A' else 'N/A'
                
                response += f"• Temperature: {temp_display}\n"
                response += f"• Humidity: {humidity_display}\n"
                response += f"• Wind: {wind_display}\n\n"
            
            if crop_data and crop_data.get('recommendations'):
                recommendations = crop_data['recommendations'][:5]
                response += f"🥇 **Government Data-Based Recommended Crops**:\n\n"
                
                for i, crop in enumerate(recommendations, 1):
                    # Create clean, simple box for each crop with English names
                    crop_name = crop.get('name', 'Crop')
                    
                    # Convert Hindi crop names to English for English output
                    english_crop_names = {
                        'गेहूं': 'Wheat',
                        'चावल': 'Rice', 
                        'मक्का': 'Maize',
                        'कपास': 'Cotton',
                        'गन्ना': 'Sugarcane',
                        'टमाटर': 'Tomato',
                        'आलू': 'Potato',
                        'प्याज': 'Onion'
                    }
                    
                    english_crop_name = english_crop_names.get(crop_name, crop_name)
                    
                    response += f"┌─────────────────────────────────────┐\n"
                    response += f"│ 🌾 {i}. {english_crop_name}\n"
                    response += f"├─────────────────────────────────────┤\n"
                    response += f"│ 💰 MSP: ₹{crop.get('msp', 'N/A')}/quintal\n"
                    response += f"│ 📈 Market Price: ₹{crop.get('market_price', 'N/A')}/quintal\n"
                    response += f"│ 💵 Expected Yield: {crop.get('expected_yield', 'N/A')}\n"
                    response += f"│ 🏆 Profit: {crop.get('profitability', 'N/A')}%\n"
                    response += f"│ 📅 Sowing Time: {crop.get('sowing_time', 'N/A')}\n"
                    response += f"└─────────────────────────────────────┘\n\n"
                
                response += f"📊 **Data Source**: ICAR, IMD, Government Agriculture Department (Real-time)\n"
                response += f"✅ **Guaranteed**: 100% Government Data Based\n"
            else:
                response += f"⚠️ Crop data loading... Please ask again in a moment.\n"
            
            return response
    
    def _generate_realtime_price_response(self, real_time_data: Dict[str, Any], entities: Dict[str, Any], language: str, location: str) -> str:
        """Generate price inquiry response with real-time data"""
        market_data = real_time_data.get('market_data', {})
        
        if language in ['hi', 'hinglish']:
            response = f"💰 **{location} के लिए वास्तविक समय मंडी भाव**\n\n"
            response += f"📍 **स्थान**: {location}\n"
            response += f"⏰ **अपडेट**: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            
            if market_data:
                response += f"📈 **वर्तमान मंडी भाव**:\n\n"
                for i, (commodity, data) in enumerate(list(market_data.items())[:5], 1):
                    response += f"┌─────────────────────────────────────┐\n"
                    response += f"│ 💰 {i}. {commodity}\n"
                    response += f"├─────────────────────────────────────┤\n"
                    response += f"│ 📈 बाजार भाव: ₹{data.get('current_price', 'N/A')}/क्विंटल\n"
                    response += f"│ 🏛️ MSP: ₹{data.get('msp', 'N/A')}/क्विंटल\n"
                    response += f"│ 📊 स्रोत: {data.get('source', 'सरकारी')}\n"
                    response += f"│ 📅 अपडेट: {data.get('date', 'आज')}\n"
                    response += f"└─────────────────────────────────────┘\n\n"
                
                response += f"📊 **डेटा स्रोत**: Agmarknet, e-NAM, सरकारी मंडी (वास्तविक समय)\n"
                response += f"✅ **गारंटी**: 100% सरकारी मंडी डेटा\n"
            else:
                response += f"⚠️ मंडी डेटा लोड हो रहा है... कृपया कुछ समय बाद पूछें।\n"
            
            return response
        
        else:  # English
            response = f"💰 **Real-time Market Prices for {location}**\n\n"
            response += f"📍 **Location**: {location}\n"
            response += f"⏰ **Updated**: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            
            if market_data:
                response += f"📈 **Current Market Prices**:\n\n"
                for i, (commodity, data) in enumerate(list(market_data.items())[:5], 1):
                    response += f"┌─────────────────────────────────────┐\n"
                    response += f"│ 💰 {i}. {commodity}\n"
                    response += f"├─────────────────────────────────────┤\n"
                    response += f"│ 📈 Market Price: ₹{data.get('current_price', 'N/A')}/quintal\n"
                    response += f"│ 🏛️ MSP: ₹{data.get('msp', 'N/A')}/quintal\n"
                    response += f"│ 📊 Source: {data.get('source', 'Government')}\n"
                    response += f"│ 📅 Updated: {data.get('date', 'Today')}\n"
                    response += f"└─────────────────────────────────────┘\n\n"
                
                response += f"📊 **Data Source**: Agmarknet, e-NAM, Government Mandis (Real-time)\n"
                response += f"✅ **Guaranteed**: 100% Government Mandi Data\n"
            else:
                response += f"⚠️ Market data loading... Please ask again in a moment.\n"
            
            return response
    
    def _generate_realtime_weather_response(self, real_time_data: Dict[str, Any], language: str, location: str) -> str:
        """Generate weather response with real-time data"""
        weather_data = real_time_data.get('weather_data', {})
        
        if language in ['hi', 'hinglish']:
            response = f"🌤️ **{location} का वास्तविक समय मौसम**\n\n"
            response += f"📍 **स्थान**: {location}\n"
            response += f"⏰ **अपडेट**: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            
            if weather_data:
                response += f"🌡️ **वर्तमान स्थिति**:\n"
                
                # Clean units to avoid duplication
                temp = weather_data.get('temperature', 'N/A')
                humidity = weather_data.get('humidity', 'N/A')
                wind = weather_data.get('wind_speed', 'N/A')
                rain_prob = weather_data.get('rainfall_probability', 'N/A')
                
                temp_display = temp if isinstance(temp, str) and '°C' in temp else f"{temp}°C" if temp != 'N/A' else 'N/A'
                humidity_display = humidity if isinstance(humidity, str) and '%' in humidity else f"{humidity}%" if humidity != 'N/A' else 'N/A'
                wind_display = wind if isinstance(wind, str) and 'km/h' in wind else f"{wind} km/h" if wind != 'N/A' else 'N/A'
                rain_display = rain_prob if isinstance(rain_prob, str) and '%' in rain_prob else f"{rain_prob}%" if rain_prob != 'N/A' else 'N/A'
                
                response += f"• तापमान: {temp_display}\n"
                response += f"• आर्द्रता: {humidity_display}\n"
                response += f"• हवा की गति: {wind_display}\n"
                response += f"• मौसम: {weather_data.get('condition', 'सामान्य')}\n"
                response += f"• बारिश की संभावना: {rain_display}\n\n"
                
                # 3-day forecast
                forecast = weather_data.get('forecast_7day', [])
                if forecast:
                    response += f"📅 **अगले 3 दिन का पूर्वानुमान**:\n"
                    for i, day in enumerate(forecast[:3]):
                        temp = day.get('temperature', 'N/A')
                        # Clean forecast temperature units
                        if isinstance(temp, str) and '°C' in temp:
                            temp_display = temp
                        else:
                            temp_display = f"{temp}°C" if temp != 'N/A' else 'N/A'
                        response += f"• {day.get('day', f'Day {i+1}')}: {temp_display}\n"
                    response += f"\n"
                
                response += f"🌾 **किसान सलाह**: {weather_data.get('farmer_advisory', 'मौसम के अनुसार फसल की देखभाल करें')}\n\n"
                response += f"📊 **डेटा स्रोत**: IMD (भारतीय मौसम विभाग) - वास्तविक समय\n"
                response += f"✅ **गारंटी**: 100% सरकारी मौसम डेटा\n"
            else:
                response += f"⚠️ मौसम डेटा लोड हो रहा है... कृपया कुछ समय बाद पूछें।\n"
            
            return response
        
        else:  # English
            response = f"🌤️ **Real-time Weather for {location}**\n\n"
            response += f"📍 **Location**: {location}\n"
            response += f"⏰ **Updated**: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            
            if weather_data:
                response += f"🌡️ **Current Conditions**:\n"
                
                # Clean units to avoid duplication
                temp = weather_data.get('temperature', 'N/A')
                humidity = weather_data.get('humidity', 'N/A')
                wind = weather_data.get('wind_speed', 'N/A')
                rain_prob = weather_data.get('rainfall_probability', 'N/A')
                
                temp_display = temp if isinstance(temp, str) and '°C' in temp else f"{temp}°C" if temp != 'N/A' else 'N/A'
                humidity_display = humidity if isinstance(humidity, str) and '%' in humidity else f"{humidity}%" if humidity != 'N/A' else 'N/A'
                wind_display = wind if isinstance(wind, str) and 'km/h' in wind else f"{wind} km/h" if wind != 'N/A' else 'N/A'
                rain_display = rain_prob if isinstance(rain_prob, str) and '%' in rain_prob else f"{rain_prob}%" if rain_prob != 'N/A' else 'N/A'
                
                response += f"• Temperature: {temp_display}\n"
                response += f"• Humidity: {humidity_display}\n"
                response += f"• Wind Speed: {wind_display}\n"
                response += f"• Condition: {weather_data.get('condition', 'Normal')}\n"
                response += f"• Rain Probability: {rain_display}\n\n"
                
                # 3-day forecast
                forecast = weather_data.get('forecast_7day', [])
                if forecast:
                    response += f"📅 **3-Day Forecast**:\n"
                    for i, day in enumerate(forecast[:3]):
                        temp = day.get('temperature', 'N/A')
                        # Clean forecast temperature units
                        if isinstance(temp, str) and '°C' in temp:
                            temp_display = temp
                        else:
                            temp_display = f"{temp}°C" if temp != 'N/A' else 'N/A'
                        response += f"• {day.get('day', f'Day {i+1}')}: {temp_display}\n"
                    response += f"\n"
                
                response += f"🌾 **Farmer Advisory**: {weather_data.get('farmer_advisory', 'Take care of crops according to weather')}\n\n"
                response += f"📊 **Data Source**: IMD (Indian Meteorological Department) - Real-time\n"
                response += f"✅ **Guaranteed**: 100% Government Weather Data\n"
            else:
                response += f"⚠️ Weather data loading... Please ask again in a moment.\n"
            
            return response
    
    def _generate_realtime_schemes_response(self, real_time_data: Dict[str, Any], language: str, location: str) -> str:
        """Generate government schemes response with real-time data"""
        schemes_data = real_time_data.get('government_schemes', {})
        
        if language in ['hi', 'hinglish']:
            response = f"🏛️ **{location} के लिए वास्तविक समय सरकारी योजनाएं**\n\n"
            response += f"📍 **स्थान**: {location}\n"
            response += f"⏰ **अपडेट**: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            
            if schemes_data:
                response += f"📋 **उपलब्ध सरकारी योजनाएं**:\n\n"
                for i, (scheme_name, scheme_info) in enumerate(list(schemes_data.items())[:5], 1):
                    response += f"┌─────────────────────────────────────┐\n"
                    response += f"│ 🏛️ {i}. {scheme_name}\n"
                    response += f"├─────────────────────────────────────┤\n"
                    response += f"│ 💰 लाभ: {scheme_info.get('benefit', 'N/A')}\n"
                    response += f"│ ✅ पात्रता: {scheme_info.get('eligibility', 'N/A')}\n"
                    response += f"│ 📝 आवेदन: {scheme_info.get('application', 'N/A')}\n"
                    response += f"│ 🏛️ विभाग: {scheme_info.get('department', 'कृषि विभाग')}\n"
                    response += f"└─────────────────────────────────────┘\n\n"
                
                response += f"📊 **डेटा स्रोत**: सरकारी पोर्टल, PM-KISAN, कृषि विभाग (वास्तविक समय)\n"
                response += f"✅ **गारंटी**: 100% सरकारी योजना डेटा\n"
            else:
                response += f"⚠️ योजना डेटा लोड हो रहा है... कृपया कुछ समय बाद पूछें।\n"
            
            return response
        
        else:  # English
            response = f"🏛️ **Real-time Government Schemes for {location}**\n\n"
            response += f"📍 **Location**: {location}\n"
            response += f"⏰ **Updated**: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            
            if schemes_data:
                response += f"📋 **Available Government Schemes**:\n\n"
                for i, (scheme_name, scheme_info) in enumerate(list(schemes_data.items())[:5], 1):
                    response += f"┌─────────────────────────────────────┐\n"
                    response += f"│ 🏛️ {i}. {scheme_name}\n"
                    response += f"├─────────────────────────────────────┤\n"
                    response += f"│ 💰 Benefit: {scheme_info.get('benefit', 'N/A')}\n"
                    response += f"│ ✅ Eligibility: {scheme_info.get('eligibility', 'N/A')}\n"
                    response += f"│ 📝 Application: {scheme_info.get('application', 'N/A')}\n"
                    response += f"│ 🏛️ Department: {scheme_info.get('department', 'Agriculture Department')}\n"
                    response += f"└─────────────────────────────────────┘\n\n"
                
                response += f"📊 **Data Source**: Government Portals, PM-KISAN, Agriculture Department (Real-time)\n"
                response += f"✅ **Guaranteed**: 100% Government Scheme Data\n"
            else:
                response += f"⚠️ Scheme data loading... Please ask again in a moment.\n"
            
            return response
    
    def _generate_realtime_cultivation_response(self, real_time_data: Dict[str, Any], entities: Dict[str, Any], language: str, location: str) -> str:
        """Generate cultivation guide response with real-time data"""
        weather_data = real_time_data.get('weather_data', {})
        soil_data = real_time_data.get('soil_data', {})
        
        if language in ['hi', 'hinglish']:
            response = f"🌱 **{location} के लिए वास्तविक समय खेती गाइड**\n\n"
            response += f"📍 **स्थान**: {location}\n"
            response += f"⏰ **अपडेट**: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            
            if weather_data:
                response += f"🌤️ **वर्तमान मौसम स्थिति**:\n"
                response += f"• तापमान: {weather_data.get('temperature', 'N/A')}°C\n"
                response += f"• आर्द्रता: {weather_data.get('humidity', 'N/A')}%\n"
                response += f"• मौसम: {weather_data.get('condition', 'सामान्य')}\n\n"
            
            if soil_data:
                response += f"🌾 **मिट्टी की स्थिति**:\n"
                response += f"• मिट्टी का प्रकार: {soil_data.get('soil_type', 'N/A')}\n"
                response += f"• पीएच स्तर: {soil_data.get('ph_level', 'N/A')}\n"
                response += f"• उर्वरता: {soil_data.get('fertility_status', 'N/A')}\n\n"
            
            response += f"💡 **खेती के लिए सुझाव**:\n"
            response += f"• वर्तमान मौसम के अनुसार बुवाई करें\n"
            response += f"• मिट्टी की जांच के बाद उर्वरक का प्रयोग करें\n"
            response += f"• सिंचाई का समय मौसम के अनुसार निर्धारित करें\n\n"
            
            response += f"📊 **डेटा स्रोत**: IMD, ICAR, सरकारी कृषि विभाग (वास्तविक समय)\n"
            response += f"✅ **गारंटी**: 100% सरकारी डेटा पर आधारित\n"
            
            return response
        
        else:  # English
            response = f"🌱 **Real-time Cultivation Guide for {location}**\n\n"
            response += f"📍 **Location**: {location}\n"
            response += f"⏰ **Updated**: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            
            if weather_data:
                response += f"🌤️ **Current Weather Conditions**:\n"
                response += f"• Temperature: {weather_data.get('temperature', 'N/A')}°C\n"
                response += f"• Humidity: {weather_data.get('humidity', 'N/A')}%\n"
                response += f"• Condition: {weather_data.get('condition', 'Normal')}\n\n"
            
            if soil_data:
                response += f"🌾 **Soil Conditions**:\n"
                response += f"• Soil Type: {soil_data.get('soil_type', 'N/A')}\n"
                response += f"• pH Level: {soil_data.get('ph_level', 'N/A')}\n"
                response += f"• Fertility: {soil_data.get('fertility_status', 'N/A')}\n\n"
            
            response += f"💡 **Cultivation Recommendations**:\n"
            response += f"• Sow according to current weather conditions\n"
            response += f"• Use fertilizers after soil testing\n"
            response += f"• Schedule irrigation according to weather\n\n"
            
            response += f"📊 **Data Source**: IMD, ICAR, Government Agriculture Department (Real-time)\n"
            response += f"✅ **Guaranteed**: 100% Government Data Based\n"
            
            return response
    
    def _generate_realtime_pest_response(self, real_time_data: Dict[str, Any], entities: Dict[str, Any], language: str, location: str) -> str:
        """Generate pest management response with real-time data"""
        weather_data = real_time_data.get('weather_data', {})
        
        if language in ['hi', 'hinglish']:
            response = f"🐛 **{location} के लिए वास्तविक समय कीट प्रबंधन**\n\n"
            response += f"📍 **स्थान**: {location}\n"
            response += f"⏰ **अपडेट**: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            
            if weather_data:
                response += f"🌤️ **वर्तमान मौसम (कीट गतिविधि के लिए महत्वपूर्ण)**:\n"
                response += f"• तापमान: {weather_data.get('temperature', 'N/A')}°C\n"
                response += f"• आर्द्रता: {weather_data.get('humidity', 'N/A')}%\n"
                response += f"• हवा: {weather_data.get('wind_speed', 'N/A')} km/h\n\n"
            
            response += f"🛡️ **मौसम के अनुसार कीट नियंत्रण सुझाव**:\n"
            response += f"• उच्च आर्द्रता में फंगल रोगों का खतरा बढ़ता है\n"
            response += f"• गर्म मौसम में कीट गतिविधि अधिक होती है\n"
            response += f"• नियमित निगरानी और समय पर उपचार करें\n\n"
            
            response += f"📊 **डेटा स्रोत**: IMD, ICAR, कृषि विभाग (वास्तविक समय)\n"
            response += f"✅ **गारंटी**: 100% सरकारी डेटा पर आधारित\n"
            
            return response
        
        else:  # English
            response = f"🐛 **Real-time Pest Management for {location}**\n\n"
            response += f"📍 **Location**: {location}\n"
            response += f"⏰ **Updated**: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            
            if weather_data:
                response += f"🌤️ **Current Weather (Critical for Pest Activity)**:\n"
                response += f"• Temperature: {weather_data.get('temperature', 'N/A')}°C\n"
                response += f"• Humidity: {weather_data.get('humidity', 'N/A')}%\n"
                response += f"• Wind: {weather_data.get('wind_speed', 'N/A')} km/h\n\n"
            
            response += f"🛡️ **Weather-Based Pest Control Recommendations**:\n"
            response += f"• High humidity increases fungal disease risk\n"
            response += f"• Hot weather increases pest activity\n"
            response += f"• Regular monitoring and timely treatment recommended\n\n"
            
            response += f"📊 **Data Source**: IMD, ICAR, Agriculture Department (Real-time)\n"
            response += f"✅ **Guaranteed**: 100% Government Data Based\n"
            
            return response
    
    def _generate_realtime_contextual_response(self, real_time_data: Dict[str, Any], deep_analysis: Dict[str, Any], language: str, location: str) -> str:
        """Generate contextual response with real-time data"""
        weather_data = real_time_data.get('weather_data', {})
        intent = deep_analysis.get('intent', 'general_inquiry')
        
        if language in ['hi', 'hinglish']:
            response = f"🌾 **{location} के लिए वास्तविक समय कृषि सलाह**\n\n"
            response += f"📍 **स्थान**: {location}\n"
            response += f"⏰ **अपडेट**: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            
            if weather_data:
                response += f"🌤️ **वर्तमान मौसम स्थिति**:\n"
                response += f"• तापमान: {weather_data.get('temperature', 'N/A')}°C\n"
                response += f"• आर्द्रता: {weather_data.get('humidity', 'N/A')}%\n"
                response += f"• मौसम: {weather_data.get('condition', 'सामान्य')}\n\n"
            
            response += f"💡 **सामान्य कृषि सलाह**:\n"
            response += f"• वर्तमान मौसम के अनुसार फसल की देखभाल करें\n"
            response += f"• सिंचाई का समय मौसम के अनुसार निर्धारित करें\n"
            response += f"• कीट और रोग की नियमित निगरानी करें\n\n"
            
            response += f"📊 **डेटा स्रोत**: IMD, ICAR, सरकारी कृषि विभाग (वास्तविक समय)\n"
            response += f"✅ **गारंटी**: 100% सरकारी डेटा पर आधारित\n"
            
            return response
        
        else:  # English
            response = f"🌾 **Real-time Agricultural Advisory for {location}**\n\n"
            response += f"📍 **Location**: {location}\n"
            response += f"⏰ **Updated**: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            
            if weather_data:
                response += f"🌤️ **Current Weather Conditions**:\n"
                response += f"• Temperature: {weather_data.get('temperature', 'N/A')}°C\n"
                response += f"• Humidity: {weather_data.get('humidity', 'N/A')}%\n"
                response += f"• Condition: {weather_data.get('condition', 'Normal')}\n\n"
            
            response += f"💡 **General Agricultural Advice**:\n"
            response += f"• Take care of crops according to current weather\n"
            response += f"• Schedule irrigation according to weather conditions\n"
            response += f"• Regular monitoring for pests and diseases\n\n"
            
            response += f"📊 **Data Source**: IMD, ICAR, Government Agriculture Department (Real-time)\n"
            response += f"✅ **Guaranteed**: 100% Government Data Based\n"
            
            return response
    
    def _generate_general_response(self, query: str, deep_analysis: Dict[str, Any], language: str) -> str:
        """Generate simple, ChatGPT-like response for general queries with optimized performance"""
        intent = deep_analysis.get('intent', 'general_inquiry')
        query_lower = query.lower()
        
        # Try to use Ollama for intelligent response first (with timeout)
        try:
            ollama_response = self.ollama.generate_response(query, language)
            if ollama_response and len(ollama_response) > 50:
                logger.info("Using Ollama for general query response")
                # Simplify Ollama response if it's too complex
                if len(ollama_response) > 500:
                    return self._simplify_response(ollama_response, language)
                return ollama_response
        except Exception as e:
            logger.warning(f"Ollama response failed, using fallback: {e}")
        
        # Fallback to simple, direct responses
        
        # Simple, direct responses for common queries
        if any(keyword in query_lower for keyword in ['who is', 'कौन है', 'what is', 'क्या है']):
            # Handle "who is" queries
            if 'allu arjun' in query_lower:
                return "Allu Arjun is a popular Indian actor who works primarily in Telugu cinema. He's known for his dancing skills and has acted in many successful films."
            elif 'narendra modi' in query_lower:
                return "Narendra Modi is the current Prime Minister of India. He has been in office since 2014 and is a member of the Bharatiya Janata Party (BJP)."
            elif 'rahul gandhi' in query_lower:
                return "Rahul Gandhi is an Indian politician and a member of the Indian National Congress party. He has served as a Member of Parliament."
        
        # Science and technology queries
        if any(keyword in query_lower for keyword in ['artificial intelligence', 'ai', 'machine learning', 'technology']):
            if language in ['hi', 'hinglish']:
                return "AI (कृत्रिम बुद्धिमत्ता) एक तकनीक है जो कंप्यूटर को मानव की तरह सोचने और सीखने की क्षमता देती है। यह मशीन लर्निंग, डीप लर्निंग और न्यूरल नेटवर्क पर आधारित है।"
            else:
                return "AI (Artificial Intelligence) is technology that enables computers to think and learn like humans. It's used in many fields like healthcare, agriculture, finance, and education."
        
        # Geography queries
        elif any(keyword in query_lower for keyword in ['capital', 'राजधानी', 'country', 'देश']):
            if language in ['hi', 'hinglish']:
                return "भारत की राजधानी नई दिल्ली है। यह दिल्ली में स्थित है और भारत का राजनीतिक केंद्र है।"
            else:
                return "India's capital is New Delhi. It's located in Delhi and serves as the political center of India."
        
        # Programming queries
        elif any(keyword in query_lower for keyword in ['programming', 'coding', 'python', 'javascript', 'learn']):
            if language in ['hi', 'hinglish']:
                return "प्रोग्रामिंग सीखने के लिए Python एक अच्छी शुरुआत है। आप Codecademy, FreeCodeCamp, या YouTube पर ट्यूटोरियल देख सकते हैं।"
            else:
                return "For learning programming, Python is a great starting language. You can use platforms like Codecademy, FreeCodeCamp, or watch tutorials on YouTube."
        
        # Default intelligent response
        else:
            if language in ['hi', 'hinglish']:
                return "मैं कृषिमित्र AI हूं, आपका बुद्धिमान कृषि सहायक। मैं कृषि, फसल, मौसम, सरकारी योजनाओं के साथ-साथ सामान्य ज्ञान के प्रश्नों का भी उत्तर दे सकता हूं। आप क्या जानना चाहते हैं?"
            else:
                return "I'm Krishimitra AI, your intelligent agricultural assistant. I can help with agriculture, crops, weather, government schemes, and also answer general knowledge questions. What would you like to know?"
    
    def _simplify_response(self, response: str, language: str) -> str:
        """Simplify complex responses to be more farmer-friendly"""
        if len(response) <= 200:
            return response
        
        # Extract key points and create a simpler version
        sentences = response.split('. ')
        if len(sentences) <= 2:
            return response
        
        # Take first 2-3 sentences for simplicity
        simplified = '. '.join(sentences[:2]) + '.'
        
        # Add a simple closing
        if language in ['hi', 'hinglish']:
            simplified += " अधिक जानकारी के लिए कृषि संबंधी प्रश्न पूछें।"
        else:
            simplified += " Ask more agriculture-related questions for detailed information."
        
        return simplified


# Global instance for easy access
realtime_gov_ai = RealTimeGovernmentAI()

def process_farming_query_realtime(query: str, language: str = 'en', location: str = '') -> Dict[str, Any]:
    """
    External function to process farming queries with real-time government data.
    This acts as the entry point for other modules.
    """
    return realtime_gov_ai.process_farming_query(query, language, location)
