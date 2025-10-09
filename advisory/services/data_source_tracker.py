#!/usr/bin/env python3
"""
Data Source Tracker for AI Assistant
Tracks and monitors data sources for farming queries
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class DataSourceTracker:
    """Tracks data sources used in AI responses"""
    
    def __init__(self):
        self.data_sources = {
            'government': {
                'name': 'Government APIs',
                'description': 'Official government agricultural data',
                'apis': ['agmarknet', 'enam', 'imd', 'fci', 'apmc'],
                'usage_count': 0,
                'last_used': None,
                'reliability': 'high'
            },
            'ml_model': {
                'name': 'Machine Learning Models',
                'description': 'AI/ML models for predictions',
                'apis': ['crop_recommendation', 'yield_prediction', 'fertilizer_recommendation'],
                'usage_count': 0,
                'last_used': None,
                'reliability': 'high'
            },
            'weather_api': {
                'name': 'Weather Services',
                'description': 'Weather data and forecasts',
                'apis': ['imd_weather', 'openweathermap'],
                'usage_count': 0,
                'last_used': None,
                'reliability': 'high'
            },
            'opentdb': {
                'name': 'Open Trivia Database',
                'description': 'Trivia questions and quiz data',
                'apis': ['trivia_api'],
                'usage_count': 0,
                'last_used': None,
                'reliability': 'medium'
            },
            'wikipedia': {
                'name': 'Wikipedia API',
                'description': 'General knowledge information',
                'apis': ['wikipedia_search'],
                'usage_count': 0,
                'last_used': None,
                'reliability': 'high'
            },
            'numbers_api': {
                'name': 'Numbers API',
                'description': 'Number facts and trivia',
                'apis': ['numbers_facts'],
                'usage_count': 0,
                'last_used': None,
                'reliability': 'medium'
            },
            'bored_api': {
                'name': 'Bored API',
                'description': 'Activity suggestions',
                'apis': ['activity_suggestions'],
                'usage_count': 0,
                'last_used': None,
                'reliability': 'medium'
            },
            'fallback': {
                'name': 'Fallback System',
                'description': 'Built-in knowledge and fallback responses',
                'apis': ['built_in_knowledge'],
                'usage_count': 0,
                'last_used': None,
                'reliability': 'high'
            }
        }
        
        self.query_log = []
        self.performance_metrics = {
            'total_queries': 0,
            'farming_queries': 0,
            'general_queries': 0,
            'mixed_queries': 0,
            'government_data_usage': 0,
            'ml_model_usage': 0,
            'api_success_rate': {},
            'avg_response_time': 0
        }
    
    def track_query(self, query: str, response: Dict[str, Any], query_type: str, 
                   response_time: float, detected_sources: List[str]) -> Dict[str, Any]:
        """Track a query and its data sources"""
        
        # Update performance metrics
        self.performance_metrics['total_queries'] += 1
        if query_type == 'farming':
            self.performance_metrics['farming_queries'] += 1
        elif query_type == 'general':
            self.performance_metrics['general_queries'] += 1
        elif query_type == 'mixed':
            self.performance_metrics['mixed_queries'] += 1
        
        # Update data source usage
        for source in detected_sources:
            if source in self.data_sources:
                self.data_sources[source]['usage_count'] += 1
                self.data_sources[source]['last_used'] = datetime.now().isoformat()
                
                if source in ['government', 'ml_model']:
                    if query_type == 'farming':
                        self.performance_metrics['government_data_usage'] += 1
                        self.performance_metrics['ml_model_usage'] += 1
        
        # Log query details
        query_log_entry = {
            'timestamp': datetime.now().isoformat(),
            'query': query[:100] + '...' if len(query) > 100 else query,
            'query_type': query_type,
            'detected_sources': detected_sources,
            'response_time': response_time,
            'has_response': bool(response.get('response')),
            'response_length': len(response.get('response', '')),
            'confidence': response.get('confidence', 0)
        }
        
        self.query_log.append(query_log_entry)
        
        # Keep only last 1000 queries
        if len(self.query_log) > 1000:
            self.query_log = self.query_log[-1000:]
        
        return query_log_entry
    
    def get_data_source_report(self) -> Dict[str, Any]:
        """Generate comprehensive data source report"""
        
        # Calculate usage statistics
        total_usage = sum(source['usage_count'] for source in self.data_sources.values())
        
        source_usage = {}
        for source_name, source_data in self.data_sources.items():
            usage_percentage = (source_data['usage_count'] / total_usage * 100) if total_usage > 0 else 0
            source_usage[source_name] = {
                'name': source_data['name'],
                'description': source_data['description'],
                'usage_count': source_data['usage_count'],
                'usage_percentage': usage_percentage,
                'last_used': source_data['last_used'],
                'reliability': source_data['reliability']
            }
        
        # Calculate farming-specific metrics
        farming_sources = ['government', 'ml_model', 'weather_api', 'fallback']
        farming_usage = sum(self.data_sources[source]['usage_count'] for source in farming_sources)
        farming_percentage = (farming_usage / total_usage * 100) if total_usage > 0 else 0
        
        # Calculate general query sources
        general_sources = ['opentdb', 'wikipedia', 'numbers_api', 'bored_api']
        general_usage = sum(self.data_sources[source]['usage_count'] for source in general_sources)
        general_percentage = (general_usage / total_usage * 100) if total_usage > 0 else 0
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_queries': self.performance_metrics['total_queries'],
            'farming_queries': self.performance_metrics['farming_queries'],
            'general_queries': self.performance_metrics['general_queries'],
            'mixed_queries': self.performance_metrics['mixed_queries'],
            'source_usage': source_usage,
            'farming_data_usage': {
                'total_usage': farming_usage,
                'percentage': farming_percentage,
                'primary_sources': farming_sources
            },
            'general_data_usage': {
                'total_usage': general_usage,
                'percentage': general_percentage,
                'primary_sources': general_sources
            },
            'government_api_verification': {
                'government_data_usage': self.performance_metrics['government_data_usage'],
                'ml_model_usage': self.performance_metrics['ml_model_usage'],
                'government_reliability': 'high' if farming_percentage > 50 else 'medium'
            },
            'recent_queries': self.query_log[-10:] if self.query_log else []
        }
    
    def get_intelligence_score(self) -> Dict[str, Any]:
        """Calculate intelligence score based on data usage and performance"""
        
        total_queries = self.performance_metrics['total_queries']
        if total_queries == 0:
            return {'score': 0, 'details': 'No queries processed yet'}
        
        # Calculate different intelligence factors
        farming_accuracy = (self.performance_metrics['farming_queries'] / total_queries) * 0.4
        government_usage = (self.performance_metrics['government_data_usage'] / total_queries) * 0.3
        ml_usage = (self.performance_metrics['ml_model_usage'] / total_queries) * 0.2
        diversity_score = len([s for s in self.data_sources.values() if s['usage_count'] > 0]) / len(self.data_sources) * 0.1
        
        intelligence_score = farming_accuracy + government_usage + ml_usage + diversity_score
        
        return {
            'overall_score': intelligence_score,
            'max_score': 1.0,
            'grade': self._get_grade(intelligence_score),
            'details': {
                'farming_accuracy': farming_accuracy,
                'government_usage': government_usage,
                'ml_usage': ml_usage,
                'diversity_score': diversity_score
            },
            'recommendations': self._get_recommendations(intelligence_score)
        }
    
    def _get_grade(self, score: float) -> str:
        """Convert score to letter grade"""
        if score >= 0.9:
            return 'A+'
        elif score >= 0.8:
            return 'A'
        elif score >= 0.7:
            return 'B+'
        elif score >= 0.6:
            return 'B'
        elif score >= 0.5:
            return 'C'
        else:
            return 'D'
    
    def _get_recommendations(self, score: float) -> List[str]:
        """Get recommendations based on intelligence score"""
        recommendations = []
        
        if score < 0.6:
            recommendations.append("Consider improving query classification logic")
            recommendations.append("Increase government API integration")
            recommendations.append("Enhance ML model usage for farming queries")
        
        if score < 0.7:
            recommendations.append("Optimize data source selection")
            recommendations.append("Improve response quality and accuracy")
        
        if score < 0.8:
            recommendations.append("Fine-tune agricultural knowledge base")
            recommendations.append("Enhance multilingual support")
        
        if score >= 0.8:
            recommendations.append("Excellent performance! Consider adding more specialized agricultural features")
        
        return recommendations
    
    def export_report(self, filename: Optional[str] = None) -> str:
        """Export comprehensive report to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ai_data_source_report_{timestamp}.json"
        
        report = {
            'data_source_report': self.get_data_source_report(),
            'intelligence_score': self.get_intelligence_score(),
            'performance_metrics': self.performance_metrics,
            'query_log': self.query_log[-100:] if self.query_log else [],  # Last 100 queries
            'generated_at': datetime.now().isoformat()
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return filename

# Create global instance
data_source_tracker = DataSourceTracker()

