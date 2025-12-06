from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

# Create your models here.

class User(AbstractUser):
    ROLES = (
        ('farmer', 'Farmer'),
        ('admin', 'Admin'),
        ('officer', 'Officer'),
    )
    role = models.CharField(max_length=10, choices=ROLES, default='farmer')

class Crop(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    ideal_soil_type = models.CharField(max_length=100)
    min_temperature_c = models.FloatField()
    max_temperature_c = models.FloatField()
    min_rainfall_mm_per_month = models.FloatField()
    max_rainfall_mm_per_month = models.FloatField()
    duration_days = models.IntegerField(help_text="Approximate duration of crop cycle in days")
    # Add more fields as needed, e.g., water requirements, sunlight, etc.

    def __str__(self):
        return self.name

class CropAdvisory(models.Model):
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='advisories')
    soil_type = models.CharField(max_length=100)
    weather_condition = models.CharField(max_length=100)
    recommendation = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.crop.name} - {self.soil_type}"

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

class ChatHistory(models.Model):
    """Model to persist chat conversation history"""
    
    user_id = models.CharField(max_length=100, help_text="Unique user identifier")
    session_id = models.CharField(max_length=100, help_text="Session identifier")
    
    # Message details
    message_type = models.CharField(
        max_length=20, 
        choices=[
            ('user', 'User Message'),
            ('assistant', 'Assistant Response'),
            ('system', 'System Message')
        ],
        help_text="Type of message"
    )
    message_content = models.TextField(help_text="The actual message content")
    
    # Language and processing info
    detected_language = models.CharField(max_length=10, help_text="Detected language")
    response_language = models.CharField(max_length=10, help_text="Response language")
    
    # Response metadata
    confidence_score = models.FloatField(null=True, blank=True, help_text="Confidence score of response")
    response_source = models.CharField(max_length=50, help_text="Source of response (advanced_chatbot, fallback, etc.)")
    response_type = models.CharField(max_length=50, help_text="Type of response (greeting, agricultural, etc.)")
    
    # Context information
    has_location = models.BooleanField(default=False, help_text="Whether location was detected")
    has_product = models.BooleanField(default=False, help_text="Whether product was mentioned")
    latitude = models.FloatField(null=True, blank=True, help_text="User's latitude")
    longitude = models.FloatField(null=True, blank=True, help_text="User's longitude")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'chat_history'
        ordering = ['session_id', 'created_at']
        indexes = [
            models.Index(fields=['user_id', 'session_id']),
            models.Index(fields=['session_id', 'created_at']),
            models.Index(fields=['user_id', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.message_type} from {self.user_id} in session {self.session_id}"

class ChatSession(models.Model):
    """Model to track chat sessions with enhanced metadata"""
    
    user_id = models.CharField(max_length=100, help_text="Unique user identifier")
    session_id = models.CharField(max_length=100, unique=True, help_text="Unique session identifier")
    
    # Session metadata
    start_time = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Conversation context
    conversation_context = models.JSONField(
        default=dict,
        help_text="Persistent conversation context including location, preferences, etc."
    )
    
    # Session preferences
    preferred_language = models.CharField(max_length=10, default='auto')
    location_name = models.CharField(max_length=200, blank=True, null=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    # Session statistics
    total_messages = models.IntegerField(default=0)
    user_messages = models.IntegerField(default=0)
    assistant_messages = models.IntegerField(default=0)
    
    # Device and browser info
    device_type = models.CharField(max_length=50, blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        db_table = 'chat_sessions'
        indexes = [
            models.Index(fields=['user_id', 'start_time']),
            models.Index(fields=['session_id']),
            models.Index(fields=['is_active', 'last_activity']),
        ]
    
    def __str__(self):
        return f"Chat session {self.session_id} for user {self.user_id}"

class ForumPost(models.Model):
    """
    Model for community forum posts.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_posts')
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} by {self.user.username}"

class DiagnosticSession(models.Model):
    """
    Tracks a user's multi-step diagnostic session (KrishiRaksha 2.0).
    """
    user_id = models.CharField(max_length=100, help_text="User ID")
    session_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    crop_detected = models.CharField(max_length=100, blank=True, null=True)
    images_json = models.JSONField(default=dict, help_text="{'whole': '/path/to/img1', 'close_up': '/path/to/img2'}")
    
    # Analysis results
    final_diagnosis = models.CharField(max_length=200, blank=True, null=True)
    confidence_score = models.FloatField(default=0.0)
    severity_level = models.CharField(max_length=50, blank=True, null=True) # Low, Medium, High
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Diagnostic {self.session_id} - {self.crop_detected}"

class ExpertVerification(models.Model):
    """
    For 'Active Learning': difficult cases sent to experts.
    """
    diagnostic_session = models.ForeignKey(DiagnosticSession, on_delete=models.CASCADE)
    is_verified = models.BooleanField(default=False)
    expert_diagnosis = models.CharField(max_length=200, blank=True, null=True)
    expert_notes = models.TextField(blank=True, null=True)
    verified_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Verification for {self.diagnostic_session.session_id}"