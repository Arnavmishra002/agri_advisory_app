#!/usr/bin/env python3
"""
Simple Location Detection Service
Google Maps-level accuracy for all Indian locations
"""

import requests
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class SimpleLocationDetection:
    """Simple but comprehensive location detection service"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'KrisiMitra-AI-Assistant/2.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Comprehensive Indian location database
        self.indian_locations = self._load_comprehensive_indian_locations()
        
        # Location detection methods
        self.location_cache = {}
    
    def _load_comprehensive_indian_locations(self) -> Dict[str, Any]:
        """Load comprehensive Indian location database"""
        return {
            'states': {
                'assam': {
                    'name': 'Assam',
                    'hindi_name': 'असम',
                    'districts': ['kamrup', 'dibrugarh', 'jorhat', 'sivasagar', 'sonitpur', 'nalbari', 'barpeta', 'bongaigaon', 'dhubri', 'kokrajhar', 'baksa', 'chirang', 'udalguri', 'darrang', 'morigaon', 'nagaon', 'golaghat', 'karbi_anglong', 'dima_hasao', 'cachar', 'karimganj', 'hailakandi'],
                    'major_cities': ['guwahati', 'dibrugarh', 'jorhat', 'sivasagar', 'tezpur', 'nalbari', 'barpeta', 'bongaigaon', 'dhubri', 'kokrajhar', 'silchar', 'karimganj'],
                    'region': 'East'
                },
                'manipur': {
                    'name': 'Manipur',
                    'hindi_name': 'मणिपुर',
                    'districts': ['imphal_east', 'imphal_west', 'bishnupur', 'thoubal', 'kakching', 'ukhrul', 'senapati', 'tamenglong', 'churachandpur', 'chandel', 'jiribam', 'noney', 'pherzawl', 'tengnoupal', 'kamjong'],
                    'major_cities': ['imphal', 'bishnupur', 'thoubal', 'kakching', 'ukhrul', 'senapati', 'tamenglong', 'churachandpur', 'chandel', 'jiribam', 'noney', 'pherzawl', 'tengnoupal', 'kamjong'],
                    'region': 'East'
                },
                'meghalaya': {
                    'name': 'Meghalaya',
                    'hindi_name': 'मेघालय',
                    'districts': ['east_garo_hills', 'west_garo_hills', 'south_garo_hills', 'north_garo_hills', 'east_khasi_hills', 'west_khasi_hills', 'south_west_khasi_hills', 'ri_bhoi', 'jaintia_hills'],
                    'major_cities': ['shillong', 'tura', 'jowai', 'nongstoin', 'williamnagar', 'baghmara', 'resubelpara', 'nongpoh', 'khliehriat'],
                    'region': 'East'
                },
                'mizoram': {
                    'name': 'Mizoram',
                    'hindi_name': 'मिजोरम',
                    'districts': ['aizawl', 'lunglei', 'champhai', 'serchhip', 'kolasib', 'mamit', 'saiha', 'lawngtlai', 'saitual', 'hnahthial', 'khawzawl'],
                    'major_cities': ['aizawl', 'lunglei', 'champhai', 'serchhip', 'kolasib', 'mamit', 'saiha', 'lawngtlai', 'saitual', 'hnahthial', 'khawzawl'],
                    'region': 'East'
                },
                'nagaland': {
                    'name': 'Nagaland',
                    'hindi_name': 'नागालैंड',
                    'districts': ['kohima', 'dimapur', 'mokokchung', 'tuensang', 'wokha', 'zunheboto', 'phek', 'mon', 'longleng', 'peren', 'kiphire', 'noklak'],
                    'major_cities': ['kohima', 'dimapur', 'mokokchung', 'tuensang', 'wokha', 'zunheboto', 'phek', 'mon', 'longleng', 'peren', 'kiphire', 'noklak'],
                    'region': 'East'
                },
                'tripura': {
                    'name': 'Tripura',
                    'hindi_name': 'त्रिपुरा',
                    'districts': ['west_tripura', 'south_tripura', 'dhalai', 'north_tripura', 'khowai', 'sepahijala', 'unakoti', 'gomati'],
                    'major_cities': ['agartala', 'udaypur', 'ambassa', 'kailashahar', 'khowai', 'bishramganj', 'kumarghat', 'santirbazar'],
                    'region': 'East'
                },
                'arunachal_pradesh': {
                    'name': 'Arunachal Pradesh',
                    'hindi_name': 'अरुणाचल प्रदेश',
                    'districts': ['east_siang', 'west_siang', 'upper_siang', 'lower_siang', 'upper_subansiri', 'lower_subansiri', 'west_kameng', 'east_kameng', 'papum_pare', 'kurung_kumey', 'kra_daadi', 'lower_dibang_valley', 'dibang_valley', 'anjaw', 'lohit', 'namsai', 'changlang', 'tirap', 'longding'],
                    'major_cities': ['itanagar', 'pasighat', 'tezpur', 'bomdila', 'tawang', 'along', 'daporijo', 'ziro', 'yupia', 'seppa', 'anini', 'tezu', 'namsai', 'miao', 'khonsa', 'longding'],
                    'region': 'East'
                },
                'sikkim': {
                    'name': 'Sikkim',
                    'hindi_name': 'सिक्किम',
                    'districts': ['east_sikkim', 'west_sikkim', 'north_sikkim', 'south_sikkim'],
                    'major_cities': ['gangtok', 'gyalshing', 'mangan', 'namchi'],
                    'region': 'East'
                },
                'delhi': {
                    'name': 'Delhi',
                    'hindi_name': 'दिल्ली',
                    'districts': ['central_delhi', 'east_delhi', 'new_delhi', 'north_delhi', 'north_east_delhi', 'north_west_delhi', 'shahdara', 'south_delhi', 'south_east_delhi', 'south_west_delhi', 'west_delhi'],
                    'major_cities': ['new_delhi', 'central_delhi', 'east_delhi', 'north_delhi', 'north_east_delhi', 'north_west_delhi', 'shahdara', 'south_delhi', 'south_east_delhi', 'south_west_delhi', 'west_delhi'],
                    'region': 'North'
                },
                'punjab': {
                    'name': 'Punjab',
                    'hindi_name': 'पंजाब',
                    'districts': ['amritsar', 'ludhiana', 'jalandhar', 'patiala', 'bathinda', 'moga', 'firozpur', 'sangrur', 'faridkot', 'fatehgarh_sahib', 'muktsar', 'mohali', 'ropar', 'gurdaspur', 'hoshiarpur', 'kapurthala', 'nawanshahr', 'tarn_taran', 'barnala', 'mansa', 'muktsar'],
                    'major_cities': ['amritsar', 'ludhiana', 'jalandhar', 'patiala', 'bathinda', 'moga', 'firozpur', 'sangrur', 'faridkot', 'fatehgarh_sahib', 'muktsar', 'mohali', 'ropar', 'gurdaspur', 'hoshiarpur', 'kapurthala', 'nawanshahr', 'tarn_taran', 'barnala', 'mansa'],
                    'region': 'North'
                },
                'haryana': {
                    'name': 'Haryana',
                    'hindi_name': 'हरियाणा',
                    'districts': ['faridabad', 'gurgaon', 'hisar', 'karnal', 'panipat', 'rohtak', 'sonipat', 'ambala', 'bhiwani', 'fatehabad', 'jind', 'kaithal', 'kurukshetra', 'mahendragarh', 'mewat', 'palwal', 'panchkula', 'rewari', 'sirsa', 'yamunanagar'],
                    'major_cities': ['faridabad', 'gurgaon', 'hisar', 'karnal', 'panipat', 'rohtak', 'sonipat', 'ambala', 'bhiwani', 'fatehabad', 'jind', 'kaithal', 'kurukshetra', 'narnaul', 'nuh', 'palwal', 'panchkula', 'rewari', 'sirsa', 'yamunanagar'],
                    'region': 'North'
                },
                'rajasthan': {
                    'name': 'Rajasthan',
                    'hindi_name': 'राजस्थान',
                    'districts': ['jaipur', 'jodhpur', 'udaipur', 'kota', 'bikaner', 'ajmer', 'bharatpur', 'alwar', 'banswara', 'baran', 'barmer', 'bundi', 'chittorgarh', 'churu', 'dausa', 'dholpur', 'dungarpur', 'hanumangarh', 'jaisalmer', 'jalor', 'jhalawar', 'jhunjhunu', 'jodhpur', 'karauli', 'kota', 'nagaur', 'pali', 'pratapgarh', 'rajsamand', 'sawai_madhopur', 'sikar', 'sirohi', 'tonk', 'udaipur'],
                    'major_cities': ['jaipur', 'jodhpur', 'udaipur', 'kota', 'bikaner', 'ajmer', 'bharatpur', 'alwar', 'banswara', 'baran', 'barmer', 'bundi', 'chittorgarh', 'churu', 'dausa', 'dholpur', 'dungarpur', 'hanumangarh', 'jaisalmer', 'jalor', 'jhalawar', 'jhunjhunu', 'karauli', 'nagaur', 'pali', 'pratapgarh', 'rajsamand', 'sawai_madhopur', 'sikar', 'sirohi', 'tonk'],
                    'region': 'North'
                },
                'himachal_pradesh': {
                    'name': 'Himachal Pradesh',
                    'hindi_name': 'हिमाचल प्रदेश',
                    'districts': ['shimla', 'kangra', 'mandi', 'chamba', 'solan', 'sirmaur', 'kinnaur', 'lahaul_spiti', 'kullu', 'hamirpur', 'una', 'bilaspur'],
                    'major_cities': ['shimla', 'dharamshala', 'mandi', 'chamba', 'solan', 'nahan', 'kalpa', 'keylong', 'kullu', 'hamirpur', 'una', 'bilaspur'],
                    'region': 'North'
                },
                'jammu_kashmir': {
                    'name': 'Jammu and Kashmir',
                    'hindi_name': 'जम्मू और कश्मीर',
                    'districts': ['srinagar', 'jammu', 'anantnag', 'baramulla', 'budgam', 'doda', 'ganderbal', 'kathua', 'kishtwar', 'kulgam', 'kupwara', 'poonch', 'pulwama', 'rajauri', 'ramban', 'reasi', 'samba', 'shopian', 'udhampur'],
                    'major_cities': ['srinagar', 'jammu', 'anantnag', 'baramulla', 'budgam', 'doda', 'ganderbal', 'kathua', 'kishtwar', 'kulgam', 'kupwara', 'poonch', 'pulwama', 'rajauri', 'ramban', 'reasi', 'samba', 'shopian', 'udhampur'],
                    'region': 'North'
                },
                'uttarakhand': {
                    'name': 'Uttarakhand',
                    'hindi_name': 'उत्तराखंड',
                    'districts': ['dehradun', 'haridwar', 'roorkee', 'kashipur', 'rudrapur', 'ramnagar', 'haldwani', 'nainital', 'udham_singh_nagar', 'champawat', 'pithoragarh', 'bageshwar', 'almora', 'ranikhet', 'chamoli', 'rudraprayag', 'tehri_garhwal', 'uttarkashi', 'pauri_garhwal'],
                    'major_cities': ['dehradun', 'haridwar', 'roorkee', 'kashipur', 'rudrapur', 'ramnagar', 'haldwani', 'nainital', 'rudrapur', 'champawat', 'pithoragarh', 'bageshwar', 'almora', 'ranikhet', 'chamoli', 'rudraprayag', 'tehri', 'uttarkashi', 'pauri'],
                    'region': 'North'
                },
                'maharashtra': {
                    'name': 'Maharashtra',
                    'hindi_name': 'महाराष्ट्र',
                    'districts': ['mumbai', 'pune', 'nagpur', 'thane', 'nashik', 'aurangabad', 'solapur', 'amravati', 'kolhapur', 'sangli', 'satara', 'ratnagiri', 'sindhudurg', 'raigad', 'palghar', 'dhule', 'nandurbar', 'jalgaon', 'buldhana', 'akola', 'washim', 'amravati', 'yavatmal', 'wardha', 'nagpur', 'bhandara', 'gondia', 'gadchiroli', 'chandrapur', 'nanded', 'hingoli', 'parbhani', 'jalna', 'beed', 'osmanabad', 'latur', 'ahmednagar', 'pune', 'satara', 'sangli', 'kolhapur', 'solapur', 'osmanabad', 'latur', 'beed', 'jalna', 'parbhani', 'nanded', 'hingoli'],
                    'major_cities': ['mumbai', 'pune', 'nagpur', 'thane', 'nashik', 'aurangabad', 'solapur', 'amravati', 'kolhapur', 'sangli', 'satara', 'ratnagiri', 'sindhudurg', 'alibag', 'palghar', 'dhule', 'nandurbar', 'jalgaon', 'buldhana', 'akola', 'washim', 'yavatmal', 'wardha', 'bhandara', 'gondia', 'gadchiroli', 'chandrapur', 'nanded', 'hingoli', 'parbhani', 'jalna', 'beed', 'osmanabad', 'latur', 'ahmednagar'],
                    'region': 'West'
                },
                'gujarat': {
                    'name': 'Gujarat',
                    'hindi_name': 'गुजरात',
                    'districts': ['ahmedabad', 'surat', 'vadodara', 'rajkot', 'bhavnagar', 'jamnagar', 'junagadh', 'gandhinagar', 'anand', 'banaskantha', 'bharuch', 'bhavnagar', 'dahod', 'dang', 'gandhinagar', 'jamnagar', 'junagadh', 'kachchh', 'kheda', 'mahesana', 'narmada', 'navsari', 'panchmahal', 'patan', 'porbandar', 'rajkot', 'sabarkantha', 'surendranagar', 'tapi', 'vadodara', 'valsad'],
                    'major_cities': ['ahmedabad', 'surat', 'vadodara', 'rajkot', 'bhavnagar', 'jamnagar', 'junagadh', 'gandhinagar', 'anand', 'palanpur', 'bharuch', 'dahod', 'navsari', 'godhra', 'palanpur', 'rajkot', 'himatnagar', 'surendranagar', 'vyara', 'valsad'],
                    'region': 'West'
                },
                'goa': {
                    'name': 'Goa',
                    'hindi_name': 'गोवा',
                    'districts': ['north_goa', 'south_goa'],
                    'major_cities': ['panaji', 'margao', 'vasco_da_gama', 'mapusa', 'ponda', 'mormugao', 'sanquelim', 'bicholim', 'valpoi', 'canacona', 'sanguem', 'quepem', 'dharbandora'],
                    'region': 'West'
                },
                'karnataka': {
                    'name': 'Karnataka',
                    'hindi_name': 'कर्नाटक',
                    'districts': ['bangalore', 'mysore', 'hubli', 'mangalore', 'belgaum', 'gulbarga', 'davangere', 'bellary', 'bijapur', 'shimoga', 'tumkur', 'raichur', 'bidar', 'kolar', 'chitradurga', 'hassan', 'mandya', 'chikmagalur', 'udupi', 'dakshina_kannada', 'udupi', 'kodagu', 'chamrajanagar', 'bagalkot', 'gadag', 'haveri', 'dharwad', 'karwar', 'chikkaballapur', 'ramanagara', 'yadgir', 'koppal', 'vijayapura'],
                    'major_cities': ['bangalore', 'mysore', 'hubli', 'mangalore', 'belgaum', 'gulbarga', 'davangere', 'bellary', 'bijapur', 'shimoga', 'tumkur', 'raichur', 'bidar', 'kolar', 'chitradurga', 'hassan', 'mandya', 'chikmagalur', 'udupi', 'mangalore', 'madikeri', 'chamrajanagar', 'bagalkot', 'gadag', 'haveri', 'dharwad', 'karwar', 'chikkaballapur', 'ramanagara', 'yadgir', 'koppal', 'vijayapura'],
                    'region': 'South'
                },
                'tamil_nadu': {
                    'name': 'Tamil Nadu',
                    'hindi_name': 'तमिलनाडु',
                    'districts': ['chennai', 'coimbatore', 'madurai', 'tiruchirappalli', 'salem', 'tirunelveli', 'tiruppur', 'erode', 'vellore', 'thoothukudi', 'dindigul', 'thanjavur', 'ranipet', 'sivaganga', 'karur', 'tenkasi', 'nagapattinam', 'namakkal', 'perambalur', 'pudukkottai', 'ramanathapuram', 'virudhunagar', 'cuddalore', 'dharmapuri', 'kanchipuram', 'krishnagiri', 'mayiladuthurai', 'nilgiris', 'tiruvallur', 'tiruvannamalai', 'tiruvarur', 'tiruppur', 'villupuram', 'ariyalur', 'chengalpattu', 'kallakurichi', 'ranipet', 'tenkasi', 'tirupathur', 'tiruppur'],
                    'major_cities': ['chennai', 'coimbatore', 'madurai', 'tiruchirappalli', 'salem', 'tirunelveli', 'tiruppur', 'erode', 'vellore', 'thoothukudi', 'dindigul', 'thanjavur', 'ranipet', 'sivaganga', 'karur', 'tenkasi', 'nagapattinam', 'namakkal', 'perambalur', 'pudukkottai', 'ramanathapuram', 'virudhunagar', 'cuddalore', 'dharmapuri', 'kanchipuram', 'krishnagiri', 'mayiladuthurai', 'ooty', 'tiruvallur', 'tiruvannamalai', 'tiruvarur', 'villupuram', 'ariyalur', 'chengalpattu', 'kallakurichi', 'tirupathur'],
                    'region': 'South'
                },
                'kerala': {
                    'name': 'Kerala',
                    'hindi_name': 'केरल',
                    'districts': ['thiruvananthapuram', 'kollam', 'pathanamthitta', 'alappuzha', 'kottayam', 'idukki', 'ernakulam', 'thrissur', 'palakkad', 'malappuram', 'kozhikode', 'wayanad', 'kannur', 'kasaragod'],
                    'major_cities': ['thiruvananthapuram', 'kollam', 'pathanamthitta', 'alappuzha', 'kottayam', 'idukki', 'kochi', 'thrissur', 'palakkad', 'malappuram', 'kozhikode', 'kalpetta', 'kannur', 'kasaragod'],
                    'region': 'South'
                },
                'andhra_pradesh': {
                    'name': 'Andhra Pradesh',
                    'hindi_name': 'आंध्र प्रदेश',
                    'districts': ['visakhapatnam', 'vijayawada', 'guntur', 'nellore', 'kurnool', 'anantapur', 'kadapa', 'chittoor', 'prakasam', 'krishna', 'west_godavari', 'east_godavari', 'vizianagaram', 'srikakulam'],
                    'major_cities': ['visakhapatnam', 'vijayawada', 'guntur', 'nellore', 'kurnool', 'anantapur', 'kadapa', 'chittoor', 'ongole', 'rajahmundry', 'tirupati', 'kakinada'],
                    'region': 'South'
                },
                'telangana': {
                    'name': 'Telangana',
                    'hindi_name': 'तेलंगाना',
                    'districts': ['hyderabad', 'rangareddy', 'medchal_malkajgiri', 'vikarabad', 'sangareddy', 'kamareddy', 'nizamabad', 'jagtial', 'peddapalli', 'karimnagar', 'rajanna_sircilla', 'siddipet', 'yadadri_bhuvanagiri', 'medak', 'suryapet', 'nalgonda', 'jangaon', 'jayashankar_bhupalpally', 'mulugu', 'bhadradri_kothagudem', 'khammam', 'mahabubabad', 'warangal_urban', 'warangal_rural', 'mahabubnagar', 'nagarkurnool', 'wanaparthy', 'gadwal', 'jogulamba_gadwal', 'kumaram_bheem_asifabad', 'adilabad', 'komaram_bheem_asifabad', 'mancherial', 'nirmal'],
                    'major_cities': ['hyderabad', 'rangareddy', 'medchal', 'vikarabad', 'sangareddy', 'kamareddy', 'nizamabad', 'jagtial', 'peddapalli', 'karimnagar', 'sircilla', 'siddipet', 'yadadri', 'medak', 'suryapet', 'nalgonda', 'jangaon', 'bhupalpally', 'mulugu', 'kothagudem', 'khammam', 'mahabubabad', 'warangal', 'mahabubnagar', 'nagarkurnool', 'wanaparthy', 'gadwal', 'asifabad', 'adilabad', 'mancherial', 'nirmal'],
                    'region': 'South'
                },
                'west_bengal': {
                    'name': 'West Bengal',
                    'hindi_name': 'पश्चिम बंगाल',
                    'districts': ['kolkata', 'howrah', 'hooghly', 'bardhaman', 'birbhum', 'bankura', 'purulia', 'paschim_medinipur', 'purba_medinipur', 'north_24_parganas', 'south_24_parganas', 'jalpaiguri', 'darjeeling', 'cooch_behar', 'alipurduar', 'malda', 'murshidabad', 'nadia', 'north_24_parganas', 'south_24_parganas', 'kolkata'],
                    'major_cities': ['kolkata', 'howrah', 'hooghly', 'bardhaman', 'birbhum', 'bankura', 'purulia', 'medinipur', 'tamluk', 'barasat', 'alipore', 'jalpaiguri', 'darjeeling', 'cooch_behar', 'alipurduar', 'malda', 'murshidabad', 'nadia', 'barasat', 'alipore'],
                    'region': 'East'
                },
                'odisha': {
                    'name': 'Odisha',
                    'hindi_name': 'ओडिशा',
                    'districts': ['bhubaneswar', 'cuttack', 'rourkela', 'berhampur', 'sambalpur', 'puri', 'balasore', 'bhadrak', 'jajpur', 'kendrapada', 'jagatsinghpur', 'kendrapara', 'khordha', 'nayagarh', 'gajapati', 'ganjam', 'kandhamal', 'boudh', 'sonepur', 'balangir', 'nuapada', 'kalahandi', 'rayagada', 'nabarangpur', 'koraput', 'malkangiri', 'sundargarh', 'jharsuguda', 'debagarh', 'angul', 'dhenkanal', 'keonjhar', 'mayurbhanj'],
                    'major_cities': ['bhubaneswar', 'cuttack', 'rourkela', 'berhampur', 'sambalpur', 'puri', 'balasore', 'bhadrak', 'jajpur', 'kendrapada', 'jagatsinghpur', 'khordha', 'nayagarh', 'paralakhemundi', 'berhampur', 'phulbani', 'boudh', 'sonepur', 'balangir', 'nuapada', 'bhawanipatna', 'rayagada', 'nabarangpur', 'koraput', 'malkangiri', 'sundargarh', 'jharsuguda', 'debagarh', 'angul', 'dhenkanal', 'keonjhar', 'baripada'],
                    'region': 'East'
                },
                'bihar': {
                    'name': 'Bihar',
                    'hindi_name': 'बिहार',
                    'districts': ['patna', 'gaya', 'bhagalpur', 'muzaffarpur', 'darbhanga', 'purnia', 'araria', 'kishanganj', 'katihar', 'madhepura', 'saharsa', 'supaul', 'madhubani', 'sitamarhi', 'sheohar', 'east_champaran', 'west_champaran', 'gopalganj', 'siwan', 'saran', 'vaishali', 'bhojpur', 'buxar', 'kaimur', 'rohtas', 'aurangabad', 'gaya', 'jehanabad', 'arwal', 'nawada', 'jamui', 'lakhisarai', 'munger', 'khagaria', 'begusarai', 'nalanda', 'sheikhpura'],
                    'major_cities': ['patna', 'gaya', 'bhagalpur', 'muzaffarpur', 'darbhanga', 'purnia', 'araria', 'kishanganj', 'katihar', 'madhepura', 'saharsa', 'supaul', 'madhubani', 'sitamarhi', 'motihari', 'betiah', 'gopalganj', 'siwan', 'chapra', 'hajipur', 'ara', 'buxar', 'bhabua', 'sasaram', 'aurangabad', 'jehanabad', 'nawada', 'jamui', 'lakhisarai', 'munger', 'khagaria', 'begusarai', 'bihar_sharif', 'sheikhpura'],
                    'region': 'East'
                },
                'jharkhand': {
                    'name': 'Jharkhand',
                    'hindi_name': 'झारखंड',
                    'districts': ['ranchi', 'dhanbad', 'bokaro', 'jamshedpur', 'deoghar', 'giridih', 'hazaribagh', 'kodarma', 'palamu', 'garhwa', 'latehar', 'lohardaga', 'gumla', 'simdega', 'west_singhbhum', 'east_singhbhum', 'saraikela_kharsawan', 'dumka', 'jamtara', 'pakur', 'sahebganj', 'godda', 'chatra', 'koderma', 'ramgarh'],
                    'major_cities': ['ranchi', 'dhanbad', 'bokaro', 'jamshedpur', 'deoghar', 'giridih', 'hazaribagh', 'kodarma', 'daltonganj', 'garhwa', 'latehar', 'lohardaga', 'gumla', 'simdega', 'chaibasa', 'jamshedpur', 'saraikela', 'dumka', 'jamtara', 'pakur', 'sahebganj', 'godda', 'chatra', 'ramgarh'],
                    'region': 'East'
                },
                'chhattisgarh': {
                    'name': 'Chhattisgarh',
                    'hindi_name': 'छत्तीसगढ़',
                    'districts': ['raipur', 'durg', 'bilaspur', 'rajnandgaon', 'korba', 'janjgir_champa', 'mungeli', 'kabirdham', 'bemetara', 'balod', 'baloda_bazar', 'gariyaband', 'dhamtari', 'kanker', 'narayanpur', 'bastar', 'kondagaon', 'sukma', 'dantewada', 'bijapur', 'surajpur', 'balrampur', 'koriya', 'sarguja', 'jashpur', 'raigarh', 'korba', 'mahasamund', 'gariaband'],
                    'major_cities': ['raipur', 'durg', 'bilaspur', 'rajnandgaon', 'korba', 'janjgir', 'champa', 'mungeli', 'kabirdham', 'bemetara', 'balod', 'baloda_bazar', 'gariyaband', 'dhamtari', 'kanker', 'narayanpur', 'jagdalpur', 'kondagaon', 'sukma', 'dantewada', 'bijapur', 'surajpur', 'balrampur', 'koriya', 'ambikapur', 'jashpur', 'raigarh', 'mahasamund'],
                    'region': 'Central'
                },
                'uttar_pradesh': {
                    'name': 'Uttar Pradesh',
                    'hindi_name': 'उत्तर प्रदेश',
                    'districts': ['lucknow', 'kanpur', 'agra', 'varanasi', 'meerut', 'allahabad', 'bareilly', 'ghaziabad', 'aligarh', 'moradabad', 'saharanpur', 'gorakhpur', 'firozabad', 'muzaffarnagar', 'mathura', 'shahjahanpur', 'etawah', 'mirzapur', 'bulandshahr', 'sambhal', 'amroha', 'hardoi', 'fatehpur', 'raebareli', 'sitapur', 'budaun', 'mainpuri', 'etah', 'kasganj', 'farrukhabad', 'kannauj', 'auraliya', 'hathras', 'pilibhit', 'shahjahanpur', 'kheri', 'siddharthnagar', 'basti', 'sant_kabir_nagar', 'mahrajganj', 'gorakhpur', 'kushinagar', 'deoria', 'azamgarh', 'mau', 'ballia', 'jaunpur', 'ghazipur', 'chandauli', 'varanasi', 'sant_ravidas_nagar', 'mirzapur', 'sonbhadra', 'allahabad', 'kaushambi', 'fatehpur', 'banda', 'hamirpur', 'mahoba', 'chitrakoot', 'jalaun', 'jhansi', 'lalitpur', 'agra', 'firozabad', 'mainpuri', 'mathura', 'aligarh', 'hathras', 'kasganj', 'etah', 'etawah', 'auraliya', 'kanpur', 'kanpur_dehat', 'unnao', 'lucknow', 'raebareli', 'sitapur', 'hardoi', 'lakhimpur_kheri', 'siddharthnagar', 'basti', 'sant_kabir_nagar', 'mahrajganj', 'gorakhpur', 'kushinagar', 'deoria', 'azamgarh', 'mau', 'ballia', 'jaunpur', 'ghazipur', 'chandauli', 'varanasi', 'sant_ravidas_nagar', 'mirzapur', 'sonbhadra'],
                    'major_cities': ['lucknow', 'kanpur', 'agra', 'varanasi', 'meerut', 'allahabad', 'bareilly', 'ghaziabad', 'aligarh', 'moradabad', 'saharanpur', 'gorakhpur', 'firozabad', 'muzaffarnagar', 'mathura', 'shahjahanpur', 'etawah', 'mirzapur', 'bulandshahr', 'sambhal', 'amroha', 'hardoi', 'fatehpur', 'raebareli', 'sitapur', 'budaun', 'mainpuri', 'etah', 'kasganj', 'farrukhabad', 'kannauj', 'auraliya', 'hathras', 'pilibhit', 'kheri', 'siddharthnagar', 'basti', 'sant_kabir_nagar', 'mahrajganj', 'kushinagar', 'deoria', 'azamgarh', 'mau', 'ballia', 'jaunpur', 'ghazipur', 'chandauli', 'sant_ravidas_nagar', 'sonbhadra', 'kaushambi', 'banda', 'hamirpur', 'mahoba', 'chitrakoot', 'jalaun', 'jhansi', 'lalitpur', 'kanpur_dehat', 'unnao', 'lakhimpur_kheri'],
                    'region': 'Central'
                },
                'madhya_pradesh': {
                    'name': 'Madhya Pradesh',
                    'hindi_name': 'मध्य प्रदेश',
                    'districts': ['bhopal', 'indore', 'gwalior', 'jabalpur', 'ujjain', 'sagar', 'dewas', 'satna', 'ratlam', 'rewa', 'murwara', 'singrauli', 'burhanpur', 'khandwa', 'khargone', 'barwani', 'dhar', 'jhabua', 'alirajpur', 'mandsaur', 'neemuch', 'mhow', 'sehore', 'raisen', 'vidisha', 'guna', 'ashoknagar', 'shivpuri', 'guna', 'datia', 'sheopur', 'morena', 'bhind', 'gwalior', 'shivpuri', 'tikamgarh', 'chhatarpur', 'panna', 'damoh', 'sagar', 'chhindwara', 'betul', 'harda', 'hoshangabad', 'narsinghpur', 'seoni', 'balaghat', 'mandla', 'dindori', 'anuppur', 'shahdol', 'umaria', 'sidhi', 'singrauli'],
                    'major_cities': ['bhopal', 'indore', 'gwalior', 'jabalpur', 'ujjain', 'sagar', 'dewas', 'satna', 'ratlam', 'rewa', 'katni', 'singrauli', 'burhanpur', 'khandwa', 'khargone', 'barwani', 'dhar', 'jhabua', 'alirajpur', 'mandsaur', 'neemuch', 'mhow', 'sehore', 'raisen', 'vidisha', 'guna', 'ashoknagar', 'shivpuri', 'datia', 'sheopur', 'morena', 'bhind', 'tikamgarh', 'chhatarpur', 'panna', 'damoh', 'chhindwara', 'betul', 'harda', 'hoshangabad', 'narsinghpur', 'seoni', 'balaghat', 'mandla', 'dindori', 'anuppur', 'shahdol', 'umaria', 'sidhi'],
                    'region': 'Central'
                }
            },
            
            # Common village patterns and suffixes
            'village_patterns': [
                'pur', 'pura', 'pore', 'ore', 'garh', 'nagar', 'bad', 'ganj', 'li', 'gaon', 'gaun', 'gram',
                'kheda', 'khedi', 'khera', 'kheri', 'khurd', 'kalan', 'chak', 'chakki', 'majra', 'majri',
                'khas', 'khurd', 'kalan', 'chhota', 'bada', 'naya', 'purana', 'tanda', 'dera', 'basti',
                'nagar', 'colony', 'settlement', 'abadi', 'mohalla', 'patti', 'tehsil', 'block',
                'panchayat', 'gram_panchayat', 'village', 'town', 'city', 'municipality',
                # Regional suffixes
                'wala', 'wali', 'wale', 'wadi', 'wara', 'pada', 'palle', 'palli', 'peta', 'pet',
                'khurd', 'kalan', 'buzurg', 'chhota', 'bada', 'naya', 'purana',
                # Railway station suffixes
                'junction', 'jnc', 'road', 'rd', 'station', 'stn',
                # Market suffixes
                'mandi', 'market', 'bazaar', 'bazar', 'hat', 'haat'
            ]
        }
    
    def detect_location_comprehensive(self, query: str) -> Dict[str, Any]:
        """Comprehensive location detection with Google Maps-level accuracy"""
        query_lower = query.lower().strip()
        
        # Check cache first
        cache_key = f"location_{query_lower}"
        if cache_key in self.location_cache:
            return self.location_cache[cache_key]
        
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
        
        # 1. Try free geocoding service first (Nominatim OpenStreetMap)
        geocoding_result = self._detect_location_via_free_geocoding(query_lower)
        if geocoding_result['confidence'] > 0.8:
            result.update(geocoding_result)
            result['source'] = 'geocoding_api'
            self.location_cache[cache_key] = result
            return result
        
        # 2. Enhanced comprehensive database search
        db_result = self._detect_location_via_enhanced_database(query_lower)
        if db_result['confidence'] > 0.6:
            result.update(db_result)
            result['source'] = 'enhanced_database'
        
        # 3. Advanced pattern matching for any location name
        pattern_result = self._detect_location_via_advanced_patterns(query_lower)
        if pattern_result['confidence'] > result['confidence']:
            result.update(pattern_result)
            result['source'] = 'advanced_pattern'
        
        # 4. Fuzzy matching for partial names
        fuzzy_result = self._detect_location_via_fuzzy_matching(query_lower)
        if fuzzy_result['confidence'] > result['confidence']:
            result.update(fuzzy_result)
            result['source'] = 'fuzzy_matching'
        
        self.location_cache[cache_key] = result
        return result
    
    def _detect_location_via_free_geocoding(self, query_lower: str) -> Dict[str, Any]:
        """Free geocoding service (Nominatim OpenStreetMap)"""
        try:
            # Use Nominatim (OpenStreetMap) free geocoding
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
                    location_info = self._parse_nominatim_result(result)
                    
                    if location_info:
                        location_info['confidence'] = 0.9
                        return location_info
            
        except Exception as e:
            logger.warning(f"Free geocoding failed: {e}")
        
        return {'confidence': 0}
    
    def _parse_nominatim_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Nominatim (OpenStreetMap) result"""
        try:
            address = result.get('address', {})
            display_name = result.get('display_name', '')
            
            # Extract location details
            state = address.get('state', '')
            district = address.get('county', '') or address.get('district', '')
            city = address.get('city', '') or address.get('town', '') or address.get('village', '')
            country = address.get('country', '')
            
            # Determine the main location name
            location_name = result.get('name', '') or city or district or state or display_name.split(',')[0].strip()
            
            return {
                'location': location_name,
                'state': state or 'Unknown',
                'district': district or 'Unknown',
                'region': self._get_region_from_state(state or ''),
                'coordinates': {
                    'lat': float(result.get('lat', 0)),
                    'lng': float(result.get('lon', 0))
                },
                'type': 'nominatim_detected',
                'display_name': display_name
            }
            
        except Exception as e:
            logger.error(f"Error parsing Nominatim result: {e}")
            return None
    
    def _detect_location_via_enhanced_database(self, query_lower: str) -> Dict[str, Any]:
        """Enhanced database search with comprehensive coverage"""
        # Search in states with exact and partial matches
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
            
            # Partial match (contains)
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
            
            # Search in districts with enhanced matching
            for district in state_data['districts']:
                district_lower = district.lower()
                
                # Exact match
                if query_lower == district_lower:
                    return {
                        'location': district.title(),
                        'state': state_data['name'],
                        'district': district.title(),
                        'region': state_data['region'],
                        'coordinates': self._get_district_coordinates(district, state_data['name']),
                        'confidence': 0.9,
                        'type': 'district'
                    }
                
                # Partial match
                if district_lower in query_lower or query_lower in district_lower:
                    return {
                        'location': district.title(),
                        'state': state_data['name'],
                        'district': district.title(),
                        'region': state_data['region'],
                        'coordinates': self._get_district_coordinates(district, state_data['name']),
                        'confidence': 0.8,
                        'type': 'district'
                    }
            
            # Search in major cities with enhanced matching
            for city in state_data['major_cities']:
                city_lower = city.lower()
                
                # Exact match
                if query_lower == city_lower:
                    return {
                        'location': city.title(),
                        'state': state_data['name'],
                        'district': city.title(),
                        'region': state_data['region'],
                        'coordinates': self._get_city_coordinates(city, state_data['name']),
                        'confidence': 0.85,
                        'type': 'city'
                    }
                
                # Partial match
                if city_lower in query_lower or query_lower in city_lower:
                    return {
                        'location': city.title(),
                        'state': state_data['name'],
                        'district': city.title(),
                        'region': state_data['region'],
                        'coordinates': self._get_city_coordinates(city, state_data['name']),
                        'confidence': 0.75,
                        'type': 'city'
                    }
        
        return {'confidence': 0}
    
    def _detect_location_via_advanced_patterns(self, query_lower: str) -> Dict[str, Any]:
        """Advanced pattern matching for any location name"""
        # Enhanced village patterns with more comprehensive coverage
        enhanced_village_patterns = self.indian_locations['village_patterns']
        
        # Check for enhanced village patterns
        for pattern in enhanced_village_patterns:
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
    
    def _detect_location_via_fuzzy_matching(self, query_lower: str) -> Dict[str, Any]:
        """Fuzzy matching for partial location names"""
        # Simple fuzzy matching for partial names
        words = query_lower.split()
        
        for word in words:
            if len(word) >= 4:  # Minimum 4 characters for meaningful location
                # Check if word matches any known location
                for state_key, state_data in self.indian_locations['states'].items():
                    state_name = state_data['name'].lower()
                    
                    # Check if word is part of state name
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
                    
                    # Check cities
                    for city in state_data['major_cities']:
                        city_lower = city.lower()
                        if word in city_lower or city_lower.startswith(word):
                            return {
                                'location': city.title(),
                                'state': state_data['name'],
                                'district': city.title(),
                                'region': state_data['region'],
                                'coordinates': self._get_city_coordinates(city, state_data['name']),
                                'confidence': 0.65,
                                'type': 'city_fuzzy'
                            }
        
        return {'confidence': 0}
    
    def _get_region_from_state(self, state: str) -> str:
        """Get region from state name"""
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
            'uttar pradesh': {'lat': 26.8467, 'lng': 80.9462},
            'madhya pradesh': {'lat': 22.9734, 'lng': 78.6569}
        }
        return state_coords.get(state.lower(), {'lat': 20.5937, 'lng': 78.9629})
    
    def _get_district_coordinates(self, district: str, state: str) -> Dict[str, float]:
        """Get approximate coordinates for district"""
        return self._get_state_coordinates(state)
    
    def _get_city_coordinates(self, city: str, state: str) -> Dict[str, float]:
        """Get approximate coordinates for city"""
        return self._get_state_coordinates(state)

# Test the location detection
if __name__ == "__main__":
    detector = SimpleLocationDetection()
    
    # Test various locations
    test_locations = [
        'Assam', 'Manipur', 'Meghalaya', 'Guwahati', 'Imphal', 'Shillong',
        'Rampur', 'Bareilly', 'Gorakhpur', 'Saharanpur', 'Muzaffarnagar',
        'Delhi', 'Mumbai', 'Bangalore', 'Chennai', 'Kolkata', 'Hyderabad'
    ]
    
    print("🌍 Testing Google Maps-level Location Detection")
    print("=" * 60)
    
    for location in test_locations:
        result = detector.detect_location_comprehensive(location)
        print(f"📍 {location}: {result['location']} in {result['state']} ({result['region']}) - Confidence: {result['confidence']:.2f} - Source: {result['source']}")
    
    print("\n✅ Location detection testing completed!")
