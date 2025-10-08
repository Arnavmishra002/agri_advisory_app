#!/usr/bin/env python3
"""
ULTIMATE COMPREHENSIVE TEST SUITE - NO LENIENCY
Tests ALL services with ZERO tolerance for failures
"""

import sys
import os
import json
import time
import requests
from datetime import datetime

sys.path.append('.')

from advisory.ml.ultimate_intelligent_ai import ultimate_ai

class UltimateTestSuite:
    def __init__(self):
        self.results = {
            'market_prices': {'passed': 0, 'failed': 0, 'details': []},
            'crop_recommendations': {'passed': 0, 'failed': 0, 'details': []},
            'weather_data': {'passed': 0, 'failed': 0, 'details': []},
            'ai_responsiveness': {'passed': 0, 'failed': 0, 'details': []},
            'location_accuracy': {'passed': 0, 'failed': 0, 'details': []},
            'government_data_sources': {'passed': 0, 'failed': 0, 'details': []},
            'dynamic_behavior': {'passed': 0, 'failed': 0, 'details': []},
            'api_integration': {'passed': 0, 'failed': 0, 'details': []}
        }
        
        self.test_locations = [
            {'name': 'Raebareli', 'coords': (26.2309, 81.2338), 'state': 'Uttar Pradesh'},
            {'name': 'Mumbai', 'coords': (19.0760, 72.8777), 'state': 'Maharashtra'},
            {'name': 'Bangalore', 'coords': (12.9716, 77.5946), 'state': 'Karnataka'},
            {'name': 'Chennai', 'coords': (13.0827, 80.2707), 'state': 'Tamil Nadu'},
            {'name': 'Lucknow', 'coords': (26.8467, 80.9462), 'state': 'Uttar Pradesh'},
            {'name': 'Hyderabad', 'coords': (17.3850, 78.4867), 'state': 'Telangana'},
            {'name': 'Kolkata', 'coords': (22.5726, 88.3639), 'state': 'West Bengal'},
            {'name': 'Pune', 'coords': (18.5204, 73.8567), 'state': 'Maharashtra'}
        ]
        
        self.test_crops = ['wheat', 'rice', 'potato', 'onion', 'tomato', 'cotton', 'sugarcane', 'maize', 'groundnut', 'chilli']
        
        self.test_queries = [
            'wheat price in raebareli',
            'crop recommendation for mumbai',
            'weather in bangalore',
            'potato price in chennai',
            'rice recommendation for lucknow',
            'weather forecast hyderabad',
            'onion price in kolkata',
            'tomato recommendation for pune',
            'cotton price in raebareli',
            'sugarcane recommendation for mumbai'
        ]

    def test_market_prices_comprehensive(self):
        """Test market prices with ZERO tolerance for failures"""
        print("\n💰 TESTING MARKET PRICES - ZERO TOLERANCE")
        print("=" * 60)
        
        for location in self.test_locations:
            for crop in self.test_crops[:5]:  # Test first 5 crops
                try:
                    query = f"{crop} price in {location['name']}"
                    response = ultimate_ai.get_response(
                        query, 
                        latitude=location['coords'][0], 
                        longitude=location['coords'][1], 
                        location_name=location['name']
                    )
                    
                    response_text = response['response']
                    
                    # STRICT CHECKS - NO LENIENCY
                    checks = {
                        'has_location': location['name'] in response_text,
                        'has_crop': crop.title() in response_text,
                        'has_price': '₹' in response_text and '/quintal' in response_text,
                        'has_mandi': 'Mandi' in response_text or 'APMC' in response_text,
                        'has_government_source': any(source in response_text for source in ['Agmarknet', 'e-NAM', 'FCI', 'Government API']),
                        'has_change': '%' in response_text,
                        'has_state': location['state'] in response_text,
                        'response_length': len(response_text) > 100
                    }
                    
                    all_passed = all(checks.values())
                    
                    if all_passed:
                        self.results['market_prices']['passed'] += 1
                        print(f"✅ {location['name']} - {crop}: PASSED")
                    else:
                        self.results['market_prices']['failed'] += 1
                        print(f"❌ {location['name']} - {crop}: FAILED")
                        for check, passed in checks.items():
                            if not passed:
                                print(f"   ❌ {check}: FAILED")
                    
                    self.results['market_prices']['details'].append({
                        'location': location['name'],
                        'crop': crop,
                        'checks': checks,
                        'passed': all_passed,
                        'response': response_text[:200] + '...'
                    })
                    
                except Exception as e:
                    self.results['market_prices']['failed'] += 1
                    print(f"❌ {location['name']} - {crop}: ERROR - {e}")

    def test_crop_recommendations_comprehensive(self):
        """Test crop recommendations with ZERO tolerance for failures"""
        print("\n🌱 TESTING CROP RECOMMENDATIONS - ZERO TOLERANCE")
        print("=" * 60)
        
        for location in self.test_locations:
            try:
                query = f"crop recommendation for {location['name']}"
                response = ultimate_ai.get_response(
                    query, 
                    latitude=location['coords'][0], 
                    longitude=location['coords'][1], 
                    location_name=location['name']
                )
                
                response_text = response['response']
                
                # STRICT CHECKS - NO LENIENCY
                checks = {
                    'has_location': location['name'] in response_text,
                    'has_highly_accurate': 'HIGHLY ACCURATE' in response_text,
                    'has_suitability_percentages': '% उपयुक्तता' in response_text or '% Suitability' in response_text,
                    'has_msp_prices': 'MSP: ₹' in response_text,
                    'has_yield_data': 'tons/hectare' in response_text,
                    'has_soil_type': any(soil in response_text for soil in ['Alluvial', 'Coastal', 'Red', 'Loamy']),
                    'has_climate': any(climate in response_text for climate in ['Sub-tropical', 'Tropical']),
                    'has_coordinates': '°N' in response_text and '°E' in response_text,
                    'has_government_source': any(source in response_text for source in ['ICAR', 'IMD', 'Government Agriculture Database']),
                    'response_length': len(response_text) > 500
                }
                
                all_passed = all(checks.values())
                
                if all_passed:
                    self.results['crop_recommendations']['passed'] += 1
                    print(f"✅ {location['name']}: PASSED")
                else:
                    self.results['crop_recommendations']['failed'] += 1
                    print(f"❌ {location['name']}: FAILED")
                    for check, passed in checks.items():
                        if not passed:
                            print(f"   ❌ {check}: FAILED")
                
                self.results['crop_recommendations']['details'].append({
                    'location': location['name'],
                    'checks': checks,
                    'passed': all_passed,
                    'response': response_text[:300] + '...'
                })
                
            except Exception as e:
                self.results['crop_recommendations']['failed'] += 1
                print(f"❌ {location['name']}: ERROR - {e}")

    def test_weather_data_comprehensive(self):
        """Test weather data with ZERO tolerance for failures"""
        print("\n🌤️ TESTING WEATHER DATA - ZERO TOLERANCE")
        print("=" * 60)
        
        for location in self.test_locations:
            try:
                query = f"weather in {location['name']}"
                response = ultimate_ai.get_response(
                    query, 
                    latitude=location['coords'][0], 
                    longitude=location['coords'][1], 
                    location_name=location['name']
                )
                
                response_text = response['response']
                
                # STRICT CHECKS - NO LENIENCY
                checks = {
                    'has_location': location['name'] in response_text,
                    'has_temperature': '°C' in response_text,
                    'has_humidity': '%' in response_text and ('नमी' in response_text or 'Humidity' in response_text),
                    'has_wind_speed': 'km/h' in response_text,
                    'has_weather_condition': any(condition in response_text for condition in ['Clear', 'Humid', 'Rainy', 'Cloudy']),
                    'has_agricultural_advice': any(advice in response_text for advice in ['कृषि', 'Agriculture', 'सुझाव', 'Suggestion']),
                    'has_government_source': any(source in response_text for source in ['IMD', 'भारतीय मौसम विभाग', 'Government IMD']),
                    'response_length': len(response_text) > 200
                }
                
                all_passed = all(checks.values())
                
                if all_passed:
                    self.results['weather_data']['passed'] += 1
                    print(f"✅ {location['name']}: PASSED")
                else:
                    self.results['weather_data']['failed'] += 1
                    print(f"❌ {location['name']}: FAILED")
                    for check, passed in checks.items():
                        if not passed:
                            print(f"   ❌ {check}: FAILED")
                
                self.results['weather_data']['details'].append({
                    'location': location['name'],
                    'checks': checks,
                    'passed': all_passed,
                    'response': response_text[:200] + '...'
                })
                
            except Exception as e:
                self.results['weather_data']['failed'] += 1
                print(f"❌ {location['name']}: ERROR - {e}")

    def test_ai_responsiveness_comprehensive(self):
        """Test AI responsiveness with ZERO tolerance for failures"""
        print("\n🤖 TESTING AI RESPONSIVENESS - ZERO TOLERANCE")
        print("=" * 60)
        
        complex_queries = [
            'wheat price and crop recommendation for raebareli',
            'weather and market prices in mumbai',
            'best crops for bangalore with prices',
            'agricultural advice for chennai farmers',
            'complete farming guide for lucknow',
            'weather forecast and crop suggestions for hyderabad',
            'market analysis and weather for kolkata',
            'farming recommendations for pune region'
        ]
        
        for query in complex_queries:
            try:
                response = ultimate_ai.get_response(query)
                response_text = response['response']
                
                # STRICT CHECKS - NO LENIENCY
                checks = {
                    'has_response': len(response_text) > 50,
                    'has_agricultural_content': any(keyword in response_text.lower() for keyword in ['crop', 'price', 'weather', 'agriculture', 'farming']),
                    'has_structured_format': any(char in response_text for char in ['🌱', '💰', '🌤️', '📊']),
                    'has_actionable_info': any(keyword in response_text for keyword in ['MSP', '₹', '°C', '%', 'tons/hectare']),
                    'has_government_source': any(source in response_text for source in ['Government', 'ICAR', 'IMD', 'Agmarknet']),
                    'response_time': response.get('timestamp') is not None,
                    'has_confidence': response.get('confidence', 0) > 0.8
                }
                
                all_passed = all(checks.values())
                
                if all_passed:
                    self.results['ai_responsiveness']['passed'] += 1
                    print(f"✅ Complex Query: PASSED")
                else:
                    self.results['ai_responsiveness']['failed'] += 1
                    print(f"❌ Complex Query: FAILED")
                    for check, passed in checks.items():
                        if not passed:
                            print(f"   ❌ {check}: FAILED")
                
                self.results['ai_responsiveness']['details'].append({
                    'query': query,
                    'checks': checks,
                    'passed': all_passed,
                    'response': response_text[:200] + '...'
                })
                
            except Exception as e:
                self.results['ai_responsiveness']['failed'] += 1
                print(f"❌ Complex Query: ERROR - {e}")

    def test_location_accuracy_comprehensive(self):
        """Test location accuracy with ZERO tolerance for failures"""
        print("\n📍 TESTING LOCATION ACCURACY - ZERO TOLERANCE")
        print("=" * 60)
        
        for location in self.test_locations:
            try:
                query = f"tell me about {location['name']}"
                response = ultimate_ai.get_response(
                    query, 
                    latitude=location['coords'][0], 
                    longitude=location['coords'][1], 
                    location_name=location['name']
                )
                
                response_text = response['response']
                
                # STRICT CHECKS - NO LENIENCY
                checks = {
                    'has_correct_location': location['name'] in response_text,
                    'has_state': location['state'] in response_text,
                    'has_coordinates': str(location['coords'][0])[:6] in response_text or str(location['coords'][1])[:6] in response_text,
                    'has_location_context': any(context in response_text for context in ['region', 'area', 'district', 'city']),
                    'response_length': len(response_text) > 100
                }
                
                all_passed = all(checks.values())
                
                if all_passed:
                    self.results['location_accuracy']['passed'] += 1
                    print(f"✅ {location['name']}: PASSED")
                else:
                    self.results['location_accuracy']['failed'] += 1
                    print(f"❌ {location['name']}: FAILED")
                    for check, passed in checks.items():
                        if not passed:
                            print(f"   ❌ {check}: FAILED")
                
                self.results['location_accuracy']['details'].append({
                    'location': location['name'],
                    'checks': checks,
                    'passed': all_passed,
                    'response': response_text[:200] + '...'
                })
                
            except Exception as e:
                self.results['location_accuracy']['failed'] += 1
                print(f"❌ {location['name']}: ERROR - {e}")

    def test_dynamic_behavior_comprehensive(self):
        """Test dynamic behavior with ZERO tolerance for failures"""
        print("\n🔄 TESTING DYNAMIC BEHAVIOR - ZERO TOLERANCE")
        print("=" * 60)
        
        # Test same query with different locations
        test_query = "wheat price"
        responses = []
        
        for location in self.test_locations[:4]:  # Test first 4 locations
            try:
                response = ultimate_ai.get_response(
                    test_query, 
                    latitude=location['coords'][0], 
                    longitude=location['coords'][1], 
                    location_name=location['name']
                )
                responses.append({
                    'location': location['name'],
                    'response': response['response'],
                    'coordinates': location['coords']
                })
            except Exception as e:
                print(f"❌ {location['name']}: ERROR - {e}")
                self.results['dynamic_behavior']['failed'] += 1
        
        # Check if responses are different (dynamic)
        if len(responses) >= 2:
            unique_responses = len(set(r['response'] for r in responses))
            total_responses = len(responses)
            
            # STRICT CHECK - All responses must be different
            if unique_responses == total_responses:
                self.results['dynamic_behavior']['passed'] += 1
                print(f"✅ Dynamic Behavior: PASSED - All {total_responses} responses are unique")
            else:
                self.results['dynamic_behavior']['failed'] += 1
                print(f"❌ Dynamic Behavior: FAILED - Only {unique_responses}/{total_responses} responses are unique")
        
        self.results['dynamic_behavior']['details'].append({
            'test': 'same_query_different_locations',
            'responses': responses,
            'unique_count': unique_responses if 'unique_responses' in locals() else 0
        })

    def test_api_integration_comprehensive(self):
        """Test API integration with ZERO tolerance for failures"""
        print("\n🔌 TESTING API INTEGRATION - ZERO TOLERANCE")
        print("=" * 60)
        
        # Test if server is running
        try:
            response = requests.get('http://127.0.0.1:8000/api/weather/current/?lat=28.6139&lon=77.2090&lang=hi', timeout=5)
            if response.status_code == 200:
                self.results['api_integration']['passed'] += 1
                print("✅ Weather API: PASSED")
            else:
                self.results['api_integration']['failed'] += 1
                print(f"❌ Weather API: FAILED - Status {response.status_code}")
        except Exception as e:
            self.results['api_integration']['failed'] += 1
            print(f"❌ Weather API: ERROR - {e}")
        
        # Test market prices API
        try:
            response = requests.get('http://127.0.0.1:8000/api/market-prices/prices/?lat=28.6139&lon=77.2090&lang=hi&product=wheat', timeout=5)
            if response.status_code == 200:
                self.results['api_integration']['passed'] += 1
                print("✅ Market Prices API: PASSED")
            else:
                self.results['api_integration']['failed'] += 1
                print(f"❌ Market Prices API: FAILED - Status {response.status_code}")
        except Exception as e:
            self.results['api_integration']['failed'] += 1
            print(f"❌ Market Prices API: ERROR - {e}")
        
        # Test crop recommendation API
        try:
            response = requests.post('http://127.0.0.1:8000/api/advisories/ml_crop_recommendation/', 
                                   json={'latitude': 28.6139, 'longitude': 77.2090, 'season': 'kharif'}, 
                                   timeout=5)
            if response.status_code == 200:
                self.results['api_integration']['passed'] += 1
                print("✅ Crop Recommendation API: PASSED")
            else:
                self.results['api_integration']['failed'] += 1
                print(f"❌ Crop Recommendation API: FAILED - Status {response.status_code}")
        except Exception as e:
            self.results['api_integration']['failed'] += 1
            print(f"❌ Crop Recommendation API: ERROR - {e}")

    def run_all_tests(self):
        """Run all tests with ZERO tolerance for failures"""
        print("🚀 ULTIMATE COMPREHENSIVE TEST SUITE - NO LENIENCY")
        print("=" * 80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run all tests
        self.test_market_prices_comprehensive()
        self.test_crop_recommendations_comprehensive()
        self.test_weather_data_comprehensive()
        self.test_ai_responsiveness_comprehensive()
        self.test_location_accuracy_comprehensive()
        self.test_dynamic_behavior_comprehensive()
        self.test_api_integration_comprehensive()
        
        # Generate final report
        self.generate_final_report()

    def generate_final_report(self):
        """Generate final report with ZERO tolerance for failures"""
        print("\n📊 ULTIMATE TEST RESULTS - NO LENIENCY")
        print("=" * 80)
        
        total_tests = 0
        total_passed = 0
        
        for test_type, result in self.results.items():
            total_tests += result['passed'] + result['failed']
            total_passed += result['passed']
            
            success_rate = (result['passed'] / (result['passed'] + result['failed']) * 100) if (result['passed'] + result['failed']) > 0 else 0
            
            print(f"\n{test_type.replace('_', ' ').title()}:")
            print(f"  ✅ Passed: {result['passed']}")
            print(f"  ❌ Failed: {result['failed']}")
            print(f"  📈 Success Rate: {success_rate:.1f}%")
            
            # ZERO TOLERANCE CHECK
            if result['failed'] > 0:
                print(f"  🚨 FAILURE DETECTED - {result['failed']} tests failed!")
        
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n🎯 OVERALL RESULTS:")
        print(f"  Total Tests: {total_tests}")
        print(f"  Total Passed: {total_passed}")
        print(f"  Total Failed: {total_tests - total_passed}")
        print(f"  Overall Success Rate: {overall_success_rate:.1f}%")
        
        # ZERO TOLERANCE FINAL VERDICT
        if overall_success_rate == 100.0:
            print(f"\n🎉 PERFECT! ALL TESTS PASSED - ZERO FAILURES!")
            print(f"✅ System is ready for production!")
        elif overall_success_rate >= 95.0:
            print(f"\n⚠️ NEAR PERFECT! {total_tests - total_passed} failures detected!")
            print(f"🔧 System needs minor fixes!")
        elif overall_success_rate >= 80.0:
            print(f"\n❌ UNACCEPTABLE! {total_tests - total_passed} failures detected!")
            print(f"🚨 System needs major fixes!")
        else:
            print(f"\n💥 CRITICAL FAILURE! {total_tests - total_passed} failures detected!")
            print(f"🔥 System is NOT ready for production!")
        
        # Save detailed results
        with open('ultimate_test_results.json', 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Detailed results saved to: ultimate_test_results.json")
        
        return overall_success_rate

if __name__ == "__main__":
    test_suite = UltimateTestSuite()
    success_rate = test_suite.run_all_tests()
    
    # Exit with error code if not 100% success
    if success_rate < 100.0:
        print(f"\n🚨 EXITING WITH ERROR CODE - SUCCESS RATE: {success_rate:.1f}%")
        sys.exit(1)
    else:
        print(f"\n✅ EXITING WITH SUCCESS - ALL TESTS PASSED!")
        sys.exit(0)
