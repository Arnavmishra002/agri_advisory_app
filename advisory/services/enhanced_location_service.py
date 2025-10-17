#!/usr/bin/env python3
"""
Enhanced Auto-Location Detection Service for Krishimitra AI
Similar to Swiggy, Blinkit, Rapido with GPS, IP, and manual location detection
"""

import os
import sys
import json
import time
import requests
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger(__name__)

class EnhancedLocationService:
    """Enhanced location detection service like Swiggy/Blinkit/Rapido"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Krishimitra-AI/1.0 (Agricultural Advisory)',
            'Accept': 'application/json'
        })
        
        # Location detection methods (in order of preference)
        self.detection_methods = [
            'gps',
            'ip_geolocation', 
            'manual_selection',
            'default_location'
        ]
        
        # Comprehensive Indian locations database - ALL major cities, towns, and villages
        self.default_locations = {
            # METRO CITIES
            'delhi': {'lat': 28.6139, 'lon': 77.2090, 'city': 'Delhi', 'state': 'Delhi', 'region': 'North'},
            'mumbai': {'lat': 19.0760, 'lon': 72.8777, 'city': 'Mumbai', 'state': 'Maharashtra', 'region': 'West'},
            'bangalore': {'lat': 12.9716, 'lon': 77.5946, 'city': 'Bangalore', 'state': 'Karnataka', 'region': 'South'},
            'kolkata': {'lat': 22.5726, 'lon': 88.3639, 'city': 'Kolkata', 'state': 'West Bengal', 'region': 'East'},
            'chennai': {'lat': 13.0827, 'lon': 80.2707, 'city': 'Chennai', 'state': 'Tamil Nadu', 'region': 'South'},
            'hyderabad': {'lat': 17.3850, 'lon': 78.4867, 'city': 'Hyderabad', 'state': 'Telangana', 'region': 'South'},
            'pune': {'lat': 18.5204, 'lon': 73.8567, 'city': 'Pune', 'state': 'Maharashtra', 'region': 'West'},
            'ahmedabad': {'lat': 23.0225, 'lon': 72.5714, 'city': 'Ahmedabad', 'state': 'Gujarat', 'region': 'West'},
            'jaipur': {'lat': 26.9124, 'lon': 75.7873, 'city': 'Jaipur', 'state': 'Rajasthan', 'region': 'North'},
            'lucknow': {'lat': 26.8467, 'lon': 80.9462, 'city': 'Lucknow', 'state': 'Uttar Pradesh', 'region': 'North'},
            
            # MAJOR CITIES
            'kanpur': {'lat': 26.4499, 'lon': 80.3319, 'city': 'Kanpur', 'state': 'Uttar Pradesh', 'region': 'North'},
            'nagpur': {'lat': 21.1458, 'lon': 79.0882, 'city': 'Nagpur', 'state': 'Maharashtra', 'region': 'West'},
            'indore': {'lat': 22.7196, 'lon': 75.8577, 'city': 'Indore', 'state': 'Madhya Pradesh', 'region': 'Central'},
            'bhopal': {'lat': 23.2599, 'lon': 77.4126, 'city': 'Bhopal', 'state': 'Madhya Pradesh', 'region': 'Central'},
            'visakhapatnam': {'lat': 17.6868, 'lon': 83.2185, 'city': 'Visakhapatnam', 'state': 'Andhra Pradesh', 'region': 'South'},
            'coimbatore': {'lat': 11.0168, 'lon': 76.9558, 'city': 'Coimbatore', 'state': 'Tamil Nadu', 'region': 'South'},
            'kochi': {'lat': 9.9312, 'lon': 76.2673, 'city': 'Kochi', 'state': 'Kerala', 'region': 'South'},
            'thiruvananthapuram': {'lat': 8.5241, 'lon': 76.9366, 'city': 'Thiruvananthapuram', 'state': 'Kerala', 'region': 'South'},
            'mysore': {'lat': 12.2958, 'lon': 76.6394, 'city': 'Mysore', 'state': 'Karnataka', 'region': 'South'},
            'madurai': {'lat': 9.9252, 'lon': 78.1198, 'city': 'Madurai', 'state': 'Tamil Nadu', 'region': 'South'},
            'salem': {'lat': 11.6643, 'lon': 78.1460, 'city': 'Salem', 'state': 'Tamil Nadu', 'region': 'South'},
            'tiruchirapalli': {'lat': 10.7905, 'lon': 78.7047, 'city': 'Tiruchirapalli', 'state': 'Tamil Nadu', 'region': 'South'},
            'tirunelveli': {'lat': 8.7139, 'lon': 77.7567, 'city': 'Tirunelveli', 'state': 'Tamil Nadu', 'region': 'South'},
            
            # UNION TERRITORIES & CAPITALS
            'chandigarh': {'lat': 30.7333, 'lon': 76.7794, 'city': 'Chandigarh', 'state': 'Chandigarh', 'region': 'North'},
            'dehradun': {'lat': 30.3165, 'lon': 78.0322, 'city': 'Dehradun', 'state': 'Uttarakhand', 'region': 'North'},
            'shimla': {'lat': 31.1048, 'lon': 77.1734, 'city': 'Shimla', 'state': 'Himachal Pradesh', 'region': 'North'},
            'srinagar': {'lat': 34.0837, 'lon': 74.7973, 'city': 'Srinagar', 'state': 'Jammu and Kashmir', 'region': 'North'},
            'jammu': {'lat': 32.7266, 'lon': 74.8570, 'city': 'Jammu', 'state': 'Jammu and Kashmir', 'region': 'North'},
            'leh': {'lat': 34.1526, 'lon': 77.5771, 'city': 'Leh', 'state': 'Ladakh', 'region': 'North'},
            'gangtok': {'lat': 27.3314, 'lon': 88.6138, 'city': 'Gangtok', 'state': 'Sikkim', 'region': 'North'},
            'itanagar': {'lat': 27.0844, 'lon': 93.6053, 'city': 'Itanagar', 'state': 'Arunachal Pradesh', 'region': 'North'},
            'kohima': {'lat': 25.6751, 'lon': 94.1086, 'city': 'Kohima', 'state': 'Nagaland', 'region': 'North'},
            'aizawl': {'lat': 23.7271, 'lon': 92.7176, 'city': 'Aizawl', 'state': 'Mizoram', 'region': 'North'},
            'imphal': {'lat': 24.8170, 'lon': 93.9368, 'city': 'Imphal', 'state': 'Manipur', 'region': 'North'},
            'shillong': {'lat': 25.5788, 'lon': 91.8933, 'city': 'Shillong', 'state': 'Meghalaya', 'region': 'North'},
            'agartala': {'lat': 23.8315, 'lon': 91.2862, 'city': 'Agartala', 'state': 'Tripura', 'region': 'North'},
            'guwahati': {'lat': 26.1445, 'lon': 91.7362, 'city': 'Guwahati', 'state': 'Assam', 'region': 'North'},
            'dispur': {'lat': 26.1433, 'lon': 91.7898, 'city': 'Dispur', 'state': 'Assam', 'region': 'North'},
            'patna': {'lat': 25.5941, 'lon': 85.1376, 'city': 'Patna', 'state': 'Bihar', 'region': 'East'},
            'ranchi': {'lat': 23.3441, 'lon': 85.3096, 'city': 'Ranchi', 'state': 'Jharkhand', 'region': 'East'},
            'bhubaneswar': {'lat': 20.2961, 'lon': 85.8245, 'city': 'Bhubaneswar', 'state': 'Odisha', 'region': 'East'},
            'raipur': {'lat': 21.2514, 'lon': 81.6296, 'city': 'Raipur', 'state': 'Chhattisgarh', 'region': 'Central'},
            'gandhinagar': {'lat': 23.2156, 'lon': 72.6369, 'city': 'Gandhinagar', 'state': 'Gujarat', 'region': 'West'},
            'panaji': {'lat': 15.4909, 'lon': 73.8278, 'city': 'Panaji', 'state': 'Goa', 'region': 'West'},
            
            # MAJOR TOWNS & CITIES
            'nashik': {'lat': 19.9975, 'lon': 73.7898, 'city': 'Nashik', 'state': 'Maharashtra', 'region': 'West'},
            'aurangabad': {'lat': 19.8762, 'lon': 75.3433, 'city': 'Aurangabad', 'state': 'Maharashtra', 'region': 'West'},
            'solapur': {'lat': 17.6599, 'lon': 75.9064, 'city': 'Solapur', 'state': 'Maharashtra', 'region': 'West'},
            'kolhapur': {'lat': 16.7050, 'lon': 74.2433, 'city': 'Kolhapur', 'state': 'Maharashtra', 'region': 'West'},
            'sangli': {'lat': 16.8524, 'lon': 74.5815, 'city': 'Sangli', 'state': 'Maharashtra', 'region': 'West'},
            'ratnagiri': {'lat': 16.9944, 'lon': 73.3002, 'city': 'Ratnagiri', 'state': 'Maharashtra', 'region': 'West'},
            'satara': {'lat': 17.6805, 'lon': 74.0183, 'city': 'Satara', 'state': 'Maharashtra', 'region': 'West'},
            'sindhudurg': {'lat': 16.1667, 'lon': 73.7500, 'city': 'Sindhudurg', 'state': 'Maharashtra', 'region': 'West'},
            'chandigarh': {'lat': 30.7333, 'lon': 76.7794, 'city': 'Chandigarh', 'state': 'Punjab', 'region': 'North'},
            'kochi': {'lat': 9.9312, 'lon': 76.2673, 'city': 'Kochi', 'state': 'Kerala', 'region': 'South'},
            'bhubaneswar': {'lat': 20.2961, 'lon': 85.8245, 'city': 'Bhubaneswar', 'state': 'Odisha', 'region': 'East'},
            'indore': {'lat': 22.7196, 'lon': 75.8577, 'city': 'Indore', 'state': 'Madhya Pradesh', 'region': 'Central'},
            'patna': {'lat': 25.5941, 'lon': 85.1376, 'city': 'Patna', 'state': 'Bihar', 'region': 'East'}
        }
        
        # Current detected location
        self.current_location = None
        self.location_history = []
        
        logger.info("Enhanced Location Service initialized")
    
    def detect_location_gps(self, lat: float = None, lon: float = None) -> Optional[Dict[str, Any]]:
        """Detect location using GPS coordinates (like Swiggy/Blinkit)"""
        try:
            if lat is None or lon is None:
                logger.info("GPS coordinates not provided")
                return None
            
            # Validate coordinates
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                logger.warning(f"Invalid GPS coordinates: {lat}, {lon}")
                return None
            
            # Use reverse geocoding to get location details
            location_data = self._reverse_geocode(lat, lon)
            
            if location_data:
                location_data.update({
                    'detection_method': 'gps',
                    'accuracy': 'high',
                    'timestamp': datetime.now().isoformat(),
                    'coordinates': {'lat': lat, 'lon': lon}
                })
                
                logger.info(f"GPS location detected: {location_data['city']}, {location_data['state']}")
                return location_data
            
        except Exception as e:
            logger.error(f"GPS location detection error: {e}")
        
        return None
    
    def detect_location_ip(self) -> Optional[Dict[str, Any]]:
        """Detect location using IP geolocation (like Swiggy/Blinkit)"""
        try:
            # Use multiple IP geolocation services for better accuracy
            ip_services = [
                'http://ip-api.com/json/',
                'https://ipapi.co/json/',
                'https://api.ipgeolocation.io/ipgeo?apiKey=demo'
            ]
            
            for service_url in ip_services:
                try:
                    response = self.session.get(service_url, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Parse different response formats
                        if 'ip-api.com' in service_url:
                            location_data = self._parse_ipapi_response(data)
                        elif 'ipapi.co' in service_url:
                            location_data = self._parse_ipapi_co_response(data)
                        elif 'ipgeolocation.io' in service_url:
                            location_data = self._parse_ipgeolocation_response(data)
                        
                        if location_data and location_data.get('country') == 'India':
                            location_data.update({
                                'detection_method': 'ip_geolocation',
                                'accuracy': 'medium',
                                'timestamp': datetime.now().isoformat()
                            })
                            
                            logger.info(f"IP location detected: {location_data['city']}, {location_data['state']}")
                            return location_data
                            
                except Exception as e:
                    logger.warning(f"IP service {service_url} failed: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"IP location detection error: {e}")
        
        return None
    
    def detect_location_manual(self, city_name: str = None, state_name: str = None) -> Optional[Dict[str, Any]]:
        """Detect location using manual city/state selection (like Swiggy/Blinkit)"""
        try:
            if not city_name:
                return None
            
            # Normalize city name
            city_key = city_name.lower().strip()
            
            # Direct match
            if city_key in self.default_locations:
                location_data = self.default_locations[city_key].copy()
                location_data.update({
                    'detection_method': 'manual_selection',
                    'accuracy': 'high',
                    'timestamp': datetime.now().isoformat(),
                    'user_input': {'city': city_name, 'state': state_name}
                })
                
                logger.info(f"Manual location detected: {location_data['city']}, {location_data['state']}")
                return location_data
            
            # Fuzzy match for similar city names
            for key, location in self.default_locations.items():
                if (city_key in key or key in city_key or 
                    city_name.lower() in location['city'].lower() or
                    location['city'].lower() in city_name.lower()):
                    
                    location_data = location.copy()
                    location_data.update({
                        'detection_method': 'manual_selection',
                        'accuracy': 'medium',
                        'timestamp': datetime.now().isoformat(),
                        'user_input': {'city': city_name, 'state': state_name},
                        'matched_city': location['city']
                    })
                    
                    logger.info(f"Manual location fuzzy matched: {city_name} -> {location_data['city']}")
                    return location_data
            
        except Exception as e:
            logger.error(f"Manual location detection error: {e}")
        
        return None
    
    def detect_location_default(self) -> Dict[str, Any]:
        """Fallback to default location (Delhi)"""
        location_data = self.default_locations['delhi'].copy()
        location_data.update({
            'detection_method': 'default_location',
            'accuracy': 'low',
            'timestamp': datetime.now().isoformat(),
            'fallback_reason': 'No other detection method succeeded'
        })
        
        logger.info(f"Using default location: {location_data['city']}, {location_data['state']}")
        return location_data
    
    def auto_detect_location(self, gps_lat: float = None, gps_lon: float = None, 
                           manual_city: str = None, manual_state: str = None) -> Dict[str, Any]:
        """Auto-detect location using multiple methods (like Swiggy/Blinkit/Rapido)"""
        
        logger.info("Starting auto location detection...")
        
        # Try GPS first (most accurate)
        if gps_lat and gps_lon:
            location = self.detect_location_gps(gps_lat, gps_lon)
            if location:
                self.current_location = location
                self.location_history.append(location)
                return location
        
        # Try manual selection (user specified)
        if manual_city:
            location = self.detect_location_manual(manual_city, manual_state)
            if location:
                self.current_location = location
                self.location_history.append(location)
                return location
        
        # Try IP geolocation
        location = self.detect_location_ip()
        if location:
            self.current_location = location
            self.location_history.append(location)
            return location
        
        # Fallback to default
        location = self.detect_location_default()
        self.current_location = location
        self.location_history.append(location)
        return location
    
    def get_current_location(self) -> Optional[Dict[str, Any]]:
        """Get current detected location"""
        return self.current_location
    
    def update_location(self, lat: float, lon: float) -> Dict[str, Any]:
        """Update location (like changing location in Swiggy/Blinkit)"""
        logger.info(f"Updating location to: {lat}, {lon}")
        
        location = self.detect_location_gps(lat, lon)
        if location:
            self.current_location = location
            self.location_history.append(location)
            logger.info(f"Location updated to: {location['city']}, {location['state']}")
            return location
        
        # Fallback to default if GPS detection fails
        return self.detect_location_default()
    
    def get_location_history(self) -> List[Dict[str, Any]]:
        """Get location detection history"""
        return self.location_history
    
    def _reverse_geocode(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Reverse geocoding to get location details from coordinates"""
        try:
            # Use OpenStreetMap Nominatim for reverse geocoding
            url = f"https://nominatim.openstreetmap.org/reverse"
            params = {
                'lat': lat,
                'lon': lon,
                'format': 'json',
                'addressdetails': 1,
                'zoom': 10
            }
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                if 'address' in data:
                    address = data['address']
                    
                    # Extract location details
                    city = (address.get('city') or 
                           address.get('town') or 
                           address.get('village') or 
                           address.get('suburb', 'Unknown'))
                    
                    state = (address.get('state') or 
                            address.get('province') or 
                            'Unknown')
                    
                    country = address.get('country', 'Unknown')
                    
                    if country.lower() == 'india':
                        # Determine region based on state
                        region = self._get_region_from_state(state)
                        
                        return {
                            'city': city,
                            'state': state,
                            'country': country,
                            'region': region,
                            'coordinates': {'lat': lat, 'lon': lon},
                            'address': data.get('display_name', ''),
                            'source': 'OpenStreetMap Nominatim'
                        }
            
        except Exception as e:
            logger.error(f"Reverse geocoding error: {e}")
        
        return None
    
    def _get_region_from_state(self, state: str) -> str:
        """Determine region based on state name"""
        state_lower = state.lower()
        
        if any(keyword in state_lower for keyword in ['delhi', 'punjab', 'haryana', 'rajasthan', 'himachal', 'uttarakhand', 'jammu', 'kashmir']):
            return 'North'
        elif any(keyword in state_lower for keyword in ['maharashtra', 'gujarat', 'goa', 'dadra', 'nagar']):
            return 'West'
        elif any(keyword in state_lower for keyword in ['karnataka', 'tamil nadu', 'kerala', 'andhra pradesh', 'telangana']):
            return 'South'
        elif any(keyword in state_lower for keyword in ['west bengal', 'odisha', 'bihar', 'jharkhand', 'assam', 'tripura', 'manipur', 'meghalaya', 'mizoram', 'nagaland', 'sikkim', 'arunachal']):
            return 'East'
        elif any(keyword in state_lower for keyword in ['madhya pradesh', 'chhattisgarh', 'uttar pradesh']):
            return 'Central'
        else:
            return 'Unknown'
    
    def _parse_ipapi_response(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse ip-api.com response"""
        try:
            if data.get('status') == 'success':
                return {
                    'city': data.get('city', 'Unknown'),
                    'state': data.get('regionName', 'Unknown'),
                    'country': data.get('country', 'Unknown'),
                    'coordinates': {
                        'lat': data.get('lat', 0),
                        'lon': data.get('lon', 0)
                    },
                    'source': 'ip-api.com'
                }
        except Exception as e:
            logger.error(f"Error parsing ip-api response: {e}")
        return None
    
    def _parse_ipapi_co_response(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse ipapi.co response"""
        try:
            return {
                'city': data.get('city', 'Unknown'),
                'state': data.get('region', 'Unknown'),
                'country': data.get('country_name', 'Unknown'),
                'coordinates': {
                    'lat': data.get('latitude', 0),
                    'lon': data.get('longitude', 0)
                },
                'source': 'ipapi.co'
            }
        except Exception as e:
            logger.error(f"Error parsing ipapi.co response: {e}")
        return None
    
    def _parse_ipgeolocation_response(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse ipgeolocation.io response"""
        try:
            return {
                'city': data.get('city', 'Unknown'),
                'state': data.get('state_prov', 'Unknown'),
                'country': data.get('country_name', 'Unknown'),
                'coordinates': {
                    'lat': data.get('latitude', 0),
                    'lon': data.get('longitude', 0)
                },
                'source': 'ipgeolocation.io'
            }
        except Exception as e:
            logger.error(f"Error parsing ipgeolocation response: {e}")
        return None
    
    def get_nearby_locations(self, radius_km: float = 50) -> List[Dict[str, Any]]:
        """Get nearby locations within radius (like Swiggy/Blinkit)"""
        if not self.current_location:
            return []
        
        current_lat = self.current_location['coordinates']['lat']
        current_lon = self.current_location['coordinates']['lon']
        
        nearby_locations = []
        
        for key, location in self.default_locations.items():
            lat = location['lat']
            lon = location['lon']
            
            # Calculate distance (simple approximation)
            distance = self._calculate_distance(current_lat, current_lon, lat, lon)
            
            if distance <= radius_km:
                location_copy = location.copy()
                location_copy['distance_km'] = distance
                nearby_locations.append(location_copy)
        
        # Sort by distance
        nearby_locations.sort(key=lambda x: x['distance_km'])
        
        return nearby_locations
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates in kilometers"""
        import math
        
        # Haversine formula
        R = 6371  # Earth's radius in kilometers
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat/2) * math.sin(dlat/2) + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon/2) * math.sin(dlon/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return distance
    
    def validate_location(self, location: Dict[str, Any]) -> bool:
        """Validate location data"""
        required_fields = ['city', 'state', 'coordinates']
        
        for field in required_fields:
            if field not in location:
                return False
        
        coords = location['coordinates']
        if 'lat' not in coords or 'lon' not in coords:
            return False
        
        lat, lon = coords['lat'], coords['lon']
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return False
        
        return True
    
    def search_locations(self, query: str) -> List[Dict[str, Any]]:
        """Search for locations using open-source APIs (Nominatim, Photon)"""
        try:
            query_lower = query.lower().strip()
            suggestions = []
            
            # Try Nominatim API (OpenStreetMap) - Free and comprehensive
            nominatim_results = self._search_nominatim(query)
            if nominatim_results:
                suggestions.extend(nominatim_results)
            
            # Try Photon API as backup
            if not suggestions:
                photon_results = self._search_photon(query)
                if photon_results:
                    suggestions.extend(photon_results)
            
            # Try Overpass API for additional coverage
            if len(suggestions) < 5:
                overpass_results = self._search_overpass(query)
                if overpass_results:
                    suggestions.extend(overpass_results)
            
            # Fallback to local database if APIs fail
            if not suggestions:
                suggestions = self._search_local_database(query)
            
            # Sort by relevance and limit results
            suggestions.sort(key=lambda x: (
                0 if query_lower in x['name'].lower() else 1,
                -x['confidence']
            ))
            
            return suggestions[:15]  # Return top 15 results
            
        except Exception as e:
            logger.error(f"Error searching locations: {e}")
            return self._search_local_database(query)
    
    def _search_nominatim(self, query: str) -> List[Dict[str, Any]]:
        """Search using Nominatim API (OpenStreetMap) - Comprehensive Indian locations"""
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': f"{query}, India",  # Explicitly include India
                'format': 'json',
                'countrycodes': 'in',  # Limit to India
                'limit': 20,  # Increased limit for more results
                'addressdetails': 1,
                'extratags': 1,
                'bounded': 0,  # Don't restrict to bounding box
                'dedupe': 1,  # Remove duplicates
                'polygon_geojson': 0
            }
            
            # Add headers to be respectful to the service
            headers = {
                'User-Agent': 'Krishimitra-AI/1.0 (Agricultural Advisory)',
                'Accept': 'application/json'
            }
            
            response = self.session.get(url, params=params, headers=headers, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            suggestions = []
            for item in data:
                address = item.get('address', {})
                display_name = item.get('display_name', '')
                
                # Extract location name (first part before comma)
                location_name = display_name.split(',')[0].strip()
                
                # Skip if name is too generic
                if location_name.lower() in ['india', 'indian', '']:
                    continue
                
                suggestions.append({
                    'name': location_name,
                    'state': address.get('state', 'Unknown'),
                    'district': address.get('county', 'Unknown'),
                    'type': self._determine_location_type(address, display_name),
                    'confidence': 0.95,
                    'lat': float(item.get('lat', 0)),
                    'lon': float(item.get('lon', 0)),
                    'region': self._get_region_from_state(address.get('state', '')),
                    'source': 'Nominatim (OpenStreetMap)',
                    'full_address': display_name
                })
            
            logger.info(f"Found {len(suggestions)} locations from Nominatim for query: {query}")
            return suggestions
            
        except Exception as e:
            logger.warning(f"Nominatim API error: {e}")
            return []
    
    def _search_photon(self, query: str) -> List[Dict[str, Any]]:
        """Search using Photon API (Komoot) - Comprehensive Indian locations"""
        try:
            url = "https://photon.komoot.io/api"
            params = {
                'q': f"{query}, India",  # Explicitly include India
                'limit': 20,  # Increased limit
                'countrycodes': 'in',  # Limit to India
                'lang': 'en'
            }
            
            headers = {
                'User-Agent': 'Krishimitra-AI/1.0 (Agricultural Advisory)',
                'Accept': 'application/json'
            }
            
            response = self.session.get(url, params=params, headers=headers, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            suggestions = []
            for item in data.get('features', []):
                properties = item.get('properties', {})
                geometry = item.get('geometry', {})
                coordinates = geometry.get('coordinates', [0, 0])
                
                location_name = properties.get('name', 'Unknown')
                
                # Skip if name is too generic
                if location_name.lower() in ['india', 'indian', '']:
                    continue
                
                suggestions.append({
                    'name': location_name,
                    'state': properties.get('state', 'Unknown'),
                    'district': properties.get('county', 'Unknown'),
                    'type': self._determine_location_type(properties, location_name),
                    'confidence': 0.9,
                    'lat': float(coordinates[1]) if len(coordinates) > 1 else 0,
                    'lon': float(coordinates[0]) if len(coordinates) > 0 else 0,
                    'region': self._get_region_from_state(properties.get('state', '')),
                    'source': 'Photon (Komoot)',
                    'full_address': f"{location_name}, {properties.get('state', '')}, India"
                })
            
            logger.info(f"Found {len(suggestions)} locations from Photon for query: {query}")
            return suggestions
            
        except Exception as e:
            logger.warning(f"Photon API error: {e}")
            return []
    
    def _search_overpass(self, query: str) -> List[Dict[str, Any]]:
        """Search using Overpass API for additional coverage"""
        try:
            # Overpass query to find places in India
            overpass_query = f"""
            [out:json][timeout:10];
            (
              node["place"]["name"~"{query}",i]["country"="IN"];
              way["place"]["name"~"{query}",i]["country"="IN"];
              relation["place"]["name"~"{query}",i]["country"="IN"];
            );
            out center;
            """
            
            url = "https://overpass-api.de/api/interpreter"
            headers = {
                'User-Agent': 'Krishimitra-AI/1.0 (Agricultural Advisory)',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            response = self.session.post(url, data=overpass_query, headers=headers, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            suggestions = []
            for element in data.get('elements', []):
                tags = element.get('tags', {})
                location_name = tags.get('name', 'Unknown')
                
                if location_name.lower() in ['india', 'indian', '']:
                    continue
                
                # Get coordinates
                lat = element.get('lat', 0)
                lon = element.get('lon', 0)
                
                # For ways and relations, use center coordinates
                if not lat and not lon:
                    center = element.get('center', {})
                    lat = center.get('lat', 0)
                    lon = center.get('lon', 0)
                
                suggestions.append({
                    'name': location_name,
                    'state': tags.get('addr:state', 'Unknown'),
                    'district': tags.get('addr:district', 'Unknown'),
                    'type': self._determine_location_type(tags, location_name),
                    'confidence': 0.85,
                    'lat': float(lat),
                    'lon': float(lon),
                    'region': self._get_region_from_state(tags.get('addr:state', '')),
                    'source': 'Overpass API',
                    'full_address': f"{location_name}, {tags.get('addr:state', '')}, India"
                })
            
            logger.info(f"Found {len(suggestions)} locations from Overpass for query: {query}")
            return suggestions[:10]  # Limit to avoid too many results
            
        except Exception as e:
            logger.warning(f"Overpass API error: {e}")
            return []
    
    def _search_local_database(self, query: str) -> List[Dict[str, Any]]:
        """Fallback search using local database"""
        try:
            query_lower = query.lower().strip()
            suggestions = []
            
            # Search through all locations
            for key, location in self.default_locations.items():
                city_name = location['city'].lower()
                state_name = location['state'].lower()
                
                # Check if query matches city or state
                if (query_lower in city_name or 
                    query_lower in state_name or
                    city_name in query_lower or
                    state_name in query_lower):
                    
                    suggestions.append({
                        'name': location['city'],
                        'state': location['state'],
                        'type': 'metro' if location['city'] in ['Delhi', 'Mumbai', 'Bangalore', 'Chennai', 'Kolkata', 'Hyderabad', 'Pune', 'Ahmedabad', 'Jaipur'] else 'city',
                        'confidence': 0.8,
                        'lat': location['lat'],
                        'lon': location['lon'],
                        'region': location.get('region', 'Unknown'),
                        'source': 'Local Database'
                    })
            
            return suggestions[:10]
            
        except Exception as e:
            logger.error(f"Error in local database search: {e}")
            return []
    
    def _determine_location_type(self, address_data: dict, display_name: str = '') -> str:
        """Determine location type from address data - Enhanced for villages"""
        try:
            # Check for metro cities
            metro_cities = ['delhi', 'mumbai', 'bangalore', 'chennai', 'kolkata', 'hyderabad', 'pune', 'ahmedabad', 'jaipur']
            city_name = address_data.get('city', '').lower()
            
            if city_name in metro_cities:
                return 'metro'
            
            # Enhanced village detection
            village_indicators = [
                'village', 'gram', 'gaon', 'pura', 'nagar', 'pur', 'palli', 'khand', 'basti',
                'nagar', 'colony', 'settlement', 'hamlet', 'mauza', 'tola', 'para', 'mohalla'
            ]
            
            # Check display name and address components
            full_text = f"{display_name} {address_data.get('city', '')} {address_data.get('county', '')}".lower()
            
            for indicator in village_indicators:
                if indicator in full_text:
                    return 'village'
            
            # Check for town indicators
            town_indicators = ['town', 'tehsil', 'taluka', 'block', 'mandal', 'tahsil']
            for indicator in town_indicators:
                if indicator in full_text:
                    return 'town'
            
            # Check for district indicators
            district_indicators = ['district', 'zilla', 'jila']
            for indicator in district_indicators:
                if indicator in full_text:
                    return 'district'
            
            # Default to city
            return 'city'
            
        except Exception:
            return 'city'
    
    def get_location_summary(self) -> Dict[str, Any]:
        """Get summary of current location detection"""
        if not self.current_location:
            return {'status': 'no_location_detected'}
        
        return {
            'current_location': self.current_location,
            'detection_method': self.current_location.get('detection_method', 'unknown'),
            'accuracy': self.current_location.get('accuracy', 'unknown'),
            'timestamp': self.current_location.get('timestamp', 'unknown'),
            'location_history_count': len(self.location_history),
            'nearby_locations': len(self.get_nearby_locations())
        }

# Global instance
location_service = EnhancedLocationService()

def main():
    """Test the enhanced location service"""
    print("Testing Enhanced Location Service...")
    print("="*60)
    
    # Test auto-detection
    print("\n1. Testing auto-detection...")
    location = location_service.auto_detect_location()
    print(f"Detected location: {location['city']}, {location['state']}")
    print(f"Method: {location['detection_method']}")
    print(f"Accuracy: {location['accuracy']}")
    
    # Test GPS detection
    print("\n2. Testing GPS detection...")
    gps_location = location_service.auto_detect_location(gps_lat=28.6139, gps_lon=77.2090)
    print(f"GPS location: {gps_location['city']}, {gps_location['state']}")
    
    # Test manual detection
    print("\n3. Testing manual detection...")
    manual_location = location_service.auto_detect_location(manual_city="Mumbai")
    print(f"Manual location: {manual_location['city']}, {manual_location['state']}")
    
    # Test location update
    print("\n4. Testing location update...")
    updated_location = location_service.update_location(19.0760, 72.8777)
    print(f"Updated location: {updated_location['city']}, {updated_location['state']}")
    
    # Test nearby locations
    print("\n5. Testing nearby locations...")
    nearby = location_service.get_nearby_locations(100)
    print(f"Nearby locations: {len(nearby)}")
    for loc in nearby[:3]:
        print(f"  - {loc['city']}, {loc['state']} ({loc['distance_km']:.1f} km)")
    
    # Get summary
    print("\n6. Location summary...")
    summary = location_service.get_location_summary()
    print(f"Current method: {summary['detection_method']}")
    print(f"Accuracy: {summary['accuracy']}")
    print(f"History entries: {summary['location_history_count']}")
    
    print("\n✓ Enhanced Location Service working correctly!")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Enhanced Auto-Location Detection Service for Krishimitra AI
Similar to Swiggy, Blinkit, Rapido with GPS, IP, and manual location detection
"""

import os
import sys
import json
import time
import requests
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger(__name__)

class EnhancedLocationService:
    """Enhanced location detection service like Swiggy/Blinkit/Rapido"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Krishimitra-AI/1.0 (Agricultural Advisory)',
            'Accept': 'application/json'
        })
        
        # Location detection methods (in order of preference)
        self.detection_methods = [
            'gps',
            'ip_geolocation', 
            'manual_selection',
            'default_location'
        ]
        
        # Comprehensive Indian locations database - ALL major cities, towns, and villages
        self.default_locations = {
            # METRO CITIES
            'delhi': {'lat': 28.6139, 'lon': 77.2090, 'city': 'Delhi', 'state': 'Delhi', 'region': 'North'},
            'mumbai': {'lat': 19.0760, 'lon': 72.8777, 'city': 'Mumbai', 'state': 'Maharashtra', 'region': 'West'},
            'bangalore': {'lat': 12.9716, 'lon': 77.5946, 'city': 'Bangalore', 'state': 'Karnataka', 'region': 'South'},
            'kolkata': {'lat': 22.5726, 'lon': 88.3639, 'city': 'Kolkata', 'state': 'West Bengal', 'region': 'East'},
            'chennai': {'lat': 13.0827, 'lon': 80.2707, 'city': 'Chennai', 'state': 'Tamil Nadu', 'region': 'South'},
            'hyderabad': {'lat': 17.3850, 'lon': 78.4867, 'city': 'Hyderabad', 'state': 'Telangana', 'region': 'South'},
            'pune': {'lat': 18.5204, 'lon': 73.8567, 'city': 'Pune', 'state': 'Maharashtra', 'region': 'West'},
            'ahmedabad': {'lat': 23.0225, 'lon': 72.5714, 'city': 'Ahmedabad', 'state': 'Gujarat', 'region': 'West'},
            'jaipur': {'lat': 26.9124, 'lon': 75.7873, 'city': 'Jaipur', 'state': 'Rajasthan', 'region': 'North'},
            'lucknow': {'lat': 26.8467, 'lon': 80.9462, 'city': 'Lucknow', 'state': 'Uttar Pradesh', 'region': 'North'},
            
            # MAJOR CITIES
            'kanpur': {'lat': 26.4499, 'lon': 80.3319, 'city': 'Kanpur', 'state': 'Uttar Pradesh', 'region': 'North'},
            'nagpur': {'lat': 21.1458, 'lon': 79.0882, 'city': 'Nagpur', 'state': 'Maharashtra', 'region': 'West'},
            'indore': {'lat': 22.7196, 'lon': 75.8577, 'city': 'Indore', 'state': 'Madhya Pradesh', 'region': 'Central'},
            'bhopal': {'lat': 23.2599, 'lon': 77.4126, 'city': 'Bhopal', 'state': 'Madhya Pradesh', 'region': 'Central'},
            'visakhapatnam': {'lat': 17.6868, 'lon': 83.2185, 'city': 'Visakhapatnam', 'state': 'Andhra Pradesh', 'region': 'South'},
            'coimbatore': {'lat': 11.0168, 'lon': 76.9558, 'city': 'Coimbatore', 'state': 'Tamil Nadu', 'region': 'South'},
            'kochi': {'lat': 9.9312, 'lon': 76.2673, 'city': 'Kochi', 'state': 'Kerala', 'region': 'South'},
            'thiruvananthapuram': {'lat': 8.5241, 'lon': 76.9366, 'city': 'Thiruvananthapuram', 'state': 'Kerala', 'region': 'South'},
            'mysore': {'lat': 12.2958, 'lon': 76.6394, 'city': 'Mysore', 'state': 'Karnataka', 'region': 'South'},
            'madurai': {'lat': 9.9252, 'lon': 78.1198, 'city': 'Madurai', 'state': 'Tamil Nadu', 'region': 'South'},
            'salem': {'lat': 11.6643, 'lon': 78.1460, 'city': 'Salem', 'state': 'Tamil Nadu', 'region': 'South'},
            'tiruchirapalli': {'lat': 10.7905, 'lon': 78.7047, 'city': 'Tiruchirapalli', 'state': 'Tamil Nadu', 'region': 'South'},
            'tirunelveli': {'lat': 8.7139, 'lon': 77.7567, 'city': 'Tirunelveli', 'state': 'Tamil Nadu', 'region': 'South'},
            
            # UNION TERRITORIES & CAPITALS
            'chandigarh': {'lat': 30.7333, 'lon': 76.7794, 'city': 'Chandigarh', 'state': 'Chandigarh', 'region': 'North'},
            'dehradun': {'lat': 30.3165, 'lon': 78.0322, 'city': 'Dehradun', 'state': 'Uttarakhand', 'region': 'North'},
            'shimla': {'lat': 31.1048, 'lon': 77.1734, 'city': 'Shimla', 'state': 'Himachal Pradesh', 'region': 'North'},
            'srinagar': {'lat': 34.0837, 'lon': 74.7973, 'city': 'Srinagar', 'state': 'Jammu and Kashmir', 'region': 'North'},
            'jammu': {'lat': 32.7266, 'lon': 74.8570, 'city': 'Jammu', 'state': 'Jammu and Kashmir', 'region': 'North'},
            'leh': {'lat': 34.1526, 'lon': 77.5771, 'city': 'Leh', 'state': 'Ladakh', 'region': 'North'},
            'gangtok': {'lat': 27.3314, 'lon': 88.6138, 'city': 'Gangtok', 'state': 'Sikkim', 'region': 'North'},
            'itanagar': {'lat': 27.0844, 'lon': 93.6053, 'city': 'Itanagar', 'state': 'Arunachal Pradesh', 'region': 'North'},
            'kohima': {'lat': 25.6751, 'lon': 94.1086, 'city': 'Kohima', 'state': 'Nagaland', 'region': 'North'},
            'aizawl': {'lat': 23.7271, 'lon': 92.7176, 'city': 'Aizawl', 'state': 'Mizoram', 'region': 'North'},
            'imphal': {'lat': 24.8170, 'lon': 93.9368, 'city': 'Imphal', 'state': 'Manipur', 'region': 'North'},
            'shillong': {'lat': 25.5788, 'lon': 91.8933, 'city': 'Shillong', 'state': 'Meghalaya', 'region': 'North'},
            'agartala': {'lat': 23.8315, 'lon': 91.2862, 'city': 'Agartala', 'state': 'Tripura', 'region': 'North'},
            'guwahati': {'lat': 26.1445, 'lon': 91.7362, 'city': 'Guwahati', 'state': 'Assam', 'region': 'North'},
            'dispur': {'lat': 26.1433, 'lon': 91.7898, 'city': 'Dispur', 'state': 'Assam', 'region': 'North'},
            'patna': {'lat': 25.5941, 'lon': 85.1376, 'city': 'Patna', 'state': 'Bihar', 'region': 'East'},
            'ranchi': {'lat': 23.3441, 'lon': 85.3096, 'city': 'Ranchi', 'state': 'Jharkhand', 'region': 'East'},
            'bhubaneswar': {'lat': 20.2961, 'lon': 85.8245, 'city': 'Bhubaneswar', 'state': 'Odisha', 'region': 'East'},
            'raipur': {'lat': 21.2514, 'lon': 81.6296, 'city': 'Raipur', 'state': 'Chhattisgarh', 'region': 'Central'},
            'gandhinagar': {'lat': 23.2156, 'lon': 72.6369, 'city': 'Gandhinagar', 'state': 'Gujarat', 'region': 'West'},
            'panaji': {'lat': 15.4909, 'lon': 73.8278, 'city': 'Panaji', 'state': 'Goa', 'region': 'West'},
            
            # MAJOR TOWNS & CITIES
            'nashik': {'lat': 19.9975, 'lon': 73.7898, 'city': 'Nashik', 'state': 'Maharashtra', 'region': 'West'},
            'aurangabad': {'lat': 19.8762, 'lon': 75.3433, 'city': 'Aurangabad', 'state': 'Maharashtra', 'region': 'West'},
            'solapur': {'lat': 17.6599, 'lon': 75.9064, 'city': 'Solapur', 'state': 'Maharashtra', 'region': 'West'},
            'kolhapur': {'lat': 16.7050, 'lon': 74.2433, 'city': 'Kolhapur', 'state': 'Maharashtra', 'region': 'West'},
            'sangli': {'lat': 16.8524, 'lon': 74.5815, 'city': 'Sangli', 'state': 'Maharashtra', 'region': 'West'},
            'ratnagiri': {'lat': 16.9944, 'lon': 73.3002, 'city': 'Ratnagiri', 'state': 'Maharashtra', 'region': 'West'},
            'satara': {'lat': 17.6805, 'lon': 74.0183, 'city': 'Satara', 'state': 'Maharashtra', 'region': 'West'},
            'sindhudurg': {'lat': 16.1667, 'lon': 73.7500, 'city': 'Sindhudurg', 'state': 'Maharashtra', 'region': 'West'},
            'chandigarh': {'lat': 30.7333, 'lon': 76.7794, 'city': 'Chandigarh', 'state': 'Punjab', 'region': 'North'},
            'kochi': {'lat': 9.9312, 'lon': 76.2673, 'city': 'Kochi', 'state': 'Kerala', 'region': 'South'},
            'bhubaneswar': {'lat': 20.2961, 'lon': 85.8245, 'city': 'Bhubaneswar', 'state': 'Odisha', 'region': 'East'},
            'indore': {'lat': 22.7196, 'lon': 75.8577, 'city': 'Indore', 'state': 'Madhya Pradesh', 'region': 'Central'},
            'patna': {'lat': 25.5941, 'lon': 85.1376, 'city': 'Patna', 'state': 'Bihar', 'region': 'East'}
        }
        
        # Current detected location
        self.current_location = None
        self.location_history = []
        
        logger.info("Enhanced Location Service initialized")
    
    def detect_location_gps(self, lat: float = None, lon: float = None) -> Optional[Dict[str, Any]]:
        """Detect location using GPS coordinates (like Swiggy/Blinkit)"""
        try:
            if lat is None or lon is None:
                logger.info("GPS coordinates not provided")
                return None
            
            # Validate coordinates
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                logger.warning(f"Invalid GPS coordinates: {lat}, {lon}")
                return None
            
            # Use reverse geocoding to get location details
            location_data = self._reverse_geocode(lat, lon)
            
            if location_data:
                location_data.update({
                    'detection_method': 'gps',
                    'accuracy': 'high',
                    'timestamp': datetime.now().isoformat(),
                    'coordinates': {'lat': lat, 'lon': lon}
                })
                
                logger.info(f"GPS location detected: {location_data['city']}, {location_data['state']}")
                return location_data
            
        except Exception as e:
            logger.error(f"GPS location detection error: {e}")
        
        return None
    
    def detect_location_ip(self) -> Optional[Dict[str, Any]]:
        """Detect location using IP geolocation (like Swiggy/Blinkit)"""
        try:
            # Use multiple IP geolocation services for better accuracy
            ip_services = [
                'http://ip-api.com/json/',
                'https://ipapi.co/json/',
                'https://api.ipgeolocation.io/ipgeo?apiKey=demo'
            ]
            
            for service_url in ip_services:
                try:
                    response = self.session.get(service_url, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Parse different response formats
                        if 'ip-api.com' in service_url:
                            location_data = self._parse_ipapi_response(data)
                        elif 'ipapi.co' in service_url:
                            location_data = self._parse_ipapi_co_response(data)
                        elif 'ipgeolocation.io' in service_url:
                            location_data = self._parse_ipgeolocation_response(data)
                        
                        if location_data and location_data.get('country') == 'India':
                            location_data.update({
                                'detection_method': 'ip_geolocation',
                                'accuracy': 'medium',
                                'timestamp': datetime.now().isoformat()
                            })
                            
                            logger.info(f"IP location detected: {location_data['city']}, {location_data['state']}")
                            return location_data
                            
                except Exception as e:
                    logger.warning(f"IP service {service_url} failed: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"IP location detection error: {e}")
        
        return None
    
    def detect_location_manual(self, city_name: str = None, state_name: str = None) -> Optional[Dict[str, Any]]:
        """Detect location using manual city/state selection (like Swiggy/Blinkit)"""
        try:
            if not city_name:
                return None
            
            # Normalize city name
            city_key = city_name.lower().strip()
            
            # Direct match
            if city_key in self.default_locations:
                location_data = self.default_locations[city_key].copy()
                location_data.update({
                    'detection_method': 'manual_selection',
                    'accuracy': 'high',
                    'timestamp': datetime.now().isoformat(),
                    'user_input': {'city': city_name, 'state': state_name}
                })
                
                logger.info(f"Manual location detected: {location_data['city']}, {location_data['state']}")
                return location_data
            
            # Fuzzy match for similar city names
            for key, location in self.default_locations.items():
                if (city_key in key or key in city_key or 
                    city_name.lower() in location['city'].lower() or
                    location['city'].lower() in city_name.lower()):
                    
                    location_data = location.copy()
                    location_data.update({
                        'detection_method': 'manual_selection',
                        'accuracy': 'medium',
                        'timestamp': datetime.now().isoformat(),
                        'user_input': {'city': city_name, 'state': state_name},
                        'matched_city': location['city']
                    })
                    
                    logger.info(f"Manual location fuzzy matched: {city_name} -> {location_data['city']}")
                    return location_data
            
        except Exception as e:
            logger.error(f"Manual location detection error: {e}")
        
        return None
    
    def detect_location_default(self) -> Dict[str, Any]:
        """Fallback to default location (Delhi)"""
        location_data = self.default_locations['delhi'].copy()
        location_data.update({
            'detection_method': 'default_location',
            'accuracy': 'low',
            'timestamp': datetime.now().isoformat(),
            'fallback_reason': 'No other detection method succeeded'
        })
        
        logger.info(f"Using default location: {location_data['city']}, {location_data['state']}")
        return location_data
    
    def auto_detect_location(self, gps_lat: float = None, gps_lon: float = None, 
                           manual_city: str = None, manual_state: str = None) -> Dict[str, Any]:
        """Auto-detect location using multiple methods (like Swiggy/Blinkit/Rapido)"""
        
        logger.info("Starting auto location detection...")
        
        # Try GPS first (most accurate)
        if gps_lat and gps_lon:
            location = self.detect_location_gps(gps_lat, gps_lon)
            if location:
                self.current_location = location
                self.location_history.append(location)
                return location
        
        # Try manual selection (user specified)
        if manual_city:
            location = self.detect_location_manual(manual_city, manual_state)
            if location:
                self.current_location = location
                self.location_history.append(location)
                return location
        
        # Try IP geolocation
        location = self.detect_location_ip()
        if location:
            self.current_location = location
            self.location_history.append(location)
            return location
        
        # Fallback to default
        location = self.detect_location_default()
        self.current_location = location
        self.location_history.append(location)
        return location
    
    def get_current_location(self) -> Optional[Dict[str, Any]]:
        """Get current detected location"""
        return self.current_location
    
    def update_location(self, lat: float, lon: float) -> Dict[str, Any]:
        """Update location (like changing location in Swiggy/Blinkit)"""
        logger.info(f"Updating location to: {lat}, {lon}")
        
        location = self.detect_location_gps(lat, lon)
        if location:
            self.current_location = location
            self.location_history.append(location)
            logger.info(f"Location updated to: {location['city']}, {location['state']}")
            return location
        
        # Fallback to default if GPS detection fails
        return self.detect_location_default()
    
    def get_location_history(self) -> List[Dict[str, Any]]:
        """Get location detection history"""
        return self.location_history
    
    def _reverse_geocode(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Reverse geocoding to get location details from coordinates"""
        try:
            # Use OpenStreetMap Nominatim for reverse geocoding
            url = f"https://nominatim.openstreetmap.org/reverse"
            params = {
                'lat': lat,
                'lon': lon,
                'format': 'json',
                'addressdetails': 1,
                'zoom': 10
            }
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                if 'address' in data:
                    address = data['address']
                    
                    # Extract location details
                    city = (address.get('city') or 
                           address.get('town') or 
                           address.get('village') or 
                           address.get('suburb', 'Unknown'))
                    
                    state = (address.get('state') or 
                            address.get('province') or 
                            'Unknown')
                    
                    country = address.get('country', 'Unknown')
                    
                    if country.lower() == 'india':
                        # Determine region based on state
                        region = self._get_region_from_state(state)
                        
                        return {
                            'city': city,
                            'state': state,
                            'country': country,
                            'region': region,
                            'coordinates': {'lat': lat, 'lon': lon},
                            'address': data.get('display_name', ''),
                            'source': 'OpenStreetMap Nominatim'
                        }
            
        except Exception as e:
            logger.error(f"Reverse geocoding error: {e}")
        
        return None
    
    def _get_region_from_state(self, state: str) -> str:
        """Determine region based on state name"""
        state_lower = state.lower()
        
        if any(keyword in state_lower for keyword in ['delhi', 'punjab', 'haryana', 'rajasthan', 'himachal', 'uttarakhand', 'jammu', 'kashmir']):
            return 'North'
        elif any(keyword in state_lower for keyword in ['maharashtra', 'gujarat', 'goa', 'dadra', 'nagar']):
            return 'West'
        elif any(keyword in state_lower for keyword in ['karnataka', 'tamil nadu', 'kerala', 'andhra pradesh', 'telangana']):
            return 'South'
        elif any(keyword in state_lower for keyword in ['west bengal', 'odisha', 'bihar', 'jharkhand', 'assam', 'tripura', 'manipur', 'meghalaya', 'mizoram', 'nagaland', 'sikkim', 'arunachal']):
            return 'East'
        elif any(keyword in state_lower for keyword in ['madhya pradesh', 'chhattisgarh', 'uttar pradesh']):
            return 'Central'
        else:
            return 'Unknown'
    
    def _parse_ipapi_response(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse ip-api.com response"""
        try:
            if data.get('status') == 'success':
                return {
                    'city': data.get('city', 'Unknown'),
                    'state': data.get('regionName', 'Unknown'),
                    'country': data.get('country', 'Unknown'),
                    'coordinates': {
                        'lat': data.get('lat', 0),
                        'lon': data.get('lon', 0)
                    },
                    'source': 'ip-api.com'
                }
        except Exception as e:
            logger.error(f"Error parsing ip-api response: {e}")
        return None
    
    def _parse_ipapi_co_response(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse ipapi.co response"""
        try:
            return {
                'city': data.get('city', 'Unknown'),
                'state': data.get('region', 'Unknown'),
                'country': data.get('country_name', 'Unknown'),
                'coordinates': {
                    'lat': data.get('latitude', 0),
                    'lon': data.get('longitude', 0)
                },
                'source': 'ipapi.co'
            }
        except Exception as e:
            logger.error(f"Error parsing ipapi.co response: {e}")
        return None
    
    def _parse_ipgeolocation_response(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse ipgeolocation.io response"""
        try:
            return {
                'city': data.get('city', 'Unknown'),
                'state': data.get('state_prov', 'Unknown'),
                'country': data.get('country_name', 'Unknown'),
                'coordinates': {
                    'lat': data.get('latitude', 0),
                    'lon': data.get('longitude', 0)
                },
                'source': 'ipgeolocation.io'
            }
        except Exception as e:
            logger.error(f"Error parsing ipgeolocation response: {e}")
        return None
    
    def get_nearby_locations(self, radius_km: float = 50) -> List[Dict[str, Any]]:
        """Get nearby locations within radius (like Swiggy/Blinkit)"""
        if not self.current_location:
            return []
        
        current_lat = self.current_location['coordinates']['lat']
        current_lon = self.current_location['coordinates']['lon']
        
        nearby_locations = []
        
        for key, location in self.default_locations.items():
            lat = location['lat']
            lon = location['lon']
            
            # Calculate distance (simple approximation)
            distance = self._calculate_distance(current_lat, current_lon, lat, lon)
            
            if distance <= radius_km:
                location_copy = location.copy()
                location_copy['distance_km'] = distance
                nearby_locations.append(location_copy)
        
        # Sort by distance
        nearby_locations.sort(key=lambda x: x['distance_km'])
        
        return nearby_locations
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates in kilometers"""
        import math
        
        # Haversine formula
        R = 6371  # Earth's radius in kilometers
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat/2) * math.sin(dlat/2) + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon/2) * math.sin(dlon/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return distance
    
    def validate_location(self, location: Dict[str, Any]) -> bool:
        """Validate location data"""
        required_fields = ['city', 'state', 'coordinates']
        
        for field in required_fields:
            if field not in location:
                return False
        
        coords = location['coordinates']
        if 'lat' not in coords or 'lon' not in coords:
            return False
        
        lat, lon = coords['lat'], coords['lon']
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return False
        
        return True
    
    def search_locations(self, query: str) -> List[Dict[str, Any]]:
        """Search for locations using open-source APIs (Nominatim, Photon)"""
        try:
            query_lower = query.lower().strip()
            suggestions = []
            
            # Try Nominatim API (OpenStreetMap) - Free and comprehensive
            nominatim_results = self._search_nominatim(query)
            if nominatim_results:
                suggestions.extend(nominatim_results)
            
            # Try Photon API as backup
            if not suggestions:
                photon_results = self._search_photon(query)
                if photon_results:
                    suggestions.extend(photon_results)
            
            # Try Overpass API for additional coverage
            if len(suggestions) < 5:
                overpass_results = self._search_overpass(query)
                if overpass_results:
                    suggestions.extend(overpass_results)
            
            # Fallback to local database if APIs fail
            if not suggestions:
                suggestions = self._search_local_database(query)
            
            # Sort by relevance and limit results
            suggestions.sort(key=lambda x: (
                0 if query_lower in x['name'].lower() else 1,
                -x['confidence']
            ))
            
            return suggestions[:15]  # Return top 15 results
            
        except Exception as e:
            logger.error(f"Error searching locations: {e}")
            return self._search_local_database(query)
    
    def _search_nominatim(self, query: str) -> List[Dict[str, Any]]:
        """Search using Nominatim API (OpenStreetMap) - Comprehensive Indian locations"""
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': f"{query}, India",  # Explicitly include India
                'format': 'json',
                'countrycodes': 'in',  # Limit to India
                'limit': 20,  # Increased limit for more results
                'addressdetails': 1,
                'extratags': 1,
                'bounded': 0,  # Don't restrict to bounding box
                'dedupe': 1,  # Remove duplicates
                'polygon_geojson': 0
            }
            
            # Add headers to be respectful to the service
            headers = {
                'User-Agent': 'Krishimitra-AI/1.0 (Agricultural Advisory)',
                'Accept': 'application/json'
            }
            
            response = self.session.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            suggestions = []
            for item in data:
                address = item.get('address', {})
                display_name = item.get('display_name', '')
                
                # Extract location name (first part before comma)
                location_name = display_name.split(',')[0].strip()
                
                # Skip if name is too generic
                if location_name.lower() in ['india', 'indian', '']:
                    continue
                
                suggestions.append({
                    'name': location_name,
                    'state': address.get('state', 'Unknown'),
                    'district': address.get('county', 'Unknown'),
                    'type': self._determine_location_type(address, display_name),
                    'confidence': 0.95,
                    'lat': float(item.get('lat', 0)),
                    'lon': float(item.get('lon', 0)),
                    'region': self._get_region_from_state(address.get('state', '')),
                    'source': 'Nominatim (OpenStreetMap)',
                    'full_address': display_name
                })
            
            logger.info(f"Found {len(suggestions)} locations from Nominatim for query: {query}")
            return suggestions
            
        except Exception as e:
            logger.warning(f"Nominatim API error: {e}")
            return []
    
    def _search_photon(self, query: str) -> List[Dict[str, Any]]:
        """Search using Photon API (Komoot) - Comprehensive Indian locations"""
        try:
            url = "https://photon.komoot.io/api"
            params = {
                'q': f"{query}, India",  # Explicitly include India
                'limit': 20,  # Increased limit
                'countrycodes': 'in',  # Limit to India
                'lang': 'en'
            }
            
            headers = {
                'User-Agent': 'Krishimitra-AI/1.0 (Agricultural Advisory)',
                'Accept': 'application/json'
            }
            
            response = self.session.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            suggestions = []
            for item in data.get('features', []):
                properties = item.get('properties', {})
                geometry = item.get('geometry', {})
                coordinates = geometry.get('coordinates', [0, 0])
                
                location_name = properties.get('name', 'Unknown')
                
                # Skip if name is too generic
                if location_name.lower() in ['india', 'indian', '']:
                    continue
                
                suggestions.append({
                    'name': location_name,
                    'state': properties.get('state', 'Unknown'),
                    'district': properties.get('county', 'Unknown'),
                    'type': self._determine_location_type(properties, location_name),
                    'confidence': 0.9,
                    'lat': float(coordinates[1]) if len(coordinates) > 1 else 0,
                    'lon': float(coordinates[0]) if len(coordinates) > 0 else 0,
                    'region': self._get_region_from_state(properties.get('state', '')),
                    'source': 'Photon (Komoot)',
                    'full_address': f"{location_name}, {properties.get('state', '')}, India"
                })
            
            logger.info(f"Found {len(suggestions)} locations from Photon for query: {query}")
            return suggestions
            
        except Exception as e:
            logger.warning(f"Photon API error: {e}")
            return []
    
    def _search_overpass(self, query: str) -> List[Dict[str, Any]]:
        """Search using Overpass API for additional coverage"""
        try:
            # Overpass query to find places in India
            overpass_query = f"""
            [out:json][timeout:10];
            (
              node["place"]["name"~"{query}",i]["country"="IN"];
              way["place"]["name"~"{query}",i]["country"="IN"];
              relation["place"]["name"~"{query}",i]["country"="IN"];
            );
            out center;
            """
            
            url = "https://overpass-api.de/api/interpreter"
            headers = {
                'User-Agent': 'Krishimitra-AI/1.0 (Agricultural Advisory)',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            response = self.session.post(url, data=overpass_query, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            suggestions = []
            for element in data.get('elements', []):
                tags = element.get('tags', {})
                location_name = tags.get('name', 'Unknown')
                
                if location_name.lower() in ['india', 'indian', '']:
                    continue
                
                # Get coordinates
                lat = element.get('lat', 0)
                lon = element.get('lon', 0)
                
                # For ways and relations, use center coordinates
                if not lat and not lon:
                    center = element.get('center', {})
                    lat = center.get('lat', 0)
                    lon = center.get('lon', 0)
                
                suggestions.append({
                    'name': location_name,
                    'state': tags.get('addr:state', 'Unknown'),
                    'district': tags.get('addr:district', 'Unknown'),
                    'type': self._determine_location_type(tags, location_name),
                    'confidence': 0.85,
                    'lat': float(lat),
                    'lon': float(lon),
                    'region': self._get_region_from_state(tags.get('addr:state', '')),
                    'source': 'Overpass API',
                    'full_address': f"{location_name}, {tags.get('addr:state', '')}, India"
                })
            
            logger.info(f"Found {len(suggestions)} locations from Overpass for query: {query}")
            return suggestions[:10]  # Limit to avoid too many results
            
        except Exception as e:
            logger.warning(f"Overpass API error: {e}")
            return []
    
    def _search_local_database(self, query: str) -> List[Dict[str, Any]]:
        """Fallback search using local database"""
        try:
            query_lower = query.lower().strip()
            suggestions = []
            
            # Search through all locations
            for key, location in self.default_locations.items():
                city_name = location['city'].lower()
                state_name = location['state'].lower()
                
                # Check if query matches city or state
                if (query_lower in city_name or 
                    query_lower in state_name or
                    city_name in query_lower or
                    state_name in query_lower):
                    
                    suggestions.append({
                        'name': location['city'],
                        'state': location['state'],
                        'type': 'metro' if location['city'] in ['Delhi', 'Mumbai', 'Bangalore', 'Chennai', 'Kolkata', 'Hyderabad', 'Pune', 'Ahmedabad', 'Jaipur'] else 'city',
                        'confidence': 0.8,
                        'lat': location['lat'],
                        'lon': location['lon'],
                        'region': location.get('region', 'Unknown'),
                        'source': 'Local Database'
                    })
            
            return suggestions[:10]
            
        except Exception as e:
            logger.error(f"Error in local database search: {e}")
            return []
    
    def _determine_location_type(self, address_data: dict, display_name: str = '') -> str:
        """Determine location type from address data - Enhanced for villages"""
        try:
            # Check for metro cities
            metro_cities = ['delhi', 'mumbai', 'bangalore', 'chennai', 'kolkata', 'hyderabad', 'pune', 'ahmedabad', 'jaipur']
            city_name = address_data.get('city', '').lower()
            
            if city_name in metro_cities:
                return 'metro'
            
            # Enhanced village detection
            village_indicators = [
                'village', 'gram', 'gaon', 'pura', 'nagar', 'pur', 'palli', 'khand', 'basti',
                'nagar', 'colony', 'settlement', 'hamlet', 'mauza', 'tola', 'para', 'mohalla'
            ]
            
            # Check display name and address components
            full_text = f"{display_name} {address_data.get('city', '')} {address_data.get('county', '')}".lower()
            
            for indicator in village_indicators:
                if indicator in full_text:
                    return 'village'
            
            # Check for town indicators
            town_indicators = ['town', 'tehsil', 'taluka', 'block', 'mandal', 'tahsil']
            for indicator in town_indicators:
                if indicator in full_text:
                    return 'town'
            
            # Check for district indicators
            district_indicators = ['district', 'zilla', 'jila']
            for indicator in district_indicators:
                if indicator in full_text:
                    return 'district'
            
            # Default to city
            return 'city'
            
        except Exception:
            return 'city'
    
    def get_location_summary(self) -> Dict[str, Any]:
        """Get summary of current location detection"""
        if not self.current_location:
            return {'status': 'no_location_detected'}
        
        return {
            'current_location': self.current_location,
            'detection_method': self.current_location.get('detection_method', 'unknown'),
            'accuracy': self.current_location.get('accuracy', 'unknown'),
            'timestamp': self.current_location.get('timestamp', 'unknown'),
            'location_history_count': len(self.location_history),
            'nearby_locations': len(self.get_nearby_locations())
        }

# Global instance
location_service = EnhancedLocationService()

def main():
    """Test the enhanced location service"""
    print("Testing Enhanced Location Service...")
    print("="*60)
    
    # Test auto-detection
    print("\n1. Testing auto-detection...")
    location = location_service.auto_detect_location()
    print(f"Detected location: {location['city']}, {location['state']}")
    print(f"Method: {location['detection_method']}")
    print(f"Accuracy: {location['accuracy']}")
    
    # Test GPS detection
    print("\n2. Testing GPS detection...")
    gps_location = location_service.auto_detect_location(gps_lat=28.6139, gps_lon=77.2090)
    print(f"GPS location: {gps_location['city']}, {gps_location['state']}")
    
    # Test manual detection
    print("\n3. Testing manual detection...")
    manual_location = location_service.auto_detect_location(manual_city="Mumbai")
    print(f"Manual location: {manual_location['city']}, {manual_location['state']}")
    
    # Test location update
    print("\n4. Testing location update...")
    updated_location = location_service.update_location(19.0760, 72.8777)
    print(f"Updated location: {updated_location['city']}, {updated_location['state']}")
    
    # Test nearby locations
    print("\n5. Testing nearby locations...")
    nearby = location_service.get_nearby_locations(100)
    print(f"Nearby locations: {len(nearby)}")
    for loc in nearby[:3]:
        print(f"  - {loc['city']}, {loc['state']} ({loc['distance_km']:.1f} km)")
    
    # Get summary
    print("\n6. Location summary...")
    summary = location_service.get_location_summary()
    print(f"Current method: {summary['detection_method']}")
    print(f"Accuracy: {summary['accuracy']}")
    print(f"History entries: {summary['location_history_count']}")
    
    print("\n✓ Enhanced Location Service working correctly!")

if __name__ == "__main__":
    main()
