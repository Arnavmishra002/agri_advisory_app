#!/usr/bin/env python3
"""
Simple API test script to verify endpoints are working
"""
import requests
import json
import time

API_BASE = "http://localhost:8000/api"

def test_server():
    """Test if the server is running"""
    try:
        response = requests.get(f"{API_BASE}/", timeout=5)
        print(f"✅ Server Status: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Server Error: {e}")
        return False

def test_trending_crops():
    """Test trending crops endpoint"""
    try:
        response = requests.get(f"{API_BASE}/trending-crops/?lat=28.6139&lon=77.2090&lang=en", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Trending Crops: {len(data)} items")
            if data:
                print(f"   Sample: {data[0]}")
            return data
        else:
            print(f"❌ Trending Crops Error: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Trending Crops Exception: {e}")
        return []

def test_market_prices():
    """Test market prices endpoint"""
    try:
        response = requests.get(f"{API_BASE}/market-prices/prices/?lat=28.6139&lon=77.2090&lang=en", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Market Prices: {len(data)} items")
            if data:
                print(f"   Sample: {data[0]}")
            return data
        else:
            print(f"❌ Market Prices Error: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Market Prices Exception: {e}")
        return []

def test_chatbot():
    """Test chatbot endpoint"""
    try:
        response = requests.post(
            f"{API_BASE}/advisories/chatbot/",
            json={
                "query": "What crops should I plant?",
                "language": "en",
                "user_id": "test_user",
                "session_id": "test_session"
            },
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Chatbot: Response received")
            print(f"   Response: {data.get('response', 'No response')[:100]}...")
            return data
        else:
            print(f"❌ Chatbot Error: {response.status_code}")
            return {}
    except Exception as e:
        print(f"❌ Chatbot Exception: {e}")
        return {}

def main():
    print("🧪 Testing Krishimitra API Endpoints")
    print("=" * 50)
    
    # Test server
    if not test_server():
        print("\n❌ Server is not running. Please start Django server first.")
        return
    
    print("\n📊 Testing API Endpoints:")
    
    # Test trending crops
    crops_data = test_trending_crops()
    
    # Test market prices
    prices_data = test_market_prices()
    
    # Test chatbot
    chatbot_data = test_chatbot()
    
    print("\n📋 Summary:")
    print(f"   Trending Crops: {'✅' if crops_data else '❌'}")
    print(f"   Market Prices: {'✅' if prices_data else '❌'}")
    print(f"   Chatbot: {'✅' if chatbot_data else '❌'}")
    
    if crops_data and prices_data and chatbot_data:
        print("\n🎉 All API endpoints are working correctly!")
    else:
        print("\n⚠️  Some endpoints have issues. Check the Django server logs.")

if __name__ == "__main__":
    main()
