"""
Pydantic models for ML prediction requests and responses.
6 features only -- mq303_ppm is NOT part of this system.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    """
    Sensor values to run ML prediction on.
    Feature order matches the scaler:
      mq2_ppm, mq7_ppm, mq135_ppm, mq136_ppm, temperature_c, humidity_pct
    """
    mq2_ppm: float = Field(default=0.0, ge=0.0, description="MQ-2 reading (LPG/propane/methane, ppm)")
    mq7_ppm: float = Field(default=0.0, ge=0.0, description="MQ-7 reading (CO, ppm)")
    mq135_ppm: float = Field(default=0.0, ge=0.0, description="MQ-135 reading (benzene/ammonia, ppm)")
    mq136_ppm: float = Field(default=0.0, ge=0.0, description="MQ-136 reading (H2S, ppm)")
    temperature_c: float = Field(default=25.0, description="Temperature (Celsius)")
    humidity_pct: float = Field(default=50.0, ge=0.0, le=100.0, description="Relative humidity (%)")


class RiskAssessment(BaseModel):
    gas_name: str
    reading: float
    who_limit: float
    unit: str
    exceeded_by_pct: float
    risk_level: str   # GREEN / YELLOW / RED


class MultiLabelResult(BaseModel):
    gas: str
    detected: bool


class PredictionResponse(BaseModel):
    model_loaded: bool
    gas_class: Optional[str] = None
    confidence: Optional[float] = None
    model_version: str
    model_data_warning: Optional[str] = None
    error: Optional[str] = None
    risk_assessments: Optional[List[RiskAssessment]] = None
    multi_label_gases: Optional[List[str]] = None

    model_config = {"protected_namespaces": ()}
