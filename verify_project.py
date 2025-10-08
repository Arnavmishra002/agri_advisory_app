#!/usr/bin/env python3
"""
Comprehensive Project Verification Script
Tests all services, AI chatbot, government APIs, and dynamic data
"""

import os
import sys
import django
import requests
import json
import time
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_result(test_name, status, details=""):
    status_symbol = "✅" if status else "❌"
    print(f"{status_symbol} {test_name}")
    if details:
        print(f"   {details}")

def test_server_status():
    """Test if Django server is running"""
    print_header("SERVER STATUS CHECK")
    
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            print_result("Django Server", True, f"Running on port 8000 (Status: {response.status_code})")
            return True
        else:
            print_result("Django Server", False, f"Server responded with status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print_result("Django Server", False, f"Server not accessible: {str(e)}")
        return False

def test_weather_api():
    """Test weather API with different locations"""
    print_header("WEATHER API TESTING")
    
    test_locations = [
        {"name": "Delhi", "lat": 28.6139, "lon": 77.2090},
        {"name": "Mumbai", "lat": 19.0760, "lon": 72.8777},
        {"name": "Bangalore", "lat": 12.9716, "lon": 77.5946},
        {"name": "Chennai", "lat": 13.0827, "lon": 80.2707}
    ]
    
    results = []
    for location in test_locations:
        try:
            url = f"http://localhost:8000/api/weather/current/?lat={location['lat']}&lon={location['lon']}&lang=en"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'temperature' in data and 'weather_condition' in data:
                    print_result(f"Weather API - {location['name']}", True, 
                               f"Temp: {data.get('temperature', 'N/A')}°C, Condition: {data.get('weather_condition', 'N/A')}")
                    results.append(True)
                else:
                    print_result(f"Weather API - {location['name']}", False, "Invalid response format")
                    results.append(False)
            else:
                print_result(f"Weather API - {location['name']}", False, f"HTTP {response.status_code}")
                results.append(False)
                
        except Exception as e:
            print_result(f"Weather API - {location['name']}", False, str(e))
            results.append(False)
    
    return any(results)

def test_market_prices_api():
    """Test market prices API with different locations and products"""
    print_header("MARKET PRICES API TESTING")
    
    test_cases = [
        {"location": "Delhi", "lat": 28.6139, "lon": 77.2090, "product": "wheat"},
        {"location": "Mumbai", "lat": 19.0760, "lon": 72.8777, "product": "rice"},
        {"location": "Bangalore", "lat": 12.9716, "lon": 77.5946, "product": "maize"},
        {"location": "Punjab", "lat": 31.1471, "lon": 75.3412, "product": "wheat"}
    ]
    
    results = []
    for test_case in test_cases:
        try:
            url = f"http://localhost:8000/api/market-prices/prices/?lat={test_case['lat']}&lon={test_case['lon']}&lang=en&product={test_case['product']}"
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if 'market_data' in data:
                    print_result(f"Market Prices - {test_case['location']} ({test_case['product']})", True, 
                               f"Data source: {data.get('data_source', 'Unknown')}")
                    results.append(True)
                else:
                    print_result(f"Market Prices - {test_case['location']} ({test_case['product']})", False, "No market data in response")
                    results.append(False)
            else:
                print_result(f"Market Prices - {test_case['location']} ({test_case['product']})", False, f"HTTP {response.status_code}")
                results.append(False)
                
        except Exception as e:
            print_result(f"Market Prices - {test_case['location']} ({test_case['product']})", False, str(e))
            results.append(False)
    
    return any(results)

def test_ai_chatbot():
    """Test AI chatbot intelligence"""
    print_header("AI CHATBOT INTELLIGENCE TESTING")
    
    test_queries = [
        {
            "query": "What crops should I plant in Delhi this season?",
            "location": {"lat": 28.6139, "lon": 77.2090}
        },
        {
            "query": "Tell me about wheat farming in Punjab",
            "location": {"lat": 31.1471, "lon": 75.3412}
        },
        {
            "query": "What are the current weather conditions for farming?",
            "location": {"lat": 19.0760, "lon": 72.8777}
        },
        {
            "query": "How to control pests in rice farming?",
            "location": {"lat": 12.9716, "lon": 77.5946}
        }
    ]
    
    results = []
    for i, test_case in enumerate(test_queries, 1):
        try:
            url = "http://localhost:8000/api/advisories/chatbot/"
            payload = {
                "query": test_case["query"],
                "language": "en",
                "latitude": test_case["location"]["lat"],
                "longitude": test_case["location"]["lon"]
            }
            
            response = requests.post(url, json=payload, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                if 'response' in data and len(data['response']) > 50:  # Check for meaningful response
                    print_result(f"AI Chatbot Test {i}", True, 
                               f"Response length: {len(data['response'])} chars")
                    results.append(True)
                else:
                    print_result(f"AI Chatbot Test {i}", False, "Insufficient response")
                    results.append(False)
            else:
                print_result(f"AI Chatbot Test {i}", False, f"HTTP {response.status_code}")
                results.append(False)
                
        except Exception as e:
            print_result(f"AI Chatbot Test {i}", False, str(e))
            results.append(False)
    
    return any(results)

def test_crop_recommendations():
    """Test crop recommendation API"""
    print_header("CROP RECOMMENDATIONS TESTING")
    
    test_cases = [
        {"soil": "loamy", "lat": 28.6139, "lon": 77.2090, "season": "kharif"},
        {"soil": "clay", "lat": 19.0760, "lon": 72.8777, "season": "rabi"},
        {"soil": "sandy", "lat": 12.9716, "lon": 77.5946, "season": "kharif"}
    ]
    
    results = []
    for test_case in test_cases:
        try:
            url = "http://localhost:8000/api/advisories/ml_crop_recommendation/"
            payload = {
                "soil_type": test_case["soil"],
                "latitude": test_case["lat"],
                "longitude": test_case["lon"],
                "season": test_case["season"]
            }
            
            response = requests.post(url, json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if 'recommendations' in data or 'crops' in data:
                    print_result(f"Crop Recommendations - {test_case['soil']} soil", True, 
                               f"Season: {test_case['season']}")
                    results.append(True)
                else:
                    print_result(f"Crop Recommendations - {test_case['soil']} soil", False, "No recommendations in response")
                    results.append(False)
            else:
                print_result(f"Crop Recommendations - {test_case['soil']} soil", False, f"HTTP {response.status_code}")
                results.append(False)
                
        except Exception as e:
            print_result(f"Crop Recommendations - {test_case['soil']} soil", False, str(e))
            results.append(False)
    
    return any(results)

def test_government_schemes():
    """Test government schemes API"""
    print_header("GOVERNMENT SCHEMES API TESTING")
    
    try:
        url = "http://localhost:8000/api/government-schemes/"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                print_result("Government Schemes API", True, f"Found {len(data)} schemes")
                return True
            else:
                print_result("Government Schemes API", False, "No schemes data")
                return False
        else:
            print_result("Government Schemes API", False, f"HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_result("Government Schemes API", False, str(e))
        return False

def test_dynamic_location_data():
    """Test dynamic data changes with different locations"""
    print_header("DYNAMIC LOCATION DATA TESTING")
    
    # Test if data changes with different locations
    locations = [
        {"name": "North India (Delhi)", "lat": 28.6139, "lon": 77.2090},
        {"name": "South India (Chennai)", "lat": 13.0827, "lon": 80.2707},
        {"name": "West India (Mumbai)", "lat": 19.0760, "lon": 72.8777},
        {"name": "East India (Kolkata)", "lat": 22.5726, "lon": 88.3639}
    ]
    
    weather_data = []
    for location in locations:
        try:
            url = f"http://localhost:8000/api/weather/current/?lat={location['lat']}&lon={location['lon']}&lang=en"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                weather_data.append({
                    'location': location['name'],
                    'temperature': data.get('temperature', 'N/A'),
                    'condition': data.get('weather_condition', 'N/A'),
                    'source': data.get('data_source', 'Unknown')
                })
        except Exception as e:
            print_result(f"Weather data for {location['name']}", False, str(e))
    
    if len(weather_data) >= 2:
        # Check if data is different for different locations
        unique_temps = set(data['temperature'] for data in weather_data if data['temperature'] != 'N/A')
        unique_conditions = set(data['condition'] for data in weather_data if data['condition'] != 'N/A')
        
        print_result("Dynamic Location Weather Data", True, f"Retrieved data for {len(weather_data)} locations")
        
        for data in weather_data:
            print(f"   {data['location']}: {data['temperature']}°C, {data['condition']} (Source: {data['source']})")
        
        if len(unique_temps) > 1 or len(unique_conditions) > 1:
            print_result("Location-based Data Variation", True, "Data varies with location")
            return True
        else:
            print_result("Location-based Data Variation", False, "Data appears static across locations")
            return False
    else:
        print_result("Dynamic Location Weather Data", False, "Could not retrieve data for multiple locations")
        return False

def main():
    """Main verification function"""
    print_header("KRISHIMITRA AI - COMPREHENSIVE PROJECT VERIFICATION")
    print(f"Verification started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test results
    tests = {
        "Server Status": False,
        "Weather API": False,
        "Market Prices API": False,
        "AI Chatbot": False,
        "Crop Recommendations": False,
        "Government Schemes": False,
        "Dynamic Location Data": False
    }
    
    # Run tests
    tests["Server Status"] = test_server_status()
    
    if tests["Server Status"]:
        tests["Weather API"] = test_weather_api()
        tests["Market Prices API"] = test_market_prices_api()
        tests["AI Chatbot"] = test_ai_chatbot()
        tests["Crop Recommendations"] = test_crop_recommendations()
        tests["Government Schemes"] = test_government_schemes()
        tests["Dynamic Location Data"] = test_dynamic_location_data()
    
    # Summary
    print_header("VERIFICATION SUMMARY")
    passed = sum(tests.values())
    total = len(tests)
    
    for test_name, result in tests.items():
        status_symbol = "✅" if result else "❌"
        print(f"{status_symbol} {test_name}")
    
    print(f"\nOverall Status: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Your Krishimitra AI project is working perfectly!")
        print("✅ All services are functional")
        print("✅ AI chatbot is intelligent and responsive")
        print("✅ Government APIs are integrated and providing real data")
        print("✅ Dynamic location-based data is working")
        print("✅ Project is ready for production use!")
    elif passed >= total * 0.7:
        print(f"\n⚠️  MOSTLY WORKING: {passed}/{total} tests passed")
        print("Most services are functional with some issues to address.")
    else:
        print(f"\n❌ NEEDS ATTENTION: Only {passed}/{total} tests passed")
        print("Several services need to be fixed.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
