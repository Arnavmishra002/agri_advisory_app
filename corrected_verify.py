#!/usr/bin/env python3
"""
Corrected Service Verification Script
Tests all services using the correct API endpoints
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
                "error": f"HTTP {response.status_code}: {response.text[:200]}...",
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
    
    # Test the correct weather endpoint
    result = test_api_endpoint("/api/realtime-gov/weather/", "POST", {
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
        
        if "forecast" in data and data["forecast"]:
            print(f"3-Day Forecast:")
            for i, day in enumerate(data["forecast"][:3]):
                print(f"   Day {i+1}: {day.get('temperature', 'N/A')}°C - {day.get('description', 'N/A')}")
    else:
        print(f"ERROR - Weather Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_market_prices_service():
    """Test market prices service with real-time data"""
    print("\nTESTING MARKET PRICES SERVICE")
    print("=" * 50)
    
    # Test the correct market prices endpoint
    result = test_api_endpoint("/api/realtime-gov/market_prices/", "POST", {
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
        
        if "price_trends" in data and data["price_trends"]:
            print(f"Price Trends:")
            for trend in data["price_trends"][:3]:
                print(f"   {trend.get('date', 'N/A')}: Rs.{trend.get('price', 'N/A')}")
    else:
        print(f"ERROR - Market Prices Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_crop_recommendations_service():
    """Test crop recommendations service with real-time data"""
    print("\nTESTING CROP RECOMMENDATIONS SERVICE")
    print("=" * 50)
    
    # Test the correct crop recommendations endpoint
    result = test_api_endpoint("/api/realtime-gov/crop_recommendations/", "POST", {
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
                print(f"      Score: {crop.get('score', 'N/A')}/100")
        
        if "analysis" in data:
            analysis = data["analysis"]
            print(f"Analysis: {analysis.get('summary', 'N/A')}")
    else:
        print(f"ERROR - Crop Recommendations Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_government_schemes_service():
    """Test government schemes service with real-time data"""
    print("\nTESTING GOVERNMENT SCHEMES SERVICE")
    print("=" * 50)
    
    # Test the correct government schemes endpoint
    result = test_api_endpoint("/api/realtime-gov/government_schemes/", "POST", {
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
                print(f"      Description: {scheme.get('description', 'N/A')[:100]}...")
        
        if "total_schemes" in data:
            print(f"Total Schemes Available: {data['total_schemes']}")
    else:
        print(f"ERROR - Government Schemes Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_soil_health_service():
    """Test soil health service with real-time data"""
    print("\nTESTING SOIL HEALTH SERVICE")
    print("=" * 50)
    
    # Test the correct soil health endpoint
    result = test_api_endpoint("/api/realtime-gov/soil_health/", "POST", {
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
            print(f"Fertility: {soil.get('fertility_level', 'N/A')}")
        
        if "recommendations" in data:
            recs = data["recommendations"]
            print(f"Recommendations:")
            for rec in recs[:3]:
                print(f"   • {rec}")
    else:
        print(f"ERROR - Soil Health Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_pest_detection_service():
    """Test pest detection service with real-time data"""
    print("\nTESTING PEST DETECTION SERVICE")
    print("=" * 50)
    
    # Test the correct pest detection endpoint
    result = test_api_endpoint("/api/realtime-gov/pest_detection/", "POST", {
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
                print(f"      Treatment: {pest.get('treatment', 'N/A')[:50]}...")
        
        if "prevention_tips" in data:
            tips = data["prevention_tips"]
            print(f"Prevention Tips:")
            for tip in tips[:3]:
                print(f"   • {tip}")
    else:
        print(f"ERROR - Pest Detection Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_ai_chatbot_service():
    """Test AI chatbot service with real-time data"""
    print("\nTESTING AI CHATBOT SERVICE")
    print("=" * 50)
    
    # Test the correct AI chatbot endpoint
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
        
        if "crop_recommendations" in data:
            crops = data["crop_recommendations"]
            print(f"AI Crop Recommendations:")
            for i, crop in enumerate(crops[:3]):
                print(f"   {i+1}. {crop.get('crop_name', 'N/A')}")
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
                
            if "Krishimitra AI" in response.text:
                print(f"App Title: Found")
            else:
                print(f"App Title: Not found")
        else:
            print(f"ERROR - Frontend Access: HTTP {response.status_code}")
    except Exception as e:
        print(f"ERROR - Frontend Access: {str(e)}")

def test_health_endpoints():
    """Test health monitoring endpoints"""
    print("\nTESTING HEALTH ENDPOINTS")
    print("=" * 50)
    
    # Test health endpoint
    result = test_api_endpoint("/api/health/", "GET", description="Health Check")
    if result["status"] == "SUCCESS":
        print(f"SUCCESS - Health Endpoint: {result['status']}")
        print(f"Response Time: {result['response_time']:.2f}s")
    else:
        print(f"ERROR - Health Endpoint: {result['status']}")
        print(f"Error: {result['error']}")

def main():
    """Main verification function"""
    print("KRISHIMITRA AI - COMPREHENSIVE SERVICE VERIFICATION")
    print("=" * 60)
    print(f"Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    
    # Test all services
    test_frontend_access()
    test_health_endpoints()
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
Corrected Service Verification Script
Tests all services using the correct API endpoints
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
                "error": f"HTTP {response.status_code}: {response.text[:200]}...",
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
    
    # Test the correct weather endpoint
    result = test_api_endpoint("/api/realtime-gov/weather/", "POST", {
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
        
        if "forecast" in data and data["forecast"]:
            print(f"3-Day Forecast:")
            for i, day in enumerate(data["forecast"][:3]):
                print(f"   Day {i+1}: {day.get('temperature', 'N/A')}°C - {day.get('description', 'N/A')}")
    else:
        print(f"ERROR - Weather Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_market_prices_service():
    """Test market prices service with real-time data"""
    print("\nTESTING MARKET PRICES SERVICE")
    print("=" * 50)
    
    # Test the correct market prices endpoint
    result = test_api_endpoint("/api/realtime-gov/market_prices/", "POST", {
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
        
        if "price_trends" in data and data["price_trends"]:
            print(f"Price Trends:")
            for trend in data["price_trends"][:3]:
                print(f"   {trend.get('date', 'N/A')}: Rs.{trend.get('price', 'N/A')}")
    else:
        print(f"ERROR - Market Prices Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_crop_recommendations_service():
    """Test crop recommendations service with real-time data"""
    print("\nTESTING CROP RECOMMENDATIONS SERVICE")
    print("=" * 50)
    
    # Test the correct crop recommendations endpoint
    result = test_api_endpoint("/api/realtime-gov/crop_recommendations/", "POST", {
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
                print(f"      Score: {crop.get('score', 'N/A')}/100")
        
        if "analysis" in data:
            analysis = data["analysis"]
            print(f"Analysis: {analysis.get('summary', 'N/A')}")
    else:
        print(f"ERROR - Crop Recommendations Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_government_schemes_service():
    """Test government schemes service with real-time data"""
    print("\nTESTING GOVERNMENT SCHEMES SERVICE")
    print("=" * 50)
    
    # Test the correct government schemes endpoint
    result = test_api_endpoint("/api/realtime-gov/government_schemes/", "POST", {
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
                print(f"      Description: {scheme.get('description', 'N/A')[:100]}...")
        
        if "total_schemes" in data:
            print(f"Total Schemes Available: {data['total_schemes']}")
    else:
        print(f"ERROR - Government Schemes Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_soil_health_service():
    """Test soil health service with real-time data"""
    print("\nTESTING SOIL HEALTH SERVICE")
    print("=" * 50)
    
    # Test the correct soil health endpoint
    result = test_api_endpoint("/api/realtime-gov/soil_health/", "POST", {
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
            print(f"Fertility: {soil.get('fertility_level', 'N/A')}")
        
        if "recommendations" in data:
            recs = data["recommendations"]
            print(f"Recommendations:")
            for rec in recs[:3]:
                print(f"   • {rec}")
    else:
        print(f"ERROR - Soil Health Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_pest_detection_service():
    """Test pest detection service with real-time data"""
    print("\nTESTING PEST DETECTION SERVICE")
    print("=" * 50)
    
    # Test the correct pest detection endpoint
    result = test_api_endpoint("/api/realtime-gov/pest_detection/", "POST", {
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
                print(f"      Treatment: {pest.get('treatment', 'N/A')[:50]}...")
        
        if "prevention_tips" in data:
            tips = data["prevention_tips"]
            print(f"Prevention Tips:")
            for tip in tips[:3]:
                print(f"   • {tip}")
    else:
        print(f"ERROR - Pest Detection Service: {result['status']}")
        print(f"Error: {result['error']}")

def test_ai_chatbot_service():
    """Test AI chatbot service with real-time data"""
    print("\nTESTING AI CHATBOT SERVICE")
    print("=" * 50)
    
    # Test the correct AI chatbot endpoint
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
        
        if "crop_recommendations" in data:
            crops = data["crop_recommendations"]
            print(f"AI Crop Recommendations:")
            for i, crop in enumerate(crops[:3]):
                print(f"   {i+1}. {crop.get('crop_name', 'N/A')}")
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
                
            if "Krishimitra AI" in response.text:
                print(f"App Title: Found")
            else:
                print(f"App Title: Not found")
        else:
            print(f"ERROR - Frontend Access: HTTP {response.status_code}")
    except Exception as e:
        print(f"ERROR - Frontend Access: {str(e)}")

def test_health_endpoints():
    """Test health monitoring endpoints"""
    print("\nTESTING HEALTH ENDPOINTS")
    print("=" * 50)
    
    # Test health endpoint
    result = test_api_endpoint("/api/health/", "GET", description="Health Check")
    if result["status"] == "SUCCESS":
        print(f"SUCCESS - Health Endpoint: {result['status']}")
        print(f"Response Time: {result['response_time']:.2f}s")
    else:
        print(f"ERROR - Health Endpoint: {result['status']}")
        print(f"Error: {result['error']}")

def main():
    """Main verification function"""
    print("KRISHIMITRA AI - COMPREHENSIVE SERVICE VERIFICATION")
    print("=" * 60)
    print(f"Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    
    # Test all services
    test_frontend_access()
    test_health_endpoints()
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
