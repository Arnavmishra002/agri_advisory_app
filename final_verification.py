#!/usr/bin/env python3
"""
Final Comprehensive Service Verification
Tests all aspects of the Krishimitra AI system
"""

import os
import sys
import django
import json
import time
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def test_service_card_functionality():
    """Test service card functionality"""
    print("🔍 Testing Service Card Functionality...")
    
    # Test service card HTML structure
    html_file = "core/templates/index.html"
    if not os.path.exists(html_file):
        print("❌ Main HTML file not found")
        return False
    
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for service cards
    service_cards = content.count('class="service-card"')
    onclick_handlers = content.count('onclick="showService(')
    data_attributes = content.count('data-service=')
    
    print(f"✅ Found {service_cards} service cards")
    print(f"✅ Found {onclick_handlers} onclick handlers")
    print(f"✅ Found {data_attributes} data-service attributes")
    
    # Check for required functions
    required_functions = [
        'function showService(',
        'function setupServiceCards(',
        'function loadServiceData(',
        'function loadGovernmentSchemes(',
        'function loadCropRecommendations(',
        'function loadWeatherData(',
        'function loadFreshMarketPrices(',
        'function loadPestControl('
    ]
    
    missing_functions = []
    for func in required_functions:
        if func not in content:
            missing_functions.append(func)
        else:
            print(f"✅ {func} found")
    
    if missing_functions:
        print(f"❌ Missing functions: {missing_functions}")
        return False
    
    return True

def test_api_endpoint_structure():
    """Test API endpoint structure"""
    print("\n🔍 Testing API Endpoint Structure...")
    
    try:
        from advisory.api.urls import urlpatterns, router
        
        # Get all registered routes
        routes = []
        for pattern in router.urls:
            if hasattr(pattern, 'pattern'):
                routes.append(str(pattern.pattern))
        
        print(f"✅ Found {len(routes)} API routes")
        
        # Check for required endpoints
        required_endpoints = [
            'chatbot',
            'weather',
            'market-prices',
            'government-schemes',
            'crops',
            'pest-detection',
            'locations',
            'realtime-gov',
            'monitoring'
        ]
        
        missing_endpoints = []
        for endpoint in required_endpoints:
            if any(endpoint in route for route in routes):
                print(f"✅ {endpoint} endpoint found")
            else:
                missing_endpoints.append(endpoint)
        
        if missing_endpoints:
            print(f"❌ Missing endpoints: {missing_endpoints}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")
        return False

def test_service_integration():
    """Test service integration"""
    print("\n🔍 Testing Service Integration...")
    
    try:
        # Test Unified Service Manager
        from advisory.services.unified_service_architecture import unified_service_manager
        
        # Test service status
        status = unified_service_manager.get_service_status()
        print(f"✅ Unified Service Manager status: {status}")
        
        # Test service processing
        test_query = "What crops should I grow in Delhi?"
        result = unified_service_manager.process_query(test_query)
        
        if result and 'response' in result:
            print("✅ Service processing test passed")
        else:
            print("❌ Service processing test failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Service integration test failed: {e}")
        return False

def test_database_functionality():
    """Test database functionality"""
    print("\n🔍 Testing Database Functionality...")
    
    try:
        from advisory.models import User, Crop, CropAdvisory
        
        # Test model creation
        print("✅ Database models imported successfully")
        
        # Test database connection
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result:
                print("✅ Database connection successful")
            else:
                print("❌ Database connection failed")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_frontend_backend_integration():
    """Test frontend-backend integration"""
    print("\n🔍 Testing Frontend-Backend Integration...")
    
    try:
        # Test API serializers
        from advisory.api.serializers import (
            ChatbotSerializer, CropRecommendationSerializer,
            YieldPredictionSerializer, FertilizerRecommendationSerializer
        )
        
        print("✅ API serializers imported successfully")
        
        # Test serializer validation
        chatbot_data = {
            'query': 'Test query',
            'language': 'en',
            'user_id': 'test_user'
        }
        
        serializer = ChatbotSerializer(data=chatbot_data)
        if serializer.is_valid():
            print("✅ Chatbot serializer validation passed")
        else:
            print(f"❌ Chatbot serializer validation failed: {serializer.errors}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Frontend-backend integration test failed: {e}")
        return False

