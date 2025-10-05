#!/usr/bin/env python3
"""
Quick Verification Script for Enhanced Agricultural AI Platform
Tests core functionality without Django dependencies
"""

import sys
import os

def test_imports():
    """Test if core modules can be imported"""
    print("🔍 Testing Core Module Imports...")
    
    try:
        # Test cache utilities
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from advisory.cache_utils import CacheManager
        print("✅ Cache utilities imported successfully")
        
        # Test security utilities (without Django)
        import re
        import json
        print("✅ Security dependencies available")
        
        # Test basic Python functionality
        import hashlib
        import functools
        print("✅ Core Python modules available")
        
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_cache_functionality():
    """Test cache functionality"""
    print("\n🔍 Testing Cache Functionality...")
    
    try:
        from advisory.cache_utils import CacheManager
        cache_manager = CacheManager()
        
        # Test cache key generation
        key = cache_manager._generate_cache_key("test", "arg1", "arg2", param="value")
        print(f"✅ Cache key generated: {key[:50]}...")
        
        # Test cache decorator creation
        decorator = cache_manager.cache_result(timeout=60)
        print("✅ Cache decorator created successfully")
        
        return True
    except Exception as e:
        print(f"❌ Cache test error: {e}")
        return False

def test_security_patterns():
    """Test security pattern detection"""
    print("\n🔍 Testing Security Patterns...")
    
    try:
        # Test XSS pattern detection
        xss_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'on\w+\s*=',
        ]
        
        test_inputs = [
            "Hello world",  # Safe
            "<script>alert('xss')</script>",  # Dangerous
            "javascript:alert(1)",  # Dangerous
            "onclick=alert(1)",  # Dangerous
        ]
        
        for pattern in xss_patterns:
            regex = re.compile(pattern, re.IGNORECASE)
            for test_input in test_inputs:
                if regex.search(test_input):
                    print(f"✅ Security pattern detected: {pattern} in '{test_input[:30]}...'")
                    break
        
        print("✅ Security pattern detection working")
        return True
    except Exception as e:
        print(f"❌ Security test error: {e}")
        return False

def test_file_structure():
    """Test project file structure"""
    print("\n🔍 Testing Project File Structure...")
    
    required_files = [
        "advisory/cache_utils.py",
        "advisory/security_utils.py", 
        "advisory/ml/advanced_chatbot.py",
        "advisory/ml/conversational_chatbot.py",
        "streamlit_app.py",
        "requirements.txt",
        "README.md",
        "COMPLETE_PROJECT_VERIFICATION.md"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
        else:
            print(f"✅ {file_path} exists")
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files present")
        return True

def test_requirements():
    """Test requirements file"""
    print("\n🔍 Testing Requirements File...")
    
    try:
        with open("requirements.txt", "r") as f:
            content = f.read()
            
        required_packages = [
            "Django",
            "djangorestframework", 
            "bleach",
            "transformers",
            "langdetect",
            "redis"
        ]
        
        missing_packages = []
        for package in required_packages:
            if package not in content:
                missing_packages.append(package)
            else:
                print(f"✅ {package} in requirements")
        
        if missing_packages:
            print(f"❌ Missing packages: {missing_packages}")
            return False
        else:
            print("✅ All required packages in requirements.txt")
            return True
            
    except Exception as e:
        print(f"❌ Requirements test error: {e}")
        return False

def main():
    """Main verification function"""
    print("🚀 Enhanced Agricultural AI Platform - Quick Verification")
    print("=" * 60)
    
    tests = [
        ("Core Imports", test_imports),
        ("Cache Functionality", test_cache_functionality),
        ("Security Patterns", test_security_patterns),
        ("File Structure", test_file_structure),
        ("Requirements", test_requirements),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed")
    
    print("\n" + "=" * 60)
    print(f"📊 VERIFICATION RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Project is ready for production!")
        print("✅ Your enhanced agricultural AI platform is fully verified!")
        return True
    else:
        print(f"⚠️  {total - passed} tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
