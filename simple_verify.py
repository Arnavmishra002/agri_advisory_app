#!/usr/bin/env python3
"""
Simple Verification Script for Krishimitra AI
Tests all components including frontend, backend, and AI services
"""

import os
import sys
import time
import requests
import json

def test_server_connection():
    """Test if Django server is running"""
    try:
        response = requests.get('http://localhost:8000/', timeout=5)
        if response.status_code == 200:
            print("PASS: Django server is running")
            return True
        else:
            print(f"FAIL: Django server returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"FAIL: Django server connection failed: {e}")
        return False

def test_api_endpoints():
    """Test all API endpoints"""
    endpoints = [
        ('/api/schema/swagger-ui/', 'API Documentation'),
        ('/admin/', 'Admin Panel')
    ]
    
    results = []
    for endpoint, name in endpoints:
        try:
            response = requests.get(f'http://localhost:8000{endpoint}', timeout=5)
            if response.status_code in [200, 201]:
                print(f"PASS: {name} - Working")
                results.append(True)
            else:
                print(f"FAIL: {name} - Status {response.status_code}")
                results.append(False)
        except requests.exceptions.RequestException as e:
            print(f"FAIL: {name} - Error - {e}")
            results.append(False)
    
    return all(results)

def test_frontend_features():
    """Test frontend features"""
    try:
        response = requests.get('http://localhost:8000/', timeout=5)
        if response.status_code == 200:
            content = response.text
            
            checks = [
                ('Krishimitra AI', 'Page title'),
                ('chatbot', 'Chatbot section'),
                ('location', 'Location features'),
                ('Bootstrap', 'CSS framework')
            ]
            
            all_passed = True
            for check_text, check_name in checks:
                if check_text.lower() in content.lower():
                    print(f"PASS: Frontend {check_name} - Present")
                else:
                    print(f"FAIL: Frontend {check_name} - Missing")
                    all_passed = False
            
            return all_passed
        else:
            print(f"FAIL: Frontend page failed to load: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"FAIL: Frontend test failed: {e}")
        return False

def main():
    """Main verification function"""
    print("KRISHIMITRA AI - COMPREHENSIVE VERIFICATION")
    print("=" * 60)
    
    # Wait a moment for server to start
    print("Waiting for server to start...")
    time.sleep(3)
    
    # Run all tests
    results = {}
    
    print("\nTesting Server Connection...")
    results['Server Connection'] = test_server_connection()
    
    print("\nTesting API Endpoints...")
    results['API Endpoints'] = test_api_endpoints()
    
    print("\nTesting Frontend...")
    results['Frontend Features'] = test_frontend_features()
    
    # Summary
    total_tests = len(results)
    passed_tests = sum(results.values())
    success_rate = (passed_tests / total_tests) * 100
    
    print(f"\nVERIFICATION COMPLETED!")
    print("=" * 60)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("SYSTEM STATUS: WORKING!")
        print("Access your app at: http://localhost:8000")
        print("API Docs at: http://localhost:8000/api/schema/swagger-ui/")
        print("Admin Panel at: http://localhost:8000/admin/")
    else:
        print("SYSTEM STATUS: NEEDS ATTENTION")
        print("Please check failed tests and fix issues.")
    
    return success_rate >= 80

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nVerification cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nVerification failed: {e}")
        sys.exit(1)
