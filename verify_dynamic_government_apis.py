#!/usr/bin/env python3
"""
Comprehensive test to verify all services use government APIs
and data changes dynamically based on location
"""

import requests
import json
import time
from datetime import datetime
from colorama import init, Fore, Style

init(autoreset=True)

BASE_URL = "http://localhost:8000"
RENDER_URL = "https://krishmitra-zrk4.onrender.com"

class DynamicAPIVerifier:
    def __init__(self, base_url):
        self.base_url = base_url
        self.results = []
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        
    def print_header(self, text):
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}{text:^80}")
        print(f"{Fore.CYAN}{'='*80}\n")
        
    def print_test(self, name, status, message="", data=None):
        if status == "PASS":
            self.passed += 1
            print(f"{Fore.GREEN}✅ PASS: {name}")
        elif status == "FAIL":
            self.failed += 1
            print(f"{Fore.RED}❌ FAIL: {name}")
        else:
            self.warnings += 1
            print(f"{Fore.YELLOW}⚠️  WARN: {name}")
            
        if message:
            print(f"{Fore.WHITE}   → {message}")
        if data and isinstance(data, dict):
            for key, value in list(data.items())[:3]:
                print(f"{Fore.WHITE}   → {key}: {value}")
                
    def test_weather_dynamic(self):
        """Test if weather data changes with location"""
        self.print_header("🌤️ TEST 1: WEATHER API - DYNAMIC LOCATION DATA")
        
        locations = [
            {"lat": 28.7041, "lon": 77.1025, "name": "Delhi"},
            {"lat": 19.0760, "lon": 72.8777, "name": "Mumbai"},
            {"lat": 12.9716, "lon": 77.5946, "name": "Bangalore"},
            {"lat": 22.5726, "lon": 88.3639, "name": "Kolkata"}
        ]
        
        weather_data = {}
        
        for loc in locations:
            try:
                print(f"\n{Fore.YELLOW}Testing: {loc['name']}...")
                url = f"{self.base_url}/api/chatbot/"
                payload = {
                    "query": f"{loc['name']} ka mausam batao",
                    "language": "hinglish",
                    "location": loc['name'],
                    "latitude": loc['lat'],
                    "longitude": loc['lon']
                }
                
                response = requests.post(url, json=payload, timeout=20)
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get('response', '')
                    
                    # Check if location name appears in response
                    if loc['name'].lower() in response_text.lower():
                        self.print_test(
                            f"Weather Response for {loc['name']}", 
                            "PASS",
                            f"Location-specific response received"
                        )
                        weather_data[loc['name']] = response_text[:200]
                    else:
                        self.print_test(
                            f"Weather Response for {loc['name']}", 
                            "WARN",
                            "Response doesn't mention location name"
                        )
                        weather_data[loc['name']] = response_text[:200]
                else:
                    self.print_test(
                        f"Weather API for {loc['name']}", 
                        "FAIL",
                        f"Status: {response.status_code}"
                    )
                    
                time.sleep(2)  # Rate limiting
                
            except Exception as e:
                self.print_test(f"Weather API for {loc['name']}", "FAIL", str(e))
        
        # Check if responses are different
        if len(set(weather_data.values())) > 1:
            self.print_test(
                "Weather Data Uniqueness", 
                "PASS",
                f"Got {len(set(weather_data.values()))} unique responses for {len(weather_data)} locations"
            )
        else:
            self.print_test(
                "Weather Data Uniqueness", 
                "FAIL",
                "All locations returned same data - not dynamic!"
            )
    
    def test_crop_recommendations_dynamic(self):
        """Test if crop recommendations change with location"""
        self.print_header("🌱 TEST 2: CROP RECOMMENDATIONS - DYNAMIC BY LOCATION")
        
        locations = [
            {"name": "Delhi", "expected_crops": ["wheat", "mustard", "potato"]},
            {"name": "Kerala", "expected_crops": ["coconut", "rubber", "rice"]},
            {"name": "Punjab", "expected_crops": ["wheat", "rice", "cotton"]},
            {"name": "Maharashtra", "expected_crops": ["cotton", "sugarcane", "soybean"]}
        ]
        
        crop_recommendations = {}
        
        for loc in locations:
            try:
                print(f"\n{Fore.YELLOW}Testing: {loc['name']}...")
                url = f"{self.base_url}/api/chatbot/"
                payload = {
                    "query": f"{loc['name']} mein kaun si fasal lagayein?",
                    "language": "hinglish",
                    "location": loc['name']
                }
                
                response = requests.post(url, json=payload, timeout=20)
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get('response', '').lower()
                    
                    # Check if location-specific crops are mentioned
                    mentioned_crops = []
                    for crop in loc['expected_crops']:
                        if crop.lower() in response_text:
                            mentioned_crops.append(crop)
                    
                    if mentioned_crops:
                        self.print_test(
                            f"Crop Recommendations for {loc['name']}", 
                            "PASS",
                            f"Location-specific crops found: {', '.join(mentioned_crops)}"
                        )
                    else:
                        self.print_test(
                            f"Crop Recommendations for {loc['name']}", 
                            "WARN",
                            f"Expected crops not found: {', '.join(loc['expected_crops'])}"
                        )
                    
                    crop_recommendations[loc['name']] = response_text[:300]
                else:
                    self.print_test(
                        f"Crop API for {loc['name']}", 
                        "FAIL",
                        f"Status: {response.status_code}"
                    )
                    
                time.sleep(2)
                
            except Exception as e:
                self.print_test(f"Crop API for {loc['name']}", "FAIL", str(e))
        
        # Check if recommendations are different
        if len(set(crop_recommendations.values())) > 1:
            self.print_test(
                "Crop Recommendations Uniqueness", 
                "PASS",
                f"Got {len(set(crop_recommendations.values()))} unique recommendations for {len(crop_recommendations)} locations"
            )
        else:
            self.print_test(
                "Crop Recommendations Uniqueness", 
                "FAIL",
                "All locations returned same recommendations - not dynamic!"
            )
    
    def test_market_prices_dynamic(self):
        """Test if market prices change with location and commodity"""
        self.print_header("📈 TEST 3: MARKET PRICES - DYNAMIC BY LOCATION & COMMODITY")
        
        tests = [
            {"location": "Delhi", "commodity": "wheat"},
            {"location": "Punjab", "commodity": "wheat"},
            {"location": "Maharashtra", "commodity": "wheat"},
            {"location": "Delhi", "commodity": "rice"},
            {"location": "Delhi", "commodity": "potato"}
        ]
        
        market_data = {}
        
        for test in tests:
            try:
                print(f"\n{Fore.YELLOW}Testing: {test['location']} - {test['commodity']}...")
                url = f"{self.base_url}/api/chatbot/"
                payload = {
                    "query": f"{test['location']} mein {test['commodity']} ki keemat kya hai?",
                    "language": "hinglish",
                    "location": test['location']
                }
                
                response = requests.post(url, json=payload, timeout=20)
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get('response', '')
                    
                    # Check for price indicators (₹, rupees, quintal, kg)
                    has_price = any(indicator in response_text for indicator in ['₹', 'rupees', 'quintal', 'kg', 'price'])
                    
                    if has_price:
                        self.print_test(
                            f"Market Price: {test['location']} - {test['commodity']}", 
                            "PASS",
                            "Price information found in response"
                        )
                    else:
                        self.print_test(
                            f"Market Price: {test['location']} - {test['commodity']}", 
                            "WARN",
                            "No price indicators found"
                        )
                    
                    key = f"{test['location']}-{test['commodity']}"
                    market_data[key] = response_text[:200]
                else:
                    self.print_test(
                        f"Market API: {test['location']} - {test['commodity']}", 
                        "FAIL",
                        f"Status: {response.status_code}"
                    )
                    
                time.sleep(2)
                
            except Exception as e:
                self.print_test(f"Market API: {test['location']} - {test['commodity']}", "FAIL", str(e))
        
        # Check if prices differ by location for same commodity
        wheat_prices = [v for k, v in market_data.items() if 'wheat' in k]
        if len(set(wheat_prices)) > 1:
            self.print_test(
                "Market Prices by Location", 
                "PASS",
                f"Wheat prices differ across {len(set(wheat_prices))} locations"
            )
        elif len(wheat_prices) > 0:
            self.print_test(
                "Market Prices by Location", 
                "WARN",
                "Wheat prices seem similar across locations"
            )
        
        # Check if prices differ by commodity in same location
        delhi_prices = [v for k, v in market_data.items() if 'Delhi' in k]
        if len(set(delhi_prices)) > 1:
            self.print_test(
                "Market Prices by Commodity", 
                "PASS",
                f"Different commodities have different prices in Delhi"
            )
        elif len(delhi_prices) > 0:
            self.print_test(
                "Market Prices by Commodity", 
                "WARN",
                "Prices seem similar for different commodities"
            )
    
    def test_government_schemes(self):
        """Test if government schemes are location-aware"""
        self.print_header("🏛️ TEST 4: GOVERNMENT SCHEMES - LOCATION AWARENESS")
        
        locations = ["Delhi", "Maharashtra", "Punjab", "Tamil Nadu"]
        
        for location in locations:
            try:
                print(f"\n{Fore.YELLOW}Testing: {location}...")
                url = f"{self.base_url}/api/chatbot/"
                payload = {
                    "query": f"{location} mein kisan ke liye kya yojana hai?",
                    "language": "hinglish",
                    "location": location
                }
                
                response = requests.post(url, json=payload, timeout=20)
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get('response', '')
                    
                    # Check for scheme indicators
                    scheme_keywords = ['yojana', 'scheme', 'pm-kisan', 'pradhan mantri', 'subsidy', 'सहायता']
                    has_schemes = any(keyword in response_text.lower() for keyword in scheme_keywords)
                    
                    if has_schemes:
                        self.print_test(
                            f"Government Schemes for {location}", 
                            "PASS",
                            "Scheme information found"
                        )
                    else:
                        self.print_test(
                            f"Government Schemes for {location}", 
                            "WARN",
                            "Limited scheme information"
                        )
                else:
                    self.print_test(
                        f"Schemes API for {location}", 
                        "FAIL",
                        f"Status: {response.status_code}"
                    )
                    
                time.sleep(2)
                
            except Exception as e:
                self.print_test(f"Schemes API for {location}", "FAIL", str(e))
    
    def test_api_data_source(self):
        """Verify responses indicate government API sources"""
        self.print_header("🔍 TEST 5: GOVERNMENT API SOURCE VERIFICATION")
        
        try:
            print(f"\n{Fore.YELLOW}Checking data sources...")
            url = f"{self.base_url}/api/chatbot/"
            payload = {
                "query": "Delhi mein mausam aur fasal ki jankari do",
                "language": "hinglish",
                "location": "Delhi"
            }
            
            response = requests.post(url, json=payload, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check data_source field
                data_source = data.get('data_source', '')
                if data_source:
                    self.print_test(
                        "Data Source Field Present", 
                        "PASS",
                        f"Source: {data_source}"
                    )
                else:
                    self.print_test(
                        "Data Source Field Present", 
                        "WARN",
                        "No data_source field in response"
                    )
                
                # Check for government API indicators in response
                response_text = data.get('response', '')
                gov_indicators = ['IMD', 'Agmarknet', 'ICAR', 'government', 'official', 'sarkari']
                found_indicators = [ind for ind in gov_indicators if ind.lower() in response_text.lower()]
                
                if found_indicators:
                    self.print_test(
                        "Government API Indicators", 
                        "PASS",
                        f"Found: {', '.join(found_indicators)}"
                    )
                else:
                    self.print_test(
                        "Government API Indicators", 
                        "WARN",
                        "No explicit government API mentions"
                    )
                    
                # Check timestamp to verify real-time data
                timestamp = data.get('timestamp')
                if timestamp:
                    self.print_test(
                        "Real-Time Data Timestamp", 
                        "PASS",
                        f"Timestamp: {timestamp}"
                    )
                else:
                    self.print_test(
                        "Real-Time Data Timestamp", 
                        "WARN",
                        "No timestamp in response"
                    )
            else:
                self.print_test(
                    "API Data Source Check", 
                    "FAIL",
                    f"Status: {response.status_code}"
                )
                
        except Exception as e:
            self.print_test("API Data Source Check", "FAIL", str(e))
    
    def test_chatbot_responsiveness(self):
        """Test if AI chatbot provides location-aware responses"""
        self.print_header("🤖 TEST 6: AI CHATBOT - LOCATION-AWARE RESPONSES")
        
        queries = [
            {"query": "Delhi mein abhi barish hogi?", "location": "Delhi"},
            {"query": "Mumbai mein kya fasal lagayein?", "location": "Mumbai"},
            {"query": "Punjab mein gehun ki keemat kya hai?", "location": "Punjab"}
        ]
        
        for query_data in queries:
            try:
                print(f"\n{Fore.YELLOW}Testing: {query_data['query']}")
                url = f"{self.base_url}/api/chatbot/"
                payload = {
                    "query": query_data['query'],
                    "language": "hinglish",
                    "location": query_data['location']
                }
                
                response = requests.post(url, json=payload, timeout=20)
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get('response', '')
                    
                    # Check if response mentions the location
                    if query_data['location'].lower() in response_text.lower():
                        self.print_test(
                            f"Chatbot: {query_data['location']} query", 
                            "PASS",
                            "Location-specific response"
                        )
                    else:
                        self.print_test(
                            f"Chatbot: {query_data['location']} query", 
                            "WARN",
                            "Response doesn't explicitly mention location"
                        )
                    
                    print(f"{Fore.WHITE}   Response preview: {response_text[:150]}...")
                else:
                    self.print_test(
                        f"Chatbot: {query_data['location']} query", 
                        "FAIL",
                        f"Status: {response.status_code}"
                    )
                    
                time.sleep(2)
                
            except Exception as e:
                self.print_test(f"Chatbot: {query_data['location']} query", "FAIL", str(e))
    
    def print_summary(self):
        """Print comprehensive summary"""
        self.print_header("📊 COMPREHENSIVE TEST SUMMARY")
        
        total_tests = self.passed + self.failed + self.warnings
        success_rate = (self.passed / total_tests * 100) if total_tests > 0 else 0
        
        print(f"{Fore.WHITE}Total Tests Run: {total_tests}")
        print(f"{Fore.GREEN}✅ Passed: {self.passed}")
        print(f"{Fore.RED}❌ Failed: {self.failed}")
        print(f"{Fore.YELLOW}⚠️  Warnings: {self.warnings}")
        print(f"\n{Fore.CYAN}Success Rate: {success_rate:.1f}%")
        
        # Overall verdict
        if success_rate >= 80 and self.failed == 0:
            print(f"\n{Fore.GREEN}{'='*80}")
            print(f"{Fore.GREEN}{'🎉 EXCELLENT! GOVERNMENT APIs WORKING DYNAMICALLY!':^80}")
            print(f"{Fore.GREEN}{'='*80}\n")
            verdict = "EXCELLENT"
        elif success_rate >= 60:
            print(f"\n{Fore.YELLOW}{'='*80}")
            print(f"{Fore.YELLOW}{'✅ GOOD! Most services using dynamic government data':^80}")
            print(f"{Fore.YELLOW}{'='*80}\n")
            verdict = "GOOD"
        else:
            print(f"\n{Fore.RED}{'='*80}")
            print(f"{Fore.RED}{'❌ NEEDS IMPROVEMENT! Some services not dynamic':^80}")
            print(f"{Fore.RED}{'='*80}\n")
            verdict = "NEEDS IMPROVEMENT"
        
        # Key findings
        print(f"{Fore.CYAN}📋 Key Findings:\n")
        if self.passed > 0:
            print(f"{Fore.GREEN}✅ {self.passed} tests confirmed dynamic, location-based data")
        if self.warnings > 0:
            print(f"{Fore.YELLOW}⚠️  {self.warnings} tests need verification (data might be static)")
        if self.failed > 0:
            print(f"{Fore.RED}❌ {self.failed} tests failed (API not responding or errors)")
        
        # Save results
        report = {
            'timestamp': datetime.now().isoformat(),
            'base_url': self.base_url,
            'total_tests': total_tests,
            'passed': self.passed,
            'failed': self.failed,
            'warnings': self.warnings,
            'success_rate': success_rate,
            'verdict': verdict
        }
        
        with open('dynamic_api_verification_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n{Fore.CYAN}📄 Report saved: dynamic_api_verification_report.json")
    
    def run_all_tests(self):
        """Run all verification tests"""
        print(f"\n{Fore.MAGENTA}{'='*80}")
        print(f"{Fore.MAGENTA}{'🔍 GOVERNMENT API DYNAMIC DATA VERIFICATION':^80}")
        print(f"{Fore.MAGENTA}{'='*80}")
        print(f"{Fore.WHITE}Target: {self.base_url}")
        print(f"{Fore.WHITE}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.MAGENTA}{'='*80}\n")
        
        print(f"{Fore.YELLOW}🔄 Checking if server is responding...")
        try:
            response = requests.get(self.base_url, timeout=5)
            if response.status_code in [200, 301, 302]:
                print(f"{Fore.GREEN}✅ Server is responding!\n")
            else:
                print(f"{Fore.RED}❌ Server returned status: {response.status_code}\n")
        except Exception as e:
            print(f"{Fore.RED}❌ Server not responding: {e}")
            print(f"{Fore.YELLOW}💡 Please start the server with: python manage.py runserver\n")
            return
        
        # Run all tests
        self.test_weather_dynamic()
        self.test_crop_recommendations_dynamic()
        self.test_market_prices_dynamic()
        self.test_government_schemes()
        self.test_api_data_source()
        self.test_chatbot_responsiveness()
        
        # Print summary
        self.print_summary()

def main():
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--render':
        print(f"{Fore.CYAN}Testing RENDER deployment...")
        verifier = DynamicAPIVerifier(RENDER_URL)
    else:
        print(f"{Fore.CYAN}Testing LOCAL server (use --render to test live site)...")
        verifier = DynamicAPIVerifier(BASE_URL)
    
    verifier.run_all_tests()

if __name__ == "__main__":
    main()

