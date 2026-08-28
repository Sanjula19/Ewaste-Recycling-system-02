"""
Pydantic response models for raw sensor readings.
Field names match the DB schema exactly.
Raw ADC values are integers -- NOT ppm.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class RawReadingResponse(BaseModel):
    """
    One reading as returned by the API.
    mq2_raw / mq135_raw are raw ADC integers (0-4095).
    mq7_raw / mq136_raw are None (sensors not installed).
    """
    id:            int
    reading_id:    str
    device_id:     str
    received_at:   datetime
    temperature_c: Optional[float] = None
    humidity_pct:  Optional[float] = None
    mq2_raw:       Optional[int]   = None   # MQ-2 ADC -- connected
    mq135_raw:     Optional[int]   = None   # MQ-135 ADC -- connected
    mq7_raw:       Optional[int]   = None   # MQ-7 ADC -- NOT installed
    mq136_raw:     Optional[int]   = None   # MQ-136 ADC -- NOT installed
    source:        str = "mqtt"
    label:         Optional[str] = None
    label_note:    Optional[str] = None

    model_config = {"from_attributes": True}


class RawReadingList(BaseModel):
    readings:  List[RawReadingResponse]
    total:     int
    page:      int
    page_size: int


class LabelRequest(BaseModel):
    reading_id: str
    gas_label:  str
    labeled_by: Optional[str] = None
    label_note: Optional[str] = None