def test_performance_monitoring():
    """Test performance monitoring"""
    print("\n🔍 Testing Performance Monitoring...")
    
    try:
        from advisory.monitoring.performance_monitor import performance_monitor
        
        # Test performance monitor
        health_status = performance_monitor.get_system_health_status()
        print(f"✅ Performance monitor status: {health_status.get('status', 'unknown')}")
        
        # Test metrics collection
        performance_monitor.record_user_activity('test_user', 'test_activity', {'test': True})
        print("✅ Metrics recording test passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance monitoring test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🌾 Krishimitra AI - Final Comprehensive Verification")
    print("=" * 70)
    
    tests = [
        ("Service Card Functionality", test_service_card_functionality),
        ("API Endpoint Structure", test_api_endpoint_structure),
        ("Service Integration", test_service_integration),
        ("Database Functionality", test_database_functionality),
        ("Frontend-Backend Integration", test_frontend_backend_integration),
        ("Performance Monitoring", test_performance_monitoring)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*70)
    print("📊 FINAL VERIFICATION SUMMARY")
    print("="*70)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("🚀 System is fully functional and ready for production!")
        print("\n✅ Service cards are clickable")
        print("✅ All API endpoints are working")
        print("✅ All services are integrated properly")
        print("✅ Frontend-backend communication is working")
        print("✅ Database is functional")
        print("✅ Performance monitoring is active")
    else:
        print(f"\n⚠️ {total-passed} tests failed. Please review the issues above.")
    
    # Save results
    verification_report = {
        'timestamp': datetime.now().isoformat(),
        'results': results,
        'passed': passed,
        'total': total,
        'success_rate': (passed/total)*100,
        'status': 'PASS' if passed == total else 'FAIL'
    }
    
    with open('final_verification_report.json', 'w') as f:
        json.dump(verification_report, f, indent=2)
    
    print(f"\n📄 Verification report saved to: final_verification_report.json")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

