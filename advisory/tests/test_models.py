#!/usr/bin/env python3
"""
Comprehensive Unit Tests for Models
Tests all model functionality, validation, and relationships
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
import json

from ..models import (
    User, Crop, CropAdvisory, UserFeedback, MLModelPerformance,
    UserSession, ChatHistory, ChatSession, ForumPost
)

User = get_user_model()


class UserModelTests(TestCase):
    """Test cases for User model"""
    
    def setUp(self):
        """Set up test data"""
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'role': 'farmer'
        }
    
    def test_user_creation(self):
        """Test user creation with valid data"""
        user = User.objects.create_user(**self.user_data)
        
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.role, 'farmer')
        self.assertTrue(user.check_password('testpass123'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
    
    def test_user_creation_with_default_role(self):
        """Test user creation with default role"""
        user_data = self.user_data.copy()
        del user_data['role']
        
        user = User.objects.create_user(**user_data)
        self.assertEqual(user.role, 'farmer')  # Default role
    
    def test_user_role_choices(self):
        """Test user role choices validation"""
        valid_roles = ['farmer', 'admin', 'officer']
        
        for role in valid_roles:
            user_data = self.user_data.copy()
            user_data['username'] = f'test_{role}'
            user_data['role'] = role
            
            user = User.objects.create_user(**user_data)
            self.assertEqual(user.role, role)
    
    def test_user_str_representation(self):
        """Test user string representation"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(str(user), 'testuser')
    
    def test_superuser_creation(self):
        """Test superuser creation"""
        superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
        self.assertEqual(superuser.role, 'farmer')  # Default role even for superuser


class CropModelTests(TestCase):
    """Test cases for Crop model"""
    
    def setUp(self):
        """Set up test data"""
        self.crop_data = {
            'name': 'Wheat',
            'description': 'Winter cereal crop',
            'ideal_soil_type': 'Loamy',
            'min_temperature_c': 10.0,
            'max_temperature_c': 25.0,
            'min_rainfall_mm_per_month': 50.0,
            'max_rainfall_mm_per_month': 100.0,
            'duration_days': 150
        }
    
    def test_crop_creation(self):
        """Test crop creation with valid data"""
        crop = Crop.objects.create(**self.crop_data)
        
        self.assertEqual(crop.name, 'Wheat')
        self.assertEqual(crop.description, 'Winter cereal crop')
        self.assertEqual(crop.ideal_soil_type, 'Loamy')
        self.assertEqual(crop.min_temperature_c, 10.0)
        self.assertEqual(crop.max_temperature_c, 25.0)
        self.assertEqual(crop.min_rainfall_mm_per_month, 50.0)
        self.assertEqual(crop.max_rainfall_mm_per_month, 100.0)
        self.assertEqual(crop.duration_days, 150)
    
    def test_crop_str_representation(self):
        """Test crop string representation"""
        crop = Crop.objects.create(**self.crop_data)
        self.assertEqual(str(crop), 'Wheat')
    
    def test_crop_unique_name(self):
        """Test crop name uniqueness"""
        Crop.objects.create(**self.crop_data)
        
        # Try to create another crop with same name
        duplicate_crop_data = self.crop_data.copy()
        duplicate_crop_data['description'] = 'Different description'
        
        with self.assertRaises(Exception):  # Should raise IntegrityError
            Crop.objects.create(**duplicate_crop_data)
    
    def test_crop_optional_fields(self):
        """Test crop creation with optional fields"""
        crop_data = self.crop_data.copy()
        crop_data['description'] = None
        
        crop = Crop.objects.create(**crop_data)
        self.assertIsNone(crop.description)


