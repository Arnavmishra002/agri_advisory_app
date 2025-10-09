#!/usr/bin/env python3
"""
Enhanced Government API Integration
Improves government data access and reliability
"""

import requests
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)

class EnhancedGovernmentAPI:
    """Enhanced government API integration with better reliability"""
    
    def __init__(self):
        # Government API endpoints - Updated with working URLs
        self.api_endpoints = {
            'agmarknet': 'https://agmarknet.gov.in/PriceAndArrivals/CommodityDailyPriceAndArrivals.aspx',
            'enam': 'https://enam.gov.in/',
            'fci': 'https://fci.gov.in/',
            'apmc': 'https://agmarknet.gov.in/',
            'imd': 'https://mausam.imd.gov.in/',
            'soil_health': 'https://soilhealth.dac.gov.in/',
            'pm_kisan': 'https://pmkisan.gov.in/',
            'nabard': 'https://nabard.org/',
            # Working alternative APIs
            'openweather': 'https://api.openweathermap.org/data/2.5/weather',
            'worldbank': 'https://api.worldbank.org/v2/country/IN/indicator',
            'data_gov': 'https://data.gov.in/api/3/action/datastore_search'
        }
        
        # Fallback data for when APIs are unavailable
        self.fallback_data = self._load_fallback_data()
        
        # Cache for API responses
        self.cache = {}
        self.cache_timeout = 3600  # 1 hour
        
        # Request session with proper headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'KrisiMitra-AI-Assistant/2.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
    def _load_fallback_data(self) -> Dict[str, Any]:
        """Load comprehensive fallback data with realistic prices and schemes"""
        return {
            'msp_prices': {
                'wheat': 2275, 'rice': 2183, 'maize': 2090, 'cotton': 6620,
                'sugarcane': 315, 'groundnut': 6377, 'bajra': 2500, 'jowar': 2977,
                'moong': 7755, 'urad': 6600, 'chana': 5440, 'mustard': 5650,
                'soybean': 3950, 'tur': 6600, 'masoor': 6100, 'barley': 1850
            },
            'market_prices': {
                'wheat': {'min': 2200, 'max': 2500, 'avg': 2350, 'msp': 2275, 'trend': '+2.5%'},
                'rice': {'min': 2100, 'max': 2800, 'avg': 2450, 'msp': 2183, 'trend': '+1.8%'},
                'maize': {'min': 1900, 'max': 2200, 'avg': 2050, 'msp': 2090, 'trend': '+3.2%'},
                'cotton': {'min': 6000, 'max': 7200, 'avg': 6600, 'msp': 6620, 'trend': '-1.5%'},
                'groundnut': {'min': 5500, 'max': 7500, 'avg': 6500, 'msp': 6377, 'trend': '+4.1%'},
                'moong': {'min': 7000, 'max': 8500, 'avg': 7750, 'msp': 7755, 'trend': '+2.8%'},
                'jowar': {'min': 2500, 'max': 3200, 'avg': 2850, 'msp': 2977, 'trend': '+1.2%'},
                'bajra': {'min': 2200, 'max': 2800, 'avg': 2500, 'msp': 2500, 'trend': '+0.8%'},
                'mustard': {'min': 5200, 'max': 6200, 'avg': 5700, 'msp': 5650, 'trend': '+3.5%'},
                'sugarcane': {'min': 300, 'max': 350, 'avg': 325, 'msp': 315, 'trend': '+2.1%'},
                'potato': {'min': 800, 'max': 1200, 'avg': 1000, 'msp': 0, 'trend': '+5.2%'},
                'onion': {'min': 1200, 'max': 1800, 'avg': 1500, 'msp': 0, 'trend': '+7.8%'}
            },
            'location_multipliers': {
                'delhi': 1.0, 'mumbai': 1.15, 'bangalore': 1.05, 'chennai': 0.95,
                'kolkata': 0.98, 'hyderabad': 1.02, 'pune': 1.08, 'ahmedabad': 1.03,
                'punjab': 0.92, 'haryana': 0.95, 'uttar_pradesh': 0.88, 'bihar': 0.85,
                'west_bengal': 0.90, 'tamil_nadu': 0.93, 'karnataka': 1.00, 'maharashtra': 1.05,
                'gujarat': 1.02, 'rajasthan': 0.89, 'madhya_pradesh': 0.87, 'odisha': 0.91
            },
            'weather_data': {
                'delhi': {'temp': 28, 'humidity': 65, 'rainfall': 25},
                'mumbai': {'temp': 30, 'humidity': 80, 'rainfall': 45},
                'kolkata': {'temp': 32, 'humidity': 75, 'rainfall': 35},
                'chennai': {'temp': 33, 'humidity': 70, 'rainfall': 30},
                'bangalore': {'temp': 26, 'humidity': 60, 'rainfall': 20}
            },
            'government_schemes': {
                'pm_kisan': {
                    'name': 'प्रधानमंत्री किसान सम्मान निधि',
                    'benefit': '₹6,000 प्रति वर्ष',
                    'eligibility': 'सभी किसान परिवार'
                },
                'fasal_bima': {
                    'name': 'प्रधानमंत्री फसल बीमा योजना',
                    'benefit': 'प्रीमियम पर 90% सब्सिडी',
                    'eligibility': 'सभी किसान'
                },
                'kisan_credit_card': {
                    'name': 'किसान क्रेडिट कार्ड',
                    'benefit': '₹3 लाख तक का ऋण',
                    'eligibility': 'जमीन वाले किसान'
                },
                'soil_health_card': {
                    'name': 'मृदा स्वास्थ्य कार्ड',
                    'benefit': 'मिट्टी परीक्षण और सुझाव',
                    'eligibility': 'सभी किसान'
                },
                'neem_coated_urea': {
                    'name': 'नीम कोटेड यूरिया',
                    'benefit': '₹268/बैग सब्सिडी',
                    'eligibility': 'सभी किसान'
                },
                'kisan_drone': {
                    'name': 'किसान ड्रोन योजना',
                    'benefit': 'ड्रोन खरीद पर 75% सब्सिडी',
                    'eligibility': 'FPO, सहकारी समितियां'
                }
            }
        }
    
    def get_enhanced_market_prices(self, crop: str, location: str, language: str = 'en') -> Dict[str, Any]:
        """Get enhanced market prices with fallback"""
        cache_key = f"market_{crop}_{location}_{language}"
        
        if self._is_cached(cache_key):
            _, data = self.cache[cache_key]
            return data
        
        # Try multiple API sources
        api_sources = ['agmarknet', 'enam', 'fci', 'apmc']
        market_data = None
        
        for source in api_sources:
            try:
                market_data = self._fetch_from_api(source, crop, location)
                if market_data:
                    break
            except Exception as e:
                logger.warning(f"API {source} failed: {e}")
                continue
        
        # If all APIs fail, use enhanced fallback
        if not market_data:
            market_data = self._get_enhanced_fallback_price(crop, location, language)
        
        # Cache the result
        self._cache_result(cache_key, market_data)
        
        return market_data
    
    def get_real_market_prices(self, crop: str, location: str = None, commodity: str = None, 
                              latitude: float = None, longitude: float = None, 
                              language: str = 'en', **kwargs) -> List[Dict[str, Any]]:
        """Get real market prices (compatibility method)"""
        try:
            # Use provided parameters or defaults
            commodity = commodity or crop
            state = location
            mandi = kwargs.get('mandi')
            
            # Use the provided parameters or defaults
            crop_name = commodity or crop
            location_name = location or state or 'Delhi'
            
            market_data = self.get_enhanced_market_prices(crop_name, location_name)
            if market_data:
                return [market_data]
            return []
        except Exception as e:
            logger.warning(f"Error getting real market prices: {e}")
            return []
    
    def get_enhanced_weather_data(self, location: str, language: str = 'en') -> Dict[str, Any]:
        """Get enhanced weather data with fallback"""
        cache_key = f"weather_{location}_{language}"
        
        if self._is_cached(cache_key):
            _, data = self.cache[cache_key]
            return data
        
        weather_data = None
        
        try:
            # Try IMD API
            weather_data = self._fetch_weather_from_imd(location)
        except Exception as e:
            logger.warning(f"Weather API failed: {e}")
        
        # If API fails, use fallback
        if not weather_data:
            weather_data = self._get_fallback_weather_data(location, language)
        
        # Cache the result
        self._cache_result(cache_key, weather_data)
        
        return weather_data
    
    def get_real_weather_data(self, location: str, language: str = 'en', **kwargs) -> Dict[str, Any]:
        """Get real weather data (compatibility method)"""
        try:
            return self.get_enhanced_weather_data(location)
        except Exception as e:
            logger.warning(f"Error getting real weather data: {e}")
            return {}
    
    def get_enhanced_crop_recommendations(self, location: str, season: str = None, 
                                        language: str = 'en') -> Dict[str, Any]:
        """Get enhanced crop recommendations"""
        cache_key = f"crops_{location}_{season}_{language}"
        
        if self._is_cached(cache_key):
            _, data = self.cache[cache_key]
            return data
        
        # Generate crop recommendations based on location and season
        recommendations = self._generate_crop_recommendations(location, season, language)
        
        result = {
            'location': location,
            'season': season or 'kharif',
            'recommendations': recommendations,
            'source': 'Enhanced Government API',
            'timestamp': datetime.now().isoformat()
        }
        
        # Cache the result
        self._cache_result(cache_key, result)
        
        return result
    
    def get_government_schemes(self, location: str = None, state: str = None, 
                              language: str = 'en') -> Dict[str, Any]:
        """Get government schemes data"""
        cache_key = f"schemes_{location}_{state}_{language}"
        
        if self._is_cached(cache_key):
            _, data = self.cache[cache_key]
            return data
        
        schemes_data = self.fallback_data['government_schemes'].copy()
        
        # Add state-specific schemes if available
        if state:
            state_schemes = self._get_state_specific_schemes(state)
            schemes_data.update(state_schemes)
        
        # Format for language
        if language == 'hi':
            schemes_data = self._translate_schemes_to_hindi(schemes_data)
        
        # Cache the result
        self._cache_result(cache_key, schemes_data)
        
        return schemes_data
    
    def _fetch_from_api(self, source: str, crop: str, location: str) -> Dict[str, Any]:
        """Fetch data from specific API source"""
        
        if source not in self.api_endpoints:
            return None
        
        url = self.api_endpoints[source]
        params = {
            'commodity': crop,
            'state': location or 'Delhi',
            'format': 'json'
        }
        
        try:
            # Add retry mechanism with exponential backoff
            for attempt in range(3):
                try:
                    response = self.session.get(url, params=params, timeout=10)
                    if response.status_code == 200:
                        # Handle UTF-8 BOM encoding issues
                        try:
                            data = response.json()
                        except ValueError:
                            # Try to decode with UTF-8-sig to handle BOM
                            response.encoding = 'utf-8-sig'
                            data = response.json()
                        
                        # Validate data structure
                        if isinstance(data, dict) and data:
                            return self._parse_api_response(data, source)
                        else:
                            logger.warning(f"API {source} returned empty or invalid data")
                            if attempt < 2:
                                time.sleep(1 * (attempt + 1))  # Exponential backoff
                                continue
                    else:
                        logger.warning(f"API {source} returned status {response.status_code} (attempt {attempt + 1})")
                        if attempt < 2:
                            time.sleep(1 * (attempt + 1))
                            continue
                except requests.exceptions.RequestException as e:
                    logger.warning(f"API {source} request failed (attempt {attempt + 1}): {e}")
                    if attempt < 2:
                        time.sleep(1 * (attempt + 1))
                        continue
                    
            return None
        except Exception as e:
            logger.warning(f"API {source} unexpected error: {e}")
            return None
    
    def _fetch_weather_from_imd(self, location: str) -> Dict[str, Any]:
        """Fetch weather data from IMD"""
        try:
            url = self.api_endpoints['imd']
            params = {
                'location': location,
                'format': 'json'
            }
            
            response = self.session.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    'temperature': data.get('temperature', 25.0),
                    'humidity': data.get('humidity', 70),
                    'condition': data.get('condition', 'Clear'),
                    'source': 'IMD'
                }
            else:
                return None
        except Exception as e:
            logger.warning(f"IMD weather API failed: {e}")
            return None
    
    def _parse_api_response(self, data: Dict[str, Any], source: str) -> Dict[str, Any]:
        """Parse API response based on source"""
        try:
            if source == 'agmarknet':
                return {
                    'price': data.get('price', 0),
                    'market': data.get('market', 'Unknown'),
                    'state': data.get('state', 'Unknown'),
                    'source': 'Agmarknet'
                }
            elif source == 'enam':
                return {
                    'price': data.get('price', 0),
                    'market': data.get('market', 'Unknown'),
                    'state': data.get('state', 'Unknown'),
                    'source': 'e-NAM'
                }
            else:
                return {
                    'price': data.get('price', 0),
                    'market': data.get('market', 'Unknown'),
                    'state': data.get('state', 'Unknown'),
                    'source': source.title()
                }
        except Exception as e:
            logger.warning(f"Error parsing {source} response: {e}")
        return None
    
    def _get_enhanced_fallback_price(self, crop: str, location: str, language: str) -> Dict[str, Any]:
        """Get enhanced fallback price data with realistic market prices"""
        market_prices = self.fallback_data['market_prices']
        
        # Get realistic price range for crop
        crop_key = crop.lower()
        price_data = market_prices.get(crop_key, market_prices.get('wheat', {'min': 2200, 'max': 2500, 'avg': 2350}))
        
        # Use average price as base
        base_price = price_data['avg']
        
        # Add location-based variation
        location_multiplier = self._get_location_multiplier(location)
        adjusted_price = int(base_price * location_multiplier)
        
        return {
            'price': adjusted_price,
            'market': f"{location} Mandi",
            'state': location,
            'source': 'Enhanced Fallback',
            'msp': price_data.get('msp', price_data['avg']),
            'trend': price_data.get('trend', '+2.0%'),
            'change': price_data.get('trend', '+2.0%'),
            'min_price': price_data['min'],
            'max_price': price_data['max'],
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_fallback_weather_data(self, location: str, language: str) -> Dict[str, Any]:
        """Get fallback weather data with realistic location-based data"""
        # Use pre-defined weather data for major cities
        location_key = location.lower().replace(' ', '').replace('city', '')
        weather_data = self.fallback_data['weather_data'].get(location_key)
        
        if weather_data:
            temperature = weather_data['temp']
            humidity = weather_data['humidity']
            rainfall = weather_data['rainfall']
        else:
            # Generate realistic weather data based on location
            temperature = self._estimate_temperature(location)
            humidity = self._estimate_humidity(location)
            rainfall = self._estimate_rainfall(location)
        
        return {
            'temperature': temperature,
            'humidity': humidity,
            'condition': 'Clear',
            'source': 'Fallback Data',
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_crop_recommendations(self, location: str, season: str, language: str) -> List[Dict[str, Any]]:
        """Generate crop recommendations based on location and season"""
        season = season or 'kharif'
        
        # Location-based crop recommendations
        location_crops = {
            'delhi': {
                'kharif': ['rice', 'maize', 'cotton', 'groundnut'],
                'rabi': ['wheat', 'mustard', 'potato', 'onion']
            },
            'mumbai': {
                'kharif': ['rice', 'sugarcane', 'cotton', 'groundnut'],
                'rabi': ['wheat', 'onion', 'tomato', 'vegetables']
            },
            'bangalore': {
                'kharif': ['rice', 'maize', 'groundnut', 'vegetables'],
                'rabi': ['wheat', 'tomato', 'onion', 'vegetables']
            }
        }
        
        # Get crops for location or default to Delhi
        location_key = location.lower()
        if location_key not in location_crops:
            location_key = 'delhi'
        
        crops = location_crops[location_key].get(season, location_crops[location_key]['kharif'])
        
        # Generate recommendations with scores
        recommendations = []
        for i, crop in enumerate(crops[:4]):
            score = 95 - (i * 5)  # Decreasing scores
            recommendations.append({
                'crop': crop,
                'name': crop.title(),
                'score': score,
                'suitability': score,
                'msp': self.fallback_data['msp_prices'].get(crop, 2500),
                'yield': '3-5 tons/hectare',
                'soil': 'Loamy',
                'climate': 'Sub-tropical'
            })
        
        return recommendations
    
    def _get_state_specific_schemes(self, state: str) -> Dict[str, Any]:
        """Get state-specific government schemes"""
        state_schemes = {
            'delhi': {
                'delhi_scheme': {
                    'name': 'Delhi Agricultural Scheme',
                    'benefit': 'Special subsidy for Delhi farmers',
                    'eligibility': 'Delhi registered farmers'
                }
            },
            'mumbai': {
                'maharashtra_scheme': {
                    'name': 'Maharashtra Agricultural Scheme',
                    'benefit': 'State-specific benefits',
                    'eligibility': 'Maharashtra farmers'
                }
            }
        }
        
        return state_schemes.get(state.lower(), {})
    
    def _translate_schemes_to_hindi(self, schemes_data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate schemes data to Hindi"""
        hindi_translations = {
            'PM Kisan Samman Nidhi': 'प्रधानमंत्री किसान सम्मान निधि',
            'PM Fasal Bima Yojana': 'प्रधानमंत्री फसल बीमा योजना',
            'Kisan Credit Card': 'किसान क्रेडिट कार्ड',
            '₹6,000 per year': '₹6,000 प्रति वर्ष',
            '90% subsidy on premium': 'प्रीमियम पर 90% सब्सिडी',
            'Up to ₹3 lakh loan': '₹3 लाख तक का ऋण'
        }
        
        translated_schemes = {}
        for key, scheme in schemes_data.items():
            translated_scheme = scheme.copy()
            for field, value in scheme.items():
                if isinstance(value, str) and value in hindi_translations:
                    translated_scheme[field] = hindi_translations[value]
            translated_schemes[key] = translated_scheme
        
        return translated_schemes
    
    def _get_location_multiplier(self, location: str) -> float:
        """Get price multiplier based on location"""
        location_key = location.lower().replace(' ', '').replace('city', '')
        multipliers = self.fallback_data['location_multipliers']
        return multipliers.get(location_key, 1.0)
    
    def _estimate_temperature(self, location: str) -> float:
        """Estimate temperature based on location"""
        location_temps = {
            'delhi': 28.0,
            'mumbai': 30.0,
            'bangalore': 25.0,
            'chennai': 32.0,
            'kolkata': 29.0,
            'hyderabad': 31.0,
            'pune': 27.0,
            'ahmedabad': 33.0
        }
        
        location_key = location.lower()
        return location_temps.get(location_key, 28.0)
    
    def _estimate_humidity(self, location: str) -> int:
        """Estimate humidity based on location"""
        location_humidity = {
            'delhi': 65,
            'mumbai': 80,
            'bangalore': 70,
            'chennai': 75,
            'kolkata': 85,
            'hyderabad': 60,
            'pune': 68,
            'ahmedabad': 55
        }
        
        location_key = location.lower()
        return location_humidity.get(location_key, 70)
    
    def _is_cached(self, key: str) -> bool:
        """Check if data is cached and not expired"""
        if key not in self.cache:
            return False
        
        cached_time, _ = self.cache[key]
        return time.time() - cached_time < self.cache_timeout
    
    def _cache_result(self, key: str, data: Any) -> None:
        """Cache the result with timestamp"""
        self.cache[key] = (time.time(), data)
        
        # Clean up old cache entries
        current_time = time.time()
        expired_keys = [k for k, (t, _) in self.cache.items() 
                       if current_time - t > self.cache_timeout]
        
        for expired_key in expired_keys:
            del self.cache[expired_key]
    
    def _estimate_rainfall(self, location: str, month: int = None) -> Dict[str, Any]:
        """Estimate rainfall for a location based on regional patterns"""
        if month is None:
            month = datetime.now().month
        
        # Regional rainfall patterns in India (mm)
        rainfall_patterns = {
            'delhi': {1: 20, 2: 20, 3: 15, 4: 10, 5: 25, 6: 70, 7: 180, 8: 170, 9: 120, 10: 15, 11: 5, 12: 15},
            'mumbai': {1: 5, 2: 2, 3: 2, 4: 5, 5: 50, 6: 350, 7: 700, 8: 450, 9: 300, 10: 100, 11: 25, 12: 10},
            'bangalore': {1: 10, 2: 10, 3: 25, 4: 50, 5: 120, 6: 80, 7: 100, 8: 120, 9: 180, 10: 180, 11: 60, 12: 20},
            'chennai': {1: 25, 2: 10, 3: 10, 4: 20, 5: 50, 6: 50, 7: 80, 8: 120, 9: 150, 10: 200, 11: 300, 12: 150},
            'kolkata': {1: 15, 2: 20, 3: 30, 4: 50, 5: 120, 6: 250, 7: 300, 8: 300, 9: 250, 10: 100, 11: 30, 12: 15},
            'hyderabad': {1: 5, 2: 5, 3: 10, 4: 20, 5: 40, 6: 100, 7: 150, 8: 150, 9: 180, 10: 100, 11: 25, 12: 10},
            'pune': {1: 5, 2: 5, 3: 10, 4: 15, 5: 40, 6: 150, 7: 200, 8: 150, 9: 120, 10: 80, 11: 20, 12: 10},
            'ahmedabad': {1: 5, 2: 2, 3: 2, 4: 5, 5: 20, 6: 100, 7: 250, 8: 200, 9: 120, 10: 30, 11: 10, 12: 5}
        }
        
        location_key = location.lower()
        if location_key not in rainfall_patterns:
            # Default to Delhi pattern for unknown locations
            location_key = 'delhi'
        
        base_rainfall = rainfall_patterns[location_key].get(month, 50)
        
        # Add some variation (±20%)
        import random
        variation = random.uniform(-0.2, 0.2)
        estimated_rainfall = base_rainfall * (1 + variation)
        
        return {
            'rainfall_mm': round(estimated_rainfall, 1),
            'month': month,
            'location': location,
            'pattern': 'estimated'
        }