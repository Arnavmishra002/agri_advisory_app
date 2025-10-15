#!/usr/bin/env python3
"""
Comprehensive Website Analysis
Tests all services and features on the Krishimitra AI website
"""

import requests
import json
import time
from datetime import datetime

def analyze_website():
    """Comprehensive analysis of all website features"""
    base_url = "http://127.0.0.1:8000"
    
    print("KRISHIMITRA AI - COMPREHENSIVE WEBSITE ANALYSIS")
    print("=" * 60)
    print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Website URL: {base_url}")
    print("=" * 60)
    
    # Test results storage
    results = {
        "homepage": {},
        "services": {},
        "location_features": {},
        "crop_search": {},
        "ai_chatbot": {},
        "ui_features": {}
    }
    
    # 1. HOMEPAGE ANALYSIS
    print("\n1. HOMEPAGE ANALYSIS")
    print("-" * 30)
    
    try:
        response = requests.get(base_url, timeout=10)
        if response.status_code == 200:
            results["homepage"]["status"] = "SUCCESS"
            results["homepage"]["load_time"] = response.elapsed.total_seconds()
            print(f"SUCCESS: Homepage loads successfully ({response.elapsed.total_seconds():.2f}s)")
            
            # Check for key elements in HTML
            html_content = response.text
            key_elements = [
                "Krishimitra AI",
                "service-card",
                "location-search",
                "crop-search",
                "AI सहायक"
            ]
            
            for element in key_elements:
                if element in html_content:
                    print(f"SUCCESS: Found {element}")
                else:
                    print(f"ERROR: Missing {element}")
                    
        else:
            results["homepage"]["status"] = "ERROR"
            results["homepage"]["error"] = f"HTTP {response.status_code}"
            print(f"ERROR: Homepage failed: HTTP {response.status_code}")
            
    except Exception as e:
        results["homepage"]["status"] = "ERROR"
        results["homepage"]["error"] = str(e)
        print(f"ERROR: Homepage error: {str(e)}")
    
    # 2. SERVICES ANALYSIS
    print("\n2. SERVICES ANALYSIS")
    print("-" * 30)
    
    services = [
        "crop_recommendations",
        "weather", 
        "market_prices",
        "government_schemes",
        "pest_detection"
    ]
    
    test_locations = [
        {"name": "Delhi", "lat": 28.7041, "lon": 77.1025},
        {"name": "Mumbai", "lat": 19.0760, "lon": 72.8777},
        {"name": "Bangalore", "lat": 12.9716, "lon": 77.5946}
    ]
    
    for service in services:
        print(f"\nTesting {service}:")
        service_results = []
        
        for location in test_locations:
            try:
                url = f"{base_url}/api/realtime-gov/{service}/"
                
                if service == "pest_detection":
                    data = {
                        "crop": "wheat",
                        "location": location['name'],
                        "latitude": location['lat'],
                        "longitude": location['lon'],
                        "symptoms": ""
                    }
                    response = requests.post(url, json=data, timeout=10)
                else:
                    params = {
                        "location": location['name'],
                        "latitude": location['lat'],
                        "longitude": location['lon']
                    }
                    response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Analyze response data
                    has_data = False
                    data_keys = []
                    
                    if service == "crop_recommendations":
                        has_data = "top_4_recommendations" in data and len(data.get("top_4_recommendations", [])) > 0
                        data_keys = list(data.keys())
                    elif service == "weather":
                        has_data = "weather_data" in data
                        data_keys = list(data.keys())
                    elif service == "market_prices":
                        has_data = "market_data" in data and len(data.get("market_data", {})) > 0
                        data_keys = list(data.keys())
                    elif service == "government_schemes":
                        has_data = ("schemes" in data or "central_schemes" in data) and len(data.get("schemes", data.get("central_schemes", []))) > 0
                        data_keys = list(data.keys())
                    elif service == "pest_detection":
                        has_data = "pest_data" in data or "pest_info" in data
                        data_keys = list(data.keys())
                    
                    service_results.append({
                        "location": location['name'],
                        "status": "SUCCESS",
                        "has_data": has_data,
                        "response_time": response.elapsed.total_seconds(),
                        "data_keys": data_keys
                    })
                    
                    status = "SUCCESS" if has_data else "WARNING"
                    print(f"  {status} {location['name']}: {response.elapsed.total_seconds():.2f}s - Data: {has_data}")
                    
                else:
                    service_results.append({
                        "location": location['name'],
                        "status": "ERROR",
                        "error": f"HTTP {response.status_code}"
                    })
                    print(f"  ERROR {location['name']}: HTTP {response.status_code}")
                    
            except Exception as e:
                service_results.append({
                    "location": location['name'],
                    "status": "ERROR",
                    "error": str(e)
                })
                print(f"  ERROR {location['name']}: {str(e)}")
        
        results["services"][service] = service_results
    
    # 3. LOCATION FEATURES ANALYSIS
    print("\n3. LOCATION FEATURES ANALYSIS")
    print("-" * 30)
    
    # Test location search
    test_locations_search = ["Delhi", "Mumbai", "Bangalore", "Chennai", "Kolkata", "Pune", "Hyderabad", "Jaipur"]
    
    location_search_results = []
    for location in test_locations_search:
        try:
            url = f"{base_url}/api/locations/search/"
            params = {"q": location}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                suggestions = data.get("suggestions", [])
                found = len(suggestions) > 0
                
                location_search_results.append({
                    "location": location,
                    "status": "SUCCESS",
                    "found": found,
                    "suggestions_count": len(suggestions)
                })
                
                status = "SUCCESS" if found else "WARNING"
                print(f"  {status} {location}: {len(suggestions)} suggestions")
            else:
                location_search_results.append({
                    "location": location,
                    "status": "ERROR",
                    "error": f"HTTP {response.status_code}"
                })
                print(f"  ERROR {location}: HTTP {response.status_code}")
                
        except Exception as e:
            location_search_results.append({
                "location": location,
                "status": "ERROR",
                "error": str(e)
            })
            print(f"  ERROR {location}: {str(e)}")
    
    results["location_features"]["search"] = location_search_results
    
    # 4. CROP SEARCH ANALYSIS
    print("\n4. CROP SEARCH ANALYSIS")
    print("-" * 30)
    
    test_crops = ["wheat", "rice", "tomato", "potato", "onion", "cotton", "sugarcane", "maize"]
    
    crop_search_results = []
    for crop in test_crops:
        try:
            url = f"{base_url}/api/realtime-gov/crop_search/"
            params = {
                "crop": crop,
                "location": "Delhi",
                "latitude": 28.7041,
                "longitude": 77.1025
            }
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                has_analysis = "comprehensive_analysis" in data
                
                crop_search_results.append({
                    "crop": crop,
                    "status": "SUCCESS",
                    "has_analysis": has_analysis,
                    "response_time": response.elapsed.total_seconds()
                })
                
                status = "SUCCESS" if has_analysis else "WARNING"
                print(f"  {status} {crop}: {response.elapsed.total_seconds():.2f}s - Analysis: {has_analysis}")
            else:
                crop_search_results.append({
                    "crop": crop,
                    "status": "ERROR",
                    "error": f"HTTP {response.status_code}"
                })
                print(f"  ERROR {crop}: HTTP {response.status_code}")
                
        except Exception as e:
            crop_search_results.append({
                "crop": crop,
                "status": "ERROR",
                "error": str(e)
            })
            print(f"  ERROR {crop}: {str(e)}")
    
    results["crop_search"] = crop_search_results
    
    # 5. AI CHATBOT ANALYSIS
    print("\n5. AI CHATBOT ANALYSIS")
    print("-" * 30)
    
    test_queries = [
        "Delhi mein kya fasal lagayein?",
        "Mumbai ka mausam kaisa hai?",
        "What crops are suitable for Bangalore?",
        "Government schemes for farmers",
        "Market prices for wheat"
    ]
    
    chatbot_results = []
    for query in test_queries:
        try:
            url = f"{base_url}/api/chatbot/"
            data = {
                "query": query,
                "language": "hinglish",
                "latitude": 28.7041,
                "longitude": 77.1025,
                "location": "Delhi"
            }
            response = requests.post(url, json=data, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                has_response = "response" in data and len(data.get("response", "")) > 0
                
                chatbot_results.append({
                    "query": query[:30] + "...",
                    "status": "SUCCESS",
                    "has_response": has_response,
                    "response_time": response.elapsed.total_seconds()
                })
                
                status = "SUCCESS" if has_response else "WARNING"
                print(f"  {status} Query: {response.elapsed.total_seconds():.2f}s - Response: {has_response}")
            else:
                chatbot_results.append({
                    "query": query[:30] + "...",
                    "status": "ERROR",
                    "error": f"HTTP {response.status_code}"
                })
                print(f"  ERROR Query: HTTP {response.status_code}")
                
        except Exception as e:
            chatbot_results.append({
                "query": query[:30] + "...",
                "status": "ERROR",
                "error": str(e)
            })
            print(f"  ERROR Query: {str(e)}")
    
    results["ai_chatbot"] = chatbot_results
    
    # 6. SUMMARY ANALYSIS
    print("\n6. SUMMARY ANALYSIS")
    print("-" * 30)
    
    # Calculate overall statistics
    total_tests = 0
    successful_tests = 0
    issues_found = []
    
    # Homepage
    if results["homepage"]["status"] == "SUCCESS":
        successful_tests += 1
    else:
        issues_found.append(f"Homepage: {results['homepage'].get('error', 'Unknown error')}")
    total_tests += 1
    
    # Services
    for service, service_results in results["services"].items():
        for result in service_results:
            total_tests += 1
            if result["status"] == "SUCCESS":
                successful_tests += 1
                if not result.get("has_data", False):
                    issues_found.append(f"{service} in {result['location']}: No data returned")
            else:
                issues_found.append(f"{service} in {result['location']}: {result.get('error', 'Unknown error')}")
    
    # Location search
    for result in results["location_features"]["search"]:
        total_tests += 1
        if result["status"] == "SUCCESS":
            successful_tests += 1
            if not result.get("found", False):
                issues_found.append(f"Location search for {result['location']}: No suggestions found")
        else:
            issues_found.append(f"Location search for {result['location']}: {result.get('error', 'Unknown error')}")
    
    # Crop search
    for result in results["crop_search"]:
        total_tests += 1
        if result["status"] == "SUCCESS":
            successful_tests += 1
            if not result.get("has_analysis", False):
                issues_found.append(f"Crop search for {result['crop']}: No analysis returned")
        else:
            issues_found.append(f"Crop search for {result['crop']}: {result.get('error', 'Unknown error')}")
    
    # AI Chatbot
    for result in results["ai_chatbot"]:
        total_tests += 1
        if result["status"] == "SUCCESS":
            successful_tests += 1
            if not result.get("has_response", False):
                issues_found.append(f"AI Chatbot query: No response returned")
        else:
            issues_found.append(f"AI Chatbot query: {result.get('error', 'Unknown error')}")
    
    success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"Total Tests: {total_tests}")
    print(f"Successful Tests: {successful_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"Issues Found: {len(issues_found)}")
    
    if issues_found:
        print("\nISSUES IDENTIFIED:")
        for i, issue in enumerate(issues_found, 1):
            print(f"{i}. {issue}")
    else:
        print("\nSUCCESS: NO ISSUES FOUND - All features working perfectly!")
    
    # Performance Analysis
    print("\n7. PERFORMANCE ANALYSIS")
    print("-" * 30)
    
    all_response_times = []
    for service_results in results["services"].values():
        for result in service_results:
            if "response_time" in result:
                all_response_times.append(result["response_time"])
    
    if all_response_times:
        avg_response_time = sum(all_response_times) / len(all_response_times)
        max_response_time = max(all_response_times)
        min_response_time = min(all_response_times)
        
        print(f"Average Response Time: {avg_response_time:.2f}s")
        print(f"Fastest Response: {min_response_time:.2f}s")
        print(f"Slowest Response: {max_response_time:.2f}s")
        
        if avg_response_time < 2.0:
            print("SUCCESS: EXCELLENT performance!")
        elif avg_response_time < 5.0:
            print("WARNING: GOOD performance")
        else:
            print("ERROR: SLOW performance - needs optimization")
    
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    
    return results

if __name__ == "__main__":
    analyze_website()

Comprehensive Website Analysis
Tests all services and features on the Krishimitra AI website
"""

import requests
import json
import time
from datetime import datetime

def analyze_website():
    """Comprehensive analysis of all website features"""
    base_url = "http://127.0.0.1:8000"
    
    print("KRISHIMITRA AI - COMPREHENSIVE WEBSITE ANALYSIS")
    print("=" * 60)
    print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Website URL: {base_url}")
    print("=" * 60)
    
    # Test results storage
    results = {
        "homepage": {},
        "services": {},
        "location_features": {},
        "crop_search": {},
        "ai_chatbot": {},
        "ui_features": {}
    }
    
    # 1. HOMEPAGE ANALYSIS
    print("\n1. HOMEPAGE ANALYSIS")
    print("-" * 30)
    
    try:
        response = requests.get(base_url, timeout=10)
        if response.status_code == 200:
            results["homepage"]["status"] = "SUCCESS"
            results["homepage"]["load_time"] = response.elapsed.total_seconds()
            print(f"SUCCESS: Homepage loads successfully ({response.elapsed.total_seconds():.2f}s)")
            
            # Check for key elements in HTML
            html_content = response.text
            key_elements = [
                "Krishimitra AI",
                "service-card",
                "location-search",
                "crop-search",
                "AI सहायक"
            ]
            
            for element in key_elements:
                if element in html_content:
                    print(f"SUCCESS: Found {element}")
                else:
                    print(f"ERROR: Missing {element}")
                    
        else:
            results["homepage"]["status"] = "ERROR"
            results["homepage"]["error"] = f"HTTP {response.status_code}"
            print(f"ERROR: Homepage failed: HTTP {response.status_code}")
            
    except Exception as e:
        results["homepage"]["status"] = "ERROR"
        results["homepage"]["error"] = str(e)
        print(f"ERROR: Homepage error: {str(e)}")
    
    # 2. SERVICES ANALYSIS
    print("\n2. SERVICES ANALYSIS")
    print("-" * 30)
    
    services = [
        "crop_recommendations",
        "weather", 
        "market_prices",
        "government_schemes",
        "pest_detection"
    ]
    
    test_locations = [
        {"name": "Delhi", "lat": 28.7041, "lon": 77.1025},
        {"name": "Mumbai", "lat": 19.0760, "lon": 72.8777},
        {"name": "Bangalore", "lat": 12.9716, "lon": 77.5946}
    ]
    
    for service in services:
        print(f"\nTesting {service}:")
        service_results = []
        
        for location in test_locations:
            try:
                url = f"{base_url}/api/realtime-gov/{service}/"
                
                if service == "pest_detection":
                    data = {
                        "crop": "wheat",
                        "location": location['name'],
                        "latitude": location['lat'],
                        "longitude": location['lon'],
                        "symptoms": ""
                    }
                    response = requests.post(url, json=data, timeout=10)
                else:
                    params = {
                        "location": location['name'],
                        "latitude": location['lat'],
                        "longitude": location['lon']
                    }
                    response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Analyze response data
                    has_data = False
                    data_keys = []
                    
                    if service == "crop_recommendations":
                        has_data = "top_4_recommendations" in data and len(data.get("top_4_recommendations", [])) > 0
                        data_keys = list(data.keys())
                    elif service == "weather":
                        has_data = "weather_data" in data
                        data_keys = list(data.keys())
                    elif service == "market_prices":
                        has_data = "market_data" in data and len(data.get("market_data", {})) > 0
                        data_keys = list(data.keys())
                    elif service == "government_schemes":
                        has_data = ("schemes" in data or "central_schemes" in data) and len(data.get("schemes", data.get("central_schemes", []))) > 0
                        data_keys = list(data.keys())
                    elif service == "pest_detection":
                        has_data = "pest_data" in data or "pest_info" in data
                        data_keys = list(data.keys())
                    
                    service_results.append({
                        "location": location['name'],
                        "status": "SUCCESS",
                        "has_data": has_data,
                        "response_time": response.elapsed.total_seconds(),
                        "data_keys": data_keys
                    })
                    
                    status = "SUCCESS" if has_data else "WARNING"
                    print(f"  {status} {location['name']}: {response.elapsed.total_seconds():.2f}s - Data: {has_data}")
                    
                else:
                    service_results.append({
                        "location": location['name'],
                        "status": "ERROR",
                        "error": f"HTTP {response.status_code}"
                    })
                    print(f"  ERROR {location['name']}: HTTP {response.status_code}")
                    
            except Exception as e:
                service_results.append({
                    "location": location['name'],
                    "status": "ERROR",
                    "error": str(e)
                })
                print(f"  ERROR {location['name']}: {str(e)}")
        
        results["services"][service] = service_results
    
    # 3. LOCATION FEATURES ANALYSIS
    print("\n3. LOCATION FEATURES ANALYSIS")
    print("-" * 30)
    
    # Test location search
    test_locations_search = ["Delhi", "Mumbai", "Bangalore", "Chennai", "Kolkata", "Pune", "Hyderabad", "Jaipur"]
    
    location_search_results = []
    for location in test_locations_search:
        try:
            url = f"{base_url}/api/locations/search/"
            params = {"q": location}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                suggestions = data.get("suggestions", [])
                found = len(suggestions) > 0
                
                location_search_results.append({
                    "location": location,
                    "status": "SUCCESS",
                    "found": found,
                    "suggestions_count": len(suggestions)
                })
                
                status = "SUCCESS" if found else "WARNING"
                print(f"  {status} {location}: {len(suggestions)} suggestions")
            else:
                location_search_results.append({
                    "location": location,
                    "status": "ERROR",
                    "error": f"HTTP {response.status_code}"
                })
                print(f"  ERROR {location}: HTTP {response.status_code}")
                
        except Exception as e:
            location_search_results.append({
                "location": location,
                "status": "ERROR",
                "error": str(e)
            })
            print(f"  ERROR {location}: {str(e)}")
    
    results["location_features"]["search"] = location_search_results
    
    # 4. CROP SEARCH ANALYSIS
    print("\n4. CROP SEARCH ANALYSIS")
    print("-" * 30)
    
    test_crops = ["wheat", "rice", "tomato", "potato", "onion", "cotton", "sugarcane", "maize"]
    
    crop_search_results = []
    for crop in test_crops:
        try:
            url = f"{base_url}/api/realtime-gov/crop_search/"
            params = {
                "crop": crop,
                "location": "Delhi",
                "latitude": 28.7041,
                "longitude": 77.1025
            }
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                has_analysis = "comprehensive_analysis" in data
                
                crop_search_results.append({
                    "crop": crop,
                    "status": "SUCCESS",
                    "has_analysis": has_analysis,
                    "response_time": response.elapsed.total_seconds()
                })
                
                status = "SUCCESS" if has_analysis else "WARNING"
                print(f"  {status} {crop}: {response.elapsed.total_seconds():.2f}s - Analysis: {has_analysis}")
            else:
                crop_search_results.append({
                    "crop": crop,
                    "status": "ERROR",
                    "error": f"HTTP {response.status_code}"
                })
                print(f"  ERROR {crop}: HTTP {response.status_code}")
                
        except Exception as e:
            crop_search_results.append({
                "crop": crop,
                "status": "ERROR",
                "error": str(e)
            })
            print(f"  ERROR {crop}: {str(e)}")
    
    results["crop_search"] = crop_search_results
    
    # 5. AI CHATBOT ANALYSIS
    print("\n5. AI CHATBOT ANALYSIS")
    print("-" * 30)
    
    test_queries = [
        "Delhi mein kya fasal lagayein?",
        "Mumbai ka mausam kaisa hai?",
        "What crops are suitable for Bangalore?",
        "Government schemes for farmers",
        "Market prices for wheat"
    ]
    
    chatbot_results = []
    for query in test_queries:
        try:
            url = f"{base_url}/api/chatbot/"
            data = {
                "query": query,
                "language": "hinglish",
                "latitude": 28.7041,
                "longitude": 77.1025,
                "location": "Delhi"
            }
            response = requests.post(url, json=data, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                has_response = "response" in data and len(data.get("response", "")) > 0
                
                chatbot_results.append({
                    "query": query[:30] + "...",
                    "status": "SUCCESS",
                    "has_response": has_response,
                    "response_time": response.elapsed.total_seconds()
                })
                
                status = "SUCCESS" if has_response else "WARNING"
                print(f"  {status} Query: {response.elapsed.total_seconds():.2f}s - Response: {has_response}")
            else:
                chatbot_results.append({
                    "query": query[:30] + "...",
                    "status": "ERROR",
                    "error": f"HTTP {response.status_code}"
                })
                print(f"  ERROR Query: HTTP {response.status_code}")
                
        except Exception as e:
            chatbot_results.append({
                "query": query[:30] + "...",
                "status": "ERROR",
                "error": str(e)
            })
            print(f"  ERROR Query: {str(e)}")
    
    results["ai_chatbot"] = chatbot_results
    
    # 6. SUMMARY ANALYSIS
    print("\n6. SUMMARY ANALYSIS")
    print("-" * 30)
    
    # Calculate overall statistics
    total_tests = 0
    successful_tests = 0
    issues_found = []
    
    # Homepage
    if results["homepage"]["status"] == "SUCCESS":
        successful_tests += 1
    else:
        issues_found.append(f"Homepage: {results['homepage'].get('error', 'Unknown error')}")
    total_tests += 1
    
    # Services
    for service, service_results in results["services"].items():
        for result in service_results:
            total_tests += 1
            if result["status"] == "SUCCESS":
                successful_tests += 1
                if not result.get("has_data", False):
                    issues_found.append(f"{service} in {result['location']}: No data returned")
            else:
                issues_found.append(f"{service} in {result['location']}: {result.get('error', 'Unknown error')}")
    
    # Location search
    for result in results["location_features"]["search"]:
        total_tests += 1
        if result["status"] == "SUCCESS":
            successful_tests += 1
            if not result.get("found", False):
                issues_found.append(f"Location search for {result['location']}: No suggestions found")
        else:
            issues_found.append(f"Location search for {result['location']}: {result.get('error', 'Unknown error')}")
    
    # Crop search
    for result in results["crop_search"]:
        total_tests += 1
        if result["status"] == "SUCCESS":
            successful_tests += 1
            if not result.get("has_analysis", False):
                issues_found.append(f"Crop search for {result['crop']}: No analysis returned")
        else:
            issues_found.append(f"Crop search for {result['crop']}: {result.get('error', 'Unknown error')}")
    
    # AI Chatbot
    for result in results["ai_chatbot"]:
        total_tests += 1
        if result["status"] == "SUCCESS":
            successful_tests += 1
            if not result.get("has_response", False):
                issues_found.append(f"AI Chatbot query: No response returned")
        else:
            issues_found.append(f"AI Chatbot query: {result.get('error', 'Unknown error')}")
    
    success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"Total Tests: {total_tests}")
    print(f"Successful Tests: {successful_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"Issues Found: {len(issues_found)}")
    
    if issues_found:
        print("\nISSUES IDENTIFIED:")
        for i, issue in enumerate(issues_found, 1):
            print(f"{i}. {issue}")
    else:
        print("\nSUCCESS: NO ISSUES FOUND - All features working perfectly!")
    
    # Performance Analysis
    print("\n7. PERFORMANCE ANALYSIS")
    print("-" * 30)
    
    all_response_times = []
    for service_results in results["services"].values():
        for result in service_results:
            if "response_time" in result:
                all_response_times.append(result["response_time"])
    
    if all_response_times:
        avg_response_time = sum(all_response_times) / len(all_response_times)
        max_response_time = max(all_response_times)
        min_response_time = min(all_response_times)
        
        print(f"Average Response Time: {avg_response_time:.2f}s")
        print(f"Fastest Response: {min_response_time:.2f}s")
        print(f"Slowest Response: {max_response_time:.2f}s")
        
        if avg_response_time < 2.0:
            print("SUCCESS: EXCELLENT performance!")
        elif avg_response_time < 5.0:
            print("WARNING: GOOD performance")
        else:
            print("ERROR: SLOW performance - needs optimization")
    
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    
    return results

if __name__ == "__main__":
    analyze_website()
