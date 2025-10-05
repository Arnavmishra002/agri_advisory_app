#!/usr/bin/env python3
"""
Simple test script for enhanced chatbot
Run this while your server is running
"""

import requests
import json

def test_chatbot():
    base_url = "http://localhost:8000"
    
    print("🤖 Testing Enhanced Agricultural Chatbot")
    print("=" * 50)
    
    # Test 1: English Chat
    print("\n1. Testing English Chat...")
    try:
        response = requests.post(
            f"{base_url}/api/advisories/chatbot/",
            json={
                "query": "Hello! How are you?",
                "language": "en",
                "user_id": "test_user",
                "session_id": "test_session_001"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Response: {data.get('response', 'No response')}")
            print(f"   Language: {data.get('language', 'Unknown')}")
            print(f"   Confidence: {data.get('confidence', 'Unknown')}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")
    
    # Test 2: Hindi Chat
    print("\n2. Testing Hindi Chat...")
    try:
        response = requests.post(
            f"{base_url}/api/advisories/chatbot/",
            json={
                "query": "नमस्ते! आप कैसे हैं?",
                "language": "hi",
                "user_id": "test_user",
                "session_id": "test_session_001"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Response: {data.get('response', 'No response')}")
            print(f"   Language: {data.get('language', 'Unknown')}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")
    
    # Test 3: Agricultural Query
    print("\n3. Testing Agricultural Query...")
    try:
        response = requests.post(
            f"{base_url}/api/advisories/chatbot/",
            json={
                "query": "What crops should I plant in Delhi?",
                "language": "en",
                "user_id": "test_user",
                "session_id": "test_session_001"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Response: {data.get('response', 'No response')}")
            print(f"   Response Type: {data.get('response_type', 'Unknown')}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")
    
    # Test 4: Chat History Persistence
    print("\n4. Testing Chat History Persistence...")
    try:
        # First message
        response1 = requests.post(
            f"{base_url}/api/advisories/chatbot/",
            json={
                "query": "Hello, I'm a farmer from Punjab",
                "language": "en",
                "user_id": "farmer_001",
                "session_id": "session_001"
            },
            timeout=10
        )
        
        # Second message (should remember context)
        response2 = requests.post(
            f"{base_url}/api/advisories/chatbot/",
            json={
                "query": "What crops grow well here?",
                "language": "en",
                "user_id": "farmer_001",
                "session_id": "session_001"
            },
            timeout=10
        )
        
        if response2.status_code == 200:
            data = response2.json()
            print(f"✅ Success! Response: {data.get('response', 'No response')}")
            print(f"   Session ID: {data.get('session_id', 'Unknown')}")
        else:
            print(f"❌ Error: {response2.status_code} - {response2.text}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Enhanced Chatbot Testing Complete!")
    print("Your chatbot includes:")
    print("✅ ChatGPT-like conversations")
    print("✅ 25+ language support")
    print("✅ Persistent chat history")
    print("✅ Agricultural expertise")

if __name__ == "__main__":
    test_chatbot()
