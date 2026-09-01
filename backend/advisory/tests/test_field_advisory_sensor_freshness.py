from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model

from advisory.models import IoTSensorReading
from advisory.services.field_sensor_service import field_sensor_service


class FieldAdvisorySensorFreshnessTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Reading a saved sensor value back is gated behind authentication
        # (saved readings are another farmer's private soil data and field_id
        # is derived from coordinates). These tests exercise the freshness
        # logic, which sits behind that gate, so they authenticate first.
        self.user = get_user_model().objects.create_user(
            username="freshness-tester", password="unused-password-123"
        )
        self.client.force_authenticate(user=self.user)

    @patch.dict("os.environ", {"IOT_SENSOR_MAX_AGE_MINUTES": "60"})
    @patch("advisory.api.viewsets.field_advisory.field_sensor_service.get_field_recommendation")
    def test_stale_saved_sensor_reading_is_not_used_as_realtime_input(self, mock_recommend):
        reading = IoTSensorReading.objects.create(
            field_id="field-1",
            latitude=26.8467,
            longitude=80.9462,
            location_name="Lucknow",
            state="Uttar Pradesh",
            nitrogen_kg_ha=140,
            phosphorus_kg_ha=22,
            potassium_kg_ha=180,
            ph=6.8,
            moisture_pct=38,
        )
        stale_time = timezone.now() - timedelta(hours=3)
        IoTSensorReading.objects.filter(pk=reading.pk).update(created_at=stale_time)

        mock_recommend.return_value = {
            "status": "success",
            "recommendations": [],
            "data_sources": ["Open-Meteo"],
        }

        response = self.client.get(
            "/api/field-advisory/recommend/",
            {
                "latitude": "26.8467",
                "longitude": "80.9462",
                "field_id": "field-1",
                "state": "Uttar Pradesh",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(mock_recommend.call_args.kwargs["sensor_data"])
        freshness = response.data["sensor_freshness"]
        self.assertEqual(freshness["status"], "stale_ignored")
        self.assertEqual(freshness["field_id"], "field-1")
        self.assertGreaterEqual(freshness["age_minutes"], 180)
        self.assertIn("Sensor reading is stale", freshness["message"])

    @patch.dict("os.environ", {"IOT_SENSOR_MAX_AGE_MINUTES": "60"})
    @patch("advisory.api.viewsets.field_advisory.field_sensor_service.get_field_recommendation")
    def test_fresh_saved_sensor_reading_is_used_with_age_metadata(self, mock_recommend):
        reading = IoTSensorReading.objects.create(
            field_id="field-2",
            latitude=26.8467,
            longitude=80.9462,
            location_name="Lucknow",
            state="Uttar Pradesh",
            nitrogen_kg_ha=140,
            moisture_pct=38,
        )
        fresh_time = timezone.now() - timedelta(minutes=10)
        IoTSensorReading.objects.filter(pk=reading.pk).update(created_at=fresh_time)

        mock_recommend.return_value = {
            "status": "success",
            "recommendations": [],
            "data_sources": [],
        }

        response = self.client.get(
            "/api/field-advisory/recommend/",
            {
                "latitude": "26.8467",
                "longitude": "80.9462",
                "field_id": "field-2",
                "state": "Uttar Pradesh",
            },
        )

        self.assertEqual(response.status_code, 200)
        sensor_data = mock_recommend.call_args.kwargs["sensor_data"]
        self.assertIsNotNone(sensor_data)
        self.assertEqual(sensor_data["_sensor_meta"]["status"], "fresh_saved")
        self.assertLessEqual(sensor_data["_sensor_meta"]["age_minutes"], 11)
        self.assertEqual(response.data["sensor_freshness"]["status"], "fresh_saved")

    def test_sensor_source_labels_preserve_freshness_context(self):
        sensor_data = {
            "sensors": {"nitrogen_kg_ha": 120, "moisture_pct": 35},
            "_sensor_meta": {
                "status": "fresh_saved",
                "recorded_at": "2026-07-04T10:00:00+05:30",
                "age_minutes": 12,
            },
        }

        merged = field_sensor_service._merge_soil_data(
            om_data={"soil_layers": {}},
            govt_soil={},
            sensor_data=sensor_data,
        )

        self.assertEqual(merged["sensor_timestamp"], "2026-07-04T10:00:00+05:30")
        self.assertEqual(merged["sensor_freshness"]["status"], "fresh_saved")
        self.assertIn("fresh saved reading, 12 min old", merged["data_sources"][-1])

    def test_request_payload_sensor_values_are_labeled_farmer_entered(self):
        sensor_data = {
            "sensors": {"nitrogen_kg_ha": 120, "moisture_pct": 35},
            "_sensor_meta": {
                "status": "farmer_entered",
                "source": "request_payload",
                "recorded_at": "2026-07-19T10:00:00+05:30",
                "age_minutes": 0,
            },
        }

        merged = field_sensor_service._merge_soil_data(
            om_data={"soil_layers": {}},
            govt_soil={},
            sensor_data=sensor_data,
        )

        self.assertEqual(merged["sensor_freshness"]["status"], "farmer_entered")
        self.assertIn("Farmer-entered soil/sensor values", merged["data_sources"][-1])
        self.assertNotIn("live request", merged["data_sources"][-1].lower())
