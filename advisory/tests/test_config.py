#!/usr/bin/env python3
"""
Test Configuration and Utilities
Common test utilities and configuration for all test modules
"""

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Test configuration
TEST_CONFIG = {
    'DATABASES': {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    },
    'CACHES': {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    },
    'SECRET_KEY': 'test-secret-key-for-testing-only',
    'DEBUG': True,
    'ALLOWED_HOSTS': ['*'],
    'INSTALLED_APPS': [
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'rest_framework',
        'rest_framework_simplejwt',
        'advisory',
    ],
    'MIDDLEWARE': [
        'django.middleware.security.SecurityMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
    ],
    'ROOT_URLCONF': 'core.urls',
    'REST_FRAMEWORK': {
        'DEFAULT_AUTHENTICATION_CLASSES': (
            'rest_framework_simplejwt.authentication.JWTAuthentication',
        ),
        'DEFAULT_PERMISSION_CLASSES': [
            'rest_framework.permissions.IsAuthenticated',
        ],
    },
    'SIMPLE_JWT': {
        'ACCESS_TOKEN_LIFETIME': 300,  # 5 minutes
        'REFRESH_TOKEN_LIFETIME': 86400,  # 1 day
    },
    'AUTH_USER_MODEL': 'advisory.User',
    'USE_TZ': True,
    'TIME_ZONE': 'UTC',
    'LANGUAGE_CODE': 'en-us',
    'USE_I18N': True,
    'USE_L10N': True,
    'STATIC_URL': '/static/',
    'MEDIA_URL': '/media/',
    'MEDIA_ROOT': os.path.join(os.path.dirname(__file__), 'test_media'),
    'STATIC_ROOT': os.path.join(os.path.dirname(__file__), 'test_static'),
}

# Mock data for testing
MOCK_DATA = {
    'users': [
        {
            'username': 'testuser1',
            'email': 'test1@example.com',
            'password': 'testpass123',
            'role': 'farmer'
        },
        {
            'username': 'testuser2',
            'email': 'test2@example.com',
            'password': 'testpass123',
            'role': 'admin'
        },
        {
            'username': 'testuser3',
            'email': 'test3@example.com',
            'password': 'testpass123',
            'role': 'officer'
        }
    ],
    'crops': [
        {
            'name': 'Wheat',
            'description': 'Winter cereal crop',
            'ideal_soil_type': 'Loamy',
            'min_temperature_c': 10.0,
            'max_temperature_c': 25.0,
            'min_rainfall_mm_per_month': 50.0,
            'max_rainfall_mm_per_month': 100.0,
            'duration_days': 150
        },
        {
            'name': 'Rice',
            'description': 'Summer cereal crop',
            'ideal_soil_type': 'Clayey',
            'min_temperature_c': 20.0,
            'max_temperature_c': 35.0,
            'min_rainfall_mm_per_month': 200.0,
            'max_rainfall_mm_per_month': 300.0,
            'duration_days': 120
        }
    ],
    'locations': [
        {
            'name': 'Delhi',
            'latitude': 28.7041,
            'longitude': 77.1025,
            'state': 'Delhi'
        },
        {
            'name': 'Mumbai',
            'latitude': 19.0760,
            'longitude': 72.8777,
            'state': 'Maharashtra'
        },
        {
            'name': 'Bangalore',
            'latitude': 12.9716,
            'longitude': 77.5946,
            'state': 'Karnataka'
        }
    ],
    'weather_data': {
        'delhi': {
            'temperature': 25.0,
            'humidity': 60,
            'condition': 'Sunny',
            'wind_speed': 10,
            'pressure': 1013
        },
        'mumbai': {
            'temperature': 28.0,
            'humidity': 75,
            'condition': 'Humid',
            'wind_speed': 15,
            'pressure': 1010
        }
    },
    'market_prices': {
        'wheat': {
            'price_per_quintal': 2450,
            'unit': 'Quintal',
            'location': 'Delhi',
            'date': '2023-01-01'
        },
        'rice': {
            'price_per_quintal': 3200,
            'unit': 'Quintal',
            'location': 'Delhi',
            'date': '2023-01-01'
        }
    },
    'government_schemes': [
        {
            'name': 'PM-Kisan',
            'description': 'Direct income support to farmers',
            'eligibility': 'Small and marginal farmers',
            'benefit': 'Rs. 6000 per year'
        },
        {
            'name': 'Soil Health Card',
            'description': 'Soil health assessment and recommendations',
            'eligibility': 'All farmers',
            'benefit': 'Free soil testing'
        }
    ]
}