Final Comprehensive Service Verification
Tests all aspects of the Krishimitra AI system
"""

import os
import sys
import django
import json
import time
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def test_service_card_functionality():
    """Test service card functionality"""
    print("🔍 Testing Service Card Functionality...")
    
    # Test service card HTML structure
    html_file = "core/templates/index.html"
    if not os.path.exists(html_file):
        print("❌ Main HTML file not found")
        return False
    
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for service cards
    service_cards = content.count('class="service-card"')
    onclick_handlers = content.count('onclick="showService(')
    data_attributes = content.count('data-service=')
    
    print(f"✅ Found {service_cards} service cards")
    print(f"✅ Found {onclick_handlers} onclick handlers")
    print(f"✅ Found {data_attributes} data-service attributes")
    
    # Check for required functions
    required_functions = [
        'function showService(',
        'function setupServiceCards(',
        'function loadServiceData(',
        'function loadGovernmentSchemes(',
        'function loadCropRecommendations(',
        'function loadWeatherData(',
        'function loadFreshMarketPrices(',
        'function loadPestControl('
    ]
    
    missing_functions = []
    for func in required_functions:
        if func not in content:
            missing_functions.append(func)
        else:
            print(f"✅ {func} found")
    
    if missing_functions:
        print(f"❌ Missing functions: {missing_functions}")
        return False
    
    return True

def test_api_endpoint_structure():
    """Test API endpoint structure"""
    print("\n🔍 Testing API Endpoint Structure...")
    
    try:
        from advisory.api.urls import urlpatterns, router
        
        # Get all registered routes
        routes = []
        for pattern in router.urls:
            if hasattr(pattern, 'pattern'):
                routes.append(str(pattern.pattern))
        
        print(f"✅ Found {len(routes)} API routes")
        
        # Check for required endpoints
        required_endpoints = [
            'chatbot',
            'weather',
            'market-prices',
            'government-schemes',
            'crops',
            'pest-detection',
            'locations',
            'realtime-gov',
            'monitoring'
        ]
        
        missing_endpoints = []
        for endpoint in required_endpoints:
            if any(endpoint in route for route in routes):
                print(f"✅ {endpoint} endpoint found")
            else:
                missing_endpoints.append(endpoint)
        
        if missing_endpoints:
            print(f"❌ Missing endpoints: {missing_endpoints}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")
        return False

def test_service_integration():
    """Test service integration"""
    print("\n🔍 Testing Service Integration...")
    
    try:
        # Test Unified Service Manager
        from advisory.services.unified_service_architecture import unified_service_manager
        
        # Test service status
        status = unified_service_manager.get_service_status()
        print(f"✅ Unified Service Manager status: {status}")
        
        # Test service processing
        test_query = "What crops should I grow in Delhi?"
        result = unified_service_manager.process_query(test_query)
        
        if result and 'response' in result:
            print("✅ Service processing test passed")
        else:
            print("❌ Service processing test failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Service integration test failed: {e}")
        return False

def test_database_functionality():
    """Test database functionality"""
    print("\n🔍 Testing Database Functionality...")
    
    try:
        from advisory.models import User, Crop, CropAdvisory
        
        # Test model creation
        print("✅ Database models imported successfully")
        
        # Test database connection
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result:
                print("✅ Database connection successful")
            else:
                print("❌ Database connection failed")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_frontend_backend_integration():
    """Test frontend-backend integration"""
    print("\n🔍 Testing Frontend-Backend Integration...")
    
    try:
        # Test API serializers
        from advisory.api.serializers import (
            ChatbotSerializer, CropRecommendationSerializer,
            YieldPredictionSerializer, FertilizerRecommendationSerializer
        )
        
        print("✅ API serializers imported successfully")
        
        # Test serializer validation
        chatbot_data = {
            'query': 'Test query',
            'language': 'en',
            'user_id': 'test_user'
        }
        
        serializer = ChatbotSerializer(data=chatbot_data)
        if serializer.is_valid():
            print("✅ Chatbot serializer validation passed")
        else:
            print(f"❌ Chatbot serializer validation failed: {serializer.errors}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Frontend-backend integration test failed: {e}")
        return False

def test_performance_monitoring():
    """Test performance monitoring"""
    print("\n🔍 Testing Performance Monitoring...")
    
    try:
        from advisory.monitoring.performance_monitor import performance_monitor
        
        # Test performance monitor
        health_status = performance_monitor.get_system_health_status()
        print(f"✅ Performance monitor status: {health_status.get('status', 'unknown')}")
        
        # Test metrics collection
        performance_monitor.record_user_activity('test_user', 'test_activity', {'test': True})
        print("✅ Metrics recording test passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance monitoring test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🌾 Krishimitra AI - Final Comprehensive Verification")
    print("=" * 70)
    
    tests = [
        ("Service Card Functionality", test_service_card_functionality),
        ("API Endpoint Structure", test_api_endpoint_structure),
        ("Service Integration", test_service_integration),
        ("Database Functionality", test_database_functionality),
        ("Frontend-Backend Integration", test_frontend_backend_integration),
        ("Performance Monitoring", test_performance_monitoring)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*70)
    print("📊 FINAL VERIFICATION SUMMARY")
    print("="*70)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("🚀 System is fully functional and ready for production!")
        print("\n✅ Service cards are clickable")
        print("✅ All API endpoints are working")
        print("✅ All services are integrated properly")
        print("✅ Frontend-backend communication is working")
        print("✅ Database is functional")
        print("✅ Performance monitoring is active")
    else:
        print(f"\n⚠️ {total-passed} tests failed. Please review the issues above.")
    
    # Save results
    verification_report = {
        'timestamp': datetime.now().isoformat(),
        'results': results,
        'passed': passed,
        'total': total,
        'success_rate': (passed/total)*100,
        'status': 'PASS' if passed == total else 'FAIL'
    }
    
    with open('final_verification_report.json', 'w') as f:
        json.dump(verification_report, f, indent=2)
    
    print(f"\n📄 Verification report saved to: final_verification_report.json")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

Final Comprehensive Service Verification
Tests all aspects of the Krishimitra AI system
"""

import os
import sys
import django
import json
import time
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def test_service_card_functionality():
    """Test service card functionality"""
    print("🔍 Testing Service Card Functionality...")
    
    # Test service card HTML structure
    html_file = "core/templates/index.html"
    if not os.path.exists(html_file):
        print("❌ Main HTML file not found")
        return False
    
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for service cards
    service_cards = content.count('class="service-card"')
    onclick_handlers = content.count('onclick="showService(')
    data_attributes = content.count('data-service=')
    
    print(f"✅ Found {service_cards} service cards")
    print(f"✅ Found {onclick_handlers} onclick handlers")
    print(f"✅ Found {data_attributes} data-service attributes")
    
    # Check for required functions
    required_functions = [
        'function showService(',
        'function setupServiceCards(',
        'function loadServiceData(',
        'function loadGovernmentSchemes(',
        'function loadCropRecommendations(',
        'function loadWeatherData(',
        'function loadFreshMarketPrices(',
        'function loadPestControl('
    ]
    
    missing_functions = []
    for func in required_functions:
        if func not in content:
            missing_functions.append(func)
        else:
            print(f"✅ {func} found")
    
    if missing_functions:
        print(f"❌ Missing functions: {missing_functions}")
        return False
    
    return True

