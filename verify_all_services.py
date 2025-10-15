#!/usr/bin/env python3
"""
Comprehensive Site Verification - Browser Testing
"""

import requests
import json
import time

def test_all_services():
    """Test all services on the Krishimitra AI website"""
    print("🌾 Krishimitra AI - Comprehensive Service Verification")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:8000"
    
    # Test cases for all services
    test_cases = [
        {
            "name": "🏠 Homepage",
            "url": f"{base_url}/",
            "method": "GET",
            "expected_status": 200
        },
        {
            "name": "🤖 AI Assistant - General Query",
            "url": f"{base_url}/api/chatbot/",
            "method": "POST",
            "data": {"query": "hello", "session_id": "test123"},
            "expected_status": 200
        },
        {
            "name": "🤖 AI Assistant - Farming Query",
            "url": f"{base_url}/api/chatbot/",
            "method": "POST",
            "data": {"query": "What crops should I grow in Raebareli?", "session_id": "test123"},
            "expected_status": 200
        },
        {
            "name": "🌾 Crop Recommendations",
            "url": f"{base_url}/api/realtime-gov/crop_recommendations/",
            "method": "GET",
            "params": {"location": "Raebareli", "latitude": 26.2, "longitude": 81.2},
            "expected_status": 200
        },
        {
            "name": "🏛️ Government Schemes",
            "url": f"{base_url}/api/realtime-gov/government_schemes/",
            "method": "GET",
            "params": {"location": "Raebareli", "latitude": 26.2, "longitude": 81.2},
            "expected_status": 200
        },
        {
            "name": "🌤️ Weather Data",
            "url": f"{base_url}/api/realtime-gov/weather/",
            "method": "GET",
            "params": {"location": "Raebareli", "latitude": 26.2, "longitude": 81.2},
            "expected_status": 200
        },
        {
            "name": "💰 Market Prices",
            "url": f"{base_url}/api/realtime-gov/market_prices/",
            "method": "GET",
            "params": {"location": "Raebareli", "latitude": 26.2, "longitude": 81.2},
            "expected_status": 200
        },
        {
            "name": "🐛 Pest Detection",
            "url": f"{base_url}/api/realtime-gov/pest_detection/",
            "method": "POST",
            "data": {"crop": "wheat", "location": "Raebareli", "latitude": 26.2, "longitude": 81.2, "symptoms": ""},
            "expected_status": 200
        },
        {
            "name": "📍 Location Search",
            "url": f"{base_url}/api/locations/search/",
            "method": "GET",
            "params": {"q": "Raebareli"},
            "expected_status": 200
        },
        {
            "name": "🔄 Reverse Geocoding",
            "url": f"{base_url}/api/locations/reverse/",
            "method": "GET",
            "params": {"lat": 26.2, "lon": 81.2},
            "expected_status": 200
        },
        {
            "name": "🔍 Crop Search",
            "url": f"{base_url}/api/realtime-gov/crop_search/",
            "method": "GET",
            "params": {"crop": "wheat", "location": "Raebareli"},
            "expected_status": 200
        }
    ]
    
    results = {
        "passed": 0,
        "failed": 0,
        "total": len(test_cases)
    }
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {test_case['name']}")
        print(f"   URL: {test_case['url']}")
        
        try:
            if test_case['method'] == 'GET':
                if 'params' in test_case:
                    response = requests.get(test_case['url'], params=test_case['params'], timeout=10)
                else:
                    response = requests.get(test_case['url'], timeout=10)
            else:  # POST
                if 'data' in test_case:
                    response = requests.post(
                        test_case['url'], 
                        json=test_case['data'], 
                        headers={'Content-Type': 'application/json'},
                        timeout=10
                    )
                else:
                    response = requests.post(test_case['url'], timeout=10)
            
            status_code = response.status_code
            print(f"   Status: {status_code}")
            
            if status_code == test_case['expected_status']:
                print(f"   ✅ PASSED")
                results["passed"] += 1
                
                # Show response preview for API endpoints
                if '/api/' in test_case['url']:
                    try:
                        data = response.json()
                        if 'response' in data:
                            preview = data['response'][:100].replace('\n', ' ')
                            print(f"   Preview: {preview}...")
                        elif 'location' in data:
                            print(f"   Location: {data.get('location', 'N/A')}")
                        elif 'schemes' in data:
                            print(f"   Schemes: {len(data.get('schemes', []))} found")
                        elif 'top_4_recommendations' in data:
                            print(f"   Crop Recommendations: {len(data.get('top_4_recommendations', []))} found")
                    except:
                        print(f"   Response Length: {len(response.text)}")
            else:
                print(f"   ❌ FAILED - Expected {test_case['expected_status']}, got {status_code}")
                results["failed"] += 1
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ TIMEOUT")
            results["failed"] += 1
        except requests.exceptions.ConnectionError:
            print(f"   🔌 CONNECTION ERROR")
            results["failed"] += 1
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)[:50]}...")
            results["failed"] += 1
        
        # Small delay between requests
        time.sleep(0.5)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"✅ Passed: {results['passed']}/{results['total']}")
    print(f"❌ Failed: {results['failed']}/{results['total']}")
    print(f"📈 Success Rate: {(results['passed']/results['total']*100):.1f}%")
    
    if results['failed'] == 0:
        print("\n🎉 ALL SERVICES ARE WORKING PERFECTLY!")
        print("🌾 Krishimitra AI is fully functional and ready for use!")
    else:
        print(f"\n⚠️  {results['failed']} service(s) need attention")
    
    return results

