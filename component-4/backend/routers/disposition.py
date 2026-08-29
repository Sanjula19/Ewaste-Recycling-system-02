"""
routers/disposition.py
-------------------------
Prefix "/api/disposition" is applied in main.py, matching your existing
main.py pattern exactly.
"""

from fastapi import APIRouter, HTTPException

from schemas import DispositionRequest, DispositionResponse
from services.disposition_service import calculate_disposition
from services import manifest_service

router = APIRouter()


@router.post("/", response_model=DispositionResponse)
def get_disposition(request: DispositionRequest) -> DispositionResponse:
    """
    Energy recovery (E_rec = M x LHV x eta), nearest waste-to-energy /
    pyrolysis facility, and indicative sale value for one batch of
    residual (non-recyclable) waste. Recyclable metals are still accepted
    here and returned with is_recyclable=True so a caller that doesn't
    know in advance which endpoint a waste_type belongs to gets a useful
    answer either way -- but should really be routed to /api/forecast.
    """
    try:
        response = calculate_disposition(request)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    manifest_service.log_disposition(response)
    return response
