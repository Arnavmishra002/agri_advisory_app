#!/usr/bin/env python3
"""
Comprehensive Test Runner
Runs all tests with proper configuration and reporting
"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner
import unittest
import time
from datetime import datetime

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Import test modules
from .test_config import TestUtilities, TestDataFactory, PerformanceTestUtils
from .test_models import *
from .test_api import *
from .test_integration import *
from .test_services import *


class TestRunner:
    """Comprehensive test runner for Krishimitra AI"""
    
    def __init__(self):
        self.test_results = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'skipped': 0,
            'start_time': None,
            'end_time': None,
            'test_details': []
        }
    
    def run_all_tests(self):
        """Run all test suites"""
        print("🧪 KRISHIMITRA AI - COMPREHENSIVE TEST SUITE")
        print("=" * 60)
        
        self.test_results['start_time'] = datetime.now()
        
        # Test suites to run
        test_suites = [
            ('Model Tests', self.run_model_tests),
            ('API Tests', self.run_api_tests),
            ('Service Tests', self.run_service_tests),
            ('Integration Tests', self.run_integration_tests),
            ('Performance Tests', self.run_performance_tests)
        ]
        
        for suite_name, suite_func in test_suites:
            print(f"\n📋 Running {suite_name}...")
            print("-" * 40)
            
            try:
                suite_func()
                print(f"✅ {suite_name} completed successfully")
            except Exception as e:
                print(f"❌ {suite_name} failed: {e}")
                self.test_results['errors'] += 1
        
        self.test_results['end_time'] = datetime.now()
        self.print_summary()
        
        return self.test_results['failed'] == 0 and self.test_results['errors'] == 0
    
    def run_model_tests(self):
        """Run model tests"""
        from .test_models import (
            UserModelTests, CropModelTests, CropAdvisoryModelTests,
            UserFeedbackModelTests, MLModelPerformanceModelTests,
            UserSessionModelTests, ChatHistoryModelTests,
            ChatSessionModelTests, ForumPostModelTests
        )
        
        model_test_classes = [
            UserModelTests, CropModelTests, CropAdvisoryModelTests,
            UserFeedbackModelTests, MLModelPerformanceModelTests,
            UserSessionModelTests, ChatHistoryModelTests,
            ChatSessionModelTests, ForumPostModelTests
        ]
        
        for test_class in model_test_classes:
            suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
            runner = unittest.TextTestRunner(verbosity=0)
            result = runner.run(suite)
            
            self.test_results['total_tests'] += result.testsRun
            self.test_results['passed'] += result.testsRun - len(result.failures) - len(result.errors)
            self.test_results['failed'] += len(result.failures)
            self.test_results['errors'] += len(result.errors)
            
            # Store test details
            for failure in result.failures:
                self.test_results['test_details'].append({
                    'test': failure[0],
                    'status': 'FAILED',
                    'error': failure[1]
                })
            
            for error in result.errors:
                self.test_results['test_details'].append({
                    'test': error[0],
                    'status': 'ERROR',
                    'error': error[1]
                })
    
    def run_api_tests(self):
        """Run API tests"""
        from .test_api import (
            AuthenticationAPITests, ChatbotAPITests, CropRecommendationsAPITests,
            WeatherAPITests, MarketPricesAPITests, GovernmentSchemesAPITests,
            PestDetectionAPITests, LocationAPITests, CropSearchAPITests,
            HealthCheckAPITests, APIPerformanceTests
        )
        
        api_test_classes = [
            AuthenticationAPITests, ChatbotAPITests, CropRecommendationsAPITests,
            WeatherAPITests, MarketPricesAPITests, GovernmentSchemesAPITests,
            PestDetectionAPITests, LocationAPITests, CropSearchAPITests,
            HealthCheckAPITests, APIPerformanceTests
        ]
        
        for test_class in api_test_classes:
            suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
            runner = unittest.TextTestRunner(verbosity=0)
            result = runner.run(suite)
            
            self.test_results['total_tests'] += result.testsRun
            self.test_results['passed'] += result.testsRun - len(result.failures) - len(result.errors)
            self.test_results['failed'] += len(result.failures)
            self.test_results['errors'] += len(result.errors)
            
            # Store test details
            for failure in result.failures:
                self.test_results['test_details'].append({
                    'test': failure[0],
                    'status': 'FAILED',
                    'error': failure[1]
                })
            
            for error in result.errors:
                self.test_results['test_details'].append({
                    'test': error[0],
                    'status': 'ERROR',
                    'error': error[1]
                })
    
    def run_service_tests(self):
        """Run service tests"""
        from .test_services import (
            RealTimeGovernmentAITests, EnhancedGovernmentAPITests,
            ComprehensiveCropRecommendationsTests, OllamaIntegrationTests,
            GoogleAIStudioTests, EnhancedMultilingualTests, EnhancedClassifierTests
        )
        
        service_test_classes = [
            RealTimeGovernmentAITests, EnhancedGovernmentAPITests,
            ComprehensiveCropRecommendationsTests, OllamaIntegrationTests,
            GoogleAIStudioTests, EnhancedMultilingualTests, EnhancedClassifierTests
        ]
        
        for test_class in service_test_classes:
            suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
            runner = unittest.TextTestRunner(verbosity=0)
            result = runner.run(suite)
            
            self.test_results['total_tests'] += result.testsRun
            self.test_results['passed'] += result.testsRun - len(result.failures) - len(result.errors)
            self.test_results['failed'] += len(result.failures)
            self.test_results['errors'] += len(result.errors)
            
            # Store test details
            for failure in result.failures:
                self.test_results['test_details'].append({
                    'test': failure[0],
                    'status': 'FAILED',
                    'error': failure[1]
                })
            
            for error in result.errors:
                self.test_results['test_details'].append({
                    'test': error[0],
                    'status': 'ERROR',
                    'error': error[1]
                })
    
    def run_integration_tests(self):
        """Run integration tests"""
        from .test_integration import (
            ServiceIntegrationTests, APIToServiceIntegrationTests,
            DatabaseIntegrationTests, ExternalServiceIntegrationTests,
            PerformanceIntegrationTests, ErrorHandlingIntegrationTests
        )
        
        integration_test_classes = [
            ServiceIntegrationTests, APIToServiceIntegrationTests,
            DatabaseIntegrationTests, ExternalServiceIntegrationTests,
            PerformanceIntegrationTests, ErrorHandlingIntegrationTests
        ]
        
        for test_class in integration_test_classes:
            suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
            runner = unittest.TextTestRunner(verbosity=0)
            result = runner.run(suite)
            
            self.test_results['total_tests'] += result.testsRun
            self.test_results['passed'] += result.testsRun - len(result.failures) - len(result.errors)
            self.test_results['failed'] += len(result.failures)
            self.test_results['errors'] += len(result.errors)
            
            # Store test details
            for failure in result.failures:
                self.test_results['test_details'].append({
                    'test': failure[0],
                    'status': 'FAILED',
                    'error': failure[1]
                })
            
            for error in result.errors:
                self.test_results['test_details'].append({
                    'test': error[0],
                    'status': 'ERROR',
                    'error': error[1]
                })
    
    def run_performance_tests(self):
        """Run performance tests"""
        print("🚀 Running Performance Tests...")
        
        # Test API response times
        from django.test import Client
        from django.urls import reverse
        
        client = Client()
        
        # Test chatbot response time
        start_time = time.time()
        response = client.post('/api/chatbot/', {
            'query': 'Test performance query',
            'session_id': 'perf_test'
        }, content_type='application/json')
        end_time = time.time()
        
        chatbot_time = end_time - start_time
        print(f"   Chatbot API: {chatbot_time:.2f}s")
        
        if chatbot_time < 5.0:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
            self.test_results['test_details'].append({
                'test': 'Chatbot Performance Test',
                'status': 'FAILED',
                'error': f'Response time {chatbot_time:.2f}s exceeds 5s limit'
            })
        
        self.test_results['total_tests'] += 1
        
        # Test crop recommendations response time
        start_time = time.time()
        response = client.get('/api/realtime-gov/crop_recommendations/', {
            'location': 'Delhi',
            'latitude': 28.7041,
            'longitude': 77.1025
        })
        end_time = time.time()
        
        crop_time = end_time - start_time
        print(f"   Crop Recommendations API: {crop_time:.2f}s")
        
        if crop_time < 3.0:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
            self.test_results['test_details'].append({
                'test': 'Crop Recommendations Performance Test',
                'status': 'FAILED',
                'error': f'Response time {crop_time:.2f}s exceeds 3s limit'
            })
        
        self.test_results['total_tests'] += 1
    
    def print_summary(self):
        """Print test summary"""
        duration = self.test_results['end_time'] - self.test_results['start_time']
        
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        print(f"Total Tests: {self.test_results['total_tests']}")
        print(f"✅ Passed: {self.test_results['passed']}")
        print(f"❌ Failed: {self.test_results['failed']}")
        print(f"💥 Errors: {self.test_results['errors']}")
        print(f"⏱️  Duration: {duration.total_seconds():.2f}s")
        
        success_rate = (self.test_results['passed'] / self.test_results['total_tests'] * 100) if self.test_results['total_tests'] > 0 else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if self.test_results['failed'] > 0 or self.test_results['errors'] > 0:
            print("\n❌ FAILED TESTS:")
            print("-" * 40)
            
            for detail in self.test_results['test_details']:
                print(f"• {detail['test']}: {detail['status']}")
                if len(detail['error']) > 100:
                    print(f"  Error: {detail['error'][:100]}...")
                else:
                    print(f"  Error: {detail['error']}")
        
        print("\n" + "=" * 60)
        
        if self.test_results['failed'] == 0 and self.test_results['errors'] == 0:
            print("🎉 ALL TESTS PASSED! System is ready for deployment.")
        else:
            print("⚠️  Some tests failed. Please review and fix issues before deployment.")
        
        print("=" * 60)
    
    def generate_test_report(self, filename='test_report.html'):
        """Generate HTML test report"""
        duration = self.test_results['end_time'] - self.test_results['start_time']
        success_rate = (self.test_results['passed'] / self.test_results['total_tests'] * 100) if self.test_results['total_tests'] > 0 else 0
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Krishimitra AI - Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
                .summary {{ background-color: #ecf0f1; padding: 15px; margin: 20px 0; border-radius: 5px; }}
                .passed {{ color: #27ae60; }}
                .failed {{ color: #e74c3c; }}
                .error {{ color: #f39c12; }}
                .test-detail {{ margin: 10px 0; padding: 10px; border-left: 4px solid #3498db; background-color: #f8f9fa; }}
                .footer {{ margin-top: 30px; text-align: center; color: #7f8c8d; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🧪 Krishimitra AI - Test Report</h1>
                <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="summary">
                <h2>📊 Test Summary</h2>
                <p><strong>Total Tests:</strong> {self.test_results['total_tests']}</p>
                <p><strong class="passed">✅ Passed:</strong> {self.test_results['passed']}</p>
                <p><strong class="failed">❌ Failed:</strong> {self.test_results['failed']}</p>
                <p><strong class="error">💥 Errors:</strong> {self.test_results['errors']}</p>
                <p><strong>⏱️ Duration:</strong> {duration.total_seconds():.2f}s</p>
                <p><strong>📈 Success Rate:</strong> {success_rate:.1f}%</p>
            </div>
            
            <h2>📋 Test Details</h2>
        """
        
        for detail in self.test_results['test_details']:
            status_class = 'failed' if detail['status'] == 'FAILED' else 'error'
            html_content += f"""
            <div class="test-detail">
                <h3 class="{status_class}">{detail['test']}: {detail['status']}</h3>
                <pre>{detail['error']}</pre>
            </div>
            """
        
        html_content += """
            <div class="footer">
                <p>Krishimitra AI - Agricultural Advisory System</p>
                <p>Test Report Generated by Comprehensive Test Suite</p>
            </div>
        </body>
        </html>
        """
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"📄 Test report generated: {filename}")


def run_tests():
    """Main function to run all tests"""
    runner = TestRunner()
    success = runner.run_all_tests()
    
    # Generate test report
    runner.generate_test_report()
    
    return success


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)

