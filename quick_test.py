#!/usr/bin/env python3
"""
Quick test to verify API endpoints are working
"""

import requests
import json

def test_api_endpoints():
    base_url = "http://localhost:8000"
    
    print("🔍 Testing API Endpoints...")
    print("=" * 50)
    
    # Test 1: API Root
    print("\n1. Testing API Root...")
    try:
        response = requests.get(f"{base_url}/api/", timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("✅ API Root working!")
            print("Available endpoints:")
            for key, value in data.items():
                print(f"  - {key}: {value}")
        else:
            print(f"❌ API Root failed: {response.text}")
    except Exception as e:
        print(f"❌ Connection error: {e}")
    
    # Test 2: Schema endpoint
    print("\n2. Testing Schema endpoint...")
    try:
        response = requests.get(f"{base_url}/api/schema/", timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Schema endpoint working!")
            data = response.json()
            if 'paths' in data:
                print(f"Found {len(data['paths'])} API endpoints")
                for path in list(data['paths'].keys())[:5]:  # Show first 5
                    print(f"  - {path}")
            else:
                print("⚠️  Schema generated but no paths found")
        else:
            print(f"❌ Schema endpoint failed: {response.text}")
    except Exception as e:
        print(f"❌ Schema error: {e}")
    
    # Test 3: Chatbot endpoint
    print("\n3. Testing Chatbot endpoint...")
    try:
        response = requests.post(
            f"{base_url}/api/advisories/chatbot/",
            json={
                "query": "Hello! Test message",
                "language": "en",
                "user_id": "test_user"
            },
            timeout=10
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("✅ Chatbot endpoint working!")
            print(f"Response: {data.get('response', 'No response')[:100]}...")
        else:
            print(f"❌ Chatbot endpoint failed: {response.text}")
    except Exception as e:
        print(f"❌ Chatbot error: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Next Steps:")
    print("1. If all tests pass, Swagger UI should work")
    print("2. Go to: http://localhost:8000/api/schema/swagger-ui/")
    print("3. You should see all API endpoints listed")

if __name__ == "__main__":
    test_api_endpoints()
