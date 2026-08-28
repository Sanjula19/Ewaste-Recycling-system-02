"""
Readings API -- raw sensor readings.
Data arrives via MQTT (not REST POST).
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.models import RawReadingDB, LabeledReadingDB
from app.models.gas_reading import RawReadingResponse, RawReadingList, LabelRequest

router = APIRouter()


def _to_resp(r: RawReadingDB) -> RawReadingResponse:
    """Convert DB row to Pydantic model. Relationship must already be loaded."""
    return RawReadingResponse(
        id            = r.id,
        reading_id    = r.reading_id,
        device_id     = r.device_id,
        received_at   = r.received_at,
        temperature_c = r.temperature_c,
        humidity_pct  = r.humidity_pct,
        mq2_raw       = r.mq2_raw,
        mq135_raw     = r.mq135_raw,
        mq7_raw       = r.mq7_raw,       # always None (sensor not installed)
        mq136_raw     = r.mq136_raw,     # always None (sensor removed)
        source        = r.source,
        label         = r.label.gas_label  if r.label else None,
        label_note    = r.label.label_note if r.label else None,
    )


@router.get("/latest", response_model=RawReadingResponse)
async def get_latest_reading(db: AsyncSession = Depends(get_db)):
    """Return the most recent real ESP32 reading, 404 if none yet."""
    result = await db.execute(
        select(RawReadingDB)
        .options(selectinload(RawReadingDB.label))   # eager load to avoid lazy-load error
        .order_by(RawReadingDB.received_at.desc(), RawReadingDB.id.desc())
        .limit(1)
    )
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(
            status_code=404,
            detail="No readings yet. Ensure ESP32 is powered on and publishing to ewaste/gas/readings."
        )
    return _to_resp(r)


@router.get("", response_model=RawReadingList)
async def list_readings(
    page: int = 1,
    page_size: int = 20,
    device_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Paginated list of raw readings, newest first."""
    q  = select(RawReadingDB).options(selectinload(RawReadingDB.label))
    cq = select(func.count()).select_from(RawReadingDB)

    if device_id:
        q  = q.where(RawReadingDB.device_id == device_id)
        cq = cq.where(RawReadingDB.device_id == device_id)

    total = (await db.execute(cq)).scalar_one() or 0
    rows  = (await db.execute(
        q.order_by(RawReadingDB.received_at.desc(), RawReadingDB.id.desc())
         .offset((page - 1) * page_size)
         .limit(page_size)
    )).scalars().all()

    return RawReadingList(
        readings  = [_to_resp(r) for r in rows],
        total     = total,
        page      = page,
        page_size = page_size,
    )


@router.get("/{reading_id}", response_model=RawReadingResponse)
async def get_reading(reading_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RawReadingDB)
        .options(selectinload(RawReadingDB.label))
        .where(RawReadingDB.reading_id == reading_id)
    )
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Reading not found")
    return _to_resp(r)


@router.post("/label", status_code=201)
async def label_reading(req: LabelRequest, db: AsyncSession = Depends(get_db)):
    """Assign a researcher ground-truth gas label to a raw reading."""
    VALID = {"LPG", "CO", "BENZENE", "AMMONIA", "H2S", "CLEAN"}
    label_upper = req.gas_label.upper()
    if label_upper not in VALID:
        raise HTTPException(422, f"Invalid gas_label. Must be one of: {sorted(VALID)}")

    raw = (await db.execute(
        select(RawReadingDB).where(RawReadingDB.reading_id == req.reading_id)
    )).scalar_one_or_none()
    if not raw:
        raise HTTPException(404, f"Reading '{req.reading_id}' not found")

    existing = (await db.execute(
        select(LabeledReadingDB).where(LabeledReadingDB.raw_reading_id == raw.id)
    )).scalar_one_or_none()

    if existing:
        existing.gas_label  = label_upper
        existing.labeled_by = req.labeled_by
        existing.label_note = req.label_note
        await db.commit()
        return {"message": "Label updated", "reading_id": req.reading_id, "gas_label": label_upper}

    db.add(LabeledReadingDB(
        raw_reading_id = raw.id,
        gas_label      = label_upper,
        labeled_by     = req.labeled_by,
        label_note     = req.label_note,
    ))
    await db.commit()
    return {"message": "Label created", "reading_id": req.reading_id, "gas_label": label_upper}
