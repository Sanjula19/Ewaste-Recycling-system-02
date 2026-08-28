"""
API Router -- registers all v1 endpoints.
No simulate routes. /predict is at the correct path.
"""
from fastapi import APIRouter
from app.api.v1 import health, readings, predictions, alerts, dashboard, trials, export

api_router = APIRouter()

# Health check and MQTT status
api_router.include_router(health.router, tags=["health"])

# Raw sensor readings (read-only + labeling)
api_router.include_router(readings.router, prefix="/readings", tags=["readings"])

# ML prediction (POST /api/v1/predict)
api_router.include_router(predictions.router, prefix="/predict", tags=["predictions"])

# WHO alerts
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])

# Dashboard stats and chart data
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])

# Dataset trial management
api_router.include_router(trials.router, prefix="/trials", tags=["trials"])
# CSV export
api_router.include_router(export.router, prefix="/export", tags=["export"])