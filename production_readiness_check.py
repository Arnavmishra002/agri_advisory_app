#!/usr/bin/env python3
"""
Production Readiness Check
Comprehensive check to ensure everything is ready for production
"""

import sys
import os
import time
import json
import requests
from datetime import datetime

# Add project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from advisory.ml.ultimate_intelligent_ai import ultimate_ai

class ProductionReadinessChecker:
    """Production Readiness Checker"""
    
    def __init__(self):
        self.production_url = "https://krishmitra-zrk4.onrender.com"
        self.issues_found = []
        self.recommendations = []
        self.ready_for_production = True
        
    def check_code_quality(self):
        """Check code quality and structure"""
        print("🔍 CHECKING CODE QUALITY")
        print("=" * 50)
        
        # Check for critical files
        critical_files = [
            'advisory/ml/ultimate_intelligent_ai.py',
            'advisory/services/enhanced_government_api.py',
            'advisory/services/general_apis.py',
            'advisory/api/views.py',
            'core/templates/index.html',
            'requirements-production.txt',
            'Procfile',
            'runtime.txt'
        ]
        
        missing_files = []
        for file in critical_files:
            if not os.path.exists(file):
                missing_files.append(file)
        
        if missing_files:
            self.issues_found.append(f"Missing critical files: {missing_files}")
            self.ready_for_production = False
            print(f"   ❌ Missing files: {missing_files}")
        else:
            print("   ✅ All critical files present")
        
        # Check for syntax errors in Python files
        python_files = [
            'advisory/ml/ultimate_intelligent_ai.py',
            'advisory/services/enhanced_government_api.py',
            'advisory/services/general_apis.py'
        ]
        
        syntax_errors = []
        for file in python_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    compile(f.read(), file, 'exec')
            except SyntaxError as e:
                syntax_errors.append(f"{file}: {e}")
        
        if syntax_errors:
            self.issues_found.append(f"Syntax errors found: {syntax_errors}")
            self.ready_for_production = False
            print(f"   ❌ Syntax errors: {syntax_errors}")
        else:
            print("   ✅ No syntax errors found")
    
    def check_dependencies(self):
        """Check dependencies and requirements"""
        print("\n📦 CHECKING DEPENDENCIES")
        print("=" * 50)
        
        # Check requirements-production.txt
        if os.path.exists('requirements-production.txt'):
            with open('requirements-production.txt', 'r') as f:
                requirements = f.read()
            
            # Check for problematic dependencies
            problematic_deps = ['threading>=1.0.0']  # threading is built-in
            found_problematic = []
            
            for dep in problematic_deps:
                if dep in requirements:
                    found_problematic.append(dep)
            
            if found_problematic:
                self.issues_found.append(f"Problematic dependencies: {found_problematic}")
                self.ready_for_production = False
                print(f"   ❌ Problematic dependencies: {found_problematic}")
            else:
                print("   ✅ No problematic dependencies found")
        else:
            self.issues_found.append("Missing requirements-production.txt")
            self.ready_for_production = False
            print("   ❌ Missing requirements-production.txt")
        
        # Check runtime.txt
        if os.path.exists('runtime.txt'):
            with open('runtime.txt', 'r') as f:
                runtime = f.read().strip()
            
            if 'python-3.11.0' in runtime:
                print("   ✅ Python runtime correctly specified")
            else:
                self.recommendations.append("Consider using Python 3.11.0 for better compatibility")
                print(f"   ⚠️  Python runtime: {runtime}")
        else:
            self.recommendations.append("Consider adding runtime.txt for Python version specification")
            print("   ⚠️  No runtime.txt found")
    
    def check_ai_functionality(self):
        """Check AI functionality"""
        print("\n🧠 CHECKING AI FUNCTIONALITY")
        print("=" * 50)
        
        test_queries = [
            {"query": "What crop should I grow in Delhi?", "language": "en"},
            {"query": "दिल्ली में कौन सी फसल उगाऊं?", "language": "hi"},
            {"query": "What is the price of wheat?", "language": "en"},
            {"query": "How to control pests in rice?", "language": "en"}
        ]
        
        successful_tests = 0
        total_tests = len(test_queries)
        
        for test in test_queries:
            try:
                response = ultimate_ai.get_response(
                    user_query=test['query'],
                    language=test['language'],
                    location_name='Delhi'
                )
                
                if response and response.get('response') and len(response['response']) > 50:
                    successful_tests += 1
                    print(f"   ✅ {test['language']}: {test['query'][:30]}...")
                else:
                    print(f"   ❌ {test['language']}: {test['query'][:30]}... - Poor response")
                    
            except Exception as e:
                print(f"   ❌ {test['language']}: {test['query'][:30]}... - Error: {e}")
        
        success_rate = (successful_tests / total_tests) * 100
        print(f"\n   📊 AI Success Rate: {success_rate:.1f}%")
        
        if success_rate < 75:
            self.issues_found.append(f"Low AI success rate: {success_rate:.1f}%")
            self.ready_for_production = False
        elif success_rate < 90:
            self.recommendations.append(f"AI success rate could be improved: {success_rate:.1f}%")
    
    def check_production_endpoints(self):
        """Check production endpoints"""
        print("\n🌐 CHECKING PRODUCTION ENDPOINTS")
        print("=" * 50)
        
        endpoints = [
            '/api/chatbot/chat/',
            '/api/market-prices/prices/',
            '/api/weather/current/',
            '/'
        ]
        
        working_endpoints = 0
        total_endpoints = len(endpoints)
        
        for endpoint in endpoints:
            try:
                url = f"{self.production_url}{endpoint}"
                response = requests.get(url, timeout=10)
                
                if response.status_code < 500:
                    working_endpoints += 1
                    print(f"   ✅ {endpoint}: {response.status_code}")
                else:
                    print(f"   ❌ {endpoint}: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"   ❌ {endpoint}: Connection error")
        
        endpoint_success_rate = (working_endpoints / total_endpoints) * 100
        print(f"\n   📊 Endpoint Success Rate: {endpoint_success_rate:.1f}%")
        
        if endpoint_success_rate < 50:
            self.issues_found.append(f"Low endpoint success rate: {endpoint_success_rate:.1f}%")
            self.ready_for_production = False
        elif endpoint_success_rate < 75:
            self.recommendations.append(f"Endpoint success rate could be improved: {endpoint_success_rate:.1f}%")
    
    def check_error_handling(self):
        """Check error handling mechanisms"""
        print("\n🛡️ CHECKING ERROR HANDLING")
        print("=" * 50)
        
        # Test error scenarios
        error_tests = [
            {"query": "", "language": "en"},  # Empty query
            {"query": "xyz123abc", "language": "en"},  # Random text
            {"query": "What crop should I grow?", "language": "invalid"},  # Invalid language
        ]
        
        error_handling_score = 0
        total_error_tests = len(error_tests)
        
        for test in error_tests:
            try:
                response = ultimate_ai.get_response(
                    user_query=test['query'],
                    language=test['language']
                )
                
                if response and response.get('response'):
                    error_handling_score += 1
                    print(f"   ✅ Error handled: {test['query'][:20] or 'empty'}")
                else:
                    print(f"   ❌ Error not handled: {test['query'][:20] or 'empty'}")
                    
            except Exception as e:
                print(f"   ❌ Exception not caught: {e}")
        
        error_handling_rate = (error_handling_score / total_error_tests) * 100
        print(f"\n   📊 Error Handling Rate: {error_handling_rate:.1f}%")
        
        if error_handling_rate < 66:
            self.issues_found.append(f"Poor error handling: {error_handling_rate:.1f}%")
            self.ready_for_production = False
        elif error_handling_rate < 100:
            self.recommendations.append(f"Error handling could be improved: {error_handling_rate:.1f}%")
    
    def check_performance(self):
        """Check performance metrics"""
        print("\n⚡ CHECKING PERFORMANCE")
        print("=" * 50)
        
        # Test response times
        test_queries = [
            "What crop should I grow in Delhi?",
            "What is the price of wheat?",
            "How to control pests in rice?"
        ]
        
        response_times = []
        
        for query in test_queries:
            try:
                start_time = time.time()
                response = ultimate_ai.get_response(
                    user_query=query,
                    language='en',
                    location_name='Delhi'
                )
                response_time = time.time() - start_time
                response_times.append(response_time)
                
                if response_time < 2:
                    print(f"   ✅ Fast response: {response_time:.2f}s")
                elif response_time < 5:
                    print(f"   ⚠️  Slow response: {response_time:.2f}s")
                else:
                    print(f"   ❌ Very slow response: {response_time:.2f}s")
                    
            except Exception as e:
                print(f"   ❌ Error during performance test: {e}")
        
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            print(f"\n   📊 Average Response Time: {avg_response_time:.2f}s")
            
            if avg_response_time > 3:
                self.issues_found.append(f"Slow average response time: {avg_response_time:.2f}s")
                self.ready_for_production = False
            elif avg_response_time > 1.5:
                self.recommendations.append(f"Response time could be improved: {avg_response_time:.2f}s")
    
    def generate_production_report(self):
        """Generate production readiness report"""
        print("\n📊 PRODUCTION READINESS REPORT")
        print("=" * 60)
        
        # Calculate overall score
        total_checks = 5
        passed_checks = total_checks - len(self.issues_found)
        readiness_score = (passed_checks / total_checks) * 100
        
        print(f"Overall Readiness Score: {readiness_score:.1f}%")
        print(f"Production Ready: {'✅ YES' if self.ready_for_production else '❌ NO'}")
        
        if self.issues_found:
            print(f"\n🚨 CRITICAL ISSUES ({len(self.issues_found)}):")
            for i, issue in enumerate(self.issues_found, 1):
                print(f"   {i}. {issue}")
        
        if self.recommendations:
            print(f"\n💡 RECOMMENDATIONS ({len(self.recommendations)}):")
            for i, rec in enumerate(self.recommendations, 1):
                print(f"   {i}. {rec}")
        
        # Generate final assessment
        if self.ready_for_production:
            if readiness_score >= 90:
                grade = "A+ (EXCELLENT)"
            elif readiness_score >= 80:
                grade = "A (VERY GOOD)"
            elif readiness_score >= 70:
                grade = "B (GOOD)"
            else:
                grade = "C (ACCEPTABLE)"
        else:
            grade = "D (NOT READY)"
        
        print(f"\n🎯 FINAL ASSESSMENT: {grade}")
        
        # Save report
        report = {
            'timestamp': datetime.now().isoformat(),
            'production_url': self.production_url,
            'readiness_score': readiness_score,
            'production_ready': self.ready_for_production,
            'grade': grade,
            'issues_found': self.issues_found,
            'recommendations': self.recommendations
        }
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f"production_readiness_report_{timestamp}.json"
        
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Report saved to: {report_filename}")
        
        return report
    
    def run_complete_check(self):
        """Run complete production readiness check"""
        print("🚀 PRODUCTION READINESS CHECK")
        print("=" * 80)
        print("Comprehensive check to ensure everything is ready for production")
        print("=" * 80)
        
        # Run all checks
        self.check_code_quality()
        self.check_dependencies()
        self.check_ai_functionality()
        self.check_production_endpoints()
        self.check_error_handling()
        self.check_performance()
        
        # Generate final report
        report = self.generate_production_report()
        
        return report

def main():
    """Main function"""
    checker = ProductionReadinessChecker()
    return checker.run_complete_check()

if __name__ == "__main__":
    main()

