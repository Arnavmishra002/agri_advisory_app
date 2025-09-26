from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class CropAdvisory(models.Model):
    crop_type = models.CharField(max_length=100)
    soil_type = models.CharField(max_length=100)
    weather_condition = models.CharField(max_length=100)
    recommendation = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.crop_type} - {self.soil_type}"

class UserFeedback(models.Model):
    """Model to store user feedback for ML model improvement"""
    
    user_id = models.CharField(max_length=100, help_text="Unique user identifier")
    session_id = models.CharField(max_length=100, help_text="Session identifier")
    prediction_type = models.CharField(max_length=50, help_text="Type of prediction (crop_recommendation, yield_prediction, etc.)")
    
    # Input data that was used for prediction
    input_data = models.JSONField(help_text="Input parameters used for prediction")
    
    # Prediction made by the system
    system_prediction = models.JSONField(help_text="System's prediction")
    
    # User's actual results/feedback
    actual_result = models.JSONField(help_text="Actual result or user's feedback")
    
    # Feedback rating (1-5 scale)
    feedback_rating = models.IntegerField(help_text="User rating from 1-5")
    
    # Additional feedback text
    feedback_text = models.TextField(blank=True, null=True, help_text="Additional user comments")
    
    # Location data
    latitude = models.FloatField(null=True, blank=True, help_text="User's latitude")
    longitude = models.FloatField(null=True, blank=True, help_text="User's longitude")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_feedback'
        indexes = [
            models.Index(fields=['user_id', 'created_at']),
            models.Index(fields=['prediction_type', 'created_at']),
            models.Index(fields=['feedback_rating', 'created_at']),
        ]
    
    def __str__(self):
        return f"Feedback from {self.user_id} for {self.prediction_type} - Rating: {self.feedback_rating}"

class MLModelPerformance(models.Model):
    """Model to track ML model performance metrics"""
    
    model_name = models.CharField(max_length=100, help_text="Name of the ML model")
    model_version = models.CharField(max_length=50, help_text="Model version")
    
    # Performance metrics
    accuracy = models.FloatField(null=True, blank=True, help_text="Model accuracy")
    precision = models.FloatField(null=True, blank=True, help_text="Model precision")
    recall = models.FloatField(null=True, blank=True, help_text="Model recall")
    f1_score = models.FloatField(null=True, blank=True, help_text="Model F1 score")
    r2_score = models.FloatField(null=True, blank=True, help_text="Model R2 score")
    rmse = models.FloatField(null=True, blank=True, help_text="Root Mean Square Error")
    
    # Training information
    training_samples = models.IntegerField(help_text="Number of training samples")
    validation_samples = models.IntegerField(help_text="Number of validation samples")
    training_date = models.DateTimeField(help_text="Date when model was trained")
    
    # Model metadata
    model_parameters = models.JSONField(help_text="Model hyperparameters")
    feature_importance = models.JSONField(null=True, blank=True, help_text="Feature importance scores")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ml_model_performance'
        ordering = ['-training_date']
    
    def __str__(self):
        return f"{self.model_name} v{self.model_version} - Accuracy: {self.accuracy}"

class UserSession(models.Model):
    """Model to track user sessions and interactions"""
    
    user_id = models.CharField(max_length=100, help_text="Unique user identifier")
    session_id = models.CharField(max_length=100, unique=True, help_text="Unique session identifier")
    
    # Session metadata
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    total_interactions = models.IntegerField(default=0)
    
    # Location data
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    location_name = models.CharField(max_length=200, blank=True, null=True)
    
    # Session preferences
    preferred_language = models.CharField(max_length=10, default='en')
    device_type = models.CharField(max_length=50, blank=True, null=True)
    
    # Session summary
    session_summary = models.JSONField(null=True, blank=True, help_text="Summary of session interactions")
    
    class Meta:
        db_table = 'user_sessions'
        indexes = [
            models.Index(fields=['user_id', 'start_time']),
            models.Index(fields=['session_id']),
        ]
    
    def __str__(self):
        return f"Session {self.session_id} for user {self.user_id}"