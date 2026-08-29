"""
services/market_service.py
-----------------------------
Dashboard "Market Overview" -- a live-price snapshot across all six
in-scope metals (aluminium, copper, nickel, zinc, lead, steel), for
operators who want a glance at the whole market rather than valuing one
batch at a time. Gold and silver are intentionally excluded, matching the
documented scope of the rest of this component (see materials_db.py /
data_loader.py) -- reopening that scope decision was explicitly declined.

Accuracy note (read before citing "live" anywhere): the historical CSVs
this component ships with are the ARIMA *training* set, not a live tick
feed -- their last row is roughly a year or more old for most metals (see
data_loader.py). There is no free, key-less price API that reliably covers
all six of these specific LME base-metal + steel-scrap series the way
services/fx_service.py's Frankfurter call covers currency, so this module
does NOT attempt to fabricate a "current" number by extrapolating a
90-day-horizon model hundreds of days past its training data -- that would
be *less* accurate, not more, the further out it's pushed. Instead:

  1. If services/influx_client.py has a live tick for a metal (i.e. the
     .env-configured InfluxDB is actually running and seeded --
     scripts/seed_influxdb.py), that's used and marked price_source="live".
  2. Otherwise, the last real recorded historical price is used, marked
     price_source="historical", with `data_as_of` carrying the exact date
     so the dashboard can show it honestly (e.g. "as of 29 Aug 2024")
     instead of implying it's today's price.

Day-over-day change and the SELL/HOLD verdict reuse the exact same
forecast_service.build_price_path() / generate_recommendation() logic that
/api/forecast/ already uses and backtests -- no separate/divergent logic.
"""

from __future__ import annotations
import asyncio
import logging
import time
from datetime import datetime, timezone

from data_loader import SUPPORTED_METALS
from services import forecast_service, fx_service
from schemas import MarketOverviewItem, MarketOverviewResponse

logger = logging.getLogger("ecovision.market")

# Computing this for real -- pretrained ARIMA+LSTM selection and backtest
# across all six metals -- takes on the order of a minute (dominated by
# TensorFlow/Keras model load + inference), far too slow to do inline on
# every dashboard load. main.py's lifespan handler starts refresh_loop()
# as a background task at server startup so this cache is normally always
# warm; get_overview() below only falls back to a slow synchronous compute
# if called before that first background pass has completed.
_REFRESH_INTERVAL_SECONDS = 5 * 60
_cache: MarketOverviewResponse | None = None
_cache_at: float = 0.0


def _build_item(metal: str, fx: dict) -> MarketOverviewItem:
    path, mape, rmse, history, current_price, is_live = forecast_service.build_price_path(metal)
    last_date = history.index[-1]

    prev_price = float(history.iloc[-2]) if len(history) > 1 else current_price
    day_change_pct = ((current_price - prev_price) / prev_price * 100) if prev_price else 0.0

    rec = forecast_service.generate_recommendation(current_price, path, last_date)

    return MarketOverviewItem(
        metal=metal,
        current_price=round(current_price, 4),
        current_price_lkr=fx_service.to_lkr(current_price, fx),
        day_change_pct=round(day_change_pct, 2),
        recommendation=rec["recommendation"],
        data_as_of=last_date.strftime("%Y-%m-%dT00:00:00Z"),
        price_source="live" if is_live else "historical",
        model_used=path.model_used,
        mape=mape,
    )


def _compute_overview() -> MarketOverviewResponse:
    fx = fx_service.get_fx_rates()
    items = [_build_item(metal, fx) for metal in SUPPORTED_METALS]
    return MarketOverviewResponse(
        items=items,
        fx=fx,
        generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )


def get_overview() -> MarketOverviewResponse:
    """Serves the warm cache; only computes synchronously (slow) if the
    background refresh loop hasn't populated it yet."""
    global _cache, _cache_at
    if _cache is None:
        _cache = _compute_overview()
        _cache_at = time.time()
    return _cache


async def refresh_loop() -> None:
    """Background task (started from main.py's lifespan) that keeps the
    Market Overview cache warm by recomputing it every
    _REFRESH_INTERVAL_SECONDS in a worker thread, so it never blocks the
    event loop and requests never wait on it."""
    while True:
        try:
            response = await asyncio.to_thread(_compute_overview)
            global _cache, _cache_at
            _cache, _cache_at = response, time.time()
        except Exception:
            logger.exception("Market overview background refresh failed -- will retry next cycle.")
        await asyncio.sleep(_REFRESH_INTERVAL_SECONDS)
