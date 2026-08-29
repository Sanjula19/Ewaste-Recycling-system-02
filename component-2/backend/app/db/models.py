"""
Database Models -- E-Waste Toxic Gas Detection System
=====================================================
Real ESP32 MQTT payload (actual hardware):
  {
    "device_id":   "ESP32_EWASTE_01",
    "temperature": 32.0,
    "humidity":    82.6,
    "mq2_raw":     17,
    "mq135_raw":   1665
  }

Schema stores values EXACTLY as received.
Raw ADC integers are NOT converted to ppm here.
MQ-7 and MQ-136 are not installed -- their columns are nullable.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from .database import Base


class RawReadingDB(Base):
    """
    One row per real MQTT message from ESP32.
    Values are stored as-received, no conversion applied.
    """
    __tablename__ = "raw_readings"

    id         = Column(Integer, primary_key=True, index=True)
    reading_id = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    device_id  = Column(String(50), nullable=False, index=True)   # from ESP32 payload
    received_at = Column(DateTime, default=datetime.utcnow, index=True)  # server timestamp

    # DHT22 readings
    temperature_c = Column(Float, nullable=True)   # "temperature" field from payload
    humidity_pct  = Column(Float, nullable=True)   # "humidity" field from payload

    # MQ sensor raw ADC values (0-4095 for ESP32 12-bit ADC)
    mq2_raw   = Column(Integer, nullable=True)   # MQ-2:   LPG / smoke  -- CONNECTED
    mq135_raw = Column(Integer, nullable=True)   # MQ-135: benzene/ammonia -- CONNECTED
    mq7_raw   = Column(Integer, nullable=True)   # MQ-7:   CO  -- NOT INSTALLED (null)
    mq136_raw = Column(Integer, nullable=True)   # MQ-136: H2S -- NOT INSTALLED (null)

    source = Column(String(20), nullable=False, default="mqtt")

    # Relationships
    label  = relationship("LabeledReadingDB", back_populates="raw_reading", uselist=False)
    alerts = relationship("AlertDB", back_populates="raw_reading")


class LabeledReadingDB(Base):
    """
    Researcher-assigned ground-truth gas labels.
    Only created during deliberate experimental exposure tests.
    """
    __tablename__ = "labeled_readings"

    id             = Column(Integer, primary_key=True, index=True)
    raw_reading_id = Column(Integer, ForeignKey("raw_readings.id"), unique=True, nullable=False)
    gas_label  = Column(String(50), nullable=False)   # e.g. "LPG", "CLEAN"
    labeled_by = Column(String(100), nullable=True)
    label_note = Column(Text, nullable=True)
    labeled_at = Column(DateTime, default=datetime.utcnow)

    raw_reading = relationship("RawReadingDB", back_populates="label")


class AlertDB(Base):
    """
    Safety alerts -- created when readings exceed configured thresholds.
    (Currently disabled until ppm calibration is available.)
    """
    __tablename__ = "alerts"

    id        = Column(Integer, primary_key=True, index=True)
    alert_id  = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    raw_reading_id = Column(Integer, ForeignKey("raw_readings.id"), nullable=False)
    device_id = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    gas_name        = Column(String(50), nullable=False)
    ppm_value       = Column(Float, nullable=True)
    who_limit       = Column(Float, nullable=True)
    unit            = Column(String(20), default="ppm")
    exceeded_by_pct = Column(Float, default=0.0)
    risk_level      = Column(String(20), nullable=False)  # YELLOW / RED

    health_risks   = Column(JSON, nullable=True)
    safety_actions = Column(JSON, nullable=True)

    acknowledged    = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)

    raw_reading = relationship("RawReadingDB", back_populates="alerts")


class TrialDB(Base):
    """
    One row per experiment trial (e.g. CLEAN_01, LPG_01).
    Readings that fall between started_at and ended_at
    belong to this trial. Condition is the gas exposure label.
    """
    __tablename__ = "trials"

    id         = Column(Integer, primary_key=True, index=True)
    trial_id   = Column(String(50), unique=True, nullable=False, index=True)
    condition  = Column(String(50), nullable=False)   # e.g. "CLEAN", "LPG"
    started_at = Column(DateTime, nullable=False)
    ended_at   = Column(DateTime, nullable=True)      # null = trial still running
    notes      = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)