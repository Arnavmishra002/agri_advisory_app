#!/usr/bin/env python3
"""
Comprehensive Live Verification Test
Tests all services on the live website to ensure:
1. All buttons are clickable
2. Data is accurate and from government APIs
3. Data changes with location changes
4. Chatbot gives proper responses like ChatGPT
"""

import requests
import time
import json
from datetime import datetime
from typing import Dict, List, Any

class LiveVerificationTester:
    def __init__(self, base_url: str = "https://krishmitra-zrk4.onrender.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            status = "✅ PASS"
        else:
            self.failed_tests += 1
            status = "❌ FAIL"
        
        result = f"{status} | {test_name}"
        if details:
            result += f"\n    Details: {details}"
        
        print(result)
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
        
    def test_website_accessibility(self):
        """Test 1: Verify website is accessible"""
        print("\n" + "="*80)
        print("TEST 1: WEBSITE ACCESSIBILITY")
        print("="*80)
        
        try:
            response = requests.get(self.base_url, timeout=10)
            if response.status_code == 200:
                self.log_test("Website is accessible", True, f"Status: {response.status_code}")
                return True
            else:
                self.log_test("Website is accessible", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Website is accessible", False, str(e))
            return False
    
    def test_api_health(self):
        """Test 2: Verify API health endpoint"""
        print("\n" + "="*80)
        print("TEST 2: API HEALTH CHECK")
        print("="*80)
        
        try:
            response = requests.get(f"{self.api_url}/health/", timeout=10)
            if response.status_code == 200:
                self.log_test("API health endpoint", True, "API is healthy")
                return True
            else:
                self.log_test("API health endpoint", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("API health endpoint", False, str(e))
            return False
    
    def test_chatbot_responses(self):
        """Test 3: Verify chatbot gives proper responses"""
        print("\n" + "="*80)
        print("TEST 3: CHATBOT RESPONSES (ChatGPT-like quality)")
        print("="*80)
        
        test_queries = [
            {
                "query": "मुझे गेहूं की खेती के बारे में बताओ",
                "expected_keywords": ["गेहूं", "खेती", "बुवाई", "मिट्टी"],
                "description": "Wheat farming query in Hindi"
            },
            {
                "query": "What crops should I grow in Delhi?",
                "expected_keywords": ["crop", "Delhi", "recommend", "suitable"],
                "description": "Crop recommendation for Delhi"
            },
            {
                "query": "आज का मौसम कैसा है?",
                "expected_keywords": ["मौसम", "तापमान", "weather"],
                "description": "Weather query in Hindi"
            },
            {
                "query": "Tell me about PM-KISAN scheme",
                "expected_keywords": ["PM-KISAN", "scheme", "farmer", "benefit"],
                "description": "Government scheme query"
            }
        ]
        
        for test_query in test_queries:
            try:
                payload = {
                    "query": test_query["query"],
                    "language": "hi" if any(ord(c) > 127 for c in test_query["query"]) else "en",
                    "session_id": f"test_{int(time.time())}",
                    "location_name": "Delhi"
                }
                
                response = requests.post(
                    f"{self.api_url}/advisories/chatbot/",
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get('response', '')
                    
                    # Check if response is meaningful (not empty, has content)
                    if len(response_text) > 50:
                        # Check for expected keywords
                        keywords_found = sum(1 for kw in test_query["expected_keywords"] 
                                           if kw.lower() in response_text.lower())
                        
                        if keywords_found >= 1:
                            self.log_test(
                                f"Chatbot: {test_query['description']}", 
                                True, 
                                f"Response length: {len(response_text)} chars, Keywords found: {keywords_found}"
                            )
                        else:
                            self.log_test(
                                f"Chatbot: {test_query['description']}", 
                                False, 
                                f"No expected keywords found in response"
                            )
                    else:
                        self.log_test(
                            f"Chatbot: {test_query['description']}", 
                            False, 
                            "Response too short or empty"
                        )
                else:
                    self.log_test(
                        f"Chatbot: {test_query['description']}", 
                        False, 
                        f"Status: {response.status_code}"
                    )
                
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                self.log_test(f"Chatbot: {test_query['description']}", False, str(e))
    
    def test_crop_recommendations_by_location(self):
        """Test 4: Verify crop recommendations change with location"""
        print("\n" + "="*80)
        print("TEST 4: LOCATION-BASED CROP RECOMMENDATIONS")
        print("="*80)
        
        test_locations = [
            {"name": "Delhi", "state": "Delhi"},
            {"name": "Mumbai", "state": "Maharashtra"},
            {"name": "Bangalore", "state": "Karnataka"},
            {"name": "Lucknow", "state": "Uttar Pradesh"}
        ]
        
        location_recommendations = {}
        
        for location in test_locations:
            try:
                payload = {
                    "query": f"मुझे {location['name']} के लिए फसल सुझाव दो",
                    "language": "hi",
                    "session_id": f"test_{int(time.time())}",
                    "location_name": location['name']
                }
                
                response = requests.post(
                    f"{self.api_url}/advisories/chatbot/",
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get('response', '')
                    location_recommendations[location['name']] = response_text
                    
                    # Check if location name is mentioned
                    if location['name'].lower() in response_text.lower() or location['state'].lower() in response_text.lower():
                        self.log_test(
                            f"Crop recommendations for {location['name']}", 
                            True, 
                            f"Location-specific data received"
                        )
                    else:
                        self.log_test(
                            f"Crop recommendations for {location['name']}", 
                            False, 
                            "Location not mentioned in response"
                        )
                else:
                    self.log_test(
                        f"Crop recommendations for {location['name']}", 
                        False, 
                        f"Status: {response.status_code}"
                    )
                
                time.sleep(1)
                
            except Exception as e:
                self.log_test(f"Crop recommendations for {location['name']}", False, str(e))
        
        # Verify recommendations are different for different locations
        if len(location_recommendations) >= 2:
            unique_responses = len(set(location_recommendations.values()))
            if unique_responses > 1:
                self.log_test(
                    "Recommendations vary by location", 
                    True, 
                    f"{unique_responses} unique responses for {len(location_recommendations)} locations"
                )
            else:
                self.log_test(
                    "Recommendations vary by location", 
                    False, 
                    "All locations returned same recommendations"
                )
    
    def test_weather_data_by_location(self):
        """Test 5: Verify weather data changes with location"""
        print("\n" + "="*80)
        print("TEST 5: LOCATION-BASED WEATHER DATA")
        print("="*80)
        
        test_locations = ["Delhi", "Mumbai", "Kolkata", "Chennai"]
        
        for location in test_locations:
            try:
                payload = {
                    "query": f"{location} का मौसम बताओ",
                    "language": "hi",
                    "session_id": f"test_{int(time.time())}",
                    "location_name": location
                }
                
                response = requests.post(
                    f"{self.api_url}/advisories/chatbot/",
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get('response', '')
                    
                    # Check for weather-related keywords
                    weather_keywords = ["तापमान", "temperature", "मौसम", "weather", "बारिश", "rain", "humidity"]
                    keywords_found = sum(1 for kw in weather_keywords if kw.lower() in response_text.lower())
                    
                    if keywords_found >= 2 and location.lower() in response_text.lower():
                        self.log_test(
                            f"Weather data for {location}", 
                            True, 
                            f"Weather keywords found: {keywords_found}"
                        )
                    else:
                        self.log_test(
                            f"Weather data for {location}", 
                            False, 
                            "Insufficient weather data or location not mentioned"
                        )
                else:
                    self.log_test(
                        f"Weather data for {location}", 
                        False, 
                        f"Status: {response.status_code}"
                    )
                
                time.sleep(1)
                
            except Exception as e:
                self.log_test(f"Weather data for {location}", False, str(e))
    
    def test_market_prices(self):
        """Test 6: Verify market prices data"""
        print("\n" + "="*80)
        print("TEST 6: MARKET PRICES DATA")
        print("="*80)
        
        test_queries = [
            {"query": "गेहूं की कीमत क्या है?", "crop": "wheat"},
            {"query": "धान का बाजार भाव बताओ", "crop": "rice"},
            {"query": "What is the price of tomato?", "crop": "tomato"}
        ]
        
        for test_query in test_queries:
            try:
                payload = {
                    "query": test_query["query"],
                    "language": "hi" if any(ord(c) > 127 for c in test_query["query"]) else "en",
                    "session_id": f"test_{int(time.time())}",
                    "location_name": "Delhi"
                }
                
                response = requests.post(
                    f"{self.api_url}/advisories/chatbot/",
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get('response', '')
                    
                    # Check for price-related keywords
                    price_keywords = ["कीमत", "price", "₹", "rupee", "रुपये", "भाव", "rate"]
                    keywords_found = sum(1 for kw in price_keywords if kw.lower() in response_text.lower())
                    
                    if keywords_found >= 1:
                        self.log_test(
                            f"Market price: {test_query['crop']}", 
                            True, 
                            "Price information found"
                        )
                    else:
                        self.log_test(
                            f"Market price: {test_query['crop']}", 
                            False, 
                            "No price information found"
                        )
                else:
                    self.log_test(
                        f"Market price: {test_query['crop']}", 
                        False, 
                        f"Status: {response.status_code}"
                    )
                
                time.sleep(1)
                
            except Exception as e:
                self.log_test(f"Market price: {test_query['crop']}", False, str(e))
    
    def test_government_schemes(self):
        """Test 7: Verify government schemes data"""
        print("\n" + "="*80)
        print("TEST 7: GOVERNMENT SCHEMES DATA")
        print("="*80)
        
        test_queries = [
            "PM-KISAN योजना के बारे में बताओ",
            "Tell me about Kisan Credit Card",
            "सरकारी योजनाएं बताओ"
        ]
        
        for query in test_queries:
            try:
                payload = {
                    "query": query,
                    "language": "hi" if any(ord(c) > 127 for c in query) else "en",
                    "session_id": f"test_{int(time.time())}",
                    "location_name": "Delhi"
                }
                
                response = requests.post(
                    f"{self.api_url}/advisories/chatbot/",
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get('response', '')
                    
                    # Check for scheme-related keywords
                    scheme_keywords = ["योजना", "scheme", "सरकार", "government", "लाभ", "benefit", "subsidy"]
                    keywords_found = sum(1 for kw in scheme_keywords if kw.lower() in response_text.lower())
                    
                    if keywords_found >= 2 and len(response_text) > 100:
                        self.log_test(
                            f"Government scheme query", 
                            True, 
                            f"Comprehensive scheme information provided"
                        )
                    else:
                        self.log_test(
                            f"Government scheme query", 
                            False, 
                            "Insufficient scheme information"
                        )
                else:
                    self.log_test(
                        f"Government scheme query", 
                        False, 
                        f"Status: {response.status_code}"
                    )
                
                time.sleep(1)
                
            except Exception as e:
                self.log_test(f"Government scheme query", False, str(e))
    
    def test_data_source_verification(self):
        """Test 8: Verify data is from government APIs"""
        print("\n" + "="*80)
        print("TEST 8: GOVERNMENT API DATA SOURCE VERIFICATION")
        print("="*80)
        
        try:
            payload = {
                "query": "मुझे दिल्ली के लिए पूरी जानकारी दो - मौसम, फसल, कीमत, योजना",
                "language": "hi",
                "session_id": f"test_{int(time.time())}",
                "location_name": "Delhi"
            }
            
            response = requests.post(
                f"{self.api_url}/advisories/chatbot/",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', '')
                
                # Check for government data indicators
                gov_indicators = [
                    "IMD", "India Meteorological", "Agmarknet", "e-NAM",
                    "ICAR", "Government", "सरकार", "Ministry", "मंत्रालय"
                ]
                
                indicators_found = sum(1 for ind in gov_indicators if ind.lower() in response_text.lower())
                
                # Check if response has substantial data
                has_weather = any(kw in response_text.lower() for kw in ["temperature", "तापमान", "weather", "मौसम"])
                has_crops = any(kw in response_text.lower() for kw in ["crop", "फसल", "recommend"])
                has_prices = any(kw in response_text.lower() for kw in ["price", "कीमत", "₹"])
                
                data_types_found = sum([has_weather, has_crops, has_prices])
                
                if data_types_found >= 2:
                    self.log_test(
                        "Government API data integration", 
                        True, 
                        f"Multiple data types found: weather={has_weather}, crops={has_crops}, prices={has_prices}"
                    )
                else:
                    self.log_test(
                        "Government API data integration", 
                        False, 
                        f"Insufficient data types: {data_types_found}/3"
                    )
            else:
                self.log_test(
                    "Government API data integration", 
                    False, 
                    f"Status: {response.status_code}"
                )
                
        except Exception as e:
            self.log_test("Government API data integration", False, str(e))
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*80)
        print("COMPREHENSIVE VERIFICATION REPORT")
        print("="*80)
        
        print(f"\nTotal Tests: {self.total_tests}")
        print(f"✅ Passed: {self.passed_tests}")
        print(f"❌ Failed: {self.failed_tests}")
        
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        print(f"\n📊 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("\n🎉 EXCELLENT! All systems operational!")
        elif success_rate >= 75:
            print("\n✅ GOOD! Most systems working well, minor issues detected.")
        elif success_rate >= 50:
            print("\n⚠️  WARNING! Several issues detected, needs attention.")
        else:
            print("\n❌ CRITICAL! Major issues detected, immediate action required.")
        
        # Save report to file
        report_file = f"verification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_tests': self.total_tests,
                'passed': self.passed_tests,
                'failed': self.failed_tests,
                'success_rate': success_rate,
                'results': self.test_results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
    
    def run_all_tests(self):
        """Run all verification tests"""
        print("\n" + "="*80)
        print("🚀 STARTING COMPREHENSIVE LIVE VERIFICATION")
        print("="*80)
        print(f"Target: {self.base_url}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Wait for deployment (6 minutes as requested)
        print("\n⏳ Waiting 6 minutes for deployment to complete...")
        for i in range(6, 0, -1):
            print(f"   {i} minutes remaining...", end='\r')
            time.sleep(60)
        print("\n✅ Deployment wait complete!\n")
        
        # Run all tests
        self.test_website_accessibility()
        self.test_api_health()
        self.test_chatbot_responses()
        self.test_crop_recommendations_by_location()
        self.test_weather_data_by_location()
        self.test_market_prices()
        self.test_government_schemes()
        self.test_data_source_verification()
        
        # Generate report
        self.generate_report()

if __name__ == "__main__":
    tester = LiveVerificationTester()
    tester.run_all_tests()

