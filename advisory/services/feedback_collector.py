#!/usr/bin/env python3
"""
Farmer Feedback Collection and Historical Performance Tracking
Enables continuous learning from actual crop outcomes
"""

import logging
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class FeedbackCollector:
    """Collect and store farmer feedback for ML training"""
    
    def __init__(self):
        self.feedback_dir = os.path.join(
            os.path.dirname(__file__), 
            'feedback_data'
        )
        os.makedirs(self.feedback_dir, exist_ok=True)
        
        self.recommendations_file = os.path.join(self.feedback_dir, 'recommendations.json')
        self.feedback_file = os.path.join(self.feedback_dir, 'feedback.json')
        self.performance_file = os.path.join(self.feedback_dir, 'performance.json')
        
        # Initialize files if they don't exist
        for file_path in [self.recommendations_file, self.feedback_file, self.performance_file]:
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    json.dump([], f)
    
    def track_recommendation(self, recommendation_data: Dict) -> str:
        """
        Track a recommendation made to a farmer
        
        Args:
            recommendation_data: {
                'location': str,
                'latitude': float,
                'longitude': float,
                'season': str,
                'soil_type': str,
                'weather_data': dict,
                'recommendations': list,
                'timestamp': str
            }
        
        Returns:
            recommendation_id: Unique ID for this recommendation
        """
        try:
            # Generate unique ID
            recommendation_id = f"REC_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(str(recommendation_data)) % 10000}"
            
            # Add ID and metadata
            recommendation_data['recommendation_id'] = recommendation_id
            recommendation_data['tracked_at'] = datetime.now().isoformat()
            
            # Load existing recommendations
            with open(self.recommendations_file, 'r') as f:
                recommendations = json.load(f)
            
            # Append new recommendation
            recommendations.append(recommendation_data)
            
            # Save
            with open(self.recommendations_file, 'w') as f:
                json.dump(recommendations, f, indent=2)
            
            logger.info(f"✅ Tracked recommendation: {recommendation_id}")
            return recommendation_id
            
        except Exception as e:
            logger.error(f"Error tracking recommendation: {e}")
            return ""
    
    def collect_feedback(self, feedback_data: Dict) -> bool:
        """
        Collect farmer feedback on crop performance
        
        Args:
            feedback_data: {
                'recommendation_id': str,
                'farmer_id': str (optional),
                'crop_chosen': str,
                'yield_achieved': float,  # quintals/hectare
                'profit_realized': float,  # ₹/hectare
                'satisfaction_rating': int,  # 1-5
                'challenges_faced': list,
                'comments': str,
                'success': bool,  # Overall success indicator
                'timestamp': str
            }
        
        Returns:
            success: bool
        """
        try:
            # Add metadata
            feedback_data['feedback_id'] = f"FB_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            feedback_data['collected_at'] = datetime.now().isoformat()
            
            # Load existing feedback
            with open(self.feedback_file, 'r') as f:
                feedbacks = json.load(f)
            
            # Append new feedback
            feedbacks.append(feedback_data)
            
            # Save
            with open(self.feedback_file, 'w') as f:
                json.dump(feedbacks, f, indent=2)
            
            # Update performance metrics
            self._update_performance_metrics(feedback_data)
            
            logger.info(f"✅ Collected feedback: {feedback_data['feedback_id']}")
            return True
            
        except Exception as e:
            logger.error(f"Error collecting feedback: {e}")
            return False
    
    def _update_performance_metrics(self, feedback_data: Dict):
        """Update aggregated performance metrics"""
        try:
            # Load existing performance data
            with open(self.performance_file, 'r') as f:
                performance = json.load(f)
            
            # Extract key data
            crop = feedback_data.get('crop_chosen', 'unknown')
            location = feedback_data.get('location', 'unknown')
            season = feedback_data.get('season', 'unknown')
            success = feedback_data.get('success', False)
            yield_achieved = feedback_data.get('yield_achieved', 0)
            profit = feedback_data.get('profit_realized', 0)
            
            # Create key for aggregation
            key = f"{location}_{crop}_{season}"
            
            # Find or create entry
            entry = None
            for perf in performance:
                if perf.get('key') == key:
                    entry = perf
                    break
            
            if entry is None:
                entry = {
                    'key': key,
                    'location': location,
                    'crop': crop,
                    'season': season,
                    'total_attempts': 0,
                    'successful_attempts': 0,
                    'total_yield': 0,
                    'total_profit': 0,
                    'avg_yield': 0,
                    'avg_profit': 0,
                    'success_rate': 0,
                    'last_updated': datetime.now().isoformat()
                }
                performance.append(entry)
            
            # Update metrics
            entry['total_attempts'] += 1
            if success:
                entry['successful_attempts'] += 1
            entry['total_yield'] += yield_achieved
            entry['total_profit'] += profit
            entry['avg_yield'] = entry['total_yield'] / entry['total_attempts']
            entry['avg_profit'] = entry['total_profit'] / entry['total_attempts']
            entry['success_rate'] = entry['successful_attempts'] / entry['total_attempts']
            entry['last_updated'] = datetime.now().isoformat()
            
            # Save updated performance
            with open(self.performance_file, 'w') as f:
                json.dump(performance, f, indent=2)
            
            logger.info(f"✅ Updated performance metrics for {key}")
            
        except Exception as e:
            logger.error(f"Error updating performance metrics: {e}")
    
    def get_crop_performance(self, location: str, crop: str, season: str) -> Optional[Dict]:
        """Get historical performance for a specific crop"""
        try:
            with open(self.performance_file, 'r') as f:
                performance = json.load(f)
            
            key = f"{location}_{crop}_{season}"
            
            for entry in performance:
                if entry.get('key') == key:
                    return entry
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting crop performance: {e}")
            return None
    
    def get_training_data(self, min_samples: int = 10) -> List[Dict]:
        """
        Get training data for ML models
        
        Returns list of samples with features and outcomes
        """
        try:
            # Load recommendations and feedback
            with open(self.recommendations_file, 'r') as f:
                recommendations = json.load(f)
            
            with open(self.feedback_file, 'r') as f:
                feedbacks = json.load(f)
            
            # Create feedback lookup
            feedback_lookup = {}
            for fb in feedbacks:
                rec_id = fb.get('recommendation_id')
                if rec_id:
                    feedback_lookup[rec_id] = fb
            
            # Combine recommendations with feedback
            training_data = []
            
            for rec in recommendations:
                rec_id = rec.get('recommendation_id')
                if rec_id in feedback_lookup:
                    fb = feedback_lookup[rec_id]
                    
                    # Create training sample
                    sample = {
                        'crop_data': {
                            'name': fb.get('crop_chosen'),
                            'season': rec.get('season'),
                            'duration_days': 120,  # Default
                            'water_requirement_encoded': 2,
                            'profit_per_hectare': fb.get('profit_realized', 50000)
                        },
                        'weather_data': rec.get('weather_data', {}),
                        'location_data': {
                            'latitude': rec.get('latitude', 28.0),
                            'longitude': rec.get('longitude', 77.0),
                            'name': rec.get('location')
                        },
                        'soil_data': {
                            'type': rec.get('soil_type', 'loamy')
                        },
                        'success': fb.get('success', False),
                        'yield': fb.get('yield_achieved', 0),
                        'profit': fb.get('profit_realized', 0)
                    }
                    
                    training_data.append(sample)
            
            logger.info(f"✅ Retrieved {len(training_data)} training samples")
            return training_data
            
        except Exception as e:
            logger.error(f"Error getting training data: {e}")
            return []
    
    def get_success_rate_by_location(self, location: str) -> Dict[str, float]:
        """Get success rates for all crops in a location"""
        try:
            with open(self.performance_file, 'r') as f:
                performance = json.load(f)
            
            success_rates = {}
            
            for entry in performance:
                if entry.get('location') == location:
                    crop = entry.get('crop')
                    success_rate = entry.get('success_rate', 0)
                    success_rates[crop] = success_rate
            
            return success_rates
            
        except Exception as e:
            logger.error(f"Error getting success rates: {e}")
            return {}
