#!/usr/bin/env python3
"""
Debug script to examine actual AI responses and identify keyword matching issues
"""

import requests
import json
import time

def test_ai_responses():
    """Test specific failing queries to see actual responses"""
    base_url = "http://localhost:8000"
    headers = {'Content-Type': 'application/json'}
    
    # Test cases that are currently failing
    failing_tests = [
        {
            "name": "English Greeting",
            "query": "hello",
            "language": "en"
        },
        {
            "name": "Hinglish Greeting", 
            "query": "hi bhai",
            "language": "hi"
        },
        {
            "name": "Crop Suggestion (English)",
            "query": "crop recommendation for delhi",
            "language": "en",
            "location": "Delhi"
        },
        {
            "name": "Weather Delhi",
            "query": "weather in delhi",
            "language": "en",
            "location": "Delhi"
        },
        {
            "name": "Potato Price Lucknow",
            "query": "potato price in lucknow",
            "language": "en",
            "location": "Lucknow",
            "lat": 26.8467,
            "lon": 80.9462
        },
        {
            "name": "Cotton Price Gujarat",
            "query": "cotton price in ahmedabad",
            "language": "en",
            "location": "Ahmedabad",
            "lat": 23.0225,
            "lon": 72.5714
        }
    ]
    
    print("🔍 DEBUGGING AI RESPONSES")
    print("=" * 60)
    
    for test in failing_tests:
        print(f"\n🧪 Testing: {test['name']}")
        print(f"📝 Query: '{test['query']}'")
        print("-" * 40)
        
        payload = {
            'query': test['query'],
            'language': test.get('language', 'hi'),
            'session_id': f'debug-{int(time.time())}',
            'latitude': test.get('lat', 28.6139),
            'longitude': test.get('lon', 77.2090),
            'location_name': test.get('location', 'Delhi')
        }
        
        try:
            response = requests.post(
                f"{base_url}/api/advisories/chatbot/",
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            response_text = data.get('response', '')
            intent = data.get('metadata', {}).get('intent', 'unknown')
            confidence = data.get('confidence', 0)
            
            print(f"📊 Intent: {intent}")
            print(f"📊 Confidence: {confidence:.2f}")
            print(f"📝 Full Response:")
            print(f"   {response_text}")
            print(f"\n🔍 Response Analysis:")
            print(f"   Length: {len(response_text)} characters")
            print(f"   Contains Hindi: {'है' in response_text or 'में' in response_text}")
            print(f"   Contains English: {any(word in response_text.lower() for word in ['hello', 'crop', 'weather', 'price'])}")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        print("=" * 60)

if __name__ == "__main__":
    test_ai_responses()
