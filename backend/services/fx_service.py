"""
services/fx_service.py
-----------------------
Live USD/LKR (and USD/INR) exchange rates for dual-currency display.

WHY FRANKFURTER WAS REMOVED
The previous primary was Frankfurter, which serves the European Central
Bank's reference rates. The ECB does not publish LKR at all, so
`rates["LKR"]` raised KeyError on every single call, `_fetch_live()`
returned None, and the service silently served its hard-coded constant
forever. The live path had never once worked. Frankfurter is not kept as
a secondary either: a source that cannot answer the main question is not
a fallback, it is a guaranteed miss. If the ECB ever adds LKR it can
come back.

PRIMARY: ExchangeRate-API open access
    GET https://open.er-api.com/v6/latest/USD
    -> {"result": "success", "time_last_update_utc": "...",
        "rates": {"LKR": 302.5, "INR": 88.1, ...}}
No key required. `result` must be "success"; a body saying anything else
is treated as a failure even on HTTP 200.

The rate's own date comes from time_last_update_utc, not from when we
happened to call. Those differ by up to a day, and showing the fetch time
as the rate date would overstate how fresh the number is -- which is the
whole point of putting a date on a council-facing dashboard.

ORDER OF PREFERENCE
  1. A successful fetch from the last CACHE_TTL_SECONDS (6 hours).
  2. A fresh fetch -- but never more than once an hour, so a failing or
     rate-limited upstream is not hammered once per request.
  3. The last rate that ever succeeded, persisted to data/fx_last.json so
     it survives a restart. Reported as "cached", however old it is, with
     its real rate_date attached.
  4. Only then the hard-coded constant, reported as "fallback".

A rate outside SANE_MIN..SANE_MAX LKR/USD is rejected at the door. A
decimal-point error upstream would otherwise be applied to every price on
the dashboard, and a wrong number that looks plausible is worse than a
stale one that is honest about its age.
"""

from __future__ import annotations
import json
import logging
import os
import time
from datetime import datetime, timezone

import requests

logger = logging.getLogger("ecovision.fx")

BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
STATE_PATH = os.path.join(BACKEND_DIR, "data", "fx_last.json")

API_URL = "https://open.er-api.com/v6/latest/USD"
ATTRIBUTION_NAME = "Exchange Rate API"
ATTRIBUTION_URL = "https://www.exchangerate-api.com"

CACHE_TTL_SECONDS = int(os.environ.get("FX_CACHE_TTL_SECONDS", 6 * 60 * 60))      # serve without calling
MIN_SECONDS_BETWEEN_CALLS = int(os.environ.get("FX_MIN_CALL_INTERVAL", 60 * 60))  # hard rate limit
REQUEST_TIMEOUT_SECONDS = 5

# A USD/LKR outside this band is a data error, not a devaluation.
SANE_MIN, SANE_MAX = 250.0, 450.0

# Last verified against Xe/OFX/CBSL-referenced aggregators on 22 Aug 2026.
FALLBACK_USD_LKR = 329.50
FALLBACK_USD_INR = 95.70
FALLBACK_AS_OF = "2026-08-22T00:00:00Z"

SOURCE_API = "exchangerate-api"
SOURCE_CACHED = "cached"
SOURCE_FALLBACK = "fallback"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_state() -> dict | None:
    try:
        with open(STATE_PATH, "r") as f:
            data = json.load(f)
        if "usd_lkr" in data or "last_attempt_epoch" in data:
            return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return None


def _write_state(data: dict) -> None:
    try:
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        tmp = STATE_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, STATE_PATH)   # atomic: a crash cannot leave half a rate on disk
    except OSError as exc:            # pragma: no cover - persistence is best effort
        logger.warning("Could not persist the FX rate to %s: %s", STATE_PATH, exc)


def is_sane(rate) -> bool:
    try:
        r = float(rate)
    except (TypeError, ValueError):
        return False
    return r == r and SANE_MIN <= r <= SANE_MAX     # r == r rejects NaN


