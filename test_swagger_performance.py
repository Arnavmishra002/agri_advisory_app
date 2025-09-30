#!/usr/bin/env python
"""
Test script to verify Swagger UI performance optimizations
"""
import requests
import time
import json

def test_endpoint_performance(url, name):
    """Test endpoint response time"""
    try:
        start_time = time.time()
        response = requests.get(url, timeout=30)
        end_time = time.time()
        
        response_time = end_time - start_time
        status = "✅ SUCCESS" if response.status_code == 200 else "❌ FAILED"
        
        print(f"{name}: {status} - {response_time:.2f}s")
        return response_time, response.status_code == 200
    except Exception as e:
        print(f"{name}: ❌ ERROR - {str(e)}")
        return None, False

def main():
    base_url = "http://localhost:8000"
    
    print("🚀 Testing Swagger UI Performance Optimizations")
    print("=" * 50)
    
    endpoints = [
        (f"{base_url}/api/docs/html/", "Fast HTML Docs"),
        (f"{base_url}/api/docs/", "Fast JSON Docs"),
        (f"{base_url}/api/schema/fast/", "Fast Schema"),
        (f"{base_url}/api/schema/", "Cached Schema"),
        (f"{base_url}/api/schema/swagger-ui/", "Optimized Swagger UI"),
    ]
    
    results = []
    
    for url, name in endpoints:
        response_time, success = test_endpoint_performance(url, name)
        results.append((name, response_time, success))
    
    print("\n📊 Performance Summary:")
    print("=" * 30)
    
    successful_tests = [r for r in results if r[2]]
    if successful_tests:
        fastest = min(successful_tests, key=lambda x: x[1] if x[1] else float('inf'))
        print(f"🏆 Fastest: {fastest[0]} ({fastest[1]:.2f}s)")
        
        # Show all results
        for name, response_time, success in results:
            if success and response_time:
                speed_indicator = "⚡" if response_time < 1.0 else "🐌" if response_time > 5.0 else "✅"
                print(f"{speed_indicator} {name}: {response_time:.2f}s")
    
    print("\n💡 Recommendations:")
    print("- Use /api/docs/html/ for fastest documentation access")
    print("- Use /api/schema/fast/ for lightweight API schema")
    print("- Use /api/schema/swagger-ui/ for full interactive documentation")

if __name__ == "__main__":
    main()
