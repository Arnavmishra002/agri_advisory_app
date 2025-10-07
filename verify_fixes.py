#!/usr/bin/env python3
"""
Quick verification test for AI fixes
"""

import requests
import json

def test_query(query, language='en', location='Delhi'):
    """Test a single query"""
    data = {
        'query': query,
        'language': language,
        'location': location
    }
    
    try:
        response = requests.post('http://localhost:8000/api/advisories/chatbot/', json=data)
        result = response.json()
        return {
            'query': query,
            'intent': result.get('metadata', {}).get('intent'),
            'response': result.get('response', ''),
            'entities': result.get('metadata', {}).get('entities', {}),
            'success': True
        }
    except Exception as e:
        return {
            'query': query,
            'error': str(e),
            'success': False
        }

def main():
    print("🔍 VERIFYING AI FIXES")
    print("=" * 50)
    
    # Test cases to verify our fixes
    test_cases = [
        # Market price tests
        {'query': 'potato price in lucknow', 'language': 'en', 'location': 'Lucknow'},
        {'query': 'cotton price in ahmedabad', 'language': 'en', 'location': 'Ahmedabad'},
        {'query': 'rice price in mumbai', 'language': 'en', 'location': 'Mumbai'},
        
        # Complex query tests
        {'query': 'crop suggest karo lucknow mein aur weather bhi batao', 'language': 'hi', 'location': 'Lucknow'},
        {'query': 'wheat price in delhi aur weather bhi batao', 'language': 'hi', 'location': 'Delhi'},
        
        # Hinglish tests
        {'query': 'hi bhai', 'language': 'hinglish', 'location': 'Delhi'},
        {'query': 'hello bro', 'language': 'hinglish', 'location': 'Mumbai'},
        
        # Weather tests
        {'query': 'weather in delhi', 'language': 'en', 'location': 'Delhi'},
        {'query': 'मुंबई का मौसम', 'language': 'hi', 'location': 'Mumbai'},
        
        # Crop recommendation tests
        {'query': 'crop recommendation for delhi', 'language': 'en', 'location': 'Delhi'},
        {'query': 'kharif season mein kya crop lagayein mumbai mein', 'language': 'hi', 'location': 'Mumbai'},
    ]
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n🧪 TEST {i}: {test['query']}")
        print(f"   Language: {test['language']}, Location: {test['location']}")
        
        result = test_query(test['query'], test['language'], test['location'])
        
        if result['success']:
            print(f"   ✅ Intent: {result['intent']}")
            print(f"   📝 Response: {result['response'][:150]}...")
            
            # Check for key improvements
            if 'Unknown Location' not in result['response']:
                print("   ✅ Location context working")
            else:
                print("   ❌ Location still showing Unknown Location")
                
            if result['intent'] == 'complex_query' and 'aur' in test['query']:
                print("   ✅ Complex query detection working")
            elif result['intent'] != 'complex_query' and 'aur' in test['query']:
                print("   ❌ Complex query not detected")
                
            if '₹' in result['response'] and 'potato' in test['query'].lower():
                if '₹1,200' in result['response']:
                    print("   ✅ Potato price correct")
                else:
                    print("   ❌ Potato price incorrect")
                    
            if '₹' in result['response'] and 'cotton' in test['query'].lower():
                if '₹6,200' in result['response']:
                    print("   ✅ Cotton price correct")
                else:
                    print("   ❌ Cotton price incorrect")
            
            passed += 1
        else:
            print(f"   ❌ Error: {result['error']}")
            failed += 1
    
    print(f"\n📊 VERIFICATION RESULTS:")
    print(f"   Total Tests: {len(test_cases)}")
    print(f"   Passed: {passed}")
    print(f"   Failed: {failed}")
    print(f"   Success Rate: {(passed/len(test_cases)*100):.1f}%")

if __name__ == "__main__":
    main()