def _parse_rate_date(raw) -> str:
    """
    time_last_update_utc looks like 'Thu, 09 Oct 2026 00:02:31 +0000'.
    Normalised to ISO so the frontend need not parse RFC 1123; if the shape
    ever changes the raw string is kept rather than silently dropped.
    """
    if not raw:
        return _now_iso()
    try:
        parsed = datetime.strptime(raw, "%a, %d %b %Y %H:%M:%S %z")
    except (ValueError, TypeError):
        return str(raw)
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _fetch_live() -> dict | None:
    """One call to ExchangeRate-API. Returns None on any failure."""
    try:
        resp = requests.get(API_URL, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        logger.warning("FX fetch failed (network): %s", exc)
        return None

    if resp.status_code == 429:
        logger.warning("FX fetch rate-limited (HTTP 429); keeping the last known rate.")
        return None
    if resp.status_code != 200:
        logger.warning("FX fetch failed (HTTP %s); keeping the last known rate.", resp.status_code)
        return None

    try:
        payload = resp.json()
    except ValueError as exc:
        logger.warning("FX response was not JSON: %s", exc)
        return None

    if payload.get("result") != "success":
        logger.warning("FX response reported result=%r (%s)",
                       payload.get("result"), str(payload.get("error-type"))[:100])
        return None

    try:
        usd_lkr = float(payload["rates"]["LKR"])
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("FX response had no usable LKR rate: %s", exc)
        return None

    if not is_sane(usd_lkr):
        logger.warning("FX rate %s USD/LKR is outside the sane %s-%s band; rejected.",
                       usd_lkr, SANE_MIN, SANE_MAX)
        return None

    try:
        usd_inr = float(payload["rates"]["INR"])
    except (KeyError, TypeError, ValueError):
        usd_inr = FALLBACK_USD_INR      # LKR is what this dashboard runs on

    return {
        "usd_lkr": usd_lkr,
        "usd_inr": usd_inr,
        "rate_date": _parse_rate_date(payload.get("time_last_update_utc")),
        "fetched_at": _now_iso(),
    }


def _as_response(data: dict, source: str) -> dict:
    """
    `rate`, `rate_date` and `fetched_at` are the fields this service is
    specified in. `usd_lkr`, `usd_inr` and `as_of` are the older names,
    kept so schemas.FXInfo and to_lkr() keep working unchanged.
    """
    return {
        "usd_lkr": float(data["usd_lkr"]),
        "usd_inr": float(data.get("usd_inr") or FALLBACK_USD_INR),
        "as_of": data["rate_date"],
        "source": source,
        "rate": float(data["usd_lkr"]),
        "rate_date": data["rate_date"],
        "fetched_at": data.get("fetched_at"),
        "provider": ATTRIBUTION_NAME,
        "provider_url": ATTRIBUTION_URL,
    }


def get_fx_rates() -> dict:
    """USD/LKR for display. See the module docstring for the order of preference."""
    state = _read_state()
    now = time.time()

    # 1. a recent success -- serve it without calling anybody
    if state and state.get("usd_lkr") is not None:
        age = now - float(state.get("fetched_at_epoch") or 0)
        if age < CACHE_TTL_SECONDS and is_sane(state["usd_lkr"]):
            return _as_response(state, SOURCE_CACHED)

    # 2. otherwise consider calling, at most once an hour
    last_attempt = float((state or {}).get("last_attempt_epoch") or 0)
    if (now - last_attempt) >= MIN_SECONDS_BETWEEN_CALLS:
        record = dict(state or {})
        record["last_attempt_epoch"] = now
        fresh = _fetch_live()
        if fresh:
            record.update(fresh)
            record["fetched_at_epoch"] = now
            _write_state(record)
            return _as_response(record, SOURCE_API)
        _write_state(record)      # remember the attempt even though it failed
        state = record

    # 3. the last rate that ever worked, however old
    if state and state.get("usd_lkr") is not None and is_sane(state["usd_lkr"]):
        return _as_response(state, SOURCE_CACHED)

    # 4. the constant
    return _as_response(
        {"usd_lkr": FALLBACK_USD_LKR, "usd_inr": FALLBACK_USD_INR,
         "rate_date": FALLBACK_AS_OF, "fetched_at": None},
        SOURCE_FALLBACK)


def to_lkr(usd_amount: float, fx: dict) -> float:
    return round(usd_amount * fx["usd_lkr"], 2)
