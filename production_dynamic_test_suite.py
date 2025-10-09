#!/usr/bin/env python3
"""
Production Dynamic Test Suite for Krishimitra AI Agricultural Advisory System
Comprehensive testing of AI responsiveness, accuracy, government APIs, and farming queries
"""

import requests
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple
import concurrent.futures
import statistics

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductionTestSuite:
    """Comprehensive production testing suite for agricultural advisory system"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.test_results = {
            'start_time': datetime.now(),
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'response_times': [],
            'api_tests': {},
            'ai_tests': {},
            'government_data_tests': {},
            'farming_query_tests': {}
        }
        
        # Test data for comprehensive testing
        self.test_queries = {
            'crop_recommendations': [
                "crop suggest karo delhi mein",
                "which crop should I plant in punjab",
                "best crop for rajasthan soil",
                "कौन सी फसल लगाऊं उत्तर प्रदेश में",
                "महाराष्ट्र में क्या उगाएं"
            ],
            'market_prices': [
                "wheat price in delhi",
                "rice market price mumbai",
                "cotton price karnataka",
                "गेहूं की कीमत दिल्ली में",
                "चावल का भाव मुंबई में"
            ],
            'weather_queries': [
                "weather in bangalore",
                "rainfall prediction for punjab",
                "temperature in chennai",
                "मुंबई में मौसम",
                "बारिश का पूर्वानुमान"
            ],
            'government_schemes': [
                "government schemes for farmers",
                "PM Kisan benefits",
                "crop insurance scheme",
                "किसानों के लिए सरकारी योजनाएं",
                "पीएम किसान योजना"
            ],
            'pest_control': [
                "pest control for rice",
                "disease in wheat crop",
                "insect problem in cotton",
                "चावल में रोग नियंत्रण",
                "गेहूं में कीट समस्या"
            ],
            'complex_queries': [
                "best crop for sandy soil in rajasthan with low rainfall",
                "crop rotation for wheat field in punjab",
                "organic farming suggestions for tomato in maharashtra",
                "राजस्थान में रेतीली मिट्टी के लिए सबसे अच्छी फसल",
                "पंजाब में गेहूं के खेत के लिए फसल चक्र"
            ]
        }
        
        self.indian_locations = [
            {'city': 'Delhi', 'lat': 28.6139, 'lon': 77.2090, 'state': 'Delhi'},
            {'city': 'Mumbai', 'lat': 19.0760, 'lon': 72.8777, 'state': 'Maharashtra'},
            {'city': 'Bangalore', 'lat': 12.9716, 'lon': 77.5946, 'state': 'Karnataka'},
            {'city': 'Chennai', 'lat': 13.0827, 'lon': 80.2707, 'state': 'Tamil Nadu'},
            {'city': 'Kolkata', 'lat': 22.5726, 'lon': 88.3639, 'state': 'West Bengal'},
            {'city': 'Hyderabad', 'lat': 17.3850, 'lon': 78.4867, 'state': 'Telangana'},
            {'city': 'Pune', 'lat': 18.5204, 'lon': 73.8567, 'state': 'Maharashtra'},
            {'city': 'Ahmedabad', 'lat': 23.0225, 'lon': 72.5714, 'state': 'Gujarat'},
            {'city': 'Jaipur', 'lat': 26.9124, 'lon': 75.7873, 'state': 'Rajasthan'},
            {'city': 'Lucknow', 'lat': 26.8467, 'lon': 80.9462, 'state': 'Uttar Pradesh'}
        ]

    def test_server_connectivity(self) -> bool:
        """Test basic server connectivity"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            if response.status_code == 200:
                logger.info("✅ Server connectivity test passed")
                return True
            else:
                logger.error(f"❌ Server connectivity test failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Server connectivity test failed: {e}")
            return False

    def test_api_endpoints(self) -> Dict[str, Any]:
        """Test all critical API endpoints"""
        logger.info("🧪 Testing API endpoints...")
        api_tests = {}
        
        endpoints = [
            ('/api/advisories/chatbot/', 'POST'),
            ('/api/weather/current/', 'GET'),
            ('/api/market-prices/prices/', 'GET'),
            ('/api/advisories/ml_crop_recommendation/', 'POST'),
            ('/api/advisories/fertilizer_recommendation/', 'POST'),
            ('/api/schema/swagger-ui/', 'GET')
        ]
        
        for endpoint, method in endpoints:
            try:
                start_time = time.time()
                
                if method == 'GET':
                    if 'weather' in endpoint:
                        response = requests.get(f"{self.base_url}{endpoint}", 
                                              params={'lat': 28.6139, 'lon': 77.2090, 'lang': 'en'}, 
                                              timeout=10)
                    elif 'market' in endpoint:
                        response = requests.get(f"{self.base_url}{endpoint}", 
                                              params={'lat': 28.6139, 'lon': 77.2090, 'lang': 'en', 'product': 'wheat'}, 
                                              timeout=10)
                    else:
                        response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                else:  # POST
                    test_data = {
                        'query': 'test query',
                        'language': 'en'
                    }
                    response = requests.post(f"{self.base_url}{endpoint}", 
                                           json=test_data, 
                                           timeout=10)
                
                response_time = time.time() - start_time
                
                api_tests[endpoint] = {
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'success': response.status_code in [200, 201],
                    'content_length': len(response.content)
                }
                
                if response.status_code in [200, 201]:
                    logger.info(f"✅ {endpoint} - {response.status_code} ({response_time:.2f}s)")
                else:
                    logger.warning(f"⚠️ {endpoint} - {response.status_code} ({response_time:.2f}s)")
                    
            except Exception as e:
                api_tests[endpoint] = {
                    'status_code': 0,
                    'response_time': 0,
                    'success': False,
                    'error': str(e)
                }
                logger.error(f"❌ {endpoint} - Error: {e}")
        
        self.test_results['api_tests'] = api_tests
        return api_tests

    def test_ai_responsiveness(self) -> Dict[str, Any]:
        """Test AI assistant responsiveness and accuracy"""
        logger.info("🤖 Testing AI assistant responsiveness...")
        ai_tests = {
            'response_times': [],
            'accuracy_scores': [],
            'language_support': {},
            'query_types': {}
        }
        
        # Test different query types
        for query_type, queries in self.test_queries.items():
            logger.info(f"Testing {query_type} queries...")
            query_results = []
            
            for query in queries:
                try:
                    start_time = time.time()
                    
                    # Determine language
                    language = 'hi' if any(ord(char) > 127 for char in query) else 'en'
                    
                    response = requests.post(
                        f"{self.base_url}/api/advisories/chatbot/",
                        json={
                            'query': query,
                            'language': language,
                            'session_id': f'test-{int(time.time())}'
                        },
                        timeout=15
                    )
                    
                    response_time = time.time() - start_time
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        response_text = response_data.get('response', '')
                        
                        # Check response quality
                        quality_score = self._assess_response_quality(query, response_text, query_type)
                        
                        query_results.append({
                            'query': query,
                            'response_time': response_time,
                            'quality_score': quality_score,
                            'response_length': len(response_text),
                            'success': True
                        })
                        
                        ai_tests['response_times'].append(response_time)
                        ai_tests['accuracy_scores'].append(quality_score)
                        
                        logger.info(f"✅ {query_type}: {response_time:.2f}s (Quality: {quality_score:.1f}/10)")
                    else:
                        query_results.append({
                            'query': query,
                            'response_time': response_time,
                            'quality_score': 0,
                            'success': False,
                            'error': f"HTTP {response.status_code}"
                        })
                        logger.error(f"❌ {query_type}: HTTP {response.status_code}")
                        
                except Exception as e:
                    query_results.append({
                        'query': query,
                        'response_time': 0,
                        'quality_score': 0,
                        'success': False,
                        'error': str(e)
                    })
                    logger.error(f"❌ {query_type}: Error - {e}")
            
            ai_tests['query_types'][query_type] = query_results
        
        self.test_results['ai_tests'] = ai_tests
        return ai_tests

    def test_government_data_integration(self) -> Dict[str, Any]:
        """Test government API data integration and quality"""
        logger.info("🏛️ Testing government data integration...")
        gov_tests = {
            'msp_prices': {},
            'schemes_data': {},
            'weather_data': {},
            'market_data': {},
            'data_quality': {}
        }
        
        # Test MSP prices
        msp_crops = ['wheat', 'rice', 'cotton', 'sugarcane', 'maize']
        for crop in msp_crops:
            try:
                response = requests.post(
                    f"{self.base_url}/api/advisories/chatbot/",
                    json={
                        'query': f"{crop} MSP price government",
                        'language': 'en'
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    response_text = response_data.get('response', '')
                    
                    # Check if MSP data is present
                    msp_indicators = ['MSP', 'minimum support price', '₹', 'rupees', 'quintal']
                    has_msp_data = any(indicator.lower() in response_text.lower() for indicator in msp_indicators)
                    
                    gov_tests['msp_prices'][crop] = {
                        'has_data': has_msp_data,
                        'response_length': len(response_text),
                        'quality': 8 if has_msp_data else 3
                    }
                    
                    logger.info(f"✅ MSP {crop}: {'Has data' if has_msp_data else 'Missing data'}")
                else:
                    gov_tests['msp_prices'][crop] = {'has_data': False, 'error': f"HTTP {response.status_code}"}
                    logger.error(f"❌ MSP {crop}: HTTP {response.status_code}")
                    
            except Exception as e:
                gov_tests['msp_prices'][crop] = {'has_data': False, 'error': str(e)}
                logger.error(f"❌ MSP {crop}: Error - {e}")
        
        # Test government schemes
        schemes = ['PM Kisan', 'PMFBY', 'Soil Health Card', 'Kisan Credit Card']
        for scheme in schemes:
            try:
                response = requests.post(
                    f"{self.base_url}/api/advisories/chatbot/",
                    json={
                        'query': f"{scheme} government scheme benefits",
                        'language': 'en'
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    response_text = response_data.get('response', '')
                    
                    # Check if scheme data is present
                    scheme_indicators = [scheme.lower(), 'benefit', 'subsidy', '₹', 'rupees', 'government']
                    has_scheme_data = any(indicator.lower() in response_text.lower() for indicator in scheme_indicators)
                    
                    gov_tests['schemes_data'][scheme] = {
                        'has_data': has_scheme_data,
                        'response_length': len(response_text),
                        'quality': 8 if has_scheme_data else 3
                    }
                    
                    logger.info(f"✅ Scheme {scheme}: {'Has data' if has_scheme_data else 'Missing data'}")
                else:
                    gov_tests['schemes_data'][scheme] = {'has_data': False, 'error': f"HTTP {response.status_code}"}
                    logger.error(f"❌ Scheme {scheme}: HTTP {response.status_code}")
                    
            except Exception as e:
                gov_tests['schemes_data'][scheme] = {'has_data': False, 'error': str(e)}
                logger.error(f"❌ Scheme {scheme}: Error - {e}")
        
        self.test_results['government_data_tests'] = gov_tests
        return gov_tests

    def test_location_based_queries(self) -> Dict[str, Any]:
        """Test location-based agricultural queries"""
        logger.info("📍 Testing location-based queries...")
        location_tests = {}
        
        for location in self.indian_locations[:5]:  # Test top 5 locations
            city = location['city']
            state = location['state']
            
            try:
                response = requests.post(
                    f"{self.base_url}/api/advisories/chatbot/",
                    json={
                        'query': f"crop recommendation for {city} {state}",
                        'language': 'en',
                        'latitude': location['lat'],
                        'longitude': location['lon'],
                        'location_name': city
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    response_text = response_data.get('response', '')
                    
                    # Check if location-specific data is present
                    location_indicators = [city.lower(), state.lower(), 'crop', 'recommendation', 'suitable']
                    has_location_data = any(indicator.lower() in response_text.lower() for indicator in location_indicators)
                    
                    location_tests[city] = {
                        'has_location_data': has_location_data,
                        'response_length': len(response_text),
                        'quality': 8 if has_location_data else 4
                    }
                    
                    logger.info(f"✅ {city}: {'Location-specific data' if has_location_data else 'Generic response'}")
                else:
                    location_tests[city] = {'has_location_data': False, 'error': f"HTTP {response.status_code}"}
                    logger.error(f"❌ {city}: HTTP {response.status_code}")
                    
            except Exception as e:
                location_tests[city] = {'has_location_data': False, 'error': str(e)}
                logger.error(f"❌ {city}: Error - {e}")
        
        return location_tests

    def test_concurrent_requests(self) -> Dict[str, Any]:
        """Test system performance under concurrent load"""
        logger.info("⚡ Testing concurrent request handling...")
        
        def make_request(query_data):
            try:
                start_time = time.time()
                response = requests.post(
                    f"{self.base_url}/api/advisories/chatbot/",
                    json=query_data,
                    timeout=10
                )
                response_time = time.time() - start_time
                
                return {
                    'success': response.status_code == 200,
                    'response_time': response_time,
                    'status_code': response.status_code
                }
            except Exception as e:
                return {
                    'success': False,
                    'response_time': 0,
                    'error': str(e)
                }
        
        # Create concurrent requests
        concurrent_requests = []
        for i in range(10):  # 10 concurrent requests
            query_data = {
                'query': f"test query {i}",
                'language': 'en',
                'session_id': f'concurrent-test-{i}'
            }
            concurrent_requests.append(query_data)
        
        # Execute concurrent requests
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, req) for req in concurrent_requests]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Filter valid response times
        valid_response_times = [r['response_time'] for r in results if r['response_time'] > 0]
        
        concurrent_tests = {
            'total_requests': len(concurrent_requests),
            'successful_requests': sum(1 for r in results if r['success']),
            'failed_requests': sum(1 for r in results if not r['success']),
            'total_time': total_time,
            'average_response_time': statistics.mean(valid_response_times) if valid_response_times else 0,
            'max_response_time': max(valid_response_times, default=0),
            'min_response_time': min(valid_response_times, default=0)
        }
        
        logger.info(f"✅ Concurrent test: {concurrent_tests['successful_requests']}/{concurrent_tests['total_requests']} successful")
        return concurrent_tests

    def _assess_response_quality(self, query: str, response: str, query_type: str) -> float:
        """Assess the quality of AI response (0-10 scale)"""
        if not response or len(response) < 10:
            return 0
        
        score = 5.0  # Base score
        
        # Length assessment
        if len(response) > 100:
            score += 1
        if len(response) > 200:
            score += 1
        
        # Content relevance
        query_lower = query.lower()
        response_lower = response.lower()
        
        if query_type == 'crop_recommendations':
            crop_indicators = ['crop', 'plant', 'grow', 'suitable', 'recommend']
            score += sum(1 for indicator in crop_indicators if indicator in response_lower)
        elif query_type == 'market_prices':
            price_indicators = ['price', '₹', 'rupees', 'quintal', 'market', 'cost']
            score += sum(1 for indicator in price_indicators if indicator in response_lower)
        elif query_type == 'weather_queries':
            weather_indicators = ['weather', 'temperature', 'rain', 'humidity', 'forecast']
            score += sum(1 for indicator in weather_indicators if indicator in response_lower)
        elif query_type == 'government_schemes':
            scheme_indicators = ['government', 'scheme', 'benefit', 'subsidy', 'pm kisan']
            score += sum(1 for indicator in scheme_indicators if indicator in response_lower)
        elif query_type == 'pest_control':
            pest_indicators = ['pest', 'disease', 'control', 'treatment', 'medicine']
            score += sum(1 for indicator in pest_indicators if indicator in response_lower)
        
        # Language consistency
        if any(ord(char) > 127 for char in query):  # Hindi query
            if any(ord(char) > 127 for char in response):  # Hindi response
                score += 1
        
        return min(score, 10.0)

    def generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        logger.info("📊 Generating comprehensive test report...")
        
        # Calculate overall statistics
        total_tests = 0
        passed_tests = 0
        
        # API tests
        api_success = sum(1 for test in self.test_results['api_tests'].values() if test.get('success', False))
        total_tests += len(self.test_results['api_tests'])
        passed_tests += api_success
        
        # AI tests
        ai_success = 0
        for query_type, results in self.test_results['ai_tests'].get('query_types', {}).items():
            ai_success += sum(1 for result in results if result.get('success', False))
            total_tests += len(results)
        passed_tests += ai_success
        
        # Government data tests
        gov_success = 0
        for category, tests in self.test_results['government_data_tests'].items():
            if isinstance(tests, dict):
                gov_success += sum(1 for test in tests.values() if test.get('has_data', False))
                total_tests += len(tests)
        passed_tests += gov_success
        
        # Calculate response time statistics
        response_times = self.test_results['ai_tests'].get('response_times', [])
        avg_response_time = statistics.mean(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        
        # Calculate accuracy statistics
        accuracy_scores = self.test_results['ai_tests'].get('accuracy_scores', [])
        avg_accuracy = statistics.mean(accuracy_scores) if accuracy_scores else 0
        
        # Production readiness assessment
        production_ready = (
            (api_success / len(self.test_results['api_tests'])) > 0.8 and
            (passed_tests / total_tests) > 0.85 and
            avg_response_time < 3.0 and
            avg_accuracy > 6.0
        )
        
        report = {
            'test_summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': total_tests - passed_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                'production_ready': production_ready
            },
            'performance_metrics': {
                'average_response_time': avg_response_time,
                'max_response_time': max_response_time,
                'min_response_time': min_response_time,
                'average_accuracy': avg_accuracy
            },
            'api_status': {
                'total_endpoints': len(self.test_results['api_tests']),
                'working_endpoints': api_success,
                'endpoint_success_rate': (api_success / len(self.test_results['api_tests']) * 100) if self.test_results['api_tests'] else 0
            },
            'government_data_status': {
                'msp_data_quality': sum(1 for test in self.test_results['government_data_tests'].get('msp_prices', {}).values() if test.get('has_data', False)),
                'schemes_data_quality': sum(1 for test in self.test_results['government_data_tests'].get('schemes_data', {}).values() if test.get('has_data', False))
            },
            'detailed_results': self.test_results,
            'timestamp': datetime.now().isoformat()
        }
        
        return report

    def run_complete_test_suite(self) -> Dict[str, Any]:
        """Run complete production test suite"""
        logger.info("🚀 Starting comprehensive production test suite...")
        logger.info("=" * 60)
        
        # Test server connectivity first
        if not self.test_server_connectivity():
            logger.error("❌ Server not accessible. Aborting tests.")
            return {'error': 'Server not accessible'}
        
        # Run all test categories
        logger.info("📡 Testing API endpoints...")
        self.test_api_endpoints()
        
        logger.info("🤖 Testing AI responsiveness...")
        self.test_ai_responsiveness()
        
        logger.info("🏛️ Testing government data integration...")
        self.test_government_data_integration()
        
        logger.info("📍 Testing location-based queries...")
        location_tests = self.test_location_based_queries()
        
        logger.info("⚡ Testing concurrent request handling...")
        concurrent_tests = self.test_concurrent_requests()
        
        # Add additional test results
        self.test_results['location_tests'] = location_tests
        self.test_results['concurrent_tests'] = concurrent_tests
        
        # Generate final report
        report = self.generate_test_report()
        
        logger.info("=" * 60)
        logger.info("🎯 PRODUCTION TEST RESULTS")
        logger.info("=" * 60)
        logger.info(f"✅ Tests Passed: {report['test_summary']['passed_tests']}/{report['test_summary']['total_tests']}")
        logger.info(f"📊 Success Rate: {report['test_summary']['success_rate']:.1f}%")
        logger.info(f"⚡ Avg Response Time: {report['performance_metrics']['average_response_time']:.2f}s")
        logger.info(f"🎯 Avg Accuracy: {report['performance_metrics']['average_accuracy']:.1f}/10")
        logger.info(f"🏛️ Government Data: MSP({report['government_data_status']['msp_data_quality']}), Schemes({report['government_data_status']['schemes_data_quality']})")
        logger.info(f"🚀 Production Ready: {'✅ YES' if report['test_summary']['production_ready'] else '❌ NO'}")
        logger.info("=" * 60)
        
        return report

def main():
    """Main function to run production tests"""
    print("🌾 Krishimitra AI - Production Dynamic Test Suite")
    print("=" * 60)
    
    # Initialize test suite
    test_suite = ProductionTestSuite()
    
    # Run complete test suite
    results = test_suite.run_complete_test_suite()
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"production_test_results_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"📄 Detailed results saved to: {filename}")
    
    return results

if __name__ == "__main__":
    main()