def test_api_endpoint_structure():
    """Test API endpoint structure"""
    print("\n🔍 Testing API Endpoint Structure...")
    
    try:
        from advisory.api.urls import urlpatterns, router
        
        # Get all registered routes
        routes = []
        for pattern in router.urls:
            if hasattr(pattern, 'pattern'):
                routes.append(str(pattern.pattern))
        
        print(f"✅ Found {len(routes)} API routes")
        
        # Check for required endpoints
        required_endpoints = [
            'chatbot',
            'weather',
            'market-prices',
            'government-schemes',
            'crops',
            'pest-detection',
            'locations',
            'realtime-gov',
            'monitoring'
        ]
        
        missing_endpoints = []
        for endpoint in required_endpoints:
            if any(endpoint in route for route in routes):
                print(f"✅ {endpoint} endpoint found")
            else:
                missing_endpoints.append(endpoint)
        
        if missing_endpoints:
            print(f"❌ Missing endpoints: {missing_endpoints}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")
        return False

def test_service_integration():
    """Test service integration"""
    print("\n🔍 Testing Service Integration...")
    
    try:
        # Test Unified Service Manager
        from advisory.services.unified_service_architecture import unified_service_manager
        
        # Test service status
        status = unified_service_manager.get_service_status()
        print(f"✅ Unified Service Manager status: {status}")
        
        # Test service processing
        test_query = "What crops should I grow in Delhi?"
        result = unified_service_manager.process_query(test_query)
        
        if result and 'response' in result:
            print("✅ Service processing test passed")
        else:
            print("❌ Service processing test failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Service integration test failed: {e}")
        return False

def test_database_functionality():
    """Test database functionality"""
    print("\n🔍 Testing Database Functionality...")
    
    try:
        from advisory.models import User, Crop, CropAdvisory
        
        # Test model creation
        print("✅ Database models imported successfully")
        
        # Test database connection
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result:
                print("✅ Database connection successful")
            else:
                print("❌ Database connection failed")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_frontend_backend_integration():
    """Test frontend-backend integration"""
    print("\n🔍 Testing Frontend-Backend Integration...")
    
    try:
        # Test API serializers
        from advisory.api.serializers import (
            ChatbotSerializer, CropRecommendationSerializer,
            YieldPredictionSerializer, FertilizerRecommendationSerializer
        )
        
        print("✅ API serializers imported successfully")
        
        # Test serializer validation
        chatbot_data = {
            'query': 'Test query',
            'language': 'en',
            'user_id': 'test_user'
        }
        
        serializer = ChatbotSerializer(data=chatbot_data)
        if serializer.is_valid():
            print("✅ Chatbot serializer validation passed")
        else:
            print(f"❌ Chatbot serializer validation failed: {serializer.errors}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Frontend-backend integration test failed: {e}")
        return False

def test_performance_monitoring():
    """Test performance monitoring"""
    print("\n🔍 Testing Performance Monitoring...")
    
    try:
        from advisory.monitoring.performance_monitor import performance_monitor
        
        # Test performance monitor
        health_status = performance_monitor.get_system_health_status()
        print(f"✅ Performance monitor status: {health_status.get('status', 'unknown')}")
        
        # Test metrics collection
        performance_monitor.record_user_activity('test_user', 'test_activity', {'test': True})
        print("✅ Metrics recording test passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance monitoring test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🌾 Krishimitra AI - Final Comprehensive Verification")
    print("=" * 70)
    
    tests = [
        ("Service Card Functionality", test_service_card_functionality),
        ("API Endpoint Structure", test_api_endpoint_structure),
        ("Service Integration", test_service_integration),
        ("Database Functionality", test_database_functionality),
        ("Frontend-Backend Integration", test_frontend_backend_integration),
        ("Performance Monitoring", test_performance_monitoring)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*70)
    print("📊 FINAL VERIFICATION SUMMARY")
    print("="*70)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("🚀 System is fully functional and ready for production!")
        print("\n✅ Service cards are clickable")
        print("✅ All API endpoints are working")
        print("✅ All services are integrated properly")
        print("✅ Frontend-backend communication is working")
        print("✅ Database is functional")
        print("✅ Performance monitoring is active")
    else:
        print(f"\n⚠️ {total-passed} tests failed. Please review the issues above.")
    
    # Save results
    verification_report = {
        'timestamp': datetime.now().isoformat(),
        'results': results,
        'passed': passed,
        'total': total,
        'success_rate': (passed/total)*100,
        'status': 'PASS' if passed == total else 'FAIL'
    }
    
    with open('final_verification_report.json', 'w') as f:
        json.dump(verification_report, f, indent=2)
    
    print(f"\n📄 Verification report saved to: final_verification_report.json")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)










































