#!/usr/bin/env python3
"""
Comprehensive Verification Script for Krishimitra AI
Tests all components including frontend, backend, and AI services
"""

import os
import sys
import time
import requests
import json
from typing import Dict, List, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_server_connection():
    """Test if Django server is running"""
    try:
        response = requests.get('http://localhost:8000/', timeout=5)
        if response.status_code == 200:
            print("✅ Django server is running")
            return True
        else:
            print(f"❌ Django server returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Django server connection failed: {e}")
        return False

def test_api_endpoints():
    """Test all API endpoints"""
    endpoints = [
        ('/api/schema/swagger-ui/', 'API Documentation'),
        ('/api/advisories/chatbot/', 'Chatbot API'),
        ('/api/weather/current/', 'Weather API'),
        ('/api/market-prices/prices/', 'Market Prices API'),
        ('/admin/', 'Admin Panel')
    ]
    
    results = []
    for endpoint, name in endpoints:
        try:
            if endpoint == '/api/advisories/chatbot/':
                # Test POST endpoint
                response = requests.post(
                    f'http://localhost:8000{endpoint}',
                    json={'query': 'Hello', 'language': 'en'},
                    timeout=5
                )
            else:
                # Test GET endpoint
                response = requests.get(f'http://localhost:8000{endpoint}', timeout=5)
            
            if response.status_code in [200, 201]:
                print(f"✅ {name}: Working")
                results.append(True)
            else:
                print(f"❌ {name}: Status {response.status_code}")
                results.append(False)
        except requests.exceptions.RequestException as e:
            print(f"❌ {name}: Error - {e}")
            results.append(False)
    
    return all(results)

def test_ai_services():
    """Test AI services directly"""
    try:
        from advisory.ml.advanced_chatbot import AdvancedAgriculturalChatbot
        from advisory.services.weather_api import MockWeatherAPI
        from advisory.services.market_api import MarketPrices
        from advisory.services.enhanced_location_service import EnhancedLocationService
        
        print("🧪 Testing AI Services...")
        
        # Test Advanced Chatbot
        chatbot = AdvancedAgriculturalChatbot()
        response = chatbot.get_response("What crops should I plant?", "en")
        if response and 'response' in response:
            print("✅ Advanced Chatbot: Working")
        else:
            print("❌ Advanced Chatbot: Failed")
            return False
        
        # Test Weather API
        weather_api = MockWeatherAPI()
        weather_data = weather_api.get_current_weather(28.6139, 77.2090)
        if weather_data and 'temperature' in weather_data:
            print("✅ Weather API: Working")
        else:
            print("❌ Weather API: Failed")
            return False
        
        # Test Market API
        market_api = MarketPrices()
        market_data = market_api.get_market_prices(28.6139, 77.2090, 'wheat')
        if market_data and len(market_data) > 0:
            print("✅ Market API: Working")
        else:
            print("❌ Market API: Failed")
            return False
        
        # Test Location Service
        location_service = EnhancedLocationService()
        location_data = location_service.get_location_info("Delhi")
        if location_data and 'lat' in location_data:
            print("✅ Location Service: Working")
        else:
            print("❌ Location Service: Failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ AI Services test failed: {e}")
        return False

def test_frontend_features():
    """Test frontend features"""
    try:
        # Test if main page loads
        response = requests.get('http://localhost:8000/', timeout=5)
        if response.status_code == 200:
            content = response.text
            
            # Check for key frontend elements
            checks = [
                ('Krishimitra AI', 'Page title'),
                ('chatbot', 'Chatbot section'),
                ('location', 'Location features'),
                ('Bootstrap', 'CSS framework'),
                ('JavaScript', 'Interactive features')
            ]
            
            all_passed = True
            for check_text, check_name in checks:
                if check_text.lower() in content.lower():
                    print(f"✅ Frontend {check_name}: Present")
                else:
                    print(f"❌ Frontend {check_name}: Missing")
                    all_passed = False
            
            return all_passed
        else:
            print(f"❌ Frontend page failed to load: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Frontend test failed: {e}")
        return False

def test_database():
    """Test database connectivity"""
    try:
        import django
        from django.conf import settings
        from django.db import connection
        
        # Setup Django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        django.setup()
        
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result:
                print("✅ Database: Connected")
                return True
            else:
                print("❌ Database: Connection failed")
                return False
                
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def generate_report(results: Dict[str, bool]):
    """Generate verification report"""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_file = f"comprehensive_verification_report_{timestamp}.txt"
    
    with open(report_file, 'w') as f:
        f.write("KRISHIMITRA AI - COMPREHENSIVE VERIFICATION REPORT\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        total_tests = len(results)
        passed_tests = sum(results.values())
        success_rate = (passed_tests / total_tests) * 100
        
        f.write(f"OVERALL RESULTS:\n")
        f.write(f"Total Tests: {total_tests}\n")
        f.write(f"Passed: {passed_tests}\n")
        f.write(f"Failed: {total_tests - passed_tests}\n")
        f.write(f"Success Rate: {success_rate:.1f}%\n\n")
        
        f.write("DETAILED RESULTS:\n")
        f.write("-" * 30 + "\n")
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            f.write(f"{test_name}: {status}\n")
        
        f.write(f"\nSYSTEM STATUS: {'PRODUCTION READY!' if success_rate >= 90 else 'NEEDS ATTENTION'}\n")
    
    print(f"\n📊 Report saved: {report_file}")
    return report_file

def main():
    """Main verification function"""
    print("🔍 KRISHIMITRA AI - COMPREHENSIVE VERIFICATION")
    print("=" * 60)
    
    # Wait a moment for server to start
    print("⏳ Waiting for server to start...")
    time.sleep(3)
    
    # Run all tests
    results = {}
    
    print("\n🌐 Testing Server Connection...")
    results['Server Connection'] = test_server_connection()
    
    print("\n🔌 Testing API Endpoints...")
    results['API Endpoints'] = test_api_endpoints()
    
    print("\n🤖 Testing AI Services...")
    results['AI Services'] = test_ai_services()
    
    print("\n🎨 Testing Frontend...")
    results['Frontend Features'] = test_frontend_features()
    
    print("\n🗄️ Testing Database...")
    results['Database'] = test_database()
    
    # Generate report
    print("\n📊 Generating Report...")
    report_file = generate_report(results)
    
    # Summary
    total_tests = len(results)
    passed_tests = sum(results.values())
    success_rate = (passed_tests / total_tests) * 100
    
    print(f"\n🎉 VERIFICATION COMPLETED!")
    print("=" * 60)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("✅ SYSTEM STATUS: PRODUCTION READY!")
        print("🌐 Access your app at: http://localhost:8000")
        print("📚 API Docs at: http://localhost:8000/api/schema/swagger-ui/")
        print("⚙️ Admin Panel at: http://localhost:8000/admin/")
    else:
        print("⚠️ SYSTEM STATUS: NEEDS ATTENTION")
        print("Please check failed tests and fix issues.")
    
    return success_rate >= 90

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Verification cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
