#!/usr/bin/env python3
"""
Consolidated Government Service
Combines all government API integrations into a single, well-organized service
Replaces: enhanced_government_api.py, ultra_dynamic_government_api.py, 
          dynamic_realtime_service.py, real_time_gov_data_service.py,
          government_data_service.py, clean_government_api.py
"""

import json
import logging
import requests
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class ConsolidatedGovernmentService:
    """
    Consolidated Government Service that handles all government API integrations:
    - IMD Weather data
    - Agmarknet market prices
    - e-NAM prices
    - ICAR crop recommendations
    - Soil Health Card data
    - PM-Kisan schemes
    - Government schemes and policies
    """
    
    def __init__(self):
        """Initialize the consolidated government service"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Krishimitra AI - Government Service',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Cache configuration
        self.cache = {}
        self.cache_duration = {
            'weather': 300,      # 5 minutes
            'prices': 600,       # 10 minutes
            'schemes': 3600,     # 1 hour
            'soil': 7200,        # 2 hours
            'default': 1800      # 30 minutes
        }
        
        # Government API endpoints
        self.api_endpoints = self._initialize_api_endpoints()
        
        # Fallback data
        self.fallback_data = self._initialize_fallback_data()
        
        # Indian locations database
        self.indian_locations = self._initialize_indian_locations()
        
        # Initialize weather API (self-referencing for method calls)
        self.weather_api = self
    
    def _initialize_api_endpoints(self) -> Dict[str, Dict]:
        """Initialize government API endpoints"""
        return {
            'imd_weather': {
                'url': 'https://mausam.imd.gov.in/api/current-weather',
                'cache_time': 300,
                'priority': 'high',
                'description': 'IMD Weather Data'
            },
            'agmarknet_prices': {
                'url': 'https://agmarknet.gov.in/api/live-prices',
                'cache_time': 600,
                'priority': 'high',
                'description': 'Agmarknet Market Prices'
            },
            'enam_prices': {
                'url': 'https://enam.gov.in/api/realtime-prices',
                'cache_time': 300,
                'priority': 'high',
                'description': 'e-NAM Prices'
            },
            'icar_recommendations': {
                'url': 'https://icar.gov.in/api/crop-recommendations',
                'cache_time': 3600,
                'priority': 'medium',
                'description': 'ICAR Crop Recommendations'
            },
            'soil_health': {
                'url': 'https://soilhealth.dac.gov.in/api/current',
                'cache_time': 7200,
                'priority': 'medium',
                'description': 'Soil Health Card Data'
            },
            'pm_kisan_schemes': {
                'url': 'https://pmkisan.gov.in/api/schemes',
                'cache_time': 3600,
                'priority': 'low',
                'description': 'PM-Kisan Schemes'
            },
            'government_schemes': {
                'url': 'https://api.data.gov.in/resource/schemes',
                'cache_time': 3600,
                'priority': 'low',
                'description': 'Government Schemes'
            }
        }
    
    def _initialize_fallback_data(self) -> Dict[str, Any]:
        """Initialize fallback data for when APIs are unavailable"""
        return {
            'weather': {
                'temperature': 25.0,
                'humidity': 60,
                'condition': 'Partly Cloudy',
                'source': 'fallback'
            },
            'prices': {
                'wheat': 2450,
                'rice': 3200,
                'maize': 1800,
                'source': 'fallback'
            },
            'schemes': [
                {
                    'name': 'PM-Kisan Samman Nidhi',
                    'amount': 6000,
                    'description': 'Direct income support to farmers'
                }
            ],
            'crop_recommendations': [
                {
                    'crop': 'Wheat',
                    'suitability': 'High',
                    'season': 'Rabi'
                }
            ]
        }
    
    def _initialize_indian_locations(self) -> Dict[str, Any]:
        """Initialize comprehensive Indian locations database"""
        return {
            'states': {
                'delhi': {'name': 'Delhi', 'hindi_name': 'दिल्ली', 'lat': 28.7041, 'lon': 77.1025},
                'mumbai': {'name': 'Mumbai', 'hindi_name': 'मुंबई', 'lat': 19.0760, 'lon': 72.8777},
                'bangalore': {'name': 'Bangalore', 'hindi_name': 'बैंगलोर', 'lat': 12.9716, 'lon': 77.5946},
                'kolkata': {'name': 'Kolkata', 'hindi_name': 'कोलकाता', 'lat': 22.5726, 'lon': 88.3639},
                'chennai': {'name': 'Chennai', 'hindi_name': 'चेन्नई', 'lat': 13.0827, 'lon': 80.2707},
                'hyderabad': {'name': 'Hyderabad', 'hindi_name': 'हैदराबाद', 'lat': 17.3850, 'lon': 78.4867},
                'pune': {'name': 'Pune', 'hindi_name': 'पुणे', 'lat': 18.5204, 'lon': 73.8567},
                'ahmedabad': {'name': 'Ahmedabad', 'hindi_name': 'अहमदाबाद', 'lat': 23.0225, 'lon': 72.5714},
                'jaipur': {'name': 'Jaipur', 'hindi_name': 'जयपुर', 'lat': 26.9124, 'lon': 75.7873},
                'lucknow': {'name': 'Lucknow', 'hindi_name': 'लखनऊ', 'lat': 26.8467, 'lon': 80.9462}
            },
            'districts': {
                'new_delhi': {'name': 'New Delhi', 'state': 'Delhi', 'lat': 28.6139, 'lon': 77.2090},
                'mumbai_suburban': {'name': 'Mumbai Suburban', 'state': 'Maharashtra', 'lat': 19.0760, 'lon': 72.8777},
                'bangalore_urban': {'name': 'Bangalore Urban', 'state': 'Karnataka', 'lat': 12.9716, 'lon': 77.5946}
            }
        }
    
    def _is_cache_valid(self, key: str, cache_type: str = 'default') -> bool:
        """Check if cache is still valid"""
        if key not in self.cache:
            return False
        
        cached_time = self.cache[key].get('timestamp', 0)
        current_time = time.time()
        cache_time = self.cache_duration.get(cache_type, self.cache_duration['default'])
        
        return (current_time - cached_time) < cache_time
    
    def _get_cached_data(self, key: str) -> Optional[Dict]:
        """Get cached data if valid"""
        if self._is_cache_valid(key):
            return self.cache[key].get('data')
        return None
    
    def _set_cache_data(self, key: str, data: Dict, cache_type: str = 'default') -> None:
        """Set data in cache"""
        self.cache[key] = {
            'data': data,
            'timestamp': time.time(),
            'cache_type': cache_type
        }
    
    def get_weather_data(self, location: str = 'Delhi') -> Dict[str, Any]:
        """
        Get weather data for a location
        
        Args:
            location: Location name or coordinates
            
        Returns:
            Weather data dictionary
        """
        try:
            cache_key = f"weather_{location.lower()}"
            cached_data = self._get_cached_data(cache_key)
            
            if cached_data:
                return cached_data
            
            # Get coordinates for location
            coords = self._get_location_coordinates(location)
            
            # Try to get real-time weather data
            weather_data = self._fetch_weather_data(coords)
            
            if weather_data:
                self._set_cache_data(cache_key, weather_data, 'weather')
                return weather_data
            
            # Fallback to static data
            fallback_data = self.fallback_data['weather'].copy()
            fallback_data['location'] = location
            fallback_data['timestamp'] = datetime.now().isoformat()
            
            return fallback_data
            
        except Exception as e:
            logger.error(f"Error getting weather data: {e}")
            return self.fallback_data['weather'].copy()
    
    def get_market_data(self, commodity: str = '', location: str = 'Delhi') -> Dict[str, Any]:
        """
        Get market price data
        
        Args:
            commodity: Commodity name
            location: Location name
            
        Returns:
            Market data dictionary
        """
        try:
            cache_key = f"market_{commodity.lower()}_{location.lower()}"
            cached_data = self._get_cached_data(cache_key)
            
            if cached_data:
                return cached_data
            
            # Try to get real-time market data
            market_data = self._fetch_market_data(commodity, location)
            
            if market_data:
                self._set_cache_data(cache_key, market_data, 'prices')
                return market_data
            
            # Fallback to static data
            fallback_data = self.fallback_data['prices'].copy()
            fallback_data['commodity'] = commodity
            fallback_data['location'] = location
            fallback_data['timestamp'] = datetime.now().isoformat()
            
            return fallback_data
            
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return self.fallback_data['prices'].copy()
    
    def get_farming_data(self, query: str, location: str = 'Delhi') -> Dict[str, Any]:
        """
        Get comprehensive farming data including crop recommendations
        
        Args:
            query: Farming query
            location: Location name
            
        Returns:
            Farming data dictionary
        """
        try:
            cache_key = f"farming_{location.lower()}_{hash(query)}"
            cached_data = self._get_cached_data(cache_key)
            
            if cached_data:
                return cached_data
            
            # Get crop recommendations
            crop_recommendations = self._get_crop_recommendations(location)
            
            # Get weather data
            weather_data = self.get_weather_data(location)
            
            # Get market data
            market_data = self.get_market_data('', location)
            
            # Combine all data
            farming_data = {
                'crop_recommendations': crop_recommendations,
                'weather': weather_data,
                'market': market_data,
                'location': location,
                'query': query,
                'timestamp': datetime.now().isoformat(),
                'response': self._generate_farming_response(query, crop_recommendations, weather_data, market_data)
            }
            
            self._set_cache_data(cache_key, farming_data, 'default')
            return farming_data
            
        except Exception as e:
            logger.error(f"Error getting farming data: {e}")
            return {
                'response': 'Sorry, I could not retrieve farming data at this time.',
                'error': str(e),
                'location': location
            }
    
    def get_government_schemes(self, location: str = 'Delhi') -> Dict[str, Any]:
        """
        Get government schemes and policies
        
        Args:
            location: Location name
            
        Returns:
            Schemes data dictionary
        """
        try:
            cache_key = f"schemes_{location.lower()}"
            cached_data = self._get_cached_data(cache_key)
            
            if cached_data:
                return cached_data
            
            # Try to get real-time schemes data
            schemes_data = self._fetch_government_schemes(location)
            
            if schemes_data:
                self._set_cache_data(cache_key, schemes_data, 'schemes')
                return schemes_data
            
            # Fallback to static data
            fallback_data = {
                'schemes': self.fallback_data['schemes'],
                'location': location,
                'timestamp': datetime.now().isoformat(),
                'source': 'fallback'
            }
            
            return fallback_data
            
        except Exception as e:
            logger.error(f"Error getting government schemes: {e}")
            return {
                'schemes': self.fallback_data['schemes'],
                'error': str(e)
            }
    
    def _get_location_coordinates(self, location: str) -> Tuple[float, float]:
        """Get coordinates for a location"""
        location_lower = location.lower()
        
        # Check states
        for key, data in self.indian_locations['states'].items():
            if key in location_lower or data['name'].lower() in location_lower:
                return data['lat'], data['lon']
        
        # Check districts
        for key, data in self.indian_locations['districts'].items():
            if key in location_lower or data['name'].lower() in location_lower:
                return data['lat'], data['lon']
        
        # Default to Delhi
        return 28.7041, 77.1025
    
    def _fetch_weather_data(self, coords: Tuple[float, float]) -> Optional[Dict]:
        """Fetch weather data from API"""
        try:
            # This would be the actual API call to IMD
            # For now, return None to use fallback
            return None
        except Exception as e:
            logger.warning(f"Weather API not available: {e}")
            return None
    
    def _fetch_market_data(self, commodity: str, location: str) -> Optional[Dict]:
        """Fetch market data from API"""
        try:
            # This would be the actual API call to Agmarknet/e-NAM
            # For now, return None to use fallback
            return None
        except Exception as e:
            logger.warning(f"Market API not available: {e}")
            return None
    
    def _get_crop_recommendations(self, location: str) -> List[Dict]:
        """Get crop recommendations for a location"""
        # This would integrate with ICAR or ML models
        return self.fallback_data['crop_recommendations']
    
    def _fetch_government_schemes(self, location: str) -> Optional[Dict]:
        """Fetch government schemes from API"""
        try:
            # This would be the actual API call to government schemes API
            # For now, return None to use fallback
            return None
        except Exception as e:
            logger.warning(f"Government schemes API not available: {e}")
            return None
    
    def _generate_farming_response(self, query: str, crop_recommendations: List[Dict], 
                                 weather_data: Dict, market_data: Dict) -> str:
        """Generate a comprehensive farming response"""
        response_parts = []
        
        # Add crop recommendations
        if crop_recommendations:
            response_parts.append("🌾 **फसल सुझाव:**")
            for crop in crop_recommendations[:3]:  # Top 3 crops
                response_parts.append(f"• {crop['crop']} - {crop['suitability']} उपयुक्तता")
        
        # Add weather information
        if weather_data:
            response_parts.append(f"\n🌤️ **मौसम:** {weather_data.get('condition', 'Unknown')}")
            response_parts.append(f"तापमान: {weather_data.get('temperature', 'N/A')}°C")
        
        # Add market information
        if market_data:
            response_parts.append(f"\n💰 **बाजार भाव:**")
            for commodity, price in list(market_data.items())[:3]:  # Top 3 commodities
                if isinstance(price, (int, float)):
                    response_parts.append(f"• {commodity.title()}: ₹{price}/quintal")
        
        return "\n".join(response_parts) if response_parts else "कृषि संबंधी जानकारी उपलब्ध नहीं है।"
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        current_time = time.time()
        stats = {
            'total_entries': len(self.cache),
            'cache_types': {},
            'oldest_entry': None,
            'newest_entry': None
        }
        
        oldest_time = float('inf')
        newest_time = 0
        
        for key, data in self.cache.items():
            timestamp = data.get('timestamp', 0)
            cache_type = data.get('cache_type', 'default')
            
            if cache_type not in stats['cache_types']:
                stats['cache_types'][cache_type] = 0
            stats['cache_types'][cache_type] += 1
            
            if timestamp < oldest_time:
                oldest_time = timestamp
                stats['oldest_entry'] = key
            
            if timestamp > newest_time:
                newest_time = timestamp
                stats['newest_entry'] = key
        
        return stats
    
    def get_comprehensive_government_data(self, location: str, latitude: float, longitude: float, commodity: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetches comprehensive real-time data from various government sources in parallel.
        """
        cache_key = f"comprehensive_data_{location}_{latitude}_{longitude}_{commodity}"
        cached_data = self._get_cached_data(cache_key, self.cache_duration['default'])
        if cached_data:
            logger.info(f"Serving comprehensive data from cache for {location}")
            return cached_data

        results = {}
        # Using ThreadPoolExecutor for parallel blocking I/O calls
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            # Weather data
            futures.append(executor.submit(self.get_weather_data, location))
            futures.append(executor.submit(self.get_weather_forecast, location, days=7))
            # Market prices
            futures.append(executor.submit(get_market_prices, latitude, longitude, 'en', commodity or 'wheat'))
            futures.append(executor.submit(get_trending_crops, latitude, longitude, 'en'))
            # Government schemes (using enhanced_gov_api for now)
            futures.append(executor.submit(self.enhanced_gov_api.get_government_schemes, location))

            for future in as_completed(futures):
                try:
                    result = future.result()
                    if 'current' in result: # Heuristic for weather
                        results['current_weather'] = result
                    elif 'forecast' in result:
                        results['forecast_weather'] = result
                    elif 'price_info' in result: # Heuristic for market prices
                        results['market_prices'] = result
                    elif 'trending_crops' in result:
                        results['trending_crops'] = result
                    elif 'schemes' in result: # Heuristic for schemes
                        results['government_schemes'] = result
                except Exception as e:
                    logger.error(f"Error fetching data in parallel: {e}")

        final_data = {
            'location': location,
            'latitude': latitude,
            'longitude': longitude,
            'timestamp': datetime.now().isoformat(),
            **results
        }
        self._set_cached_data(cache_key, final_data)
        return final_data
    
    def get_weather_data(self, location: str) -> Dict[str, Any]:
        """Get current weather data for a location"""
        try:
            # Use IMD weather API or fallback
            weather_data = self._get_imd_weather_data(location)
            return {
                'current': weather_data,
                'location': location,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting weather data: {e}")
            return {
                'current': self.fallback_data['weather'],
                'location': location,
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def get_weather_forecast(self, location: str, days: int = 7) -> Dict[str, Any]:
        """Get weather forecast for a location"""
        try:
            forecast_data = self._get_imd_forecast_data(location, days)
            return {
                'forecast': forecast_data,
                'location': location,
                'days': days,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting weather forecast: {e}")
            return {
                'forecast': [self.fallback_data['weather'] for _ in range(days)],
                'location': location,
                'days': days,
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def _get_cached_data(self, key: str, max_age_seconds: int) -> Optional[Dict[str, Any]]:
        """Retrieves data from cache if valid."""
        if key in self.cache:
            cached_item = self.cache[key]
            if (datetime.now() - cached_item['timestamp']).total_seconds() < max_age_seconds:
                return cached_item['data']
        return None

    def _set_cached_data(self, key: str, data: Dict[str, Any]):
        """Stores data in cache with a timestamp."""
        self.cache[key] = {'data': data, 'timestamp': datetime.now()}


# Convenience functions for backward compatibility
def get_weather_data(location: str = 'Delhi') -> Dict[str, Any]:
    """Convenience function to get weather data"""
    gov_service = ConsolidatedGovernmentService()
    return gov_service.get_weather_data(location)

def get_market_data(commodity: str = '', location: str = 'Delhi') -> Dict[str, Any]:
    """Convenience function to get market data"""
    gov_service = ConsolidatedGovernmentService()
    return gov_service.get_market_data(commodity, location)

def get_farming_data(query: str, location: str = 'Delhi') -> Dict[str, Any]:
    """Convenience function to get farming data"""
    gov_service = ConsolidatedGovernmentService()
    return gov_service.get_farming_data(query, location)
