"""
routers/manifest.py
----------------------
Prefix "/api/manifest" is applied in main.py.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from services import manifest_service

router = APIRouter()


@router.get("/summary")
def get_summary(cycle_id: int | None = None) -> dict:
    try:
        return manifest_service.summary(cycle_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/cycles")
def get_cycles() -> dict:
    return {"cycles": manifest_service.list_cycles()}


@router.get("/pdf")
def get_pdf(facility_name: str = "Urban Recycling Facility", cycle_id: int | None = None):
    try:
        pdf_bytes = manifest_service.generate_pdf(facility_name, cycle_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    filename = f"tonnage_manifest_cycle_{cycle_id}.pdf" if cycle_id is not None else "tonnage_manifest.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/reset")
def reset_ledger() -> dict:
    return manifest_service.reset()
