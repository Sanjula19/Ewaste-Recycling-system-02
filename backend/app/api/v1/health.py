"""Health check and MQTT status endpoints."""
import time
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.database import get_db
from app.services.ml_service import ml_service
from app.services.mqtt_subscriber import mqtt_subscriber
from app.config import settings

router = APIRouter()
_START = time.time()


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    db_ok = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_ok = f"error: {e}"

    s = mqtt_subscriber.status
    return {
        "status":  "ok" if db_ok == "ok" else "degraded",
        "uptime_seconds": round(time.time() - _START, 1),
        "database": {"status": db_ok},
        "ml_model": {
            "loaded": ml_service.is_loaded,
            "version": ml_service.version,
            "prediction_available": False,
            "reason": "Requires 6 calibrated ppm inputs; only 2 raw ADC inputs currently available",
        },
        "mqtt": {
            "running":           s["running"],
            "connected":         s["connected"],
            "broker":            s["broker"],
            "topic":             s["topic"],
            "messages_received": s["messages_received"],
            "parse_errors":      s["parse_errors"],
            "last_received_at":  s["last_received_at"],
            "last_reading_id":   s["last_reading_id"],
        },
    }


@router.get("/mqtt/status")
async def mqtt_status():
    return mqtt_subscriber.status
