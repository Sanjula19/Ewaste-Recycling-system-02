"""
Export API -- download labeled dataset as CSV.
Joins raw_readings with trials by timestamp overlap.
Only exports readings that fall within a completed trial window.
"""
import csv
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.database import get_db
from app.db.models import RawReadingDB, TrialDB

router = APIRouter()


@router.get("/dataset.csv")
async def export_dataset(db: AsyncSession = Depends(get_db)):
    """
    Download all trial-labeled readings as CSV.
    Columns: trial_id, condition, timestamp,
             mq2_raw, mq135_raw, temperature, humidity
    """
    # Load all completed trials
    trials = (await db.execute(
        select(TrialDB)
        .where(TrialDB.ended_at.isnot(None))
        .order_by(TrialDB.started_at)
    )).scalars().all()

    # Load all readings
    readings = (await db.execute(
        select(RawReadingDB).order_by(RawReadingDB.received_at)
    )).scalars().all()

    # Match readings to trials by timestamp
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        "trial_id", "condition", "timestamp",
        "mq2_raw", "mq135_raw",
        "temperature", "humidity",
    ])

    row_count = 0
    for reading in readings:
        for trial in trials:
            # Check if reading falls inside this trial's window
            if trial.started_at <= reading.received_at <= trial.ended_at:
                writer.writerow([
                    trial.trial_id,
                    trial.condition,
                    reading.received_at.isoformat(),
                    reading.mq2_raw   if reading.mq2_raw   is not None else "",
                    reading.mq135_raw if reading.mq135_raw is not None else "",
                    reading.temperature_c if reading.temperature_c is not None else "",
                    reading.humidity_pct  if reading.humidity_pct  is not None else "",
                ])
                row_count += 1
                break  # one trial per reading

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ewaste_dataset.csv"},
    )


@router.get("/summary")
async def export_summary(db: AsyncSession = Depends(get_db)):
    """Quick summary of how many readings per trial."""
    trials = (await db.execute(
        select(TrialDB).order_by(TrialDB.started_at)
    )).scalars().all()

    readings = (await db.execute(
        select(RawReadingDB).order_by(RawReadingDB.received_at)
    )).scalars().all()

    summary = []
    for trial in trials:
        count = sum(
            1 for r in readings
            if trial.ended_at and trial.started_at <= r.received_at <= trial.ended_at
        )
        summary.append({
            "trial_id":   trial.trial_id,
            "condition":  trial.condition,
            "started_at": trial.started_at.isoformat(),
            "ended_at":   trial.ended_at.isoformat() if trial.ended_at else None,
            "running":    trial.ended_at is None,
            "reading_count": count,
        })
    return summary