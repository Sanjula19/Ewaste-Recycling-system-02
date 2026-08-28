"""
Alerts API -- WHO threshold violation alerts.
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.db.database import get_db
from app.db.models import AlertDB
from app.models.alert import AlertResponse, AlertList, RiskLevel

router = APIRouter()


def _db_to_alert_response(a: AlertDB) -> AlertResponse:
    return AlertResponse(
        alert_id=a.alert_id,
        raw_reading_id=a.raw_reading_id,
        timestamp=a.timestamp,
        device_id=a.device_id,
        risk_level=RiskLevel(a.risk_level),
        gas_name=a.gas_name,
        ppm_value=a.ppm_value,
        who_limit=a.who_limit,
        measured_value=a.ppm_value,
        threshold=a.who_limit,
        unit=a.unit,
        exceeded_by_pct=a.exceeded_by_pct,
        health_risks=a.health_risks or [],
        safety_actions=a.safety_actions or [],
        acknowledged=a.acknowledged,
        acknowledged_at=a.acknowledged_at,
    )


@router.get("", response_model=AlertList)
async def list_alerts(
    page: int = 1,
    page_size: int = 20,
    risk_level: Optional[RiskLevel] = None,
    acknowledged: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    """Return paginated list of alerts, optionally filtered by risk level or acknowledgement."""
    query = select(AlertDB)
    count_query = select(func.count(AlertDB.id))

    if risk_level:
        query = query.where(AlertDB.risk_level == risk_level.value)
        count_query = count_query.where(AlertDB.risk_level == risk_level.value)
    if acknowledged is not None:
        query = query.where(AlertDB.acknowledged == acknowledged)
        count_query = count_query.where(AlertDB.acknowledged == acknowledged)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one() or 0

    query = query.order_by(AlertDB.timestamp.desc(), AlertDB.id.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    alerts = result.scalars().all()

    return AlertList(
        alerts=[_db_to_alert_response(a) for a in alerts],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    """Return a single alert by its UUID."""
    query = select(AlertDB).where(AlertDB.alert_id == alert_id)
    result = await db.execute(query)
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _db_to_alert_response(a)


@router.put("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    """Acknowledge an alert (mark as reviewed)."""
    query = select(AlertDB).where(AlertDB.alert_id == alert_id)
    result = await db.execute(query)
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")

    a.acknowledged = True
    a.acknowledged_at = datetime.utcnow()
    await db.commit()
    await db.refresh(a)
    return _db_to_alert_response(a)
