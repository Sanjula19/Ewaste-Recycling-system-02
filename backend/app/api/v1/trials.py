"""
Trials API -- dataset collection trial management.
Start and stop named experiment trials (e.g. CLEAN_01, LPG_01).
Readings between started_at and ended_at belong to the trial.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.db.models import TrialDB

router = APIRouter()

VALID_CONDITIONS = {"CLEAN", "LPG"}


class TrialStartRequest(BaseModel):
    trial_id:  str          # e.g. "CLEAN_01"
    condition: str          # e.g. "CLEAN" or "LPG"
    notes:     Optional[str] = None


class TrialResponse(BaseModel):
    trial_id:   str
    condition:  str
    started_at: datetime
    ended_at:   Optional[datetime]
    notes:      Optional[str]
    running:    bool


def _to_resp(t: TrialDB) -> TrialResponse:
    return TrialResponse(
        trial_id   = t.trial_id,
        condition  = t.condition,
        started_at = t.started_at,
        ended_at   = t.ended_at,
        notes      = t.notes,
        running    = t.ended_at is None,
    )


@router.post("/start", response_model=TrialResponse, status_code=201)
async def start_trial(req: TrialStartRequest, db: AsyncSession = Depends(get_db)):
    """Start a new experiment trial."""
    condition = req.condition.upper().strip()
    if condition not in VALID_CONDITIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid condition '{condition}'. Must be one of: {sorted(VALID_CONDITIONS)}"
        )

    # Check trial_id not already used
    existing = (await db.execute(
        select(TrialDB).where(TrialDB.trial_id == req.trial_id)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Trial '{req.trial_id}' already exists."
        )

    trial = TrialDB(
        trial_id   = req.trial_id.strip(),
        condition  = condition,
        started_at = datetime.now(timezone.utc),
        ended_at   = None,
        notes      = req.notes,
    )
    db.add(trial)
    await db.commit()
    return _to_resp(trial)


@router.post("/stop/{trial_id}", response_model=TrialResponse)
async def stop_trial(trial_id: str, db: AsyncSession = Depends(get_db)):
    """Stop a running trial."""
    trial = (await db.execute(
        select(TrialDB).where(TrialDB.trial_id == trial_id)
    )).scalar_one_or_none()

    if not trial:
        raise HTTPException(status_code=404, detail=f"Trial '{trial_id}' not found.")
    if trial.ended_at is not None:
        raise HTTPException(status_code=409, detail=f"Trial '{trial_id}' already stopped.")

    trial.ended_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(trial)
    return _to_resp(trial)


@router.get("", response_model=list[TrialResponse])
async def list_trials(db: AsyncSession = Depends(get_db)):
    """List all trials, newest first."""
    rows = (await db.execute(
        select(TrialDB).order_by(TrialDB.started_at.desc())
    )).scalars().all()
    return [_to_resp(r) for r in rows]


@router.get("/{trial_id}", response_model=TrialResponse)
async def get_trial(trial_id: str, db: AsyncSession = Depends(get_db)):
    """Get one trial by ID."""
    trial = (await db.execute(
        select(TrialDB).where(TrialDB.trial_id == trial_id)
    )).scalar_one_or_none()
    if not trial:
        raise HTTPException(status_code=404, detail=f"Trial '{trial_id}' not found.")
    return _to_resp(trial)