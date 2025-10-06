#!/usr/bin/env python3
"""
Comprehensive Service Verification Script
Tests all services and components of KrishiMitra AI
"""

import requests
import json
import time
import sys
from datetime import datetime

class ServiceVerifier:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.results = {
            'passed': 0,
            'failed': 0,
            'errors': []
        }
    
    def log_result(self, test_name, success, error_msg=None):
        """Log test result"""
        if success:
            print(f"✅ {test_name}: PASSED")
            self.results['passed'] += 1
        else:
            print(f"❌ {test_name}: FAILED")
            if error_msg:
                print(f"   Error: {error_msg}")
            self.results['failed'] += 1
            self.results['errors'].append(f"{test_name}: {error_msg}")
    
    def test_server_connection(self):
        """Test if Django server is running"""
        try:
            response = requests.get(f"{self.base_url}/api/", timeout=5)
            success = response.status_code == 200
            self.log_result("Django Server Connection", success, 
                           f"Status code: {response.status_code}" if not success else None)
            return success
        except Exception as e:
            self.log_result("Django Server Connection", False, str(e))
            return False
    
    def test_weather_api(self):
        """Test weather API endpoint"""
        try:
            url = f"{self.base_url}/api/weather/current/"
            params = {'lat': 28.6139, 'lon': 77.2090, 'lang': 'hi'}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['temperature', 'humidity', 'wind_speed']
                has_required = all(field in data for field in required_fields)
                self.log_result("Weather API", has_required, 
                               "Missing required fields" if not has_required else None)
                return has_required
            else:
                self.log_result("Weather API", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Weather API", False, str(e))
            return False
    
    def test_market_prices_api(self):
        """Test market prices API endpoint"""
        try:
            url = f"{self.base_url}/api/market-prices/prices/"
            params = {'lat': 28.6139, 'lon': 77.2090, 'lang': 'hi', 'product': 'wheat'}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                is_list = isinstance(data, list)
                has_price = is_list and len(data) > 0 and 'price' in data[0]
                self.log_result("Market Prices API", has_price, 
                               "Invalid data format" if not has_price else None)
                return has_price
            else:
                self.log_result("Market Prices API", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Market Prices API", False, str(e))
            return False
    
    def test_chatbot_api(self):
        """Test chatbot API endpoint"""
        try:
            url = f"{self.base_url}/api/advisories/chatbot/"
            data = {
                'query': 'Hello, how are you?',
                'language': 'hi',
                'latitude': 28.6139,
                'longitude': 77.2090
            }
            response = requests.post(url, json=data, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                has_response = 'response' in data and data['response']
                self.log_result("Chatbot API", has_response, 
                               "No response generated" if not has_response else None)
                return has_response
            else:
                self.log_result("Chatbot API", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Chatbot API", False, str(e))
            return False
    
    def test_crop_recommendation_api(self):
        """Test crop recommendation API endpoint"""
        try:
            url = f"{self.base_url}/api/advisories/ml_crop_recommendation/"
            data = {
                'soil_type': 'loamy',
                'latitude': 28.6139,
                'longitude': 77.2090,
                'season': 'kharif'
            }
            response = requests.post(url, json=data, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                has_crops = 'recommended_crops' in data and len(data['recommended_crops']) > 0
                self.log_result("Crop Recommendation API", has_crops, 
                               "No crops recommended" if not has_crops else None)
                return has_crops
            else:
                self.log_result("Crop Recommendation API", False, f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Crop Recommendation API", False, str(e))
            return False
    
    def test_government_data_service(self):
        """Test government data service"""
        try:
            # Test ICAR crop recommendations
            url = f"{self.base_url}/api/government-data/icar-crops/"
            params = {'lat': 28.6139, 'lon': 77.2090}
            response = requests.get(url, params=params, timeout=10)
            
            success = response.status_code == 200
            self.log_result("Government Data Service (ICAR)", success, 
                           f"Status code: {response.status_code}" if not success else None)
            return success
        except Exception as e:
            self.log_result("Government Data Service (ICAR)", False, str(e))
            return False
    
    def test_location_service(self):
        """Test location service"""
        try:
            url = f"{self.base_url}/api/location/detect/"
            data = {'latitude': 28.6139, 'longitude': 77.2090}
            response = requests.post(url, json=data, timeout=10)
            
            success = response.status_code == 200
            self.log_result("Location Service", success, 
                           f"Status code: {response.status_code}" if not success else None)
            return success
        except Exception as e:
            self.log_result("Location Service", False, str(e))
            return False
    
    def test_frontend_accessibility(self):
        """Test if frontend is accessible"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            success = response.status_code == 200
            self.log_result("Frontend Accessibility", success, 
                           f"Status code: {response.status_code}" if not success else None)
            return success
        except Exception as e:
            self.log_result("Frontend Accessibility", False, str(e))
            return False
    
    def run_all_tests(self):
        """Run all verification tests"""
        print("🔍 Starting Comprehensive Service Verification")
        print("=" * 50)
        print(f"Testing against: {self.base_url}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        # Test server connection first
        if not self.test_server_connection():
            print("\n❌ Server not running. Please start Django server first:")
            print("   python manage.py runserver 8000")
            return False
        
        print("\n🧪 Running API Tests...")
        self.test_weather_api()
        self.test_market_prices_api()
        self.test_chatbot_api()
        self.test_crop_recommendation_api()
        self.test_government_data_service()
        self.test_location_service()
        self.test_frontend_accessibility()
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 VERIFICATION SUMMARY")
        print("=" * 50)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📈 Success Rate: {(self.results['passed'] / (self.results['passed'] + self.results['failed']) * 100):.1f}%")
        
        if self.results['errors']:
            print("\n🚨 ERRORS FOUND:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        print("\n" + "=" * 50)
        
        # Overall result
        if self.results['failed'] == 0:
            print("🎉 ALL SERVICES WORKING PERFECTLY!")
            return True
        else:
            print("⚠️  SOME SERVICES NEED ATTENTION")
            return False

def main():
    """Main function"""
    verifier = ServiceVerifier()
    success = verifier.run_all_tests()
    
    if success:
        print("\n✅ All services verified successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some services need fixing!")
        sys.exit(1)

if __name__ == "__main__":
    main()
