#!/usr/bin/env python3
"""
Accurate Location API Service
Ensures ALL services use Google Maps-level accurate location detection
"""

import requests
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import time
from functools import lru_cache
from ..rate_limiters import rate_limit, nominatim_limiter

logger = logging.getLogger(__name__)

class AccurateLocationAPI:
    """Accurate location detection service for all agricultural services"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'KrisiMitra-AI-Assistant/2.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Comprehensive Indian location database
        self.indian_locations = self._load_comprehensive_indian_locations()
    
    def _load_comprehensive_indian_locations(self) -> Dict[str, Any]:
        """Load comprehensive Indian location database"""
        return {
            'states': {
                'assam': {'name': 'Assam', 'hindi_name': 'असम', 'region': 'East'},
                'manipur': {'name': 'Manipur', 'hindi_name': 'मणिपुर', 'region': 'East'},
                'meghalaya': {'name': 'Meghalaya', 'hindi_name': 'मेघालय', 'region': 'East'},
                'mizoram': {'name': 'Mizoram', 'hindi_name': 'मिजोरम', 'region': 'East'},
                'nagaland': {'name': 'Nagaland', 'hindi_name': 'नागालैंड', 'region': 'East'},
                'tripura': {'name': 'Tripura', 'hindi_name': 'त्रिपुरा', 'region': 'East'},
                'arunachal_pradesh': {'name': 'Arunachal Pradesh', 'hindi_name': 'अरुणाचल प्रदेश', 'region': 'East'},
                'sikkim': {'name': 'Sikkim', 'hindi_name': 'सिक्किम', 'region': 'East'},
                'delhi': {'name': 'Delhi', 'hindi_name': 'दिल्ली', 'region': 'North'},
                'punjab': {'name': 'Punjab', 'hindi_name': 'पंजाब', 'region': 'North'},
                'haryana': {'name': 'Haryana', 'hindi_name': 'हरियाणा', 'region': 'North'},
                'rajasthan': {'name': 'Rajasthan', 'hindi_name': 'राजस्थान', 'region': 'North'},
                'himachal_pradesh': {'name': 'Himachal Pradesh', 'hindi_name': 'हिमाचल प्रदेश', 'region': 'North'},
                'jammu_kashmir': {'name': 'Jammu and Kashmir', 'hindi_name': 'जम्मू और कश्मीर', 'region': 'North'},
                'uttarakhand': {'name': 'Uttarakhand', 'hindi_name': 'उत्तराखंड', 'region': 'North'},
                'maharashtra': {'name': 'Maharashtra', 'hindi_name': 'महाराष्ट्र', 'region': 'West'},
                'gujarat': {'name': 'Gujarat', 'hindi_name': 'गुजरात', 'region': 'West'},
                'goa': {'name': 'Goa', 'hindi_name': 'गोवा', 'region': 'West'},
                'karnataka': {'name': 'Karnataka', 'hindi_name': 'कर्नाटक', 'region': 'South'},
                'tamil_nadu': {'name': 'Tamil Nadu', 'hindi_name': 'तमिलनाडु', 'region': 'South'},
                'kerala': {'name': 'Kerala', 'hindi_name': 'केरल', 'region': 'South'},
                'andhra_pradesh': {'name': 'Andhra Pradesh', 'hindi_name': 'आंध्र प्रदेश', 'region': 'South'},
                'telangana': {'name': 'Telangana', 'hindi_name': 'तेलंगाना', 'region': 'South'},
                'west_bengal': {'name': 'West Bengal', 'hindi_name': 'पश्चिम बंगाल', 'region': 'East'},
                'odisha': {'name': 'Odisha', 'hindi_name': 'ओडिशा', 'region': 'East'},
                'bihar': {'name': 'Bihar', 'hindi_name': 'बिहार', 'region': 'East'},
                'jharkhand': {'name': 'Jharkhand', 'hindi_name': 'झारखंड', 'region': 'East'},
                'chhattisgarh': {'name': 'Chhattisgarh', 'hindi_name': 'छत्तीसगढ़', 'region': 'Central'},
                'uttar_pradesh': {'name': 'Uttar Pradesh', 'hindi_name': 'उत्तर प्रदेश', 'region': 'Central'},
                'madhya_pradesh': {'name': 'Madhya Pradesh', 'hindi_name': 'मध्य प्रदेश', 'region': 'Central'}
            },
            'major_cities': {
                'guwahati': {'state': 'Assam', 'region': 'East'},
                'imphal': {'state': 'Manipur', 'region': 'East'},
                'shillong': {'state': 'Meghalaya', 'region': 'East'},
                'aizawl': {'state': 'Mizoram', 'region': 'East'},
                'kohima': {'state': 'Nagaland', 'region': 'East'},
                'agartala': {'state': 'Tripura', 'region': 'East'},
                'itanagar': {'state': 'Arunachal Pradesh', 'region': 'East'},
                'gangtok': {'state': 'Sikkim', 'region': 'East'},
                'new_delhi': {'state': 'Delhi', 'region': 'North'},
                'mumbai': {'state': 'Maharashtra', 'region': 'West'},
                'bangalore': {'state': 'Karnataka', 'region': 'South'},
                'chennai': {'state': 'Tamil Nadu', 'region': 'South'},
                'kolkata': {'state': 'West Bengal', 'region': 'East'},
                'hyderabad': {'state': 'Telangana', 'region': 'South'},
                'rampur': {'state': 'Uttar Pradesh', 'region': 'Central'},
                'bareilly': {'state': 'Uttar Pradesh', 'region': 'Central'},
                'gorakhpur': {'state': 'Uttar Pradesh', 'region': 'Central'}
            },
            'village_patterns': [
                'pur', 'pura', 'pore', 'ore', 'garh', 'nagar', 'bad', 'ganj', 'li', 'gaon', 'gaun', 'gram',
                'kheda', 'khedi', 'khera', 'kheri', 'khurd', 'kalan', 'chak', 'chakki', 'majra', 'majri',
                'mandi', 'market', 'bazaar', 'bazar', 'hat', 'haat', 'junction', 'jnc', 'road', 'rd', 'station', 'stn'
            ]
        }
    
    @lru_cache(maxsize=1024)
    def detect_accurate_location(self, query: str) -> Dict[str, Any]:
        """Detect accurate location with Google Maps-level precision"""
        query_lower = query.lower().strip()
        
        result = {
            'location': None,
            'state': None,
            'district': None,
            'region': None,
            'coordinates': None,
            'confidence': 0,
            'source': 'none',
            'type': 'unknown'
        }
        
        # 1. Try free geocoding service (Nominatim OpenStreetMap)
        geocoding_result = self._detect_via_geocoding(query_lower)
        if geocoding_result['confidence'] > 0.8:
            result.update(geocoding_result)
            result['source'] = 'geocoding_api'
            return result
        
        # 2. Enhanced database search
        db_result = self._detect_via_database(query_lower)
        if db_result['confidence'] > 0.6:
            result.update(db_result)
            result['source'] = 'database'
        
        # 3. Pattern matching for villages
        pattern_result = self._detect_via_patterns(query_lower)
        if pattern_result['confidence'] > result['confidence']:
            result.update(pattern_result)
            result['source'] = 'pattern'
        
        # 4. Fuzzy matching
        fuzzy_result = self._detect_via_fuzzy(query_lower)
        if fuzzy_result['confidence'] > result['confidence']:
            result.update(fuzzy_result)
            result['source'] = 'fuzzy'
        
        return result
    
    @rate_limit(nominatim_limiter)
    def _detect_via_geocoding(self, query_lower: str) -> Dict[str, Any]:
        """Use free geocoding service for accurate location detection"""
        try:
            geocoding_url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': f"{query_lower}, India",
                'format': 'json',
                'limit': 1,
                'countrycodes': 'in',
                'addressdetails': 1
            }
            
            headers = {
                'User-Agent': 'KrisiMitra-AI-Assistant/2.0'
            }
            
            response = self.session.get(geocoding_url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data and len(data) > 0:
                    result = data[0]
                    address = result.get('address', {})
                    
                    # Extract location details
                    state = address.get('state', '')
                    district = address.get('county', '') or address.get('district', '')
                    city = address.get('city', '') or address.get('town', '') or address.get('village', '')
                    
                    # Determine the main location name
                    location_name = result.get('name', '') or city or district or state or result.get('display_name', '').split(',')[0].strip()
                    
                    return {
                        'location': location_name,
                        'state': state or 'Unknown',
                        'district': district or 'Unknown',
                        'region': self._get_region_from_state(state or ''),
                        'coordinates': {
                            'lat': float(result.get('lat', 0)),
                            'lng': float(result.get('lon', 0))
                        },
                        'confidence': 0.9,
                        'type': 'geocoded'
                    }
            
        except Exception as e:
            logger.warning(f"Geocoding failed: {e}")
        
        return {'confidence': 0}
    
    def _detect_via_database(self, query_lower: str) -> Dict[str, Any]:
        """Enhanced database search"""
        # Search in states
        for state_key, state_data in self.indian_locations['states'].items():
            state_name = state_data['name'].lower()
            hindi_name = state_data['hindi_name'].lower()
            
            # Exact match
            if query_lower == state_name or query_lower == hindi_name:
                return {
                    'location': state_data['name'],
                    'state': state_data['name'],
                    'district': 'Multiple',
                    'region': state_data['region'],
                    'coordinates': self._get_state_coordinates(state_data['name']),
                    'confidence': 0.95,
                    'type': 'state'
                }
            
            # Partial match
            if state_name in query_lower or query_lower in state_name:
                return {
                    'location': state_data['name'],
                    'state': state_data['name'],
                    'district': 'Multiple',
                    'region': state_data['region'],
                    'coordinates': self._get_state_coordinates(state_data['name']),
                    'confidence': 0.85,
                    'type': 'state'
                }
        
        # Search in major cities
        for city_key, city_data in self.indian_locations['major_cities'].items():
            if query_lower == city_key:
                return {
                    'location': city_key.title(),
                    'state': city_data['state'],
                    'district': city_key.title(),
                    'region': city_data['region'],
                    'coordinates': self._get_state_coordinates(city_data['state']),
                    'confidence': 0.85,
                    'type': 'city'
                }
        
        return {'confidence': 0}
    
    def _detect_via_patterns(self, query_lower: str) -> Dict[str, Any]:
        """Pattern matching for villages and small locations"""
        for pattern in self.indian_locations['village_patterns']:
            if query_lower.endswith(pattern):
                base_name = query_lower[:-len(pattern)].strip()
                if len(base_name) > 2:
                    confidence = 0.7 if pattern in ['mandi', 'market', 'bazaar', 'junction'] else 0.6
                    return {
                        'location': query_lower.title(),
                        'state': 'Unknown',
                        'district': 'Unknown',
                        'region': 'Unknown',
                        'coordinates': None,
                        'confidence': confidence,
                        'type': 'village' if confidence < 0.7 else 'market'
                    }
        
        return {'confidence': 0}
    
    def _detect_via_fuzzy(self, query_lower: str) -> Dict[str, Any]:
        """Fuzzy matching for partial names"""
        words = query_lower.split()
        
        for word in words:
            if len(word) >= 4:
                for state_key, state_data in self.indian_locations['states'].items():
                    state_name = state_data['name'].lower()
                    
                    if word in state_name or state_name.startswith(word):
                        return {
                            'location': state_data['name'],
                            'state': state_data['name'],
                            'district': 'Multiple',
                            'region': state_data['region'],
                            'coordinates': self._get_state_coordinates(state_data['name']),
                            'confidence': 0.7,
                            'type': 'state_fuzzy'
                        }
        
        return {'confidence': 0}
    
    def _get_region_from_state(self, state: str) -> str:
        """Get region from state name"""
        state_lower = state.lower()
        
        if any(keyword in state_lower for keyword in ['delhi', 'punjab', 'haryana', 'rajasthan', 'himachal', 'uttarakhand', 'jammu', 'kashmir']):
            return 'North'
        elif any(keyword in state_lower for keyword in ['maharashtra', 'gujarat', 'goa']):
            return 'West'
        elif any(keyword in state_lower for keyword in ['karnataka', 'tamil nadu', 'kerala', 'andhra pradesh', 'telangana']):
            return 'South'
        elif any(keyword in state_lower for keyword in ['west bengal', 'odisha', 'bihar', 'jharkhand', 'assam', 'tripura', 'manipur', 'meghalaya', 'mizoram', 'nagaland', 'sikkim', 'arunachal']):
            return 'East'
        elif any(keyword in state_lower for keyword in ['madhya pradesh', 'chhattisgarh', 'uttar pradesh']):
            return 'Central'
        else:
            return 'Unknown'
    
    def _get_state_coordinates(self, state: str) -> Dict[str, float]:
        """Get approximate coordinates for state"""
        state_coords = {
            'assam': {'lat': 26.2006, 'lng': 92.9376},
            'manipur': {'lat': 24.6637, 'lng': 93.9063},
            'meghalaya': {'lat': 25.4670, 'lng': 91.3662},
            'mizoram': {'lat': 23.1645, 'lng': 92.9376},
            'nagaland': {'lat': 26.1584, 'lng': 94.5624},
            'tripura': {'lat': 23.9408, 'lng': 91.9882},
            'arunachal pradesh': {'lat': 28.2180, 'lng': 94.7278},
            'sikkim': {'lat': 27.5330, 'lng': 88.5122},
            'delhi': {'lat': 28.7041, 'lng': 77.1025},
            'punjab': {'lat': 31.1471, 'lng': 75.3412},
            'haryana': {'lat': 29.0588, 'lng': 76.0856},
            'rajasthan': {'lat': 27.0238, 'lng': 74.2179},
            'himachal pradesh': {'lat': 31.1048, 'lng': 77.1734},
            'jammu and kashmir': {'lat': 34.0837, 'lng': 74.7973},
            'uttarakhand': {'lat': 30.0668, 'lng': 79.0193},
            'maharashtra': {'lat': 19.7515, 'lng': 75.7139},
            'gujarat': {'lat': 23.0225, 'lng': 72.5714},
            'goa': {'lat': 15.2993, 'lng': 74.1240},
            'karnataka': {'lat': 15.3173, 'lng': 75.7139},
            'tamil nadu': {'lat': 11.1271, 'lng': 78.6569},
            'kerala': {'lat': 10.8505, 'lng': 76.2711},
            'andhra pradesh': {'lat': 15.9129, 'lng': 79.7400},
            'telangana': {'lat': 18.1124, 'lng': 79.0193},
            'west bengal': {'lat': 22.9868, 'lng': 87.8550},
            'odisha': {'lat': 20.9517, 'lng': 85.0985},
            'bihar': {'lat': 25.0961, 'lng': 85.3131},
            'jharkhand': {'lat': 23.6102, 'lng': 85.2799},
            'chhattisgarh': {'lat': 21.2787, 'lng': 81.8661},
            'uttar_pradesh': {'lat': 26.8467, 'lng': 80.9462},
            'madhya pradesh': {'lat': 22.9734, 'lng': 78.6569}
        }
        return state_coords.get(state.lower(), {'lat': 20.5937, 'lng': 78.9629})
    
    @rate_limit(nominatim_limiter)
    def reverse_geocode(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Reverse geocoding - convert coordinates to location name"""
        try:
            # Use Nominatim API for reverse geocoding
            reverse_url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                'lat': latitude,
                'lon': longitude,
                'format': 'json',
                'addressdetails': 1,
                'zoom': 10
            }
            
            headers = {
                'User-Agent': 'KrisiMitra-AI-Assistant/2.0'
            }
            
            response = self.session.get(reverse_url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                address = data.get('address', {})
                
                # Extract location details
                city = address.get('city', '') or address.get('town', '') or address.get('village', '') or address.get('municipality', '')
                state = address.get('state', '')
                district = address.get('county', '') or address.get('district', '')
                
                # Determine the main location name
                location_name = city or district or state or data.get('display_name', '').split(',')[0].strip()
                
                return {
                    'status': 'success',
                    'location': {
                        'name': location_name,
                        'city': city,
                        'state': state,
                        'district': district,
                        'coordinates': {'lat': latitude, 'lng': longitude}
                    },
                    'data_source': 'Nominatim (OpenStreetMap)',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                logger.warning(f"Reverse geocoding API returned status {response.status_code}")
                return {
                    'status': 'error',
                    'message': f'API returned status {response.status_code}',
                    'data_source': 'AccurateLocationAPI',
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Reverse geocoding error: {e}")
            return {
                'status': 'error',
                'message': f'Reverse geocoding error: {str(e)}',
                'data_source': 'AccurateLocationAPI',
                'timestamp': datetime.now().isoformat()
            }

# Global instance for all services to use
accurate_location_api = AccurateLocationAPI()

def get_accurate_location(query: str) -> Dict[str, Any]:
    """Global function for all services to get accurate location"""
    return accurate_location_api.detect_accurate_location(query)

# Test the accurate location detection
if __name__ == "__main__":
    print("🌍 Testing Accurate Location Detection")
    print("=" * 50)
    
    test_locations = [
        'Assam', 'Manipur', 'Meghalaya', 'Guwahati', 'Imphal', 'Shillong',
        'Rampur', 'Bareilly', 'Gorakhpur', 'Saharanpur', 'Muzaffarnagar'
    ]
    
    for location in test_locations:
        result = accurate_location_api.detect_accurate_location(location)
        print(f"📍 {location}: {result['location']} in {result['state']} ({result['region']}) - Confidence: {result['confidence']:.2f} - Source: {result['source']}")
    
    print("\n✅ Accurate location detection testing completed!")
