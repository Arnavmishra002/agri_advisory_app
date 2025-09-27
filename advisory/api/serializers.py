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
