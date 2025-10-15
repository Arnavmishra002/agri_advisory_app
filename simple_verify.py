#!/usr/bin/env python3
"""
Simple Service Verification Script
Tests all services and displays real-time data correctly
"""

import requests
import json
import time
import sys
from datetime import datetime

# Base URL for the API
BASE_URL = "http://127.0.0.1:8000"

def test_api_endpoint(endpoint, method="GET", data=None, description=""):
    """Test an API endpoint and return results"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            return {
                "status": "SUCCESS",
                "data": response.json(),
                "response_time": response.elapsed.total_seconds()
            }
        else:
            return {
                "status": "ERROR",
                "error": f"HTTP {response.status_code}: {response.text}",
                "response_time": response.elapsed.total_seconds()
            }
    except requests.exceptions.ConnectionError:
        return {
            "status": "CONNECTION_ERROR",
            "error": "Cannot connect to server. Is it running?",
            "response_time": 0
        }
    except requests.exceptions.Timeout:
        return {
            "status": "TIMEOUT",
            "error": "Request timed out",
            "response_time": 10
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e),
            "response_time": 0
        }

def test_weather_service():
    """Test weather service with real-time data"""
    print("\nTESTING WEATHER SERVICE")
    print("=" * 50)
    
    result = test_api_endpoint("/api/locations/weather/", "POST", {
        "latitude": 28.7041,
        "longitude": 77.1025,
        "location": "Delhi"
    }, "Weather Data")
    
    if result["status"] == "SUCCESS":
        data = result["data"]
        print(f"SUCCESS - Weather Service: {result['status']}")
        print(f"Response Time: {result['response_time']:.2f}s")
        
        if "weather_data" in data:
            weather = data["weather_data"]
            print(f"Temperature: {weather.get('temperature', 'N/A')}°C")
            print(f"Humidity: {weather.get('humidity', 'N/A')}%")
            print(f"Wind Speed: {weather.get('wind_speed', 'N/A')} km/h")
            print(f"Description: {weather.get('description', 'N/A')}")
    else:
        print(f"ERROR - Weather Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_market_prices_service():
    """Test market prices service with real-time data"""
    print("\nTESTING MARKET PRICES SERVICE")
    print("=" * 50)
    
    result = test_api_endpoint("/api/locations/market_prices/", "POST", {
        "commodity": "wheat",
        "state": "Delhi"
    }, "Market Prices")
    
    if result["status"] == "SUCCESS":
        data = result["data"]
        print(f"SUCCESS - Market Prices Service: {result['status']}")
        print(f"Response Time: {result['response_time']:.2f}s")
        
        if "market_data" in data:
            market = data["market_data"]
            print(f"Commodity: {market.get('commodity', 'N/A')}")
            print(f"Price: Rs.{market.get('price', 'N/A')}/quintal")
            print(f"Market: {market.get('market', 'N/A')}")
            print(f"State: {market.get('state', 'N/A')}")
    else:
        print(f"ERROR - Market Prices Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_crop_recommendations_service():
    """Test crop recommendations service with real-time data"""
    print("\nTESTING CROP RECOMMENDATIONS SERVICE")
    print("=" * 50)
    
    result = test_api_endpoint("/api/locations/crop_recommendations/", "POST", {
        "location": "Delhi",
        "season": "rabi"
    }, "Crop Recommendations")
    
    if result["status"] == "SUCCESS":
        data = result["data"]
        print(f"SUCCESS - Crop Recommendations Service: {result['status']}")
        print(f"Response Time: {result['response_time']:.2f}s")
        
        if "crop_recommendations" in data:
            crops = data["crop_recommendations"]
            print(f"Top 5 Recommended Crops:")
            for i, crop in enumerate(crops[:5]):
                print(f"   {i+1}. {crop.get('crop_name', 'N/A')}")
                print(f"      Profit: Rs.{crop.get('profit_per_acre', 'N/A')}/acre")
                print(f"      Yield: {crop.get('yield_per_acre', 'N/A')} quintals/acre")
    else:
        print(f"ERROR - Crop Recommendations Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_government_schemes_service():
    """Test government schemes service with real-time data"""
    print("\nTESTING GOVERNMENT SCHEMES SERVICE")
    print("=" * 50)
    
    result = test_api_endpoint("/api/locations/government_schemes/", "POST", {
        "location": "Delhi"
    }, "Government Schemes")
    
    if result["status"] == "SUCCESS":
        data = result["data"]
        print(f"SUCCESS - Government Schemes Service: {result['status']}")
        print(f"Response Time: {result['response_time']:.2f}s")
        
        if "schemes" in data:
            schemes = data["schemes"]
            print(f"Available Schemes ({len(schemes)}):")
            for i, scheme in enumerate(schemes[:5]):
                print(f"   {i+1}. {scheme.get('name', 'N/A')}")
                print(f"      Amount: Rs.{scheme.get('amount', 'N/A')}")
    else:
        print(f"ERROR - Government Schemes Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_soil_health_service():
    """Test soil health service with real-time data"""
    print("\nTESTING SOIL HEALTH SERVICE")
    print("=" * 50)
    
    result = test_api_endpoint("/api/locations/soil_health/", "POST", {
        "location": "Delhi"
    }, "Soil Health")
    
    if result["status"] == "SUCCESS":
        data = result["data"]
        print(f"SUCCESS - Soil Health Service: {result['status']}")
        print(f"Response Time: {result['response_time']:.2f}s")
        
        if "soil_data" in data:
            soil = data["soil_data"]
            print(f"Location: {soil.get('location', 'N/A')}")
            print(f"pH Level: {soil.get('ph_level', 'N/A')}")
            print(f"Organic Matter: {soil.get('organic_matter', 'N/A')}%")
            print(f"Moisture: {soil.get('moisture', 'N/A')}%")
    else:
        print(f"ERROR - Soil Health Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_pest_detection_service():
    """Test pest detection service with real-time data"""
    print("\nTESTING PEST DETECTION SERVICE")
    print("=" * 50)
    
    result = test_api_endpoint("/api/locations/pest_detection/", "POST", {
        "location": "Delhi",
        "crop": "wheat"
    }, "Pest Detection")
    
    if result["status"] == "SUCCESS":
        data = result["data"]
        print(f"SUCCESS - Pest Detection Service: {result['status']}")
        print(f"Response Time: {result['response_time']:.2f}s")
        
        if "pest_data" in data:
            pests = data["pest_data"]
            print(f"Common Pests for {data.get('crop', 'N/A')}:")
            for i, pest in enumerate(pests[:5]):
                print(f"   {i+1}. {pest.get('name', 'N/A')}")
                print(f"      Severity: {pest.get('severity', 'N/A')}")
    else:
        print(f"ERROR - Pest Detection Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_ai_chatbot_service():
    """Test AI chatbot service with real-time data"""
    print("\nTESTING AI CHATBOT SERVICE")
    print("=" * 50)
    
    result = test_api_endpoint("/api/chatbot/", "POST", {
        "query": "Delhi mein kya fasal lagayein?",
        "language": "hinglish",
        "latitude": 28.7041,
        "longitude": 77.1025,
        "location": "Delhi"
    }, "AI Chatbot")
    
    if result["status"] == "SUCCESS":
        data = result["data"]
        print(f"SUCCESS - AI Chatbot Service: {result['status']}")
        print(f"Response Time: {result['response_time']:.2f}s")
        
        if "response" in data:
            response = data["response"]
            print(f"AI Response: {response[:200]}...")
    else:
        print(f"ERROR - AI Chatbot Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_frontend_access():
    """Test if frontend is accessible"""
    print("\nTESTING FRONTEND ACCESS")
    print("=" * 50)
    
    try:
        response = requests.get(f"{BASE_URL}/", timeout=10)
        if response.status_code == 200:
            print(f"SUCCESS - Frontend Access: SUCCESS")
            print(f"Response Time: {response.elapsed.total_seconds():.2f}s")
            print(f"Content Length: {len(response.text)} characters")
            
            # Check if it contains service cards
            if "service-card" in response.text:
                print(f"Service Cards: Found in HTML")
            else:
                print(f"Service Cards: Not found in HTML")
                
            if "loadRealTimeData" in response.text:
                print(f"JavaScript Functions: Found")
            else:
                print(f"JavaScript Functions: Not found")
        else:
            print(f"ERROR - Frontend Access: HTTP {response.status_code}")
    except Exception as e:
        print(f"ERROR - Frontend Access: {str(e)}")

def main():
    """Main verification function"""
    print("KRISHIMITRA AI - COMPREHENSIVE SERVICE VERIFICATION")
    print("=" * 60)
    print(f"Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    
    # Test all services
    test_frontend_access()
    test_weather_service()
    test_market_prices_service()
    test_crop_recommendations_service()
    test_government_schemes_service()
    test_soil_health_service()
    test_pest_detection_service()
    test_ai_chatbot_service()
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print(f"Test Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nOpen your browser and visit: http://127.0.0.1:8000/")
    print("All service cards should be clickable and show real-time data!")

if __name__ == "__main__":
    main()
"""
Simple Service Verification Script
Tests all services and displays real-time data correctly
"""

import requests
import json
import time
import sys
from datetime import datetime

# Base URL for the API
BASE_URL = "http://127.0.0.1:8000"

def test_api_endpoint(endpoint, method="GET", data=None, description=""):
    """Test an API endpoint and return results"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            return {
                "status": "SUCCESS",
                "data": response.json(),
                "response_time": response.elapsed.total_seconds()
            }
        else:
            return {
                "status": "ERROR",
                "error": f"HTTP {response.status_code}: {response.text}",
                "response_time": response.elapsed.total_seconds()
            }
    except requests.exceptions.ConnectionError:
        return {
            "status": "CONNECTION_ERROR",
            "error": "Cannot connect to server. Is it running?",
            "response_time": 0
        }
    except requests.exceptions.Timeout:
        return {
            "status": "TIMEOUT",
            "error": "Request timed out",
            "response_time": 10
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e),
            "response_time": 0
        }

