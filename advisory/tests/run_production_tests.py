#!/usr/bin/env python3
"""
Production-Ready Test Runner
Runs comprehensive production tests for all services
"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def run_tests():
    """Run all production tests"""
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # Test modules to run
    test_modules = [
        'advisory.tests.test_production_services',
        'advisory.tests.test_government_api_integration',
        'advisory.tests.test_ai_accuracy',
        'advisory.tests.test_frontend_integration',
        'advisory.tests.test_api',
        'advisory.tests.test_services',
    ]
    
    print("=" * 80)
    print("PRODUCTION-READY COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print("\nRunning tests for:")
    for module in test_modules:
        print(f"  - {module}")
    print("\n" + "=" * 80 + "\n")
    
    # Run tests
    failures = test_runner.run_tests(test_modules)
    
    if failures:
        print("\n" + "=" * 80)
        print("❌ SOME TESTS FAILED")
        print("=" * 80)
        sys.exit(1)
    else:
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        sys.exit(0)


if __name__ == '__main__':
    run_tests()


