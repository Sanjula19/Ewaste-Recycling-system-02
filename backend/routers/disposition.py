"""
routers/disposition.py
-------------------------
Prefix "/api/disposition" is applied in main.py, matching your existing
main.py pattern exactly.
"""

from fastapi import APIRouter, HTTPException

from schemas import DispositionRequest, DispositionResponse
from services.disposition_service import calculate_disposition
from services import facility_service, manifest_service

router = APIRouter()


@router.get("/local-authorities")
def list_local_authorities() -> dict:
    """
    The origins a batch can be dispatched from, for the dashboard's
    selector. Served from backend/data/local_authorities.json so the
    dashboard cannot drift from the register the routing actually uses --
    the two used to hold separate copies of the same coordinates.
    """
    return {
        "default": facility_service.default_local_authority_name(),
        "local_authorities": [
            {
                "name": la.name,
                "district": la.district,
                "province": la.province,
                "latitude": la.latitude,
                "longitude": la.longitude,
                "coordinates_source": la.coordinates_source,
            }
            for la in facility_service.load_local_authorities()
        ],
    }


@router.get("/facilities")
def list_facilities() -> dict:
    """
    The whole facility register, including entries that cannot be routed
    to. `routable` is false where coordinates are missing, so a caller can
    show the plant and say why it is unavailable instead of omitting it.
    """
    return {
        "facilities": [
            {
                "id": f.id, "name": f.name, "operator": f.operator, "town": f.town,
                "district": f.district, "technology": f.technology,
                "accepts": list(f.accepts), "status": f.status,
                "unconfirmed": not f.is_operational,
                "latitude": f.latitude, "longitude": f.longitude,
                "routable": f.has_coordinates,
                "exports_electricity": f.exports_electricity,
                "tariff_lkr_per_kwh": f.tariff_lkr_per_kwh,
                "source_url": f.source_url,
                "coordinates_source": f.coordinates_source,
                "last_verified": f.last_verified,
            }
            for f in facility_service.load_facilities()
        ]
    }


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
        # exc.args[0], not str(exc): str() on a KeyError re-quotes the
        # message, so a rejection reads as "'Contaminated glass is ...'"
        # with stray quotes around it in the client's error banner.
        detail = exc.args[0] if exc.args else "Unsupported waste_type"
        raise HTTPException(status_code=400, detail=detail)

    manifest_service.log_disposition(response)
    return response
