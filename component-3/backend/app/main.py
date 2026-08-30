"""
Component 3 - Smart Process Optimization Engine
FastAPI Main Application
IT22277640 - SLIIT
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.models.material_model.load_models import load_all_models
from app.api.routes import optimize, history, health, materials, sensor, detections, reports
from app.config import initialize_firebase

app = FastAPI(
    title="Component 3 - Smart Process Optimization Engine",
    description="AI-powered waste recycling process optimizer - IT22277640",
    version="1.0.0"
)

# CORS - allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(optimize.router,  prefix="/api", tags=["Optimize"])
app.include_router(history.router,   prefix="/api", tags=["History"])
app.include_router(health.router,    prefix="/api", tags=["Health"])
app.include_router(materials.router, prefix="/api", tags=["Materials"])
app.include_router(sensor.router, tags=["Sensor"])  # sensor routes already carry the /api prefix
app.include_router(detections.router, tags=["Detections"])  # also carries the /api prefix
app.include_router(reports.router, tags=["Reports"])  # also carries the /api prefix

@app.on_event("startup")
async def startup_event():
    """Load models and initialize Firebase on startup."""
    load_all_models()
    initialize_firebase()
    print("=" * 50)
    print("  Component 3 API Started!")
    print("  POST /api/optimize")
    print("  GET  /api/history")
    print("  GET  /api/health")
    print("  Docs: http://localhost:8000/docs")
    print("=" * 50)


@app.get("/")
def root():
    return {
        "component" : "Component 3 - Smart Process Optimization Engine",
        "student"   : "IT22277640",
        "status"    : "running",
        "version"   : "1.0.0",
        "docs"      : "http://localhost:8000/docs"
    }
