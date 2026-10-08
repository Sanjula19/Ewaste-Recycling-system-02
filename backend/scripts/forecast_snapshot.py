"""
scripts/forecast_snapshot.py
----------------------------
Captures the full numeric output of the forecast service for every metal, so
a refactor can be proved not to have changed any result.

Used two ways:
  * as a script, to write a baseline file before a refactor --
        venv/Scripts/python.exe scripts/forecast_snapshot.py --out results_v2/forecast_baseline.json
  * from tests/test_forecast_equivalence.py, which recomputes the snapshot
    and compares it against that baseline to 1e-6.

FX is pinned to fixed rates here. services/fx_service.py fetches live ECB
rates with a 6-hour file cache and a dated fallback constant, so leaving it
live would make every *_lkr figure drift between runs and turn an
equivalence check into a flaky test of the network. The USD figures are the
model output; the LKR figures are that times one rate.

The `fx` block itself and the `at`/`generated_at`-style timestamps are
excluded for the same reason: they are not model results.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

PINNED_FX = {
    "usd_lkr": 300.0,
    "usd_inr": 90.0,
    "as_of": "2026-01-01T00:00:00Z",
    "source": "fallback",
}

# Scalar response fields that must not move. Deliberately explicit rather
# than "everything except a denylist", so a newly added field does not
# silently escape comparison.
SCALAR_FIELDS = [
    "metal", "current_price", "current_price_lkr", "recommendation",
    "recommendation_reason", "profit_if_sell", "profit_if_sell_lkr",
    "expected_peak_price", "expected_peak_price_lkr", "expected_peak_date",
    "mape", "rmse", "model_used", "weight_kg", "unit_price", "unit_price_lkr",
    "operator_action", "operator_action_note",
]


def _pin_fx():
    """Point fx_service at fixed rates for the duration of the process."""
    from services import fx_service
    fx_service.get_fx_rates = lambda: dict(PINNED_FX)


def snapshot_one(metal: str, weight_kg: float = 100.0) -> dict:
    from schemas import ForecastRequest
    from services.forecast_service import calculate_forecast

    resp = calculate_forecast(ForecastRequest(metal=metal, weight_kg=weight_kg))
    data = resp.model_dump()

    out = {k: data.get(k) for k in SCALAR_FIELDS}
    # Optional fields added after this baseline was taken are captured too,
    # but kept apart so an older baseline still compares cleanly.
    out["_added_fields"] = {
        k: data[k] for k in ("persistence_mape", "signal") if k in data
    }
    out["series"] = [
        {"date": p["date"], "price": p["price"],
         "lower_bound": p["lower_bound"], "upper_bound": p["upper_bound"],
         "price_lkr": p["price_lkr"]}
        for p in data["forecast_90d"]
    ]
    return out


def snapshot(metals: list[str], weight_kg: float = 100.0) -> dict:
    _pin_fx()
    from services import pretrained_models

    return {
        "model_dir": os.path.basename(pretrained_models.models_dir()),
        "pinned_fx": PINNED_FX,
        "weight_kg": weight_kg,
        "metals": {m: snapshot_one(m, weight_kg) for m in metals},
    }


def main():
    from data_loader import SUPPORTED_METALS

    ap = argparse.ArgumentParser()
    ap.add_argument("--metals", nargs="*", default=SUPPORTED_METALS)
    ap.add_argument("--out", default="results_v2/forecast_baseline.json")
    args = ap.parse_args()

    snap = snapshot(args.metals)
    path = args.out if os.path.isabs(args.out) else os.path.join(BACKEND_DIR, args.out)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(snap, f, indent=2, sort_keys=True)

    for m, row in snap["metals"].items():
        print(f"{m:10s} {row['model_used']:28s} MAPE {row['mape']:>6} "
              f"-> {row['recommendation']:9s} peak={row['expected_peak_price']}")
    print(f"\nWrote {path}")


if __name__ == "__main__":
    main()
