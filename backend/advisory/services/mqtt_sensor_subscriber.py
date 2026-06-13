"""
KrishiMitra MQTT Sensor Subscriber — Phase 2 & 3
=================================================
Listens for ESP32 IoT sensor telemetry via MQTT and persists readings
to the IoTSensorReading model. Once running, the chatbot's
_resolve_sensor_context() Tier 1 DB path activates automatically.

Refactored to use thread-safe batching (BatchedSensorIngestor) to prevent
SQLite database locking under concurrent sensor streams.

Hardware setup:
  ESP32 → WiFi → Mosquitto broker → this subscriber → Django DB
                                                        ↓
                                             ChatIntelligenceService
                                             uses real sensor readings

ESP32 publishes to topic:
  krishimitra/farm/{field_id}/telemetry

Payload (JSON):
  {
    "field_id":        "farm_001",
    "latitude":        28.7041,
    "longitude":       77.1025,
    "moisture_pct":    42.3,
    "soil_temp_c":     24.1,
    "nitrogen_kg_ha":  185.0,
    "phosphorus_kg_ha": 18.5,
    "potassium_kg_ha": 142.0,
    "ph":              6.8,
    "ec_ds_m":         0.45,
    "sensor_device_id": "ESP32-001"
  }

Usage (run as a background Celery task or standalone process):
  # Standalone:
  python manage.py run_mqtt_subscriber

  # Or import and call:
  from advisory.services.mqtt_sensor_subscriber import mqtt_subscriber
  mqtt_subscriber.start()

Requirements (install when hardware is ready):
  pip install paho-mqtt==1.6.1

Configuration (add to .env):
  MQTT_BROKER_HOST=localhost
  MQTT_BROKER_PORT=1883
  MQTT_USERNAME=krishimitra
  MQTT_PASSWORD=<your-password>
  MQTT_TOPIC_PREFIX=krishimitra/farm
  MQTT_CLIENT_ID=krishimitra-backend
"""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
MQTT_BROKER_HOST   = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT   = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_USERNAME      = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD      = os.getenv("MQTT_PASSWORD", "")
MQTT_TOPIC_PREFIX  = os.getenv("MQTT_TOPIC_PREFIX", "krishimitra/farm")
MQTT_CLIENT_ID     = os.getenv("MQTT_CLIENT_ID", "krishimitra-backend")
MQTT_SUBSCRIBE     = f"{MQTT_TOPIC_PREFIX}/+/telemetry"   # + wildcard = any field_id
MQTT_KEEPALIVE     = 60
MQTT_QOS           = 1   # at-least-once delivery

# Maximum sensor readings to retain per field (keeps DB lean)
MAX_READINGS_PER_FIELD = 100

# Batch configuration
BATCH_FLUSH_INTERVAL = 10  # seconds
BATCH_SIZE_THRESHOLD = 20  # flush immediately if queue size reaches threshold
TRIM_INTERVAL = 300        # trim oldest records every 5 minutes to keep DB clean
_last_trim_time = 0.0


# ── Batched Sensor Ingestion ───────────────────────────────────────────────

class BatchedSensorIngestor:
    """Thread-safe buffer that collects sensor telemetry and inserts in bulk."""

    def __init__(self):
        self._queue = queue.Queue()
        self._lock = threading.Lock()
        self._last_flush = time.time()

    def add_reading(self, payload: Dict[str, Any]) -> None:
        self._queue.put(payload)
        if self._queue.qsize() >= BATCH_SIZE_THRESHOLD:
            self.flush()

    def flush(self) -> None:
        """Perform bulk database insert for all queued payloads."""
        with self._lock:
            qsize = self._queue.qsize()
            if qsize == 0:
                return

            payloads_to_write = []
            for _ in range(qsize):
                try:
                    payloads_to_write.append(self._queue.get_nowait())
                except queue.Empty:
                    break

            if not payloads_to_write:
                return

            self._bulk_insert(payloads_to_write)
            self._last_flush = time.time()

    def check_periodic_flush(self) -> None:
        """Call periodically from background thread to flush on time intervals."""
        if time.time() - self._last_flush >= BATCH_FLUSH_INTERVAL:
            self.flush()

    def _bulk_insert(self, payloads: List[Dict[str, Any]]) -> None:
        try:
            import django
            if not django.conf.settings.configured:
                return

            from advisory.models import IoTSensorReading
            from django.utils import timezone

            readings = []
            for p in payloads:
                try:
                    readings.append(
                        IoTSensorReading(
                            field_id=str(p.get("field_id", "unknown")),
                            latitude=float(p["latitude"]),
                            longitude=float(p["longitude"]),
                            location_name=p.get("location_name", ""),
                            state=p.get("state", ""),
                            moisture_pct=p.get("moisture_pct"),
                            soil_temp_c=p.get("soil_temp_c"),
                            nitrogen_kg_ha=p.get("nitrogen_kg_ha"),
                            phosphorus_kg_ha=p.get("phosphorus_kg_ha"),
                            potassium_kg_ha=p.get("potassium_kg_ha"),
                            ph=p.get("ph"),
                            ec_ds_m=p.get("ec_ds_m"),
                            organic_carbon=p.get("organic_carbon"),
                            sensor_device_id=p.get("sensor_device_id", ""),
                            created_at=timezone.now() if hasattr(timezone, 'now') else datetime.now()
                        )
                    )
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning("Skipping malformed sensor payload: %s", e)

            if readings:
                IoTSensorReading.objects.bulk_create(readings)
                logger.info("Successfully bulk-inserted %d sensor readings.", len(readings))

                # Periodically trim old readings beyond MAX_READINGS_PER_FIELD to keep DB lean
                global _last_trim_time
                now_time = time.time()
                if now_time - _last_trim_time >= TRIM_INTERVAL:
                    _last_trim_time = now_time
                    try:
                        field_ids = {p.get("field_id") for p in payloads if p.get("field_id")}
                        for f_id in field_ids:
                            old_ids = list(
                                IoTSensorReading.objects
                                .filter(field_id=f_id)
                                .order_by("-created_at")
                                .values_list("id", flat=True)[MAX_READINGS_PER_FIELD:]
                            )
                            if old_ids:
                                IoTSensorReading.objects.filter(id__in=old_ids).delete()
                        logger.info("Successfully trimmed old readings for fields: %s", list(field_ids))
                    except Exception as trim_exc:
                        logger.warning("Periodic sensor trimming failed: %s", trim_exc)

        except Exception as exc:
            logger.error("Failed to execute bulk sensor insert: %s", exc)


