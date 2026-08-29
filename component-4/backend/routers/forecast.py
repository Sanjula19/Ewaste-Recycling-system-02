"""
routers/forecast.py
---------------------
Prefix "/api/forecast" is applied in main.py via
app.include_router(forecast.router, prefix="/api/forecast", tags=[...]),
matching your existing main.py exactly -- this file defines a bare router.
"""

from fastapi import APIRouter, HTTPException

from schemas import ForecastRequest, ForecastResponse
from services.forecast_service import calculate_forecast
from services import manifest_service

router = APIRouter()


@router.post("/", response_model=ForecastResponse)
def get_forecast(request: ForecastRequest) -> ForecastResponse:
    """
    90-day ARIMA price forecast + Sell/Hold recommendation (with the
    crush-and-compress HOLD action) for one of the metals this component
    covers: aluminium, nickel, steel, lead, zinc, copper.
    """
    try:
        response = calculate_forecast(request)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    manifest_service.log_forecast(response)
    return response


@router.get("/supported-metals")
def supported_metals() -> dict:
    from data_loader import SUPPORTED_METALS

    return {"metals": SUPPORTED_METALS}