def test_frontend_features():
    """Test frontend-specific features"""
    print("\n🖥️  FRONTEND FEATURES TEST")
    print("=" * 40)
    
    try:
        response = requests.get("http://127.0.0.1:8000/", timeout=10)
        if response.status_code == 200:
            html_content = response.text
            
            # Check for key frontend features
            features = [
                ("AI Assistant Chat", "chatMessages"),
                ("Location Search", "locationSearchInput"),
                ("Service Cards", "service-card"),
                ("Crop Recommendations", "cropsData"),
                ("Government Schemes", "schemesData"),
                ("Weather Data", "weatherData"),
                ("Market Prices", "pricesData"),
                ("Pest Control", "pestData"),
                ("JavaScript Functions", "sendMessage"),
                ("Cache Busting", "cache-bust")
            ]
            
            for feature_name, feature_id in features:
                if feature_id in html_content:
                    print(f"✅ {feature_name}: Found")
                else:
                    print(f"❌ {feature_name}: Missing")
            
            print(f"\n📄 Page Size: {len(html_content):,} characters")
            print(f"🌐 Content-Type: {response.headers.get('content-type', 'Unknown')}")
            
        else:
            print(f"❌ Frontend not accessible: Status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Frontend test failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting Comprehensive Site Verification...")
    print("📍 Testing: http://127.0.0.1:8000/")
    print("🎯 Location: Raebareli (26.2°N, 81.2°E)")
    print()
    
    # Test all services
    service_results = test_all_services()
    
    # Test frontend features
    test_frontend_features()
    
    print("\n" + "=" * 60)
    print("🏁 VERIFICATION COMPLETE")
    print("=" * 60)
    
    if service_results['failed'] == 0:
        print("🎉 SUCCESS: All services are working perfectly!")
        print("🌾 Your Krishimitra AI system is fully operational!")
    else:
        print(f"⚠️  ATTENTION: {service_results['failed']} service(s) need fixing")
    
    print("\n💡 Next Steps:")
    print("1. Visit http://127.0.0.1:8000/ in your browser")
    print("2. Test the AI assistant with different queries")
    print("3. Try changing location to Raebareli")
    print("4. Verify all service cards are working")
    print("5. Test the location search functionality")