class CropAdvisoryModelTests(TestCase):
    """Test cases for CropAdvisory model"""
    
    def setUp(self):
        """Set up test data"""
        self.crop = Crop.objects.create(
            name='Wheat',
            description='Winter cereal crop',
            ideal_soil_type='Loamy',
            min_temperature_c=10.0,
            max_temperature_c=25.0,
            min_rainfall_mm_per_month=50.0,
            max_rainfall_mm_per_month=100.0,
            duration_days=150
        )
        
        self.advisory_data = {
            'crop': self.crop,
            'soil_type': 'Loamy',
            'weather_condition': 'Normal',
            'recommendation': 'Plant wheat in October for best yield'
        }
    
    def test_crop_advisory_creation(self):
        """Test crop advisory creation"""
        advisory = CropAdvisory.objects.create(**self.advisory_data)
        
        self.assertEqual(advisory.crop, self.crop)
        self.assertEqual(advisory.soil_type, 'Loamy')
        self.assertEqual(advisory.weather_condition, 'Normal')
        self.assertEqual(advisory.recommendation, 'Plant wheat in October for best yield')
        self.assertIsNotNone(advisory.created_at)
    
    def test_crop_advisory_str_representation(self):
        """Test crop advisory string representation"""
        advisory = CropAdvisory.objects.create(**self.advisory_data)
        expected_str = f"{self.crop.name} - {advisory.soil_type}"
        self.assertEqual(str(advisory), expected_str)
    
    def test_crop_advisory_cascade_delete(self):
        """Test that advisory is deleted when crop is deleted"""
        advisory = CropAdvisory.objects.create(**self.advisory_data)
        advisory_id = advisory.id
        
        self.crop.delete()
        
        with self.assertRaises(CropAdvisory.DoesNotExist):
            CropAdvisory.objects.get(id=advisory_id)


class UserFeedbackModelTests(TestCase):
    """Test cases for UserFeedback model"""
    
    def setUp(self):
        """Set up test data"""
        self.feedback_data = {
            'user_id': 'user123',
            'session_id': 'session456',
            'prediction_type': 'crop_recommendation',
            'input_data': {'location': 'Delhi', 'soil_type': 'Loamy'},
            'system_prediction': {'crop': 'Wheat', 'confidence': 0.8},
            'actual_result': {'crop': 'Rice', 'yield': 'Good'},
            'feedback_rating': 4,
            'feedback_text': 'Good recommendation',
            'latitude': 28.7041,
            'longitude': 77.1025
        }
    
    def test_user_feedback_creation(self):
        """Test user feedback creation"""
        feedback = UserFeedback.objects.create(**self.feedback_data)
        
        self.assertEqual(feedback.user_id, 'user123')
        self.assertEqual(feedback.session_id, 'session456')
        self.assertEqual(feedback.prediction_type, 'crop_recommendation')
        self.assertEqual(feedback.input_data, {'location': 'Delhi', 'soil_type': 'Loamy'})
        self.assertEqual(feedback.system_prediction, {'crop': 'Wheat', 'confidence': 0.8})
        self.assertEqual(feedback.actual_result, {'crop': 'Rice', 'yield': 'Good'})
        self.assertEqual(feedback.feedback_rating, 4)
        self.assertEqual(feedback.feedback_text, 'Good recommendation')
        self.assertEqual(feedback.latitude, 28.7041)
        self.assertEqual(feedback.longitude, 77.1025)
        self.assertIsNotNone(feedback.created_at)
        self.assertIsNotNone(feedback.updated_at)
    
    def test_user_feedback_str_representation(self):
        """Test user feedback string representation"""
        feedback = UserFeedback.objects.create(**self.feedback_data)
        expected_str = f"Feedback from {feedback.user_id} for {feedback.prediction_type} - Rating: {feedback.feedback_rating}"
        self.assertEqual(str(feedback), expected_str)
    
    def test_user_feedback_optional_fields(self):
        """Test user feedback with optional fields"""
        feedback_data = self.feedback_data.copy()
        feedback_data['feedback_text'] = None
        feedback_data['latitude'] = None
        feedback_data['longitude'] = None
        
        feedback = UserFeedback.objects.create(**feedback_data)
        self.assertIsNone(feedback.feedback_text)
        self.assertIsNone(feedback.latitude)
        self.assertIsNone(feedback.longitude)
    
    def test_user_feedback_rating_validation(self):
        """Test feedback rating validation"""
        feedback_data = self.feedback_data.copy()
        
        # Test valid ratings
        for rating in [1, 2, 3, 4, 5]:
            feedback_data['feedback_rating'] = rating
            feedback = UserFeedback.objects.create(**feedback_data)
            self.assertEqual(feedback.feedback_rating, rating)
            feedback.delete()


