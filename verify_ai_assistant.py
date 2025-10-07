#!/usr/bin/env python3
"""
AI Assistant Verification Script
Tests all query types and verifies government data integration
"""

import requests
import json
import time
from typing import Dict, List, Any

class AIAssistantVerifier:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        
    def test_api_connection(self) -> bool:
        """Test if API is accessible"""
        try:
            response = requests.get(f"{self.base_url}/api/schema/swagger-ui/", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def send_query(self, query: str, language: str = "hi", location: str = "Delhi", 
                   lat: float = 28.6139, lon: float = 77.2090) -> Dict[str, Any]:
        """Send query to AI assistant"""
        try:
            response = requests.post(
                f"{self.base_url}/api/advisories/chatbot/",
                json={
                    'query': query,
                    'language': language,
                    'session_id': f'verify-{int(time.time())}',
                    'latitude': lat,
                    'longitude': lon,
                    'location_name': location
                },
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {'error': f'HTTP {response.status_code}', 'response': 'API Error'}
                
        except Exception as e:
            return {'error': str(e), 'response': 'Connection Error'}
    
    def verify_query(self, test_name: str, query: str, expected_features: List[str] = None) -> Dict[str, Any]:
        """Verify a single query"""
        print(f"\n🔍 Testing: {test_name}")
        print(f"📝 Query: '{query}'")
        
        result = self.send_query(query)
        
        verification = {
            'test_name': test_name,
            'query': query,
            'status_code': result.get('status_code', 'N/A'),
            'response': result.get('response', 'No response'),
            'intent': result.get('metadata', {}).get('intent', 'unknown'),
            'confidence': result.get('confidence', 0),
            'source': result.get('source', 'unknown'),
            'passed': False,
            'issues': [],
            'features_found': []
        }
        
        # Check for error responses
        if "क्षमा करें" in result.get('response', '') or "Sorry" in result.get('response', ''):
            verification['issues'].append("Generic error response")
        
        # Check for expected features
        if expected_features:
            for feature in expected_features:
                if feature.lower() in result.get('response', '').lower():
                    verification['features_found'].append(feature)
                else:
                    verification['issues'].append(f"Missing expected feature: {feature}")
        
        # Check response quality
        response_text = result.get('response', '')
        if len(response_text) < 50:
            verification['issues'].append("Response too short")
        
        # Check for government data indicators
        government_indicators = ['सरकारी', 'government', 'scheme', 'योजना', 'subsidy', 'सब्सिडी']
        for indicator in government_indicators:
            if indicator.lower() in response_text.lower():
                verification['features_found'].append(f"Government data: {indicator}")
        
        # Check for predictive elements
        predictive_indicators = ['सुझाव', 'recommendation', 'prediction', 'forecast', 'trend', 'रुझान']
        for indicator in predictive_indicators:
            if indicator.lower() in response_text.lower():
                verification['features_found'].append(f"Predictive element: {indicator}")
        
        # Determine if test passed
        verification['passed'] = len(verification['issues']) == 0
        
        if verification['passed']:
            print(f"✅ PASSED")
        else:
            print(f"❌ FAILED: {', '.join(verification['issues'])}")
        
        print(f"📊 Intent: {verification['intent']}")
        print(f"📊 Confidence: {verification['confidence']}")
        print(f"📊 Response: {response_text[:150]}...")
        
        self.test_results.append(verification)
        return verification
    
    def test_crop_recommendations(self):
        """Test crop recommendation queries"""
        print("\n🌾 TESTING CROP RECOMMENDATIONS")
        print("=" * 50)
        
        crop_queries = [
            ("Basic crop suggestion", "crop suggest karo lucknow mei", ["crop", "suggestion", "लखनऊ"]),
            ("Hindi crop suggestion", "फसल सुझाव दो लखनऊ में", ["फसल", "सुझाव", "लखनऊ"]),
            ("Seasonal crop query", "kharif season mein kya crop lagayein", ["kharif", "crop", "season"]),
            ("Soil-specific query", "loamy soil mein kya crop lagayein", ["loamy", "soil", "crop"]),
            ("Location-specific UP", "uttar pradesh mein kya crop lagayein", ["uttar pradesh", "crop"]),
            ("Location-specific Punjab", "punjab mein kya crop lagayein", ["punjab", "crop"]),
            ("Location-specific Maharashtra", "maharashtra mein kya crop lagayein", ["maharashtra", "crop"]),
            ("Location-specific Karnataka", "karnataka mein kya crop lagayein", ["karnataka", "crop"]),
            ("Location-specific Tamil Nadu", "tamil nadu mein kya crop lagayein", ["tamil nadu", "crop"]),
            ("Location-specific Gujarat", "gujarat mein kya crop lagayein", ["gujarat", "crop"]),
        ]
        
        for test_name, query, expected_features in crop_queries:
            self.verify_query(test_name, query, expected_features)
    
    def test_market_prices(self):
        """Test market price queries"""
        print("\n💰 TESTING MARKET PRICES")
        print("=" * 50)
        
        price_queries = [
            ("Wheat price Delhi", "wheat price in delhi", ["wheat", "price", "delhi"]),
            ("Rice price Mumbai", "rice price in mumbai", ["rice", "price", "mumbai"]),
            ("Potato price Lucknow", "potato price in lucknow", ["potato", "price", "lucknow"]),
            ("Hindi wheat price", "गेहूं की कीमत दिल्ली में", ["गेहूं", "कीमत", "दिल्ली"]),
            ("Hindi rice price", "चावल की कीमत मुंबई में", ["चावल", "कीमत", "मुंबई"]),
            ("Hindi potato price", "आलू की कीमत लखनऊ में", ["आलू", "कीमत", "लखनऊ"]),
            ("Market price query", "market price of wheat", ["market", "price", "wheat"]),
            ("Mandi price query", "wheat price in delhi mandi", ["wheat", "price", "mandi"]),
        ]
        
        for test_name, query, expected_features in price_queries:
            self.verify_query(test_name, query, expected_features)
    
    def test_weather_queries(self):
        """Test weather queries"""
        print("\n🌤️ TESTING WEATHER QUERIES")
        print("=" * 50)
        
        weather_queries = [
            ("Basic weather query", "weather in delhi", ["weather", "delhi"]),
            ("Hindi weather query", "दिल्ली में मौसम", ["मौसम", "दिल्ली"]),
            ("Temperature query", "temperature in mumbai", ["temperature", "mumbai"]),
            ("Rain query", "rain in bangalore", ["rain", "bangalore"]),
            ("Hindi temperature", "मुंबई में तापमान", ["तापमान", "मुंबई"]),
            ("Hindi rain", "बैंगलोर में बारिश", ["बारिश", "बैंगलोर"]),
            ("Weather forecast", "weather forecast for delhi", ["weather", "forecast", "delhi"]),
            ("Hindi weather forecast", "दिल्ली के लिए मौसम पूर्वानुमान", ["मौसम", "पूर्वानुमान", "दिल्ली"]),
        ]
        
        for test_name, query, expected_features in weather_queries:
            self.verify_query(test_name, query, expected_features)
    
    def test_pest_control(self):
        """Test pest control queries"""
        print("\n🐛 TESTING PEST CONTROL")
        print("=" * 50)
        
        pest_queries = [
            ("Basic pest query", "pest control for wheat", ["pest", "control", "wheat"]),
            ("Hindi pest query", "गेहूं में कीट नियंत्रण", ["कीट", "नियंत्रण", "गेहूं"]),
            ("Disease query", "disease in rice", ["disease", "rice"]),
            ("Hindi disease query", "चावल में रोग", ["रोग", "चावल"]),
            ("Pest identification", "identify pest in potato", ["identify", "pest", "potato"]),
            ("Hindi pest identification", "आलू में कीट की पहचान", ["कीट", "पहचान", "आलू"]),
            ("Pest treatment", "pest treatment for tomato", ["pest", "treatment", "tomato"]),
            ("Hindi pest treatment", "टमाटर में कीट उपचार", ["कीट", "उपचार", "टमाटर"]),
        ]
        
        for test_name, query, expected_features in pest_queries:
            self.verify_query(test_name, query, expected_features)
    
    def test_government_schemes(self):
        """Test government scheme queries"""
        print("\n🏛️ TESTING GOVERNMENT SCHEMES")
        print("=" * 50)
        
        scheme_queries = [
            ("Government schemes", "government schemes for farmers", ["government", "schemes", "farmers"]),
            ("Hindi schemes", "किसानों के लिए सरकारी योजनाएं", ["सरकारी", "योजनाएं", "किसानों"]),
            ("Subsidy query", "subsidy for agriculture", ["subsidy", "agriculture"]),
            ("Hindi subsidy", "कृषि के लिए सब्सिडी", ["सब्सिडी", "कृषि"]),
            ("PM Kisan", "PM Kisan scheme", ["PM Kisan", "scheme"]),
            ("Hindi PM Kisan", "PM किसान योजना", ["PM किसान", "योजना"]),
            ("Crop insurance", "crop insurance scheme", ["crop", "insurance", "scheme"]),
            ("Hindi crop insurance", "फसल बीमा योजना", ["फसल", "बीमा", "योजना"]),
        ]
        
        for test_name, query, expected_features in scheme_queries:
            self.verify_query(test_name, query, expected_features)
    
    def test_multilingual_queries(self):
        """Test multilingual queries"""
        print("\n🌍 TESTING MULTILINGUAL QUERIES")
        print("=" * 50)
        
        multilingual_queries = [
            ("English crop query", "crop recommendation for delhi", ["crop", "recommendation", "delhi"]),
            ("Hindi crop query", "दिल्ली के लिए फसल सुझाव", ["फसल", "सुझाव", "दिल्ली"]),
            ("Hinglish crop query", "delhi के लिए crop suggest करो", ["crop", "suggest", "delhi"]),
            ("English price query", "wheat price in delhi", ["wheat", "price", "delhi"]),
            ("Hindi price query", "दिल्ली में गेहूं की कीमत", ["गेहूं", "कीमत", "दिल्ली"]),
            ("Hinglish price query", "delhi में wheat की price", ["wheat", "price", "delhi"]),
            ("English weather query", "weather in delhi", ["weather", "delhi"]),
            ("Hindi weather query", "दिल्ली में मौसम", ["मौसम", "दिल्ली"]),
            ("Hinglish weather query", "delhi में weather कैसा है", ["weather", "delhi"]),
        ]
        
        for test_name, query, expected_features in multilingual_queries:
            self.verify_query(test_name, query, expected_features)
    
    def test_complex_queries(self):
        """Test complex queries"""
        print("\n🔗 TESTING COMPLEX QUERIES")
        print("=" * 50)
        
        complex_queries = [
            ("Complex crop weather", "crop suggest karo lucknow mein aur weather bhi batao", ["crop", "weather", "lucknow"]),
            ("Complex price weather", "wheat price in delhi aur weather bhi batao", ["wheat", "price", "weather", "delhi"]),
            ("Complex pest crop", "pest control for wheat aur crop suggest bhi karo", ["pest", "control", "wheat", "crop"]),
            ("Complex location crop", "lucknow mein kya crop lagayein aur weather kaisa hai", ["crop", "weather", "lucknow"]),
            ("Complex season crop", "kharif season mein kya crop lagayein lucknow mein", ["kharif", "season", "crop", "lucknow"]),
            ("Complex soil crop", "loamy soil mein kya crop lagayein delhi mein", ["loamy", "soil", "crop", "delhi"]),
            ("Complex price location", "wheat price in delhi mandi aur mumbai mandi", ["wheat", "price", "delhi", "mumbai"]),
            ("Complex weather location", "weather in delhi aur mumbai mein", ["weather", "delhi", "mumbai"]),
        ]
        
        for test_name, query, expected_features in complex_queries:
            self.verify_query(test_name, query, expected_features)
    
    def run_all_tests(self):
        """Run all verification tests"""
        print("🚀 STARTING AI ASSISTANT VERIFICATION")
        print("=" * 60)
        
        if not self.test_api_connection():
            print("❌ API connection failed. Please start the server first.")
            return False
        
        print("✅ API connection successful. Starting verification...")
        
        # Run all test suites
        self.test_crop_recommendations()
        self.test_market_prices()
        self.test_weather_queries()
        self.test_pest_control()
        self.test_government_schemes()
        self.test_multilingual_queries()
        self.test_complex_queries()
        
        # Generate verification report
        self.generate_verification_report()
        
        return True
    
    def generate_verification_report(self):
        """Generate comprehensive verification report"""
        print("\n📊 AI ASSISTANT VERIFICATION REPORT")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['passed']])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"📈 Total Tests: {total_tests}")
        print(f"✅ Passed Tests: {passed_tests}")
        print(f"❌ Failed Tests: {failed_tests}")
        print(f"📊 Success Rate: {success_rate:.2f}%")
        
        # Analyze features found
        all_features = []
        for result in self.test_results:
            all_features.extend(result['features_found'])
        
        feature_counts = {}
        for feature in all_features:
            feature_counts[feature] = feature_counts.get(feature, 0) + 1
        
        if feature_counts:
            print(f"\n🔍 Features Found:")
            for feature, count in sorted(feature_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"   • {feature}: {count} times")
        
        # Show failed tests
        failed_tests = [result for result in self.test_results if not result['passed']]
        if failed_tests:
            print(f"\n❌ Failed Tests Details:")
            for result in failed_tests[:10]:  # Show first 10 failures
                print(f"   • {result['test_name']}: {', '.join(result['issues'])}")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        if success_rate >= 90:
            print("   🎉 Excellent! The AI assistant is performing very well.")
        elif success_rate >= 80:
            print("   👍 Good performance! Minor improvements needed.")
        elif success_rate >= 70:
            print("   ⚠️ Moderate performance. Several improvements needed.")
        else:
            print("   🚨 Poor performance. Major improvements required.")
        
        print(f"\n📝 Detailed results saved to verification_results.json")
        
        # Save detailed results
        with open('verification_results.json', 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)

def main():
    """Main function to run AI assistant verification"""
    verifier = AIAssistantVerifier()
    
    print("🤖 AI Assistant Verification")
    print("Testing all query types and government data integration...")
    
    success = verifier.run_all_tests()
    
    if success:
        print("\n🎯 Verification completed successfully!")
        print("Check the verification report above for detailed results.")
    else:
        print("\n❌ Verification failed. Please check the server status.")

if __name__ == "__main__":
    main()
