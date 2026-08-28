"""
Pydantic models for alerts.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


class RiskLevel(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class AlertResponse(BaseModel):
    alert_id: str
    raw_reading_id: int
    timestamp: datetime
    device_id: str
    risk_level: RiskLevel
    gas_name: str
    ppm_value: Optional[float] = None
    who_limit: Optional[float] = None
    measured_value: Optional[float] = None
    threshold: Optional[float] = None
    unit: str
    exceeded_by_pct: float
    health_risks: List[str]
    safety_actions: List[str]
    acknowledged: bool
    acknowledged_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AlertList(BaseModel):
    alerts: List[AlertResponse]
    total: int
    page: int
    page_size: int
