"""
Component 3 - GET /history route
"""
from fastapi import APIRouter
from app.services.firestore_service import get_optimization_history

router = APIRouter()


@router.get("/history")
def history(limit: int = 20):
    """Retrieve past optimization results from Firestore."""
    results = get_optimization_history(limit=limit)
    return {"count": len(results), "results": results}
