"""
Dashboard API -- statistics and chart data from real stored readings.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.db.database import get_db
from app.db.models import RawReadingDB, AlertDB
from app.models.report import DashboardStats, ChartDataPoint, ChartDataResponse
from app.models.gas_reading import RawReadingResponse
from app.services.mqtt_subscriber import mqtt_subscriber

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    total_readings = (await db.execute(select(func.count(RawReadingDB.id)))).scalar_one() or 0
    total_alerts   = (await db.execute(select(func.count(AlertDB.id)))).scalar_one() or 0
    active_devices = (await db.execute(
        select(func.count(func.distinct(RawReadingDB.device_id)))
    )).scalar_one() or 0

    r = (await db.execute(
        select(RawReadingDB)
        .order_by(RawReadingDB.received_at.desc(), RawReadingDB.id.desc())
        .limit(1)
    )).scalar_one_or_none()

    latest_reading = None
    latest_ts      = None
    if r:
        latest_ts = r.received_at
        latest_reading = RawReadingResponse(
            id            = r.id,
            reading_id    = r.reading_id,
            device_id     = r.device_id,
            received_at   = r.received_at,
            temperature_c = r.temperature_c,
            humidity_pct  = r.humidity_pct,
            mq2_raw       = r.mq2_raw,
            mq135_raw     = r.mq135_raw,
            mq7_raw       = r.mq7_raw,
            mq136_raw     = r.mq136_raw,
            source        = r.source,
        )

    mqtt_status = mqtt_subscriber.status
    latest_naive = latest_ts.replace(tzinfo=None) if latest_ts and latest_ts.tzinfo else latest_ts
    sensor_data_recent = bool(
        latest_naive and (datetime.utcnow() - latest_naive).total_seconds() <= 15
    )
    sensor_data_status = (
        "recent" if sensor_data_recent
        else "stale" if latest_ts
        else "no_data"
    )

    return DashboardStats(
        total_readings     = total_readings,
        total_alerts       = total_alerts,
        active_devices     = active_devices,
        latest_received_at = latest_ts,
        latest_reading     = latest_reading,
        mqtt_connected     = mqtt_status["connected"],
        mqtt_last_received_at = mqtt_status["last_received_at"],
        sensor_data_recent = sensor_data_recent,
        sensor_data_status = sensor_data_status,
    )


@router.get("/chart-data", response_model=ChartDataResponse)
async def get_chart_data(
    limit: int = 50,
    device_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Return recent readings in chronological order for charts.
    Empty list if no readings stored yet.
    """
    q = select(RawReadingDB)
    if device_id:
        q = q.where(RawReadingDB.device_id == device_id)

    rows = (await db.execute(
        q.order_by(RawReadingDB.received_at.desc(), RawReadingDB.id.desc()).limit(limit)
    )).scalars().all()

    rows = list(reversed(rows))   # chronological order for charts

    points = [
        ChartDataPoint(
            timestamp     = r.received_at,
            temperature_c = r.temperature_c,
            humidity_pct  = r.humidity_pct,
            mq2_raw       = r.mq2_raw,
            mq7_raw       = r.mq7_raw,    # MQ-7 CO sensor
            mq135_raw     = r.mq135_raw,
        )
        for r in rows
    ]

    return ChartDataResponse(data_points=points, total=len(points))
