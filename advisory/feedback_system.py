"""
User Feedback Collection and Analysis System
Collects, stores, and analyzes user feedback for continuous ML model improvement
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from django.db import models
from advisory.models import User, UserFeedback
import logging

logger = logging.getLogger(__name__)


class FeedbackAnalytics:
    """Analytics system for user feedback"""
    
    def __init__(self):
        self.feedback_data = []
    
    def collect_feedback(self, user_id: str, session_id: str, prediction_type: str,
                        input_data: Dict, system_prediction: Dict, actual_result: Dict,
                        feedback_rating: int, feedback_text: str = "", 
                        latitude: float = None, longitude: float = None) -> bool:
        """Collect and store user feedback"""
        try:
            # Create feedback entry
            feedback = UserFeedback.objects.create(
                user_id=user_id,
                session_id=session_id,
                prediction_type=prediction_type,
                input_data=input_data,
                system_prediction=system_prediction,
                actual_result=actual_result,
                feedback_rating=feedback_rating,
                feedback_text=feedback_text,
                latitude=latitude,
                longitude=longitude
            )
            
            # Store in memory for quick access
            self.feedback_data.append({
                'id': feedback.id,
                'user_id': user_id,
                'prediction_type': prediction_type,
                'feedback_rating': feedback_rating,
                'timestamp': feedback.created_at.isoformat(),
                'input_data': input_data,
                'system_prediction': system_prediction,
                'actual_result': actual_result
            })
            
            logger.info(f"Feedback collected from user {user_id} for {prediction_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error collecting feedback: {e}")
            return False
    
    def get_feedback_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get analytics on user feedback"""
        try:
            # Get feedback from last N days
            start_date = datetime.now() - timedelta(days=days)
            recent_feedback = UserFeedback.objects.filter(created_at__gte=start_date)
            
            # Calculate metrics
            total_feedback = recent_feedback.count()
            if total_feedback == 0:
                return {'message': 'No feedback data available'}
            
            # Average rating
            avg_rating = recent_feedback.aggregate(
                avg_rating=models.Avg('feedback_rating')
            )['avg_rating']
            
            # Rating distribution
            rating_distribution = {}
            for rating in range(1, 6):
                count = recent_feedback.filter(feedback_rating=rating).count()
                rating_distribution[rating] = count
            
            # Prediction type distribution
            prediction_types = {}
            for feedback in recent_feedback.values('prediction_type').distinct():
                pred_type = feedback['prediction_type']
                count = recent_feedback.filter(prediction_type=pred_type).count()
                prediction_types[pred_type] = count
            
            # User engagement
            unique_users = recent_feedback.values('user_id').distinct().count()
            avg_feedback_per_user = total_feedback / unique_users if unique_users > 0 else 0
            
            # Geographic distribution
            geo_feedback = recent_feedback.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
            geo_count = geo_feedback.count()
            
            # Recent trends (last 7 days)
            week_ago = datetime.now() - timedelta(days=7)
            recent_trend = recent_feedback.filter(created_at__gte=week_ago).count()
            
            return {
                'period_days': days,
                'total_feedback': total_feedback,
                'average_rating': round(avg_rating, 2),
                'rating_distribution': rating_distribution,
                'prediction_types': prediction_types,
                'unique_users': unique_users,
                'avg_feedback_per_user': round(avg_feedback_per_user, 2),
                'geographic_coverage': geo_count,
                'recent_trend_7_days': recent_trend,
                'feedback_quality': self._assess_feedback_quality(recent_feedback),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting feedback analytics: {e}")
            return {'error': str(e)}
    
    def _assess_feedback_quality(self, feedback_queryset) -> Dict[str, Any]:
        """Assess the quality of feedback data"""
        try:
            total = feedback_queryset.count()
            if total == 0:
                return {'quality_score': 0, 'issues': []}
            
            issues = []
            quality_score = 100
            
            # Check for low ratings
            low_ratings = feedback_queryset.filter(feedback_rating__lte=2).count()
            if low_ratings / total > 0.3:  # More than 30% low ratings
                issues.append('High percentage of low ratings')
                quality_score -= 20
            
            # Check for missing feedback text
            missing_text = feedback_queryset.filter(feedback_text__isnull=True).count()
            if missing_text / total > 0.8:  # More than 80% missing text
                issues.append('Most feedback lacks detailed comments')
                quality_score -= 10
            
            # Check for geographic diversity
            geo_feedback = feedback_queryset.exclude(latitude__isnull=True)
            if geo_feedback.count() / total < 0.5:  # Less than 50% have location
                issues.append('Limited geographic data')
                quality_score -= 15
            
            # Check for prediction type diversity
            pred_types = feedback_queryset.values('prediction_type').distinct().count()
            if pred_types < 2:
                issues.append('Limited prediction type diversity')
                quality_score -= 10
            
            return {
                'quality_score': max(0, quality_score),
                'issues': issues,
                'total_feedback_analyzed': total
            }
            
        except Exception as e:
            logger.error(f"Error assessing feedback quality: {e}")
            return {'quality_score': 0, 'issues': ['Error in quality assessment']}
    
    def get_user_feedback_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get feedback history for a specific user"""
        try:
            feedback_history = UserFeedback.objects.filter(
                user_id=user_id
            ).order_by('-created_at')[:limit]
            
            history = []
            for feedback in feedback_history:
                history.append({
                    'id': feedback.id,
                    'prediction_type': feedback.prediction_type,
                    'feedback_rating': feedback.feedback_rating,
                    'feedback_text': feedback.feedback_text,
                    'created_at': feedback.created_at.isoformat(),
                    'input_data': feedback.input_data,
                    'system_prediction': feedback.system_prediction,
                    'actual_result': feedback.actual_result
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting user feedback history: {e}")
            return []
    
    def get_prediction_accuracy(self, prediction_type: str, days: int = 30) -> Dict[str, Any]:
        """Get accuracy metrics for a specific prediction type"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            feedback = UserFeedback.objects.filter(
                prediction_type=prediction_type,
                created_at__gte=start_date
            )
            
            total = feedback.count()
            if total == 0:
                return {'message': f'No feedback data for {prediction_type}'}
            
            # Calculate accuracy based on ratings
            high_ratings = feedback.filter(feedback_rating__gte=4).count()
            medium_ratings = feedback.filter(feedback_rating=3).count()
            low_ratings = feedback.filter(feedback_rating__lte=2).count()
            
            accuracy = (high_ratings + medium_ratings * 0.5) / total
            
            # Get common issues from low ratings
            low_rating_feedback = feedback.filter(feedback_rating__lte=2)
            common_issues = self._analyze_common_issues(low_rating_feedback)
            
            return {
                'prediction_type': prediction_type,
                'total_predictions': total,
                'accuracy_score': round(accuracy, 3),
                'high_ratings': high_ratings,
                'medium_ratings': medium_ratings,
                'low_ratings': low_ratings,
                'common_issues': common_issues,
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Error getting prediction accuracy: {e}")
            return {'error': str(e)}
    
    def _analyze_common_issues(self, low_rating_feedback) -> List[str]:
        """Analyze common issues from low-rated feedback"""
        issues = []
        
        # Analyze feedback text for common issues
        feedback_texts = low_rating_feedback.exclude(feedback_text__isnull=True).values_list('feedback_text', flat=True)
        
        # Simple keyword analysis (in a real system, you'd use NLP)
        issue_keywords = {
            'inaccurate': ['wrong', 'incorrect', 'inaccurate', 'not right'],
            'irrelevant': ['irrelevant', 'not useful', 'doesn\'t help'],
            'incomplete': ['incomplete', 'missing', 'not enough'],
            'outdated': ['outdated', 'old', 'not current'],
            'confusing': ['confusing', 'unclear', 'hard to understand']
        }
        
        for category, keywords in issue_keywords.items():
            count = 0
            for text in feedback_texts:
                if any(keyword in text.lower() for keyword in keywords):
                    count += 1
            
            if count > len(feedback_texts) * 0.2:  # More than 20% mention this issue
                issues.append(category)
        
        return issues
    
    def export_feedback_data(self, format: str = 'json', days: int = 30) -> str:
        """Export feedback data for analysis"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            feedback = UserFeedback.objects.filter(created_at__gte=start_date)
            
            data = []
            for f in feedback:
                data.append({
                    'user_id': f.user_id,
                    'prediction_type': f.prediction_type,
                    'input_data': f.input_data,
                    'system_prediction': f.system_prediction,
                    'actual_result': f.actual_result,
                    'feedback_rating': f.feedback_rating,
                    'feedback_text': f.feedback_text,
                    'latitude': f.latitude,
                    'longitude': f.longitude,
                    'created_at': f.created_at.isoformat()
                })
            
            if format == 'json':
                filename = f'feedback_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                filepath = os.path.join('exports', filename)
                os.makedirs('exports', exist_ok=True)
                
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2)
                
                return filepath
            
            return str(data)
            
        except Exception as e:
            logger.error(f"Error exporting feedback data: {e}")
            return ""
    
    def cleanup_old_feedback(self, days: int = 365) -> int:
        """Clean up old feedback data to manage storage"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            old_feedback = UserFeedback.objects.filter(created_at__lt=cutoff_date)
            count = old_feedback.count()
            old_feedback.delete()
            
            logger.info(f"Cleaned up {count} old feedback entries")
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up old feedback: {e}")
            return 0
