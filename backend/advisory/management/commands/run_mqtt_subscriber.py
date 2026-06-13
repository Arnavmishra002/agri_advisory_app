"""
Management command: run_mqtt_subscriber
========================================
Starts the MQTT sensor subscriber as a blocking foreground process.

Usage:
    python manage.py run_mqtt_subscriber

In production, run via Supervisor or as a Procfile worker:
    worker: python manage.py run_mqtt_subscriber

Requires paho-mqtt: pip install paho-mqtt==1.6.1
"""

import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Start MQTT sensor subscriber for ESP32 IoT telemetry (Phase 2)"

    def handle(self, *args, **options):
        from advisory.services.mqtt_sensor_subscriber import (
            MQTT_BROKER_HOST,
            MQTT_BROKER_PORT,
            MQTT_SUBSCRIBE,
            mqtt_subscriber,
        )

        self.stdout.write(self.style.SUCCESS(
            f"Starting MQTT subscriber → {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}"
        ))
        self.stdout.write(f"Topic: {MQTT_SUBSCRIBE}")
        self.stdout.write("Press Ctrl+C to stop.\n")

        try:
            mqtt_subscriber.start(blocking=True)
        except ImportError as e:
            self.stderr.write(self.style.ERROR(str(e)))
        except KeyboardInterrupt:
            self.stdout.write("\nShutting down MQTT subscriber.")
            mqtt_subscriber.stop()
