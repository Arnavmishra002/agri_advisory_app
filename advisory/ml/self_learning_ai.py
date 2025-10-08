#!/usr/bin/env python3
"""
SELF-LEARNING AI SYSTEM FOR KRISHIMITRA
AI that learns and improves from farmer queries and feedback
"""

import json
import os
import logging
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from collections import defaultdict, Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import re

logger = logging.getLogger(__name__)

class SelfLearningAI:
    """Self-Learning AI that improves from farmer interactions"""
    
    def __init__(self, data_dir: str = "advisory/ml/learning_data"):
        self.data_dir = data_dir
        self.ensure_data_directory()
        
        # Learning components
        self.query_patterns = self._load_learning_data("query_patterns.json", {})
        self.response_effectiveness = self._load_learning_data("response_effectiveness.json", {})
        self.farmer_preferences = self._load_learning_data("farmer_preferences.json", {})
        self.knowledge_base = self._load_learning_data("knowledge_base.json", {})
        self.conversation_history = self._load_learning_data("conversation_history.json", [])
        
        # ML components for pattern recognition
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.query_clusters = self._load_learning_data("query_clusters.pkl", None)
        self.response_clusters = self._load_learning_data("response_clusters.pkl", None)
        
        # Learning statistics
        self.learning_stats = self._load_learning_data("learning_stats.json", {
            "total_queries": 0,
            "total_feedback": 0,
            "improvement_rate": 0.0,
            "last_learning": None,
            "patterns_learned": 0,
            "knowledge_entries": 0
        })
        
        # Initialize ML models if data exists
        if len(self.conversation_history) > 10:
            self._train_ml_models()
    
    def ensure_data_directory(self):
        """Ensure learning data directory exists"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)
    
    def _load_learning_data(self, filename: str, default_value: Any) -> Any:
        """Load learning data from file"""
        filepath = os.path.join(self.data_dir, filename)
        try:
            if os.path.exists(filepath):
                if filename.endswith('.pkl'):
                    with open(filepath, 'rb') as f:
                        return pickle.load(f)
                else:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load {filename}: {e}")
        return default_value
    
    def _save_learning_data(self, filename: str, data: Any):
        """Save learning data to file"""
        filepath = os.path.join(self.data_dir, filename)
        try:
            if filename.endswith('.pkl'):
                with open(filepath, 'wb') as f:
                    pickle.dump(data, f)
            else:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Could not save {filename}: {e}")
    
    def learn_from_query(self, query: str, response: str, user_feedback: str = None, 
                        location: str = None, language: str = 'en') -> Dict[str, Any]:
        """Learn from a farmer query and response"""
        
        # Extract learning insights
        insights = self._extract_query_insights(query, response, user_feedback, location, language)
        
        # Update learning data
        self._update_query_patterns(query, insights)
        self._update_response_effectiveness(response, user_feedback)
        self._update_farmer_preferences(location, language, insights)
        self._update_knowledge_base(query, response, insights)
        
        # Add to conversation history
        conversation_entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "response": response,
            "feedback": user_feedback,
            "location": location,
            "language": language,
            "insights": insights
        }
        self.conversation_history.append(conversation_entry)
        
        # Update learning statistics
        self.learning_stats["total_queries"] += 1
        if user_feedback:
            self.learning_stats["total_feedback"] += 1
        self.learning_stats["last_learning"] = datetime.now().isoformat()
        
        # Retrain ML models periodically
        if self.learning_stats["total_queries"] % 50 == 0:
            self._train_ml_models()
        
        # Save learning data
        self._save_all_learning_data()
        
        return {
            "learned": True,
            "insights": insights,
            "total_queries": self.learning_stats["total_queries"],
            "improvement_opportunities": self._identify_improvement_opportunities()
        }
    
    def _extract_query_insights(self, query: str, response: str, feedback: str, 
                               location: str, language: str) -> Dict[str, Any]:
        """Extract insights from query and response"""
        insights = {
            "query_type": self._classify_query_type(query),
            "complexity": self._assess_query_complexity(query),
            "response_quality": self._assess_response_quality(response),
            "feedback_sentiment": self._analyze_feedback_sentiment(feedback) if feedback else None,
            "location_specific": location is not None,
            "language_preference": language,
            "key_topics": self._extract_key_topics(query),
            "response_length": len(response),
            "query_length": len(query)
        }
        
        return insights
    
    def _classify_query_type(self, query: str) -> str:
        """Classify the type of query"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['price', 'cost', 'rate', 'market']):
            return "market_price"
        elif any(word in query_lower for word in ['weather', 'rain', 'temperature']):
            return "weather"
        elif any(word in query_lower for word in ['crop', 'plant', 'grow', 'recommend']):
            return "crop_recommendation"
        elif any(word in query_lower for word in ['pest', 'disease', 'problem']):
            return "pest_disease"
        elif any(word in query_lower for word in ['scheme', 'subsidy', 'government']):
            return "government_schemes"
        elif any(word in query_lower for word in ['fertilizer', 'soil', 'irrigation']):
            return "farming_practices"
        else:
            return "general"
    
    def _assess_query_complexity(self, query: str) -> str:
        """Assess query complexity"""
        query_length = len(query.split())
        
        if query_length <= 5:
            return "simple"
        elif query_length <= 15:
            return "medium"
        else:
            return "complex"
    
    def _assess_response_quality(self, response: str) -> Dict[str, Any]:
        """Assess response quality"""
        quality_metrics = {
            "length": len(response),
            "has_specifics": bool(re.search(r'\d+', response)),  # Contains numbers
            "has_emojis": bool(re.search(r'[🌾💰🌤️📊💡🏪]', response)),
            "has_recommendations": bool(re.search(r'(recommend|suggest|advice|should)', response.lower())),
            "has_sources": bool(re.search(r'(source|data|api|government)', response.lower())),
            "structured": len(response.split('\n')) > 3
        }
        
        # Calculate quality score
        quality_score = sum(quality_metrics.values()) / len(quality_metrics)
        
        return {
            "score": quality_score,
            "metrics": quality_metrics,
            "level": "high" if quality_score > 0.7 else "medium" if quality_score > 0.4 else "low"
        }
    
    def _analyze_feedback_sentiment(self, feedback: str) -> Dict[str, Any]:
        """Analyze feedback sentiment"""
        if not feedback:
            return None
        
        feedback_lower = feedback.lower()
        
        # Simple sentiment analysis
        positive_words = ['good', 'great', 'helpful', 'accurate', 'useful', 'thanks', 'perfect']
        negative_words = ['bad', 'wrong', 'useless', 'inaccurate', 'confused', 'not helpful']
        
        positive_count = sum(1 for word in positive_words if word in feedback_lower)
        negative_count = sum(1 for word in negative_words if word in feedback_lower)
        
        if positive_count > negative_count:
            sentiment = "positive"
        elif negative_count > positive_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        return {
            "sentiment": sentiment,
            "positive_score": positive_count,
            "negative_score": negative_count,
            "confidence": abs(positive_count - negative_count) / max(1, positive_count + negative_count)
        }
    
    def _extract_key_topics(self, query: str) -> List[str]:
        """Extract key topics from query"""
        # Simple topic extraction based on keywords
        topics = []
        query_lower = query.lower()
        
        topic_keywords = {
            'crops': ['wheat', 'rice', 'cotton', 'sugarcane', 'maize', 'potato'],
            'weather': ['rain', 'temperature', 'humidity', 'monsoon', 'drought'],
            'markets': ['price', 'mandi', 'market', 'cost', 'selling'],
            'farming': ['irrigation', 'fertilizer', 'soil', 'harvest', 'sowing'],
            'problems': ['pest', 'disease', 'problem', 'issue', 'help']
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    def _update_query_patterns(self, query: str, insights: Dict[str, Any]):
        """Update query patterns based on new query"""
        query_type = insights['query_type']
        
        if query_type not in self.query_patterns:
            self.query_patterns[query_type] = {
                "count": 0,
                "common_words": {},
                "complexity_distribution": {},
                "location_frequency": {},
                "language_frequency": {}
            }
        
        pattern_data = self.query_patterns[query_type]
        pattern_data["count"] += 1
        
        # Update word frequency
        words = query.lower().split()
        for word in words:
            # Clean the word (remove punctuation)
            clean_word = ''.join(c for c in word if c.isalnum())
            if len(clean_word) > 3:  # Only meaningful words
                if clean_word not in pattern_data["common_words"]:
                    pattern_data["common_words"][clean_word] = 0
                pattern_data["common_words"][clean_word] += 1
        
        # Update complexity distribution
        complexity = insights.get('complexity', 'simple')
        if complexity not in pattern_data["complexity_distribution"]:
            pattern_data["complexity_distribution"][complexity] = 0
        pattern_data["complexity_distribution"][complexity] += 1
        
        # Update location and language frequency
        if insights.get('location_specific', False):
            if "location_specific" not in pattern_data["location_frequency"]:
                pattern_data["location_frequency"]["location_specific"] = 0
            pattern_data["location_frequency"]["location_specific"] += 1
        
        language_pref = insights.get('language_preference', 'en')
        if language_pref not in pattern_data["language_frequency"]:
            pattern_data["language_frequency"][language_pref] = 0
        pattern_data["language_frequency"][language_pref] += 1
        
        self.learning_stats["patterns_learned"] += 1
    
    def _update_response_effectiveness(self, response: str, feedback: str):
        """Update response effectiveness based on feedback"""
        if not feedback:
            return
        
        response_hash = str(hash(response))[:10]
        
        if response_hash not in self.response_effectiveness:
            self.response_effectiveness[response_hash] = {
                "response": response,
                "total_feedback": 0,
                "positive_feedback": 0,
                "negative_feedback": 0,
                "effectiveness_score": 0.5
            }
        
        effectiveness_data = self.response_effectiveness[response_hash]
        effectiveness_data["total_feedback"] += 1
        
        # Analyze feedback sentiment
        feedback_analysis = self._analyze_feedback_sentiment(feedback)
        if feedback_analysis:
            if feedback_analysis['sentiment'] == 'positive':
                effectiveness_data["positive_feedback"] += 1
            elif feedback_analysis['sentiment'] == 'negative':
                effectiveness_data["negative_feedback"] += 1
            
            # Update effectiveness score
            total = effectiveness_data["positive_feedback"] + effectiveness_data["negative_feedback"]
            if total > 0:
                effectiveness_data["effectiveness_score"] = effectiveness_data["positive_feedback"] / total
    
    def _update_farmer_preferences(self, location: str, language: str, insights: Dict[str, Any]):
        """Update farmer preferences"""
        if location:
            if location not in self.farmer_preferences:
                self.farmer_preferences[location] = {
                    "query_types": {},
                    "languages": {},
                    "topics": {},
                    "complexity_preference": {}
                }
            
            location_prefs = self.farmer_preferences[location]
            
            # Update query types
            query_type = insights.get('query_type', 'general')
            if query_type not in location_prefs["query_types"]:
                location_prefs["query_types"][query_type] = 0
            location_prefs["query_types"][query_type] += 1
            
            # Update languages
            if language not in location_prefs["languages"]:
                location_prefs["languages"][language] = 0
            location_prefs["languages"][language] += 1
            
            # Update complexity preference
            complexity = insights.get('complexity', 'simple')
            if complexity not in location_prefs["complexity_preference"]:
                location_prefs["complexity_preference"][complexity] = 0
            location_prefs["complexity_preference"][complexity] += 1
            
            # Update topics
            for topic in insights.get('key_topics', []):
                if topic not in location_prefs["topics"]:
                    location_prefs["topics"][topic] = 0
                location_prefs["topics"][topic] += 1
    
    def _update_knowledge_base(self, query: str, response: str, insights: Dict[str, Any]):
        """Update knowledge base with new information"""
        query_type = insights['query_type']
        
        if query_type not in self.knowledge_base:
            self.knowledge_base[query_type] = {
                "queries": [],
                "responses": [],
                "patterns": [],
                "best_practices": []
            }
        
        knowledge_entry = {
            "query": query,
            "response": response,
            "quality_score": insights['response_quality']['score'],
            "topics": insights['key_topics'],
            "timestamp": datetime.now().isoformat()
        }
        
        self.knowledge_base[query_type]["queries"].append(knowledge_entry)
        
        # Keep only recent entries (last 1000 per type)
        if len(self.knowledge_base[query_type]["queries"]) > 1000:
            self.knowledge_base[query_type]["queries"] = self.knowledge_base[query_type]["queries"][-1000:]
        
        self.learning_stats["knowledge_entries"] += 1
    
    def _train_ml_models(self):
        """Train ML models for pattern recognition"""
        if len(self.conversation_history) < 10:
            return
        
        try:
            # Prepare data for training
            queries = [entry['query'] for entry in self.conversation_history[-1000:]]
            responses = [entry['response'] for entry in self.conversation_history[-1000:]]
            
            if len(queries) > 5:
                # Train query clustering
                query_vectors = self.vectorizer.fit_transform(queries)
                if query_vectors.shape[0] > 5:
                    self.query_clusters = KMeans(n_clusters=min(10, len(queries)//5), random_state=42)
                    self.query_clusters.fit(query_vectors)
                
                # Train response clustering
                response_vectors = self.vectorizer.fit_transform(responses)
                if response_vectors.shape[0] > 5:
                    self.response_clusters = KMeans(n_clusters=min(10, len(responses)//5), random_state=42)
                    self.response_clusters.fit(response_vectors)
                
                logger.info(f"Retrained ML models with {len(queries)} examples")
                
        except Exception as e:
            logger.warning(f"Could not train ML models: {e}")
    
    def _identify_improvement_opportunities(self) -> List[str]:
        """Identify areas for improvement"""
        opportunities = []
        
        # Check response effectiveness
        low_effectiveness = [
            response for response, data in self.response_effectiveness.items()
            if data["effectiveness_score"] < 0.3 and data["total_feedback"] > 2
        ]
        
        if low_effectiveness:
            opportunities.append(f"Improve responses with low effectiveness: {len(low_effectiveness)} responses")
        
        # Check query pattern gaps
        if len(self.query_patterns) < 6:  # We have 6 main query types
            opportunities.append("Expand coverage of different query types")
        
        # Check feedback ratio
        feedback_ratio = self.learning_stats["total_feedback"] / max(1, self.learning_stats["total_queries"])
        if feedback_ratio < 0.1:
            opportunities.append("Increase farmer feedback collection")
        
        return opportunities
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Get insights about the learning progress"""
        return {
            "total_queries": self.learning_stats["total_queries"],
            "total_feedback": self.learning_stats["total_feedback"],
            "feedback_rate": self.learning_stats["total_feedback"] / max(1, self.learning_stats["total_queries"]),
            "query_types_learned": len(self.query_patterns),
            "knowledge_entries": self.learning_stats["knowledge_entries"],
            "last_learning": self.learning_stats["last_learning"],
            "improvement_opportunities": self._identify_improvement_opportunities(),
            "top_query_types": self._get_top_query_types(),
            "location_preferences": self._get_location_preferences()
        }
    
    def _get_top_query_types(self) -> List[Dict[str, Any]]:
        """Get top query types by frequency"""
        query_type_counts = {qtype: data["count"] for qtype, data in self.query_patterns.items()}
        sorted_types = sorted(query_type_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [{"type": qtype, "count": count} for qtype, count in sorted_types[:5]]
    
    def _get_location_preferences(self) -> Dict[str, Any]:
        """Get location-based preferences"""
        return {
            location: {
                "total_queries": sum(data["query_types"].values()),
                "top_topics": [topic for topic, count in sorted(data["topics"].items(), key=lambda x: x[1], reverse=True)[:3]],
                "language_preference": sorted(data["languages"].items(), key=lambda x: x[1], reverse=True)[0][0] if data["languages"] else "en"
            }
            for location, data in self.farmer_preferences.items()
        }
    
    def suggest_improved_response(self, query: str, current_response: str) -> str:
        """Suggest an improved response based on learning"""
        query_type = self._classify_query_type(query)
        
        if query_type in self.knowledge_base:
            # Find similar successful responses
            similar_responses = self._find_similar_successful_responses(query_type, current_response)
            
            if similar_responses:
                # Combine best practices from similar responses
                improved_response = self._combine_best_practices(similar_responses)
                return improved_response
        
        return current_response
    
    def _find_similar_successful_responses(self, query_type: str, current_response: str) -> List[Dict[str, Any]]:
        """Find similar successful responses"""
        if query_type not in self.knowledge_base:
            return []
        
        responses = self.knowledge_base[query_type]["queries"]
        
        # Filter high-quality responses
        high_quality_responses = [
            resp for resp in responses 
            if resp["quality_score"] > 0.7
        ]
        
        # Sort by quality score
        return sorted(high_quality_responses, key=lambda x: x["quality_score"], reverse=True)[:3]
    
    def _combine_best_practices(self, successful_responses: List[Dict[str, Any]]) -> str:
        """Combine best practices from successful responses"""
        if not successful_responses:
            return ""
        
        # Use the highest quality response as base
        best_response = successful_responses[0]["response"]
        
        # Add elements from other high-quality responses if they improve the response
        for response_data in successful_responses[1:]:
            response = response_data["response"]
            
            # Add missing emojis if they're present in other responses
            if not re.search(r'[🌾💰🌤️📊💡🏪]', best_response) and re.search(r'[🌾💰🌤️📊💡🏪]', response):
                best_response = self._add_emojis_to_response(best_response)
            
            # Add missing recommendations if they're present in other responses
            if not re.search(r'(recommend|suggest|advice)', best_response.lower()) and re.search(r'(recommend|suggest|advice)', response.lower()):
                best_response = self._add_recommendations_to_response(best_response)
        
        return best_response
    
    def _add_emojis_to_response(self, response: str) -> str:
        """Add relevant emojis to response"""
        emoji_mapping = {
            'price': '💰',
            'market': '🏪',
            'crop': '🌾',
            'weather': '🌤️',
            'recommend': '💡',
            'data': '📊'
        }
        
        for keyword, emoji in emoji_mapping.items():
            if keyword in response.lower() and emoji not in response:
                response = response.replace(keyword.title(), f"{emoji} {keyword.title()}")
        
        return response
    
    def _add_recommendations_to_response(self, response: str) -> str:
        """Add recommendations section to response"""
        if "💡 Recommendations:" not in response:
            recommendations = "\n\n💡 Recommendations:\n• Monitor market trends regularly\n• Consider seasonal variations\n• Check multiple sources for accuracy"
            response += recommendations
        
        return response
    
    def _save_all_learning_data(self):
        """Save all learning data"""
        self._save_learning_data("query_patterns.json", self.query_patterns)
        self._save_learning_data("response_effectiveness.json", self.response_effectiveness)
        self._save_learning_data("farmer_preferences.json", self.farmer_preferences)
        self._save_learning_data("knowledge_base.json", self.knowledge_base)
        self._save_learning_data("conversation_history.json", self.conversation_history)
        self._save_learning_data("learning_stats.json", self.learning_stats)
        
        if self.query_clusters:
            self._save_learning_data("query_clusters.pkl", self.query_clusters)
        if self.response_clusters:
            self._save_learning_data("response_clusters.pkl", self.response_clusters)

# Global instance
self_learning_ai = SelfLearningAI()
