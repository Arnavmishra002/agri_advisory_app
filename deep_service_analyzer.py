#!/usr/bin/env python3
"""
Deep Service Analyzer - Tests each service component individually and thoroughly
"""

import requests
import json
import time
import random
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DeepServiceAnalyzer:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.analysis_results = {}
        
        # Deep test scenarios
        self.deep_test_scenarios = {
            'crop_database_verification': [
                'vegetables', 'fruits', 'spices', 'medicinal', 'cash_crop', 
                'cereal', 'pulse', 'oilseed'
            ],
            'location_coverage': [
                'Delhi', 'Mumbai', 'Bangalore', 'Chennai', 'Hyderabad', 
                'Pune', 'Kolkata', 'Ahmedabad', 'Jaipur', 'Lucknow'
            ],
            'language_coverage': ['hi', 'en', 'hinglish'],
            'query_complexity': [
                'simple', 'medium', 'complex', 'multi_intent'
            ]
        }

    def analyze_crop_recommendation_depth(self):
        """Deep analysis of crop recommendation system"""
        logger.info("🔍 DEEP ANALYSIS: Crop Recommendation System")
        
        analysis = {
            'crop_types_found': [],
            'profitability_analysis': {},
            'location_variations': {},
            'scoring_consistency': {},
            'government_data_integration': {},
            'issues_found': []
        }
        
        # Test each crop type
        for crop_type in self.deep_test_scenarios['crop_database_verification']:
            logger.info(f"   Testing crop type: {crop_type}")
            
            query = f"Delhi mein {crop_type} fasal lagayein"
            try:
                payload = {
                    'query': query,
                    'language': 'hinglish',
                    'latitude': 28.7041,
                    'longitude': 77.1025,
                    'location': 'Delhi'
                }
                
                response = requests.post(f"{self.base_url}/api/chatbot/", 
                                       json=payload, 
                                       headers={'Content-Type': 'application/json'},
                                       timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get('response', '')
                    
                    # Analyze response for crop type
                    if crop_type.lower() in response_text.lower():
                        analysis['crop_types_found'].append(crop_type)
                    
                    # Extract profitability scores
                    import re
                    scores = re.findall(r'स्कोर: (\d+\.?\d*)/100', response_text)
                    if scores:
                        analysis['profitability_analysis'][crop_type] = {
                            'scores_found': len(scores),
                            'avg_score': sum(float(s) for s in scores) / len(scores),
                            'max_score': max(float(s) for s in scores),
                            'min_score': min(float(s) for s in scores)
                        }
                    
                    # Check for government data indicators
                    gov_indicators = ['सरकारी', 'Government', 'IMD', 'ICAR', 'Agmarknet']
                    gov_count = sum(1 for indicator in gov_indicators if indicator in response_text)
                    analysis['government_data_integration'][crop_type] = gov_count
                    
                else:
                    analysis['issues_found'].append(f"Crop type {crop_type}: HTTP {response.status_code}")
                    
            except Exception as e:
                analysis['issues_found'].append(f"Crop type {crop_type}: {str(e)}")
        
        # Test location variations
        for location in self.deep_test_scenarios['location_coverage'][:5]:  # Test first 5 locations
            logger.info(f"   Testing location: {location}")
            
            query = f"{location} mein kya fasal lagayein"
            try:
                payload = {
                    'query': query,
                    'language': 'hinglish',
                    'latitude': 28.7041,
                    'longitude': 77.1025,
                    'location': location
                }
                
                response = requests.post(f"{self.base_url}/api/chatbot/", 
                                       json=payload, 
                                       headers={'Content-Type': 'application/json'},
                                       timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get('response', '')
                    
                    # Check for location-specific content
                    location_mentioned = location in response_text
                    
                    # Extract top crop scores
                    import re
                    scores = re.findall(r'स्कोर: (\d+\.?\d*)/100', response_text)
                    
                    analysis['location_variations'][location] = {
                        'location_mentioned': location_mentioned,
                        'scores_found': len(scores),
                        'top_score': max(float(s) for s in scores) if scores else 0,
                        'response_length': len(response_text)
                    }
                    
                else:
                    analysis['issues_found'].append(f"Location {location}: HTTP {response.status_code}")
                    
            except Exception as e:
                analysis['issues_found'].append(f"Location {location}: {str(e)}")
        
        self.analysis_results['crop_recommendations'] = analysis
        return analysis

    def analyze_weather_system_depth(self):
        """Deep analysis of weather system"""
        logger.info("🌤️ DEEP ANALYSIS: Weather System")
        
        analysis = {
            'forecast_completeness': {},
            'historical_data_integration': {},
            'location_accuracy': {},
            'advisory_quality': {},
            'issues_found': []
        }
        
        # Test weather forecast completeness
        for location in self.deep_test_scenarios['location_coverage'][:5]:
            logger.info(f"   Testing weather for: {location}")
            
            query = f"{location} ka mausam kaisa hai"
            try:
                payload = {
                    'query': query,
                    'language': 'hinglish',
                    'latitude': 28.7041,
                    'longitude': 77.1025,
                    'location': location
                }
                
                response = requests.post(f"{self.base_url}/api/chatbot/", 
                                       json=payload, 
                                       headers={'Content-Type': 'application/json'},
                                       timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get('response', '')
                    
                    # Check forecast completeness
                    forecast_indicators = [
                        'वर्तमान मौसम' in response_text or 'Current Weather' in response_text,
                        'पूर्वानुमान' in response_text or 'Forecast' in response_text,
                        'तापमान' in response_text or 'Temperature' in response_text,
                        'आर्द्रता' in response_text or 'Humidity' in response_text,
                        'किसानों के लिए सुझाव' in response_text or 'Farmer\'s Advisory' in response_text
                    ]
                    
                    analysis['forecast_completeness'][location] = {
                        'indicators_found': sum(forecast_indicators),
                        'has_current_weather': forecast_indicators[0],
                        'has_forecast': forecast_indicators[1],
                        'has_temperature': forecast_indicators[2],
                        'has_humidity': forecast_indicators[3],
                        'has_farmer_advisory': forecast_indicators[4]
                    }
                    
                    # Check historical data integration
                    historical_indicators = [
                        'ऐतिहासिक' in response_text or 'Historical' in response_text,
                        'पिछले वर्ष' in response_text or 'Last Year' in response_text,
                        'मौसमी' in response_text or 'Seasonal' in response_text
                    ]
                    
                    analysis['historical_data_integration'][location] = {
                        'historical_indicators': sum(historical_indicators),
                        'has_historical_data': any(historical_indicators)
                    }
                    
                    # Check advisory quality
                    advisory_indicators = [
                        'फसल सुझाव' in response_text or 'Crop Advisory' in response_text,
                        'सिंचाई सुझाव' in response_text or 'Irrigation Advisory' in response_text,
                        'कीट सुझाव' in response_text or 'Pest Advisory' in response_text
                    ]
                    
                    analysis['advisory_quality'][location] = {
                        'advisory_types': sum(advisory_indicators),
                        'has_crop_advisory': advisory_indicators[0],
                        'has_irrigation_advisory': advisory_indicators[1],
                        'has_pest_advisory': advisory_indicators[2]
                    }
                    
                else:
                    analysis['issues_found'].append(f"Weather {location}: HTTP {response.status_code}")
                    
            except Exception as e:
                analysis['issues_found'].append(f"Weather {location}: {str(e)}")
        
        self.analysis_results['weather_system'] = analysis
        return analysis

    def analyze_market_prices_depth(self):
        """Deep analysis of market prices system"""
        logger.info("💰 DEEP ANALYSIS: Market Prices System")
        
        analysis = {
            'price_data_accuracy': {},
            'crop_coverage': {},
            'location_variations': {},
            'government_source_attribution': {},
            'issues_found': []
        }
        
        # Test different crops
        crops_to_test = ['wheat', 'rice', 'tomato', 'onion', 'potato', 'sugar', 'maize', 'cotton', 'turmeric', 'ginger']
        
        for crop in crops_to_test:
            logger.info(f"   Testing market price for: {crop}")
            
            query = f"Delhi mein {crop} ka price kya hai"
            try:
                payload = {
                    'query': query,
                    'language': 'hinglish',
                    'latitude': 28.7041,
                    'longitude': 77.1025,
                    'location': 'Delhi'
                }
                
                response = requests.post(f"{self.base_url}/api/chatbot/", 
                                       json=payload, 
                                       headers={'Content-Type': 'application/json'},
                                       timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get('response', '')
                    
                    # Check price data accuracy
                    has_currency = '₹' in response_text
                    has_unit = 'क्विंटल' in response_text or 'quintal' in response_text
                    has_government_source = any(source in response_text for source in ['सरकारी', 'Government', 'Agmarknet', 'e-NAM'])
                    
                    analysis['price_data_accuracy'][crop] = {
                        'has_currency': has_currency,
                        'has_unit': has_unit,
                        'has_government_source': has_government_source,
                        'response_length': len(response_text)
                    }
                    
                    # Check crop coverage
                    crop_mentioned = crop.lower() in response_text.lower()
                    analysis['crop_coverage'][crop] = crop_mentioned
                    
                    # Check government source attribution
                    gov_sources = []
                    if 'Agmarknet' in response_text:
                        gov_sources.append('Agmarknet')
                    if 'e-NAM' in response_text:
                        gov_sources.append('e-NAM')
                    if 'सरकारी' in response_text:
                        gov_sources.append('Government')
                    
                    analysis['government_source_attribution'][crop] = gov_sources
                    
                else:
                    analysis['issues_found'].append(f"Market price {crop}: HTTP {response.status_code}")
                    
            except Exception as e:
                analysis['issues_found'].append(f"Market price {crop}: {str(e)}")
        
        self.analysis_results['market_prices'] = analysis
        return analysis

    def analyze_ai_intelligence_depth(self):
        """Deep analysis of AI intelligence system"""
        logger.info("🤖 DEEP ANALYSIS: AI Intelligence System")
        
        analysis = {
            'query_type_handling': {},
            'response_quality': {},
            'context_understanding': {},
            'language_switching': {},
            'issues_found': []
        }
        
        # Test different query types
        query_types = {
            'agricultural': [
                'Delhi mein kya fasal lagayein?',
                'How to prevent pest attacks?',
                'What is soil health?',
                'Government schemes for farmers?'
            ],
            'general_knowledge': [
                'What is artificial intelligence?',
                'Explain machine learning',
                'How does weather affect climate?',
                'What is photosynthesis?'
            ],
            'mixed_intent': [
                'Hello, I want to know about farming in Delhi',
                'What is AI and how can it help farmers?',
                'Tell me about weather and crop recommendations'
            ]
        }
        
        for query_type, queries in query_types.items():
            logger.info(f"   Testing query type: {query_type}")
            
            type_results = []
            for query in queries:
                try:
                    payload = {
                        'query': query,
                        'language': 'en',
                        'latitude': 28.7041,
                        'longitude': 77.1025,
                        'location': 'Delhi'
                    }
                    
                    response = requests.post(f"{self.base_url}/api/chatbot/", 
                                           json=payload, 
                                           headers={'Content-Type': 'application/json'},
                                           timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        response_text = data.get('response', '')
                        
                        # Analyze response quality
                        quality_indicators = {
                            'substantial_response': len(response_text) > 100,
                            'relevant_content': any(word in response_text.lower() for word in query.lower().split()[:3]),
                            'not_generic': not response_text.startswith('Sorry') and not response_text.startswith('I don\'t'),
                            'well_structured': '•' in response_text or '**' in response_text or len(response_text.split('\n')) > 3
                        }
                        
                        type_results.append({
                            'query': query[:50] + '...' if len(query) > 50 else query,
                            'quality_score': sum(quality_indicators.values()),
                            'indicators': quality_indicators,
                            'response_length': len(response_text)
                        })
                        
                    else:
                        analysis['issues_found'].append(f"AI Intelligence {query_type}: HTTP {response.status_code}")
                        
                except Exception as e:
                    analysis['issues_found'].append(f"AI Intelligence {query_type}: {str(e)}")
            
            analysis['query_type_handling'][query_type] = type_results
        
        self.analysis_results['ai_intelligence'] = analysis
        return analysis

    def analyze_system_performance_depth(self):
        """Deep analysis of system performance"""
        logger.info("⚡ DEEP ANALYSIS: System Performance")
        
        analysis = {
            'response_times': {},
            'throughput_analysis': {},
            'error_rates': {},
            'scalability_indicators': {},
            'issues_found': []
        }
        
        # Test response times under different loads
        test_scenarios = [
            {'query': 'Delhi mein kya fasal lagayein?', 'type': 'crop_recommendations'},
            {'query': 'Delhi ka mausam kaisa hai?', 'type': 'weather'},
            {'query': 'Delhi mein wheat ka price kya hai?', 'type': 'market_prices'},
            {'query': 'What is artificial intelligence?', 'type': 'ai_intelligence'}
        ]
        
        for scenario in test_scenarios:
            logger.info(f"   Testing performance for: {scenario['type']}")
            
            times = []
            errors = 0
            
            # Run multiple requests to test consistency
            for i in range(5):
                try:
                    start_time = time.time()
                    payload = {
                        'query': scenario['query'],
                        'language': 'hinglish',
                        'latitude': 28.7041,
                        'longitude': 77.1025,
                        'location': 'Delhi'
                    }
                    
                    response = requests.post(f"{self.base_url}/api/chatbot/", 
                                           json=payload, 
                                           headers={'Content-Type': 'application/json'},
                                           timeout=15)
                    
                    response_time = time.time() - start_time
                    
                    if response.status_code == 200:
                        times.append(response_time)
                    else:
                        errors += 1
                        
                except Exception as e:
                    errors += 1
                    analysis['issues_found'].append(f"Performance test {scenario['type']}: {str(e)}")
            
            if times:
                analysis['response_times'][scenario['type']] = {
                    'average': sum(times) / len(times),
                    'min': min(times),
                    'max': max(times),
                    'consistency': max(times) - min(times),  # Lower is better
                    'success_rate': len(times) / (len(times) + errors) * 100
                }
                
                analysis['error_rates'][scenario['type']] = {
                    'errors': errors,
                    'error_rate': errors / (len(times) + errors) * 100
                }
        
        self.analysis_results['system_performance'] = analysis
        return analysis

    def run_deep_analysis(self):
        """Run all deep analyses"""
        logger.info("🔍 Starting Deep Service Analysis...")
        logger.info("=" * 80)
        
        start_time = time.time()
        
        # Run all deep analyses
        analyses = [
            self.analyze_crop_recommendation_depth,
            self.analyze_weather_system_depth,
            self.analyze_market_prices_depth,
            self.analyze_ai_intelligence_depth,
            self.analyze_system_performance_depth
        ]
        
        for analysis_method in analyses:
            try:
                analysis_method()
                time.sleep(1)  # Brief pause between analyses
            except Exception as e:
                logger.error(f"❌ Analysis method {analysis_method.__name__} failed: {e}")
        
        total_time = time.time() - start_time
        
        # Generate deep analysis report
        self.generate_deep_analysis_report(total_time)
        
        return self.analysis_results

    def generate_deep_analysis_report(self, total_time):
        """Generate comprehensive deep analysis report"""
        logger.info("📊 Generating Deep Analysis Report...")
        logger.info("=" * 80)
        
        # Overall analysis summary
        total_issues = sum(len(analysis.get('issues_found', [])) for analysis in self.analysis_results.values())
        
        logger.info(f"🎯 DEEP ANALYSIS SUMMARY:")
        logger.info(f"   Analysis Time: {total_time:.2f} seconds")
        logger.info(f"   Total Issues Found: {total_issues}")
        logger.info(f"   Services Analyzed: {len(self.analysis_results)}")
        
        # Service-specific deep analysis
        for service, analysis in self.analysis_results.items():
            logger.info(f"\n🔧 {service.upper().replace('_', ' ')} DEEP ANALYSIS:")
            
            if service == 'crop_recommendations':
                crop_types_found = len(analysis.get('crop_types_found', []))
                logger.info(f"   Crop Types Detected: {crop_types_found}/8")
                logger.info(f"   Profitability Analysis: {len(analysis.get('profitability_analysis', {}))} crops analyzed")
                logger.info(f"   Location Variations: {len(analysis.get('location_variations', {}))} locations tested")
                
            elif service == 'weather_system':
                forecast_complete = len(analysis.get('forecast_completeness', {}))
                historical_data = sum(1 for loc_data in analysis.get('historical_data_integration', {}).values() 
                                    if loc_data.get('has_historical_data', False))
                logger.info(f"   Forecast Completeness: {forecast_complete} locations tested")
                logger.info(f"   Historical Data Integration: {historical_data}/{forecast_complete} locations")
                
            elif service == 'market_prices':
                price_accuracy = len(analysis.get('price_data_accuracy', {}))
                gov_sources = sum(len(sources) for sources in analysis.get('government_source_attribution', {}).values())
                logger.info(f"   Price Data Accuracy: {price_accuracy} crops tested")
                logger.info(f"   Government Source Attribution: {gov_sources} sources found")
                
            elif service == 'ai_intelligence':
                query_types = len(analysis.get('query_type_handling', {}))
                total_queries = sum(len(queries) for queries in analysis.get('query_type_handling', {}).values())
                logger.info(f"   Query Types Handled: {query_types}")
                logger.info(f"   Total Queries Tested: {total_queries}")
                
            elif service == 'system_performance':
                services_tested = len(analysis.get('response_times', {}))
                avg_response_time = sum(perf.get('average', 0) for perf in analysis.get('response_times', {}).values()) / services_tested if services_tested > 0 else 0
                logger.info(f"   Services Performance Tested: {services_tested}")
                logger.info(f"   Average Response Time: {avg_response_time:.2f}s")
            
            # Show issues for this service
            issues = analysis.get('issues_found', [])
            if issues:
                logger.info(f"   Issues Found: {len(issues)}")
                for issue in issues[:3]:  # Show first 3 issues
                    logger.info(f"     • {issue}")
                if len(issues) > 3:
                    logger.info(f"     ... and {len(issues) - 3} more issues")
            else:
                logger.info(f"   Issues Found: 0 ✅")
        
        # Save detailed analysis report
        report_filename = f"deep_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(self.analysis_results, f, indent=2, default=str)
        
        logger.info(f"\n📄 Detailed analysis report saved to: {report_filename}")
        logger.info("=" * 80)

def main():
    """Main function to run deep analysis"""
    print("🔍 Starting Deep Service Analysis Suite")
    print("=" * 80)
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/api/health/", timeout=5)
        if response.status_code != 200:
            print("❌ Server not responding. Please start the server first:")
            print("   python manage.py runserver 8000")
            return
    except:
        print("❌ Cannot connect to server. Please start the server first:")
        print("   python manage.py runserver 8000")
        return
    
    # Run deep analysis
    analyzer = DeepServiceAnalyzer()
    results = analyzer.run_deep_analysis()
    
    print("\n🎉 Deep analysis completed!")
    print("Check the generated report for detailed findings.")

if __name__ == "__main__":
    main()




