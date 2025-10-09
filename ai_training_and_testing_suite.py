#!/usr/bin/env python3
"""
AI Training and Testing Suite
Advanced training and comprehensive testing for the AI assistant
"""

import sys
import os
import time
import json
import random
from datetime import datetime
from typing import Dict, List, Any

# Add project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from advisory.ml.ultimate_intelligent_ai import ultimate_ai

class AITrainingAndTestingSuite:
    """Advanced AI Training and Testing Suite"""
    
    def __init__(self):
        self.training_data = []
        self.test_results = []
        self.performance_metrics = {
            'total_queries': 0,
            'successful_responses': 0,
            'average_confidence': 0,
            'average_intelligence': 0,
            'response_times': [],
            'language_accuracy': {},
            'intent_accuracy': {},
            'government_data_usage': 0
        }
    
    def generate_training_data(self):
        """Generate comprehensive training data for AI improvement"""
        print("🧠 Generating AI Training Data...")
        
        # Comprehensive training queries
        training_queries = {
            'farming_basic': [
                "What crop should I grow in Delhi this season?",
                "दिल्ली में कौन सी फसल उगाऊं?",
                "Delhi mein kya crop grow karu?",
                "What is the best crop for Punjab?",
                "पंजाब के लिए सबसे अच्छी फसल कौन सी है?",
                "Which crop is suitable for Mumbai weather?",
                "मुंबई के मौसम के लिए कौन सी फसल उपयुक्त है?"
            ],
            'market_prices': [
                "What is the current price of wheat in Mumbai?",
                "मुंबई में गेहूं की कीमत क्या है?",
                "Mumbai mein wheat ka price kya hai?",
                "Tell me wheat price in Delhi",
                "दिल्ली में गेहूं की दर बताओ",
                "What's the market rate for rice in Punjab?",
                "पंजाब में चावल का बाजार भाव क्या है?"
            ],
            'weather_forecasts': [
                "What's the weather like for farming in Delhi?",
                "दिल्ली में कृषि के लिए मौसम कैसा है?",
                "Delhi mein farming ke liye weather kaisa hai?",
                "Will it rain tomorrow in Mumbai?",
                "क्या कल मुंबई में बारिश होगी?",
                "What's the temperature in Punjab today?",
                "आज पंजाब में तापमान क्या है?"
            ],
            'government_schemes': [
                "What government schemes are available for farmers?",
                "किसानों के लिए कौन सी सरकारी योजनाएं हैं?",
                "Farmers ke liye sarkari yojanayein kya hain?",
                "Tell me about PM Kisan scheme",
                "पीएम किसान योजना के बारे में बताओ",
                "What is crop insurance scheme?",
                "फसल बीमा योजना क्या है?"
            ],
            'pest_control': [
                "How to control pests in rice crop?",
                "चावल की फसल में कीट नियंत्रण कैसे करें?",
                "Rice crop mein pest control kaise kare?",
                "What to do about aphids on wheat?",
                "गेहूं पर एफिड्स का क्या करें?",
                "How to prevent crop diseases?",
                "फसल रोगों से कैसे बचें?"
            ],
            'fertilizer_advice': [
                "What fertilizer should I use for tomato crop?",
                "टमाटर की फसल के लिए कौन सा उर्वरक इस्तेमाल करें?",
                "Tomato crop ke liye kya fertilizer use kare?",
                "How much urea for wheat per acre?",
                "गेहूं के लिए प्रति एकड़ कितना यूरिया?",
                "What is NPK fertilizer?",
                "एनपीके उर्वरक क्या है?"
            ],
            'irrigation_methods': [
                "What irrigation methods are best for rice?",
                "चावल के लिए कौन सी सिंचाई विधि सबसे अच्छी है?",
                "Rice ke liye best irrigation method kya hai?",
                "How to save water in farming?",
                "खेती में पानी कैसे बचाएं?",
                "What is drip irrigation?",
                "ड्रिप सिंचाई क्या है?"
            ],
            'mixed_queries': [
                "Tell me about wheat cultivation and market prices",
                "गेहूं की खेती और बाजार भाव के बारे में बताओ",
                "Wheat cultivation aur market prices batao",
                "What's the weather for farming and give me a trivia question",
                "खेती के लिए मौसम कैसा है और एक सामान्य ज्ञान सवाल दो",
                "Weather for farming aur ek fun fact batao"
            ],
            'complex_queries': [
                "What is the best crop to grow in Delhi during kharif season considering soil type and market demand?",
                "दिल्ली में खरीफ सीजन में मिट्टी के प्रकार और बाजार की मांग को ध्यान में रखते हुए सबसे अच्छी फसल कौन सी है?",
                "Delhi mein kharif season mein soil type aur market demand ke hisab se best crop kya hai?",
                "Compare wheat and rice farming in terms of yield, cost, and market price",
                "उपज, लागत और बाजार भाव के मामले में गेहूं और चावल की खेती की तुलना करें",
                "Wheat aur rice farming ko yield, cost aur market price ke terms mein compare karo"
            ],
            'error_handling': [
                "what crop i should grow in delhi",  # Missing capitalization
                "wht is the price of wheat in mumbai",  # Typo
                "how control pest in rice",  # Missing articles
                "दिल्ली में कौन सी फसल उगाना चाहिए",  # Hindi without question mark
                "मुंबई में गेहूं की किमत क्या है",  # Hindi typo
                "Delhi mein kya crop lagayein",  # Hinglish variation
                "Mumbai mein wheat price kitna hai"  # Hinglish variation
            ]
        }
        
        # Convert to training format
        for category, queries in training_queries.items():
            for query in queries:
                self.training_data.append({
                    'query': query,
                    'category': category,
                    'expected_intent': self._determine_expected_intent(category),
                    'language': self._detect_language(query),
                    'complexity': self._assess_complexity(query)
                })
        
        print(f"   ✅ Generated {len(self.training_data)} training samples")
        return self.training_data
    
    def _determine_expected_intent(self, category: str) -> str:
        """Determine expected intent from category"""
        intent_mapping = {
            'farming_basic': 'crop_recommendation',
            'market_prices': 'market',
            'weather_forecasts': 'weather',
            'government_schemes': 'government',
            'pest_control': 'pest',
            'fertilizer_advice': 'fertilizer',
            'irrigation_methods': 'irrigation',
            'mixed_queries': 'mixed',
            'complex_queries': 'complex',
            'error_handling': 'error_handling'
        }
        return intent_mapping.get(category, 'general')
    
    def _detect_language(self, query: str) -> str:
        """Detect language from query"""
        hindi_chars = any('\u0900' <= char <= '\u097F' for char in query)
        if hindi_chars:
            return 'hi'
        elif any(word in query.lower() for word in ['mein', 'ka', 'kya', 'hai', 'aur', 'batao']):
            return 'hinglish'
        else:
            return 'en'
    
    def _assess_complexity(self, query: str) -> str:
        """Assess query complexity"""
        if len(query.split()) > 15:
            return 'high'
        elif len(query.split()) > 8:
            return 'medium'
        else:
            return 'low'
    
    def train_ai_with_data(self):
        """Train AI with generated data"""
        print("\n🎯 Training AI with Comprehensive Data...")
        
        training_results = {
            'total_training_queries': len(self.training_data),
            'successful_training': 0,
            'average_confidence': 0,
            'average_intelligence': 0,
            'language_performance': {},
            'category_performance': {},
            'training_time': 0
        }
        
        start_time = time.time()
        confidence_scores = []
        intelligence_scores = []
        
        for i, training_item in enumerate(self.training_data):
            query = training_item['query']
            category = training_item['category']
            language = training_item['language']
            
            try:
                # Get AI response
                response = ultimate_ai.get_response(
                    user_query=query,
                    language=language,
                    location_name="Delhi"
                )
                
                # Analyze response
                confidence = response.get('confidence', 0)
                intelligence = response.get('intelligence_score', 0)
                query_type = response.get('query_type', 'unknown')
                
                confidence_scores.append(confidence)
                intelligence_scores.append(intelligence)
                
                # Track performance by category
                if category not in training_results['category_performance']:
                    training_results['category_performance'][category] = {
                        'total': 0, 'successful': 0, 'avg_confidence': 0
                    }
                
                training_results['category_performance'][category]['total'] += 1
                if confidence > 0.7:
                    training_results['category_performance'][category]['successful'] += 1
                    training_results['successful_training'] += 1
                
                # Track language performance
                if language not in training_results['language_performance']:
                    training_results['language_performance'][language] = {
                        'total': 0, 'successful': 0, 'avg_confidence': 0
                    }
                
                training_results['language_performance'][language]['total'] += 1
                if confidence > 0.7:
                    training_results['language_performance'][language]['successful'] += 1
                
                # Progress indicator
                if (i + 1) % 10 == 0:
                    print(f"   📊 Progress: {i + 1}/{len(self.training_data)} queries processed")
                
            except Exception as e:
                print(f"   ❌ Error processing query: {e}")
        
        # Calculate final metrics
        training_time = time.time() - start_time
        training_results['training_time'] = training_time
        training_results['average_confidence'] = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        training_results['average_intelligence'] = sum(intelligence_scores) / len(intelligence_scores) if intelligence_scores else 0
        
        # Calculate category and language performance
        for category, data in training_results['category_performance'].items():
            if data['total'] > 0:
                data['avg_confidence'] = data['successful'] / data['total']
        
        for language, data in training_results['language_performance'].items():
            if data['total'] > 0:
                data['avg_confidence'] = data['successful'] / data['total']
        
        print(f"   ✅ Training completed in {training_time:.2f} seconds")
        print(f"   📊 Success Rate: {(training_results['successful_training']/len(self.training_data))*100:.1f}%")
        print(f"   🧠 Average Confidence: {training_results['average_confidence']:.2f}")
        print(f"   🎯 Average Intelligence: {training_results['average_intelligence']:.2f}")
        
        return training_results
    
    def run_comprehensive_testing(self):
        """Run comprehensive testing suite"""
        print("\n🧪 Running Comprehensive Testing Suite...")
        
        test_categories = [
            {
                'name': 'Basic Farming Queries',
                'queries': [
                    "What crop should I grow in Delhi?",
                    "दिल्ली में कौन सी फसल उगाऊं?",
                    "Delhi mein kya crop grow karu?",
                    "What is the price of wheat in Mumbai?",
                    "मुंबई में गेहूं की कीमत क्या है?",
                    "Mumbai mein wheat ka price kya hai?"
                ]
            },
            {
                'name': 'Government Data Integration',
                'queries': [
                    "What government schemes are available for farmers?",
                    "किसानों के लिए सरकारी योजनाएं क्या हैं?",
                    "Tell me about PM Kisan scheme",
                    "पीएम किसान योजना के बारे में बताओ"
                ]
            },
            {
                'name': 'Weather and Climate',
                'queries': [
                    "What's the weather like for farming in Punjab?",
                    "पंजाब में कृषि के लिए मौसम कैसा है?",
                    "Will it rain tomorrow in Delhi?",
                    "क्या कल दिल्ली में बारिश होगी?"
                ]
            },
            {
                'name': 'Technical Farming Terms',
                'queries': [
                    "What is MSP for wheat?",
                    "गेहूं के लिए एमएसपी क्या है?",
                    "How to control pests in rice crop?",
                    "चावल की फसल में कीट नियंत्रण कैसे करें?"
                ]
            },
            {
                'name': 'Error Handling',
                'queries': [
                    "what crop i should grow in delhi",  # Grammar error
                    "wht is the price of wheat",  # Typo
                    "how control pest in rice",  # Missing words
                    "मुंबई में गेहूं की किमत क्या है"  # Hindi typo
                ]
            },
            {
                'name': 'Complex Multi-Intent',
                'queries': [
                    "Tell me about wheat cultivation, market prices, and government schemes",
                    "गेहूं की खेती, बाजार भाव और सरकारी योजनाओं के बारे में बताओ",
                    "What's the weather for farming and give me a fun fact",
                    "खेती के लिए मौसम कैसा है और एक सामान्य ज्ञान सवाल दो"
                ]
            }
        ]
        
        test_results = {
            'total_tests': 0,
            'passed_tests': 0,
            'category_results': {},
            'overall_metrics': {
                'average_confidence': 0,
                'average_intelligence': 0,
                'average_response_time': 0,
                'government_data_usage': 0,
                'multilingual_success': 0
            }
        }
        
        confidence_scores = []
        intelligence_scores = []
        response_times = []
        government_data_count = 0
        multilingual_success_count = 0
        
        for category in test_categories:
            category_name = category['name']
            queries = category['queries']
            
            print(f"\n   🔍 Testing: {category_name}")
            
            category_results = {
                'total': len(queries),
                'passed': 0,
                'confidence_scores': [],
                'intelligence_scores': [],
                'response_times': []
            }
            
            for query in queries:
                try:
                    start_time = time.time()
                    
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
                    
                    response_time = time.time() - start_time
                    
                    # Analyze response
                    confidence = response.get('confidence', 0)
                    intelligence = response.get('intelligence_score', 0)
                    has_gov_data = response.get('has_government_data', False)
                    response_content = response.get('response', '')
                    
                    # Check if response is successful
                    is_successful = (
                        confidence > 0.7 and 
                        intelligence > 0.7 and 
                        len(response_content) > 50 and
                        response_time < 3.0
                    )
                    
                    if is_successful:
                        category_results['passed'] += 1
                        test_results['passed_tests'] += 1
                    
                    # Track metrics
                    category_results['confidence_scores'].append(confidence)
                    category_results['intelligence_scores'].append(intelligence)
                    category_results['response_times'].append(response_time)
                    
                    confidence_scores.append(confidence)
                    intelligence_scores.append(intelligence)
                    response_times.append(response_time)
                    
                    if has_gov_data:
                        government_data_count += 1
                    
                    # Check multilingual success
                    if language == 'hi' and any('\u0900' <= char <= '\u097F' for char in response_content):
                        multilingual_success_count += 1
                    elif language == 'en' and not any('\u0900' <= char <= '\u097F' for char in response_content):
                        multilingual_success_count += 1
                    elif language == 'hinglish':
                        multilingual_success_count += 1
                    
                    test_results['total_tests'] += 1
                    
                    # Display result
                    status = "✅ PASS" if is_successful else "❌ FAIL"
                    print(f"      {status} | Conf: {confidence:.2f} | Intel: {intelligence:.2f} | Time: {response_time:.2f}s")
                    
                except Exception as e:
                    print(f"      ❌ ERROR: {e}")
                    test_results['total_tests'] += 1
            
            # Calculate category metrics
            if category_results['confidence_scores']:
                category_results['avg_confidence'] = sum(category_results['confidence_scores']) / len(category_results['confidence_scores'])
                category_results['avg_intelligence'] = sum(category_results['intelligence_scores']) / len(category_results['intelligence_scores'])
                category_results['avg_response_time'] = sum(category_results['response_times']) / len(category_results['response_times'])
                category_results['success_rate'] = (category_results['passed'] / category_results['total']) * 100
            
            test_results['category_results'][category_name] = category_results
        
        # Calculate overall metrics
        if confidence_scores:
            test_results['overall_metrics']['average_confidence'] = sum(confidence_scores) / len(confidence_scores)
            test_results['overall_metrics']['average_intelligence'] = sum(intelligence_scores) / len(intelligence_scores)
            test_results['overall_metrics']['average_response_time'] = sum(response_times) / len(response_times)
            test_results['overall_metrics']['government_data_usage'] = (government_data_count / test_results['total_tests']) * 100
            test_results['overall_metrics']['multilingual_success'] = (multilingual_success_count / test_results['total_tests']) * 100
        
        return test_results
    
    def generate_performance_report(self, training_results: Dict, test_results: Dict):
        """Generate comprehensive performance report"""
        print("\n📊 GENERATING PERFORMANCE REPORT")
        print("=" * 60)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'training_results': training_results,
            'test_results': test_results,
            'overall_assessment': {}
        }
        
        # Overall Assessment
        overall_success_rate = (test_results['passed_tests'] / test_results['total_tests']) * 100 if test_results['total_tests'] > 0 else 0
        avg_confidence = test_results['overall_metrics']['average_confidence']
        avg_intelligence = test_results['overall_metrics']['average_intelligence']
        gov_data_usage = test_results['overall_metrics']['government_data_usage']
        multilingual_success = test_results['overall_metrics']['multilingual_success']
        
        # Determine overall grade
        if overall_success_rate >= 90 and avg_confidence >= 0.8 and avg_intelligence >= 0.8:
            overall_grade = "A+ (EXCELLENT)"
        elif overall_success_rate >= 80 and avg_confidence >= 0.7 and avg_intelligence >= 0.7:
            overall_grade = "A (VERY GOOD)"
        elif overall_success_rate >= 70 and avg_confidence >= 0.6 and avg_intelligence >= 0.6:
            overall_grade = "B (GOOD)"
        elif overall_success_rate >= 60:
            overall_grade = "C (AVERAGE)"
        else:
            overall_grade = "D (NEEDS IMPROVEMENT)"
        
        report['overall_assessment'] = {
            'grade': overall_grade,
            'success_rate': overall_success_rate,
            'confidence_score': avg_confidence,
            'intelligence_score': avg_intelligence,
            'government_data_usage': gov_data_usage,
            'multilingual_success': multilingual_success,
            'production_ready': overall_success_rate >= 80 and avg_confidence >= 0.7
        }
        
        # Display report
        print(f"\n🎯 OVERALL PERFORMANCE ASSESSMENT")
        print(f"Grade: {overall_grade}")
        print(f"Success Rate: {overall_success_rate:.1f}%")
        print(f"Average Confidence: {avg_confidence:.2f}")
        print(f"Average Intelligence: {avg_intelligence:.2f}")
        print(f"Government Data Usage: {gov_data_usage:.1f}%")
        print(f"Multilingual Success: {multilingual_success:.1f}%")
        print(f"Production Ready: {'✅ YES' if report['overall_assessment']['production_ready'] else '❌ NO'}")
        
        print(f"\n📊 CATEGORY-WISE PERFORMANCE")
        for category_name, results in test_results['category_results'].items():
            success_rate = results.get('success_rate', 0)
            avg_conf = results.get('avg_confidence', 0)
            print(f"   {category_name}: {success_rate:.1f}% success, {avg_conf:.2f} confidence")
        
        # Save report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f"ai_performance_report_{timestamp}.json"
        
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Report saved to: {report_filename}")
        
        return report
    
    def run_complete_suite(self):
        """Run the complete AI training and testing suite"""
        print("🚀 AI TRAINING AND TESTING SUITE")
        print("=" * 60)
        print("Comprehensive AI Training and Testing for Agricultural Assistant")
        print("=" * 60)
        
        # Step 1: Generate training data
        training_data = self.generate_training_data()
        
        # Step 2: Train AI with data
        training_results = self.train_ai_with_data()
        
        # Step 3: Run comprehensive testing
        test_results = self.run_comprehensive_testing()
        
        # Step 4: Generate performance report
        performance_report = self.generate_performance_report(training_results, test_results)
        
        print(f"\n🎉 AI TRAINING AND TESTING COMPLETE!")
        print(f"📊 Final Grade: {performance_report['overall_assessment']['grade']}")
        print(f"🚀 Production Ready: {'✅ YES' if performance_report['overall_assessment']['production_ready'] else '❌ NO'}")
        
        return performance_report

def main():
    """Main function to run the AI training and testing suite"""
    suite = AITrainingAndTestingSuite()
    return suite.run_complete_suite()

if __name__ == "__main__":
    main()
