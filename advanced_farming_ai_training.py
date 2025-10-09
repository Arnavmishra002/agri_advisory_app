#!/usr/bin/env python3
"""
Advanced Farming AI Training System
Comprehensive training focused on farming queries and government API integration
"""

import sys
import os
import json
import time
import random
from datetime import datetime
from typing import Dict, List, Any

# Add project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from advisory.ml.ultimate_intelligent_ai import ultimate_ai

class AdvancedFarmingAITrainer:
    """Advanced Farming AI Training System"""
    
    def __init__(self):
        self.training_results = {
            'farming_training': {},
            'government_api_integration': {},
            'query_understanding': {},
            'output_verification': {},
            'timestamp': datetime.now().isoformat()
        }
        
    def generate_comprehensive_farming_training_data(self):
        """Generate comprehensive farming training data"""
        print("🌱 GENERATING COMPREHENSIVE FARMING TRAINING DATA")
        print("=" * 70)
        
        training_data = {
            'crop_recommendations': [
                # English queries
                {"query": "What crops should I grow in Delhi during Kharif season?", "language": "en", "expected_intent": "crop_recommendation", "location": "Delhi", "season": "Kharif"},
                {"query": "Best crops for Punjab soil in Rabi season", "language": "en", "expected_intent": "crop_recommendation", "location": "Punjab", "season": "Rabi"},
                {"query": "Which crops are suitable for Maharashtra climate?", "language": "en", "expected_intent": "crop_recommendation", "location": "Maharashtra"},
                {"query": "What should I plant in Karnataka this season?", "language": "en", "expected_intent": "crop_recommendation", "location": "Karnataka"},
                {"query": "Crop suggestions for Tamil Nadu farmers", "language": "en", "expected_intent": "crop_recommendation", "location": "Tamil Nadu"},
                
                # Hindi queries
                {"query": "दिल्ली में खरीफ सीजन में कौन सी फसलें उगाऊं?", "language": "hi", "expected_intent": "crop_recommendation", "location": "Delhi", "season": "Kharif"},
                {"query": "पंजाब की मिट्टी के लिए रबी सीजन की सबसे अच्छी फसलें", "language": "hi", "expected_intent": "crop_recommendation", "location": "Punjab", "season": "Rabi"},
                {"query": "महाराष्ट्र की जलवायु के लिए उपयुक्त फसलें कौन सी हैं?", "language": "hi", "expected_intent": "crop_recommendation", "location": "Maharashtra"},
                {"query": "कर्नाटक में इस सीजन में क्या बोना चाहिए?", "language": "hi", "expected_intent": "crop_recommendation", "location": "Karnataka"},
                {"query": "तमिलनाडु के किसानों के लिए फसल सुझाव", "language": "hi", "expected_intent": "crop_recommendation", "location": "Tamil Nadu"},
                
                # Hinglish queries
                {"query": "Delhi mein Kharif season mein kaun si crops grow karu?", "language": "hinglish", "expected_intent": "crop_recommendation", "location": "Delhi", "season": "Kharif"},
                {"query": "Punjab soil ke liye Rabi season ki best crops kya hain?", "language": "hinglish", "expected_intent": "crop_recommendation", "location": "Punjab", "season": "Rabi"},
                {"query": "Maharashtra climate ke liye suitable crops kaun se hain?", "language": "hinglish", "expected_intent": "crop_recommendation", "location": "Maharashtra"},
                {"query": "Karnataka mein is season mein kya plant karu?", "language": "hinglish", "expected_intent": "crop_recommendation", "location": "Karnataka"},
                {"query": "Tamil Nadu farmers ke liye crop suggestions", "language": "hinglish", "expected_intent": "crop_recommendation", "location": "Tamil Nadu"}
            ],
            
            'market_prices': [
                # English queries
                {"query": "What is the current price of wheat in Delhi mandi?", "language": "en", "expected_intent": "market_price", "crop": "wheat", "location": "Delhi"},
                {"query": "Rice price in Mumbai APMC today", "language": "en", "expected_intent": "market_price", "crop": "rice", "location": "Mumbai"},
                {"query": "How much is maize selling for in Punjab?", "language": "en", "expected_intent": "market_price", "crop": "maize", "location": "Punjab"},
                {"query": "Cotton market price in Gujarat", "language": "en", "expected_intent": "market_price", "crop": "cotton", "location": "Gujarat"},
                {"query": "Sugarcane price per quintal in Uttar Pradesh", "language": "en", "expected_intent": "market_price", "crop": "sugarcane", "location": "Uttar Pradesh"},
                
                # Hindi queries
                {"query": "दिल्ली मंडी में गेहूं की वर्तमान कीमत क्या है?", "language": "hi", "expected_intent": "market_price", "crop": "wheat", "location": "Delhi"},
                {"query": "मुंबई APMC में आज चावल की कीमत", "language": "hi", "expected_intent": "market_price", "crop": "rice", "location": "Mumbai"},
                {"query": "पंजाब में मक्का कितने में बिक रहा है?", "language": "hi", "expected_intent": "market_price", "crop": "maize", "location": "Punjab"},
                {"query": "गुजरात में कपास का बाजार भाव", "language": "hi", "expected_intent": "market_price", "crop": "cotton", "location": "Gujarat"},
                {"query": "उत्तर प्रदेश में गन्ने की प्रति क्विंटल कीमत", "language": "hi", "expected_intent": "market_price", "crop": "sugarcane", "location": "Uttar Pradesh"},
                
                # Hinglish queries
                {"query": "Delhi mandi mein wheat ki current price kya hai?", "language": "hinglish", "expected_intent": "market_price", "crop": "wheat", "location": "Delhi"},
                {"query": "Mumbai APMC mein aaj rice ki price", "language": "hinglish", "expected_intent": "market_price", "crop": "rice", "location": "Mumbai"},
                {"query": "Punjab mein maize kitne mein bik raha hai?", "language": "hinglish", "expected_intent": "market_price", "crop": "maize", "location": "Punjab"},
                {"query": "Gujarat mein cotton ka market rate", "language": "hinglish", "expected_intent": "market_price", "crop": "cotton", "location": "Gujarat"},
                {"query": "UP mein sugarcane ki per quintal price", "language": "hinglish", "expected_intent": "market_price", "crop": "sugarcane", "location": "Uttar Pradesh"}
            ],
            
            'weather_forecasting': [
                # English queries
                {"query": "Weather forecast for Delhi farming activities", "language": "en", "expected_intent": "weather", "location": "Delhi"},
                {"query": "Rain prediction for Punjab this week", "language": "en", "expected_intent": "weather", "location": "Punjab"},
                {"query": "Temperature forecast for Maharashtra crops", "language": "en", "expected_intent": "weather", "location": "Maharashtra"},
                {"query": "Humidity levels for Karnataka farming", "language": "en", "expected_intent": "weather", "location": "Karnataka"},
                {"query": "Wind speed for Tamil Nadu agricultural work", "language": "en", "expected_intent": "weather", "location": "Tamil Nadu"},
                
                # Hindi queries
                {"query": "दिल्ली में कृषि गतिविधियों के लिए मौसम पूर्वानुमान", "language": "hi", "expected_intent": "weather", "location": "Delhi"},
                {"query": "पंजाब में इस सप्ताह बारिश का अनुमान", "language": "hi", "expected_intent": "weather", "location": "Punjab"},
                {"query": "महाराष्ट्र की फसलों के लिए तापमान पूर्वानुमान", "language": "hi", "expected_intent": "weather", "location": "Maharashtra"},
                {"query": "कर्नाटक में कृषि के लिए आर्द्रता स्तर", "language": "hi", "expected_intent": "weather", "location": "Karnataka"},
                {"query": "तमिलनाडु में कृषि कार्य के लिए हवा की गति", "language": "hi", "expected_intent": "weather", "location": "Tamil Nadu"},
                
                # Hinglish queries
                {"query": "Delhi mein farming activities ke liye weather forecast", "language": "hinglish", "expected_intent": "weather", "location": "Delhi"},
                {"query": "Punjab mein is week rain prediction", "language": "hinglish", "expected_intent": "weather", "location": "Punjab"},
                {"query": "Maharashtra crops ke liye temperature forecast", "language": "hinglish", "expected_intent": "weather", "location": "Maharashtra"},
                {"query": "Karnataka farming ke liye humidity levels", "language": "hinglish", "expected_intent": "weather", "location": "Karnataka"},
                {"query": "Tamil Nadu agricultural work ke liye wind speed", "language": "hinglish", "expected_intent": "weather", "location": "Tamil Nadu"}
            ],
            
            'pest_control': [
                # English queries
                {"query": "How to control aphids in wheat crop?", "language": "en", "expected_intent": "pest_control", "pest": "aphids", "crop": "wheat"},
                {"query": "Best treatment for rice blast disease", "language": "en", "expected_intent": "pest_control", "disease": "rice blast", "crop": "rice"},
                {"query": "Natural pesticides for cotton bollworm", "language": "en", "expected_intent": "pest_control", "pest": "bollworm", "crop": "cotton"},
                {"query": "How to prevent maize stem borer?", "language": "en", "expected_intent": "pest_control", "pest": "stem borer", "crop": "maize"},
                {"query": "Organic control for tomato fruit borer", "language": "en", "expected_intent": "pest_control", "pest": "fruit borer", "crop": "tomato"},
                
                # Hindi queries
                {"query": "गेहूं की फसल में एफिड्स को कैसे नियंत्रित करें?", "language": "hi", "expected_intent": "pest_control", "pest": "aphids", "crop": "wheat"},
                {"query": "चावल के ब्लास्ट रोग का सबसे अच्छा उपचार", "language": "hi", "expected_intent": "pest_control", "disease": "rice blast", "crop": "rice"},
                {"query": "कपास के बॉलवर्म के लिए प्राकृतिक कीटनाशक", "language": "hi", "expected_intent": "pest_control", "pest": "bollworm", "crop": "cotton"},
                {"query": "मक्के के तना छेदक को कैसे रोकें?", "language": "hi", "expected_intent": "pest_control", "pest": "stem borer", "crop": "maize"},
                {"query": "टमाटर के फल छेदक के लिए जैविक नियंत्रण", "language": "hi", "expected_intent": "pest_control", "pest": "fruit borer", "crop": "tomato"},
                
                # Hinglish queries
                {"query": "Wheat crop mein aphids ko kaise control kare?", "language": "hinglish", "expected_intent": "pest_control", "pest": "aphids", "crop": "wheat"},
                {"query": "Rice ke blast disease ka best treatment", "language": "hinglish", "expected_intent": "pest_control", "disease": "rice blast", "crop": "rice"},
                {"query": "Cotton ke bollworm ke liye natural pesticides", "language": "hinglish", "expected_intent": "pest_control", "pest": "bollworm", "crop": "cotton"},
                {"query": "Maize ke stem borer ko kaise prevent kare?", "language": "hinglish", "expected_intent": "pest_control", "pest": "stem borer", "crop": "maize"},
                {"query": "Tomato ke fruit borer ke liye organic control", "language": "hinglish", "expected_intent": "pest_control", "pest": "fruit borer", "crop": "tomato"}
            ],
            
            'government_schemes': [
                # English queries
                {"query": "How to apply for PM Kisan scheme?", "language": "en", "expected_intent": "government_scheme", "scheme": "PM Kisan"},
                {"query": "Eligibility criteria for Pradhan Mantri Fasal Bima Yojana", "language": "en", "expected_intent": "government_scheme", "scheme": "PMFBY"},
                {"query": "Benefits of Soil Health Card scheme", "language": "en", "expected_intent": "government_scheme", "scheme": "Soil Health Card"},
                {"query": "How to get Kisan Credit Card?", "language": "en", "expected_intent": "government_scheme", "scheme": "Kisan Credit Card"},
                {"query": "Details of Paramparagat Krishi Vikas Yojana", "language": "en", "expected_intent": "government_scheme", "scheme": "PKVY"},
                
                # Hindi queries
                {"query": "पीएम किसान योजना के लिए कैसे आवेदन करें?", "language": "hi", "expected_intent": "government_scheme", "scheme": "PM Kisan"},
                {"query": "प्रधानमंत्री फसल बीमा योजना की पात्रता", "language": "hi", "expected_intent": "government_scheme", "scheme": "PMFBY"},
                {"query": "मृदा स्वास्थ्य कार्ड योजना के लाभ", "language": "hi", "expected_intent": "government_scheme", "scheme": "Soil Health Card"},
                {"query": "किसान क्रेडिट कार्ड कैसे प्राप्त करें?", "language": "hi", "expected_intent": "government_scheme", "scheme": "Kisan Credit Card"},
                {"query": "परंपरागत कृषि विकास योजना का विवरण", "language": "hi", "expected_intent": "government_scheme", "scheme": "PKVY"},
                
                # Hinglish queries
                {"query": "PM Kisan scheme ke liye kaise apply kare?", "language": "hinglish", "expected_intent": "government_scheme", "scheme": "PM Kisan"},
                {"query": "Pradhan Mantri Fasal Bima Yojana ki eligibility", "language": "hinglish", "expected_intent": "government_scheme", "scheme": "PMFBY"},
                {"query": "Soil Health Card scheme ke benefits", "language": "hinglish", "expected_intent": "government_scheme", "scheme": "Soil Health Card"},
                {"query": "Kisan Credit Card kaise get kare?", "language": "hinglish", "expected_intent": "government_scheme", "scheme": "Kisan Credit Card"},
                {"query": "Paramparagat Krishi Vikas Yojana ke details", "language": "hinglish", "expected_intent": "government_scheme", "scheme": "PKVY"}
            ],
            
            'fertilizer_advice': [
                # English queries
                {"query": "What fertilizer should I use for wheat crop?", "language": "en", "expected_intent": "fertilizer", "crop": "wheat"},
                {"query": "NPK ratio for rice cultivation", "language": "en", "expected_intent": "fertilizer", "crop": "rice"},
                {"query": "Organic fertilizers for cotton farming", "language": "en", "expected_intent": "fertilizer", "crop": "cotton", "type": "organic"},
                {"query": "When to apply urea to maize crop?", "language": "en", "expected_intent": "fertilizer", "crop": "maize", "fertilizer": "urea"},
                {"query": "DAP fertilizer application for sugarcane", "language": "en", "expected_intent": "fertilizer", "crop": "sugarcane", "fertilizer": "DAP"},
                
                # Hindi queries
                {"query": "गेहूं की फसल के लिए कौन सा उर्वरक इस्तेमाल करें?", "language": "hi", "expected_intent": "fertilizer", "crop": "wheat"},
                {"query": "चावल की खेती के लिए NPK अनुपात", "language": "hi", "expected_intent": "fertilizer", "crop": "rice"},
                {"query": "कपास की खेती के लिए जैविक उर्वरक", "language": "hi", "expected_intent": "fertilizer", "crop": "cotton", "type": "organic"},
                {"query": "मक्के की फसल में यूरिया कब डालें?", "language": "hi", "expected_intent": "fertilizer", "crop": "maize", "fertilizer": "urea"},
                {"query": "गन्ने के लिए DAP उर्वरक का प्रयोग", "language": "hi", "expected_intent": "fertilizer", "crop": "sugarcane", "fertilizer": "DAP"},
                
                # Hinglish queries
                {"query": "Wheat crop ke liye kaun sa fertilizer use kare?", "language": "hinglish", "expected_intent": "fertilizer", "crop": "wheat"},
                {"query": "Rice cultivation ke liye NPK ratio", "language": "hinglish", "expected_intent": "fertilizer", "crop": "rice"},
                {"query": "Cotton farming ke liye organic fertilizers", "language": "hinglish", "expected_intent": "fertilizer", "crop": "cotton", "type": "organic"},
                {"query": "Maize crop mein urea kab apply kare?", "language": "hinglish", "expected_intent": "fertilizer", "crop": "maize", "fertilizer": "urea"},
                {"query": "Sugarcane ke liye DAP fertilizer application", "language": "hinglish", "expected_intent": "fertilizer", "crop": "sugarcane", "fertilizer": "DAP"}
            ]
        }
        
        total_queries = sum(len(queries) for queries in training_data.values())
        print(f"   ✅ Generated {total_queries} comprehensive farming training queries")
        print(f"   📊 Categories: {len(training_data)} farming domains")
        print(f"   🌍 Languages: English, Hindi, Hinglish")
        print(f"   🎯 Focus: Government API integration and accurate responses")
        
        return training_data
    
    def train_ai_with_farming_data(self, training_data):
        """Train AI with comprehensive farming data"""
        print("\n🧠 TRAINING AI WITH COMPREHENSIVE FARMING DATA")
        print("=" * 70)
        
        training_results = {
            'total_queries': 0,
            'successful_training': 0,
            'failed_training': 0,
            'category_results': {},
            'government_data_integration': 0,
            'response_accuracy': 0,
            'average_confidence': 0,
            'average_intelligence': 0
        }
        
        confidence_scores = []
        intelligence_scores = []
        government_data_used = 0
        
        for category, queries in training_data.items():
            print(f"\n   🎯 Training {category.replace('_', ' ').title()}")
            
            category_result = {
                'total': len(queries),
                'successful': 0,
                'failed': 0,
                'avg_confidence': 0,
                'avg_intelligence': 0,
                'government_data': 0
            }
            
            category_confidence = []
            category_intelligence = []
            
            for query_data in queries:
                try:
                    # Get AI response
                    response = ultimate_ai.get_response(
                        user_query=query_data['query'],
                        language=query_data['language'],
                        location_name=query_data.get('location', 'Delhi')
                    )
                    
                    confidence = response.get('confidence', 0)
                    intelligence = response.get('intelligence_score', 0)
                    has_gov_data = response.get('has_government_data', False)
                    
                    confidence_scores.append(confidence)
                    intelligence_scores.append(intelligence)
                    category_confidence.append(confidence)
                    category_intelligence.append(intelligence)
                    
                    if has_gov_data:
                        government_data_used += 1
                        category_result['government_data'] += 1
                    
                    if confidence > 0.8 and intelligence > 0.7:
                        category_result['successful'] += 1
                        training_results['successful_training'] += 1
                    else:
                        category_result['failed'] += 1
                        training_results['failed_training'] += 1
                    
                    training_results['total_queries'] += 1
                    
                    status = "✅ HIGH" if confidence > 0.8 else "⚠️ MEDIUM" if confidence > 0.6 else "❌ LOW"
                    gov_indicator = "🏛️" if has_gov_data else "📝"
                    print(f"      {status} {gov_indicator} | Conf: {confidence:.2f} | Intel: {intelligence:.2f} | {query_data['language']}")
                    
                except Exception as e:
                    print(f"      ❌ ERROR: {e}")
                    category_result['failed'] += 1
                    training_results['failed_training'] += 1
                    training_results['total_queries'] += 1
            
            # Calculate category averages
            if category_confidence:
                category_result['avg_confidence'] = sum(category_confidence) / len(category_confidence)
            if category_intelligence:
                category_result['avg_intelligence'] = sum(category_intelligence) / len(category_intelligence)
            
            training_results['category_results'][category] = category_result
        
        # Calculate overall metrics
        if confidence_scores:
            training_results['average_confidence'] = sum(confidence_scores) / len(confidence_scores)
        if intelligence_scores:
            training_results['average_intelligence'] = sum(intelligence_scores) / len(intelligence_scores)
        
        training_results['government_data_integration'] = (government_data_used / training_results['total_queries']) * 100
        training_results['response_accuracy'] = (training_results['successful_training'] / training_results['total_queries']) * 100
        
        print(f"\n📊 Farming AI Training Summary:")
        print(f"   Success Rate: {training_results['response_accuracy']:.1f}%")
        print(f"   Government Data Integration: {training_results['government_data_integration']:.1f}%")
        print(f"   Average Confidence: {training_results['average_confidence']:.2f}")
        print(f"   Average Intelligence: {training_results['average_intelligence']:.2f}")
        
        self.training_results['farming_training'] = training_results
        return training_results
    
    def verify_government_api_integration(self):
        """Verify government API integration and data accuracy"""
        print("\n🏛️ VERIFYING GOVERNMENT API INTEGRATION")
        print("=" * 70)
        
        verification_tests = [
            {
                'query': 'What is the MSP for wheat this year?',
                'language': 'en',
                'expected_keywords': ['msp', 'minimum support price', '₹', 'wheat', 'government'],
                'test_type': 'msp_verification'
            },
            {
                'query': 'Current market price of rice in Delhi mandi',
                'language': 'en',
                'expected_keywords': ['price', '₹', 'rice', 'delhi', 'mandi', 'quintal'],
                'test_type': 'market_price_verification'
            },
            {
                'query': 'Weather forecast for Punjab farming',
                'language': 'en',
                'expected_keywords': ['weather', 'temperature', 'rainfall', 'humidity', 'forecast'],
                'test_type': 'weather_verification'
            },
            {
                'query': 'PM Kisan scheme benefits and eligibility',
                'language': 'en',
                'expected_keywords': ['pm kisan', 'scheme', 'benefits', 'eligibility', '₹6000'],
                'test_type': 'government_scheme_verification'
            },
            {
                'query': 'गेहूं के लिए इस साल का MSP क्या है?',
                'language': 'hi',
                'expected_keywords': ['msp', 'न्यूनतम समर्थन मूल्य', '₹', 'गेहूं', 'सरकार'],
                'test_type': 'msp_verification_hindi'
            },
            {
                'query': 'दिल्ली मंडी में चावल की वर्तमान बाजार कीमत',
                'language': 'hi',
                'expected_keywords': ['कीमत', '₹', 'चावल', 'दिल्ली', 'मंडी', 'क्विंटल'],
                'test_type': 'market_price_verification_hindi'
            }
        ]
        
        verification_results = {
            'total_tests': len(verification_tests),
            'passed_tests': 0,
            'failed_tests': 0,
            'government_data_accuracy': 0,
            'test_details': {}
        }
        
        for test in verification_tests:
            try:
                response = ultimate_ai.get_response(
                    user_query=test['query'],
                    language=test['language'],
                    location_name='Delhi'
                )
                
                response_text = response.get('response', '').lower()
                has_gov_data = response.get('has_government_data', False)
                
                # Check for expected keywords
                keyword_matches = sum(1 for keyword in test['expected_keywords'] if keyword.lower() in response_text)
                keyword_accuracy = (keyword_matches / len(test['expected_keywords'])) * 100
                
                # Determine if test passed
                test_passed = keyword_accuracy >= 60 and has_gov_data
                
                if test_passed:
                    verification_results['passed_tests'] += 1
                    status = "✅ PASS"
                else:
                    verification_results['failed_tests'] += 1
                    status = "❌ FAIL"
                
                verification_results['test_details'][test['test_type']] = {
                    'passed': test_passed,
                    'keyword_accuracy': keyword_accuracy,
                    'has_government_data': has_gov_data,
                    'confidence': response.get('confidence', 0),
                    'intelligence': response.get('intelligence_score', 0)
                }
                
                print(f"   {status} | {test['test_type']} | Keywords: {keyword_accuracy:.1f}% | Gov Data: {'✅' if has_gov_data else '❌'}")
                
            except Exception as e:
                print(f"   ❌ ERROR | {test['test_type']} | Error: {e}")
                verification_results['failed_tests'] += 1
                verification_results['test_details'][test['test_type']] = {
                    'passed': False,
                    'error': str(e)
                }
        
        verification_results['government_data_accuracy'] = (verification_results['passed_tests'] / verification_results['total_tests']) * 100
        
        print(f"\n📊 Government API Integration Verification:")
        print(f"   Pass Rate: {verification_results['government_data_accuracy']:.1f}%")
        print(f"   Passed Tests: {verification_results['passed_tests']}/{verification_results['total_tests']}")
        
        self.training_results['government_api_integration'] = verification_results
        return verification_results
    
    def test_query_understanding(self):
        """Test AI's understanding of farming queries"""
        print("\n🎯 TESTING QUERY UNDERSTANDING")
        print("=" * 70)
        
        understanding_tests = [
            # Intent recognition tests
            {"query": "Delhi mein kya crop grow karu?", "expected_intent": "crop_recommendation", "language": "hinglish"},
            {"query": "Wheat ka price kya hai?", "expected_intent": "market_price", "language": "hinglish"},
            {"query": "मौसम कैसा रहेगा?", "expected_intent": "weather", "language": "hi"},
            {"query": "कीट नियंत्रण कैसे करें?", "expected_intent": "pest_control", "language": "hi"},
            {"query": "सरकारी योजना क्या है?", "expected_intent": "government_scheme", "language": "hi"},
            
            # Entity extraction tests
            {"query": "Punjab mein wheat ki price", "expected_entities": ["Punjab", "wheat", "price"], "language": "hinglish"},
            {"query": "महाराष्ट्र में चावल की खेती", "expected_entities": ["महाराष्ट्र", "चावल", "खेती"], "language": "hi"},
            {"query": "Karnataka weather for farming", "expected_entities": ["Karnataka", "weather", "farming"], "language": "en"},
            
            # Complex query understanding
            {"query": "Delhi mein wheat grow karne ke liye fertilizer aur weather ka advice chahiye", "expected_intent": "mixed", "language": "hinglish"},
            {"query": "मुंबई में चावल की कीमत और सरकारी योजना दोनों बताओ", "expected_intent": "mixed", "language": "hi"},
            {"query": "Best crops for Tamil Nadu with market prices and government schemes", "expected_intent": "mixed", "language": "en"}
        ]
        
        understanding_results = {
            'total_tests': len(understanding_tests),
            'intent_recognition': 0,
            'entity_extraction': 0,
            'complex_understanding': 0,
            'overall_understanding': 0
        }
        
        intent_tests = 0
        entity_tests = 0
        complex_tests = 0
        
        for test in understanding_tests:
            try:
                response = ultimate_ai.get_response(
                    user_query=test['query'],
                    language=test['language'],
                    location_name='Delhi'
                )
                
                response_text = response.get('response', '').lower()
                confidence = response.get('confidence', 0)
                
                # Test intent recognition
                if 'expected_intent' in test:
                    intent_tests += 1
                    if test['expected_intent'] == 'mixed':
                        # Check if response addresses multiple intents
                        if any(word in response_text for word in ['price', 'कीमत', 'fertilizer', 'उर्वरक', 'weather', 'मौसम', 'scheme', 'योजना']):
                            understanding_results['intent_recognition'] += 1
                    else:
                        # Check if response addresses the expected intent
                        intent_keywords = {
                            'crop_recommendation': ['crop', 'फसल', 'grow', 'उगाएं', 'recommendation', 'सुझाव'],
                            'market_price': ['price', 'कीमत', 'market', 'बाजार', '₹', 'quintal', 'क्विंटल'],
                            'weather': ['weather', 'मौसम', 'temperature', 'तापमान', 'rainfall', 'बारिश'],
                            'pest_control': ['pest', 'कीट', 'control', 'नियंत्रण', 'disease', 'रोग'],
                            'government_scheme': ['scheme', 'योजना', 'government', 'सरकार', 'pm kisan', 'benefits', 'लाभ']
                        }
                        
                        keywords = intent_keywords.get(test['expected_intent'], [])
                        if any(keyword in response_text for keyword in keywords):
                            understanding_results['intent_recognition'] += 1
                
                # Test entity extraction
                if 'expected_entities' in test:
                    entity_tests += 1
                    entities_found = sum(1 for entity in test['expected_entities'] if entity.lower() in response_text)
                    if entities_found >= len(test['expected_entities']) * 0.6:  # 60% entities found
                        understanding_results['entity_extraction'] += 1
                
                # Test complex understanding
                if 'expected_intent' in test and test['expected_intent'] == 'mixed':
                    complex_tests += 1
                    if confidence > 0.8 and len(response_text) > 100:
                        understanding_results['complex_understanding'] += 1
                
                status = "✅ GOOD" if confidence > 0.8 else "⚠️ MEDIUM" if confidence > 0.6 else "❌ POOR"
                print(f"   {status} | {test['query'][:40]}... | Conf: {confidence:.2f}")
                
            except Exception as e:
                print(f"   ❌ ERROR | {test['query'][:40]}... | Error: {e}")
        
        # Calculate percentages
        if intent_tests > 0:
            understanding_results['intent_recognition'] = (understanding_results['intent_recognition'] / intent_tests) * 100
        if entity_tests > 0:
            understanding_results['entity_extraction'] = (understanding_results['entity_extraction'] / entity_tests) * 100
        if complex_tests > 0:
            understanding_results['complex_understanding'] = (understanding_results['complex_understanding'] / complex_tests) * 100
        
        understanding_results['overall_understanding'] = (
            understanding_results['intent_recognition'] + 
            understanding_results['entity_extraction'] + 
            understanding_results['complex_understanding']
        ) / 3
        
        print(f"\n📊 Query Understanding Results:")
        print(f"   Intent Recognition: {understanding_results['intent_recognition']:.1f}%")
        print(f"   Entity Extraction: {understanding_results['entity_extraction']:.1f}%")
        print(f"   Complex Understanding: {understanding_results['complex_understanding']:.1f}%")
        print(f"   Overall Understanding: {understanding_results['overall_understanding']:.1f}%")
        
        self.training_results['query_understanding'] = understanding_results
        return understanding_results
    
    def verify_output_accuracy(self):
        """Verify output accuracy and correctness"""
        print("\n✅ VERIFYING OUTPUT ACCURACY")
        print("=" * 70)
        
        accuracy_tests = [
            {
                'query': 'What is the current MSP for wheat?',
                'language': 'en',
                'expected_elements': ['₹', 'per quintal', 'minimum support price', 'wheat'],
                'test_type': 'msp_accuracy'
            },
            {
                'query': 'दिल्ली में गेहूं की कीमत क्या है?',
                'language': 'hi',
                'expected_elements': ['₹', 'क्विंटल', 'गेहूं', 'दिल्ली'],
                'test_type': 'price_accuracy_hindi'
            },
            {
                'query': 'Best crops for Punjab soil',
                'language': 'en',
                'expected_elements': ['wheat', 'rice', 'maize', 'punjab', 'soil'],
                'test_type': 'crop_recommendation_accuracy'
            },
            {
                'query': 'PM Kisan scheme ke benefits kya hain?',
                'language': 'hinglish',
                'expected_elements': ['₹6000', 'yearly', 'benefits', 'pm kisan'],
                'test_type': 'scheme_accuracy_hinglish'
            }
        ]
        
        accuracy_results = {
            'total_tests': len(accuracy_tests),
            'accurate_responses': 0,
            'partially_accurate': 0,
            'inaccurate_responses': 0,
            'overall_accuracy': 0
        }
        
        for test in accuracy_tests:
            try:
                response = ultimate_ai.get_response(
                    user_query=test['query'],
                    language=test['language'],
                    location_name='Delhi'
                )
                
                response_text = response.get('response', '').lower()
                
                # Check for expected elements
                elements_found = sum(1 for element in test['expected_elements'] if element.lower() in response_text)
                accuracy_percentage = (elements_found / len(test['expected_elements'])) * 100
                
                if accuracy_percentage >= 80:
                    accuracy_results['accurate_responses'] += 1
                    status = "✅ ACCURATE"
                elif accuracy_percentage >= 50:
                    accuracy_results['partially_accurate'] += 1
                    status = "⚠️ PARTIAL"
                else:
                    accuracy_results['inaccurate_responses'] += 1
                    status = "❌ INACCURATE"
                
                print(f"   {status} | {test['test_type']} | Accuracy: {accuracy_percentage:.1f}%")
                
            except Exception as e:
                print(f"   ❌ ERROR | {test['test_type']} | Error: {e}")
                accuracy_results['inaccurate_responses'] += 1
        
        accuracy_results['overall_accuracy'] = (
            (accuracy_results['accurate_responses'] * 100) + 
            (accuracy_results['partially_accurate'] * 50) + 
            (accuracy_results['inaccurate_responses'] * 0)
        ) / accuracy_results['total_tests']
        
        print(f"\n📊 Output Accuracy Results:")
        print(f"   Accurate Responses: {accuracy_results['accurate_responses']}/{accuracy_results['total_tests']}")
        print(f"   Partially Accurate: {accuracy_results['partially_accurate']}/{accuracy_results['total_tests']}")
        print(f"   Overall Accuracy: {accuracy_results['overall_accuracy']:.1f}%")
        
        self.training_results['output_verification'] = accuracy_results
        return accuracy_results
    
    def generate_training_report(self):
        """Generate comprehensive training report"""
        print("\n📊 GENERATING COMPREHENSIVE TRAINING REPORT")
        print("=" * 70)
        
        # Calculate overall training score
        farming_training = self.training_results.get('farming_training', {})
        gov_api = self.training_results.get('government_api_integration', {})
        query_understanding = self.training_results.get('query_understanding', {})
        output_verification = self.training_results.get('output_verification', {})
        
        # Calculate overall score
        farming_score = farming_training.get('response_accuracy', 0)
        gov_score = gov_api.get('government_data_accuracy', 0)
        understanding_score = query_understanding.get('overall_understanding', 0)
        accuracy_score = output_verification.get('overall_accuracy', 0)
        
        overall_score = (farming_score + gov_score + understanding_score + accuracy_score) / 4
        
        # Determine training grade
        if overall_score >= 90:
            training_grade = "A+ (EXCELLENT)"
        elif overall_score >= 80:
            training_grade = "A (VERY GOOD)"
        elif overall_score >= 70:
            training_grade = "B (GOOD)"
        elif overall_score >= 60:
            training_grade = "C (AVERAGE)"
        else:
            training_grade = "D (NEEDS IMPROVEMENT)"
        
        training_report = {
            'timestamp': datetime.now().isoformat(),
            'overall_assessment': {
                'training_score': overall_score,
                'training_grade': training_grade,
                'farming_accuracy': farming_score,
                'government_integration': gov_score,
                'query_understanding': understanding_score,
                'output_accuracy': accuracy_score
            },
            'detailed_results': self.training_results,
            'recommendations': self._generate_training_recommendations(overall_score, farming_score, gov_score, understanding_score, accuracy_score)
        }
        
        # Display report
        print(f"\n🎯 ADVANCED FARMING AI TRAINING ASSESSMENT")
        print(f"Overall Training Score: {overall_score:.1f}%")
        print(f"Training Grade: {training_grade}")
        print(f"Farming Query Accuracy: {farming_score:.1f}%")
        print(f"Government API Integration: {gov_score:.1f}%")
        print(f"Query Understanding: {understanding_score:.1f}%")
        print(f"Output Accuracy: {accuracy_score:.1f}%")
        
        # Save report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f"advanced_farming_ai_training_report_{timestamp}.json"
        
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(training_report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Training report saved to: {report_filename}")
        
        return training_report
    
    def _generate_training_recommendations(self, overall_score, farming_score, gov_score, understanding_score, accuracy_score):
        """Generate training recommendations"""
        recommendations = []
        
        if overall_score < 80:
            recommendations.append("🔧 Critical: Overall training needs significant improvement")
        
        if farming_score < 80:
            recommendations.append("🌱 Farming: Improve farming query understanding and response accuracy")
        
        if gov_score < 70:
            recommendations.append("🏛️ Government APIs: Enhance government data integration and accuracy")
        
        if understanding_score < 80:
            recommendations.append("🎯 Query Understanding: Improve intent recognition and entity extraction")
        
        if accuracy_score < 80:
            recommendations.append("✅ Output Accuracy: Enhance response accuracy and government data verification")
        
        if not recommendations:
            recommendations.append("🎉 Excellent: AI training is performing optimally!")
        
        return recommendations
    
    def run_complete_training(self):
        """Run complete advanced farming AI training"""
        print("🚀 ADVANCED FARMING AI TRAINING SYSTEM")
        print("=" * 80)
        print("Comprehensive training focused on farming queries and government API integration")
        print("=" * 80)
        
        # Step 1: Generate comprehensive training data
        training_data = self.generate_comprehensive_farming_training_data()
        
        # Step 2: Train AI with farming data
        farming_results = self.train_ai_with_farming_data(training_data)
        
        # Step 3: Verify government API integration
        gov_api_results = self.verify_government_api_integration()
        
        # Step 4: Test query understanding
        understanding_results = self.test_query_understanding()
        
        # Step 5: Verify output accuracy
        accuracy_results = self.verify_output_accuracy()
        
        # Step 6: Generate comprehensive report
        training_report = self.generate_training_report()
        
        print(f"\n🎉 ADVANCED FARMING AI TRAINING COMPLETE!")
        print(f"📊 Training Grade: {training_report['overall_assessment']['training_grade']}")
        print(f"🎯 Overall Score: {training_report['overall_assessment']['training_score']:.1f}%")
        
        return training_report

def main():
    """Main function"""
    trainer = AdvancedFarmingAITrainer()
    return trainer.run_complete_training()

if __name__ == "__main__":
    main()

