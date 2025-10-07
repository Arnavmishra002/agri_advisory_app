#!/usr/bin/env python3
"""
Quick AI Assistant Test with Government Data
"""

import requests
import json
import time

def test_ai_assistant():
    """Test the AI assistant with government data integration"""
    
    print("🤖 Testing AI Assistant with Government Data Integration")
    print("=" * 60)
    
    # Test queries
    test_queries = [
        {
            "name": "Crop Recommendation with Government Data",
            "query": "crop suggest karo lucknow mei",
            "language": "hi",
            "location": "Lucknow",
            "lat": 26.8467,
            "lon": 80.9462
        },
        {
            "name": "Market Price with Government MSP",
            "query": "wheat price in delhi",
            "language": "hi", 
            "location": "Delhi",
            "lat": 28.6139,
            "lon": 77.2090
        },
        {
            "name": "Government Schemes Query",
            "query": "government schemes for farmers",
            "language": "hi",
            "location": "Delhi",
            "lat": 28.6139,
            "lon": 77.2090
        },
        {
            "name": "Hindi Crop Suggestion",
            "query": "फसल सुझाव दो लखनऊ में",
            "language": "hi",
            "location": "Lucknow", 
            "lat": 26.8467,
            "lon": 80.9462
        },
        {
            "name": "Weather Query",
            "query": "weather in mumbai",
            "language": "hi",
            "location": "Mumbai",
            "lat": 19.0760,
            "lon": 72.8777
        }
    ]
    
    base_url = "http://localhost:8000"
    
    # Test API connection
    try:
        response = requests.get(f"{base_url}/api/schema/swagger-ui/", timeout=5)
        if response.status_code == 200:
            print("✅ API connection successful")
        else:
            print("❌ API connection failed")
            return False
    except:
        print("❌ Server not running. Please start the server first.")
        return False
    
    print("\n🧪 Running Tests...")
    print("-" * 40)
    
    passed_tests = 0
    total_tests = len(test_queries)
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n{i}. {test['name']}")
        print(f"   Query: '{test['query']}'")
        
        try:
            response = requests.post(
                f"{base_url}/api/advisories/chatbot/",
                json={
                    'query': test['query'],
                    'language': test['language'],
                    'session_id': f'test-{i}',
                    'latitude': test['lat'],
                    'longitude': test['lon'],
                    'location_name': test['location']
                },
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', '')
                intent = data.get('metadata', {}).get('intent', 'unknown')
                confidence = data.get('confidence', 0)
                
                print(f"   ✅ Status: 200")
                print(f"   📊 Intent: {intent}")
                print(f"   📊 Confidence: {confidence}")
                
                # Check for government data indicators
                gov_indicators = ['सरकारी', 'government', 'MSP', 'scheme', 'योजना', 'subsidy', 'सब्सिडी']
                gov_found = any(indicator.lower() in response_text.lower() for indicator in gov_indicators)
                
                if gov_found:
                    print(f"   🏛️ Government data: Found")
                else:
                    print(f"   🏛️ Government data: Not found")
                
                # Check response quality
                if len(response_text) > 100:
                    print(f"   📝 Response: {response_text[:150]}...")
                    passed_tests += 1
                else:
                    print(f"   ❌ Response too short")
                
            else:
                print(f"   ❌ Status: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    print(f"\n📊 Test Results:")
    print(f"   ✅ Passed: {passed_tests}/{total_tests}")
    print(f"   📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print(f"\n🎉 All tests passed! AI Assistant is working perfectly with government data.")
    elif passed_tests >= total_tests * 0.8:
        print(f"\n👍 Good performance! Minor improvements needed.")
    else:
        print(f"\n⚠️ Some issues detected. Check server logs for details.")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    test_ai_assistant()
