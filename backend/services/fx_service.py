"""
services/fx_service.py
-----------------------
Live USD/LKR and USD/INR exchange rates for dual-currency display.

Design:
  1. Try a live call to the Frankfurter API (https://frankfurter.dev) --
     free, no API key, backed by the European Central Bank's daily
     reference rates. One call returns both LKR and INR against USD.
  2. Cache the result to a small local JSON file for CACHE_TTL_SECONDS
     (default 6 hours) so every dashboard request doesn't re-hit the API.
  3. If the live call fails (offline dev machine, firewall, API down),
     fall back to a hardcoded constant -- clearly dated below -- and mark
     the response `source: "fallback"` so the frontend can show a small
     "rate may be stale" indicator instead of silently presenting a
     possibly-old number as live.

For a municipal-council-facing dashboard, "accurate" mostly means
*honest about its own freshness* -- hence the explicit `source` and
`as_of` fields on every FXInfo returned, rather than just a bare number.

NOTE: the Central Bank of Sri Lanka publishes its own official indicative
USD/LKR spot rate (cbsl.gov.lk/en/rates-and-indicators/exchange-rates),
which is the more authoritative source for a Sri Lankan government-facing
deployment. It doesn't have a simple public JSON endpoint the way
Frankfurter does, so it isn't wired in here, but swapping the primary
source to a scraped/official CBSL feed is a natural next step before
production rollout -- see README.
"""

from __future__ import annotations
import json
import os
import time
from datetime import datetime, timezone

import requests

CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".fx_cache.json")
CACHE_TTL_SECONDS = int(os.environ.get("FX_CACHE_TTL_SECONDS", 6 * 60 * 60))  # 6 hours
REQUEST_TIMEOUT_SECONDS = 5

# Fallback constants -- last verified against Xe/OFX/CBSL-referenced
# aggregators on 22 Aug 2026. Update periodically even though the live
# path is primary; this is the number shown when the live+cache path
# both fail.
FALLBACK_USD_LKR = 329.50
FALLBACK_USD_INR = 95.70
FALLBACK_AS_OF = "2026-08-22T00:00:00Z"


def _read_cache() -> dict | None:
    try:
        with open(CACHE_PATH, "r") as f:
            data = json.load(f)
        if time.time() - data.get("_cached_at", 0) < CACHE_TTL_SECONDS:
            return data
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass
    return None


def _write_cache(usd_lkr: float, usd_inr: float, as_of: str) -> None:
    try:
        with open(CACHE_PATH, "w") as f:
            json.dump(
                {"usd_lkr": usd_lkr, "usd_inr": usd_inr, "as_of": as_of, "_cached_at": time.time()},
                f,
            )
    except OSError:
        pass  # caching is a nice-to-have, never fatal


def _fetch_live() -> tuple[float, float, str] | None:
    try:
        resp = requests.get(
            "https://api.frankfurter.dev/v1/latest",
            params={"from": "USD", "to": "LKR,INR"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        payload = resp.json()
        rates = payload["rates"]
        as_of = f"{payload['date']}T00:00:00Z"
        return float(rates["LKR"]), float(rates["INR"]), as_of
    except (requests.RequestException, KeyError, ValueError):
        return None


def get_fx_rates() -> dict:
    """
    Returns {"usd_lkr": float, "usd_inr": float, "as_of": iso_str,
    "source": "live" | "cached" | "fallback"} -- matches schemas.FXInfo.
    """
    cached = _read_cache()
    if cached:
        return {
            "usd_lkr": cached["usd_lkr"],
            "usd_inr": cached["usd_inr"],
            "as_of": cached["as_of"],
            "source": "cached",
        }

    live = _fetch_live()
    if live:
        usd_lkr, usd_inr, as_of = live
        _write_cache(usd_lkr, usd_inr, as_of)
        return {"usd_lkr": usd_lkr, "usd_inr": usd_inr, "as_of": as_of, "source": "live"}

    return {
        "usd_lkr": FALLBACK_USD_LKR,
        "usd_inr": FALLBACK_USD_INR,
        "as_of": FALLBACK_AS_OF,
        "source": "fallback",
    }


def to_lkr(usd_amount: float, fx: dict) -> float:
    return round(usd_amount * fx["usd_lkr"], 2)