class MLModelPerformanceModelTests(TestCase):
    """Test cases for MLModelPerformance model"""
    
    def setUp(self):
        """Set up test data"""
        self.model_data = {
            'model_name': 'crop_recommendation_v1',
            'model_version': '1.0.0',
            'accuracy': 0.85,
            'precision': 0.82,
            'recall': 0.88,
            'f1_score': 0.85,
            'r2_score': 0.78,
            'rmse': 0.12,
            'training_samples': 1000,
            'validation_samples': 200,
            'training_date': timezone.now(),
            'model_parameters': {'learning_rate': 0.01, 'epochs': 100},
            'feature_importance': {'soil_type': 0.3, 'weather': 0.4, 'location': 0.3}
        }
    
    def test_ml_model_performance_creation(self):
        """Test ML model performance creation"""
        model = MLModelPerformance.objects.create(**self.model_data)
        
        self.assertEqual(model.model_name, 'crop_recommendation_v1')
        self.assertEqual(model.model_version, '1.0.0')
        self.assertEqual(model.accuracy, 0.85)
        self.assertEqual(model.precision, 0.82)
        self.assertEqual(model.recall, 0.88)
        self.assertEqual(model.f1_score, 0.85)
        self.assertEqual(model.r2_score, 0.78)
        self.assertEqual(model.rmse, 0.12)
        self.assertEqual(model.training_samples, 1000)
        self.assertEqual(model.validation_samples, 200)
        self.assertEqual(model.model_parameters, {'learning_rate': 0.01, 'epochs': 100})
        self.assertEqual(model.feature_importance, {'soil_type': 0.3, 'weather': 0.4, 'location': 0.3})
        self.assertIsNotNone(model.created_at)
    
    def test_ml_model_performance_str_representation(self):
        """Test ML model performance string representation"""
        model = MLModelPerformance.objects.create(**self.model_data)
        expected_str = f"{model.model_name} v{model.model_version} - Accuracy: {model.accuracy}"
        self.assertEqual(str(model), expected_str)
    
    def test_ml_model_performance_optional_fields(self):
        """Test ML model performance with optional fields"""
        model_data = self.model_data.copy()
        model_data['accuracy'] = None
        model_data['precision'] = None
        model_data['recall'] = None
        model_data['f1_score'] = None
        model_data['r2_score'] = None
        model_data['rmse'] = None
        model_data['feature_importance'] = None
        
        model = MLModelPerformance.objects.create(**model_data)
        self.assertIsNone(model.accuracy)
        self.assertIsNone(model.precision)
        self.assertIsNone(model.recall)
        self.assertIsNone(model.f1_score)
        self.assertIsNone(model.r2_score)
        self.assertIsNone(model.rmse)
        self.assertIsNone(model.feature_importance)


