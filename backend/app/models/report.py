from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel
from .gas_reading import RawReadingResponse


class DashboardStats(BaseModel):
    total_readings:     int
    total_alerts:       int
    active_devices:     int
    latest_received_at: Optional[datetime] = None
    latest_reading:     Optional[RawReadingResponse] = None
    mqtt_connected:     bool = False
    mqtt_last_received_at: Optional[datetime] = None
    sensor_data_recent: bool = False
    sensor_data_status: str = "no_data"


class ChartDataPoint(BaseModel):
    timestamp:    datetime
    temperature_c: Optional[float] = None
    humidity_pct:  Optional[float] = None
    mq2_raw:       Optional[int]   = None
    mq7_raw:       Optional[int]   = None   # MQ-7 CO sensor (newly added)
    mq135_raw:     Optional[int]   = None


class ChartDataResponse(BaseModel):
    data_points: List[ChartDataPoint]
    total:       int
