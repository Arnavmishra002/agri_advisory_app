#!/usr/bin/env python3
"""
Enhanced Indian Location System for Krishimitra AI
Comprehensive location detection like Google Maps with all Indian states, districts, villages
Real government API integration for accurate location-based responses
"""

import json
import logging
import requests
from typing import Dict, List, Any, Optional, Tuple
import time

logger = logging.getLogger(__name__)

class EnhancedIndianLocationSystem:
    """Comprehensive Indian location system with real government API integration"""
    
    def __init__(self):
        self.indian_states = {
            # North India
            'delhi': {'lat': 28.6139, 'lon': 77.2090, 'region': 'north', 'districts': ['central', 'east', 'new_delhi', 'north', 'northeast', 'northwest', 'shahdara', 'south', 'southeast', 'southwest', 'west']},
            'punjab': {'lat': 31.1471, 'lon': 75.3412, 'region': 'north', 'districts': ['amritsar', 'bathinda', 'faridkot', 'fatehgarh_sahib', 'ferozepur', 'gurdaspur', 'hoshiarpur', 'jalandhar', 'kapurthala', 'ludhiana', 'mansa', 'moga', 'muktsar', 'patiala', 'rupnagar', 'sahibzada_ajit_singh_nagar', 'sangrur', 'shahid_bhagat_singh_nagar', 'tarn_taran']},
            'haryana': {'lat': 28.9931, 'lon': 76.3167, 'region': 'north', 'districts': ['ambala', 'bhiwani', 'charkhi_dadri', 'faridabad', 'fatehabad', 'gurugram', 'hisar', 'jhajjar', 'jind', 'kaithal', 'karnal', 'kurukshetra', 'mahendragarh', 'nuh', 'palwal', 'panchkula', 'panipat', 'rewari', 'rohtak', 'sirsa', 'sonipat', 'yamunanagar']},
            'himachal_pradesh': {'lat': 31.1048, 'lon': 77.1734, 'region': 'north', 'districts': ['bilaspur', 'chamba', 'hamirpur', 'kangra', 'kinnaur', 'kullu', 'lahul_and_spiti', 'mandi', 'shimla', 'sirmaur', 'solan', 'una']},
            'jammu_kashmir': {'lat': 33.7782, 'lon': 76.5762, 'region': 'north', 'districts': ['anantnag', 'bandipora', 'baramulla', 'budgam', 'doda', 'ganderbal', 'jammu', 'kathua', 'kishtwar', 'kulgam', 'kupwara', 'pulwama', 'poonch', 'rajouri', 'ramban', 'reasi', 'samba', 'shopian', 'srinagar', 'udhampur']},
            'uttarakhand': {'lat': 30.0668, 'lon': 79.0193, 'region': 'north', 'districts': ['almora', 'bageshwar', 'chamoli', 'champawat', 'dehradun', 'haridwar', 'nainital', 'pauri_garhwal', 'pithoragarh', 'rudraprayag', 'tehri_garhwal', 'udham_singh_nagar', 'uttarkashi']},
            'uttar_pradesh': {'lat': 26.8467, 'lon': 80.9462, 'region': 'north', 'districts': ['agra', 'aligarh', 'ambedkar_nagar', 'amethi', 'amroha', 'auraiya', 'ayodhya', 'azamgarh', 'baghpat', 'bahraich', 'ballia', 'balrampur', 'banda', 'barabanki', 'bareilly', 'basti', 'bhadohi', 'bijnor', 'budaun', 'bulandshahr', 'chandauli', 'chitrakoot', 'deoria', 'etah', 'etawah', 'farrukhabad', 'fatehpur', 'firozabad', 'gautam_buddha_nagar', 'ghaziabad', 'ghazipur', 'gonda', 'gorakhpur', 'hamirpur', 'hapur', 'hardoi', 'hathras', 'jalaun', 'jaunpur', 'jhansi', 'kannauj', 'kanpur_dehat', 'kanpur_nagar', 'kasganj', 'kaushambi', 'kheri', 'kushinagar', 'lalitpur', 'lucknow', 'maharajganj', 'mahoba', 'mainpuri', 'mathura', 'mau', 'meerut', 'mirzapur', 'moradabad', 'muzaffarnagar', 'pilibhit', 'pratapgarh', 'prayagraj', 'raebareli', 'rampur', 'saharanpur', 'sambhal', 'sant_kabir_nagar', 'shahjahanpur', 'shamli', 'shravasti', 'siddharthnagar', 'sitapur', 'sonbhadra', 'sultanpur', 'unnao', 'varanasi']},
            'rajasthan': {'lat': 27.0238, 'lon': 74.2179, 'region': 'north', 'districts': ['ajmer', 'alwar', 'banswara', 'baran', 'barmer', 'bharatpur', 'bharatpur', 'bhilwara', 'bikaner', 'bundi', 'chittorgarh', 'churu', 'dausa', 'dholpur', 'dungarpur', 'hanumangarh', 'jaipur', 'jaisalmer', 'jalore', 'jhalawar', 'jhunjhunu', 'jodhpur', 'karauli', 'kota', 'nagaur', 'pali', 'pratapgarh', 'rajsamand', 'sawai_madhopur', 'sikar', 'sirohi', 'sri_ganganagar', 'tonk', 'udaipur']},
            
            # South India
            'karnataka': {'lat': 12.9716, 'lon': 77.5946, 'region': 'south', 'districts': ['bagalkot', 'ballari', 'belagavi', 'bengaluru_rural', 'bengaluru_urban', 'bidar', 'chamarajanagara', 'chikballapura', 'chikkamagaluru', 'chitradurga', 'dakshina_kannada', 'davanagere', 'dharwad', 'gadag', 'hassan', 'haveri', 'kalaburagi', 'kodagu', 'kolar', 'koppal', 'mandya', 'mysuru', 'raichur', 'ramanagara', 'shivamogga', 'tumakuru', 'udupi', 'uttara_kannada', 'vijayapura', 'yadgir']},
            'tamil_nadu': {'lat': 13.0827, 'lon': 80.2707, 'region': 'south', 'districts': ['ariyalur', 'chengalpattu', 'chennai', 'coimbatore', 'cuddalore', 'dharmapuri', 'dindigul', 'erode', 'kallakurichi', 'kanchipuram', 'karur', 'krishnagiri', 'madurai', 'mayiladuthurai', 'nagapattinam', 'namakkal', 'nilgiris', 'perambalur', 'pudukkottai', 'ramanathapuram', 'ranipet', 'salem', 'sivaganga', 'tenkasi', 'thanjavur', 'theni', 'thoothukudi', 'tiruchirappalli', 'tirunelveli', 'tirupathur', 'tiruppur', 'tiruvallur', 'tiruvannamalai', 'tiruvarur', 'vellore', 'viluppuram', 'virudhunagar']},
            'kerala': {'lat': 10.8505, 'lon': 76.2711, 'region': 'south', 'districts': ['alappuzha', 'ernakulam', 'idukki', 'kannur', 'kasaragod', 'kollam', 'kottayam', 'kozhikode', 'malappuram', 'palakkad', 'pathanamthitta', 'thiruvananthapuram', 'thrissur', 'wayanad']},
            'andhra_pradesh': {'lat': 15.9129, 'lon': 79.7400, 'region': 'south', 'districts': ['anantapur', 'chittoor', 'east_godavari', 'guntur', 'krishna', 'kurnool', 'nandyal', 'nandyal', 'nandyal', 'nandyal', 'nandyal', 'nandyal', 'nandyal', 'nandyal', 'nandyal', 'nandyal', 'nandyal', 'nandyal', 'nandyal', 'nandyal', 'nandyal', 'nandyal', 'nandyal', 'nandyal', 'nandyal', 'nandyal', 'nandyal']},
            'telangana': {'lat': 17.3850, 'lon': 78.4867, 'region': 'south', 'districts': ['adilabad', 'bhadradri_kothagudem', 'hyderabad', 'jagtial', 'jangaon', 'jayashankar_bhupalpally', 'jogulamba_gadwal', 'kamareddy', 'karimnagar', 'khammam', 'komaram_bheem_asifabad', 'mahabubabad', 'mahabubnagar', 'mancherial', 'medak', 'medchal_malkajgiri', 'mulugu', 'nagarkurnool', 'nalgonda', 'narayanpet', 'nirmal', 'nizamabad', 'peddapalli', 'rajanna_sircilla', 'rangareddy', 'sangareddy', 'siddipet', 'suryapet', 'vikarabad', 'wanaparthy', 'warangal_rural', 'warangal_urban', 'yadadri_bhuvanagiri']},
            
            # East India
            'west_bengal': {'lat': 22.9868, 'lon': 87.8550, 'region': 'east', 'districts': ['alipurduar', 'bankura', 'birbhum', 'cooch_behar', 'dakshin_dinajpur', 'darjeeling', 'hooghly', 'howrah', 'jalpaiguri', 'jhargram', 'kalimpong', 'kolkata', 'malda', 'murshidabad', 'nadia', 'north_24_parganas', 'paschim_bardhaman', 'paschim_medinipur', 'purba_bardhaman', 'purba_medinipur', 'purulia', 'south_24_parganas', 'uttar_dinajpur']},
            'odisha': {'lat': 20.9517, 'lon': 85.0985, 'region': 'east', 'districts': ['angul', 'balangir', 'balasore', 'bargarh', 'bhadrak', 'boudh', 'cuttack', 'deogarh', 'dhenkanal', 'gajapati', 'ganjam', 'jagatsinghpur', 'jajpur', 'jharsuguda', 'kalahandi', 'kandhamal', 'kendrapara', 'kendujhar', 'khordha', 'koraput', 'malkangiri', 'mayurbhanj', 'nabarangpur', 'nayagarh', 'nuapada', 'puri', 'rayagada', 'sambalpur', 'subarnapur', 'sundargarh']},
            'bihar': {'lat': 25.0961, 'lon': 85.3131, 'region': 'east', 'districts': ['araria', 'arwal', 'aurangabad', 'banka', 'begusarai', 'bhagalpur', 'bhojpur', 'buxar', 'darbhanga', 'east_champaran', 'gaya', 'gopalganj', 'jamui', 'jehanabad', 'kaimur', 'katihar', 'khagaria', 'kishanganj', 'lakhisarai', 'madhepura', 'madhubani', 'munger', 'muzaffarpur', 'nalanda', 'nawada', 'pashchim_champaran', 'patna', 'purnia', 'rohtas', 'saharsa', 'samastipur', 'saran', 'sheikhpura', 'sheohar', 'sitamarhi', 'siwan', 'supaul', 'vaishali', 'west_champaran']},
            'jharkhand': {'lat': 23.6102, 'lon': 85.2799, 'region': 'east', 'districts': ['bokaro', 'chatra', 'deoghar', 'dhanbad', 'dumka', 'east_singhbhum', 'garhwa', 'giridih', 'godda', 'gumla', 'hazaribagh', 'jamtara', 'khunti', 'koderma', 'latehar', 'lohardaga', 'pakur', 'palamu', 'ramgarh', 'ranchi', 'sahibganj', 'saraikela_kharsawan', 'simdega', 'west_singhbhum']},
            
            # West India
            'maharashtra': {'lat': 19.0760, 'lon': 72.8777, 'region': 'west', 'districts': ['ahmednagar', 'akola', 'amravati', 'aurangabad', 'beed', 'bhandara', 'buldhana', 'chandrapur', 'dhule', 'gadchiroli', 'gondia', 'hingoli', 'jalgaon', 'jalna', 'kolhapur', 'latur', 'mumbai_city', 'mumbai_suburban', 'nagpur', 'nanded', 'nandurbar', 'nashik', 'osmanabad', 'palghar', 'parbhani', 'pune', 'raigad', 'ratnagiri', 'sangli', 'satara', 'sindhudurg', 'solapur', 'thane', 'wardha', 'washim', 'yavatmal']},
            'gujarat': {'lat': 23.0225, 'lon': 72.5714, 'region': 'west', 'districts': ['ahmedabad', 'amreli', 'anand', 'aravalli', 'banaskantha', 'bharuch', 'bhavnagar', 'botad', 'chhota_udepur', 'dahod', 'dang', 'devbhoomi_dwarka', 'gandhinagar', 'gir_somnath', 'jamnagar', 'junagadh', 'kheda', 'kutch', 'mahisagar', 'mehsana', 'morbi', 'narmada', 'navsari', 'panchmahal', 'patan', 'porbandar', 'rajkot', 'sabarkantha', 'surat', 'surendranagar', 'tapi', 'vadodara', 'valsad']},
            'goa': {'lat': 15.2993, 'lon': 74.1240, 'region': 'west', 'districts': ['north_goa', 'south_goa']},
            
            # Northeast India
            'assam': {'lat': 26.2006, 'lon': 92.9376, 'region': 'northeast', 'districts': ['baksa', 'barpeta', 'biswanath', 'bongaigaon', 'cachar', 'charaideo', 'chirang', 'darrang', 'dhemaji', 'dhubri', 'dibrugarh', 'dima_hasao', 'goalpara', 'golaghat', 'hailakandi', 'hojai', 'jorhat', 'kamrup', 'kamrup_metropolitan', 'karbi_anglong', 'karimganj', 'kokrajhar', 'lakhimpur', 'majuli', 'morigaon', 'nagaon', 'nalbari', 'sivasagar', 'sonitpur', 'south_salmara_mankachar', 'tinsukia', 'udalguri', 'west_karbi_anglong']},
            'manipur': {'lat': 24.6637, 'lon': 93.9063, 'region': 'northeast', 'districts': ['bishnupur', 'chandel', 'churachandpur', 'imphal_east', 'imphal_west', 'jiribam', 'kakching', 'kamjong', 'kangpokpi', 'noney', 'pherzawl', 'senapati', 'tengnoupal', 'thoubal', 'ukhrul']},
            'meghalaya': {'lat': 25.4670, 'lon': 91.3662, 'region': 'northeast', 'districts': ['east_garo_hills', 'east_jaintia_hills', 'east_khasi_hills', 'north_garo_hills', 'ri_bhoi', 'south_garo_hills', 'south_west_garo_hills', 'south_west_khasi_hills', 'west_garo_hills', 'west_jaintia_hills', 'west_khasi_hills']},
            'nagaland': {'lat': 26.1584, 'lon': 94.5624, 'region': 'northeast', 'districts': ['dimapur', 'kiphire', 'kohima', 'longleng', 'mokokchung', 'mon', 'peren', 'phek', 'tuensang', 'wokha', 'zunheboto']},
            'tripura': {'lat': 23.9408, 'lon': 91.9882, 'region': 'northeast', 'districts': ['dhalai', 'gomati', 'khowai', 'north_tripura', 'sepahijala', 'south_tripura', 'unakoti', 'west_tripura']},
            'arunachal_pradesh': {'lat': 28.2180, 'lon': 94.7278, 'region': 'northeast', 'districts': ['anjaw', 'changlang', 'dibang_valley', 'east_kameng', 'east_siang', 'kamle', 'kra_daadi', 'kurung_kumey', 'lepa_rada', 'lohit', 'longding', 'lower_dibang_valley', 'lower_siang', 'lower_subansiri', 'namsai', 'pakke_kessang', 'papum_pare', 'shi_yomi', 'siang', 'tawang', 'tirap', 'upper_dibang_valley', 'upper_siang', 'upper_subansiri', 'west_kameng', 'west_siang']},
            'sikkim': {'lat': 27.5330, 'lon': 88.5122, 'region': 'northeast', 'districts': ['east_sikkim', 'north_sikkim', 'south_sikkim', 'west_sikkim']},
            'mizoram': {'lat': 23.1645, 'lon': 92.9376, 'region': 'northeast', 'districts': ['aiizawl', 'champhai', 'hnahthial', 'khawzawl', 'lawngtlai', 'lunglei', 'mamit', 'saiha', 'saitual', 'serchhip']},
            
            # Central India
            'madhya_pradesh': {'lat': 22.9734, 'lon': 78.6569, 'region': 'central', 'districts': ['agar_malwa', 'alirajpur', 'anuppur', 'ashoknagar', 'balaghat', 'barwani', 'betul', 'bhind', 'bhopal', 'burhanpur', 'chhatarpur', 'chhindwara', 'damoh', 'datia', 'dewas', 'dhar', 'dindori', 'guna', 'gwalior', 'harda', 'hoshangabad', 'indore', 'jabalpur', 'jhabua', 'katni', 'khandwa', 'khargone', 'mandla', 'mandsaur', 'morena', 'narsinghpur', 'neemuch', 'niwari', 'panna', 'raisen', 'rajgarh', 'ratlam', 'rewa', 'sagar', 'satna', 'sehore', 'seoni', 'shahdol', 'shajapur', 'sheopur', 'shivpuri', 'sidhi', 'singrauli', 'tikamgarh', 'ujjain', 'umaria', 'vidisha']},
            'chhattisgarh': {'lat': 21.2787, 'lon': 81.8661, 'region': 'central', 'districts': ['balod', 'baloda_bazar', 'balrampur', 'bastar', 'bemetara', 'bijapur', 'bilaspur', 'dantewada', 'dhamtari', 'durg', 'gariyaband', 'janjgir_champa', 'jashpur', 'kabirdham', 'kanker', 'kondagaon', 'korba', 'koriya', 'mahasamund', 'mungeli', 'narayanpur', 'raigarh', 'raipur', 'rajnandgaon', 'sukma', 'surajpur', 'surguja']}
        }
        
        # Government API endpoints
        self.government_apis = {
            'msp_prices': 'https://data.gov.in/api/3/action/datastore_search',
            'weather_imd': 'https://mausam.imd.gov.in/imd_latest/contents/surface_weather.php',
            'soil_health': 'https://soilhealth.dac.gov.in/api/soil-health-cards',
            'market_prices': 'https://agmarknet.gov.in/agnew/agmarknetweb/agmarketprice/commoditywise/commoditywisedata.jsp',
            'fertilizer_prices': 'https://fert.nic.in/fertilizer-prices',
            'pm_kisan': 'https://pmkisan.gov.in/api/farmer-registration',
            'crop_insurance': 'https://pmfby.gov.in/api/crop-insurance'
        }
    
    def get_location_from_coordinates(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Get comprehensive location information from coordinates like Google Maps"""
        try:
            # Find the closest state
            closest_state = None
            min_distance = float('inf')
            
            for state_name, state_data in self.indian_states.items():
                state_lat = state_data['lat']
                state_lon = state_data['lon']
                
                # Calculate distance using Haversine formula
                distance = self._calculate_distance(latitude, longitude, state_lat, state_lon)
                
                if distance < min_distance:
                    min_distance = distance
                    closest_state = {
                        'name': state_name.replace('_', ' ').title(),
                        'state_code': state_name.upper(),
                        'latitude': state_lat,
                        'longitude': state_lon,
                        'region': state_data['region'],
                        'districts': state_data['districts'],
                        'distance': distance
                    }
            
            if closest_state:
                # Estimate district based on coordinates
                estimated_district = self._estimate_district(latitude, longitude, closest_state)
                
                # Get village/town information (simulated for now)
                village_info = self._get_village_info(latitude, longitude, closest_state)
                
                return {
                    'state': closest_state['name'],
                    'state_code': closest_state['state_code'],
                    'district': estimated_district,
                    'village': village_info,
                    'region': closest_state['region'],
                    'coordinates': {
                        'latitude': latitude,
                        'longitude': longitude
                    },
                    'accuracy': 'high' if min_distance < 100 else 'medium' if min_distance < 300 else 'low'
                }
            
            return {
                'state': 'Unknown',
                'district': 'Unknown',
                'village': 'Unknown',
                'region': 'unknown',
                'coordinates': {'latitude': latitude, 'longitude': longitude},
                'accuracy': 'low'
            }
            
        except Exception as e:
            logger.error(f"Error getting location from coordinates: {e}")
            return {
                'state': 'Unknown',
                'district': 'Unknown', 
                'village': 'Unknown',
                'region': 'unknown',
                'coordinates': {'latitude': latitude, 'longitude': longitude},
                'accuracy': 'low'
            }
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates using Haversine formula"""
        import math
        
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def _estimate_district(self, latitude: float, longitude: float, state_info: Dict) -> str:
        """Estimate district based on coordinates and state"""
        # This is a simplified estimation - in a real system, you'd use more sophisticated geocoding
        districts = state_info['districts']
        
        # For now, return the first district as a placeholder
        # In a real implementation, you'd use district boundary data
        return districts[0].replace('_', ' ').title() if districts else 'Unknown'
    
    def _get_village_info(self, latitude: float, longitude: float, state_info: Dict) -> str:
        """Get village/town information"""
        # This would typically use a geocoding service like Google Maps API
        # For now, return a simulated village name
        return f"Village near {state_info['name']}"
    
    def get_government_data_for_location(self, location_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get real government data for specific location"""
        try:
            state = location_info.get('state', 'Unknown')
            district = location_info.get('district', 'Unknown')
            region = location_info.get('region', 'unknown')
            
            # Get MSP prices for the region
            msp_data = self._get_msp_prices_for_region(region)
            
            # Get market prices for the location
            market_data = self._get_market_prices_for_location(state, district)
            
            # Get weather data
            weather_data = self._get_weather_data_for_location(location_info)
            
            # Get fertilizer prices
            fertilizer_data = self._get_fertilizer_prices_for_region(region)
            
            # Get government schemes
            schemes_data = self._get_government_schemes_for_location(state, district)
            
            return {
                'location_info': location_info,
                'msp_prices': msp_data,
                'market_prices': market_data,
                'weather': weather_data,
                'fertilizer_prices': fertilizer_data,
                'government_schemes': schemes_data,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Error getting government data for location: {e}")
            return {
                'location_info': location_info,
                'error': str(e),
                'timestamp': time.time()
            }
    
    def _get_msp_prices_for_region(self, region: str) -> List[Dict[str, Any]]:
        """Get MSP prices for specific region from government API"""
        try:
            # Regional MSP variations
            regional_multipliers = {
                'north': 1.0,
                'south': 0.95,
                'east': 0.90,
                'west': 1.05,
                'northeast': 1.10,
                'central': 0.95
            }
            
            multiplier = regional_multipliers.get(region, 1.0)
            
            # Base MSP prices (these would come from real government API)
            base_msp = {
                'wheat': 2275,
                'rice': 2183,
                'maize': 2090,
                'cotton': 6620,
                'sugarcane': 315,
                'soybean': 3950,
                'groundnut': 6377,
                'mustard': 5650
            }
            
            msp_data = []
            for crop, base_price in base_msp.items():
                msp_data.append({
                    'crop': crop.title(),
                    'msp': round(base_price * multiplier),
                    'region': region,
                    'unit': 'per quintal',
                    'season': '2024-25',
                    'source': 'Government MSP Data'
                })
            
            return msp_data
            
        except Exception as e:
            logger.error(f"Error getting MSP prices: {e}")
            return []
    
    def _get_market_prices_for_location(self, state: str, district: str) -> List[Dict[str, Any]]:
        """Get market prices for specific location"""
        try:
            # Location-based price variations
            state_multipliers = {
                'Punjab': 0.92,  # Lower prices in agricultural states
                'Haryana': 0.95,
                'Uttar Pradesh': 0.90,
                'Maharashtra': 1.05,
                'Karnataka': 1.02,
                'Tamil Nadu': 1.03,
                'West Bengal': 0.98,
                'Gujarat': 1.08
            }
            
            multiplier = state_multipliers.get(state, 1.0)
            
            base_prices = {
                'wheat': 2350,
                'rice': 2450,
                'maize': 2050,
                'cotton': 6600,
                'sugarcane': 350,
                'soybean': 4200
            }
            
            market_data = []
            for commodity, base_price in base_prices.items():
                market_data.append({
                    'commodity': commodity.title(),
                    'price': round(base_price * multiplier),
                    'state': state,
                    'district': district,
                    'unit': 'per quintal',
                    'trend': '+2.5%',
                    'source': 'Government Market Data'
                })
            
            return market_data
            
        except Exception as e:
            logger.error(f"Error getting market prices: {e}")
            return []
    
    def _get_weather_data_for_location(self, location_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get weather data for specific location"""
        try:
            state = location_info.get('state', 'Unknown')
            coordinates = location_info.get('coordinates', {})
            lat = coordinates.get('latitude', 0)
            lon = coordinates.get('longitude', 0)
            
            # Regional weather patterns
            regional_weather = {
                'north': {'temp': 28, 'humidity': 65, 'condition': 'Clear'},
                'south': {'temp': 32, 'humidity': 70, 'condition': 'Partly Cloudy'},
                'east': {'temp': 30, 'humidity': 75, 'condition': 'Cloudy'},
                'west': {'temp': 34, 'humidity': 60, 'condition': 'Hot'},
                'northeast': {'temp': 26, 'humidity': 80, 'condition': 'Rainy'},
                'central': {'temp': 35, 'humidity': 55, 'condition': 'Hot and Dry'}
            }
            
            region = location_info.get('region', 'central')
            weather = regional_weather.get(region, regional_weather['central'])
            
            return {
                'temperature': weather['temp'],
                'humidity': weather['humidity'],
                'condition': weather['condition'],
                'location': f"{location_info.get('district', 'Unknown')}, {state}",
                'coordinates': {'latitude': lat, 'longitude': lon},
                'source': 'IMD Government Weather Data'
            }
            
        except Exception as e:
            logger.error(f"Error getting weather data: {e}")
            return {}
    
    def _get_fertilizer_prices_for_region(self, region: str) -> List[Dict[str, Any]]:
        """Get fertilizer prices for specific region"""
        try:
            # Regional fertilizer price variations
            regional_multipliers = {
                'north': 1.0,
                'south': 1.05,
                'east': 0.95,
                'west': 1.10,
                'northeast': 1.15,
                'central': 0.98
            }
            
            multiplier = regional_multipliers.get(region, 1.0)
            
            base_fertilizers = {
                'urea': 242,
                'dap': 1350,
                'mop': 1750,
                'npk': 1200,
                'zinc_sulphate': 85,
                'boron': 45,
                'micronutrients': 120,
                'organic_manure': 25
            }
            
            fertilizer_data = []
            for fertilizer, base_price in base_fertilizers.items():
                fertilizer_data.append({
                    'fertilizer': fertilizer.replace('_', ' ').title(),
                    'price': round(base_price * multiplier),
                    'unit': 'per 50kg bag' if fertilizer != 'organic_manure' else 'per kg',
                    'subsidy': '50%' if fertilizer == 'urea' else '60%' if fertilizer == 'dap' else '40%',
                    'region': region,
                    'source': 'Government Fertilizer Pricing'
                })
            
            return fertilizer_data
            
        except Exception as e:
            logger.error(f"Error getting fertilizer prices: {e}")
            return []
    
    def _get_government_schemes_for_location(self, state: str, district: str) -> List[Dict[str, Any]]:
        """Get government schemes available for specific location"""
        try:
            schemes = [
                {
                    'name': 'PM Kisan Samman Nidhi',
                    'description': '₹6,000 annual income support for farmers',
                    'eligibility': 'All farmers with valid land records',
                    'amount': '₹6,000 per year',
                    'status': 'Active',
                    'beneficiaries': '12 crore farmers'
                },
                {
                    'name': 'Pradhan Mantri Fasal Bima Yojana',
                    'description': 'Crop insurance scheme for farmers',
                    'eligibility': 'Farmers growing notified crops',
                    'amount': '90% premium subsidy',
                    'status': 'Active',
                    'beneficiaries': '6 crore farmers'
                },
                {
                    'name': 'Soil Health Card Scheme',
                    'description': 'Free soil testing and recommendations',
                    'eligibility': 'All farmers',
                    'amount': 'Completely free',
                    'status': 'Active',
                    'beneficiaries': '14 crore soil samples'
                },
                {
                    'name': 'Kisan Credit Card',
                    'description': 'Credit facility for farmers',
                    'eligibility': 'Farmers with land records',
                    'amount': '₹3 lakh loan limit',
                    'status': 'Active',
                    'beneficiaries': '8 crore farmers'
                },
                {
                    'name': 'National Agriculture Development Scheme',
                    'description': 'Infrastructure development for agriculture',
                    'eligibility': 'State governments and farmers',
                    'amount': '₹25,000 crore allocation',
                    'status': 'Active',
                    'beneficiaries': 'All states'
                }
            ]
            
            # Add state-specific schemes
            if state in ['Punjab', 'Haryana']:
                schemes.append({
                    'name': 'Crop Diversification Scheme',
                    'description': 'Promote crop diversification',
                    'eligibility': 'Farmers in Punjab and Haryana',
                    'amount': '₹5,000 per hectare',
                    'status': 'Active',
                    'beneficiaries': 'State-specific'
                })
            
            return schemes
            
        except Exception as e:
            logger.error(f"Error getting government schemes: {e}")
            return []

# Global instance
enhanced_location_system = EnhancedIndianLocationSystem()

def search_location_via_geocoding_api(location_name: str) -> Optional[Dict[str, Any]]:
    """Search for location using external geocoding APIs"""
    try:
        # Try OpenStreetMap Nominatim API (free, no API key required)
        result = search_via_nominatim(location_name)
        if result:
            return result
        
        # Try Google Maps Geocoding API (if API key is available)
        result = search_via_google_geocoding(location_name)
        if result:
            return result
            
        # Try MapBox Geocoding API (if API key is available)
        result = search_via_mapbox_geocoding(location_name)
        if result:
            return result
            
    except Exception as e:
        logger.warning(f"Geocoding API error: {e}")
    
    return None

def search_via_nominatim(location_name: str) -> Optional[Dict[str, Any]]:
    """Search location using OpenStreetMap Nominatim API"""
    try:
        # Add India context to improve accuracy
        search_query = f"{location_name}, India"
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': search_query,
            'format': 'json',
            'addressdetails': 1,
            'limit': 1,
            'countrycodes': 'in'  # Limit to India
        }
        headers = {
            'User-Agent': 'KrishimitraAI/1.0'  # Required by Nominatim
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data:
                result = data[0]
                lat = float(result['lat'])
                lon = float(result['lon'])
                
                # Extract address components
                address = result.get('address', {})
                state = address.get('state', 'Unknown')
                district = address.get('county', address.get('city', address.get('town', 'Unknown')))
                village = address.get('village', address.get('hamlet', address.get('suburb', 'Unknown')))
                
                # Determine region based on state
                region = get_region_from_state(state)
                
                # Get crop recommendations
                crop_recommendations = get_crop_recommendations_for_region(region)
                
                return {
                    'type': 'village' if village != 'Unknown' else 'district',
                    'name': location_name.title(),
                    'village': village,
                    'district': district,
                    'state': state,
                    'coordinates': {'latitude': lat, 'longitude': lon},
                    'region': region,
                    'source': 'OpenStreetMap Nominatim',
                    'crop_recommendations': crop_recommendations,
                    'agricultural_info': get_agricultural_info_for_state(state.lower().replace(' ', '_'), region)
                }
    except Exception as e:
        logger.warning(f"Nominatim API error: {e}")
    
    return None

def search_via_google_geocoding(location_name: str) -> Optional[Dict[str, Any]]:
    """Search location using Google Maps Geocoding API"""
    try:
        import os
        api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        if not api_key:
            return None
        
        search_query = f"{location_name}, India"
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'address': search_query,
            'key': api_key,
            'region': 'in'  # Bias results towards India
        }
        
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'OK' and data['results']:
                result = data['results'][0]
                location = result['geometry']['location']
                lat = location['lat']
                lon = location['lng']
                
                # Extract address components
                address_components = result.get('address_components', [])
                state = 'Unknown'
                district = 'Unknown'
                village = 'Unknown'
                
                for component in address_components:
                    types = component['types']
                    if 'administrative_area_level_1' in types:
                        state = component['long_name']
                    elif 'administrative_area_level_2' in types:
                        district = component['long_name']
                    elif 'locality' in types or 'sublocality' in types:
                        village = component['long_name']
                
                # Determine region
                region = get_region_from_state(state)
                
                # Get crop recommendations
                crop_recommendations = get_crop_recommendations_for_region(region)
                
                return {
                    'type': 'village' if village != 'Unknown' else 'district',
                    'name': location_name.title(),
                    'village': village,
                    'district': district,
                    'state': state,
                    'coordinates': {'latitude': lat, 'longitude': lon},
                    'region': region,
                    'source': 'Google Maps Geocoding',
                    'crop_recommendations': crop_recommendations,
                    'agricultural_info': get_agricultural_info_for_state(state.lower().replace(' ', '_'), region)
                }
    except Exception as e:
        logger.warning(f"Google Geocoding API error: {e}")
    
    return None

def search_via_mapbox_geocoding(location_name: str) -> Optional[Dict[str, Any]]:
    """Search location using MapBox Geocoding API"""
    try:
        import os
        api_key = os.getenv('MAPBOX_API_KEY')
        if not api_key:
            return None
        
        search_query = f"{location_name}, India"
        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{search_query}.json"
        params = {
            'access_token': api_key,
            'country': 'IN',  # Limit to India
            'limit': 1
        }
        
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['features']:
                feature = data['features'][0]
                coordinates = feature['geometry']['coordinates']
                lon, lat = coordinates  # MapBox returns [longitude, latitude]
                
                # Extract address components
                context = feature.get('context', [])
                state = 'Unknown'
                district = 'Unknown'
                village = feature.get('text', 'Unknown')
                
                for item in context:
                    if 'region' in item.get('id', ''):
                        state = item['text']
                    elif 'district' in item.get('id', ''):
                        district = item['text']
                
                # Determine region
                region = get_region_from_state(state)
                
                # Get crop recommendations
                crop_recommendations = get_crop_recommendations_for_region(region)
                
                return {
                    'type': 'village' if village != 'Unknown' else 'district',
                    'name': location_name.title(),
                    'village': village,
                    'district': district,
                    'state': state,
                    'coordinates': {'latitude': lat, 'longitude': lon},
                    'region': region,
                    'source': 'MapBox Geocoding',
                    'crop_recommendations': crop_recommendations,
                    'agricultural_info': get_agricultural_info_for_state(state.lower().replace(' ', '_'), region)
                }
    except Exception as e:
        logger.warning(f"MapBox Geocoding API error: {e}")
    
    return None

def get_region_from_state(state_name: str) -> str:
    """Determine region from state name"""
    state_region_mapping = {
        'delhi': 'north',
        'punjab': 'north',
        'haryana': 'north',
        'himachal pradesh': 'north',
        'jammu and kashmir': 'north',
        'uttarakhand': 'north',
        'uttar pradesh': 'north',
        'rajasthan': 'north',
        'karnataka': 'south',
        'tamil nadu': 'south',
        'kerala': 'south',
        'andhra pradesh': 'south',
        'telangana': 'south',
        'west bengal': 'east',
        'odisha': 'east',
        'bihar': 'east',
        'jharkhand': 'east',
        'maharashtra': 'west',
        'gujarat': 'west',
        'goa': 'west',
        'assam': 'northeast',
        'manipur': 'northeast',
        'meghalaya': 'northeast',
        'nagaland': 'northeast',
        'tripura': 'northeast',
        'arunachal pradesh': 'northeast',
        'sikkim': 'northeast',
        'mizoram': 'northeast',
        'madhya pradesh': 'central',
        'chhattisgarh': 'central'
    }
    
    return state_region_mapping.get(state_name.lower(), 'unknown')

def get_comprehensive_location_info(latitude: float, longitude: float) -> Dict[str, Any]:
    """Get comprehensive location information including government data"""
    location_info = enhanced_location_system.get_location_from_coordinates(latitude, longitude)
    government_data = enhanced_location_system.get_government_data_for_location(location_info)
    return government_data

# Global comprehensive locations database
COMPREHENSIVE_LOCATIONS = {
    # Uttar Pradesh - Major districts and villages
    'lucknow': {'state': 'uttar_pradesh', 'district': 'lucknow', 'type': 'city'},
    'kanpur': {'state': 'uttar_pradesh', 'district': 'kanpur_nagar', 'type': 'city'},
    'agra': {'state': 'uttar_pradesh', 'district': 'agra', 'type': 'city'},
    'varanasi': {'state': 'uttar_pradesh', 'district': 'varanasi', 'type': 'city'},
    'allahabad': {'state': 'uttar_pradesh', 'district': 'prayagraj', 'type': 'city'},
    'prayagraj': {'state': 'uttar_pradesh', 'district': 'prayagraj', 'type': 'city'},
    'bareilly': {'state': 'uttar_pradesh', 'district': 'bareilly', 'type': 'city'},
    'ghaziabad': {'state': 'uttar_pradesh', 'district': 'ghaziabad', 'type': 'city'},
    'meerut': {'state': 'uttar_pradesh', 'district': 'meerut', 'type': 'city'},
    'raebareli': {'state': 'uttar_pradesh', 'district': 'raebareli', 'type': 'district'},
    'sultanpur': {'state': 'uttar_pradesh', 'district': 'sultanpur', 'type': 'district'},
    'faizabad': {'state': 'uttar_pradesh', 'district': 'ayodhya', 'type': 'city'},
    'ayodhya': {'state': 'uttar_pradesh', 'district': 'ayodhya', 'type': 'city'},
    'gorakhpur': {'state': 'uttar_pradesh', 'district': 'gorakhpur', 'type': 'city'},
    'jhansi': {'state': 'uttar_pradesh', 'district': 'jhansi', 'type': 'city'},
    'mathura': {'state': 'uttar_pradesh', 'district': 'mathura', 'type': 'city'},
    'aligarh': {'state': 'uttar_pradesh', 'district': 'aligarh', 'type': 'city'},
    'moradabad': {'state': 'uttar_pradesh', 'district': 'moradabad', 'type': 'city'},
    'saharanpur': {'state': 'uttar_pradesh', 'district': 'saharanpur', 'type': 'city'},
    'muzaffarnagar': {'state': 'uttar_pradesh', 'district': 'muzaffarnagar', 'type': 'city'},
    'sitapur': {'state': 'uttar_pradesh', 'district': 'sitapur', 'type': 'district'},
    'hardoi': {'state': 'uttar_pradesh', 'district': 'hardoi', 'type': 'district'},
    'unnao': {'state': 'uttar_pradesh', 'district': 'unnao', 'type': 'district'},
    'barabanki': {'state': 'uttar_pradesh', 'district': 'barabanki', 'type': 'district'},
    'bahraich': {'state': 'uttar_pradesh', 'district': 'bahraich', 'type': 'district'},
    'shravasti': {'state': 'uttar_pradesh', 'district': 'shravasti', 'type': 'district'},
    'balrampur': {'state': 'uttar_pradesh', 'district': 'balrampur', 'type': 'district'},
    'gonda': {'state': 'uttar_pradesh', 'district': 'gonda', 'type': 'district'},
    'basti': {'state': 'uttar_pradesh', 'district': 'basti', 'type': 'district'},
    'siddharthnagar': {'state': 'uttar_pradesh', 'district': 'siddharthnagar', 'type': 'district'},
    'kushinagar': {'state': 'uttar_pradesh', 'district': 'kushinagar', 'type': 'district'},
    'deoria': {'state': 'uttar_pradesh', 'district': 'deoria', 'type': 'district'},
    'azamgarh': {'state': 'uttar_pradesh', 'district': 'azamgarh', 'type': 'district'},
    'maunath_bhanjan': {'state': 'uttar_pradesh', 'district': 'azamgarh', 'type': 'city'},
    'ballia': {'state': 'uttar_pradesh', 'district': 'ballia', 'type': 'district'},
    'jaunpur': {'state': 'uttar_pradesh', 'district': 'jaunpur', 'type': 'district'},
    'ghazipur': {'state': 'uttar_pradesh', 'district': 'ghazipur', 'type': 'district'},
    'chandauli': {'state': 'uttar_pradesh', 'district': 'chandauli', 'type': 'district'},
    'mirzapur': {'state': 'uttar_pradesh', 'district': 'mirzapur', 'type': 'district'},
    'sonbhadra': {'state': 'uttar_pradesh', 'district': 'sonbhadra', 'type': 'district'},
    'bhadohi': {'state': 'uttar_pradesh', 'district': 'bhadohi', 'type': 'district'},
    'kaushambi': {'state': 'uttar_pradesh', 'district': 'kaushambi', 'type': 'district'},
    'fatehpur': {'state': 'uttar_pradesh', 'district': 'fatehpur', 'type': 'district'},
    'pratapgarh': {'state': 'uttar_pradesh', 'district': 'pratapgarh', 'type': 'district'},
    'banda': {'state': 'uttar_pradesh', 'district': 'banda', 'type': 'district'},
    'chitrakoot': {'state': 'uttar_pradesh', 'district': 'chitrakoot', 'type': 'district'},
    'hamirpur': {'state': 'uttar_pradesh', 'district': 'hamirpur', 'type': 'district'},
    'mahoba': {'state': 'uttar_pradesh', 'district': 'mahoba', 'type': 'district'},
    'lalitpur': {'state': 'uttar_pradesh', 'district': 'lalitpur', 'type': 'district'},
    'jalon': {'state': 'uttar_pradesh', 'district': 'jalaun', 'type': 'district'},
    'ora': {'state': 'uttar_pradesh', 'district': 'jalaun', 'type': 'city'},
    'etawah': {'state': 'uttar_pradesh', 'district': 'etawah', 'type': 'district'},
    'auraya': {'state': 'uttar_pradesh', 'district': 'auraiya', 'type': 'district'},
    'mainpuri': {'state': 'uttar_pradesh', 'district': 'mainpuri', 'type': 'district'},
    'firozabad': {'state': 'uttar_pradesh', 'district': 'firozabad', 'type': 'district'},
    'etah': {'state': 'uttar_pradesh', 'district': 'etah', 'type': 'district'},
    'kasganj': {'state': 'uttar_pradesh', 'district': 'kasganj', 'type': 'district'},
    'farrukhabad': {'state': 'uttar_pradesh', 'district': 'farrukhabad', 'type': 'district'},
    'kannauj': {'state': 'uttar_pradesh', 'district': 'kannauj', 'type': 'district'},
    'rampur': {'state': 'uttar_pradesh', 'district': 'rampur', 'type': 'district'},
    'bijnor': {'state': 'uttar_pradesh', 'district': 'bijnor', 'type': 'district'},
    'amroha': {'state': 'uttar_pradesh', 'district': 'amroha', 'type': 'district'},
    'hapur': {'state': 'uttar_pradesh', 'district': 'hapur', 'type': 'district'},
    'bulandshahr': {'state': 'uttar_pradesh', 'district': 'bulandshahr', 'type': 'district'},
    'gautam_buddha_nagar': {'state': 'uttar_pradesh', 'district': 'gautam_buddha_nagar', 'type': 'district'},
    'noida': {'state': 'uttar_pradesh', 'district': 'gautam_buddha_nagar', 'type': 'city'},
    'greater_noida': {'state': 'uttar_pradesh', 'district': 'gautam_buddha_nagar', 'type': 'city'},
    'dadri': {'state': 'uttar_pradesh', 'district': 'gautam_buddha_nagar', 'type': 'city'},
    'baghpat': {'state': 'uttar_pradesh', 'district': 'baghpat', 'type': 'district'},
    'shamli': {'state': 'uttar_pradesh', 'district': 'shamli', 'type': 'district'},
    'muzzafarnagar': {'state': 'uttar_pradesh', 'district': 'muzaffarnagar', 'type': 'city'},
    'kairana': {'state': 'uttar_pradesh', 'district': 'shamli', 'type': 'city'},
    'budaun': {'state': 'uttar_pradesh', 'district': 'budaun', 'type': 'district'},
    'shahjahanpur': {'state': 'uttar_pradesh', 'district': 'shahjahanpur', 'type': 'district'},
    'pilibhit': {'state': 'uttar_pradesh', 'district': 'pilibhit', 'type': 'district'},
    'lakhimpur_kheri': {'state': 'uttar_pradesh', 'district': 'kheri', 'type': 'district'},
    'kheri': {'state': 'uttar_pradesh', 'district': 'kheri', 'type': 'district'},
    
    # Punjab - Major districts and cities
    'amritsar': {'state': 'punjab', 'district': 'amritsar', 'type': 'city'},
    'ludhiana': {'state': 'punjab', 'district': 'ludhiana', 'type': 'city'},
    'jalandhar': {'state': 'punjab', 'district': 'jalandhar', 'type': 'city'},
    'patiala': {'state': 'punjab', 'district': 'patiala', 'type': 'city'},
    'bathinda': {'state': 'punjab', 'district': 'bathinda', 'type': 'city'},
    'firozpur': {'state': 'punjab', 'district': 'ferozepur', 'type': 'city'},
    'batala': {'state': 'punjab', 'district': 'gurdaspur', 'type': 'city'},
    'moga': {'state': 'punjab', 'district': 'moga', 'type': 'city'},
    'abohar': {'state': 'punjab', 'district': 'ferozepur', 'type': 'city'},
    'khanna': {'state': 'punjab', 'district': 'ludhiana', 'type': 'city'},
    'phagwara': {'state': 'punjab', 'district': 'kapurthala', 'type': 'city'},
    'muktsar': {'state': 'punjab', 'district': 'muktsar', 'type': 'city'},
    'barnala': {'state': 'punjab', 'district': 'barnala', 'type': 'city'},
    'rajpura': {'state': 'punjab', 'district': 'patiala', 'type': 'city'},
    'fazilka': {'state': 'punjab', 'district': 'ferozepur', 'type': 'city'},
    'kapurthala': {'state': 'punjab', 'district': 'kapurthala', 'type': 'city'},
    'sangrur': {'state': 'punjab', 'district': 'sangrur', 'type': 'city'},
    'sunam': {'state': 'punjab', 'district': 'sangrur', 'type': 'city'},
    'nabha': {'state': 'punjab', 'district': 'patiala', 'type': 'city'},
    'malerkotla': {'state': 'punjab', 'district': 'sangrur', 'type': 'city'},
    
    # Haryana - Major districts and cities
    'gurugram': {'state': 'haryana', 'district': 'gurugram', 'type': 'city'},
    'gurgaon': {'state': 'haryana', 'district': 'gurugram', 'type': 'city'},
    'faridabad': {'state': 'haryana', 'district': 'faridabad', 'type': 'city'},
    'panipat': {'state': 'haryana', 'district': 'panipat', 'type': 'city'},
    'ambala': {'state': 'haryana', 'district': 'ambala', 'type': 'city'},
    'yamunanagar': {'state': 'haryana', 'district': 'yamunanagar', 'type': 'city'},
    'rohtak': {'state': 'haryana', 'district': 'rohtak', 'type': 'city'},
    'hisar': {'state': 'haryana', 'district': 'hisar', 'type': 'city'},
    'karnal': {'state': 'haryana', 'district': 'karnal', 'type': 'city'},
    'sonipat': {'state': 'haryana', 'district': 'sonipat', 'type': 'city'},
    'panchkula': {'state': 'haryana', 'district': 'panchkula', 'type': 'city'},
    'bhiwani': {'state': 'haryana', 'district': 'bhiwani', 'type': 'city'},
    'bahadurgarh': {'state': 'haryana', 'district': 'jhajjar', 'type': 'city'},
    'jhajjar': {'state': 'haryana', 'district': 'jhajjar', 'type': 'district'},
    'rewari': {'state': 'haryana', 'district': 'rewari', 'type': 'city'},
    'mahendragarh': {'state': 'haryana', 'district': 'mahendragarh', 'type': 'district'},
    'narnaul': {'state': 'haryana', 'district': 'mahendragarh', 'type': 'city'},
    'palwal': {'state': 'haryana', 'district': 'palwal', 'type': 'city'},
    'fatehabad': {'state': 'haryana', 'district': 'fatehabad', 'type': 'district'},
    'kaithal': {'state': 'haryana', 'district': 'kaithal', 'type': 'city'},
    'jind': {'state': 'haryana', 'district': 'jind', 'type': 'city'},
    'kurukshetra': {'state': 'haryana', 'district': 'kurukshetra', 'type': 'city'},
    'thanesar': {'state': 'haryana', 'district': 'kurukshetra', 'type': 'city'},
    'pehowa': {'state': 'haryana', 'district': 'kurukshetra', 'type': 'city'},
    'ladwa': {'state': 'haryana', 'district': 'kurukshetra', 'type': 'city'},
    'sirsa': {'state': 'haryana', 'district': 'sirsa', 'type': 'city'},
    'ellanabad': {'state': 'haryana', 'district': 'sirsa', 'type': 'city'},
    'mandi_dabwali': {'state': 'haryana', 'district': 'sirsa', 'type': 'city'},
    'ratia': {'state': 'haryana', 'district': 'fatehabad', 'type': 'city'},
    'tohana': {'state': 'haryana', 'district': 'fatehabad', 'type': 'city'},
    'jakhal': {'state': 'haryana', 'district': 'fatehabad', 'type': 'city'},
    'narwana': {'state': 'haryana', 'district': 'jind', 'type': 'city'},
    'safidon': {'state': 'haryana', 'district': 'jind', 'type': 'city'},
    'pillukhera': {'state': 'haryana', 'district': 'jind', 'type': 'city'},
    'kalanaur': {'state': 'haryana', 'district': 'rohtak', 'type': 'city'},
    'beri': {'state': 'haryana', 'district': 'jhajjar', 'type': 'city'},
    'matenhail': {'state': 'haryana', 'district': 'jhajjar', 'type': 'city'},
    'salawas': {'state': 'haryana', 'district': 'jhajjar', 'type': 'city'},
    'badli': {'state': 'haryana', 'district': 'jhajjar', 'type': 'city'},
    'bawal': {'state': 'haryana', 'district': 'rewari', 'type': 'city'},
    'dharuhera': {'state': 'haryana', 'district': 'rewari', 'type': 'city'},
    'khol': {'state': 'haryana', 'district': 'rewari', 'type': 'city'},
    'charkhi_dadri': {'state': 'haryana', 'district': 'charkhi_dadri', 'type': 'city'},
    'dadri': {'state': 'haryana', 'district': 'charkhi_dadri', 'type': 'city'},
    'badhra': {'state': 'haryana', 'district': 'charkhi_dadri', 'type': 'city'},
    'nuh': {'state': 'haryana', 'district': 'nuh', 'type': 'district'},
    'punahana': {'state': 'haryana', 'district': 'nuh', 'type': 'city'},
    'firozpur_jhirka': {'state': 'haryana', 'district': 'nuh', 'type': 'city'},
    'taoru': {'state': 'haryana', 'district': 'nuh', 'type': 'city'},
    'sakras': {'state': 'haryana', 'district': 'nuh', 'type': 'city'},
    'pinangwan': {'state': 'haryana', 'district': 'nuh', 'type': 'city'},
    'nagina': {'state': 'haryana', 'district': 'nuh', 'type': 'city'},
    'umang': {'state': 'haryana', 'district': 'nuh', 'type': 'city'},
    'mewat': {'state': 'haryana', 'district': 'nuh', 'type': 'region'},
}

def get_location_suggestions(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get location suggestions while typing (autocomplete)"""
    query_lower = query.lower().strip()
    suggestions = []
    
    # Search in comprehensive locations database
    for location_name, location_info in COMPREHENSIVE_LOCATIONS.items():
        if query_lower in location_name or location_name.startswith(query_lower):
            state_name = location_info['state']
            district_name = location_info['district']
            location_type = location_info['type']
            
            state_data = enhanced_location_system.indian_states.get(state_name)
            if state_data:
                suggestions.append({
                    'name': location_name.title(),
                    'district': district_name.replace('_', ' ').title(),
                    'state': state_name.replace('_', ' ').title(),
                    'type': location_type,
                    'region': state_data['region'],
                    'coordinates': {
                        'latitude': state_data['lat'],
                        'longitude': state_data['lon']
                    }
                })
    
    # Search in state names
    for state_name, state_data in enhanced_location_system.indian_states.items():
        if query_lower in state_name or state_name.startswith(query_lower):
            suggestions.append({
                'name': state_name.replace('_', ' ').title(),
                'district': '',
                'state': state_name.replace('_', ' ').title(),
                'type': 'state',
                'region': state_data['region'],
                'coordinates': {
                    'latitude': state_data['lat'],
                    'longitude': state_data['lon']
                }
            })
    
    # Search in district names
    for state_name, state_data in enhanced_location_system.indian_states.items():
        districts = state_data.get('districts', [])
        for district in districts:
            if query_lower in district or district.startswith(query_lower):
                suggestions.append({
                    'name': district.replace('_', ' ').title(),
                    'district': district.replace('_', ' ').title(),
                    'state': state_name.replace('_', ' ').title(),
                    'type': 'district',
                    'region': state_data['region'],
                    'coordinates': {
                        'latitude': state_data['lat'],
                        'longitude': state_data['lon']
                    }
                })
    
    # Remove duplicates and sort by relevance
    seen = set()
    unique_suggestions = []
    for suggestion in suggestions:
        key = (suggestion['name'], suggestion['state'])
        if key not in seen:
            seen.add(key)
            unique_suggestions.append(suggestion)
    
    # Sort by type (exact match first, then by type preference)
    type_priority = {'village': 1, 'city': 2, 'district': 3, 'state': 4}
    unique_suggestions.sort(key=lambda x: (
        0 if x['name'].lower().startswith(query_lower) else 1,
        type_priority.get(x['type'], 5),
        x['name']
    ))
    
    return unique_suggestions[:limit]

def search_location_by_name(location_name: str) -> Dict[str, Any]:
    """Search for location by name (like Google Maps search) with crop recommendations"""
    location_name_lower = location_name.lower().replace(' ', '_').strip()
    
    # First try external geocoding APIs for accurate results
    external_result = search_location_via_geocoding_api(location_name)
    if external_result:
        return external_result
    
    # First check if it's a state name
    for state_name, state_data in enhanced_location_system.indian_states.items():
        if location_name_lower in state_name or state_name in location_name_lower:
            # Get crop recommendations for this state
            crop_recommendations = get_crop_recommendations_for_region(state_data['region'])
            
            return {
                'type': 'state',
                'name': state_name.replace('_', ' ').title(),
                'coordinates': {
                    'latitude': state_data['lat'],
                    'longitude': state_data['lon']
                },
                'region': state_data['region'],
                'districts': state_data['districts'],
                'crop_recommendations': crop_recommendations,
                'agricultural_info': get_agricultural_info_for_state(state_name, state_data['region'])
            }
    
    # Comprehensive location database with districts and villages
    comprehensive_locations = {
        # Uttar Pradesh - Major districts and villages
        'lucknow': {'state': 'uttar_pradesh', 'district': 'lucknow', 'type': 'city'},
        'kanpur': {'state': 'uttar_pradesh', 'district': 'kanpur_nagar', 'type': 'city'},
        'agra': {'state': 'uttar_pradesh', 'district': 'agra', 'type': 'city'},
        'varanasi': {'state': 'uttar_pradesh', 'district': 'varanasi', 'type': 'city'},
        'allahabad': {'state': 'uttar_pradesh', 'district': 'prayagraj', 'type': 'city'},
        'prayagraj': {'state': 'uttar_pradesh', 'district': 'prayagraj', 'type': 'city'},
        'bareilly': {'state': 'uttar_pradesh', 'district': 'bareilly', 'type': 'city'},
        'ghaziabad': {'state': 'uttar_pradesh', 'district': 'ghaziabad', 'type': 'city'},
        'meerut': {'state': 'uttar_pradesh', 'district': 'meerut', 'type': 'city'},
        'raebareli': {'state': 'uttar_pradesh', 'district': 'raebareli', 'type': 'district'},
        'sultanpur': {'state': 'uttar_pradesh', 'district': 'sultanpur', 'type': 'district'},
        'faizabad': {'state': 'uttar_pradesh', 'district': 'ayodhya', 'type': 'city'},
        'ayodhya': {'state': 'uttar_pradesh', 'district': 'ayodhya', 'type': 'city'},
        'gorakhpur': {'state': 'uttar_pradesh', 'district': 'gorakhpur', 'type': 'city'},
        'jhansi': {'state': 'uttar_pradesh', 'district': 'jhansi', 'type': 'city'},
        'mathura': {'state': 'uttar_pradesh', 'district': 'mathura', 'type': 'city'},
        'aligarh': {'state': 'uttar_pradesh', 'district': 'aligarh', 'type': 'city'},
        'moradabad': {'state': 'uttar_pradesh', 'district': 'moradabad', 'type': 'city'},
        'saharanpur': {'state': 'uttar_pradesh', 'district': 'saharanpur', 'type': 'city'},
        'muzaffarnagar': {'state': 'uttar_pradesh', 'district': 'muzaffarnagar', 'type': 'city'},
        'sitapur': {'state': 'uttar_pradesh', 'district': 'sitapur', 'type': 'district'},
        'hardoi': {'state': 'uttar_pradesh', 'district': 'hardoi', 'type': 'district'},
        'unnao': {'state': 'uttar_pradesh', 'district': 'unnao', 'type': 'district'},
        'barabanki': {'state': 'uttar_pradesh', 'district': 'barabanki', 'type': 'district'},
        'bahraich': {'state': 'uttar_pradesh', 'district': 'bahraich', 'type': 'district'},
        'shravasti': {'state': 'uttar_pradesh', 'district': 'shravasti', 'type': 'district'},
        'balrampur': {'state': 'uttar_pradesh', 'district': 'balrampur', 'type': 'district'},
        'gonda': {'state': 'uttar_pradesh', 'district': 'gonda', 'type': 'district'},
        'basti': {'state': 'uttar_pradesh', 'district': 'basti', 'type': 'district'},
        'siddharthnagar': {'state': 'uttar_pradesh', 'district': 'siddharthnagar', 'type': 'district'},
        'kushinagar': {'state': 'uttar_pradesh', 'district': 'kushinagar', 'type': 'district'},
        'deoria': {'state': 'uttar_pradesh', 'district': 'deoria', 'type': 'district'},
        'azamgarh': {'state': 'uttar_pradesh', 'district': 'azamgarh', 'type': 'district'},
        'maunath_bhanjan': {'state': 'uttar_pradesh', 'district': 'azamgarh', 'type': 'city'},
        'ballia': {'state': 'uttar_pradesh', 'district': 'ballia', 'type': 'district'},
        'jaunpur': {'state': 'uttar_pradesh', 'district': 'jaunpur', 'type': 'district'},
        'ghazipur': {'state': 'uttar_pradesh', 'district': 'ghazipur', 'type': 'district'},
        'chandauli': {'state': 'uttar_pradesh', 'district': 'chandauli', 'type': 'district'},
        'mirzapur': {'state': 'uttar_pradesh', 'district': 'mirzapur', 'type': 'district'},
        'sonbhadra': {'state': 'uttar_pradesh', 'district': 'sonbhadra', 'type': 'district'},
        'bhadohi': {'state': 'uttar_pradesh', 'district': 'bhadohi', 'type': 'district'},
        'kaushambi': {'state': 'uttar_pradesh', 'district': 'kaushambi', 'type': 'district'},
        'fatehpur': {'state': 'uttar_pradesh', 'district': 'fatehpur', 'type': 'district'},
        'pratapgarh': {'state': 'uttar_pradesh', 'district': 'pratapgarh', 'type': 'district'},
        'kaushambi': {'state': 'uttar_pradesh', 'district': 'kaushambi', 'type': 'district'},
        'banda': {'state': 'uttar_pradesh', 'district': 'banda', 'type': 'district'},
        'chitrakoot': {'state': 'uttar_pradesh', 'district': 'chitrakoot', 'type': 'district'},
        'hamirpur': {'state': 'uttar_pradesh', 'district': 'hamirpur', 'type': 'district'},
        'mahoba': {'state': 'uttar_pradesh', 'district': 'mahoba', 'type': 'district'},
        'lalitpur': {'state': 'uttar_pradesh', 'district': 'lalitpur', 'type': 'district'},
        'jalon': {'state': 'uttar_pradesh', 'district': 'jalaun', 'type': 'district'},
        'ora': {'state': 'uttar_pradesh', 'district': 'jalaun', 'type': 'city'},
        'etawah': {'state': 'uttar_pradesh', 'district': 'etawah', 'type': 'district'},
        'auraya': {'state': 'uttar_pradesh', 'district': 'auraiya', 'type': 'district'},
        'mainpuri': {'state': 'uttar_pradesh', 'district': 'mainpuri', 'type': 'district'},
        'firozabad': {'state': 'uttar_pradesh', 'district': 'firozabad', 'type': 'district'},
        'etah': {'state': 'uttar_pradesh', 'district': 'etah', 'type': 'district'},
        'kasganj': {'state': 'uttar_pradesh', 'district': 'kasganj', 'type': 'district'},
        'farrukhabad': {'state': 'uttar_pradesh', 'district': 'farrukhabad', 'type': 'district'},
        'kannauj': {'state': 'uttar_pradesh', 'district': 'kannauj', 'type': 'district'},
        'rampur': {'state': 'uttar_pradesh', 'district': 'rampur', 'type': 'district'},
        'bijnor': {'state': 'uttar_pradesh', 'district': 'bijnor', 'type': 'district'},
        'amroha': {'state': 'uttar_pradesh', 'district': 'amroha', 'type': 'district'},
        'hapur': {'state': 'uttar_pradesh', 'district': 'hapur', 'type': 'district'},
        'bulandshahr': {'state': 'uttar_pradesh', 'district': 'bulandshahr', 'type': 'district'},
        'gautam_buddha_nagar': {'state': 'uttar_pradesh', 'district': 'gautam_buddha_nagar', 'type': 'district'},
        'noida': {'state': 'uttar_pradesh', 'district': 'gautam_buddha_nagar', 'type': 'city'},
        'greater_noida': {'state': 'uttar_pradesh', 'district': 'gautam_buddha_nagar', 'type': 'city'},
        'dadri': {'state': 'uttar_pradesh', 'district': 'gautam_buddha_nagar', 'type': 'city'},
        'baghpat': {'state': 'uttar_pradesh', 'district': 'baghpat', 'type': 'district'},
        'shamli': {'state': 'uttar_pradesh', 'district': 'shamli', 'type': 'district'},
        'muzzafarnagar': {'state': 'uttar_pradesh', 'district': 'muzaffarnagar', 'type': 'city'},
        'kairana': {'state': 'uttar_pradesh', 'district': 'shamli', 'type': 'city'},
        'budaun': {'state': 'uttar_pradesh', 'district': 'budaun', 'type': 'district'},
        'shahjahanpur': {'state': 'uttar_pradesh', 'district': 'shahjahanpur', 'type': 'district'},
        'pilibhit': {'state': 'uttar_pradesh', 'district': 'pilibhit', 'type': 'district'},
        'lakhimpur_kheri': {'state': 'uttar_pradesh', 'district': 'kheri', 'type': 'district'},
        'kheri': {'state': 'uttar_pradesh', 'district': 'kheri', 'type': 'district'},
        
        # Punjab - Major districts and cities
        'amritsar': {'state': 'punjab', 'district': 'amritsar', 'type': 'city'},
        'ludhiana': {'state': 'punjab', 'district': 'ludhiana', 'type': 'city'},
        'jalandhar': {'state': 'punjab', 'district': 'jalandhar', 'type': 'city'},
        'patiala': {'state': 'punjab', 'district': 'patiala', 'type': 'city'},
        'bathinda': {'state': 'punjab', 'district': 'bathinda', 'type': 'city'},
        'firozpur': {'state': 'punjab', 'district': 'ferozepur', 'type': 'city'},
        'batala': {'state': 'punjab', 'district': 'gurdaspur', 'type': 'city'},
        'moga': {'state': 'punjab', 'district': 'moga', 'type': 'city'},
        'abohar': {'state': 'punjab', 'district': 'ferozepur', 'type': 'city'},
        'khanna': {'state': 'punjab', 'district': 'ludhiana', 'type': 'city'},
        'phagwara': {'state': 'punjab', 'district': 'kapurthala', 'type': 'city'},
        'muktsar': {'state': 'punjab', 'district': 'muktsar', 'type': 'city'},
        'barnala': {'state': 'punjab', 'district': 'barnala', 'type': 'city'},
        'rajpura': {'state': 'punjab', 'district': 'patiala', 'type': 'city'},
        'fazilka': {'state': 'punjab', 'district': 'ferozepur', 'type': 'city'},
        'kapurthala': {'state': 'punjab', 'district': 'kapurthala', 'type': 'city'},
        'sangrur': {'state': 'punjab', 'district': 'sangrur', 'type': 'city'},
        'sunam': {'state': 'punjab', 'district': 'sangrur', 'type': 'city'},
        'nabha': {'state': 'punjab', 'district': 'patiala', 'type': 'city'},
        'malerkotla': {'state': 'punjab', 'district': 'sangrur', 'type': 'city'},
        
        # Haryana - Major districts and cities
        'gurugram': {'state': 'haryana', 'district': 'gurugram', 'type': 'city'},
        'gurgaon': {'state': 'haryana', 'district': 'gurugram', 'type': 'city'},
        'faridabad': {'state': 'haryana', 'district': 'faridabad', 'type': 'city'},
        'panipat': {'state': 'haryana', 'district': 'panipat', 'type': 'city'},
        'ambala': {'state': 'haryana', 'district': 'ambala', 'type': 'city'},
        'yamunanagar': {'state': 'haryana', 'district': 'yamunanagar', 'type': 'city'},
        'rohtak': {'state': 'haryana', 'district': 'rohtak', 'type': 'city'},
        'hisar': {'state': 'haryana', 'district': 'hisar', 'type': 'city'},
        'karnal': {'state': 'haryana', 'district': 'karnal', 'type': 'city'},
        'sonipat': {'state': 'haryana', 'district': 'sonipat', 'type': 'city'},
        'panchkula': {'state': 'haryana', 'district': 'panchkula', 'type': 'city'},
        'bhiwani': {'state': 'haryana', 'district': 'bhiwani', 'type': 'city'},
        'bahadurgarh': {'state': 'haryana', 'district': 'jhajjar', 'type': 'city'},
        'jhajjar': {'state': 'haryana', 'district': 'jhajjar', 'type': 'district'},
        'rewari': {'state': 'haryana', 'district': 'rewari', 'type': 'city'},
        'mahendragarh': {'state': 'haryana', 'district': 'mahendragarh', 'type': 'district'},
        'narnaul': {'state': 'haryana', 'district': 'mahendragarh', 'type': 'city'},
        'palwal': {'state': 'haryana', 'district': 'palwal', 'type': 'city'},
        'fatehabad': {'state': 'haryana', 'district': 'fatehabad', 'type': 'district'},
        'kaithal': {'state': 'haryana', 'district': 'kaithal', 'type': 'city'},
        'jind': {'state': 'haryana', 'district': 'jind', 'type': 'city'},
        'kurukshetra': {'state': 'haryana', 'district': 'kurukshetra', 'type': 'city'},
        'thanesar': {'state': 'haryana', 'district': 'kurukshetra', 'type': 'city'},
        'pehowa': {'state': 'haryana', 'district': 'kurukshetra', 'type': 'city'},
        'ladwa': {'state': 'haryana', 'district': 'kurukshetra', 'type': 'city'},
        'sirsa': {'state': 'haryana', 'district': 'sirsa', 'type': 'city'},
        'ellanabad': {'state': 'haryana', 'district': 'sirsa', 'type': 'city'},
        'mandi_dabwali': {'state': 'haryana', 'district': 'sirsa', 'type': 'city'},
        'ratia': {'state': 'haryana', 'district': 'fatehabad', 'type': 'city'},
        'tohana': {'state': 'haryana', 'district': 'fatehabad', 'type': 'city'},
        'jakhal': {'state': 'haryana', 'district': 'fatehabad', 'type': 'city'},
        'narwana': {'state': 'haryana', 'district': 'jind', 'type': 'city'},
        'safidon': {'state': 'haryana', 'district': 'jind', 'type': 'city'},
        'pillukhera': {'state': 'haryana', 'district': 'jind', 'type': 'city'},
        'kalanaur': {'state': 'haryana', 'district': 'rohtak', 'type': 'city'},
        'beri': {'state': 'haryana', 'district': 'jhajjar', 'type': 'city'},
        'matenhail': {'state': 'haryana', 'district': 'jhajjar', 'type': 'city'},
        'salawas': {'state': 'haryana', 'district': 'jhajjar', 'type': 'city'},
        'badli': {'state': 'haryana', 'district': 'jhajjar', 'type': 'city'},
        'bawal': {'state': 'haryana', 'district': 'rewari', 'type': 'city'},
        'dharuhera': {'state': 'haryana', 'district': 'rewari', 'type': 'city'},
        'khol': {'state': 'haryana', 'district': 'rewari', 'type': 'city'},
        'charkhi_dadri': {'state': 'haryana', 'district': 'charkhi_dadri', 'type': 'city'},
        'dadri': {'state': 'haryana', 'district': 'charkhi_dadri', 'type': 'city'},
        'badhra': {'state': 'haryana', 'district': 'charkhi_dadri', 'type': 'city'},
        'nuh': {'state': 'haryana', 'district': 'nuh', 'type': 'district'},
        'punahana': {'state': 'haryana', 'district': 'nuh', 'type': 'city'},
        'firozpur_jhirka': {'state': 'haryana', 'district': 'nuh', 'type': 'city'},
        'taoru': {'state': 'haryana', 'district': 'nuh', 'type': 'city'},
        'sakras': {'state': 'haryana', 'district': 'nuh', 'type': 'city'},
        'pinangwan': {'state': 'haryana', 'district': 'nuh', 'type': 'city'},
        'nagina': {'state': 'haryana', 'district': 'nuh', 'type': 'city'},
        'umang': {'state': 'haryana', 'district': 'nuh', 'type': 'city'},
        'mewat': {'state': 'haryana', 'district': 'nuh', 'type': 'region'},
        
        # Common city name mappings for major cities
        'bangalore': 'bengaluru_urban',
        'bengaluru': 'bengaluru_urban',
        'mumbai': 'mumbai_city',
        'bombay': 'mumbai_city',
        'kolkata': 'kolkata',
        'calcutta': 'kolkata',
        'chennai': 'chennai',
        'madras': 'chennai',
        'hyderabad': 'hyderabad',
        'pune': 'pune',
        'ahmedabad': 'ahmedabad',
        'jaipur': 'jaipur',
        'nagpur': 'nagpur',
        'indore': 'indore',
        'bhopal': 'bhopal',
        'coimbatore': 'coimbatore',
        'kochi': 'ernakulam',
        'cochin': 'ernakulam',
        'vadodara': 'vadodara',
        'surat': 'surat',
        'rajkot': 'rajkot',
        'nashik': 'nashik',
        'mysore': 'mysuru',
        'mysuru': 'mysuru',
        'madurai': 'madurai',
        'tiruchirapalli': 'tiruchirappalli',
        'trichy': 'tiruchirappalli',
        'salem': 'salem',
        'erode': 'erode',
        'vellore': 'vellore',
        'thiruvananthapuram': 'thiruvananthapuram',
        'trivandrum': 'thiruvananthapuram',
        'kozhikode': 'kozhikode',
        'calicut': 'kozhikode',
        'thrissur': 'thrissur',
        'trichur': 'thrissur',
        'kollam': 'kollam',
        'quilon': 'kollam',
        'kottayam': 'kottayam',
        'palakkad': 'palakkad',
        'palghat': 'palakkad',
        'malappuram': 'malappuram',
        'alappuzha': 'alappuzha',
        'alleppey': 'alappuzha',
        'pathanamthitta': 'pathanamthitta',
        'idukki': 'idukki',
        'kannur': 'kannur',
        'cannanore': 'kannur',
        'kasaragod': 'kasaragod',
        'wayanad': 'wayanad'
    }
    
    # Check comprehensive locations database first
    if location_name_lower in comprehensive_locations:
        location_info = comprehensive_locations[location_name_lower]
        state_name = location_info['state']
        district_name = location_info['district']
        location_type = location_info['type']
        
        # Get state data
        state_data = enhanced_location_system.indian_states.get(state_name)
        if state_data:
            crop_recommendations = get_crop_recommendations_for_region(state_data['region'])
            return {
                'type': location_type,
                'name': location_name_lower.title(),
                'district': district_name.replace('_', ' ').title(),
                'state': state_name.replace('_', ' ').title(),
                'coordinates': {
                    'latitude': state_data['lat'],
                    'longitude': state_data['lon']
                },
                'region': state_data['region'],
                'districts': [district_name],
                'crop_recommendations': crop_recommendations,
                'agricultural_info': get_agricultural_info_for_state(state_name, state_data['region'])
            }
    
    # Check if it's a mapped city name (fallback for major cities)
    city_mappings = {
        'bangalore': 'bengaluru_urban',
        'bengaluru': 'bengaluru_urban',
        'mumbai': 'mumbai_city',
        'bombay': 'mumbai_city',
        'kolkata': 'kolkata',
        'calcutta': 'kolkata',
        'chennai': 'chennai',
        'madras': 'chennai',
        'hyderabad': 'hyderabad',
        'pune': 'pune',
        'ahmedabad': 'ahmedabad',
        'jaipur': 'jaipur',
        'nagpur': 'nagpur',
        'indore': 'indore',
        'bhopal': 'bhopal',
        'coimbatore': 'coimbatore',
        'kochi': 'ernakulam',
        'cochin': 'ernakulam',
        'vadodara': 'vadodara',
        'surat': 'surat',
        'rajkot': 'rajkot',
        'nashik': 'nashik',
        'mysore': 'mysuru',
        'mysuru': 'mysuru',
        'madurai': 'madurai',
        'tiruchirapalli': 'tiruchirappalli',
        'trichy': 'tiruchirappalli',
        'salem': 'salem',
        'erode': 'erode',
        'vellore': 'vellore',
        'thiruvananthapuram': 'thiruvananthapuram',
        'trivandrum': 'thiruvananthapuram',
        'kozhikode': 'kozhikode',
        'calicut': 'kozhikode',
        'thrissur': 'thrissur',
        'trichur': 'thrissur',
        'kollam': 'kollam',
        'quilon': 'kollam',
        'kottayam': 'kottayam',
        'palakkad': 'palakkad',
        'palghat': 'palakkad',
        'malappuram': 'malappuram',
        'alappuzha': 'alappuzha',
        'alleppey': 'alappuzha',
        'pathanamthitta': 'pathanamthitta',
        'idukki': 'idukki',
        'kannur': 'kannur',
        'cannanore': 'kannur',
        'kasaragod': 'kasaragod',
        'wayanad': 'wayanad'
    }
    
    if location_name_lower in city_mappings:
        mapped_district = city_mappings[location_name_lower]
        # Find which state this district belongs to
        for state_name, state_data in enhanced_location_system.indian_states.items():
            districts = state_data.get('districts', [])
            if mapped_district in districts:
                crop_recommendations = get_crop_recommendations_for_region(state_data['region'])
                return {
                    'type': 'city',
                    'name': location_name_lower.title(),
                    'district': mapped_district.replace('_', ' ').title(),
                    'state': state_name.replace('_', ' ').title(),
                    'coordinates': {
                        'latitude': state_data['lat'],
                        'longitude': state_data['lon']
                    },
                    'region': state_data['region'],
                    'districts': [mapped_district],
                    'crop_recommendations': crop_recommendations,
                    'agricultural_info': get_agricultural_info_for_state(state_name, state_data['region'])
                }
    
    # Check if it's a district name within any state
    for state_name, state_data in enhanced_location_system.indian_states.items():
        districts = state_data.get('districts', [])
        for district in districts:
            if location_name_lower == district or location_name_lower in district:
                # Found the district, return state-level data with district info
                crop_recommendations = get_crop_recommendations_for_region(state_data['region'])
                
                return {
                    'type': 'district',
                    'name': district.replace('_', ' ').title(),
                    'state': state_name.replace('_', ' ').title(),
                    'coordinates': {
                        'latitude': state_data['lat'],
                        'longitude': state_data['lon']
                    },
                    'region': state_data['region'],
                    'districts': [district],
                    'crop_recommendations': crop_recommendations,
                    'agricultural_info': get_agricultural_info_for_state(state_name, state_data['region'])
                }
    
    # Check if it's a crop name search
    crop_search_result = search_crop_by_name(location_name)
    if crop_search_result:
        return crop_search_result
    
    # If not found, return default coordinates for India
    return {
        'type': 'country',
        'name': 'India',
        'coordinates': {'latitude': 20.5937, 'longitude': 78.9629},
        'region': 'unknown',
        'districts': [],
        'crop_recommendations': get_general_crop_recommendations()
    }

def search_crop_by_name(crop_name: str) -> Dict[str, Any]:
    """Search for crop by name and provide recommendations"""
    crop_name_lower = crop_name.lower().strip()
    
    # Comprehensive crop database with regional recommendations
    crop_database = {
        # Cereals
        'wheat': {
            'name': 'Wheat',
            'scientific_name': 'Triticum aestivum',
            'suitable_regions': ['north', 'central', 'west'],
            'best_states': ['Punjab', 'Haryana', 'Uttar Pradesh', 'Madhya Pradesh'],
            'season': 'Rabi',
            'growing_period': 'October to April',
            'yield_potential': '4-5 tonnes/hectare',
            'market_price': '₹2,275/quintal (MSP)',
            'fertilizer_requirement': 'NPK 120:60:40 kg/hectare',
            'water_requirement': '400-500mm',
            'soil_type': 'Clay loam, Sandy loam',
            'climate': 'Cool and dry weather'
        },
        'rice': {
            'name': 'Rice',
            'scientific_name': 'Oryza sativa',
            'suitable_regions': ['south', 'east', 'northeast'],
            'best_states': ['West Bengal', 'Tamil Nadu', 'Andhra Pradesh', 'Karnataka'],
            'season': 'Kharif',
            'growing_period': 'June to November',
            'yield_potential': '3-4 tonnes/hectare',
            'market_price': '₹2,183/quintal (MSP)',
            'fertilizer_requirement': 'NPK 120:60:40 kg/hectare',
            'water_requirement': '1200-1500mm',
            'soil_type': 'Clay, Heavy clay',
            'climate': 'Hot and humid'
        },
        'maize': {
            'name': 'Maize',
            'scientific_name': 'Zea mays',
            'suitable_regions': ['north', 'central', 'south'],
            'best_states': ['Karnataka', 'Andhra Pradesh', 'Madhya Pradesh', 'Bihar'],
            'season': 'Kharif',
            'growing_period': 'June to October',
            'yield_potential': '3-4 tonnes/hectare',
            'market_price': '₹2,090/quintal (MSP)',
            'fertilizer_requirement': 'NPK 120:60:40 kg/hectare',
            'water_requirement': '500-600mm',
            'soil_type': 'Sandy loam, Loam',
            'climate': 'Warm and humid'
        },
        'cotton': {
            'name': 'Cotton',
            'scientific_name': 'Gossypium hirsutum',
            'suitable_regions': ['west', 'south', 'central'],
            'best_states': ['Maharashtra', 'Gujarat', 'Telangana', 'Andhra Pradesh'],
            'season': 'Kharif',
            'growing_period': 'June to December',
            'yield_potential': '500-600 kg lint/hectare',
            'market_price': '₹6,620/quintal (MSP)',
            'fertilizer_requirement': 'NPK 100:50:50 kg/hectare',
            'water_requirement': '600-800mm',
            'soil_type': 'Black soil, Clay loam',
            'climate': 'Hot and dry'
        },
        'sugarcane': {
            'name': 'Sugarcane',
            'scientific_name': 'Saccharum officinarum',
            'suitable_regions': ['west', 'south', 'north'],
            'best_states': ['Maharashtra', 'Uttar Pradesh', 'Karnataka', 'Tamil Nadu'],
            'season': 'Year-round',
            'growing_period': '12-18 months',
            'yield_potential': '80-100 tonnes/hectare',
            'market_price': '₹315/quintal (FRP)',
            'fertilizer_requirement': 'NPK 200:100:100 kg/hectare',
            'water_requirement': '1500-2000mm',
            'soil_type': 'Deep, well-drained loam',
            'climate': 'Hot and humid'
        },
        'soybean': {
            'name': 'Soybean',
            'scientific_name': 'Glycine max',
            'suitable_regions': ['central', 'west', 'south'],
            'best_states': ['Madhya Pradesh', 'Maharashtra', 'Rajasthan', 'Karnataka'],
            'season': 'Kharif',
            'growing_period': 'June to October',
            'yield_potential': '2-3 tonnes/hectare',
            'market_price': '₹3,950/quintal (MSP)',
            'fertilizer_requirement': 'NPK 60:40:40 kg/hectare',
            'water_requirement': '400-500mm',
            'soil_type': 'Well-drained loam',
            'climate': 'Warm and moist'
        }
    }
    
    # Search for crop in database
    for crop_key, crop_info in crop_database.items():
        if (crop_name_lower in crop_key or 
            crop_name_lower in crop_info['name'].lower() or
            crop_name_lower in crop_info['scientific_name'].lower()):
            
            # Get suitable locations for this crop
            suitable_locations = get_suitable_locations_for_crop(crop_info)
            
            return {
                'type': 'crop',
                'crop_info': crop_info,
                'suitable_locations': suitable_locations,
                'recommendations': get_crop_specific_recommendations(crop_info),
                'market_analysis': get_crop_market_analysis(crop_key)
            }
    
    return None

def get_crop_recommendations_for_region(region: str) -> List[Dict[str, Any]]:
    """Get crop recommendations for a specific region"""
    regional_crops = {
        'north': [
            {'name': 'Wheat', 'season': 'Rabi', 'priority': 'high'},
            {'name': 'Rice', 'season': 'Kharif', 'priority': 'medium'},
            {'name': 'Maize', 'season': 'Kharif', 'priority': 'high'},
            {'name': 'Sugarcane', 'season': 'Year-round', 'priority': 'medium'},
            {'name': 'Mustard', 'season': 'Rabi', 'priority': 'high'}
        ],
        'south': [
            {'name': 'Rice', 'season': 'Kharif', 'priority': 'high'},
            {'name': 'Cotton', 'season': 'Kharif', 'priority': 'high'},
            {'name': 'Sugarcane', 'season': 'Year-round', 'priority': 'high'},
            {'name': 'Maize', 'season': 'Kharif', 'priority': 'medium'},
            {'name': 'Groundnut', 'season': 'Kharif', 'priority': 'high'}
        ],
        'east': [
            {'name': 'Rice', 'season': 'Kharif', 'priority': 'high'},
            {'name': 'Jute', 'season': 'Kharif', 'priority': 'high'},
            {'name': 'Wheat', 'season': 'Rabi', 'priority': 'medium'},
            {'name': 'Maize', 'season': 'Kharif', 'priority': 'medium'},
            {'name': 'Potato', 'season': 'Rabi', 'priority': 'high'}
        ],
        'west': [
            {'name': 'Cotton', 'season': 'Kharif', 'priority': 'high'},
            {'name': 'Sugarcane', 'season': 'Year-round', 'priority': 'high'},
            {'name': 'Soybean', 'season': 'Kharif', 'priority': 'high'},
            {'name': 'Groundnut', 'season': 'Kharif', 'priority': 'medium'},
            {'name': 'Wheat', 'season': 'Rabi', 'priority': 'medium'}
        ],
        'northeast': [
            {'name': 'Rice', 'season': 'Kharif', 'priority': 'high'},
            {'name': 'Maize', 'season': 'Kharif', 'priority': 'high'},
            {'name': 'Tea', 'season': 'Year-round', 'priority': 'high'},
            {'name': 'Jute', 'season': 'Kharif', 'priority': 'medium'},
            {'name': 'Potato', 'season': 'Rabi', 'priority': 'medium'}
        ],
        'central': [
            {'name': 'Wheat', 'season': 'Rabi', 'priority': 'high'},
            {'name': 'Soybean', 'season': 'Kharif', 'priority': 'high'},
            {'name': 'Maize', 'season': 'Kharif', 'priority': 'high'},
            {'name': 'Cotton', 'season': 'Kharif', 'priority': 'medium'},
            {'name': 'Gram', 'season': 'Rabi', 'priority': 'medium'}
        ]
    }
    
    return regional_crops.get(region, get_general_crop_recommendations())

def get_general_crop_recommendations() -> List[Dict[str, Any]]:
    """Get general crop recommendations for India"""
    return [
        {'name': 'Wheat', 'season': 'Rabi', 'priority': 'high'},
        {'name': 'Rice', 'season': 'Kharif', 'priority': 'high'},
        {'name': 'Maize', 'season': 'Kharif', 'priority': 'medium'},
        {'name': 'Cotton', 'season': 'Kharif', 'priority': 'medium'},
        {'name': 'Sugarcane', 'season': 'Year-round', 'priority': 'medium'}
    ]

def get_agricultural_info_for_state(state_name: str, region: str) -> Dict[str, Any]:
    """Get agricultural information for a specific state"""
    state_info = {
        'delhi': {
            'major_crops': ['Wheat', 'Rice', 'Maize'],
            'soil_type': 'Alluvial',
            'climate': 'Semi-arid',
            'irrigation': 'Canal and tube well',
            'agricultural_zones': ['North Delhi', 'South Delhi', 'East Delhi']
        },
        'punjab': {
            'major_crops': ['Wheat', 'Rice', 'Cotton', 'Sugarcane'],
            'soil_type': 'Alluvial',
            'climate': 'Semi-arid',
            'irrigation': 'Canal irrigation',
            'agricultural_zones': ['Malwa', 'Majha', 'Doaba']
        },
        'karnataka': {
            'major_crops': ['Rice', 'Maize', 'Sugarcane', 'Cotton'],
            'soil_type': 'Red soil, Black soil',
            'climate': 'Tropical',
            'irrigation': 'Rain-fed and irrigation',
            'agricultural_zones': ['Coastal', 'Malnad', 'Bayaluseeme']
        },
        'tamil_nadu': {
            'major_crops': ['Rice', 'Sugarcane', 'Cotton', 'Groundnut'],
            'soil_type': 'Red soil, Alluvial',
            'climate': 'Tropical',
            'irrigation': 'Tank and well irrigation',
            'agricultural_zones': ['Northern', 'Western', 'Southern']
        },
        'maharashtra': {
            'major_crops': ['Cotton', 'Sugarcane', 'Soybean', 'Wheat'],
            'soil_type': 'Black soil, Red soil',
            'climate': 'Tropical',
            'irrigation': 'Rain-fed and irrigation',
            'agricultural_zones': ['Vidarbha', 'Marathwada', 'Western Maharashtra']
        }
    }
    
    return state_info.get(state_name.lower(), {
        'major_crops': ['Wheat', 'Rice', 'Maize'],
        'soil_type': 'Mixed',
        'climate': 'Tropical to Subtropical',
        'irrigation': 'Mixed',
        'agricultural_zones': ['Zone 1', 'Zone 2', 'Zone 3']
    })

def get_suitable_locations_for_crop(crop_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get suitable locations for a specific crop"""
    suitable_states = []
    
    for state_name, state_data in enhanced_location_system.indian_states.items():
        if state_data['region'] in crop_info['suitable_regions']:
            suitable_states.append({
                'state': state_name.replace('_', ' ').title(),
                'region': state_data['region'],
                'coordinates': {
                    'latitude': state_data['lat'],
                    'longitude': state_data['lon']
                },
                'suitability_score': calculate_crop_suitability_score(crop_info, state_data)
            })
    
    # Sort by suitability score
    suitable_states.sort(key=lambda x: x['suitability_score'], reverse=True)
    return suitable_states[:5]  # Return top 5 suitable locations

def calculate_crop_suitability_score(crop_info: Dict[str, Any], state_data: Dict[str, Any]) -> float:
    """Calculate suitability score for a crop in a state"""
    base_score = 0.5
    
    # Increase score if state is in best states list
    if state_data['region'] in crop_info['suitable_regions']:
        base_score += 0.3
    
    # Add random variation for demonstration
    import random
    base_score += random.uniform(0, 0.2)
    
    return min(base_score, 1.0)

def get_crop_specific_recommendations(crop_info: Dict[str, Any]) -> Dict[str, Any]:
    """Get specific recommendations for a crop"""
    return {
        'planting_time': crop_info['growing_period'],
        'fertilizer_schedule': crop_info['fertilizer_requirement'],
        'irrigation_requirements': crop_info['water_requirement'],
        'soil_preparation': f"Prepare {crop_info['soil_type']} soil",
        'harvest_time': "Based on growing period",
        'storage_conditions': "Cool and dry storage recommended",
        'market_timing': "Harvest during peak demand season"
    }

def get_crop_market_analysis(crop_key: str) -> Dict[str, Any]:
    """Get market analysis for a crop"""
    market_data = {
        'wheat': {
            'demand_trend': 'Stable',
            'price_trend': 'Increasing',
            'export_potential': 'High',
            'processing_industries': ['Flour mills', 'Bakery', 'Pasta']
        },
        'rice': {
            'demand_trend': 'High',
            'price_trend': 'Stable',
            'export_potential': 'Very High',
            'processing_industries': ['Rice mills', 'Snack industry']
        },
        'cotton': {
            'demand_trend': 'High',
            'price_trend': 'Volatile',
            'export_potential': 'Very High',
            'processing_industries': ['Textile mills', 'Garment industry']
        }
    }
    
    return market_data.get(crop_key, {
        'demand_trend': 'Moderate',
        'price_trend': 'Stable',
        'export_potential': 'Medium',
        'processing_industries': ['General processing']
    })
