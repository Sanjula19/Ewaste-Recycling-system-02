"""
Component 3 - GET /health route
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    """API health check."""
    return {
        "status"    : "ok",
        "component" : "Component 3 - Smart Process Optimization Engine",
        "student"   : "IT22277640",
        "version"   : "1.0.0"
    }