sensor_ingestor = BatchedSensorIngestor()


# ── Payload Validation ────────────────────────────────────────────────────────

def _validate_payload(raw: bytes) -> Optional[Dict[str, Any]]:
    """Parse and validate MQTT payload. Returns dict or None on failure."""
    try:
        data = json.loads(raw.decode("utf-8"))
        if "latitude" not in data or "longitude" not in data:
            logger.warning("Sensor payload missing lat/lon: %s", str(data)[:100])
            return None
        return data
    except json.JSONDecodeError as exc:
        logger.warning("Invalid JSON in MQTT payload: %s", exc)
        return None


# ── Subscriber Daemon ─────────────────────────────────────────────────────────

class MQTTSensorSubscriber:
    """
    MQTT client that listens for ESP32 sensor telemetry and writes to Django DB.

    Designed to run as a background thread or standalone process.
    Reconnects automatically on broker disconnect.
    Safe to import even when paho-mqtt is not installed — raises ImportError
    only when start() is called.
    """

    def __init__(self):
        self._client          = None
        self._running         = False
        self._thread: Optional[threading.Thread] = None
        self._flusher_thread: Optional[threading.Thread] = None
        self._connected       = False
        self._reconnect_delay = 5   # seconds

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self, blocking: bool = False) -> None:
        """
        Start the MQTT subscriber.

        Args:
            blocking: If True, blocks the calling thread. If False (default),
                      runs in a background daemon thread.
        """
        try:
            import paho.mqtt.client as mqtt_lib
        except ImportError:
            raise ImportError(
                "paho-mqtt is required for sensor integration. "
                "Install it: pip install paho-mqtt==1.6.1\n"
                "Then set MQTT_BROKER_HOST in .env."
            )

        self._running = True

        # Start helper thread to check for time-based batch flushes
        self._flusher_thread = threading.Thread(
            target=self._periodic_flush_worker,
            daemon=True,
            name="mqtt-batch-flusher"
        )
        self._flusher_thread.start()

        if blocking:
            self._run_loop(mqtt_lib)
        else:
            self._thread = threading.Thread(
                target=self._run_loop,
                args=(mqtt_lib,),
                daemon=True,
                name="mqtt-sensor-subscriber",
            )
            self._thread.start()
            logger.info("MQTT subscriber started in background thread")

    def stop(self) -> None:
        """Stop the subscriber gracefully."""
        self._running = False
        if self._client:
            try:
                self._client.disconnect()
            except Exception:
                pass
        # Final flush on stop
        sensor_ingestor.flush()
        logger.info("MQTT subscriber stopped")

    def is_running(self) -> bool:
        return bool(self._running and self._thread and self._thread.is_alive())

    # ── Internal ──────────────────────────────────────────────────────────────

    def _run_loop(self, mqtt_lib) -> None:
        """Main loop with auto-reconnect."""
        while self._running:
            try:
                self._connect(mqtt_lib)
                self._client.loop_forever()
            except Exception as exc:
                logger.error("MQTT loop error: %s — reconnecting in %ds", exc, self._reconnect_delay)
                time.sleep(self._reconnect_delay)

    def _periodic_flush_worker(self) -> None:
        """Checks every second if the buffer flush timer has expired."""
        while self._running:
            try:
                sensor_ingestor.check_periodic_flush()
            except Exception as exc:
                logger.error("Periodic flusher encountered error: %s", exc)
            time.sleep(1)

    def _connect(self, mqtt_lib) -> None:
        client = mqtt_lib.Client(client_id=MQTT_CLIENT_ID, clean_session=True)

        if MQTT_USERNAME:
            client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

        client.on_connect    = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message    = self._on_message

        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=MQTT_KEEPALIVE)
        self._client = client
        logger.info("Connecting to MQTT broker %s:%d", MQTT_BROKER_HOST, MQTT_BROKER_PORT)

    def _on_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            self._connected = True
            client.subscribe(MQTT_SUBSCRIBE, qos=MQTT_QOS)
            logger.info("MQTT connected. Subscribed to: %s", MQTT_SUBSCRIBE)
        else:
            logger.error("MQTT connection failed (rc=%d)", rc)

    def _on_disconnect(self, client, userdata, rc) -> None:
        self._connected = False
        if rc != 0:
            logger.warning("MQTT unexpected disconnect (rc=%d)", rc)

    def _on_message(self, client, userdata, msg) -> None:
        logger.debug("MQTT message on %s: %s", msg.topic, msg.payload[:80])
        payload = _validate_payload(msg.payload)
        if payload is None:
            return

        # Extract field_id from topic: krishimitra/farm/{field_id}/telemetry
        parts = msg.topic.split("/")
        if len(parts) >= 3 and not payload.get("field_id"):
            payload["field_id"] = parts[-2]

        sensor_ingestor.add_reading(payload)


# ── Module-level singleton ────────────────────────────────────────────────────
mqtt_subscriber = MQTTSensorSubscriber()
