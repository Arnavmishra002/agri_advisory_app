"""IoT + blockchain simulation API."""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ...services.unified_realtime_service import iot_blockchain
from ..serializers import LocationQuerySerializer


class IoTBlockchainViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=["get"])
    def sensor_data(self, request):
        serializer = LocationQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response({"error": "Invalid sensor query", "errors": serializer.errors}, status=400)
        location = serializer.validated_data.get("location", "Delhi")
        data = iot_blockchain.get_iot_sensor_data(location)
        return Response(data)

    def list(self, request):
        return self.sensor_data(request)
