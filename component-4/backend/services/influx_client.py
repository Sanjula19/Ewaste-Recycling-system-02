"""
services/influx_client.py
---------------------------
Thin wrapper around the InfluxDB client, matching the .env you already
have:

    INFLUXDB_URL=http://localhost:8086
    INFLUXDB_TOKEN=your_influxdb_token_here
    INFLUXDB_ORG=ewaste_org
    INFLUXDB_BUCKET=metal_prices

Intent: InfluxDB holds the *live* daily price feed going forward (one
point per metal per day, written by a scheduled job you run -- see
scripts/seed_influxdb.py for a one-off historical backfill and a template
for that daily job). The 10-year CSVs stay the ARIMA *training* set
(data_loader.py); Influx is for "what's the price right now".

Everything here degrades gracefully:
  - If the `influxdb-client` package isn't installed, or the server at
    INFLUXDB_URL isn't reachable, every function returns None (or an empty
    Series) instead of raising. Callers (forecast_service.py) fall back to
    the last point in the historical CSV in that case, so the API still
    works end-to-end in a dev environment with no Influx instance running.
  - A short in-process log line is emitted on first failure so it's
    obvious in the console why you're seeing fallback data, without
    spamming the log on every request.
"""

from __future__ import annotations
import os
import logging
from datetime import datetime, timezone

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("ecovision.influx")

INFLUXDB_URL = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.environ.get("INFLUXDB_TOKEN", "")
INFLUXDB_ORG = os.environ.get("INFLUXDB_ORG", "ewaste_org")
INFLUXDB_BUCKET = os.environ.get("INFLUXDB_BUCKET", "metal_prices")
MEASUREMENT = "price"

_warned_once = False

# --- Circuit breaker ------------------------------------------------
# When nothing is listening at INFLUXDB_URL, the client still spends
# ~4 seconds per call retrying with backoff before giving up. Two calls
# per forecast meant ~8s of pure dead time on every request -- enough to
# blow past the ESP32's HTTP timeout, for a database that was never
# started.
#
# So after a failure we stop trying for a while and go straight to the
# CSV fallback. If Influx is later started, the breaker reopens on its
# own once the cooldown lapses -- no restart needed.
import time as _time

_BREAKER_COOLDOWN_SECONDS = 60.0
_breaker_open_until = 0.0


def _breaker_is_open() -> bool:
    return _time.time() < _breaker_open_until


def _trip_breaker() -> None:
    global _breaker_open_until
    _breaker_open_until = _time.time() + _BREAKER_COOLDOWN_SECONDS


def _client():
    global _warned_once

    if _breaker_is_open():
        return None

    try:
        from influxdb_client import InfluxDBClient  # local import: optional dependency
    except ImportError:
        if not _warned_once:
            logger.warning(
                "influxdb-client not installed -- falling back to CSV data for all "
                "price lookups. Run `pip install influxdb-client` to enable live storage."
            )
            _warned_once = True
        return None

    try:
        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG, timeout=3_000)
        return client
    except Exception as exc:  # pragma: no cover - defensive
        if not _warned_once:
            logger.warning("Could not connect to InfluxDB at %s (%s) -- using CSV fallback.", INFLUXDB_URL, exc)
            _warned_once = True
        _trip_breaker()
        return None


def write_price_point(metal: str, price_usd_kg: float, when: datetime | None = None) -> bool:
    """Writes one price point. Returns True on success, False if Influx is unavailable."""
    client = _client()
    if client is None:
        return False
    try:
        from influxdb_client import Point
        from influxdb_client.client.write_api import SYNCHRONOUS

        point = (
            Point(MEASUREMENT)
            .tag("metal", metal.lower())
            .field("price_usd_kg", float(price_usd_kg))
            .time(when or datetime.now(timezone.utc))
        )
        write_api = client.write_api(write_options=SYNCHRONOUS)
        write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
        return True
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("InfluxDB write failed for %s: %s", metal, exc)
        return False
    finally:
        client.close()


def query_latest_price(metal: str) -> float | None:
    """Latest known price (USD/kg) for `metal` from InfluxDB, or None if unavailable."""
    client = _client()
    if client is None:
        return None
    try:
        query_api = client.query_api()
        flux = f'''
            from(bucket: "{INFLUXDB_BUCKET}")
              |> range(start: -30d)
              |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")
              |> filter(fn: (r) => r.metal == "{metal.lower()}")
              |> filter(fn: (r) => r._field == "price_usd_kg")
              |> last()
        '''
        tables = query_api.query(flux, org=INFLUXDB_ORG)
        for table in tables:
            for record in table.records:
                return float(record.get_value())
        return None
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("InfluxDB query failed for %s: %s", metal, exc)
        _trip_breaker()
        return None
    finally:
        client.close()


def query_history(metal: str, days: int = 3650) -> pd.Series:
    """Historical USD/kg series from InfluxDB, or an empty Series if unavailable."""
    client = _client()
    if client is None:
        return pd.Series(dtype=float)
    try:
        query_api = client.query_api()
        flux = f'''
            from(bucket: "{INFLUXDB_BUCKET}")
              |> range(start: -{days}d)
              |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")
              |> filter(fn: (r) => r.metal == "{metal.lower()}")
              |> filter(fn: (r) => r._field == "price_usd_kg")
              |> sort(columns: ["_time"])
        '''
        tables = query_api.query(flux, org=INFLUXDB_ORG)
        rows = [(r.get_time(), r.get_value()) for table in tables for r in table.records]
        if not rows:
            return pd.Series(dtype=float)
        idx, vals = zip(*rows)
        return pd.Series(vals, index=pd.to_datetime(idx), name="price_usd_kg")
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("InfluxDB history query failed for %s: %s", metal, exc)
        _trip_breaker()
        return pd.Series(dtype=float)
    finally:
        client.close()