# Test utilities
class TestUtilities:
    """Common test utilities"""
    
    @staticmethod
    def create_test_user(username='testuser', email='test@example.com', password='testpass123', role='farmer'):
        """Create a test user"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=role
        )
    
    @staticmethod
    def create_test_crop(name='Test Crop', **kwargs):
        """Create a test crop"""
        from advisory.models import Crop
        
        crop_data = {
            'name': name,
            'description': 'Test crop description',
            'ideal_soil_type': 'Loamy',
            'min_temperature_c': 10.0,
            'max_temperature_c': 25.0,
            'min_rainfall_mm_per_month': 50.0,
            'max_rainfall_mm_per_month': 100.0,
            'duration_days': 150
        }
        crop_data.update(kwargs)
        
        return Crop.objects.create(**crop_data)
    
    @staticmethod
    def create_test_chat_session(user_id='testuser', session_id='test_session'):
        """Create a test chat session"""
        from advisory.models import ChatSession
        
        return ChatSession.objects.create(
            user_id=user_id,
            session_id=session_id,
            conversation_context={'test': 'data'},
            preferred_language='en'
        )
    
    @staticmethod
    def create_test_chat_history(user_id='testuser', session_id='test_session', message_type='user', content='Test message'):
        """Create test chat history"""
        from advisory.models import ChatHistory
        
        return ChatHistory.objects.create(
            user_id=user_id,
            session_id=session_id,
            message_type=message_type,
            message_content=content,
            detected_language='en',
            response_language='en'
        )
    
    @staticmethod
    def get_auth_headers(user):
        """Get authentication headers for API requests"""
        from rest_framework.test import APIClient
        from django.urls import reverse
        
        client = APIClient()
        
        # Get JWT token
        token_url = reverse('token_obtain_pair')
        response = client.post(token_url, {
            'username': user.username,
            'password': 'testpass123'
        }, format='json')
        
        if response.status_code == 200:
            token = response.data['access']
            return {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        
        return {}
    
    @staticmethod
    def mock_external_api_response(status_code=200, json_data=None):
        """Create a mock external API response"""
        from unittest.mock import Mock
        
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.json.return_value = json_data or {}
        
        return mock_response
    
    @staticmethod
    def assert_response_structure(response_data, expected_keys):
        """Assert that response has expected structure"""
        for key in expected_keys:
            assert key in response_data, f"Expected key '{key}' not found in response"
    
    @staticmethod
    def assert_api_response(response, expected_status=200, expected_keys=None):
        """Assert API response structure and status"""
        assert response.status_code == expected_status, f"Expected status {expected_status}, got {response.status_code}"
        
        if expected_keys and response.status_code == 200:
            response_data = response.json()
            TestUtilities.assert_response_structure(response_data, expected_keys)

# Test data factories
class TestDataFactory:
    """Factory for creating test data"""
    
    @staticmethod
    def create_user_batch(count=5, role='farmer'):
        """Create a batch of test users"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        users = []
        for i in range(count):
            user = User.objects.create_user(
                username=f'testuser{i}',
                email=f'test{i}@example.com',
                password='testpass123',
                role=role
            )
            users.append(user)
        
        return users
    
    @staticmethod
    def create_crop_batch(count=5):
        """Create a batch of test crops"""
        from advisory.models import Crop
        
        crops = []
        crop_names = ['Wheat', 'Rice', 'Maize', 'Cotton', 'Sugarcane']
        
        for i in range(min(count, len(crop_names))):
            crop = Crop.objects.create(
                name=crop_names[i],
                description=f'Test {crop_names[i]} crop',
                ideal_soil_type='Loamy',
                min_temperature_c=10.0 + i,
                max_temperature_c=25.0 + i,
                min_rainfall_mm_per_month=50.0 + i * 10,
                max_rainfall_mm_per_month=100.0 + i * 10,
                duration_days=120 + i * 10
            )
            crops.append(crop)
        
        return crops
    
    @staticmethod
    def create_chat_session_batch(count=5):
        """Create a batch of test chat sessions"""
        from advisory.models import ChatSession
        
        sessions = []
        for i in range(count):
            session = ChatSession.objects.create(
                user_id=f'testuser{i}',
                session_id=f'test_session_{i}',
                conversation_context={'test': f'data_{i}'},
                preferred_language='en'
            )
            sessions.append(session)
        
        return sessions

# Performance testing utilities
class PerformanceTestUtils:
    """Utilities for performance testing"""
    
    @staticmethod
    def measure_response_time(func, *args, **kwargs):
        """Measure function execution time"""
        import time
        
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        return result, end_time - start_time
    
    @staticmethod
    def assert_response_time(response_time, max_time):
        """Assert that response time is within acceptable limits"""
        assert response_time < max_time, f"Response time {response_time:.2f}s exceeds maximum {max_time}s"
    
    @staticmethod
    def benchmark_api_endpoint(client, url, method='GET', data=None, iterations=10):
        """Benchmark API endpoint performance"""
        import time
        
        times = []
        
        for _ in range(iterations):
            start_time = time.time()
            
            if method == 'GET':
                response = client.get(url, data)
            elif method == 'POST':
                response = client.post(url, data, format='json')
            
            end_time = time.time()
            times.append(end_time - start_time)
        
        return {
            'min_time': min(times),
            'max_time': max(times),
            'avg_time': sum(times) / len(times),
            'times': times
        }

# Test configuration for different environments
TEST_ENVIRONMENTS = {
    'unit': {
        'description': 'Unit tests - fast, isolated tests',
        'database': 'sqlite',
        'cache': 'locmem',
        'external_apis': 'mocked'
    },
    'integration': {
        'description': 'Integration tests - test component interactions',
        'database': 'sqlite',
        'cache': 'locmem',
        'external_apis': 'mocked'
    },
    'api': {
        'description': 'API tests - test API endpoints',
        'database': 'sqlite',
        'cache': 'locmem',
        'external_apis': 'mocked'
    },
    'performance': {
        'description': 'Performance tests - test response times and load',
        'database': 'sqlite',
        'cache': 'locmem',
        'external_apis': 'mocked'
    }
}

# Test markers for pytest
PYTEST_MARKERS = [
    'unit: Unit tests',
    'integration: Integration tests',
    'api: API tests',
    'performance: Performance tests',
    'slow: Slow running tests',
    'external: Tests that require external services'
]

if __name__ == '__main__':
    # Run tests
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['advisory.tests'])
    
    if failures:
        sys.exit(bool(failures))

