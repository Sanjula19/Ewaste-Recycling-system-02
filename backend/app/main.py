"""
FastAPI Application -- E-Waste Toxic Gas Detection System
=========================================================
Startup sequence:
  1. Create DB tables (if not exists)
  2. Load ML models
  3. Start MQTT subscriber background thread
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging

from app.config import settings
from app.middleware.cors import add_cors_middleware
from app.api.v1.router import api_router
from app.services.ml_service import ml_service
from app.services.mqtt_subscriber import mqtt_subscriber
from app.db.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- Startup ----
    logger.info("=" * 60)
    logger.info("E-Waste Toxic Gas Detection System -- Starting up")
    logger.info("=" * 60)

    # 1. Initialise DB tables
    logger.info("Initialising database...")
    await init_db()
    logger.info("Database ready.")

    # 2. Load ML models
    logger.info("Loading ML models...")
    ml_service.load_models()
    if ml_service.is_loaded:
        logger.info(f"ML models loaded (version: {ml_service.version})")
    else:
        logger.warning("ML models NOT loaded -- predictions will return error responses")

    # 3. Start real MQTT subscriber
    logger.info(f"Starting MQTT subscriber -> {settings.mqtt_broker}:{settings.mqtt_port}")
    logger.info(f"Subscribing to topic: {settings.mqtt_topic}")
    mqtt_subscriber.start()

    logger.info("Startup complete. Waiting for ESP32 MQTT messages...")
    logger.info("=" * 60)

    yield

    # ---- Shutdown ----
    logger.info("Shutting down -- stopping MQTT subscriber...")
    mqtt_subscriber.stop()
    logger.info("Shutdown complete.")


app = FastAPI(
    title=settings.app_name,
    description=(
        "E-Waste Toxic Gas Detection System Backend API. "
        "Receives real sensor data from ESP32 via MQTT. "
        "No simulated or hardcoded data."
    ),
    version=settings.app_version,
    lifespan=lifespan,
)

add_cors_middleware(app)
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "message": "E-Waste Toxic Gas Detection System API",
        "docs": "/docs",
        "health": "/api/v1/health",
        "mqtt_status": "/api/v1/mqtt/status",
        "latest_reading": "/api/v1/readings/latest",
    }
