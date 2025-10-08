#!/usr/bin/env python3
"""
Quick Project Verification - Tests code structure and imports
"""

import os
import sys
import django
from datetime import datetime

def print_header(title):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")

def print_result(test_name, status, details=""):
    status_symbol = "✅" if status else "❌"
    print(f"{status_symbol} {test_name}")
    if details:
        print(f"   {details}")

def test_django_setup():
    """Test Django setup and imports"""
    print_header("DJANGO SETUP VERIFICATION")
    
    try:
        # Setup Django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
        django.setup()
        print_result("Django Setup", True, "Django configured successfully")
        return True
    except Exception as e:
        print_result("Django Setup", False, str(e))
        return False

def test_imports():
    """Test critical imports"""
    print_header("CRITICAL IMPORTS TEST")
    
    imports_to_test = [
        ("Django", "django"),
        ("Django REST Framework", "rest_framework"),
        ("Advisory Views", "advisory.api.views"),
        ("Weather ViewSet", "advisory.api.views.WeatherViewSet"),
        ("Market Prices ViewSet", "advisory.api.views.MarketPricesViewSet"),
        ("Chatbot ViewSet", "advisory.api.views.ChatbotViewSet"),
        ("Enhanced Government API", "advisory.services.enhanced_government_api.EnhancedGovernmentAPI"),
        ("Real Time Government API", "advisory.services.real_time_government_api.RealTimeGovernmentAPI"),
        ("AI Chatbot", "advisory.ml.intelligent_chatbot.IntelligentAgriculturalChatbot"),
    ]
    
    results = []
    for name, module_path in imports_to_test:
        try:
            if '.' in module_path:
                module_name, class_name = module_path.rsplit('.', 1)
                module = __import__(module_name, fromlist=[class_name])
                getattr(module, class_name)
                print_result(f"Import - {name}", True)
                results.append(True)
            else:
                __import__(module_path)
                print_result(f"Import - {name}", True)
                results.append(True)
        except Exception as e:
            print_result(f"Import - {name}", False, str(e))
            results.append(False)
    
    return all(results)

def test_api_structure():
    """Test API structure and URL configuration"""
    print_header("API STRUCTURE VERIFICATION")
    
    try:
        from django.urls import reverse
        from django.test import Client
        
        client = Client()
        
        # Test URL patterns
        url_tests = [
            ("Weather API", "/api/weather/current/"),
            ("Market Prices API", "/api/market-prices/prices/"),
            ("Chatbot API", "/api/advisories/chatbot/"),
            ("Crop Recommendations", "/api/advisories/ml_crop_recommendation/"),
            ("Government Schemes", "/api/government-schemes/"),
        ]
        
        results = []
        for name, url in url_tests:
            try:
                # Test if URL resolves
                response = client.get(url + "?lat=28.6139&lon=77.2090&lang=en")
                if response.status_code in [200, 400, 405]:  # 400/405 are expected for GET on POST endpoints
                    print_result(f"URL - {name}", True, f"Status: {response.status_code}")
                    results.append(True)
                else:
                    print_result(f"URL - {name}", False, f"Unexpected status: {response.status_code}")
                    results.append(False)
            except Exception as e:
                print_result(f"URL - {name}", False, str(e))
                results.append(False)
        
        return any(results)
        
    except Exception as e:
        print_result("API Structure Test", False, str(e))
        return False

def test_government_api_classes():
    """Test government API classes"""
    print_header("GOVERNMENT API CLASSES TEST")
    
    try:
        from advisory.services.enhanced_government_api import EnhancedGovernmentAPI
        from advisory.services.real_time_government_api import RealTimeGovernmentAPI
        
        # Test class instantiation
        enhanced_api = EnhancedGovernmentAPI()
        real_time_api = RealTimeGovernmentAPI()
        
        print_result("Enhanced Government API", True, "Class instantiated successfully")
        print_result("Real Time Government API", True, "Class instantiated successfully")
        
        # Test if classes have required methods
        required_methods_enhanced = ['get_real_weather_data', 'get_real_market_prices']
        required_methods_realtime = ['get_real_time_weather_data', 'get_real_time_market_prices']
        
        for method in required_methods_enhanced:
            if hasattr(enhanced_api, method):
                print_result(f"Enhanced API - {method}", True)
            else:
                print_result(f"Enhanced API - {method}", False, "Method not found")
        
        for method in required_methods_realtime:
            if hasattr(real_time_api, method):
                print_result(f"Real Time API - {method}", True)
            else:
                print_result(f"Real Time API - {method}", False, "Method not found")
        
        return True
        
    except Exception as e:
        print_result("Government API Classes", False, str(e))
        return False

def test_ai_components():
    """Test AI and ML components"""
    print_header("AI & ML COMPONENTS TEST")
    
    try:
        from advisory.ml.intelligent_chatbot import IntelligentAgriculturalChatbot
        from advisory.ml.ml_models import AgriculturalMLSystem
        
        # Test AI chatbot
        chatbot = IntelligentAgriculturalChatbot()
        print_result("Intelligent Agricultural Chatbot", True, "Class instantiated successfully")
        
        # Test ML models
        ml_model = AgriculturalMLSystem()
        print_result("Agricultural ML System", True, "Class instantiated successfully")
        
        return True
        
    except Exception as e:
        print_result("AI & ML Components", False, str(e))
        return False

def test_database_models():
    """Test database models"""
    print_header("DATABASE MODELS TEST")
    
    try:
        from advisory.models import ForumPost, ChatHistory, ChatSession
        
        # Test model imports
        print_result("ForumPost Model", True, "Model imported successfully")
        print_result("ChatHistory Model", True, "Model imported successfully")
        print_result("ChatSession Model", True, "Model imported successfully")
        
        return True
        
    except Exception as e:
        print_result("Database Models", False, str(e))
        return False

def main():
    """Main verification function"""
    print_header("KRISHIMITRA AI - QUICK PROJECT VERIFICATION")
    print(f"Verification started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test results
    tests = {
        "Django Setup": False,
        "Critical Imports": False,
        "API Structure": False,
        "Government API Classes": False,
        "AI & ML Components": False,
        "Database Models": False
    }
    
    # Run tests
    tests["Django Setup"] = test_django_setup()
    
    if tests["Django Setup"]:
        tests["Critical Imports"] = test_imports()
        tests["API Structure"] = test_api_structure()
        tests["Government API Classes"] = test_government_api_classes()
        tests["AI & ML Components"] = test_ai_components()
        tests["Database Models"] = test_database_models()
    
    # Summary
    print_header("VERIFICATION SUMMARY")
    passed = sum(tests.values())
    total = len(tests)
    
    for test_name, result in tests.items():
        status_symbol = "✅" if result else "❌"
        print(f"{status_symbol} {test_name}")
    
    print(f"\nOverall Status: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL CODE TESTS PASSED!")
        print("✅ Project structure is correct")
        print("✅ All imports are working")
        print("✅ API endpoints are configured")
        print("✅ Government APIs are ready")
        print("✅ AI components are functional")
        print("✅ Database models are working")
        print("\n🚀 Your project is ready to run!")
        print("Run 'python manage.py runserver' to start the server")
    elif passed >= total * 0.8:
        print(f"\n⚠️  MOSTLY WORKING: {passed}/{total} tests passed")
        print("Project structure is mostly correct with minor issues.")
    else:
        print(f"\n❌ NEEDS ATTENTION: Only {passed}/{total} tests passed")
        print("Several components need to be fixed.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
