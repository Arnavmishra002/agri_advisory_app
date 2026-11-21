"""Sensor readings belong to the account that submitted them.

IoTSensorReading has no owner column, and any signed-in account could write a
reading for any field_id (including another farmer's "user:<id>") or plant one
next to a farm; the chatbot then treated it as that farmer's soil data.
"""
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from advisory.api.viewsets.chatbot import _load_farmer_context
from advisory.models import FarmerProfile, IoTSensorReading

User = get_user_model()
LUCKNOW = {"latitude": 26.8467, "longitude": 80.9462, "location": "Lucknow", "state": "Uttar Pradesh"}


class SensorFieldOwnershipTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner_farmer", password="strong-pass-123")
        self.attacker = User.objects.create_user(username="attacker_farmer", password="strong-pass-123")
        self.client = APIClient()
        self.client.force_authenticate(user=self.attacker)

    def _post(self, **extra):
        return self.client.post("/api/field-advisory/sensor_data/",
                                {**LUCKNOW, "nitrogen_kg_ha": 999, "moisture_pct": 5, **extra}, format="json")

    def test_readings_are_stored_under_the_submitting_account(self):
        self.assertEqual(self._post().status_code, 200)
        self.assertEqual(self._post(field_id="north_plot").status_code, 200)
        ids = set(IoTSensorReading.objects.values_list("field_id", flat=True))
        self.assertEqual(ids, {f"user:{self.attacker.pk}", f"user:{self.attacker.pk}:north_plot"})

    def test_another_farmers_field_cannot_be_written(self):
        response = self._post(field_id=f"user:{self.owner.pk}")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(IoTSensorReading.objects.exists())

    def test_chatbot_ignores_readings_planted_near_another_farm(self):
        FarmerProfile.objects.create(session_id=f"user:{self.owner.pk}", location_name="Owner farm",
                                     latitude=26.8467, longitude=80.9462)
        self._post()  # the attacker's own reading, right next to the owner's farm
        request = SimpleNamespace(user=self.owner, META={}, headers={})

        with patch("advisory.api.viewsets.chatbot._authenticated_user_for_profile", return_value=self.owner):
            context = _load_farmer_context(request, None, {})

        self.assertNotIn("sensor_reading", context)

    def test_general_chat_sensor_context_ignores_account_readings(self):
        from advisory.services.chat_intelligence_service import ChatIntelligenceService
        from advisory.services.location_context import LocationContext

        IoTSensorReading.objects.create(field_id=f"user:{self.attacker.pk}", latitude=26.8467,
                                        longitude=80.9462, moisture_pct=5)
        ctx = LocationContext(latitude=26.8467, longitude=80.9462, display_name="Lucknow")

        sensor = ChatIntelligenceService()._resolve_sensor_context(ctx, None)

        self.assertEqual(sensor.source, "none")

    def test_mqtt_payload_cannot_claim_an_account_field(self):
        from advisory.services.mqtt_sensor_subscriber import BatchedSensorIngestor

        buffer = BatchedSensorIngestor.__new__(BatchedSensorIngestor)
        buffer._bulk_insert([
            {"field_id": f"user:{self.owner.pk}", "latitude": 26.8, "longitude": 80.9, "moisture_pct": 5},
            {"field_id": "farm_001", "latitude": 26.8, "longitude": 80.9, "moisture_pct": 30},
        ])

        self.assertEqual(list(IoTSensorReading.objects.values_list("field_id", flat=True)), ["farm_001"])

    def _owner_context(self):
        request = SimpleNamespace(user=self.owner, META={}, headers={})
        with patch("advisory.api.viewsets.chatbot._authenticated_user_for_profile", return_value=self.owner):
            return _load_farmer_context(request, None, {})

    def test_chatbot_uses_only_recent_readings_near_the_farm(self):
        FarmerProfile.objects.create(session_id=f"user:{self.owner.pk}", location_name="Owner farm",
                                     latitude=26.8467, longitude=80.9462)
        owner_id = f"user:{self.owner.pk}"

        # The farmer's own reading for a leased plot in Kanpur is not this farm.
        IoTSensorReading.objects.create(field_id=f"{owner_id}:kanpur_plot", latitude=26.4499,
                                        longitude=80.3319, ph=8.9, moisture_pct=5)
        self.assertNotIn("sensor_reading", self._owner_context())

        # A reading months old is not the farm's current status.
        stale = IoTSensorReading.objects.create(field_id=owner_id, latitude=26.8467,
                                                longitude=80.9462, ph=7.9, moisture_pct=9)
        IoTSensorReading.objects.filter(pk=stale.pk).update(created_at=timezone.now() - timedelta(days=180))
        self.assertNotIn("sensor_reading", self._owner_context())

        # A labelled plot at the farm counts.
        IoTSensorReading.objects.create(field_id=f"{owner_id}:north_plot", latitude=26.8468,
                                        longitude=80.9463, ph=6.8, moisture_pct=31)
        self.assertEqual(self._owner_context()["sensor_reading"]["ph"], 6.8)

        # The farmer's default field is used first.
        IoTSensorReading.objects.create(field_id=owner_id, latitude=26.8467, longitude=80.9462,
                                        ph=6.5, moisture_pct=28)
        self.assertEqual(self._owner_context()["sensor_reading"]["ph"], 6.5)

    def test_rejected_mqtt_payload_does_not_trim_the_account_history(self):
        from advisory.services import mqtt_sensor_subscriber
        from advisory.services.mqtt_sensor_subscriber import BatchedSensorIngestor

        owner_id = f"user:{self.owner.pk}"
        for moisture in (10, 20, 30):
            IoTSensorReading.objects.create(field_id=owner_id, latitude=26.8, longitude=80.9,
                                            moisture_pct=moisture)
        buffer = BatchedSensorIngestor.__new__(BatchedSensorIngestor)

        with patch.object(mqtt_sensor_subscriber, "MAX_READINGS_PER_FIELD", 1), \
                patch.object(mqtt_sensor_subscriber, "_last_trim_time", 0.0):
            buffer._bulk_insert([
                {"field_id": owner_id, "latitude": 26.8, "longitude": 80.9, "moisture_pct": 5},
                {"field_id": "farm_001", "latitude": 26.8, "longitude": 80.9, "moisture_pct": 30},
            ])

        self.assertEqual(IoTSensorReading.objects.filter(field_id=owner_id).count(), 3)
