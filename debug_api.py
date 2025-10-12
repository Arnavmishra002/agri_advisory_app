#!/usr/bin/env python3
"""
Debug API issues
"""

import requests
import json

def test_chatbot_api():
    """Test chatbot API with minimal data"""
    base_url = "http://127.0.0.1:8000"
    
    print("🔍 DEBUGGING CHATBOT API")
    print("=" * 40)
    
    # Test 1: Minimal request
    print("\n📝 Test 1: Minimal request")
    try:
        data = {
            "query": "hello"
        }
        
        response = requests.post(
            f"{base_url}/api/chatbot/",
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        if response.status_code == 400:
            try:
                error_data = response.json()
                print(f"Error Details: {error_data}")
            except:
                print("Could not parse error response as JSON")
                
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Check API endpoint structure
    print("\n📝 Test 2: Check API endpoint structure")
    try:
        response = requests.get(f"{base_url}/api/", timeout=5)
        print(f"API Root Status: {response.status_code}")
        print(f"API Root Response: {response.text[:200]}...")
    except Exception as e:
        print(f"API Root Error: {e}")
    
    # Test 3: Check chatbot endpoint directly
    print("\n📝 Test 3: Check chatbot endpoint")
    try:
        response = requests.get(f"{base_url}/api/chatbot/", timeout=5)
        print(f"Chatbot GET Status: {response.status_code}")
        print(f"Chatbot GET Response: {response.text[:200]}...")
    except Exception as e:
        print(f"Chatbot GET Error: {e}")

if __name__ == "__main__":
    test_chatbot_api()
