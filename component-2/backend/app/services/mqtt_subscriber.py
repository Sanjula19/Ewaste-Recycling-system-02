"""
MQTT Subscriber -- E-Waste Toxic Gas Detection System
=====================================================
Broker : HiveMQ Cloud (TLS/SSL, port 8883, username+password)
Topic  : ewaste/esp32/sensors

Real ESP32 payload (from firmware mqtt_handler.cpp):
  {
    "device_id":   "ESP32_EWASTE_01",
    "temperature": 32.40,
    "humidity":    81.90,
    "mq2_raw":     5,
    "mq135_raw":   1589,
    "mq7_raw":     120
  }

Sensors:
  MQ-2   -- CONNECTED, real ADC value stored as mq2_raw
  MQ-7   -- CONNECTED (newly added), real ADC value stored as mq7_raw
  MQ-135 -- CONNECTED, real ADC value stored as mq135_raw
  MQ-136 -- REMOVED, mq136_raw always NULL

Bug fix (2026-08-21):
  DetachedInstanceError after session.commit() caused only 1st message to be
  stored. Fix: generate reading_id UUID before ORM object creation, and use
  expire_on_commit=False so attributes remain accessible after commit.
"""
import json
import logging
import ssl
import threading
import time
import uuid
import traceback
from datetime import datetime, timezone
from typing import Optional

import paho.mqtt.client as mqtt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.models import RawReadingDB

logger = logging.getLogger(__name__)

# Fields required in every valid payload
REQUIRED_FIELDS = {"temperature", "humidity", "mq2_raw", "mq135_raw"}


