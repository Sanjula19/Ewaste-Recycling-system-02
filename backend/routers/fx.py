"""
routers/fx.py
----------------
Prefix "/api/fx" is applied in main.py.

Exists so the exchange rate can be inspected on its own, without reading
it out of a forecast response -- useful when checking whether the live
provider is actually being reached, which is exactly the failure the
previous Frankfurter-based service hid.
"""

from fastapi import APIRouter

from schemas import FXInfo
from services import fx_service

router = APIRouter()


@router.get("/rates", response_model=FXInfo)
def get_rates() -> FXInfo:
    """Current USD/LKR, its provider, the rate's own date and when it was fetched."""
    return FXInfo(**fx_service.get_fx_rates())
