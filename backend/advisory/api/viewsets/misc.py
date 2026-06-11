"""Placeholder viewsets for SMS/IVR, users, TTS, and forum."""

from rest_framework import viewsets
from rest_framework.response import Response


class SMSIVRViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({"message": "SMS/IVR service"})


class UserViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({"message": "User service"})


class TextToSpeechViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({"message": "Text to speech service"})


class ForumPostViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({"message": "Forum post service"})
