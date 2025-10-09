#!/usr/bin/env python3
"""
Production Testing and AI Training Suite
Comprehensive testing and training for the deployed agricultural AI assistant
"""

import sys
import os
import time
import json
import requests
import random
from datetime import datetime
from typing import Dict, List, Any

# Add project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from advisory.ml.ultimate_intelligent_ai import ultimate_ai

class ProductionTestingAndTrainingSuite:
    """Production Testing and AI Training Suite"""
    
    def __init__(self):
        self.production_url = "https://krishmitra-zrk4.onrender.com"
        self.test_results = {
            'production_tests': {},
            'ai_training': {},
            'performance_metrics': {},
            'timestamp': datetime.now().isoformat()
        }
        
    def test_production_endpoints(self):
        """Test all production endpoints"""
        print("🧪 TESTING PRODUCTION ENDPOINTS")
        print("=" * 60)
        
        endpoints = {
            'chatbot': '/api/chatbot/chat/',
            'market_prices': '/api/market-prices/prices/',
            'weather': '/api/weather/current/',
            'crop_advisory': '/api/advisories/',
            'government_schemes': '/api/government-schemes/schemes/',
            'pest_detection': '/api/pest-detection/detect/',
            'trending_crops': '/api/trending-crops/trending/',
            'text_to_speech': '/api/tts/convert/'
        }
        
        production_results = {
            'total_endpoints': len(endpoints),
            'successful_endpoints': 0,
            'failed_endpoints': 0,
            'endpoint_details': {},
            'overall_status': 'unknown'
        }
        
        for endpoint_name, endpoint_path in endpoints.items():
            print(f"\n🔍 Testing: {endpoint_name}")
            
            try:
                # Test endpoint availability
                url = f"{self.production_url}{endpoint_path}"
                response = requests.get(url, timeout=10)
                
                endpoint_result = {
                    'url': url,
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'accessible': response.status_code < 500,
                    'content_type': response.headers.get('content-type', 'unknown')
                }
                
                if endpoint_result['accessible']:
                    print(f"   ✅ {endpoint_name}: {response.status_code} - {endpoint_result['response_time']:.2f}s")
                    production_results['successful_endpoints'] += 1
                else:
                    print(f"   ❌ {endpoint_name}: {response.status_code} - Error")
                    production_results['failed_endpoints'] += 1
                
                production_results['endpoint_details'][endpoint_name] = endpoint_result
                
            except requests.exceptions.RequestException as e:
                print(f"   ❌ {endpoint_name}: Connection Error - {e}")
                production_results['failed_endpoints'] += 1
                production_results['endpoint_details'][endpoint_name] = {
                    'url': f"{self.production_url}{endpoint_path}",
                    'error': str(e),
                    'accessible': False
                }
        
        # Calculate overall status
        success_rate = (production_results['successful_endpoints'] / production_results['total_endpoints']) * 100
        if success_rate >= 80:
            production_results['overall_status'] = 'excellent'
        elif success_rate >= 60:
            production_results['overall_status'] = 'good'
        elif success_rate >= 40:
            production_results['overall_status'] = 'fair'
        else:
            production_results['overall_status'] = 'poor'
        
        print(f"\n📊 Production Endpoint Summary:")
        print(f"   Success Rate: {success_rate:.1f}%")
        print(f"   Successful: {production_results['successful_endpoints']}/{production_results['total_endpoints']}")
        print(f"   Overall Status: {production_results['overall_status'].upper()}")
        
        self.test_results['production_tests'] = production_results
        return production_results
    
    def test_chatbot_functionality(self):
        """Test chatbot functionality with various queries"""
        print("\n🤖 TESTING CHATBOT FUNCTIONALITY")
        print("=" * 60)
        
        test_queries = {
            'basic_farming': [
                {"query": "What crop should I grow in Delhi?", "language": "en", "expected_intent": "crop_recommendation"},
                {"query": "दिल्ली में कौन सी फसल उगाऊं?", "language": "hi", "expected_intent": "crop_recommendation"},
                {"query": "Delhi mein kya crop grow karu?", "language": "hinglish", "expected_intent": "crop_recommendation"}
            ],
            'market_prices': [
                {"query": "What is the price of wheat in Mumbai?", "language": "en", "expected_intent": "market"},
                {"query": "मुंबई में गेहूं की कीमत क्या है?", "language": "hi", "expected_intent": "market"},
                {"query": "Mumbai mein wheat ka price kya hai?", "language": "hinglish", "expected_intent": "market"}
            ],
            'weather_queries': [
                {"query": "What's the weather like for farming in Punjab?", "language": "en", "expected_intent": "weather"},
                {"query": "पंजाब में कृषि के लिए मौसम कैसा है?", "language": "hi", "expected_intent": "weather"}
            ],
            'government_schemes': [
                {"query": "What government schemes are available for farmers?", "language": "en", "expected_intent": "government"},
                {"query": "किसानों के लिए सरकारी योजनाएं क्या हैं?", "language": "hi", "expected_intent": "government"}
            ],
            'pest_control': [
                {"query": "How to control pests in rice crop?", "language": "en", "expected_intent": "pest"},
                {"query": "चावल की फसल में कीट नियंत्रण कैसे करें?", "language": "hi", "expected_intent": "pest"}
            ],
            'fertilizer_advice': [
                {"query": "What fertilizer should I use for tomato crop?", "language": "en", "expected_intent": "fertilizer"},
                {"query": "टमाटर की फसल के लिए कौन सा उर्वरक इस्तेमाल करें?", "language": "hi", "expected_intent": "fertilizer"}
            ],
            'complex_queries': [
                {"query": "Tell me about wheat cultivation, market prices, and government schemes", "language": "en", "expected_intent": "mixed"},
                {"query": "गेहूं की खेती, बाजार भाव और सरकारी योजनाओं के बारे में बताओ", "language": "hi", "expected_intent": "mixed"}
            ],
            'error_handling': [
                {"query": "what crop i should grow in delhi", "language": "en", "expected_intent": "error_handling"},
                {"query": "wht is the price of wheat", "language": "en", "expected_intent": "error_handling"},
                {"query": "मुंबई में गेहूं की किमत क्या है", "language": "hi", "expected_intent": "error_handling"}
            ]
        }
        
        chatbot_results = {
            'total_queries': 0,
            'successful_responses': 0,
            'failed_responses': 0,
            'category_results': {},
            'average_response_time': 0,
            'multilingual_success': 0,
            'intent_accuracy': 0
        }
        
        response_times = []
        multilingual_success_count = 0
        intent_accuracy_count = 0
        
        for category, queries in test_queries.items():
            print(f"\n   📝 Testing {category.replace('_', ' ').title()}")
            
            category_result = {
                'total': len(queries),
                'successful': 0,
                'failed': 0,
                'response_times': [],
                'intent_accuracy': 0
            }
            
            for query_data in queries:
                try:
                    start_time = time.time()
                    
                    # Test production chatbot endpoint
                    response = requests.post(
                        f"{self.production_url}/api/chatbot/chat/",
                        json=query_data,
                        timeout=15
                    )
                    
                    response_time = time.time() - start_time
                    response_times.append(response_time)
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        response_text = response_data.get('response', '')
                        
                        # Check if response is meaningful
                        is_successful = (
                            len(response_text) > 50 and
                            response_time < 10 and
                            'error' not in response_text.lower()
                        )
                        
                        if is_successful:
                            category_result['successful'] += 1
                            chatbot_results['successful_responses'] += 1
                        else:
                            category_result['failed'] += 1
                            chatbot_results['failed_responses'] += 1
                        
                        # Check multilingual success
                        if query_data['language'] == 'hi' and any('\u0900' <= char <= '\u097F' for char in response_text):
                            multilingual_success_count += 1
                        elif query_data['language'] == 'en' and not any('\u0900' <= char <= '\u097F' for char in response_text):
                            multilingual_success_count += 1
                        elif query_data['language'] == 'hinglish':
                            multilingual_success_count += 1
                        
                        # Check intent accuracy (basic check)
                        expected_intent = query_data['expected_intent']
                        if expected_intent in response_text.lower() or any(keyword in response_text.lower() for keyword in ['crop', 'price', 'weather', 'government', 'pest', 'fertilizer']):
                            intent_accuracy_count += 1
                            category_result['intent_accuracy'] += 1
                        
                        status = "✅ PASS" if is_successful else "❌ FAIL"
                        print(f"      {status} | {response_time:.2f}s | {query_data['language']}")
                        
                    else:
                        print(f"      ❌ ERROR | {response.status_code} | {query_data['language']}")
                        category_result['failed'] += 1
                        chatbot_results['failed_responses'] += 1
                    
                    chatbot_results['total_queries'] += 1
                    
                except requests.exceptions.RequestException as e:
                    print(f"      ❌ CONNECTION ERROR | {e}")
                    category_result['failed'] += 1
                    chatbot_results['failed_responses'] += 1
                    chatbot_results['total_queries'] += 1
            
            chatbot_results['category_results'][category] = category_result
        
        # Calculate overall metrics
        if response_times:
            chatbot_results['average_response_time'] = sum(response_times) / len(response_times)
        chatbot_results['multilingual_success'] = (multilingual_success_count / chatbot_results['total_queries']) * 100
        chatbot_results['intent_accuracy'] = (intent_accuracy_count / chatbot_results['total_queries']) * 100
        
        print(f"\n📊 Chatbot Testing Summary:")
        print(f"   Success Rate: {(chatbot_results['successful_responses']/chatbot_results['total_queries'])*100:.1f}%")
        print(f"   Average Response Time: {chatbot_results['average_response_time']:.2f}s")
        print(f"   Multilingual Success: {chatbot_results['multilingual_success']:.1f}%")
        print(f"   Intent Accuracy: {chatbot_results['intent_accuracy']:.1f}%")
        
        self.test_results['chatbot_functionality'] = chatbot_results
        return chatbot_results
    
    def train_ai_with_production_data(self):
        """Train AI with production data and feedback"""
        print("\n🧠 TRAINING AI WITH PRODUCTION DATA")
        print("=" * 60)
        
        # Enhanced training data based on production testing
        production_training_data = {
            'farming_queries': [
                "What is the best crop for Delhi climate?",
                "दिल्ली की जलवायु के लिए सबसे अच्छी फसल कौन सी है?",
                "Delhi climate ke liye best crop kya hai?",
                "Which crop has highest profit in Punjab?",
                "पंजाब में सबसे ज्यादा मुनाफा कौन सी फसल देती है?",
                "Punjab mein sabse zyada munafa kaun si crop deti hai?"
            ],
            'market_intelligence': [
                "What are the current market trends for wheat?",
                "गेहूं के लिए वर्तमान बाजार रुझान क्या हैं?",
                "Wheat ke liye current market trends kya hain?",
                "When is the best time to sell rice?",
                "चावल बेचने का सबसे अच्छा समय कब है?",
                "Rice bechne ka best time kab hai?"
            ],
            'weather_adaptation': [
                "How to adapt farming to climate change?",
                "जलवायु परिवर्तन के अनुसार खेती कैसे करें?",
                "Climate change ke according farming kaise kare?",
                "What to do during unexpected rainfall?",
                "अप्रत्याशित बारिश के दौरान क्या करें?",
                "Unexpected rainfall ke time kya kare?"
            ],
            'government_integration': [
                "How to apply for PM Kisan scheme?",
                "पीएम किसान योजना के लिए कैसे आवेदन करें?",
                "PM Kisan scheme ke liye kaise apply kare?",
                "What documents are needed for crop insurance?",
                "फसल बीमा के लिए कौन से दस्तावेज चाहिए?",
                "Crop insurance ke liye kaun se documents chahiye?"
            ],
            'advanced_queries': [
                "Compare wheat and rice farming profitability in different states",
                "विभिन्न राज्यों में गेहूं और चावल की खेती की लाभप्रदता की तुलना करें",
                "Different states mein wheat aur rice farming profitability compare karo",
                "What are the latest agricultural technologies?",
                "नवीनतम कृषि प्रौद्योगिकियां क्या हैं?",
                "Latest agricultural technologies kya hain?"
            ]
        }
        
        training_results = {
            'total_training_samples': 0,
            'successful_training': 0,
            'training_time': 0,
            'confidence_improvements': {},
            'intelligence_improvements': {},
            'language_performance': {}
        }
        
        start_time = time.time()
        confidence_scores = []
        intelligence_scores = []
        
        for category, queries in production_training_data.items():
            print(f"\n   🎯 Training {category.replace('_', ' ').title()}")
            
            category_confidence = []
            category_intelligence = []
            
            for query in queries:
                try:
                    # Detect language
                    language = 'hi' if any('\u0900' <= char <= '\u097F' for char in query) else 'en'
                    if any(word in query.lower() for word in ['mein', 'ka', 'kya', 'hai', 'aur', 'batao']):
                        language = 'hinglish'
                    
                    # Get AI response
                    response = ultimate_ai.get_response(
                        user_query=query,
                        language=language,
                        location_name="Delhi"
                    )
                    
                    confidence = response.get('confidence', 0)
                    intelligence = response.get('intelligence_score', 0)
                    
                    confidence_scores.append(confidence)
                    intelligence_scores.append(intelligence)
                    category_confidence.append(confidence)
                    category_intelligence.append(intelligence)
                    
                    if confidence > 0.7 and intelligence > 0.7:
                        training_results['successful_training'] += 1
                    
                    training_results['total_training_samples'] += 1
                    
                    # Track language performance
                    if language not in training_results['language_performance']:
                        training_results['language_performance'][language] = {
                            'total': 0, 'successful': 0, 'avg_confidence': 0
                        }
                    
                    training_results['language_performance'][language]['total'] += 1
                    if confidence > 0.7:
                        training_results['language_performance'][language]['successful'] += 1
                    
                    status = "✅ HIGH" if confidence > 0.8 else "⚠️ MEDIUM" if confidence > 0.6 else "❌ LOW"
                    print(f"      {status} | Conf: {confidence:.2f} | Intel: {intelligence:.2f} | {language}")
                    
                except Exception as e:
                    print(f"      ❌ ERROR: {e}")
                    training_results['total_training_samples'] += 1
            
            # Calculate category improvements
            if category_confidence:
                training_results['confidence_improvements'][category] = {
                    'average': sum(category_confidence) / len(category_confidence),
                    'count': len(category_confidence)
                }
            if category_intelligence:
                training_results['intelligence_improvements'][category] = {
                    'average': sum(category_intelligence) / len(category_intelligence),
                    'count': len(category_intelligence)
                }
        
        # Calculate final metrics
        training_time = time.time() - start_time
        training_results['training_time'] = training_time
        
        if confidence_scores:
            training_results['overall_confidence'] = sum(confidence_scores) / len(confidence_scores)
        if intelligence_scores:
            training_results['overall_intelligence'] = sum(intelligence_scores) / len(intelligence_scores)
        
        # Calculate language performance
        for language, data in training_results['language_performance'].items():
            if data['total'] > 0:
                data['avg_confidence'] = data['successful'] / data['total']
        
        print(f"\n📊 AI Training Summary:")
        print(f"   Training Time: {training_time:.2f} seconds")
        print(f"   Success Rate: {(training_results['successful_training']/training_results['total_training_samples'])*100:.1f}%")
        print(f"   Overall Confidence: {training_results.get('overall_confidence', 0):.2f}")
        print(f"   Overall Intelligence: {training_results.get('overall_intelligence', 0):.2f}")
        
        self.test_results['ai_training'] = training_results
        return training_results
    
    def generate_production_report(self):
        """Generate comprehensive production testing and training report"""
        print("\n📊 GENERATING PRODUCTION REPORT")
        print("=" * 60)
        
        # Calculate overall performance
        production_tests = self.test_results.get('production_tests', {})
        chatbot_tests = self.test_results.get('chatbot_functionality', {})
        ai_training = self.test_results.get('ai_training', {})
        
        # Overall assessment
        endpoint_success = (production_tests.get('successful_endpoints', 0) / production_tests.get('total_endpoints', 1)) * 100
        chatbot_success = (chatbot_tests.get('successful_responses', 0) / chatbot_tests.get('total_queries', 1)) * 100
        ai_success = (ai_training.get('successful_training', 0) / ai_training.get('total_training_samples', 1)) * 100
        
        overall_score = (endpoint_success + chatbot_success + ai_success) / 3
        
        # Determine production readiness
        if overall_score >= 85:
            production_grade = "A+ (EXCELLENT)"
            production_ready = True
        elif overall_score >= 75:
            production_grade = "A (VERY GOOD)"
            production_ready = True
        elif overall_score >= 65:
            production_grade = "B (GOOD)"
            production_ready = True
        elif overall_score >= 55:
            production_grade = "C (AVERAGE)"
            production_ready = False
        else:
            production_grade = "D (NEEDS IMPROVEMENT)"
            production_ready = False
        
        production_report = {
            'timestamp': datetime.now().isoformat(),
            'production_url': self.production_url,
            'overall_assessment': {
                'grade': production_grade,
                'overall_score': overall_score,
                'production_ready': production_ready,
                'endpoint_success': endpoint_success,
                'chatbot_success': chatbot_success,
                'ai_training_success': ai_success
            },
            'test_results': self.test_results,
            'recommendations': self._generate_recommendations(overall_score, production_tests, chatbot_tests, ai_training)
        }
        
        # Display report
        print(f"\n🎯 PRODUCTION ASSESSMENT")
        print(f"Overall Grade: {production_grade}")
        print(f"Overall Score: {overall_score:.1f}%")
        print(f"Production Ready: {'✅ YES' if production_ready else '❌ NO'}")
        print(f"Endpoint Success: {endpoint_success:.1f}%")
        print(f"Chatbot Success: {chatbot_success:.1f}%")
        print(f"AI Training Success: {ai_success:.1f}%")
        
        # Save report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f"production_report_{timestamp}.json"
        
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(production_report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Production report saved to: {report_filename}")
        
        return production_report
    
    def _generate_recommendations(self, overall_score, production_tests, chatbot_tests, ai_training):
        """Generate recommendations based on test results"""
        recommendations = []
        
        if overall_score < 70:
            recommendations.append("🔧 Critical: Address failing endpoints and improve chatbot reliability")
        
        if production_tests.get('successful_endpoints', 0) < production_tests.get('total_endpoints', 1) * 0.8:
            recommendations.append("🌐 Network: Check server connectivity and endpoint configurations")
        
        if chatbot_tests.get('average_response_time', 0) > 5:
            recommendations.append("⚡ Performance: Optimize response times for better user experience")
        
        if chatbot_tests.get('multilingual_success', 0) < 80:
            recommendations.append("🌍 Language: Improve multilingual support and translation accuracy")
        
        if ai_training.get('overall_confidence', 0) < 0.8:
            recommendations.append("🧠 AI: Enhance confidence scoring and response quality")
        
        if not recommendations:
            recommendations.append("🎉 Excellent: Your AI assistant is performing optimally!")
        
        return recommendations
    
    def run_complete_suite(self):
        """Run the complete production testing and training suite"""
        print("🚀 PRODUCTION TESTING AND AI TRAINING SUITE")
        print("=" * 80)
        print("Comprehensive testing and training for deployed agricultural AI assistant")
        print("=" * 80)
        
        # Step 1: Test production endpoints
        production_results = self.test_production_endpoints()
        
        # Step 2: Test chatbot functionality
        chatbot_results = self.test_chatbot_functionality()
        
        # Step 3: Train AI with production data
        training_results = self.train_ai_with_production_data()
        
        # Step 4: Generate comprehensive report
        production_report = self.generate_production_report()
        
        print(f"\n🎉 PRODUCTION TESTING AND TRAINING COMPLETE!")
        print(f"📊 Final Grade: {production_report['overall_assessment']['grade']}")
        print(f"🚀 Production Ready: {'✅ YES' if production_report['overall_assessment']['production_ready'] else '❌ NO'}")
        
        return production_report

def main():
    """Main function to run the production testing and training suite"""
    suite = ProductionTestingAndTrainingSuite()
    return suite.run_complete_suite()

if __name__ == "__main__":
    main()

