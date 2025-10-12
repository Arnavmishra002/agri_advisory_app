#!/usr/bin/env python3
"""
Debug 500 errors on live website
"""

import requests
import json

def debug_live_errors():
    """Debug 500 errors on live website"""
    base_url = "https://krishmitra-zrk4.onrender.com"
    
    print("🔍 DEBUGGING LIVE WEBSITE ERRORS")
    print("=" * 50)
    
    # Test chatbot endpoint with detailed error info
    print("\n📝 Testing Chatbot API:")
    try:
        url = f"{base_url}/api/chatbot/"
        data = {"query": "test"}
        
        response = requests.post(url, json=data, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        try:
            error_data = response.json()
            print(f"Error Response: {json.dumps(error_data, indent=2)}")
        except:
            print(f"Raw Response: {response.text[:500]}...")
            
    except Exception as e:
        print(f"Request Error: {e}")
    
    # Test location endpoint
    print("\n📝 Testing Location API:")
    try:
        url = f"{base_url}/api/locations/suggestions/?q=delhi"
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        try:
            error_data = response.json()
            print(f"Error Response: {json.dumps(error_data, indent=2)}")
        except:
            print(f"Raw Response: {response.text[:500]}...")
            
    except Exception as e:
        print(f"Request Error: {e}")
    
    # Test health endpoint (working)
    print("\n📝 Testing Health API (should work):")
    try:
        url = f"{base_url}/api/health/"
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"Request Error: {e}")

if __name__ == "__main__":
    debug_live_errors()