def test_weather_service():
    """Test weather service with real-time data"""
    print("\nTESTING WEATHER SERVICE")
    print("=" * 50)
    
    result = test_api_endpoint("/api/locations/weather/", "POST", {
        "latitude": 28.7041,
        "longitude": 77.1025,
        "location": "Delhi"
    }, "Weather Data")
    
    if result["status"] == "SUCCESS":
        data = result["data"]
        print(f"SUCCESS - Weather Service: {result['status']}")
        print(f"Response Time: {result['response_time']:.2f}s")
        
        if "weather_data" in data:
            weather = data["weather_data"]
            print(f"Temperature: {weather.get('temperature', 'N/A')}°C")
            print(f"Humidity: {weather.get('humidity', 'N/A')}%")
            print(f"Wind Speed: {weather.get('wind_speed', 'N/A')} km/h")
            print(f"Description: {weather.get('description', 'N/A')}")
    else:
        print(f"ERROR - Weather Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_market_prices_service():
    """Test market prices service with real-time data"""
    print("\nTESTING MARKET PRICES SERVICE")
    print("=" * 50)
    
    result = test_api_endpoint("/api/locations/market_prices/", "POST", {
        "commodity": "wheat",
        "state": "Delhi"
    }, "Market Prices")
    
    if result["status"] == "SUCCESS":
        data = result["data"]
        print(f"SUCCESS - Market Prices Service: {result['status']}")
        print(f"Response Time: {result['response_time']:.2f}s")
        
        if "market_data" in data:
            market = data["market_data"]
            print(f"Commodity: {market.get('commodity', 'N/A')}")
            print(f"Price: Rs.{market.get('price', 'N/A')}/quintal")
            print(f"Market: {market.get('market', 'N/A')}")
            print(f"State: {market.get('state', 'N/A')}")
    else:
        print(f"ERROR - Market Prices Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_crop_recommendations_service():
    """Test crop recommendations service with real-time data"""
    print("\nTESTING CROP RECOMMENDATIONS SERVICE")
    print("=" * 50)
    
    result = test_api_endpoint("/api/locations/crop_recommendations/", "POST", {
        "location": "Delhi",
        "season": "rabi"
    }, "Crop Recommendations")
    
    if result["status"] == "SUCCESS":
        data = result["data"]
        print(f"SUCCESS - Crop Recommendations Service: {result['status']}")
        print(f"Response Time: {result['response_time']:.2f}s")
        
        if "crop_recommendations" in data:
            crops = data["crop_recommendations"]
            print(f"Top 5 Recommended Crops:")
            for i, crop in enumerate(crops[:5]):
                print(f"   {i+1}. {crop.get('crop_name', 'N/A')}")
                print(f"      Profit: Rs.{crop.get('profit_per_acre', 'N/A')}/acre")
                print(f"      Yield: {crop.get('yield_per_acre', 'N/A')} quintals/acre")
    else:
        print(f"ERROR - Crop Recommendations Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_government_schemes_service():
    """Test government schemes service with real-time data"""
    print("\nTESTING GOVERNMENT SCHEMES SERVICE")
    print("=" * 50)
    
    result = test_api_endpoint("/api/locations/government_schemes/", "POST", {
        "location": "Delhi"
    }, "Government Schemes")
    
    if result["status"] == "SUCCESS":
        data = result["data"]
        print(f"SUCCESS - Government Schemes Service: {result['status']}")
        print(f"Response Time: {result['response_time']:.2f}s")
        
        if "schemes" in data:
            schemes = data["schemes"]
            print(f"Available Schemes ({len(schemes)}):")
            for i, scheme in enumerate(schemes[:5]):
                print(f"   {i+1}. {scheme.get('name', 'N/A')}")
                print(f"      Amount: Rs.{scheme.get('amount', 'N/A')}")
    else:
        print(f"ERROR - Government Schemes Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_soil_health_service():
    """Test soil health service with real-time data"""
    print("\nTESTING SOIL HEALTH SERVICE")
    print("=" * 50)
    
    result = test_api_endpoint("/api/locations/soil_health/", "POST", {
        "location": "Delhi"
    }, "Soil Health")
    
    if result["status"] == "SUCCESS":
        data = result["data"]
        print(f"SUCCESS - Soil Health Service: {result['status']}")
        print(f"Response Time: {result['response_time']:.2f}s")
        
        if "soil_data" in data:
            soil = data["soil_data"]
            print(f"Location: {soil.get('location', 'N/A')}")
            print(f"pH Level: {soil.get('ph_level', 'N/A')}")
            print(f"Organic Matter: {soil.get('organic_matter', 'N/A')}%")
            print(f"Moisture: {soil.get('moisture', 'N/A')}%")
    else:
        print(f"ERROR - Soil Health Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_pest_detection_service():
    """Test pest detection service with real-time data"""
    print("\nTESTING PEST DETECTION SERVICE")
    print("=" * 50)
    
    result = test_api_endpoint("/api/locations/pest_detection/", "POST", {
        "location": "Delhi",
        "crop": "wheat"
    }, "Pest Detection")
    
    if result["status"] == "SUCCESS":
        data = result["data"]
        print(f"SUCCESS - Pest Detection Service: {result['status']}")
        print(f"Response Time: {result['response_time']:.2f}s")
        
        if "pest_data" in data:
            pests = data["pest_data"]
            print(f"Common Pests for {data.get('crop', 'N/A')}:")
            for i, pest in enumerate(pests[:5]):
                print(f"   {i+1}. {pest.get('name', 'N/A')}")
                print(f"      Severity: {pest.get('severity', 'N/A')}")
    else:
        print(f"ERROR - Pest Detection Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_ai_chatbot_service():
    """Test AI chatbot service with real-time data"""
    print("\nTESTING AI CHATBOT SERVICE")
    print("=" * 50)
    
    result = test_api_endpoint("/api/chatbot/", "POST", {
        "query": "Delhi mein kya fasal lagayein?",
        "language": "hinglish",
        "latitude": 28.7041,
        "longitude": 77.1025,
        "location": "Delhi"
    }, "AI Chatbot")
    
    if result["status"] == "SUCCESS":
        data = result["data"]
        print(f"SUCCESS - AI Chatbot Service: {result['status']}")
        print(f"Response Time: {result['response_time']:.2f}s")
        
        if "response" in data:
            response = data["response"]
            print(f"AI Response: {response[:200]}...")
    else:
        print(f"ERROR - AI Chatbot Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_frontend_access():
    """Test if frontend is accessible"""
    print("\nTESTING FRONTEND ACCESS")
    print("=" * 50)
    
    try:
        response = requests.get(f"{BASE_URL}/", timeout=10)
        if response.status_code == 200:
            print(f"SUCCESS - Frontend Access: SUCCESS")
            print(f"Response Time: {response.elapsed.total_seconds():.2f}s")
            print(f"Content Length: {len(response.text)} characters")
            
            # Check if it contains service cards
            if "service-card" in response.text:
                print(f"Service Cards: Found in HTML")
            else:
                print(f"Service Cards: Not found in HTML")
                
            if "loadRealTimeData" in response.text:
                print(f"JavaScript Functions: Found")
            else:
                print(f"JavaScript Functions: Not found")
        else:
            print(f"ERROR - Frontend Access: HTTP {response.status_code}")
    except Exception as e:
        print(f"ERROR - Frontend Access: {str(e)}")

def main():
    """Main verification function"""
    print("KRISHIMITRA AI - COMPREHENSIVE SERVICE VERIFICATION")
    print("=" * 60)
    print(f"Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    
    # Test all services
    test_frontend_access()
    test_weather_service()
    test_market_prices_service()
    test_crop_recommendations_service()
    test_government_schemes_service()
    test_soil_health_service()
    test_pest_detection_service()
    test_ai_chatbot_service()
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print(f"Test Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nOpen your browser and visit: http://127.0.0.1:8000/")
    print("All service cards should be clickable and show real-time data!")

if __name__ == "__main__":
    main()
