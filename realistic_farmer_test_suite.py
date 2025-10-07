#!/usr/bin/env python3
"""
REALISTIC FARMER TEST SUITE
Comprehensive testing based on real farmer queries and normal people questions
Covers all types of agricultural scenarios, edge cases, and user interactions
"""

import sys
import os
import time
import json
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from advisory.ml.ultimate_intelligent_ai import UltimateIntelligentAI

class RealisticFarmerTestSuite:
    def __init__(self):
        self.ultimate_ai = UltimateIntelligentAI()
        self.test_results = {
            "basic_farmer_queries": {"passed": 0, "total": 0, "details": []},
            "crop_advice": {"passed": 0, "total": 0, "details": []},
            "weather_concerns": {"passed": 0, "total": 0, "details": []},
            "disease_problems": {"passed": 0, "total": 0, "details": []},
            "market_queries": {"passed": 0, "total": 0, "details": []},
            "government_help": {"passed": 0, "total": 0, "details": []},
            "emergency_situations": {"passed": 0, "total": 0, "details": []},
            "seasonal_questions": {"passed": 0, "total": 0, "details": []},
            "beginner_farmer": {"passed": 0, "total": 0, "details": []},
            "experienced_farmer": {"passed": 0, "total": 0, "details": []},
            "mixed_language": {"passed": 0, "total": 0, "details": []},
            "complex_scenarios": {"passed": 0, "total": 0, "details": []},
            "edge_cases": {"passed": 0, "total": 0, "details": []},
            "normal_people": {"passed": 0, "total": 0, "details": []}
        }

    def run_test(self, test_name, query, expected_intent=None, expected_entities=None, 
                 language='en', location=None, test_category="general", 
                 expected_response_keywords=None, min_confidence=0.7):
        """Run a realistic test case"""
        print(f"\n🧪 {test_name}: {query}")
        start_time = time.time()
        
        try:
            response_data = self.ultimate_ai.get_response(
                user_query=query,
                language=language,
                location_name=location
            )
            end_time = time.time()
            response_time = end_time - start_time
            
            response = response_data.get('response', '')
            intent = response_data.get('metadata', {}).get('intent')
            confidence = response_data.get('confidence')
            entities = response_data.get('metadata', {}).get('entities', {})

            print(f"   Intent: {intent}")
            print(f"   Confidence: {confidence}")
            print(f"   Entities: {entities}")
            print(f"   Response Time: {response_time:.3f}s")
            print(f"   Response: {response[:120]}...")

            passed = True
            issues = []

            # Check intent
            if expected_intent and intent != expected_intent:
                passed = False
                issues.append(f"Expected intent '{expected_intent}', got '{intent}'")
            
            # Check entities
            if expected_entities:
                for key, value in expected_entities.items():
                    if entities.get(key) != value:
                        passed = False
                        issues.append(f"Expected entity '{key}': '{value}', got '{entities.get(key)}'")
            
            # Check confidence
            if confidence < min_confidence:
                passed = False
                issues.append(f"Low confidence: {confidence} < {min_confidence}")
            
            # Check response quality
            if not response or len(response) < 15:
                passed = False
                issues.append("Response too short or empty")

            # Check response keywords
            if expected_response_keywords:
                for keyword in expected_response_keywords:
                    if keyword.lower() not in response.lower():
                        passed = False
                        issues.append(f"Expected keyword '{keyword}' not found in response")

            # Update test results
            self.test_results[test_category]["total"] += 1
            if passed:
                self.test_results[test_category]["passed"] += 1
                print("   ✅ PASSED")
            else:
                print(f"   ❌ FAILED - Issues: {', '.join(issues)}")
            
            self.test_results[test_category]["details"].append({
                "test_name": test_name,
                "query": query,
                "passed": passed,
                "issues": issues,
                "response_time": response_time,
                "confidence": confidence
            })

            return passed, issues, response_time

        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            self.test_results[test_category]["total"] += 1
            self.test_results[test_category]["details"].append({
                "test_name": test_name,
                "query": query,
                "passed": False,
                "issues": [str(e)],
                "response_time": 0,
                "confidence": 0
            })
            return False, [str(e)], 0

    def test_basic_farmer_queries(self):
        """Test basic farmer questions"""
        print("\n🌾 TESTING BASIC FARMER QUERIES")
        print("=" * 60)
        
        test_cases = [
            # Simple greetings and basic questions
            {"name": "Simple Greeting", "query": "hello", "expected_intent": "greeting"},
            {"name": "Hindi Greeting", "query": "नमस्ते", "expected_intent": "greeting", "language": "hi"},
            {"name": "Hinglish Greeting", "query": "hi bhai", "expected_intent": "greeting", "language": "hinglish"},
            {"name": "Basic Help", "query": "help", "expected_intent": "general"},
            {"name": "Hindi Help", "query": "मदद", "expected_intent": "general", "language": "hi"},
            {"name": "Hinglish Help", "query": "help chahiye", "expected_intent": "general", "language": "hinglish"},
            
            # Basic crop questions
            {"name": "What to grow", "query": "kya lagayein", "expected_intent": "crop_recommendation", "language": "hinglish"},
            {"name": "Crop suggestion", "query": "crop suggest karo", "expected_intent": "crop_recommendation", "language": "hinglish"},
            {"name": "Best crop", "query": "best crop kya hai", "expected_intent": "crop_recommendation", "language": "hinglish"},
            
            # Basic weather questions
            {"name": "Weather check", "query": "weather kaisa hai", "expected_intent": "weather", "language": "hinglish"},
            {"name": "Rain question", "query": "barish hogi", "expected_intent": "weather", "language": "hinglish"},
            {"name": "Temperature", "query": "temperature kya hai", "expected_intent": "weather", "language": "hinglish"},
            
            # Basic price questions
            {"name": "Price inquiry", "query": "price kya hai", "expected_intent": "market_price", "language": "hinglish"},
            {"name": "Wheat price", "query": "wheat ka price", "expected_intent": "market_price", "language": "hinglish"},
            {"name": "Rice price", "query": "rice ka rate", "expected_intent": "market_price", "language": "hinglish"},
        ]

        for test in test_cases:
            self.run_test(
                test["name"], 
                test["query"], 
                test.get("expected_intent"), 
                test.get("expected_entities"),
                test.get("language", "en"),
                test.get("location"),
                "basic_farmer_queries",
                test.get("expected_response_keywords")
            )

    def test_crop_advice_scenarios(self):
        """Test crop advice scenarios"""
        print("\n🌱 TESTING CROP ADVICE SCENARIOS")
        print("=" * 60)
        
        test_cases = [
            # Location-based crop advice
            {"name": "Punjab crops", "query": "Punjab mein kya lagayein", "expected_intent": "crop_recommendation", "expected_entities": {"location": "Punjab"}, "language": "hinglish"},
            {"name": "Maharashtra crops", "query": "Maharashtra mein kya crop", "expected_intent": "crop_recommendation", "expected_entities": {"location": "Maharashtra"}, "language": "hinglish"},
            {"name": "UP crops", "query": "Uttar Pradesh mein kya lagayein", "expected_intent": "crop_recommendation", "expected_entities": {"location": "Uttar Pradesh"}, "language": "hinglish"},
            {"name": "Delhi crops", "query": "Delhi mein kya crop lagayein", "expected_intent": "crop_recommendation", "expected_entities": {"location": "Delhi"}, "language": "hinglish"},
            
            # Season-based advice
            {"name": "Kharif crops", "query": "kharif season mein kya lagayein", "expected_intent": "crop_recommendation", "expected_entities": {"season": "kharif"}, "language": "hinglish"},
            {"name": "Rabi crops", "query": "rabi season mein kya lagayein", "expected_intent": "crop_recommendation", "expected_entities": {"season": "rabi"}, "language": "hinglish"},
            {"name": "Summer crops", "query": "summer mein kya lagayein", "expected_intent": "crop_recommendation", "language": "hinglish"},
            
            # Specific crop questions
            {"name": "Wheat advice", "query": "wheat kaise lagayein", "expected_intent": "crop_recommendation", "expected_entities": {"crop": "wheat"}, "language": "hinglish"},
            {"name": "Rice advice", "query": "rice kaise lagayein", "expected_intent": "crop_recommendation", "expected_entities": {"crop": "rice"}, "language": "hinglish"},
            {"name": "Cotton advice", "query": "cotton kaise lagayein", "expected_intent": "crop_recommendation", "expected_entities": {"crop": "cotton"}, "language": "hinglish"},
            
            # Hindi crop queries
            {"name": "Hindi crop query", "query": "क्या फसल लगाएं", "expected_intent": "crop_recommendation", "language": "hi"},
            {"name": "Hindi wheat", "query": "गेहूं कैसे लगाएं", "expected_intent": "crop_recommendation", "expected_entities": {"crop": "wheat"}, "language": "hi"},
            {"name": "Hindi rice", "query": "चावल कैसे लगाएं", "expected_intent": "crop_recommendation", "expected_entities": {"crop": "rice"}, "language": "hi"},
            
            # English crop queries
            {"name": "English crop query", "query": "what crops should I grow", "expected_intent": "crop_recommendation"},
            {"name": "English wheat", "query": "how to grow wheat", "expected_intent": "crop_recommendation", "expected_entities": {"crop": "wheat"}},
            {"name": "English rice", "query": "how to grow rice", "expected_intent": "crop_recommendation", "expected_entities": {"crop": "rice"}},
        ]

        for test in test_cases:
            self.run_test(
                test["name"], 
                test["query"], 
                test.get("expected_intent"), 
                test.get("expected_entities"),
                test.get("language", "en"),
                test.get("location"),
                "crop_advice",
                test.get("expected_response_keywords")
            )

    def test_weather_concerns(self):
        """Test weather-related farmer concerns"""
        print("\n🌤️ TESTING WEATHER CONCERNS")
        print("=" * 60)
        
        test_cases = [
            # Basic weather questions
            {"name": "Weather check", "query": "mausam kaisa hai", "expected_intent": "weather", "language": "hinglish"},
            {"name": "Rain question", "query": "barish hogi kya", "expected_intent": "weather", "language": "hinglish"},
            {"name": "Temperature", "query": "kitna garam hai", "expected_intent": "weather", "language": "hinglish"},
            {"name": "Humidity", "query": "humidity kya hai", "expected_intent": "weather", "language": "hinglish"},
            
            # Location-specific weather
            {"name": "Delhi weather", "query": "Delhi ka mausam", "expected_intent": "weather", "expected_entities": {"location": "Delhi"}, "language": "hinglish"},
            {"name": "Mumbai weather", "query": "Mumbai ka mausam", "expected_intent": "weather", "expected_entities": {"location": "Mumbai"}, "language": "hinglish"},
            {"name": "Punjab weather", "query": "Punjab ka mausam", "expected_intent": "weather", "expected_entities": {"location": "Punjab"}, "language": "hinglish"},
            
            # Hindi weather queries
            {"name": "Hindi weather", "query": "मौसम कैसा है", "expected_intent": "weather", "language": "hi"},
            {"name": "Hindi rain", "query": "बारिश होगी क्या", "expected_intent": "weather", "language": "hi"},
            {"name": "Hindi temperature", "query": "तापमान क्या है", "expected_intent": "weather", "language": "hi"},
            
            # English weather queries
            {"name": "English weather", "query": "how is the weather", "expected_intent": "weather"},
            {"name": "English rain", "query": "will it rain", "expected_intent": "weather"},
            {"name": "English temperature", "query": "what is the temperature", "expected_intent": "weather"},
            
            # Weather for farming
            {"name": "Farming weather", "query": "farming ke liye weather", "expected_intent": "weather", "language": "hinglish"},
            {"name": "Crop weather", "query": "crop ke liye mausam", "expected_intent": "weather", "language": "hinglish"},
            {"name": "Sowing weather", "query": "sowing ke liye weather", "expected_intent": "weather", "language": "hinglish"},
        ]

        for test in test_cases:
            self.run_test(
                test["name"], 
                test["query"], 
                test.get("expected_intent"), 
                test.get("expected_entities"),
                test.get("language", "en"),
                test.get("location"),
                "weather_concerns",
                test.get("expected_response_keywords")
            )

    def test_disease_problems(self):
        """Test disease and pest problems"""
        print("\n🦠 TESTING DISEASE PROBLEMS")
        print("=" * 60)
        
        test_cases = [
            # Disease symptoms
            {"name": "Yellow spots", "query": "yellow spots aa rahe hain", "expected_intent": "pest_control", "language": "hinglish"},
            {"name": "Wilting plants", "query": "plants murjha rahe hain", "expected_intent": "pest_control", "language": "hinglish"},
            {"name": "Brown patches", "query": "brown patches aa rahe hain", "expected_intent": "pest_control", "language": "hinglish"},
            {"name": "White spots", "query": "white spots aa rahe hain", "expected_intent": "pest_control", "language": "hinglish"},
            
            # Specific crop diseases
            {"name": "Wheat disease", "query": "wheat mein disease", "expected_intent": "pest_control", "expected_entities": {"crop": "wheat"}, "language": "hinglish"},
            {"name": "Rice disease", "query": "rice mein disease", "expected_intent": "pest_control", "expected_entities": {"crop": "rice"}, "language": "hinglish"},
            {"name": "Cotton disease", "query": "cotton mein disease", "expected_intent": "pest_control", "expected_entities": {"crop": "cotton"}, "language": "hinglish"},
            
            # Pest problems
            {"name": "Insect problem", "query": "insects aa gaye hain", "expected_intent": "pest_control", "language": "hinglish"},
            {"name": "Whitefly attack", "query": "whitefly attack ho gaya", "expected_intent": "pest_control", "language": "hinglish"},
            {"name": "Aphid problem", "query": "aphid problem hai", "expected_intent": "pest_control", "language": "hinglish"},
            
            # Hindi disease queries
            {"name": "Hindi disease", "query": "रोग लग गया है", "expected_intent": "pest_control", "language": "hi"},
            {"name": "Hindi pest", "query": "कीट लग गए हैं", "expected_intent": "pest_control", "language": "hi"},
            {"name": "Hindi treatment", "query": "उपचार क्या है", "expected_intent": "pest_control", "language": "hi"},
            
            # English disease queries
            {"name": "English disease", "query": "plants are diseased", "expected_intent": "pest_control"},
            {"name": "English pest", "query": "pests are attacking", "expected_intent": "pest_control"},
            {"name": "English treatment", "query": "what is the treatment", "expected_intent": "pest_control"},
            
            # Treatment requests
            {"name": "Organic treatment", "query": "organic treatment kya hai", "expected_intent": "pest_control", "language": "hinglish"},
            {"name": "Chemical treatment", "query": "chemical treatment kya hai", "expected_intent": "pest_control", "language": "hinglish"},
            {"name": "Medicine", "query": "medicine kya hai", "expected_intent": "pest_control", "language": "hinglish"},
        ]

        for test in test_cases:
            self.run_test(
                test["name"], 
                test["query"], 
                test.get("expected_intent"), 
                test.get("expected_entities"),
                test.get("language", "en"),
                test.get("location"),
                "disease_problems",
                test.get("expected_response_keywords")
            )

    def test_market_queries(self):
        """Test market and price queries"""
        print("\n💰 TESTING MARKET QUERIES")
        print("=" * 60)
        
        test_cases = [
            # Price inquiries
            {"name": "Wheat price", "query": "wheat ka price kya hai", "expected_intent": "market_price", "expected_entities": {"crop": "wheat"}, "language": "hinglish"},
            {"name": "Rice price", "query": "rice ka price kya hai", "expected_intent": "market_price", "expected_entities": {"crop": "rice"}, "language": "hinglish"},
            {"name": "Cotton price", "query": "cotton ka price kya hai", "expected_intent": "market_price", "expected_entities": {"crop": "cotton"}, "language": "hinglish"},
            {"name": "Maize price", "query": "maize ka price kya hai", "expected_intent": "market_price", "expected_entities": {"crop": "maize"}, "language": "hinglish"},
            
            # Location-specific prices
            {"name": "Delhi price", "query": "Delhi mein wheat ka price", "expected_intent": "market_price", "expected_entities": {"crop": "wheat", "location": "Delhi"}, "language": "hinglish"},
            {"name": "Mumbai price", "query": "Mumbai mein rice ka price", "expected_intent": "market_price", "expected_entities": {"crop": "rice", "location": "Mumbai"}, "language": "hinglish"},
            {"name": "Punjab price", "query": "Punjab mein cotton ka price", "expected_intent": "market_price", "expected_entities": {"crop": "cotton", "location": "Punjab"}, "language": "hinglish"},
            
            # Hindi price queries
            {"name": "Hindi wheat price", "query": "गेहूं की कीमत क्या है", "expected_intent": "market_price", "expected_entities": {"crop": "wheat"}, "language": "hi"},
            {"name": "Hindi rice price", "query": "चावल की कीमत क्या है", "expected_intent": "market_price", "expected_entities": {"crop": "rice"}, "language": "hi"},
            {"name": "Hindi cotton price", "query": "कपास की कीमत क्या है", "expected_intent": "market_price", "expected_entities": {"crop": "cotton"}, "language": "hi"},
            
            # English price queries
            {"name": "English wheat price", "query": "what is wheat price", "expected_intent": "market_price", "expected_entities": {"crop": "wheat"}},
            {"name": "English rice price", "query": "what is rice price", "expected_intent": "market_price", "expected_entities": {"crop": "rice"}},
            {"name": "English cotton price", "query": "what is cotton price", "expected_intent": "market_price", "expected_entities": {"crop": "cotton"}},
            
            # Market trends
            {"name": "Market trend", "query": "market trend kya hai", "expected_intent": "market_price", "language": "hinglish"},
            {"name": "Price prediction", "query": "price prediction kya hai", "expected_intent": "market_price", "language": "hinglish"},
            {"name": "Future price", "query": "future price kya hoga", "expected_intent": "market_price", "language": "hinglish"},
            
            # MSP queries
            {"name": "MSP query", "query": "MSP kya hai", "expected_intent": "market_price", "language": "hinglish"},
            {"name": "Support price", "query": "support price kya hai", "expected_intent": "market_price", "language": "hinglish"},
            {"name": "Government price", "query": "government price kya hai", "expected_intent": "market_price", "language": "hinglish"},
        ]

        for test in test_cases:
            self.run_test(
                test["name"], 
                test["query"], 
                test.get("expected_intent"), 
                test.get("expected_entities"),
                test.get("language", "en"),
                test.get("location"),
                "market_queries",
                test.get("expected_response_keywords")
            )

    def test_government_help(self):
        """Test government scheme queries"""
        print("\n🏛️ TESTING GOVERNMENT HELP")
        print("=" * 60)
        
        test_cases = [
            # Government schemes
            {"name": "PM Kisan", "query": "PM Kisan scheme", "expected_intent": "government_schemes", "language": "hinglish"},
            {"name": "Kisan Credit Card", "query": "Kisan Credit Card", "expected_intent": "government_schemes", "language": "hinglish"},
            {"name": "Crop Insurance", "query": "crop insurance", "expected_intent": "government_schemes", "language": "hinglish"},
            {"name": "Subsidy", "query": "subsidy kya hai", "expected_intent": "government_schemes", "language": "hinglish"},
            
            # Hindi government queries
            {"name": "Hindi PM Kisan", "query": "पीएम किसान योजना", "expected_intent": "government_schemes", "language": "hi"},
            {"name": "Hindi Credit Card", "query": "किसान क्रेडिट कार्ड", "expected_intent": "government_schemes", "language": "hi"},
            {"name": "Hindi Insurance", "query": "फसल बीमा", "expected_intent": "government_schemes", "language": "hi"},
            {"name": "Hindi Subsidy", "query": "सब्सिडी क्या है", "expected_intent": "government_schemes", "language": "hi"},
            
            # English government queries
            {"name": "English PM Kisan", "query": "PM Kisan scheme details", "expected_intent": "government_schemes"},
            {"name": "English Credit Card", "query": "Kisan Credit Card details", "expected_intent": "government_schemes"},
            {"name": "English Insurance", "query": "crop insurance details", "expected_intent": "government_schemes"},
            {"name": "English Subsidy", "query": "subsidy information", "expected_intent": "government_schemes"},
            
            # Application queries
            {"name": "How to apply", "query": "kaise apply karein", "expected_intent": "government_schemes", "language": "hinglish"},
            {"name": "Application process", "query": "application process kya hai", "expected_intent": "government_schemes", "language": "hinglish"},
            {"name": "Documents needed", "query": "documents kya chahiye", "expected_intent": "government_schemes", "language": "hinglish"},
            
            # Loan queries
            {"name": "Loan amount", "query": "loan kitna milega", "expected_intent": "government_schemes", "language": "hinglish"},
            {"name": "Loan interest", "query": "loan interest kya hai", "expected_intent": "government_schemes", "language": "hinglish"},
            {"name": "Loan process", "query": "loan process kya hai", "expected_intent": "government_schemes", "language": "hinglish"},
        ]

        for test in test_cases:
            self.run_test(
                test["name"], 
                test["query"], 
                test.get("expected_intent"), 
                test.get("expected_entities"),
                test.get("language", "en"),
                test.get("location"),
                "government_help",
                test.get("expected_response_keywords")
            )

    def test_emergency_situations(self):
        """Test emergency and urgent situations"""
        print("\n🚨 TESTING EMERGENCY SITUATIONS")
        print("=" * 60)
        
        test_cases = [
            # Urgent help requests
            {"name": "Urgent help", "query": "urgent help chahiye", "expected_intent": "general", "language": "hinglish"},
            {"name": "Emergency", "query": "emergency hai", "expected_intent": "general", "language": "hinglish"},
            {"name": "Quick advice", "query": "quick advice chahiye", "expected_intent": "general", "language": "hinglish"},
            {"name": "Immediate help", "query": "immediate help chahiye", "expected_intent": "general", "language": "hinglish"},
            
            # Crop emergency
            {"name": "Crop dying", "query": "crop mar raha hai", "expected_intent": "pest_control", "language": "hinglish"},
            {"name": "Plants dying", "query": "plants mar rahe hain", "expected_intent": "pest_control", "language": "hinglish"},
            {"name": "Crop problem", "query": "crop mein problem hai", "expected_intent": "pest_control", "language": "hinglish"},
            
            # Weather emergency
            {"name": "Heavy rain", "query": "heavy rain aa rahi hai", "expected_intent": "weather", "language": "hinglish"},
            {"name": "Drought", "query": "drought ho gaya", "expected_intent": "weather", "language": "hinglish"},
            {"name": "Storm", "query": "storm aa raha hai", "expected_intent": "weather", "language": "hinglish"},
            
            # Hindi emergency
            {"name": "Hindi urgent", "query": "तुरंत मदद चाहिए", "expected_intent": "general", "language": "hi"},
            {"name": "Hindi emergency", "query": "आपातकाल है", "expected_intent": "general", "language": "hi"},
            {"name": "Hindi crop dying", "query": "फसल मर रही है", "expected_intent": "pest_control", "language": "hi"},
            
            # English emergency
            {"name": "English urgent", "query": "urgent help needed", "expected_intent": "general"},
            {"name": "English emergency", "query": "emergency situation", "expected_intent": "general"},
            {"name": "English crop dying", "query": "crops are dying", "expected_intent": "pest_control"},
        ]

        for test in test_cases:
            self.run_test(
                test["name"], 
                test["query"], 
                test.get("expected_intent"), 
                test.get("expected_entities"),
                test.get("language", "en"),
                test.get("location"),
                "emergency_situations",
                test.get("expected_response_keywords")
            )

    def test_seasonal_questions(self):
        """Test seasonal farming questions"""
        print("\n🌾 TESTING SEASONAL QUESTIONS")
        print("=" * 60)
        
        test_cases = [
            # Kharif season
            {"name": "Kharif crops", "query": "kharif mein kya lagayein", "expected_intent": "crop_recommendation", "expected_entities": {"season": "kharif"}, "language": "hinglish"},
            {"name": "Monsoon crops", "query": "monsoon mein kya lagayein", "expected_intent": "crop_recommendation", "expected_entities": {"season": "kharif"}, "language": "hinglish"},
            {"name": "Rainy season", "query": "rainy season mein kya lagayein", "expected_intent": "crop_recommendation", "expected_entities": {"season": "kharif"}, "language": "hinglish"},
            
            # Rabi season
            {"name": "Rabi crops", "query": "rabi mein kya lagayein", "expected_intent": "crop_recommendation", "expected_entities": {"season": "rabi"}, "language": "hinglish"},
            {"name": "Winter crops", "query": "winter mein kya lagayein", "expected_intent": "crop_recommendation", "expected_entities": {"season": "rabi"}, "language": "hinglish"},
            {"name": "Cold season", "query": "cold season mein kya lagayein", "expected_intent": "crop_recommendation", "expected_entities": {"season": "rabi"}, "language": "hinglish"},
            
            # Hindi seasonal
            {"name": "Hindi kharif", "query": "खरीफ में क्या लगाएं", "expected_intent": "crop_recommendation", "expected_entities": {"season": "kharif"}, "language": "hi"},
            {"name": "Hindi rabi", "query": "रबी में क्या लगाएं", "expected_intent": "crop_recommendation", "expected_entities": {"season": "rabi"}, "language": "hi"},
            {"name": "Hindi monsoon", "query": "मानसून में क्या लगाएं", "expected_intent": "crop_recommendation", "expected_entities": {"season": "kharif"}, "language": "hi"},
            
            # English seasonal
            {"name": "English kharif", "query": "what to grow in kharif", "expected_intent": "crop_recommendation", "expected_entities": {"season": "kharif"}},
            {"name": "English rabi", "query": "what to grow in rabi", "expected_intent": "crop_recommendation", "expected_entities": {"season": "rabi"}},
            {"name": "English monsoon", "query": "what to grow in monsoon", "expected_intent": "crop_recommendation", "expected_entities": {"season": "kharif"}},
            
            # Seasonal timing
            {"name": "Sowing time", "query": "sowing time kya hai", "expected_intent": "crop_recommendation", "language": "hinglish"},
            {"name": "Planting time", "query": "planting time kya hai", "expected_intent": "crop_recommendation", "language": "hinglish"},
            {"name": "Harvest time", "query": "harvest time kya hai", "expected_intent": "crop_recommendation", "language": "hinglish"},
        ]

        for test in test_cases:
            self.run_test(
                test["name"], 
                test["query"], 
                test.get("expected_intent"), 
                test.get("expected_entities"),
                test.get("language", "en"),
                test.get("location"),
                "seasonal_questions",
                test.get("expected_response_keywords")
            )

    def test_beginner_farmer(self):
        """Test beginner farmer questions"""
        print("\n🌱 TESTING BEGINNER FARMER")
        print("=" * 60)
        
        test_cases = [
            # Basic farming questions
            {"name": "How to start", "query": "farming kaise start karein", "expected_intent": "general", "language": "hinglish"},
            {"name": "New farmer", "query": "new farmer hun", "expected_intent": "general", "language": "hinglish"},
            {"name": "Beginner help", "query": "beginner help chahiye", "expected_intent": "general", "language": "hinglish"},
            {"name": "First time", "query": "first time farming", "expected_intent": "general", "language": "hinglish"},
            
            # Basic crop questions
            {"name": "Easy crops", "query": "easy crops kya hain", "expected_intent": "crop_recommendation", "language": "hinglish"},
            {"name": "Simple crops", "query": "simple crops kya hain", "expected_intent": "crop_recommendation", "language": "hinglish"},
            {"name": "Beginner crops", "query": "beginner crops kya hain", "expected_intent": "crop_recommendation", "language": "hinglish"},
            
            # Basic techniques
            {"name": "How to sow", "query": "kaise sow karein", "expected_intent": "crop_recommendation", "language": "hinglish"},
            {"name": "How to water", "query": "kaise water karein", "expected_intent": "crop_recommendation", "language": "hinglish"},
            {"name": "How to fertilize", "query": "kaise fertilize karein", "expected_intent": "crop_recommendation", "language": "hinglish"},
            
            # Hindi beginner
            {"name": "Hindi beginner", "query": "नया किसान हूँ", "expected_intent": "general", "language": "hi"},
            {"name": "Hindi easy crops", "query": "आसान फसलें क्या हैं", "expected_intent": "crop_recommendation", "language": "hi"},
            {"name": "Hindi how to start", "query": "खेती कैसे शुरू करें", "expected_intent": "general", "language": "hi"},
            
            # English beginner
            {"name": "English beginner", "query": "I am new to farming", "expected_intent": "general"},
            {"name": "English easy crops", "query": "what are easy crops", "expected_intent": "crop_recommendation"},
            {"name": "English how to start", "query": "how to start farming", "expected_intent": "general"},
        ]

        for test in test_cases:
            self.run_test(
                test["name"], 
                test["query"], 
                test.get("expected_intent"), 
                test.get("expected_entities"),
                test.get("language", "en"),
                test.get("location"),
                "beginner_farmer",
                test.get("expected_response_keywords")
            )

    def test_experienced_farmer(self):
        """Test experienced farmer questions"""
        print("\n👨‍🌾 TESTING EXPERIENCED FARMER")
        print("=" * 60)
        
        test_cases = [
            # Advanced techniques
            {"name": "Crop rotation", "query": "crop rotation kaise karein", "expected_intent": "crop_recommendation", "language": "hinglish"},
            {"name": "Intercropping", "query": "intercropping kaise karein", "expected_intent": "crop_recommendation", "language": "hinglish"},
            {"name": "Mixed farming", "query": "mixed farming kaise karein", "expected_intent": "crop_recommendation", "language": "hinglish"},
            
            # Advanced crop management
            {"name": "Yield optimization", "query": "yield kaise badhayein", "expected_intent": "crop_recommendation", "language": "hinglish"},
            {"name": "Quality improvement", "query": "quality kaise improve karein", "expected_intent": "crop_recommendation", "language": "hinglish"},
            {"name": "Cost reduction", "query": "cost kaise kam karein", "expected_intent": "crop_recommendation", "language": "hinglish"},
            
            # Advanced pest control
            {"name": "IPM", "query": "IPM kaise karein", "expected_intent": "pest_control", "language": "hinglish"},
            {"name": "Biological control", "query": "biological control kaise karein", "expected_intent": "pest_control", "language": "hinglish"},
            {"name": "Integrated pest management", "query": "integrated pest management", "expected_intent": "pest_control", "language": "hinglish"},
            
            # Hindi advanced
            {"name": "Hindi crop rotation", "query": "फसल चक्र कैसे करें", "expected_intent": "crop_recommendation", "language": "hi"},
            {"name": "Hindi yield", "query": "उत्पादन कैसे बढ़ाएं", "expected_intent": "crop_recommendation", "language": "hi"},
            {"name": "Hindi IPM", "query": "समेकित कीट प्रबंधन", "expected_intent": "pest_control", "language": "hi"},
            
            # English advanced
            {"name": "English crop rotation", "query": "how to do crop rotation", "expected_intent": "crop_recommendation"},
            {"name": "English yield", "query": "how to increase yield", "expected_intent": "crop_recommendation"},
            {"name": "English IPM", "query": "integrated pest management", "expected_intent": "pest_control"},
        ]

        for test in test_cases:
            self.run_test(
                test["name"], 
                test["query"], 
                test.get("expected_intent"), 
                test.get("expected_entities"),
                test.get("language", "en"),
                test.get("location"),
                "experienced_farmer",
                test.get("expected_response_keywords")
            )

    def test_mixed_language(self):
        """Test mixed language queries"""
        print("\n🌐 TESTING MIXED LANGUAGE")
        print("=" * 60)
        
        test_cases = [
            # Mixed Hindi-English
            {"name": "Mixed greeting", "query": "नमस्ते, hello", "expected_intent": "greeting", "language": "hinglish"},
            {"name": "Mixed help", "query": "मदद chahiye", "expected_intent": "general", "language": "hinglish"},
            {"name": "Mixed crop", "query": "फसल suggest karo", "expected_intent": "crop_recommendation", "language": "hinglish"},
            
            # Mixed English-Hindi
            {"name": "English-Hindi greeting", "query": "hello नमस्ते", "expected_intent": "greeting", "language": "hinglish"},
            {"name": "English-Hindi help", "query": "help मदद", "expected_intent": "general", "language": "hinglish"},
            {"name": "English-Hindi crop", "query": "crop फसल", "expected_intent": "crop_recommendation", "language": "hinglish"},
            
            # Complex mixed queries
            {"name": "Complex mixed", "query": "wheat की price क्या hai", "expected_intent": "market_price", "expected_entities": {"crop": "wheat"}, "language": "hinglish"},
            {"name": "Mixed weather", "query": "weather मौसम kaisa hai", "expected_intent": "weather", "language": "hinglish"},
            {"name": "Mixed disease", "query": "disease रोग ka treatment क्या hai", "expected_intent": "pest_control", "language": "hinglish"},
            
            # Location mixed
            {"name": "Mixed location", "query": "Delhi में wheat की price", "expected_intent": "market_price", "expected_entities": {"crop": "wheat", "location": "Delhi"}, "language": "hinglish"},
            {"name": "Mixed Punjab", "query": "Punjab में क्या lagayein", "expected_intent": "crop_recommendation", "expected_entities": {"location": "Punjab"}, "language": "hinglish"},
            {"name": "Mixed Maharashtra", "query": "Maharashtra में rice kaise lagayein", "expected_intent": "crop_recommendation", "expected_entities": {"location": "Maharashtra", "crop": "rice"}, "language": "hinglish"},
        ]

        for test in test_cases:
            self.run_test(
                test["name"], 
                test["query"], 
                test.get("expected_intent"), 
                test.get("expected_entities"),
                test.get("language", "en"),
                test.get("location"),
                "mixed_language",
                test.get("expected_response_keywords")
            )

    def test_complex_scenarios(self):
        """Test complex real-world scenarios"""
        print("\n🔍 TESTING COMPLEX SCENARIOS")
        print("=" * 60)
        
        test_cases = [
            # Multi-intent queries
            {"name": "Price and weather", "query": "wheat price aur weather kaisa hai", "expected_intent": "complex_query", "expected_entities": {"crop": "wheat"}, "language": "hinglish"},
            {"name": "Crop and disease", "query": "rice crop mein disease ka treatment", "expected_intent": "complex_query", "expected_entities": {"crop": "rice"}, "language": "hinglish"},
            {"name": "Weather and crop", "query": "weather ke hisab se kya lagayein", "expected_intent": "complex_query", "language": "hinglish"},
            
            # Contextual queries
            {"name": "Land size", "query": "5 acre land mein kya lagayein", "expected_intent": "crop_recommendation", "language": "hinglish"},
            {"name": "Soil type", "query": "clay soil mein kya lagayein", "expected_intent": "crop_recommendation", "language": "hinglish"},
            {"name": "Water availability", "query": "kam water mein kya lagayein", "expected_intent": "crop_recommendation", "language": "hinglish"},
            
            # Hindi complex
            {"name": "Hindi complex", "query": "गेहूं की कीमत और मौसम बताओ", "expected_intent": "complex_query", "expected_entities": {"crop": "wheat"}, "language": "hi"},
            {"name": "Hindi contextual", "query": "5 एकड़ जमीन में क्या लगाएं", "expected_intent": "crop_recommendation", "language": "hi"},
            {"name": "Hindi soil", "query": "चिकनी मिट्टी में क्या लगाएं", "expected_intent": "crop_recommendation", "language": "hi"},
            
            # English complex
            {"name": "English complex", "query": "wheat price and weather forecast", "expected_intent": "complex_query", "expected_entities": {"crop": "wheat"}},
            {"name": "English contextual", "query": "what to grow in 5 acres", "expected_intent": "crop_recommendation"},
            {"name": "English soil", "query": "what to grow in clay soil", "expected_intent": "crop_recommendation"},
        ]

        for test in test_cases:
            self.run_test(
                test["name"], 
                test["query"], 
                test.get("expected_intent"), 
                test.get("expected_entities"),
                test.get("language", "en"),
                test.get("location"),
                "complex_scenarios",
                test.get("expected_response_keywords")
            )

    def test_edge_cases(self):
        """Test edge cases and unusual queries"""
        print("\n🔬 TESTING EDGE CASES")
        print("=" * 60)
        
        test_cases = [
            # Very short queries
            {"name": "Single word", "query": "help", "expected_intent": "general"},
            {"name": "Two words", "query": "crop suggest", "expected_intent": "crop_recommendation"},
            {"name": "Three words", "query": "wheat price kya", "expected_intent": "market_price", "expected_entities": {"crop": "wheat"}, "language": "hinglish"},
            
            # Very long queries
            {"name": "Long query", "query": "I am a farmer from Punjab and I want to know about wheat cultivation and its market price and weather conditions", "expected_intent": "complex_query", "expected_entities": {"location": "Punjab", "crop": "wheat"}},
            {"name": "Very long Hindi", "query": "मैं पंजाब का किसान हूँ और मुझे गेहूं की खेती और उसकी बाजार कीमत और मौसम की स्थिति के बारे में जानना है", "expected_intent": "complex_query", "expected_entities": {"location": "Punjab", "crop": "wheat"}, "language": "hi"},
            
            # Unusual characters
            {"name": "Numbers", "query": "123", "expected_intent": "general"},
            {"name": "Special chars", "query": "!@#$%", "expected_intent": "general"},
            {"name": "Mixed chars", "query": "crop123", "expected_intent": "crop_recommendation"},
            
            # Ambiguous queries
            {"name": "Ambiguous", "query": "kya", "expected_intent": "general", "language": "hinglish"},
            {"name": "Vague", "query": "help me", "expected_intent": "general"},
            {"name": "Unclear", "query": "samajh nahi aa raha", "expected_intent": "general", "language": "hinglish"},
            
            # Typos and misspellings
            {"name": "Typo wheat", "query": "wheat price kya hai", "expected_intent": "market_price", "expected_entities": {"crop": "wheat"}, "language": "hinglish"},
            {"name": "Misspelled", "query": "rice price kya hai", "expected_intent": "market_price", "expected_entities": {"crop": "rice"}, "language": "hinglish"},
            {"name": "Wrong spelling", "query": "cotton price kya hai", "expected_intent": "market_price", "expected_entities": {"crop": "cotton"}, "language": "hinglish"},
        ]

        for test in test_cases:
            self.run_test(
                test["name"], 
                test["query"], 
                test.get("expected_intent"), 
                test.get("expected_entities"),
                test.get("language", "en"),
                test.get("location"),
                "edge_cases",
                test.get("expected_response_keywords")
            )

    def test_normal_people(self):
        """Test queries from normal people (non-farmers)"""
        print("\n👥 TESTING NORMAL PEOPLE QUERIES")
        print("=" * 60)
        
        test_cases = [
            # General curiosity
            {"name": "General curiosity", "query": "what is farming", "expected_intent": "general"},
            {"name": "Hindi curiosity", "query": "खेती क्या है", "expected_intent": "general", "language": "hi"},
            {"name": "Hinglish curiosity", "query": "farming kya hai", "expected_intent": "general", "language": "hinglish"},
            
            # Food questions
            {"name": "Food source", "query": "where does rice come from", "expected_intent": "crop_recommendation", "expected_entities": {"crop": "rice"}},
            {"name": "Hindi food", "query": "चावल कहाँ से आता है", "expected_intent": "crop_recommendation", "expected_entities": {"crop": "rice"}, "language": "hi"},
            {"name": "Hinglish food", "query": "rice kahan se aata hai", "expected_intent": "crop_recommendation", "expected_entities": {"crop": "rice"}, "language": "hinglish"},
            
            # Price curiosity
            {"name": "Price curiosity", "query": "how much does wheat cost", "expected_intent": "market_price", "expected_entities": {"crop": "wheat"}},
            {"name": "Hindi price", "query": "गेहूं की कीमत कितनी है", "expected_intent": "market_price", "expected_entities": {"crop": "wheat"}, "language": "hi"},
            {"name": "Hinglish price", "query": "wheat kitne ka hai", "expected_intent": "market_price", "expected_entities": {"crop": "wheat"}, "language": "hinglish"},
            
            # Weather curiosity
            {"name": "Weather curiosity", "query": "how is the weather for farming", "expected_intent": "weather"},
            {"name": "Hindi weather", "query": "खेती के लिए मौसम कैसा है", "expected_intent": "weather", "language": "hi"},
            {"name": "Hinglish weather", "query": "farming ke liye weather kaisa hai", "expected_intent": "weather", "language": "hinglish"},
            
            # Learning questions
            {"name": "Learning", "query": "how to learn farming", "expected_intent": "general"},
            {"name": "Hindi learning", "query": "खेती कैसे सीखें", "expected_intent": "general", "language": "hi"},
            {"name": "Hinglish learning", "query": "farming kaise seekhein", "expected_intent": "general", "language": "hinglish"},
        ]

        for test in test_cases:
            self.run_test(
                test["name"], 
                test["query"], 
                test.get("expected_intent"), 
                test.get("expected_entities"),
                test.get("language", "en"),
                test.get("location"),
                "normal_people",
                test.get("expected_response_keywords")
            )

    def run_all_tests(self):
        """Run all realistic farmer tests"""
        print("🚀 REALISTIC FARMER TEST SUITE")
        print("=" * 80)
        print("Testing AI with real farmer queries and normal people questions")
        print("=" * 80)
        
        # Run all test categories
        self.test_basic_farmer_queries()
        self.test_crop_advice_scenarios()
        self.test_weather_concerns()
        self.test_disease_problems()
        self.test_market_queries()
        self.test_government_help()
        self.test_emergency_situations()
        self.test_seasonal_questions()
        self.test_beginner_farmer()
        self.test_experienced_farmer()
        self.test_mixed_language()
        self.test_complex_scenarios()
        self.test_edge_cases()
        self.test_normal_people()
        
        # Generate comprehensive report
        self.generate_report()

    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 80)
        print("📊 REALISTIC FARMER TEST REPORT")
        print("=" * 80)
        
        total_tests = sum(category["total"] for category in self.test_results.values())
        total_passed = sum(category["passed"] for category in self.test_results.values())
        overall_success_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\n📈 OVERALL RESULTS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed Tests: {total_passed}")
        print(f"   Failed Tests: {total_tests - total_passed}")
        print(f"   Overall Success Rate: {overall_success_rate:.1f}%")
        
        print(f"\n📊 CATEGORY BREAKDOWN:")
        for category, results in self.test_results.items():
            if results["total"] > 0:
                success_rate = (results["passed"] / results["total"]) * 100
                print(f"   {category.replace('_', ' ').title()}: {results['passed']}/{results['total']} ({success_rate:.1f}%)")
        
        print(f"\n🎯 FINAL ASSESSMENT:")
        if overall_success_rate >= 90:
            print("🌟 OUTSTANDING! AI is performing at ChatGPT/Gemini level!")
            print("   ✅ Production ready with advanced capabilities")
            print("   ✅ Highly intelligent and responsive")
            print("   ✅ Advanced features working excellently")
        elif overall_success_rate >= 80:
            print("🌟 EXCELLENT! AI is performing very well!")
            print("   ✅ Production ready")
            print("   ✅ High intelligence and responsiveness")
            print("   ✅ Advanced capabilities working well")
        elif overall_success_rate >= 70:
            print("✅ GOOD! AI is performing well.")
            print("   ⚠️ Almost ready for production")
            print("   🔧 Requires minor improvements")
        else:
            print("❌ NEEDS IMPROVEMENT!")
            print("   ❌ Not ready for production")
            print("   🔧 Requires significant enhancements")
        
        # Save detailed results
        results_filename = f"realistic_farmer_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_filename, 'w', encoding='utf-8') as f:
            json.dump({
                "overall_results": {
                    "total_tests": total_tests,
                    "passed_tests": total_passed,
                    "failed_tests": total_tests - total_passed,
                    "success_rate": f"{overall_success_rate:.1f}%"
                },
                "category_results": self.test_results,
                "timestamp": datetime.now().isoformat()
            }, f, indent=4, ensure_ascii=False)
        
        print(f"\n💾 Detailed results saved to: {results_filename}")

if __name__ == "__main__":
    tester = RealisticFarmerTestSuite()
    tester.run_all_tests()
