from django.shortcuts import render
from rest_framework import viewsets
from .serializers import CropAdvisorySerializer
from .models import CropAdvisory
from rest_framework.decorators import action
from rest_framework.response import Response
from .ai_models import predict_yield, detect_pest_disease, get_chatbot_response

# Create your views here.

class CropAdvisoryViewSet(viewsets.ModelViewSet):
    queryset = CropAdvisory.objects.all()
    serializer_class = CropAdvisorySerializer

    @action(detail=False, methods=['post'])
    def predict_yield(self, request):
        crop_type = request.data.get('crop_type')
        soil_type = request.data.get('soil_type')
        weather_data = request.data.get('weather_data')
        result = predict_yield(crop_type, soil_type, weather_data)
        return Response(result)

    @action(detail=False, methods=['post'])
    def detect_pest_disease(self, request):
        image_upload = request.data.get('image') # Assuming image is sent as a base64 string or URL
        result = detect_pest_disease(image_upload)
        return Response(result)

    @action(detail=False, methods=['post'])
    def chatbot(self, request):
        user_query = request.data.get('query')
        language = request.data.get('language', 'en')
        response = get_chatbot_response(user_query, language)
        return Response({'response': response})
