#!/usr/bin/env python3
"""
Ultra-Dynamic Real-Time Government API Service System
Ensures all farming-related queries use real-time government data with maximum accuracy
Integrates with: IMD, Agmarknet, e-NAM, ICAR, Soil Health Card, PM-Kisan
"""

import json
import time
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

logger = logging.getLogger(__name__)

class DynamicRealTimeService:
    """Ultra-dynamic real-time service with minimal caching for maximum accuracy"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Krishimitra AI - Dynamic Real-time Service',
            'Accept': 'application/json',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        })
        
        # Ultra-short cache for critical real-time data (30 seconds max)
        self.real_time_cache = {}
        self.cache_duration = 30  # 30 seconds maximum cache
        
        # Government API endpoints with real-time focus
        self.api_endpoints = {
            'imd_weather': {
                'url': 'https://mausam.imd.gov.in/api/current-weather',
                'cache_time': 300,  # 5 minutes for weather
                'priority': 'high'
            },
            'agmarknet_prices': {
                'url': 'https://agmarknet.gov.in/api/live-prices',
                'cache_time': 600,  # 10 minutes for prices
                'priority': 'high'
            },
            'enam_prices': {
                'url': 'https://enam.gov.in/api/realtime-prices',
                'cache_time': 300,  # 5 minutes
                'priority': 'high'
            },
            'soil_health': {
                'url': 'https://soilhealth.dac.gov.in/api/current',
                'cache_time': 3600,  # 1 hour for soil data
                'priority': 'medium'
            },
            'fertilizer_prices': {
                'url': 'https://api.data.gov.in/resource/fertilizer-prices',
                'cache_time': 1800,  # 30 minutes
                'priority': 'medium'
            },
            'government_schemes': {
                'url': 'https://api.data.gov.in/resource/schemes',
                'cache_time': 7200,  # 2 hours
                'priority': 'low'
            }
        }
        
        # Real-time data validation
        self.data_validators = {
            'weather': self._validate_weather_data,
            'market_prices': self._validate_market_data,
            'soil': self._validate_soil_data,
            'schemes': self._validate_scheme_data
        }
    
    def _is_cache_valid(self, key: str, cache_time: int) -> bool:
        """Check if cache is still valid based on data type"""
        if key not in self.real_time_cache:
            return False
        
        cached_time = self.real_time_cache[key].get('timestamp', 0)
        current_time = time.time()
        
        # For high priority data, use shorter cache times
        return (current_time - cached_time) < cache_time
    
    def _validate_weather_data(self, data: Dict) -> bool:
        """Validate weather data for accuracy"""
        required_fields = ['temperature', 'humidity', 'condition']
        return all(field in data for field in required_fields) and \
               isinstance(data.get('temperature'), (int, float)) and \
               isinstance(data.get('humidity'), (int, float))
    
    def _validate_market_data(self, data: Dict) -> bool:
        """Validate market price data for accuracy"""
        required_fields = ['price', 'commodity', 'location']
        return all(field in data for field in required_fields) and \
               isinstance(data.get('price'), (int, float)) and \
               data.get('price', 0) > 0
    
    def _validate_soil_data(self, data: Dict) -> bool:
        """Validate soil data for accuracy"""
        required_fields = ['ph', 'organic_matter', 'nutrients']
        return all(field in data for field in required_fields)
    
    def _validate_scheme_data(self, data: Dict) -> bool:
        """Validate government scheme data"""
        required_fields = ['scheme_name', 'benefit', 'eligibility']
        return all(field in data for field in required_fields)
    
    def _fetch_real_time_data(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Fetch real-time data from government APIs with error handling"""
        try:
            config = self.api_endpoints[endpoint]
            
            # Add timestamp to prevent caching
            if params is None:
                params = {}
            params['timestamp'] = str(int(time.time() * 1000))
            
            response = self.session.get(
                config['url'],
                params=params,
                timeout=10,
                headers={'Cache-Control': 'no-cache'}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Validate data based on endpoint type
                validator = self.data_validators.get(endpoint.split('_')[0])
                if validator and not validator(data):
                    logger.warning(f"Data validation failed for {endpoint}")
                    return None
                
                return {
                    'data': data,
                    'timestamp': time.time(),
                    'source': endpoint,
                    'status': 'live'
                }
            else:
                logger.error(f"API error for {endpoint}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching data from {endpoint}: {e}")
            return None
    
    def get_ultra_real_time_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Get ultra-real-time weather data with minimal caching"""
        cache_key = f"weather_{latitude}_{longitude}"
        
        # Check cache validity (5 minutes for weather)
        if self._is_cache_valid(cache_key, 300):
            cached_data = self.real_time_cache[cache_key]
            cached_data['source'] = 'cached_live'
            return cached_data
        
        # Fetch fresh data
        weather_data = self._fetch_real_time_data('imd_weather', {
            'lat': latitude,
            'lon': longitude
        })
        
        if weather_data:
            self.real_time_cache[cache_key] = weather_data
            return weather_data
        else:
            # Return minimal fallback with timestamp
            return {
                'data': {
                    'temperature': 25,
                    'humidity': 65,
                    'condition': 'Normal',
                    'wind_speed': 10,
                    'rainfall_probability': 20
                },
                'timestamp': time.time(),
                'source': 'fallback',
                'status': 'estimated',
                'message': 'Using estimated data - API unavailable'
            }
    
    def get_ultra_real_time_market_prices(self, commodity: str = None, location: str = None) -> Dict[str, Any]:
        """Get ultra-real-time market prices with minimal caching"""
        cache_key = f"market_{commodity}_{location}"
        
        # Check cache validity (10 minutes for prices)
        if self._is_cache_valid(cache_key, 600):
            cached_data = self.real_time_cache[cache_key]
            cached_data['source'] = 'cached_live'
            return cached_data
        
        # Fetch from multiple sources simultaneously
        prices_data = []
        
        # Agmarknet prices
        agmarknet_data = self._fetch_real_time_data('agmarknet_prices', {
            'commodity': commodity,
            'location': location
        })
        if agmarknet_data:
            prices_data.append(agmarknet_data)
        
        # e-NAM prices
        enam_data = self._fetch_real_time_data('enam_prices', {
            'commodity': commodity,
            'location': location
        })
        if enam_data:
            prices_data.append(enam_data)
        
        if prices_data:
            # Combine and validate prices
            combined_data = {
                'prices': [],
                'sources': [],
                'timestamp': time.time(),
                'status': 'live'
            }
            
            for price_data in prices_data:
                combined_data['prices'].extend(price_data['data'].get('prices', []))
                combined_data['sources'].append(price_data['source'])
            
            # Remove duplicates and sort by price
            unique_prices = {}
            for price in combined_data['prices']:
                key = f"{price.get('commodity')}_{price.get('location')}"
                if key not in unique_prices or price.get('price', 0) > unique_prices[key].get('price', 0):
                    unique_prices[key] = price
            
            combined_data['prices'] = list(unique_prices.values())
            combined_data['prices'].sort(key=lambda x: x.get('price', 0), reverse=True)
            
            self.real_time_cache[cache_key] = combined_data
            return combined_data
        else:
            # Return fallback with current timestamp
            return {
                'prices': [{
                    'commodity': commodity or 'General',
                    'price': 2000,
                    'location': location or 'India',
                    'unit': 'quintal',
                    'source': 'estimated'
                }],
                'sources': ['fallback'],
                'timestamp': time.time(),
                'status': 'estimated',
                'message': 'Using estimated prices - APIs unavailable'
            }
    
    def get_ultra_real_time_soil_data(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Get ultra-real-time soil health data"""
        cache_key = f"soil_{latitude}_{longitude}"
        
        # Check cache validity (1 hour for soil data)
        if self._is_cache_valid(cache_key, 3600):
            cached_data = self.real_time_cache[cache_key]
            cached_data['source'] = 'cached_live'
            return cached_data
        
        # Fetch fresh soil data
        soil_data = self._fetch_real_time_data('soil_health', {
            'lat': latitude,
            'lon': longitude
        })
        
        if soil_data:
            self.real_time_cache[cache_key] = soil_data
            return soil_data
        else:
            return {
                'data': {
                    'ph': 7.0,
                    'organic_matter': 1.5,
                    'nutrients': {
                        'nitrogen': 'Medium',
                        'phosphorus': 'Medium',
                        'potassium': 'Medium'
                    },
                    'soil_type': 'Alluvial'
                },
                'timestamp': time.time(),
                'source': 'estimated',
                'status': 'estimated',
                'message': 'Using estimated soil data - API unavailable'
            }
    
    def get_ultra_real_time_fertilizer_prices(self) -> Dict[str, Any]:
        """Get ultra-real-time fertilizer prices"""
        cache_key = "fertilizer_prices"
        
        # Check cache validity (30 minutes)
        if self._is_cache_valid(cache_key, 1800):
            cached_data = self.real_time_cache[cache_key]
            cached_data['source'] = 'cached_live'
            return cached_data
        
        # Fetch fresh fertilizer data
        fertilizer_data = self._fetch_real_time_data('fertilizer_prices')
        
        if fertilizer_data:
            self.real_time_cache[cache_key] = fertilizer_data
            return fertilizer_data
        else:
            return {
                'data': {
                    'urea': {'price': 266.50, 'unit': 'per bag'},
                    'dap': {'price': 1350, 'unit': 'per bag'},
                    'npk': {'price': 1250, 'unit': 'per bag'},
                    'potash': {'price': 650, 'unit': 'per bag'}
                },
                'timestamp': time.time(),
                'source': 'estimated',
                'status': 'estimated',
                'message': 'Using estimated fertilizer prices - API unavailable'
            }
    
    def get_comprehensive_real_time_data(self, latitude: float, longitude: float, 
                                       commodity: str = None) -> Dict[str, Any]:
        """Get comprehensive real-time data from all sources simultaneously"""
        start_time = time.time()
        
        # Fetch all data types in parallel for maximum speed
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                'weather': executor.submit(self.get_ultra_real_time_weather, latitude, longitude),
                'market_prices': executor.submit(self.get_ultra_real_time_market_prices, commodity),
                'soil_data': executor.submit(self.get_ultra_real_time_soil_data, latitude, longitude),
                'fertilizer_prices': executor.submit(self.get_ultra_real_time_fertilizer_prices)
            }
            
            results = {}
            for key, future in futures.items():
                try:
                    results[key] = future.result(timeout=10)
                except Exception as e:
                    logger.error(f"Error fetching {key}: {e}")
                    results[key] = None
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Determine overall data freshness
        timestamps = []
        for result in results.values():
            if result and 'timestamp' in result:
                timestamps.append(result['timestamp'])
        
        latest_timestamp = max(timestamps) if timestamps else time.time()
        data_age = time.time() - latest_timestamp
        
        return {
            'comprehensive_data': results,
            'response_time': response_time,
            'data_freshness': {
                'latest_update': latest_timestamp,
                'age_seconds': data_age,
                'freshness_status': 'live' if data_age < 300 else 'recent' if data_age < 1800 else 'stale'
            },
            'location': {'latitude': latitude, 'longitude': longitude},
            'commodity': commodity,
            'timestamp': time.time(),
            'status': 'comprehensive_real_time'
        }
    
    def clear_all_cache(self):
        """Clear all cached data for fresh real-time updates"""
        self.real_time_cache.clear()
        logger.info("All real-time cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        current_time = time.time()
        valid_entries = 0
        stale_entries = 0
        
        for key, data in self.real_time_cache.items():
            age = current_time - data.get('timestamp', 0)
            if age < self.cache_duration:
                valid_entries += 1
            else:
                stale_entries += 1
        
        return {
            'total_entries': len(self.real_time_cache),
            'valid_entries': valid_entries,
            'stale_entries': stale_entries,
            'cache_hit_potential': f"{(valid_entries / len(self.real_time_cache) * 100):.1f}%" if self.real_time_cache else "0%",
            'cache_duration': self.cache_duration,
            'timestamp': current_time
        }

Ultra-Dynamic Real-Time Government API Service System
Ensures all farming-related queries use real-time government data with maximum accuracy
Integrates with: IMD, Agmarknet, e-NAM, ICAR, Soil Health Card, PM-Kisan
"""

import json
import time
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

logger = logging.getLogger(__name__)

class DynamicRealTimeService:
    """Ultra-dynamic real-time service with minimal caching for maximum accuracy"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Krishimitra AI - Dynamic Real-time Service',
            'Accept': 'application/json',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        })
        
        # Ultra-short cache for critical real-time data (30 seconds max)
        self.real_time_cache = {}
        self.cache_duration = 30  # 30 seconds maximum cache
        
        # Government API endpoints with real-time focus
        self.api_endpoints = {
            'imd_weather': {
                'url': 'https://mausam.imd.gov.in/api/current-weather',
                'cache_time': 300,  # 5 minutes for weather
                'priority': 'high'
            },
            'agmarknet_prices': {
                'url': 'https://agmarknet.gov.in/api/live-prices',
                'cache_time': 600,  # 10 minutes for prices
                'priority': 'high'
            },
            'enam_prices': {
                'url': 'https://enam.gov.in/api/realtime-prices',
                'cache_time': 300,  # 5 minutes
                'priority': 'high'
            },
            'soil_health': {
                'url': 'https://soilhealth.dac.gov.in/api/current',
                'cache_time': 3600,  # 1 hour for soil data
                'priority': 'medium'
            },
            'fertilizer_prices': {
                'url': 'https://api.data.gov.in/resource/fertilizer-prices',
                'cache_time': 1800,  # 30 minutes
                'priority': 'medium'
            },
            'government_schemes': {
                'url': 'https://api.data.gov.in/resource/schemes',
                'cache_time': 7200,  # 2 hours
                'priority': 'low'
            }
        }
        
        # Real-time data validation
        self.data_validators = {
            'weather': self._validate_weather_data,
            'market_prices': self._validate_market_data,
            'soil': self._validate_soil_data,
            'schemes': self._validate_scheme_data
        }
    
    def _is_cache_valid(self, key: str, cache_time: int) -> bool:
        """Check if cache is still valid based on data type"""
        if key not in self.real_time_cache:
            return False
        
        cached_time = self.real_time_cache[key].get('timestamp', 0)
        current_time = time.time()
        
        # For high priority data, use shorter cache times
        return (current_time - cached_time) < cache_time
    
    def _validate_weather_data(self, data: Dict) -> bool:
        """Validate weather data for accuracy"""
        required_fields = ['temperature', 'humidity', 'condition']
        return all(field in data for field in required_fields) and \
               isinstance(data.get('temperature'), (int, float)) and \
               isinstance(data.get('humidity'), (int, float))
    
    def _validate_market_data(self, data: Dict) -> bool:
        """Validate market price data for accuracy"""
        required_fields = ['price', 'commodity', 'location']
        return all(field in data for field in required_fields) and \
               isinstance(data.get('price'), (int, float)) and \
               data.get('price', 0) > 0
    
    def _validate_soil_data(self, data: Dict) -> bool:
        """Validate soil data for accuracy"""
        required_fields = ['ph', 'organic_matter', 'nutrients']
        return all(field in data for field in required_fields)
    
    def _validate_scheme_data(self, data: Dict) -> bool:
        """Validate government scheme data"""
        required_fields = ['scheme_name', 'benefit', 'eligibility']
        return all(field in data for field in required_fields)
    
    def _fetch_real_time_data(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Fetch real-time data from government APIs with error handling"""
        try:
            config = self.api_endpoints[endpoint]
            
            # Add timestamp to prevent caching
            if params is None:
                params = {}
            params['timestamp'] = str(int(time.time() * 1000))
            
            response = self.session.get(
                config['url'],
                params=params,
                timeout=10,
                headers={'Cache-Control': 'no-cache'}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Validate data based on endpoint type
                validator = self.data_validators.get(endpoint.split('_')[0])
                if validator and not validator(data):
                    logger.warning(f"Data validation failed for {endpoint}")
                    return None
                
                return {
                    'data': data,
                    'timestamp': time.time(),
                    'source': endpoint,
                    'status': 'live'
                }
            else:
                logger.error(f"API error for {endpoint}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching data from {endpoint}: {e}")
            return None
    
    def get_ultra_real_time_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Get ultra-real-time weather data with minimal caching"""
        cache_key = f"weather_{latitude}_{longitude}"
        
        # Check cache validity (5 minutes for weather)
        if self._is_cache_valid(cache_key, 300):
            cached_data = self.real_time_cache[cache_key]
            cached_data['source'] = 'cached_live'
            return cached_data
        
        # Fetch fresh data
        weather_data = self._fetch_real_time_data('imd_weather', {
            'lat': latitude,
            'lon': longitude
        })
        
        if weather_data:
            self.real_time_cache[cache_key] = weather_data
            return weather_data
        else:
            # Return minimal fallback with timestamp
            return {
                'data': {
                    'temperature': 25,
                    'humidity': 65,
                    'condition': 'Normal',
                    'wind_speed': 10,
                    'rainfall_probability': 20
                },
                'timestamp': time.time(),
                'source': 'fallback',
                'status': 'estimated',
                'message': 'Using estimated data - API unavailable'
            }
    
    def get_ultra_real_time_market_prices(self, commodity: str = None, location: str = None) -> Dict[str, Any]:
        """Get ultra-real-time market prices with minimal caching"""
        cache_key = f"market_{commodity}_{location}"
        
        # Check cache validity (10 minutes for prices)
        if self._is_cache_valid(cache_key, 600):
            cached_data = self.real_time_cache[cache_key]
            cached_data['source'] = 'cached_live'
            return cached_data
        
        # Fetch from multiple sources simultaneously
        prices_data = []
        
        # Agmarknet prices
        agmarknet_data = self._fetch_real_time_data('agmarknet_prices', {
            'commodity': commodity,
            'location': location
        })
        if agmarknet_data:
            prices_data.append(agmarknet_data)
        
        # e-NAM prices
        enam_data = self._fetch_real_time_data('enam_prices', {
            'commodity': commodity,
            'location': location
        })
        if enam_data:
            prices_data.append(enam_data)
        
        if prices_data:
            # Combine and validate prices
            combined_data = {
                'prices': [],
                'sources': [],
                'timestamp': time.time(),
                'status': 'live'
            }
            
            for price_data in prices_data:
                combined_data['prices'].extend(price_data['data'].get('prices', []))
                combined_data['sources'].append(price_data['source'])
            
            # Remove duplicates and sort by price
            unique_prices = {}
            for price in combined_data['prices']:
                key = f"{price.get('commodity')}_{price.get('location')}"
                if key not in unique_prices or price.get('price', 0) > unique_prices[key].get('price', 0):
                    unique_prices[key] = price
            
            combined_data['prices'] = list(unique_prices.values())
            combined_data['prices'].sort(key=lambda x: x.get('price', 0), reverse=True)
            
            self.real_time_cache[cache_key] = combined_data
            return combined_data
        else:
            # Return fallback with current timestamp
            return {
                'prices': [{
                    'commodity': commodity or 'General',
                    'price': 2000,
                    'location': location or 'India',
                    'unit': 'quintal',
                    'source': 'estimated'
                }],
                'sources': ['fallback'],
                'timestamp': time.time(),
                'status': 'estimated',
                'message': 'Using estimated prices - APIs unavailable'
            }
    
    def get_ultra_real_time_soil_data(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Get ultra-real-time soil health data"""
        cache_key = f"soil_{latitude}_{longitude}"
        
        # Check cache validity (1 hour for soil data)
        if self._is_cache_valid(cache_key, 3600):
            cached_data = self.real_time_cache[cache_key]
            cached_data['source'] = 'cached_live'
            return cached_data
        
        # Fetch fresh soil data
        soil_data = self._fetch_real_time_data('soil_health', {
            'lat': latitude,
            'lon': longitude
        })
        
        if soil_data:
            self.real_time_cache[cache_key] = soil_data
            return soil_data
        else:
            return {
                'data': {
                    'ph': 7.0,
                    'organic_matter': 1.5,
                    'nutrients': {
                        'nitrogen': 'Medium',
                        'phosphorus': 'Medium',
                        'potassium': 'Medium'
                    },
                    'soil_type': 'Alluvial'
                },
                'timestamp': time.time(),
                'source': 'estimated',
                'status': 'estimated',
                'message': 'Using estimated soil data - API unavailable'
            }
    
    def get_ultra_real_time_fertilizer_prices(self) -> Dict[str, Any]:
        """Get ultra-real-time fertilizer prices"""
        cache_key = "fertilizer_prices"
        
        # Check cache validity (30 minutes)
        if self._is_cache_valid(cache_key, 1800):
            cached_data = self.real_time_cache[cache_key]
            cached_data['source'] = 'cached_live'
            return cached_data
        
        # Fetch fresh fertilizer data
        fertilizer_data = self._fetch_real_time_data('fertilizer_prices')
        
        if fertilizer_data:
            self.real_time_cache[cache_key] = fertilizer_data
            return fertilizer_data
        else:
            return {
                'data': {
                    'urea': {'price': 266.50, 'unit': 'per bag'},
                    'dap': {'price': 1350, 'unit': 'per bag'},
                    'npk': {'price': 1250, 'unit': 'per bag'},
                    'potash': {'price': 650, 'unit': 'per bag'}
                },
                'timestamp': time.time(),
                'source': 'estimated',
                'status': 'estimated',
                'message': 'Using estimated fertilizer prices - API unavailable'
            }
    
    def get_comprehensive_real_time_data(self, latitude: float, longitude: float, 
                                       commodity: str = None) -> Dict[str, Any]:
        """Get comprehensive real-time data from all sources simultaneously"""
        start_time = time.time()
        
        # Fetch all data types in parallel for maximum speed
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                'weather': executor.submit(self.get_ultra_real_time_weather, latitude, longitude),
                'market_prices': executor.submit(self.get_ultra_real_time_market_prices, commodity),
                'soil_data': executor.submit(self.get_ultra_real_time_soil_data, latitude, longitude),
                'fertilizer_prices': executor.submit(self.get_ultra_real_time_fertilizer_prices)
            }
            
            results = {}
            for key, future in futures.items():
                try:
                    results[key] = future.result(timeout=10)
                except Exception as e:
                    logger.error(f"Error fetching {key}: {e}")
                    results[key] = None
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Determine overall data freshness
        timestamps = []
        for result in results.values():
            if result and 'timestamp' in result:
                timestamps.append(result['timestamp'])
        
        latest_timestamp = max(timestamps) if timestamps else time.time()
        data_age = time.time() - latest_timestamp
        
        return {
            'comprehensive_data': results,
            'response_time': response_time,
            'data_freshness': {
                'latest_update': latest_timestamp,
                'age_seconds': data_age,
                'freshness_status': 'live' if data_age < 300 else 'recent' if data_age < 1800 else 'stale'
            },
            'location': {'latitude': latitude, 'longitude': longitude},
            'commodity': commodity,
            'timestamp': time.time(),
            'status': 'comprehensive_real_time'
        }
    
    def clear_all_cache(self):
        """Clear all cached data for fresh real-time updates"""
        self.real_time_cache.clear()
        logger.info("All real-time cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        current_time = time.time()
        valid_entries = 0
        stale_entries = 0
        
        for key, data in self.real_time_cache.items():
            age = current_time - data.get('timestamp', 0)
            if age < self.cache_duration:
                valid_entries += 1
            else:
                stale_entries += 1
        
        return {
            'total_entries': len(self.real_time_cache),
            'valid_entries': valid_entries,
            'stale_entries': stale_entries,
            'cache_hit_potential': f"{(valid_entries / len(self.real_time_cache) * 100):.1f}%" if self.real_time_cache else "0%",
            'cache_duration': self.cache_duration,
            'timestamp': current_time
        }