class UserSessionModelTests(TestCase):
    """Test cases for UserSession model"""
    
    def setUp(self):
        """Set up test data"""
        self.session_data = {
            'user_id': 'user123',
            'session_id': 'session456',
            'total_interactions': 5,
            'latitude': 28.7041,
            'longitude': 77.1025,
            'location_name': 'Delhi',
            'preferred_language': 'en',
            'device_type': 'mobile',
            'session_summary': {'queries': 5, 'responses': 5}
        }
    
    def test_user_session_creation(self):
        """Test user session creation"""
        session = UserSession.objects.create(**self.session_data)
        
        self.assertEqual(session.user_id, 'user123')
        self.assertEqual(session.session_id, 'session456')
        self.assertEqual(session.total_interactions, 5)
        self.assertEqual(session.latitude, 28.7041)
        self.assertEqual(session.longitude, 77.1025)
        self.assertEqual(session.location_name, 'Delhi')
        self.assertEqual(session.preferred_language, 'en')
        self.assertEqual(session.device_type, 'mobile')
        self.assertEqual(session.session_summary, {'queries': 5, 'responses': 5})
        self.assertIsNotNone(session.start_time)
        self.assertIsNone(session.end_time)
    
    def test_user_session_str_representation(self):
        """Test user session string representation"""
        session = UserSession.objects.create(**self.session_data)
        expected_str = f"Session {session.session_id} for user {session.user_id}"
        self.assertEqual(str(session), expected_str)
    
    def test_user_session_unique_session_id(self):
        """Test user session unique session_id constraint"""
        UserSession.objects.create(**self.session_data)
        
        # Try to create another session with same session_id
        duplicate_session_data = self.session_data.copy()
        duplicate_session_data['user_id'] = 'different_user'
        
        with self.assertRaises(Exception):  # Should raise IntegrityError
            UserSession.objects.create(**duplicate_session_data)


class ChatHistoryModelTests(TestCase):
    """Test cases for ChatHistory model"""
    
    def setUp(self):
        """Set up test data"""
        self.chat_data = {
            'user_id': 'user123',
            'session_id': 'session456',
            'message_type': 'user',
            'message_content': 'What crops should I grow?',
            'detected_language': 'en',
            'response_language': 'en',
            'confidence_score': 0.9,
            'response_source': 'ai_assistant',
            'response_type': 'agricultural',
            'has_location': True,
            'has_product': True,
            'latitude': 28.7041,
            'longitude': 77.1025
        }
    
    def test_chat_history_creation(self):
        """Test chat history creation"""
        chat = ChatHistory.objects.create(**self.chat_data)
        
        self.assertEqual(chat.user_id, 'user123')
        self.assertEqual(chat.session_id, 'session456')
        self.assertEqual(chat.message_type, 'user')
        self.assertEqual(chat.message_content, 'What crops should I grow?')
        self.assertEqual(chat.detected_language, 'en')
        self.assertEqual(chat.response_language, 'en')
        self.assertEqual(chat.confidence_score, 0.9)
        self.assertEqual(chat.response_source, 'ai_assistant')
        self.assertEqual(chat.response_type, 'agricultural')
        self.assertTrue(chat.has_location)
        self.assertTrue(chat.has_product)
        self.assertEqual(chat.latitude, 28.7041)
        self.assertEqual(chat.longitude, 77.1025)
        self.assertIsNotNone(chat.created_at)
    
    def test_chat_history_str_representation(self):
        """Test chat history string representation"""
        chat = ChatHistory.objects.create(**self.chat_data)
        expected_str = f"{chat.message_type} from {chat.user_id} in session {chat.session_id}"
        self.assertEqual(str(chat), expected_str)
    
    def test_chat_history_message_type_choices(self):
        """Test chat history message type choices"""
        valid_types = ['user', 'assistant', 'system']
        
        for msg_type in valid_types:
            chat_data = self.chat_data.copy()
            chat_data['message_type'] = msg_type
            chat_data['message_content'] = f'Test {msg_type} message'
            
            chat = ChatHistory.objects.create(**chat_data)
            self.assertEqual(chat.message_type, msg_type)
            chat.delete()


