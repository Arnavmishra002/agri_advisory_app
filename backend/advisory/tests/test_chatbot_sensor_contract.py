import json
from datetime import timedelta
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from advisory.services.chat_intelligence_service import ChatIntelligenceService


def _sensor_payload(**overrides):
    payload = {
        "source": "esp32",
        "device_id": "field-node-17",
        "observed_at": timezone.now().isoformat(),
        "soil_moisture_pct": 70,
        "nitrogen_kg_ha": 180,
        "phosphorus_kg_ha": 22,
        "potassium_kg_ha": 140,
    }
    payload.update(overrides)
    return payload


@override_settings(RATE_LIMIT_ENABLED=False)
class ChatbotSensorContractTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/chatbot/query/"
        self.base = {
            "query": "Should I irrigate my wheat today?",
            "language": "en",
            "location": "Lucknow",
            "latitude": 26.8467,
            "longitude": 80.9462,
        }

    @patch("advisory.api.viewsets.chatbot._dispatch_writes")
    @patch("advisory.api.viewsets.chatbot.chat_intelligence_service.answer")
    def test_canonical_sensor_context_is_normalised_and_forwarded(self, answer, _writes):
        answer.return_value = {
            "response": "Moisture is adequate, so do not irrigate now.",
            "intent": "irrigation",
            "language": "en",
            "data_source": "KrishiMitra Advisory Engine",
            "iot_sensors_used": True,
            "sensor_source": "esp32:field-node-17",
            "sensor_observed_at": _sensor_payload()["observed_at"],
            "sensor_age_seconds": 1,
            "weather_constraints": {"irrigation_blocked": True},
        }

        response = self.client.post(
            self.url,
            {**self.base, "sensor_context": _sensor_payload()},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        forwarded = answer.call_args.kwargs["sensor_context"]
        self.assertEqual(forwarded["soil_moisture_pct"], 70.0)
        self.assertEqual(forwarded["source"], "esp32")
        self.assertTrue(response.json()["iot_sensors_used"])
        self.assertTrue(response.json()["weather_constraints"]["irrigation_blocked"])

    @patch("advisory.api.viewsets.chatbot._dispatch_writes")
    @patch("advisory.api.viewsets.chatbot.chat_intelligence_service.answer")
    def test_legacy_sensors_alias_is_accepted(self, answer, _writes):
        answer.return_value = {
            "response": "Use the measured NPK values.",
            "intent": "fertilizer",
            "language": "en",
            "data_source": "KrishiMitra Advisory Engine",
        }

        response = self.client.post(
            self.url,
            {**self.base, "sensors": _sensor_payload(soil_moisture_percentage=61)},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        forwarded = answer.call_args.kwargs["sensor_context"]
        self.assertEqual(forwarded["soil_moisture_pct"], 70.0)

    def test_sending_both_sensor_fields_is_rejected(self):
        response = self.client.post(
            self.url,
            {
                **self.base,
                "sensor_context": _sensor_payload(),
                "sensors": _sensor_payload(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("sensor_context", str(response.json()["details"]))

    def test_unknown_or_non_numeric_sensor_values_are_rejected(self):
        for sensor in (
            _sensor_payload(soil_moisture_pct="wet"),
            _sensor_payload(unexpected="reject"),
        ):
            with self.subTest(sensor=sensor):
                response = self.client.post(
                    self.url,
                    {**self.base, "sensor_context": sensor},
                    format="json",
                )
                self.assertEqual(response.status_code, 400)

    def test_stale_sensor_payload_is_rejected(self):
        stale = (timezone.now() - timedelta(minutes=31)).isoformat()
        response = self.client.post(
            self.url,
            {**self.base, "sensor_context": _sensor_payload(observed_at=stale)},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("observed_at", str(response.json()["details"]))

    @patch("advisory.api.viewsets.chatbot._dispatch_writes")
    @patch("advisory.api.viewsets.chatbot._load_farmer_context", return_value={})
    @patch(
        "advisory.api.viewsets.chatbot._build_history_and_context",
        return_value=([], {}, "en"),
    )
    @patch("advisory.api.viewsets.chatbot.chat_intelligence_service.answer_stream")
    def test_sse_final_frame_contains_sensor_safety_metadata(
        self, answer_stream, _history, _farmer, _writes
    ):
        observed_at = _sensor_payload()["observed_at"]
        answer_stream.return_value = iter([
            "Do not irrigate.",
            {
                "__done__": True,
                "intent": "irrigation",
                "language": "en",
                "iot_sensors_used": True,
                "sensor_source": "esp32:field-node-17",
                "sensor_observed_at": observed_at,
                "sensor_age_seconds": 1,
                "weather_constraints": {"irrigation_blocked": True},
            },
        ])

        response = self.client.post(
            "/api/chatbot/stream/",
            data=json.dumps({**self.base, "sensor_context": _sensor_payload()}),
            content_type="application/json",
        )
        frames = "".join(part.decode("utf-8") for part in response.streaming_content)
        done = json.loads(frames.strip().split("\n\n")[-1].removeprefix("data: "))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(done["iot_sensors_used"])
        self.assertEqual(done["sensor_source"], "esp32:field-node-17")
        self.assertTrue(done["weather_constraints"]["irrigation_blocked"])
        self.assertEqual(
            answer_stream.call_args.kwargs["sensor_context"]["device_id"],
            "field-node-17",
        )


class GroundedPromptContractTests(SimpleTestCase):
    def test_public_prompt_builder_is_deterministic_and_complete(self):
        service = ChatIntelligenceService()
        sensor = _sensor_payload()
        government = {
            "location": "Lucknow, Uttar Pradesh",
            "season": "Kharif",
            "forecast_3day": "Tomorrow: rain 12mm",
            "active_weather_warnings": "Heavy rain warning",
            "government_rag_snippets": "ICAR wheat irrigation guidance",
            "current_market_price": "Live mandi rows unavailable",
        }

        first = service.build_grounded_prompt(sensor, government, "Should I irrigate?", language="en")
        second = service.build_grounded_prompt(sensor, government, "Should I irrigate?", language="en")

        self.assertEqual(first, second)
        self.assertIn("[FIELD SENSOR DATA]", first)
        self.assertIn("70.0%", first)
        self.assertIn("Heavy rain warning", first)
        self.assertIn("Should I irrigate?", first)
        self.assertNotIn("{farmer_query}", first)
