#!/usr/bin/env python3
"""
Comprehensive Service Verification Script
Tests all 6 services for dynamic location-based data from government APIs
"""

import requests
import json
import time
from datetime import datetime
from colorama import init, Fore, Style

init(autoreset=True)

# Test both local and live
LOCAL_URL = "http://localhost:8000"
RENDER_URL = "https://krishmitra-zrk4.onrender.com"

class ServiceVerifier:
    def __init__(self, base_url):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.passed = 0
        self.failed = 0
        self.total = 0
        
    def print_header(self, text):
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}{text:^80}")
        print(f"{Fore.CYAN}{'='*80}\n")
    
    def test_result(self, name, passed, message=""):
        self.total += 1
        if passed:
            self.passed += 1
            print(f"{Fore.GREEN}✅ PASS: {name}")
        else:
            self.failed += 1
            print(f"{Fore.RED}❌ FAIL: {name}")
        
        if message:
            print(f"{Fore.WHITE}   → {message}")
    
    def test_weather_dynamic(self):
        """Test if weather data changes with location"""
        self.print_header("🌤️ TEST 1: WEATHER - DYNAMIC LOCATION DATA")
        
        locations = [
            {"name": "Delhi", "should_differ": True},
            {"name": "Mumbai", "should_differ": True},
            {"name": "Bangalore", "should_differ": True}
        ]
        
        weather_responses = {}
        
        for loc in locations:
            try:
                print(f"\n{Fore.YELLOW}Testing weather for: {loc['name']}")
                
                response = requests.post(
                    f"{self.api_url}/chatbot/",
                    json={
                        "query": f"{loc['name']} ka mausam batao",
                        "language": "hinglish",
                        "location": loc['name']
                    },
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    weather_text = data.get('response', '')
                    weather_responses[loc['name']] = weather_text
                    
                    # Check if location name is mentioned
                    if loc['name'].lower() in weather_text.lower():
                        self.test_result(
                            f"Weather API: {loc['name']}", 
                            True,
                            f"Location-specific response received"
                        )
                    else:
                        self.test_result(
                            f"Weather API: {loc['name']}", 
                            False,
                            "Location not mentioned in response"
                        )
                else:
                    self.test_result(f"Weather API: {loc['name']}", False, f"HTTP {response.status_code}")
                    
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                self.test_result(f"Weather API: {loc['name']}", False, str(e))
        
        # Verify responses are different (dynamic)
        unique_responses = len(set(weather_responses.values()))
        if unique_responses > 1:
            self.test_result(
                "Weather Data Uniqueness",
                True,
                f"{unique_responses} different responses for {len(weather_responses)} locations = DYNAMIC ✅"
            )
        else:
            self.test_result(
                "Weather Data Uniqueness",
                False,
                "Same response for all locations = NOT DYNAMIC ❌"
            )
    
    def test_crop_recommendations_dynamic(self):
        """Test if crop recommendations change with location"""
        self.print_header("🌱 TEST 2: CROP RECOMMENDATIONS - DYNAMIC BY LOCATION")
        
        locations = [
            {"name": "Delhi", "expected": ["wheat", "mustard", "potato"]},
            {"name": "Kerala", "expected": ["coconut", "rubber", "rice"]},
            {"name": "Punjab", "expected": ["wheat", "rice", "cotton"]}
        ]
        
        crop_responses = {}
        
        for loc in locations:
            try:
                print(f"\n{Fore.YELLOW}Testing crops for: {loc['name']}")
                
                response = requests.post(
                    f"{self.api_url}/chatbot/",
                    json={
                        "query": f"{loc['name']} mein kaun si fasal lagayein?",
                        "language": "hinglish",
                        "location": loc['name']
                    },
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    crop_text = data.get('response', '').lower()
                    crop_responses[loc['name']] = crop_text
                    
                    # Check if any expected crops are mentioned
                    found_crops = [crop for crop in loc['expected'] if crop in crop_text]
                    
                    if found_crops:
                        self.test_result(
                            f"Crop Recommendations: {loc['name']}", 
                            True,
                            f"Location-specific crops found: {', '.join(found_crops)}"
                        )
                    else:
                        self.test_result(
                            f"Crop Recommendations: {loc['name']}", 
                            False,
                            f"Expected crops not found: {', '.join(loc['expected'])}"
                        )
                else:
                    self.test_result(f"Crop Recommendations: {loc['name']}", False, f"HTTP {response.status_code}")
                    
                time.sleep(1)
                
            except Exception as e:
                self.test_result(f"Crop Recommendations: {loc['name']}", False, str(e))
        
        # Verify uniqueness
        unique_responses = len(set(crop_responses.values()))
        if unique_responses > 1:
            self.test_result(
                "Crop Recommendations Uniqueness",
                True,
                f"{unique_responses} different recommendations for {len(crop_responses)} locations = DYNAMIC ✅"
            )
        else:
            self.test_result(
                "Crop Recommendations Uniqueness",
                False,
                "Same recommendations for all locations = NOT DYNAMIC ❌"
            )
    
    def test_market_prices_dynamic(self):
        """Test if market prices change with location and commodity"""
        self.print_header("📈 TEST 3: MARKET PRICES - DYNAMIC BY LOCATION & COMMODITY")
        
        tests = [
            {"location": "Delhi", "commodity": "wheat", "key": "Delhi-wheat"},
            {"location": "Punjab", "commodity": "wheat", "key": "Punjab-wheat"},
            {"location": "Delhi", "commodity": "rice", "key": "Delhi-rice"}
        ]
        
        price_responses = {}
        
        for test in tests:
            try:
                print(f"\n{Fore.YELLOW}Testing: {test['location']} - {test['commodity']}")
                
                response = requests.post(
                    f"{self.api_url}/chatbot/",
                    json={
                        "query": f"{test['location']} mein {test['commodity']} ki keemat kya hai?",
                        "language": "hinglish",
                        "location": test['location']
                    },
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    price_text = data.get('response', '')
                    price_responses[test['key']] = price_text
                    
                    # Check for price indicators
                    has_price = any(ind in price_text for ind in ['₹', 'rupees', 'quintal', 'price', 'keemat'])
                    
                    if has_price:
                        self.test_result(
                            f"Market Price: {test['key']}", 
                            True,
                            "Price information found"
                        )
                    else:
                        self.test_result(
                            f"Market Price: {test['key']}", 
                            False,
                            "No price information found"
                        )
                else:
                    self.test_result(f"Market Price: {test['key']}", False, f"HTTP {response.status_code}")
                    
                time.sleep(1)
                
            except Exception as e:
                self.test_result(f"Market Price: {test['key']}", False, str(e))
        
        # Check if prices differ by location for same commodity
        if 'Delhi-wheat' in price_responses and 'Punjab-wheat' in price_responses:
            if price_responses['Delhi-wheat'] != price_responses['Punjab-wheat']:
                self.test_result(
                    "Price Variation by Location",
                    True,
                    "Wheat prices differ between Delhi and Punjab = DYNAMIC ✅"
                )
            else:
                self.test_result(
                    "Price Variation by Location",
                    False,
                    "Same wheat price for both locations = NOT DYNAMIC ❌"
                )
        
        # Check if prices differ by commodity in same location
        if 'Delhi-wheat' in price_responses and 'Delhi-rice' in price_responses:
            if price_responses['Delhi-wheat'] != price_responses['Delhi-rice']:
                self.test_result(
                    "Price Variation by Commodity",
                    True,
                    "Different commodities have different prices = DYNAMIC ✅"
                )
            else:
                self.test_result(
                    "Price Variation by Commodity",
                    False,
                    "Same price for different commodities = NOT DYNAMIC ❌"
                )
    
    def test_government_schemes(self):
        """Test government schemes service"""
        self.print_header("🏛️ TEST 4: GOVERNMENT SCHEMES")
        
        locations = ["Delhi", "Maharashtra", "Punjab"]
        
        for location in locations:
            try:
                print(f"\n{Fore.YELLOW}Testing schemes for: {location}")
                
                response = requests.post(
                    f"{self.api_url}/chatbot/",
                    json={
                        "query": f"{location} mein kisan ke liye kya yojana hai?",
                        "language": "hinglish",
                        "location": location
                    },
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    schemes_text = data.get('response', '')
                    
                    # Check for scheme keywords
                    scheme_keywords = ['yojana', 'scheme', 'pm-kisan', 'pradhan mantri', 'subsidy']
                    has_schemes = any(kw in schemes_text.lower() for kw in scheme_keywords)
                    
                    if has_schemes:
                        self.test_result(
                            f"Government Schemes: {location}", 
                            True,
                            "Scheme information found"
                        )
                    else:
                        self.test_result(
                            f"Government Schemes: {location}", 
                            False,
                            "No scheme information found"
                        )
                else:
                    self.test_result(f"Government Schemes: {location}", False, f"HTTP {response.status_code}")
                    
                time.sleep(1)
                
            except Exception as e:
                self.test_result(f"Government Schemes: {location}", False, str(e))
    
    def test_pest_control(self):
        """Test pest control service"""
        self.print_header("🐛 TEST 5: PEST CONTROL")
        
        test = {
            "crop": "tomato",
            "problem": "leaves turning yellow and spots appearing"
        }
        
        try:
            print(f"\n{Fore.YELLOW}Testing pest control for: {test['crop']}")
            
            response = requests.post(
                f"{self.api_url}/chatbot/",
                json={
                    "query": f"{test['crop']} ki fasal mein yeh samasya hai: {test['problem']}. Kya upay batao?",
                    "language": "hinglish",
                    "location": "Delhi"
                },
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                pest_text = data.get('response', '')
                
                # Check for solution keywords
                solution_keywords = ['spray', 'treatment', 'control', 'niyantran', 'upay', 'ilaj']
                has_solution = any(kw in pest_text.lower() for kw in solution_keywords)
                
                if has_solution:
                    self.test_result(
                        "Pest Control Solution", 
                        True,
                        "Solution information found"
                    )
                else:
                    self.test_result(
                        "Pest Control Solution", 
                        False,
                        "No solution information found"
                    )
            else:
                self.test_result("Pest Control Solution", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.test_result("Pest Control Solution", False, str(e))
    
    def test_ai_chatbot(self):
        """Test AI chatbot service"""
        self.print_header("🤖 TEST 6: AI CHATBOT")
        
        queries = [
            {"query": "Delhi mein abhi barish hogi?", "location": "Delhi"},
            {"query": "Mumbai mein kya fasal lagayein?", "location": "Mumbai"}
        ]
        
        for query_data in queries:
            try:
                print(f"\n{Fore.YELLOW}Testing chatbot: {query_data['query']}")
                
                response = requests.post(
                    f"{self.api_url}/chatbot/",
                    json={
                        "query": query_data['query'],
                        "language": "hinglish",
                        "location": query_data['location']
                    },
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get('response', '')
                    
                    # Check if response mentions the location
                    if query_data['location'].lower() in response_text.lower():
                        self.test_result(
                            f"Chatbot: {query_data['location']}", 
                            True,
                            "Location-aware response"
                        )
                    else:
                        self.test_result(
                            f"Chatbot: {query_data['location']}", 
                            False,
                            "Response doesn't mention location"
                        )
                    
                    print(f"{Fore.WHITE}   Response preview: {response_text[:100]}...")
                else:
                    self.test_result(f"Chatbot: {query_data['location']}", False, f"HTTP {response.status_code}")
                    
                time.sleep(1)
                
            except Exception as e:
                self.test_result(f"Chatbot: {query_data['location']}", False, str(e))
    
    def print_summary(self):
        """Print verification summary"""
        self.print_header("📊 VERIFICATION SUMMARY")
        
        success_rate = (self.passed / self.total * 100) if self.total > 0 else 0
        
        print(f"{Fore.WHITE}Total Tests: {self.total}")
        print(f"{Fore.GREEN}✅ Passed: {self.passed}")
        print(f"{Fore.RED}❌ Failed: {self.failed}")
        print(f"\n{Fore.CYAN}Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print(f"\n{Fore.GREEN}{'='*80}")
            print(f"{Fore.GREEN}{'🎉 EXCELLENT! ALL SERVICES WORKING DYNAMICALLY!':^80}")
            print(f"{Fore.GREEN}{'='*80}\n")
        elif success_rate >= 60:
            print(f"\n{Fore.YELLOW}{'='*80}")
            print(f"{Fore.YELLOW}{'✅ GOOD! Most services working':^80}")
            print(f"{Fore.YELLOW}{'='*80}\n")
        else:
            print(f"\n{Fore.RED}{'='*80}")
            print(f"{Fore.RED}{'❌ NEEDS ATTENTION! Some services failing':^80}")
            print(f"{Fore.RED}{'='*80}\n")
        
        # Save report
        report = {
            'timestamp': datetime.now().isoformat(),
            'base_url': self.base_url,
            'total_tests': self.total,
            'passed': self.passed,
            'failed': self.failed,
            'success_rate': success_rate
        }
        
        with open('service_verification_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"{Fore.CYAN}📄 Report saved: service_verification_report.json")
    
    def run_all_tests(self):
        """Run all verification tests"""
        print(f"\n{Fore.MAGENTA}{'='*80}")
        print(f"{Fore.MAGENTA}{'🔍 COMPREHENSIVE SERVICE VERIFICATION':^80}")
        print(f"{Fore.MAGENTA}{'='*80}")
        print(f"{Fore.WHITE}Target: {self.base_url}")
        print(f"{Fore.WHITE}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.MAGENTA}{'='*80}\n")
        
        # Check if server is responding
        try:
            print(f"{Fore.YELLOW}🔄 Checking server status...")
            response = requests.get(self.base_url, timeout=5)
            print(f"{Fore.GREEN}✅ Server is responding (Status: {response.status_code})\n")
        except Exception as e:
            print(f"{Fore.RED}❌ Server not responding: {e}")
            print(f"{Fore.YELLOW}💡 If testing locally, start server with: python manage.py runserver\n")
            return
        
        # Run all tests
        self.test_weather_dynamic()
        self.test_crop_recommendations_dynamic()
        self.test_market_prices_dynamic()
        self.test_government_schemes()
        self.test_pest_control()
        self.test_ai_chatbot()
        
        # Print summary
        self.print_summary()

def main():
    import sys
    
    print(f"\n{Fore.CYAN}Select target to test:")
    print(f"{Fore.WHITE}1. Local server (http://localhost:8000)")
    print(f"{Fore.WHITE}2. Live Render site (https://krishmitra-zrk4.onrender.com)")
    print(f"{Fore.WHITE}3. Both\n")
    
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input(f"{Fore.YELLOW}Enter choice (1/2/3): ").strip()
    
    if choice == '1':
        verifier = ServiceVerifier(LOCAL_URL)
        verifier.run_all_tests()
    elif choice == '2':
        print(f"\n{Fore.YELLOW}⏳ Waiting 10 seconds for Render deployment to complete...")
        time.sleep(10)
        verifier = ServiceVerifier(RENDER_URL)
        verifier.run_all_tests()
    elif choice == '3':
        print(f"\n{Fore.CYAN}Testing LOCAL server first...")
        verifier_local = ServiceVerifier(LOCAL_URL)
        verifier_local.run_all_tests()
        
        print(f"\n{Fore.YELLOW}⏳ Waiting 5 seconds before testing Render...")
        time.sleep(5)
        
        print(f"\n{Fore.CYAN}Testing RENDER deployment...")
        verifier_render = ServiceVerifier(RENDER_URL)
        verifier_render.run_all_tests()
    else:
        print(f"{Fore.RED}Invalid choice. Use: python verify_all_services.py [1|2|3]")

if __name__ == "__main__":
    main()

