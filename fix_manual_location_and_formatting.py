#!/usr/bin/env python3
"""
Fix Manual Location Input and Data Formatting Issues
"""

import requests
import json

def test_manual_location_input():
    """Test manual location input functionality"""
    print("🔍 Testing Manual Location Input...")
    
    try:
        # Test location suggestions API
        url = "https://krishmitra-zrk4.onrender.com/api/locations/suggestions/"
        test_locations = ["Mumbai", "Bangalore", "Pune", "Kolkata", "Chennai"]
        
        for location in test_locations:
            params = {"q": location}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('suggestions') and len(data['suggestions']) > 0:
                    suggestion = data['suggestions'][0]
                    print(f"✅ {location}: {suggestion.get('name')}, {suggestion.get('state')}")
                else:
                    print(f"❌ {location}: No suggestions found")
            else:
                print(f"❌ {location}: API failed - {response.status_code}")
                
    except Exception as e:
        print(f"❌ Manual location test failed: {e}")

def test_crop_recommendations_format():
    """Test crop recommendations formatting"""
    print("\n🔍 Testing Crop Recommendations Format...")
    
    try:
        # Test chatbot with crop recommendation query
        test_data = {
            "query": "Delhi mein kya fasal lagayein?",
            "language": "hinglish",
            "latitude": 28.7041,
            "longitude": 77.1025,
            "location": "Delhi"
        }
        
        response = requests.post("https://krishmitra-zrk4.onrender.com/api/chatbot/", json=test_data, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            response_text = data.get('response', '')
            
            print("📊 Crop Recommendation Response Format:")
            print("-" * 50)
            print(response_text[:500] + "..." if len(response_text) > 500 else response_text)
            print("-" * 50)
            
            # Check for proper formatting
            if "═══" in response_text or "═" in response_text:
                print("✅ Response contains proper box formatting")
            else:
                print("❌ Response missing proper box formatting")
                
            if "MSP" in response_text or "मूल्य" in response_text:
                print("✅ Response contains pricing information")
            else:
                print("❌ Response missing pricing information")
                
            if "उपयुक्तता" in response_text or "Suitability" in response_text:
                print("✅ Response contains suitability scores")
            else:
                print("❌ Response missing suitability scores")
                
        else:
            print(f"❌ Crop recommendations test failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Crop recommendations test failed: {e}")

def test_other_locations():
    """Test crop recommendations for different locations"""
    print("\n🔍 Testing Different Locations...")
    
    test_locations = [
        {"name": "Mumbai", "lat": 19.0760, "lon": 72.8777},
        {"name": "Bangalore", "lat": 12.9716, "lon": 77.5946},
        {"name": "Pune", "lat": 18.5204, "lon": 73.8567}
    ]
    
    for location in test_locations:
        try:
            test_data = {
                "query": f"{location['name']} mein kya fasal lagayein?",
                "language": "hinglish",
                "latitude": location['lat'],
                "longitude": location['lon'],
                "location": location['name']
            }
            
            response = requests.post("https://krishmitra-zrk4.onrender.com/api/chatbot/", json=test_data, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', '')
                
                if location['name'] in response_text:
                    print(f"✅ {location['name']}: Location-specific recommendations working")
                else:
                    print(f"❌ {location['name']}: Generic recommendations (not location-specific)")
            else:
                print(f"❌ {location['name']}: API failed - {response.status_code}")
                
        except Exception as e:
            print(f"❌ {location['name']} test failed: {e}")

def main():
    """Run comprehensive tests"""
    print("🚀 KRISHIMITRA AI - MANUAL LOCATION & FORMATTING TEST")
    print("=" * 60)
    
    test_manual_location_input()
    test_crop_recommendations_format()
    test_other_locations()
    
    print("\n" + "=" * 60)
    print("📊 TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
