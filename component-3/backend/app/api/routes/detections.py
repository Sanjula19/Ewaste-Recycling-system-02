# backend/app/api/routes/detections.py
#
# Receives classified-item detections pushed from Component 1 (AI Waste
# Assessment: POST /waste/predict -> {waste_type, condition, final_grade}).
# Mirrors the sensor.py pattern: Component 1 (or its integration bridge)
# pushes here, the Component 3 frontend polls and drains the queue.
#
# NOTE: weight_kg is intentionally NOT accepted here — Component 1's
# /waste/predict response has no weight field (the real weight lives on the
# Raspberry Pi's load cell, in weight_camera.py, and is never sent to the
# backend). The frontend asks the user to confirm a real weight before an
# incoming detection can be added to the batch queue, rather than fabricating
# one.

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter()

# In-memory queue — detections wait here until the frontend polls and drains them.
_pending_detections = []


class Detection(BaseModel):
    waste_type: str                          # "Plastic" | "Glass" | "Metal" | "Paper" | "Cardboard"
    condition: str                           # "Clean" | "Contaminated" | "Damaged"
    final_grade: str                         # "A" | "B" | "C"
    waste_confidence: Optional[float] = None
    condition_confidence: Optional[float] = None


@router.post("/api/detections/push")
async def push_detection(detection: Detection):
    """Component 1 posts a classified item here as soon as it has one."""
    _pending_detections.append({
        **detection.dict(),
        "timestamp": datetime.now().isoformat(),
    })
    return {"status": "queued", "pending_count": len(_pending_detections)}


@router.get("/api/detections/pending")
async def get_pending_detections():
    """Component 3 frontend polls here and claims (drains) whatever has arrived."""
    global _pending_detections
    items = _pending_detections
    _pending_detections = []
    return {"count": len(items), "detections": items}
