import os
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIRequestFactory

from advisory.api.viewsets.iot import IoTBlockchainViewSet
from advisory.services.chat_intelligence_service import (
    ChatIntelligenceService,
    SensorContext,
    WeatherConstraints,
)
from advisory.services.location_context import LocationContext
from advisory.services.unified_realtime_service import BlockchainIoTSimulator


class ChatSensorTruthfulnessTests(TestCase):
    def setUp(self):
        self.service = ChatIntelligenceService()
        self.ctx = LocationContext(
            latitude=26.8467,
            longitude=80.9462,
            display_name="Lucknow",
            state="Uttar Pradesh",
        )

    @patch("advisory.services.unified_realtime_service.iot_blockchain.get_iot_sensor_data")
    def test_chat_does_not_fallback_to_simulated_sensor_data(self, simulator):
        sensor_context = self.service._resolve_sensor_context(self.ctx)

        simulator.assert_not_called()
        self.assertEqual(sensor_context.source, "none")
        self.assertIsNone(sensor_context.soil_moisture_pct)
        self.assertIsNone(sensor_context.nitrogen_kg_ha)
        self.assertEqual(sensor_context.moisture_status, "Unknown")

    def test_unavailable_sensor_context_is_not_rendered_as_live(self):
        prompt = self.service._render_grounded_prompt(
            query="Should I irrigate today?",
            ctx=self.ctx,
            sc=SensorContext(source="none"),
            wc=WeatherConstraints(forecast_3day="Forecast unavailable"),
            rag="No specific advisory found.",
            market_price_str="No live price rows today",
            history_block="No prior messages.",
            lang="en",
            season="Kharif",
        )

        self.assertNotIn("[LIVE SENSOR DATA]", prompt)
        self.assertIn("[FIELD SENSOR DATA]", prompt)
        self.assertIn("N/A - sensor data unavailable", prompt)


class IoTSimulatorTruthfulnessTests(SimpleTestCase):
    def test_iot_endpoint_default_response_is_unavailable_not_fake_readings(self):
        with patch.dict(os.environ, {"KRISHIMITRA_ENABLE_IOT_DEMO": "0"}, clear=False):
            request = APIRequestFactory().get(
                "/api/iot-blockchain/sensor_data/",
                {"location": "Delhi"},
            )
            response = IoTBlockchainViewSet.as_view({"get": "sensor_data"})(request)

        self.assertEqual(response.data["status"], "unavailable")
        self.assertFalse(response.data["is_live"])
        self.assertFalse(response.data["simulation"])
        self.assertNotIn("readings", response.data)
        self.assertFalse(response.data["blockchain"]["verified"])

    def test_demo_iot_data_is_explicitly_non_live_and_unverified(self):
        with patch.dict(os.environ, {"KRISHIMITRA_ENABLE_IOT_DEMO": "true"}, clear=False):
            data = BlockchainIoTSimulator().get_iot_sensor_data("Delhi")

        self.assertEqual(data["status"], "demo")
        self.assertFalse(data["is_live"])
        self.assertTrue(data["simulation"])
        self.assertEqual(data["data_source"], "demo_iot_simulator")
        self.assertFalse(data["blockchain"]["verified"])
