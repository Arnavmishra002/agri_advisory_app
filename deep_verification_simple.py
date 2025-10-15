#!/usr/bin/env python3
"""
DEEP COMPREHENSIVE SERVICE VERIFICATION
Using All Available Capabilities
"""

import requests
import json
import time
import re
from datetime import datetime
import sys

class DeepServiceVerifier:
    def __init__(self):
        self.base_url = "http://127.0.0.1:8000"
        self.test_results = {}
        self.start_time = datetime.now()
        
    def log_result(self, service, test_name, status, details=""):
        """Log test results"""
        if service not in self.test_results:
            self.test_results[service] = {}
        self.test_results[service][test_name] = {
            'status': status,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
    
    def test_ai_assistant_deep(self):
        """Deep test of AI Assistant with multiple scenarios"""
        print("\n" + "="*80)
        print("AI ASSISTANT DEEP VERIFICATION")
        print("="*80)
        
        # Test scenarios
        scenarios = [
            {
                "name": "General Greeting",
                "query": "hello",
                "expected_source": ["general_ai", "open_source_ai"],
                "expected_indicators": ["Hello", "I'm", "Krishimitra"]
            },
            {
                "name": "Farming Query",
                "query": "What crops should I grow in Raebareli?",
                "expected_source": ["real_time_government_apis"],
                "expected_indicators": ["crop", "Raebareli", "recommendation"]
            },
            {
                "name": "Technical Query",
                "query": "What is artificial intelligence?",
                "expected_source": ["open_source_ai", "general_ai"],
                "expected_indicators": ["AI", "technology", "computer"]
            },
            {
                "name": "Weather Query",
                "query": "What's the weather in Raebareli?",
                "expected_source": ["real_time_government_apis"],
                "expected_indicators": ["weather", "Raebareli", "temperature"]
            },
            {
                "name": "Casual Query",
                "query": "Tell me a joke",
                "expected_source": ["general_ai", "open_source_ai"],
                "expected_indicators": ["joke", "funny", "humor"]
            },
            {
                "name": "Identity Query",
                "query": "Who are you?",
                "expected_source": ["general_ai", "open_source_ai"],
                "expected_indicators": ["Krishimitra", "AI", "assistant"]
            }
        ]
        
        for scenario in scenarios:
            print(f"\nTesting: {scenario['name']}")
            print(f"   Query: {scenario['query']}")
            
            try:
                response = requests.post(
                    f"{self.base_url}/api/chatbot/",
                    json={"query": scenario['query'], "session_id": "deep_test"},
                    headers={'Content-Type': 'application/json'},
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get('response', '')
                    data_source = data.get('data_source', '')
                    
                    # Check data source routing
                    source_correct = any(expected in data_source for expected in scenario['expected_source'])
                    
                    # Check response content
                    content_correct = any(indicator.lower() in response_text.lower() for indicator in scenario['expected_indicators'])
                    
                    # Check response quality
                    response_length = len(response_text)
                    quality_good = response_length > 50
                    
                    if source_correct and content_correct and quality_good:
                        print(f"   PASSED - Source: {data_source}, Length: {response_length}")
                        self.log_result("AI Assistant", scenario['name'], "PASSED", 
                                      f"Source: {data_source}, Length: {response_length}")
                    else:
                        print(f"   PARTIAL - Source: {data_source}, Content: {content_correct}, Quality: {quality_good}")
                        self.log_result("AI Assistant", scenario['name'], "PARTIAL", 
                                      f"Source: {data_source}, Content: {content_correct}, Quality: {quality_good}")
                    
                    # Show response preview
                    preview = response_text[:150].replace('\n', ' ')
                    print(f"   Preview: {preview}...")
                    
                else:
                    print(f"   FAILED - Status: {response.status_code}")
                    self.log_result("AI Assistant", scenario['name'], "FAILED", f"Status: {response.status_code}")
                    
            except Exception as e:
                print(f"   ERROR: {str(e)}")
                self.log_result("AI Assistant", scenario['name'], "ERROR", str(e))
    
    def test_crop_recommendations_deep(self):
        """Deep test of crop recommendations"""
        print("\n" + "="*80)
        print("CROP RECOMMENDATIONS DEEP VERIFICATION")
        print("="*80)
        
        locations = [
            {"name": "Raebareli", "lat": 26.2, "lon": 81.2},
            {"name": "Delhi", "lat": 28.7, "lon": 77.1},
            {"name": "Mumbai", "lat": 19.1, "lon": 72.9}
        ]
        
        for location in locations:
            print(f"\nTesting Location: {location['name']}")
            
            try:
                response = requests.get(
                    f"{self.base_url}/api/realtime-gov/crop_recommendations/",
                    params={
                        "location": location['name'],
                        "latitude": location['lat'],
                        "longitude": location['lon']
                    },
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check required fields
                    required_fields = ['location', 'top_4_recommendations', 'timestamp']
                    fields_present = all(field in data for field in required_fields)
                    
                    # Check crop recommendations
                    recommendations = data.get('top_4_recommendations', [])
                    has_recommendations = len(recommendations) > 0
                    
                    # Check individual crop data
                    crop_data_complete = True
                    if recommendations:
                        for crop in recommendations[:2]:  # Check first 2 crops
                            crop_fields = ['name', 'msp', 'yield', 'profit', 'profit_percentage']
                            if not all(field in crop for field in crop_fields):
                                crop_data_complete = False
                                break
                    
                    if fields_present and has_recommendations and crop_data_complete:
                        print(f"   PASSED - {len(recommendations)} crops recommended")
                        self.log_result("Crop Recommendations", location['name'], "PASSED", 
                                      f"{len(recommendations)} crops, complete data")
                        
                        # Show sample crop
                        if recommendations:
                            sample_crop = recommendations[0]
                            print(f"   Sample: {sample_crop.get('name', 'Unknown')} - {sample_crop.get('profit_percentage', 'N/A')}% profit")
                    else:
                        print(f"   PARTIAL - Fields: {fields_present}, Crops: {has_recommendations}, Complete: {crop_data_complete}")
                        self.log_result("Crop Recommendations", location['name'], "PARTIAL", 
                                      f"Fields: {fields_present}, Crops: {has_recommendations}")
                        
                else:
                    print(f"   FAILED - Status: {response.status_code}")
                    self.log_result("Crop Recommendations", location['name'], "FAILED", f"Status: {response.status_code}")
                    
            except Exception as e:
                print(f"   ERROR: {str(e)}")
                self.log_result("Crop Recommendations", location['name'], "ERROR", str(e))
    
    def test_government_schemes_deep(self):
        """Deep test of government schemes"""
        print("\n" + "="*80)
        print("GOVERNMENT SCHEMES DEEP VERIFICATION")
        print("="*80)
        
        try:
            response = requests.get(
                f"{self.base_url}/api/realtime-gov/government_schemes/",
                params={"location": "Raebareli", "latitude": 26.2, "longitude": 81.2},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check scheme structure
                schemes = data.get('schemes', [])
                central_schemes = data.get('central_schemes', [])
                state_schemes = data.get('state_schemes', [])
                
                total_schemes = len(schemes)
                has_central = len(central_schemes) > 0
                has_state = len(state_schemes) > 0
                
                # Check scheme data quality
                scheme_data_quality = True
                if schemes:
                    for scheme in schemes[:3]:  # Check first 3 schemes
                        required_fields = ['name', 'description']
                        if not all(field in scheme for field in required_fields):
                            scheme_data_quality = False
                            break
                
                if total_schemes > 0 and scheme_data_quality:
                    print(f"   PASSED - {total_schemes} schemes found")
                    print(f"   Central: {len(central_schemes)}, State: {len(state_schemes)}")
                    self.log_result("Government Schemes", "Scheme Count", "PASSED", 
                                  f"{total_schemes} total, {len(central_schemes)} central, {len(state_schemes)} state")
                    
                    # Show sample schemes
                    if schemes:
                        print(f"   Sample: {schemes[0].get('name', 'Unknown')}")
                else:
                    print(f"   PARTIAL - Schemes: {total_schemes}, Quality: {scheme_data_quality}")
                    self.log_result("Government Schemes", "Scheme Count", "PARTIAL", 
                                  f"{total_schemes} schemes, quality: {scheme_data_quality}")
                    
            else:
                print(f"   FAILED - Status: {response.status_code}")
                self.log_result("Government Schemes", "API Response", "FAILED", f"Status: {response.status_code}")
                
        except Exception as e:
            print(f"   ERROR: {str(e)}")
            self.log_result("Government Schemes", "API Response", "ERROR", str(e))
    
    def test_weather_data_deep(self):
        """Deep test of weather data"""
        print("\n" + "="*80)
        print("WEATHER DATA DEEP VERIFICATION")
        print("="*80)
        
        try:
            response = requests.get(
                f"{self.base_url}/api/realtime-gov/weather/",
                params={"location": "Raebareli", "latitude": 26.2, "longitude": 81.2},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check weather data structure
                weather_data = data.get('weather_data', {})
                has_temperature = 'temperature' in weather_data
                has_humidity = 'humidity' in weather_data
                has_wind = 'wind_speed' in weather_data
                has_location = data.get('location') == 'Raebareli'
                
                # Check data quality
                temp_value = weather_data.get('temperature', 0)
                humidity_value = weather_data.get('humidity', 0)
                wind_value = weather_data.get('wind_speed', 0)
                
                temp_realistic = 0 <= temp_value <= 50
                humidity_realistic = 0 <= humidity_value <= 100
                wind_realistic = 0 <= wind_value <= 100
                
                if has_temperature and has_humidity and has_wind and has_location:
                    print(f"   PASSED - Complete weather data for Raebareli")
                    print(f"   Temp: {temp_value}C, Humidity: {humidity_value}%, Wind: {wind_value} km/h")
                    self.log_result("Weather Data", "Data Completeness", "PASSED", 
                                  f"Temp: {temp_value}C, Humidity: {humidity_value}%")
                else:
                    print(f"   PARTIAL - Temp: {has_temperature}, Humidity: {has_humidity}, Wind: {has_wind}")
                    self.log_result("Weather Data", "Data Completeness", "PARTIAL", 
                                  f"Temp: {has_temperature}, Humidity: {has_humidity}, Wind: {has_wind}")
                    
            else:
                print(f"   FAILED - Status: {response.status_code}")
                self.log_result("Weather Data", "API Response", "FAILED", f"Status: {response.status_code}")
                
        except Exception as e:
            print(f"   ERROR: {str(e)}")
            self.log_result("Weather Data", "API Response", "ERROR", str(e))
    
    def test_market_prices_deep(self):
        """Deep test of market prices"""
        print("\n" + "="*80)
        print("MARKET PRICES DEEP VERIFICATION")
        print("="*80)
        
        try:
            response = requests.get(
                f"{self.base_url}/api/realtime-gov/market_prices/",
                params={"location": "Raebareli", "latitude": 26.2, "longitude": 81.2},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check market data structure
                market_data = data.get('market_data', {})
                crops = market_data.get('crops', [])
                
                has_crops = len(crops) > 0
                crop_data_complete = True
                
                if crops:
                    for crop in crops[:3]:  # Check first 3 crops
                        required_fields = ['name', 'current_price', 'msp', 'profit_margin']
                        if not all(field in crop for field in required_fields):
                            crop_data_complete = False
                            break
                
                if has_crops and crop_data_complete:
                    print(f"   PASSED - {len(crops)} crops with complete price data")
                    self.log_result("Market Prices", "Price Data", "PASSED", f"{len(crops)} crops")
                    
                    # Show sample crop prices
                    if crops:
                        sample_crop = crops[0]
                        print(f"   Sample: {sample_crop.get('name', 'Unknown')} - Rs {sample_crop.get('current_price', 'N/A')}/quintal")
                else:
                    print(f"   PARTIAL - Crops: {has_crops}, Complete: {crop_data_complete}")
                    self.log_result("Market Prices", "Price Data", "PARTIAL", 
                                  f"Crops: {has_crops}, Complete: {crop_data_complete}")
                    
            else:
                print(f"   FAILED - Status: {response.status_code}")
                self.log_result("Market Prices", "API Response", "FAILED", f"Status: {response.status_code}")
                
        except Exception as e:
            print(f"   ERROR: {str(e)}")
            self.log_result("Market Prices", "API Response", "ERROR", str(e))
    
    def test_location_services_deep(self):
        """Deep test of location services"""
        print("\n" + "="*80)
        print("LOCATION SERVICES DEEP VERIFICATION")
        print("="*80)
        
        # Test location search
        print("\nTesting Location Search:")
        search_queries = ["Raebareli", "Delhi", "Mumbai", "Bangalore"]
        
        for query in search_queries:
            try:
                response = requests.get(
                    f"{self.base_url}/api/locations/search/",
                    params={"q": query},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    suggestions = data.get('suggestions', [])
                    
                    if suggestions:
                        print(f"   PASSED {query}: {len(suggestions)} suggestions found")
                        self.log_result("Location Search", query, "PASSED", f"{len(suggestions)} suggestions")
                    else:
                        print(f"   PARTIAL {query}: No suggestions")
                        self.log_result("Location Search", query, "PARTIAL", "No suggestions")
                        
                else:
                    print(f"   FAILED {query}: Status {response.status_code}")
                    self.log_result("Location Search", query, "FAILED", f"Status: {response.status_code}")
                    
            except Exception as e:
                print(f"   ERROR {query}: {str(e)}")
                self.log_result("Location Search", query, "ERROR", str(e))
        
        # Test reverse geocoding
        print("\nTesting Reverse Geocoding:")
        coordinates = [
            {"lat": 26.2, "lon": 81.2, "expected": "Raebareli"},
            {"lat": 28.7, "lon": 77.1, "expected": "Delhi"},
            {"lat": 19.1, "lon": 72.9, "expected": "Mumbai"}
        ]
        
        for coord in coordinates:
            try:
                response = requests.get(
                    f"{self.base_url}/api/locations/reverse/",
                    params={"lat": coord['lat'], "lon": coord['lon']},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    location = data.get('location', '')
                    
                    if coord['expected'].lower() in location.lower():
                        print(f"   PASSED ({coord['lat']}, {coord['lon']}): {location}")
                        self.log_result("Reverse Geocoding", f"({coord['lat']}, {coord['lon']})", "PASSED", location)
                    else:
                        print(f"   PARTIAL ({coord['lat']}, {coord['lon']}): {location} (expected {coord['expected']})")
                        self.log_result("Reverse Geocoding", f"({coord['lat']}, {coord['lon']})", "PARTIAL", f"{location} vs {coord['expected']}")
                        
                else:
                    print(f"   FAILED ({coord['lat']}, {coord['lon']}): Status {response.status_code}")
                    self.log_result("Reverse Geocoding", f"({coord['lat']}, {coord['lon']})", "FAILED", f"Status: {response.status_code}")
                    
            except Exception as e:
                print(f"   ERROR ({coord['lat']}, {coord['lon']}): {str(e)}")
                self.log_result("Reverse Geocoding", f"({coord['lat']}, {coord['lon']})", "ERROR", str(e))
    
    def test_pest_detection_deep(self):
        """Deep test of pest detection"""
        print("\n" + "="*80)
        print("PEST DETECTION DEEP VERIFICATION")
        print("="*80)
        
        crops = ["wheat", "rice", "maize", "cotton"]
        
        for crop in crops:
            print(f"\nTesting Crop: {crop}")
            
            try:
                response = requests.post(
                    f"{self.base_url}/api/realtime-gov/pest_detection/",
                    json={
                        "crop": crop,
                        "location": "Raebareli",
                        "latitude": 26.2,
                        "longitude": 81.2,
                        "symptoms": ""
                    },
                    headers={'Content-Type': 'application/json'},
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    pest_analysis = data.get('pest_analysis', {})
                    
                    # Check pest data structure
                    pests = pest_analysis.get('pests', [])
                    prevention_tips = pest_analysis.get('prevention_tips', [])
                    treatment_recommendations = pest_analysis.get('treatment_recommendations', [])
                    
                    has_pests = len(pests) > 0
                    has_prevention = len(prevention_tips) > 0
                    has_treatment = len(treatment_recommendations) > 0
                    
                    if has_pests and has_prevention and has_treatment:
                        print(f"   PASSED - Complete pest data for {crop}")
                        print(f"   Pests: {len(pests)}, Prevention: {len(prevention_tips)}, Treatment: {len(treatment_recommendations)}")
                        self.log_result("Pest Detection", crop, "PASSED", 
                                      f"Pests: {len(pests)}, Prevention: {len(prevention_tips)}")
                    else:
                        print(f"   PARTIAL - Pests: {has_pests}, Prevention: {has_prevention}, Treatment: {has_treatment}")
                        self.log_result("Pest Detection", crop, "PARTIAL", 
                                      f"Pests: {has_pests}, Prevention: {has_prevention}, Treatment: {has_treatment}")
                        
                else:
                    print(f"   FAILED - Status: {response.status_code}")
                    self.log_result("Pest Detection", crop, "FAILED", f"Status: {response.status_code}")
                    
            except Exception as e:
                print(f"   ERROR: {str(e)}")
                self.log_result("Pest Detection", crop, "ERROR", str(e))
    
    def test_frontend_deep(self):
        """Deep test of frontend functionality"""
        print("\n" + "="*80)
        print("FRONTEND DEEP VERIFICATION")
        print("="*80)
        
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            
            if response.status_code == 200:
                html_content = response.text
                
                # Check critical frontend elements
                frontend_checks = [
                    ("HTML Structure", "<!DOCTYPE html>"),
                    ("Bootstrap CSS", "bootstrap"),
                    ("JavaScript Functions", "function sendMessage"),
                    ("AI Chat Interface", "chatMessages"),
                    ("Location Search", "locationSearchInput"),
                    ("Service Cards", "service-card"),
                    ("Crop Data Container", "cropsData"),
                    ("Scheme Data Container", "schemesData"),
                    ("Weather Data Container", "weatherData"),
                    ("Market Prices Container", "pricesData"),
                    ("Pest Control Container", "pestData"),
                    ("Cache Busting", "cache-bust"),
                    ("Notification System", "showNotification"),
                    ("Location Update", "selectLocation"),
                    ("Service Loading", "loadServiceData")
                ]
                
                passed_checks = 0
                total_checks = len(frontend_checks)
                
                for check_name, check_pattern in frontend_checks:
                    if check_pattern in html_content:
                        print(f"   PASSED {check_name}: Found")
                        passed_checks += 1
                    else:
                        print(f"   FAILED {check_name}: Missing")
                
                # Check page metrics
                page_size = len(html_content)
                has_meta_tags = "<meta" in html_content
                has_css = "<style>" in html_content or "stylesheet" in html_content
                has_js = "<script>" in html_content
                
                print(f"\nFrontend Metrics:")
                print(f"   Page Size: {page_size:,} characters")
                print(f"   Meta Tags: {has_meta_tags}")
                print(f"   CSS: {has_css}")
                print(f"   JavaScript: {has_js}")
                
                if passed_checks >= total_checks * 0.8:  # 80% pass rate
                    print(f"\n   FRONTEND PASSED - {passed_checks}/{total_checks} checks passed")
                    self.log_result("Frontend", "Overall", "PASSED", f"{passed_checks}/{total_checks} checks")
                else:
                    print(f"\n   FRONTEND PARTIAL - {passed_checks}/{total_checks} checks passed")
                    self.log_result("Frontend", "Overall", "PARTIAL", f"{passed_checks}/{total_checks} checks")
                    
            else:
                print(f"   Frontend not accessible - Status: {response.status_code}")
                self.log_result("Frontend", "Accessibility", "FAILED", f"Status: {response.status_code}")
                
        except Exception as e:
            print(f"   Frontend test error: {str(e)}")
            self.log_result("Frontend", "Accessibility", "ERROR", str(e))
    
    def generate_comprehensive_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*80)
        print("COMPREHENSIVE TEST REPORT")
        print("="*80)
        
        total_tests = 0
        passed_tests = 0
        partial_tests = 0
        failed_tests = 0
        
        for service, tests in self.test_results.items():
            print(f"\n{service.upper()}:")
            for test_name, result in tests.items():
                total_tests += 1
                status = result['status']
                details = result['details']
                
                if status == "PASSED":
                    passed_tests += 1
                    print(f"   PASSED {test_name}: {details}")
                elif status == "PARTIAL":
                    partial_tests += 1
                    print(f"   PARTIAL {test_name}: {details}")
                else:
                    failed_tests += 1
                    print(f"   FAILED {test_name}: {details}")
        
        # Calculate metrics
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        partial_rate = (partial_tests / total_tests * 100) if total_tests > 0 else 0
        failure_rate = (failed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\nOVERALL METRICS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   PASSED: {passed_tests} ({success_rate:.1f}%)")
        print(f"   PARTIAL: {partial_tests} ({partial_rate:.1f}%)")
        print(f"   FAILED: {failed_tests} ({failure_rate:.1f}%)")
        
        # Overall assessment
        if success_rate >= 80:
            print(f"\nEXCELLENT: System is highly functional!")
        elif success_rate >= 60:
            print(f"\nGOOD: System is mostly functional with minor issues")
        elif success_rate >= 40:
            print(f"\nFAIR: System needs improvements")
        else:
            print(f"\nPOOR: System requires significant fixes")
        
        # Test duration
        duration = datetime.now() - self.start_time
        print(f"\nTest Duration: {duration.total_seconds():.1f} seconds")
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'partial_tests': partial_tests,
            'failed_tests': failed_tests,
            'success_rate': success_rate
        }
    
    def run_all_tests(self):
        """Run all deep verification tests"""
        print("STARTING DEEP COMPREHENSIVE VERIFICATION")
        print("Using All Available Capabilities")
        print(f"Target: {self.base_url}")
        print(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run all test suites
        self.test_ai_assistant_deep()
        self.test_crop_recommendations_deep()
        self.test_government_schemes_deep()
        self.test_weather_data_deep()
        self.test_market_prices_deep()
        self.test_location_services_deep()
        self.test_pest_detection_deep()
        self.test_frontend_deep()
        
        # Generate comprehensive report
        return self.generate_comprehensive_report()

if __name__ == "__main__":
    verifier = DeepServiceVerifier()
    results = verifier.run_all_tests()
    
    print("\n" + "="*80)
    print("DEEP VERIFICATION COMPLETE")
    print("="*80)
    
    if results['success_rate'] >= 80:
        print("SUCCESS: Your Krishimitra AI system is highly functional!")
        print("All major services are working excellently!")
    else:
        print(f"ATTENTION: {results['failed_tests']} tests failed, {results['partial_tests']} partial")
        print("Some services may need attention")
    
    print("\nNext Steps:")
    print("1. Review any failed or partial tests above")
    print("2. Test the system in your browser at http://127.0.0.1:8000/")
    print("3. Verify all features work as expected")
    print("4. Report any issues found during manual testing")
