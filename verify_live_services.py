#!/usr/bin/env python3
"""
Verify all services are working from live website
"""

import requests
import json
import time
from datetime import datetime

class LiveServiceVerifier:
    def __init__(self, base_url="https://krishmitra-zrk4.onrender.com"):
        self.base_url = base_url
        self.results = {}
        
    def test_website_accessibility(self):
        """Test if website is accessible"""
        print("\n🌐 TESTING WEBSITE ACCESSIBILITY")
        print("=" * 50)
        
        try:
            response = requests.get(self.base_url, timeout=10)
            if response.status_code == 200:
                print(f"✅ Website is accessible")
                print(f"   Status Code: {response.status_code}")
                print(f"   Response Time: {response.elapsed.total_seconds():.2f}s")
                print(f"   Content Length: {len(response.text)} characters")
                
                # Check if key elements are present
                content = response.text.lower()
                checks = {
                    'service_cards': 'service-card' in content,
                    'javascript': 'showservice' in content or 'showService' in content,
                    'government_schemes': 'सरकारी योजनाएं' in content,
                    'crop_recommendations': 'फसल सुझाव' in content,
                    'weather': 'मौसम' in content,
                    'market_prices': 'बाजार कीमतें' in content,
                    'pest_control': 'कीट नियंत्रण' in content,
                    'ai_assistant': 'ai सहायक' in content
                }
                
                print(f"\n📋 CONTENT VERIFICATION:")
                for check, result in checks.items():
                    status = "✅" if result else "❌"
                    print(f"   {status} {check.replace('_', ' ').title()}: {'Found' if result else 'Missing'}")
                
                self.results['website_access'] = {
                    'status': 'success',
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'content_checks': checks
                }
                
                return True
            else:
                print(f"❌ Website not accessible: {response.status_code}")
                self.results['website_access'] = {
                    'status': 'failed',
                    'status_code': response.status_code
                }
                return False
                
        except Exception as e:
            print(f"❌ Error accessing website: {e}")
            self.results['website_access'] = {
                'status': 'error',
                'error': str(e)
            }
            return False
    
    def test_api_endpoints(self):
        """Test API endpoints"""
        print("\n🔌 TESTING API ENDPOINTS")
        print("=" * 50)
        
        endpoints = [
            ('/api/health/', 'Health Check'),
            ('/api/chatbot/', 'Chatbot API'),
            ('/api/locations/suggestions/?q=delhi', 'Location API'),
            ('/api/crops/', 'Crops API')
        ]
        
        for endpoint, name in endpoints:
            try:
                url = self.base_url + endpoint
                if endpoint.endswith('/chatbot/'):
                    # Test POST request for chatbot
                    data = {"query": "test"}
                    response = requests.post(url, json=data, timeout=10)
                else:
                    # Test GET request
                    response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    print(f"✅ {name}: Working (Status: {response.status_code})")
                    self.results[f'api_{name.lower().replace(" ", "_")}'] = {
                        'status': 'success',
                        'status_code': response.status_code,
                        'response_time': response.elapsed.total_seconds()
                    }
                else:
                    print(f"❌ {name}: Failed (Status: {response.status_code})")
                    self.results[f'api_{name.lower().replace(" ", "_")}'] = {
                        'status': 'failed',
                        'status_code': response.status_code
                    }
                    
            except Exception as e:
                print(f"❌ {name}: Error - {e}")
                self.results[f'api_{name.lower().replace(" ", "_")}'] = {
                    'status': 'error',
                    'error': str(e)
                }
    
    def test_service_functionality(self):
        """Test service functionality through API"""
        print("\n🎯 TESTING SERVICE FUNCTIONALITY")
        print("=" * 50)
        
        services = [
            {
                'name': 'Crop Recommendations',
                'query': 'Delhi mein kya fasal lagayein?',
                'expected_keywords': ['फसल', 'crop', 'recommendation']
            },
            {
                'name': 'Weather Service',
                'query': 'Delhi ka mausam kaisa hai?',
                'expected_keywords': ['मौसम', 'weather', 'temperature']
            },
            {
                'name': 'Market Prices',
                'query': 'Delhi mein wheat ki price kya hai?',
                'expected_keywords': ['price', 'market', 'wheat']
            },
            {
                'name': 'Government Schemes',
                'query': 'Delhi mein koi government scheme hai kya?',
                'expected_keywords': ['scheme', 'government', 'सरकारी']
            },
            {
                'name': 'AI Assistant',
                'query': 'Hello, how are you?',
                'expected_keywords': ['response', 'assistant', 'help']
            }
        ]
        
        for service in services:
            try:
                url = self.base_url + '/api/chatbot/'
                data = {"query": service['query']}
                
                response = requests.post(url, json=data, timeout=15)
                
                if response.status_code == 200:
                    result = response.json()
                    response_text = result.get('response', '').lower()
                    
                    # Check if response contains expected keywords
                    keyword_found = any(keyword.lower() in response_text for keyword in service['expected_keywords'])
                    
                    if keyword_found:
                        print(f"✅ {service['name']}: Working with relevant response")
                    else:
                        print(f"⚠️ {service['name']}: Responding but content unclear")
                    
                    self.results[f'service_{service["name"].lower().replace(" ", "_")}'] = {
                        'status': 'success',
                        'status_code': response.status_code,
                        'response_time': response.elapsed.total_seconds(),
                        'has_relevant_content': keyword_found,
                        'response_length': len(result.get('response', ''))
                    }
                else:
                    print(f"❌ {service['name']}: Failed (Status: {response.status_code})")
                    self.results[f'service_{service["name"].lower().replace(" ", "_")}'] = {
                        'status': 'failed',
                        'status_code': response.status_code
                    }
                    
            except Exception as e:
                print(f"❌ {service['name']}: Error - {e}")
                self.results[f'service_{service["name"].lower().replace(" ", "_")}'] = {
                    'status': 'error',
                    'error': str(e)
                }
    
    def test_location_detection(self):
        """Test location detection service"""
        print("\n📍 TESTING LOCATION DETECTION")
        print("=" * 50)
        
        try:
            url = self.base_url + '/api/locations/suggestions/?q=delhi'
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                suggestions = result.get('suggestions', [])
                
                if suggestions:
                    print(f"✅ Location Detection: Working")
                    print(f"   Suggestions found: {len(suggestions)}")
                    for suggestion in suggestions[:2]:
                        print(f"   - {suggestion.get('name', 'N/A')}, {suggestion.get('state', 'N/A')}")
                else:
                    print(f"⚠️ Location Detection: Responding but no suggestions")
                
                self.results['location_detection'] = {
                    'status': 'success',
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'suggestions_count': len(suggestions)
                }
            else:
                print(f"❌ Location Detection: Failed (Status: {response.status_code})")
                self.results['location_detection'] = {
                    'status': 'failed',
                    'status_code': response.status_code
                }
                
        except Exception as e:
            print(f"❌ Location Detection: Error - {e}")
            self.results['location_detection'] = {
                'status': 'error',
                'error': str(e)
            }
    
    def test_performance(self):
        """Test website performance"""
        print("\n⚡ TESTING PERFORMANCE")
        print("=" * 50)
        
        try:
            start_time = time.time()
            response = requests.get(self.base_url, timeout=15)
            end_time = time.time()
            
            if response.status_code == 200:
                load_time = end_time - start_time
                print(f"✅ Website Load Time: {load_time:.2f}s")
                
                if load_time < 3:
                    print(f"   🚀 Excellent performance")
                elif load_time < 5:
                    print(f"   ✅ Good performance")
                else:
                    print(f"   ⚠️ Slow performance")
                
                self.results['performance'] = {
                    'status': 'success',
                    'load_time': load_time,
                    'status_code': response.status_code
                }
            else:
                print(f"❌ Performance test failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Performance test error: {e}")
    
    def run_all_tests(self):
        """Run all verification tests"""
        print("🔍 COMPREHENSIVE LIVE SERVICE VERIFICATION")
        print("=" * 60)
        print(f"Testing: {self.base_url}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run all tests
        website_ok = self.test_website_accessibility()
        
        if website_ok:
            self.test_api_endpoints()
            self.test_service_functionality()
            self.test_location_detection()
            self.test_performance()
        
        # Generate summary report
        self.generate_summary_report()
    
    def generate_summary_report(self):
        """Generate summary report"""
        print("\n📊 LIVE SERVICE VERIFICATION REPORT")
        print("=" * 60)
        
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results.values() if r['status'] == 'success')
        failed_tests = sum(1 for r in self.results.values() if r['status'] == 'failed')
        error_tests = sum(1 for r in self.results.values() if r['status'] == 'error')
        
        print(f"📈 OVERALL STATISTICS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Successful: {successful_tests}/{total_tests} ({successful_tests/total_tests*100:.1f}%)")
        print(f"   Failed: {failed_tests}/{total_tests} ({failed_tests/total_tests*100:.1f}%)")
        print(f"   Errors: {error_tests}/{total_tests} ({error_tests/total_tests*100:.1f}%)")
        
        print(f"\n📋 DETAILED RESULTS:")
        for test_name, result in self.results.items():
            status_icon = "✅" if result['status'] == 'success' else "❌"
            
            print(f"   {status_icon} {test_name.replace('_', ' ').title()}:")
            print(f"      Status: {result['status']}")
            
            if result['status'] == 'success':
                if 'response_time' in result:
                    print(f"      Response Time: {result['response_time']:.2f}s")
                if 'load_time' in result:
                    print(f"      Load Time: {result['load_time']:.2f}s")
                if 'content_checks' in result:
                    passed_checks = sum(1 for v in result['content_checks'].values() if v)
                    total_checks = len(result['content_checks'])
                    print(f"      Content Checks: {passed_checks}/{total_checks} passed")
            elif result['status'] == 'failed':
                print(f"      Status Code: {result.get('status_code', 'N/A')}")
            else:
                print(f"      Error: {result.get('error', 'N/A')}")
        
        print(f"\n🎯 RECOMMENDATIONS:")
        if successful_tests == total_tests:
            print(f"   🎉 All services are working perfectly!")
            print(f"   🚀 Website is fully functional and ready for users")
        elif successful_tests > total_tests * 0.8:
            print(f"   ✅ Most services are working well")
            print(f"   🔧 Minor issues detected, but overall functional")
        else:
            print(f"   ⚠️ Several issues detected")
            print(f"   🔧 Review failed tests and fix critical issues")
        
        print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    verifier = LiveServiceVerifier()
    verifier.run_all_tests()
