# backend/app/api/routes/sensor.py

from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

# Simple in-memory storage for the latest reading (per material type)
latest_sensor_data = {
    "moisture_status": "Dry",
    "raw_value": None,
    "timestamp": None,
}

class SensorReading(BaseModel):
    moisture_status: str  # "Wet" or "Dry"
    raw_value: int

@router.post("/api/sensor/moisture")
async def receive_moisture_reading(reading: SensorReading):
    """ESP32 posts here every few seconds."""
    latest_sensor_data["moisture_status"] = reading.moisture_status
    latest_sensor_data["raw_value"] = reading.raw_value
    latest_sensor_data["timestamp"] = datetime.now().isoformat()
    return {"status": "received", "data": latest_sensor_data}

@router.get("/api/sensor/moisture/latest")
async def get_latest_moisture():
    """Dashboard calls this to show the live reading."""
    return latest_sensor_data