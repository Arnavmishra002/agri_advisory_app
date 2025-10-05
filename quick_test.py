#!/usr/bin/env python3
"""
Quick test script to verify all components are working
"""
import requests
import json
import time

def test_server():
    """Test if Django server is running"""
    try:
        response = requests.get("http://127.0.0.1:8000/api/", timeout=5)
        if response.status_code == 200:
            print("✅ Django server is running")
            return True
        else:
            print(f"❌ Django server returned status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Django server not accessible: {e}")
        return False

def test_api_endpoints():
    """Test all API endpoints"""
    endpoints = [
        ("/api/trending-crops/?lat=28.6139&lon=77.2090&lang=en", "Trending Crops"),
        ("/api/market-prices/prices/?lat=28.6139&lon=77.2090&lang=en", "Market Prices"),
        ("/api/weather/current/?lat=28.6139&lon=77.2090&lang=en", "Weather"),
    ]
    
    results = {}
    
    for endpoint, name in endpoints:
        try:
            response = requests.get(f"http://127.0.0.1:8000{endpoint}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                results[name] = {"status": "✅", "data": data}
                print(f"✅ {name}: {len(data) if isinstance(data, list) else 'OK'}")
            else:
                results[name] = {"status": "❌", "error": f"Status {response.status_code}"}
                print(f"❌ {name}: Status {response.status_code}")
        except Exception as e:
            results[name] = {"status": "❌", "error": str(e)}
            print(f"❌ {name}: {e}")
    
    return results

def test_chatbot():
    """Test chatbot endpoint"""
    try:
        response = requests.post(
            "http://127.0.0.1:8000/api/advisory/chatbot/",
            json={
                "query": "What crops should I grow in Delhi?",
                "language": "en",
                "user_id": "test_user",
                "session_id": "test_session"
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Chatbot: Response received")
            print(f"   Response: {data.get('response', '')[:100]}...")
            return True
        else:
            print(f"❌ Chatbot: Status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Chatbot: {e}")
        return False

def main():
    print("🧪 Quick Test - Krishimitra Agricultural AI Assistant")
    print("=" * 60)
    
    # Test server
    if not test_server():
        print("\n❌ Server not running. Please start Django server first.")
        return
    
    print("\n📊 Testing API Endpoints:")
    results = test_api_endpoints()
    
    print("\n🤖 Testing Chatbot:")
    chatbot_ok = test_chatbot()
    
    print("\n📋 Summary:")
    print(f"   Trending Crops: {results.get('Trending Crops', {}).get('status', '❌')}")
    print(f"   Market Prices: {results.get('Market Prices', {}).get('status', '❌')}")
    print(f"   Weather: {results.get('Weather', {}).get('status', '❌')}")
    print(f"   Chatbot: {'✅' if chatbot_ok else '❌'}")
    
    # Check if Market Prices has data
    market_prices = results.get('Market Prices', {})
    if market_prices.get('status') == '✅':
        data = market_prices.get('data', [])
        if data:
            print(f"\n💰 Market Prices Data Sample:")
            for item in data[:3]:
                if isinstance(item, dict):
                    print(f"   {item.get('commodity', 'Unknown')}: {item.get('price', 'N/A')}")
        else:
            print("\n⚠️ Market Prices API returned empty data")
    
    print("\n🎉 Test completed!")

if __name__ == "__main__":
    main()
