#!/usr/bin/env python3
"""
Simple Location Search Test
"""

import requests
import json

def test_simple_search():
    """Test simple location search"""
    print("Testing Simple Location Search...")
    
    try:
        # Test with a simple query
        response = requests.get(
            "http://127.0.0.1:8000/api/locations/search/?q=Delhi",
            timeout=5
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success! Found {len(data.get('suggestions', []))} suggestions")
            return True
        else:
            print(f"Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Exception: {e}")
        return False

def test_server_status():
    """Test if server is running"""
    print("Testing Server Status...")
    
    try:
        response = requests.get("http://127.0.0.1:8000/", timeout=5)
        print(f"Server Status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"Server not responding: {e}")
        return False

if __name__ == "__main__":
    print("Starting Location Search Debug Test")
    print("=" * 40)
    
    # Test server status first
    if test_server_status():
        print("Server is running")
        test_simple_search()
    else:
        print("Server is not running or not accessible")

"""
Simple Location Search Test
"""

import requests
import json

def test_simple_search():
    """Test simple location search"""
    print("Testing Simple Location Search...")
    
    try:
        # Test with a simple query
        response = requests.get(
            "http://127.0.0.1:8000/api/locations/search/?q=Delhi",
            timeout=5
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success! Found {len(data.get('suggestions', []))} suggestions")
            return True
        else:
            print(f"Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Exception: {e}")
        return False

def test_server_status():
    """Test if server is running"""
    print("Testing Server Status...")
    
    try:
        response = requests.get("http://127.0.0.1:8000/", timeout=5)
        print(f"Server Status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"Server not responding: {e}")
        return False

if __name__ == "__main__":
    print("Starting Location Search Debug Test")
    print("=" * 40)
    
    # Test server status first
    if test_server_status():
        print("Server is running")
        test_simple_search()
    else:
        print("Server is not running or not accessible")
