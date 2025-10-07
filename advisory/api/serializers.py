from rest_framework import serializers
from ..models import CropAdvisory, Crop, User, ForumPost # Update import for models

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'first_name', 'last_name')
        read_only_fields = ('role',) # Role should typically be set by admin, not user directly via registration

class CropSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crop
        fields = '__all__'

class CropAdvisorySerializer(serializers.ModelSerializer):
    # Define choices for validation
    SOIL_TYPE_CHOICES = [
        ('sandy', 'Sandy'),
        ('clayey', 'Clayey'),
        ('loamy', 'Loamy'),
        ('silty', 'Silty'),
        ('peaty', 'Peaty'),
    ]
    WEATHER_CONDITION_CHOICES = [
        ('sunny', 'Sunny'),
        ('cloudy', 'Cloudy'),
        ('rainy', 'Rainy'),
        ('humid', 'Humid'),
        ('dry', 'Dry'),
    ]

    crop = CropSerializer(read_only=True)
    crop_id = serializers.PrimaryKeyRelatedField(queryset=Crop.objects.all(), source='crop', write_only=True)
    soil_type = serializers.ChoiceField(choices=SOIL_TYPE_CHOICES)
    weather_condition = serializers.ChoiceField(choices=WEATHER_CONDITION_CHOICES)

    class Meta:
        model = CropAdvisory
        fields = '__all__'

class SMSSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20, required=True)
    message = serializers.CharField(max_length=160, required=True)

class IVRInputSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20, required=True)
    user_input = serializers.CharField(max_length=255, required=True)

class PestDetectionSerializer(serializers.Serializer):
    image = serializers.ImageField(required=True)

class TextToSpeechSerializer(serializers.Serializer):
    text = serializers.CharField(required=True)
    language = serializers.CharField(max_length=10, default='en')

class ForumPostSerializer(serializers.ModelSerializer):
    user_username = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = ForumPost
        fields = ('id', 'user', 'user_username', 'title', 'content', 'created_at', 'updated_at')
        read_only_fields = ('user', 'created_at', 'updated_at')

# API Endpoint Serializers for Swagger Documentation
class YieldPredictionSerializer(serializers.Serializer):
    crop_type = serializers.CharField(max_length=100, help_text="Type of crop (e.g., 'rice', 'wheat', 'corn')")
    soil_type = serializers.CharField(max_length=100, help_text="Type of soil (e.g., 'sandy', 'clayey', 'loamy')")
    weather_data = serializers.DictField(required=False, help_text="Weather data dictionary")
    temperature = serializers.FloatField(default=25.0, help_text="Temperature in Celsius")
    rainfall = serializers.FloatField(default=800.0, help_text="Rainfall in mm")
    humidity = serializers.FloatField(default=60.0, help_text="Humidity percentage")
    ph = serializers.FloatField(default=6.5, help_text="Soil pH level")
    organic_matter = serializers.FloatField(default=2.0, help_text="Organic matter percentage")
    season = serializers.CharField(default='kharif', help_text="Growing season (kharif/rabi)")

class ChatbotSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=500, help_text="User's question or query")
    language = serializers.ChoiceField(
        choices=[('en', 'English'), ('hi', 'Hindi'), ('hinglish', 'Hinglish'), ('auto', 'Auto-detect')],
        default='en', 
        help_text="Language code (en, hi, hinglish, auto)"
    )
    user_id = serializers.CharField(default='anonymous', max_length=100, help_text="User identifier")
    session_id = serializers.CharField(required=False, max_length=100, help_text="Session identifier")
    latitude = serializers.FloatField(required=False, help_text="Latitude coordinate")
    longitude = serializers.FloatField(required=False, help_text="Longitude coordinate")
    conversation_history = serializers.ListField(required=False, help_text="Previous conversation history")
    location_name = serializers.CharField(required=False, max_length=100, help_text="Location name")

class FertilizerRecommendationSerializer(serializers.Serializer):
    crop_type = serializers.CharField(max_length=100, help_text="Type of crop")
    soil_type = serializers.CharField(max_length=100, help_text="Type of soil")
    season = serializers.CharField(default='kharif', max_length=50, help_text="Growing season")
    area_hectares = serializers.FloatField(default=1.0, help_text="Area in hectares")
    language = serializers.CharField(default='en', max_length=10, help_text="Language code")

class CropRecommendationSerializer(serializers.Serializer):
    soil_type = serializers.CharField(max_length=100, required=False, help_text="Type of soil (auto-detected if not provided)")
    latitude = serializers.FloatField(help_text="Latitude coordinate")
    longitude = serializers.FloatField(help_text="Longitude coordinate")
    season = serializers.CharField(default='kharif', max_length=50, help_text="Growing season")
    user_id = serializers.CharField(default='anonymous', max_length=100, help_text="User identifier")
    forecast_days = serializers.IntegerField(default=7, min_value=1, max_value=14, help_text="Weather forecast days")

class FeedbackSerializer(serializers.Serializer):
    user_id = serializers.CharField(max_length=100, help_text="User identifier")
    session_id = serializers.CharField(max_length=100, help_text="Session identifier")
    prediction_type = serializers.CharField(max_length=100, help_text="Type of prediction")
    input_data = serializers.DictField(help_text="Input data used for prediction")
    system_prediction = serializers.DictField(help_text="System's prediction")
    actual_result = serializers.DictField(help_text="Actual result")
    feedback_rating = serializers.IntegerField(min_value=1, max_value=5, help_text="Rating from 1-5")
    feedback_text = serializers.CharField(required=False, max_length=500, help_text="Additional feedback text")
    latitude = serializers.FloatField(required=False, help_text="Latitude coordinate")
    longitude = serializers.FloatField(required=False, help_text="Longitude coordinate")