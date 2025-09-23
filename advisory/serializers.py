from rest_framework import serializers
from .models import CropAdvisory

class CropAdvisorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CropAdvisory
        fields = '__all__'
