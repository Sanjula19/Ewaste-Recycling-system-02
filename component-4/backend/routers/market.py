"""
routers/market.py
--------------------
Prefix "/api/market" is applied in main.py.
"""

from fastapi import APIRouter

from schemas import MarketOverviewResponse
from services import market_service

router = APIRouter()


@router.get("/overview", response_model=MarketOverviewResponse)
def get_overview() -> MarketOverviewResponse:
    """
    Live-ish snapshot across all six in-scope metals for the Dashboard's
    Market Overview -- current price (USD + LKR), day-over-day change, and
    the same SELL NOW / HOLD verdict /api/forecast/ would give each metal.
    """
    return market_service.get_overview()