class MQTTSubscriber:
    """
    Background MQTT subscriber (paho-mqtt thread).
    Connects to HiveMQ Cloud with TLS + credentials.
    Uses a synchronous SQLAlchemy engine so it is safe from asyncio.
    """

    def __init__(self):
        self._client: Optional[mqtt.Client] = None
        self._thread: Optional[threading.Thread] = None
        self._running   = False
        self._connected = False
        self._messages_received = 0
        self._parse_errors      = 0
        self._db_errors         = 0
        self._last_received_at: Optional[str] = None
        self._last_reading_id:  Optional[str] = None
        self._last_error:       Optional[str] = None

        # Synchronous engine (strip async driver for thread safety)
        sync_url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
        self._engine = create_engine(
            sync_url,
            connect_args={"check_same_thread": False},
        )
        self._Session = sessionmaker(
            bind=self._engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,   # CRITICAL: prevents DetachedInstanceError
        )

    # ── Public interface ───────────────────────────────────────────────

    def start(self):
        if self._running:
            logger.warning("[MQTT] Subscriber already running")
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="mqtt-subscriber"
        )
        self._thread.start()
        logger.info("[MQTT] Subscriber thread started")

    def stop(self):
        self._running = False
        if self._client:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:
                pass
        logger.info("[MQTT] Subscriber stopped")

    @property
    def status(self) -> dict:
        return {
            "running":            self._running,
            "connected":          self._connected,
            "broker":             settings.mqtt_broker,
            "port":               settings.mqtt_port,
            "topic":              settings.mqtt_topic,
            "messages_received":  self._messages_received,
            "parse_errors":       self._parse_errors,
            "db_errors":          self._db_errors,
            "last_received_at":   self._last_received_at,
            "last_reading_id":    self._last_reading_id,
            "last_error":         self._last_error,
        }

    # ── MQTT callbacks ─────────────────────────────────────────────────

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self._connected = True
            logger.info(
                f"[MQTT] Connected to {settings.mqtt_broker}:{settings.mqtt_port}"
            )
            client.subscribe(settings.mqtt_topic, qos=1)
            logger.info(f"[MQTT] Subscribed to topic: {settings.mqtt_topic}")
        else:
            self._connected = False
            logger.error(f"[MQTT] Connection failed, rc={rc}")

    def _on_disconnect(self, client, userdata, rc, properties=None, reason_code=None):
        self._connected = False
        if rc != 0:
            logger.warning(f"[MQTT] Unexpected disconnect (rc={rc}), will auto-retry")

    def _on_message(self, client, userdata, msg):
        """
        Called for every incoming MQTT message.
        Every valid message creates exactly ONE new row in raw_readings.
        """
        raw_str = msg.payload.decode("utf-8", errors="replace").strip()
        logger.info(f"[MQTT] RECEIVED: {raw_str}")

        # ── 1. JSON parse ─────────────────────────────────────────────
        try:
            data = json.loads(raw_str)
        except json.JSONDecodeError as e:
            self._parse_errors += 1
            self._last_error = f"JSON error: {e}"
            logger.error(f"[MQTT] Malformed JSON rejected: {self._last_error}")
            return

        if not isinstance(data, dict):
            self._parse_errors += 1
            self._last_error = "Payload is not a JSON object"
            logger.error(f"[MQTT] Rejected: {self._last_error}")
            return

        # ── 2. Validate required fields ───────────────────────────────
        missing = REQUIRED_FIELDS - data.keys()
        if missing:
            self._parse_errors += 1
            self._last_error = f"Missing required fields: {missing}"
            logger.error(
                f"[MQTT] Rejected: {self._last_error} | payload={data}"
            )
            return

        # ── 3. Extract values as plain Python types (NOT ORM objects) ──
        try:
            device_id = str(data.get("device_id", "ESP32_UNKNOWN"))
            temp_c    = float(data["temperature"]) if data.get("temperature") is not None else None
            hum_pct   = float(data["humidity"])    if data.get("humidity")    is not None else None
            mq2       = int(data["mq2_raw"])       if data.get("mq2_raw")    is not None else None
            mq135     = int(data["mq135_raw"])     if data.get("mq135_raw")  is not None else None
            # mq7_raw is optional — present when MQ-7 sensor is connected
            mq7       = int(data["mq7_raw"])       if data.get("mq7_raw")    is not None else None
            rid       = str(uuid.uuid4())          # UUID generated BEFORE ORM object
        except (ValueError, TypeError) as e:
            self._parse_errors += 1
            self._last_error = f"Type conversion error: {e}"
            logger.error(f"[MQTT] Rejected: {self._last_error}")
            return

        logger.info(
            f"[MQTT] PARSED: device={device_id} | "
            f"temp={temp_c} hum={hum_pct} | "
            f"MQ2={mq2} MQ7={mq7} MQ135={mq135} | "
            f"rid={rid[:8]}..."
        )

        # ── 4. Insert into DB ─────────────────────────────────────────
        try:
            logger.info(f"[MQTT] INSERTING READING {rid[:8]}...")
            now = datetime.now(timezone.utc)

            session = self._Session()
            try:
                reading = RawReadingDB(
                    reading_id    = rid,
                    device_id     = device_id,
                    received_at   = now,
                    temperature_c = temp_c,
                    humidity_pct  = hum_pct,
                    mq2_raw       = mq2,
                    mq7_raw       = mq7,     # Real value from MQ-7 (None if not in payload)
                    mq135_raw     = mq135,
                    mq136_raw     = None,    # MQ-136 removed from system
                    source        = "mqtt",
                )
                session.add(reading)
                session.commit()
                db_id = reading.id          # safe because expire_on_commit=False
                logger.info(f"[MQTT] COMMITTED READING: {rid} (db_id={db_id})")
            except Exception as e:
                session.rollback()
                raise e
            finally:
                session.close()

            # Update counters using plain Python values only
            self._messages_received += 1
            self._last_received_at  = now.isoformat()
            self._last_reading_id   = rid
            logger.info(
                f"[MQTT] Stored #{self._messages_received}: "
                f"MQ2={mq2} MQ7={mq7} MQ135={mq135} "
                f"temp={temp_c} hum={hum_pct}"
            )

        except Exception as e:
            self._db_errors += 1
            self._last_error = f"DB error: {e}"
            logger.error(f"[MQTT] ERROR: {self._last_error}")
            logger.error(f"[MQTT] TRACEBACK:\n{traceback.format_exc()}")

    # ── Reconnect loop with TLS ────────────────────────────────────────

    def _run_loop(self):
        retry_delay = 5
        while self._running:
            try:
                self._client = mqtt.Client(
                    client_id=f"ewaste-backend-{uuid.uuid4().hex[:8]}",
                    protocol=mqtt.MQTTv311,
                    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                )

                # HiveMQ Cloud requires TLS + username/password
                self._client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)
                self._client.username_pw_set(
                    settings.mqtt_user, settings.mqtt_password
                )

                self._client.on_connect    = self._on_connect
                self._client.on_disconnect = self._on_disconnect
                self._client.on_message    = self._on_message

                logger.info(
                    f"[MQTT] Connecting to {settings.mqtt_broker}:{settings.mqtt_port} (TLS)..."
                )
                self._client.connect(
                    settings.mqtt_broker, settings.mqtt_port, keepalive=60
                )
                retry_delay = 5   # reset on successful connect
                self._client.loop_forever()

            except Exception as e:
                self._connected = False
                self._last_error = f"Connection exception: {e}"
                logger.error(f"[MQTT] {self._last_error}")

            if self._running:
                logger.info(f"[MQTT] Reconnecting in {retry_delay}s...")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)


mqtt_subscriber = MQTTSubscriber()
