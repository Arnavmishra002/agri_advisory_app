#!/usr/bin/env python3
"""
Simple Test Runner for Krishimitra AI
Quick test execution script
"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def run_simple_tests():
    """Run a simple test suite"""
    print("🧪 Running Simple Test Suite for Krishimitra AI")
    print("=" * 50)
    
    # Run basic tests
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # Run tests for advisory app
    failures = test_runner.run_tests(['advisory.tests.test_models'])
    
    if failures:
        print(f"❌ {failures} test(s) failed")
        return False
    else:
        print("✅ All tests passed!")
        return True

def run_api_tests():
    """Run API tests"""
    print("🌐 Running API Tests")
    print("=" * 30)
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    failures = test_runner.run_tests(['advisory.tests.test_api'])
    
    if failures:
        print(f"❌ {failures} API test(s) failed")
        return False
    else:
        print("✅ All API tests passed!")
        return True

def run_all_tests():
    """Run all tests"""
    print("🚀 Running Complete Test Suite")
    print("=" * 40)
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    failures = test_runner.run_tests(['advisory.tests'])
    
    if failures:
        print(f"❌ {failures} test(s) failed")
        return False
    else:
        print("✅ All tests passed!")
        return True

if __name__ == '__main__':
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == 'models':
            success = run_simple_tests()
        elif test_type == 'api':
            success = run_api_tests()
        elif test_type == 'all':
            success = run_all_tests()
        else:
            print("Usage: python run_simple_tests.py [models|api|all]")
            sys.exit(1)
    else:
        success = run_simple_tests()
    
    sys.exit(0 if success else 1)





