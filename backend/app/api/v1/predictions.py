"""
Predictions API -- ML gas classification.

The current ML model requires 6 features:
  [mq2_ppm, mq7_ppm, mq135_ppm, mq136_ppm, temperature_c, humidity_pct]

However:
  - The ESP32 sends raw ADC values, NOT calibrated ppm values.
  - MQ-7 and MQ-136 are currently NOT installed.

Therefore: ML prediction is unavailable until:
  1. All 6 sensors are connected, AND
  2. ADC-to-ppm calibration constants are applied.

This endpoint returns a clear status message explaining why.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class PredictionStatus(BaseModel):
    available:    bool
    reason:       str
    sensors_needed:  list
    sensors_present: list


@router.post("", response_model=PredictionStatus)
async def predict():
    """
    ML prediction is currently unavailable.
    Required sensors (MQ-7, MQ-136) are not installed.
    Current ESP32 only provides MQ-2 and MQ-135 raw ADC values.
    """
    return PredictionStatus(
        available    = False,
        reason       = (
            "ML prediction unavailable: required sensors are not currently connected. "
            "The model needs 6 calibrated ppm values. "
            "Currently only MQ-2 and MQ-135 raw ADC readings are available. "
            "Connect MQ-7 and MQ-136, apply ADC-to-ppm calibration, then retrain."
        ),
        sensors_needed   = ["MQ-2 (ppm)", "MQ-7 (ppm)", "MQ-135 (ppm)", "MQ-136 (ppm)", "temperature", "humidity"],
        sensors_present  = ["MQ-2 (raw ADC)", "MQ-135 (raw ADC)", "temperature", "humidity"],
    )


@router.get("/status", response_model=PredictionStatus)
async def prediction_status():
    """Return current ML prediction availability status."""
    return await predict()