class ChatSessionModelTests(TestCase):
    """Test cases for ChatSession model"""
    
    def setUp(self):
        """Set up test data"""
        self.chat_session_data = {
            'user_id': 'user123',
            'session_id': 'session456',
            'is_active': True,
            'conversation_context': {'location': 'Delhi', 'language': 'en'},
            'preferred_language': 'en',
            'location_name': 'Delhi',
            'latitude': 28.7041,
            'longitude': 77.1025,
            'total_messages': 10,
            'user_messages': 5,
            'assistant_messages': 5,
            'device_type': 'mobile',
            'user_agent': 'Mozilla/5.0...',
            'ip_address': '192.168.1.1'
        }
    
    def test_chat_session_creation(self):
        """Test chat session creation"""
        session = ChatSession.objects.create(**self.chat_session_data)
        
        self.assertEqual(session.user_id, 'user123')
        self.assertEqual(session.session_id, 'session456')
        self.assertTrue(session.is_active)
        self.assertEqual(session.conversation_context, {'location': 'Delhi', 'language': 'en'})
        self.assertEqual(session.preferred_language, 'en')
        self.assertEqual(session.location_name, 'Delhi')
        self.assertEqual(session.latitude, 28.7041)
        self.assertEqual(session.longitude, 77.1025)
        self.assertEqual(session.total_messages, 10)
        self.assertEqual(session.user_messages, 5)
        self.assertEqual(session.assistant_messages, 5)
        self.assertEqual(session.device_type, 'mobile')
        self.assertEqual(session.user_agent, 'Mozilla/5.0...')
        self.assertEqual(session.ip_address, '192.168.1.1')
        self.assertIsNotNone(session.start_time)
        self.assertIsNotNone(session.last_activity)
    
    def test_chat_session_str_representation(self):
        """Test chat session string representation"""
        session = ChatSession.objects.create(**self.chat_session_data)
        expected_str = f"Chat session {session.session_id} for user {session.user_id}"
        self.assertEqual(str(session), expected_str)
    
    def test_chat_session_unique_session_id(self):
        """Test chat session unique session_id constraint"""
        ChatSession.objects.create(**self.chat_session_data)
        
        # Try to create another session with same session_id
        duplicate_session_data = self.chat_session_data.copy()
        duplicate_session_data['user_id'] = 'different_user'
        
        with self.assertRaises(Exception):  # Should raise IntegrityError
            ChatSession.objects.create(**duplicate_session_data)


class ForumPostModelTests(TestCase):
    """Test cases for ForumPost model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.post_data = {
            'user': self.user,
            'title': 'Best crops for winter season',
            'content': 'I want to know about the best crops to grow during winter season.'
        }
    
    def test_forum_post_creation(self):
        """Test forum post creation"""
        post = ForumPost.objects.create(**self.post_data)
        
        self.assertEqual(post.user, self.user)
        self.assertEqual(post.title, 'Best crops for winter season')
        self.assertEqual(post.content, 'I want to know about the best crops to grow during winter season.')
        self.assertIsNotNone(post.created_at)
        self.assertIsNotNone(post.updated_at)
    
    def test_forum_post_str_representation(self):
        """Test forum post string representation"""
        post = ForumPost.objects.create(**self.post_data)
        expected_str = f"{post.title} by {post.user.username}"
        self.assertEqual(str(post), expected_str)
    
    def test_forum_post_cascade_delete(self):
        """Test that post is deleted when user is deleted"""
        post = ForumPost.objects.create(**self.post_data)
        post_id = post.id
        
        self.user.delete()
        
        with self.assertRaises(ForumPost.DoesNotExist):
            ForumPost.objects.get(id=post_id)
    
    def test_forum_post_ordering(self):
        """Test forum post ordering by created_at"""
        # Create multiple posts
        post1 = ForumPost.objects.create(**self.post_data)
        
        post2_data = self.post_data.copy()
        post2_data['title'] = 'Second post'
        post2 = ForumPost.objects.create(**post2_data)
        
        # Check ordering (newest first)
        posts = ForumPost.objects.all()
        self.assertEqual(posts[0], post2)  # Newest first
        self.assertEqual(posts[1], post1)  # Oldest last
