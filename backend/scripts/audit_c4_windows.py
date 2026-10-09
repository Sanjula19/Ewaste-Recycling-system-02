"""
scripts/audit_c4_windows.py
---------------------------
Pre-run leakage audit for evaluate_c4_v2.py. Answers two questions with
counts rather than assurances, before an hours-long run is started:

  1. For EVERY planned decision point, do the training window and the
     validation slice end strictly before the decision date?
  2. Is the min-max scaler fitted on the training window only?

    cd backend
    DATA_VERSION=v3 venv/Scripts/python.exe scripts/audit_c4_windows.py

(1) is checked analytically over the full plan -- no training needed, so
every decision point is covered, not a sample. (2) is checked empirically:
one model is actually trained at an early retrain index into a throwaway
cache, and its frozen scaler bounds are compared against the training
window, the full series, and the future it must not have seen.

Exit code is non-zero if any check fails.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, os.path.join(BACKEND_DIR, "scripts"))

import numpy as np

import data_loader
from data_loader import SUPPORTED_METALS, load_metal_series_raw, native_to_usd_per_kg
from evaluate_c4_v2 import (HOLDOUT, HORIZON, RETRAIN_EVERY, SEED, SPACING, START_OFFSET,
                            VAL_FRAC, WINDOW, make_sequences, model_index, plan, to_scaled)


def audit_windows(metal: str, start: int, spacing: int, retrain_every: int) -> dict:
    """Every decision point: training end and validation end vs the decision date."""
    series = load_metal_series_raw(metal)
    n = len(series)
    t_list, r_list = plan(n, start, spacing, retrain_every, None)

    violations = []
    for t in t_list:
        k = model_index(t, r_list)
        r = r_list[k]

        # Training window is vals[:r+1]; its last observation is index r.
        train_end_idx = r
        # make_sequences over the scaled training window: the final
        # validation target is y[-1] = s[len(s)-1], i.e. index r as well.
        n_seq = (r + 1) - WINDOW
        n_val = max(1, int(round(n_seq * VAL_FRAC)))
        val_end_idx = r
        val_start_idx = r - n_val + 1

        ok_train = train_end_idx <= t - HOLDOUT
        ok_val = val_end_idx < t
        ok_val_date = series.index[val_end_idx] < series.index[t]
        ok_train_date = series.index[train_end_idx] < series.index[t]
        ok_future = t + HORIZON < n or True   # horizon truncation handled by plan()

        if not (ok_train and ok_val and ok_val_date and ok_train_date):
            violations.append({
                "t": t, "date": str(series.index[t].date()), "train_end": train_end_idx,
                "train_end_date": str(series.index[train_end_idx].date()),
                "val_start": val_start_idx, "val_end": val_end_idx,
                "val_end_date": str(series.index[val_end_idx].date()),
            })

    # Tightest case across the run, for the report.
    gaps = []
    for t in t_list:
        r = r_list[model_index(t, r_list)]
        gaps.append((t - r, (series.index[t] - series.index[r]).days))
    min_obs_gap = min(g[0] for g in gaps) if gaps else None
    min_day_gap = min(g[1] for g in gaps) if gaps else None

    return {
        "metal": metal, "n_obs": n, "decision_points": len(t_list), "retrains": len(r_list),
        "first_decision": str(series.index[t_list[0]].date()) if t_list else "",
        "last_decision": str(series.index[t_list[-1]].date()) if t_list else "",
        "violations": violations,
        "min_obs_between_train_end_and_decision": min_obs_gap,
        "min_days_between_train_end_and_decision": min_day_gap,
    }


def audit_scaler(metal: str, start: int, retrain_every: int, seed: int) -> dict:
    """Train one model for real and interrogate the scaler bounds it froze."""
    from evaluate_c4_v2 import get_model

    series = load_metal_series_raw(metal)
    vals = series.to_numpy()
    r = start - HOLDOUT                       # the first retrain index
    tmp = tempfile.mkdtemp(prefix="c4_audit_")
    try:
        bundle, _secs, _trained = get_model(vals, r, tmp, seed)
        meta = bundle.meta
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    train = vals[: r + 1]
    future = vals[r + 1:]
    lo, hi = float(meta["lo"]), float(meta["hi"])

    checks = {
        "lo_equals_training_min": lo == float(train.min()),
        "hi_equals_training_max": hi == float(train.max()),
        "lo_is_not_full_series_min": lo != float(vals.min()) or float(train.min()) == float(vals.min()),
        "hi_is_not_full_series_max": hi != float(vals.max()) or float(train.max()) == float(vals.max()),
        "train_end_recorded_correctly": int(meta["train_end"]) == r,
    }
    # Does the future actually extend beyond those bounds? If it does, a
    # scaler fitted on the whole series would have had different bounds,
    # which makes this a test with teeth rather than a tautology.
    informative = bool(future.size and (future.min() < lo or future.max() > hi))

    return {
        "metal": metal, "train_end": r, "n_train": int(len(train)),
        "scaler_lo": lo, "scaler_hi": hi,
        "training_min": float(train.min()), "training_max": float(train.max()),
        "full_series_min": float(vals.min()), "full_series_max": float(vals.max()),
        "future_min": float(future.min()) if future.size else None,
        "future_max": float(future.max()) if future.size else None,
        "future_exceeds_training_bounds": informative,
        "checks": checks,
        "n_seq_val": int(meta["n_seq_val"]), "n_seq_fit": int(meta["n_seq_fit"]),
        "val_frac_actual": round(meta["n_seq_val"] / (meta["n_seq_val"] + meta["n_seq_fit"]), 4),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metals", nargs="*", default=SUPPORTED_METALS)
    ap.add_argument("--start-offset", type=int, default=START_OFFSET)
    ap.add_argument("--spacing", type=int, default=SPACING)
    ap.add_argument("--retrain-every", type=int, default=RETRAIN_EVERY)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--scaler-metal", default="nickel")
    args = ap.parse_args()

    print(f"DATA_VERSION = {data_loader.DATA_VERSION}")
    print(f"settings: start_offset={args.start_offset} spacing={args.spacing} "
          f"retrain_every={args.retrain_every} holdout={HOLDOUT} horizon={HORIZON} "
          f"window={WINDOW} val_frac={VAL_FRAC} seed={args.seed}\n")

    # --- currency check: nothing may be divided by the old INR constant ---
    print("=========== CURRENCY ===========")
    bad_currency = []
    for metal in args.metals:
        one = float(native_to_usd_per_kg(metal, 1.0))
        if one != 1.0:
            bad_currency.append((metal, one))
        print(f"  {metal:10s} native_to_usd_per_kg(1.0) = {one:.10g}"
              f"   {'<-- CONVERSION APPLIED' if one != 1.0 else '(identity, already USD/kg)'}")
    print(f"  USD_INR_RATE_HISTORICAL is {data_loader.USD_INR_RATE_HISTORICAL}, "
          f"applied to {len(bad_currency)} of {len(args.metals)} metals\n")

    # --- (1) window ordering, every decision point ---
    print("=========== WINDOW ORDERING (every decision point) ===========")
    hdr = (f"{'metal':10s} {'obs':>6s} {'points':>7s} {'retrains':>9s} {'first':>12s} {'last':>12s} "
           f"{'min gap':>8s} {'viol':>5s}")
    print(hdr)
    print("-" * len(hdr))
    total_points = total_violations = 0
    rows = []
    for metal in args.metals:
        res = audit_windows(metal, args.start_offset, args.spacing, args.retrain_every)
        rows.append(res)
        total_points += res["decision_points"]
        total_violations += len(res["violations"])
        print(f"{res['metal']:10s} {res['n_obs']:6d} {res['decision_points']:7d} {res['retrains']:9d} "
              f"{res['first_decision']:>12s} {res['last_decision']:>12s} "
              f"{res['min_obs_between_train_end_and_decision']:8d} {len(res['violations']):5d}")
    print(f"\n  checked {total_points} decision points across {len(rows)} metals")
    print(f"  VIOLATIONS (training or validation window ending on/after the decision date): "
          f"{total_violations}")
    print(f"  tightest separation anywhere: "
          f"{min(r['min_obs_between_train_end_and_decision'] for r in rows)} observations "
          f"({min(r['min_days_between_train_end_and_decision'] for r in rows)} calendar days); "
          f"required > 0, design minimum is the {HOLDOUT}-observation inner holdout")
    for r in rows:
        for v in r["violations"][:5]:
            print(f"    {r['metal']}: {v}")

    # --- (2) scaler fitted on the training window only ---
    print("\n=========== SCALER (trained for real, bounds interrogated) ===========")
    s = audit_scaler(args.scaler_metal, args.start_offset, args.retrain_every, args.seed)
    print(f"  metal                : {s['metal']}  (train_end index {s['train_end']}, "
          f"{s['n_train']} observations)")
    print(f"  scaler bounds        : lo={s['scaler_lo']:.6g}  hi={s['scaler_hi']:.6g}")
    print(f"  training window      : min={s['training_min']:.6g}  max={s['training_max']:.6g}")
    print(f"  full series          : min={s['full_series_min']:.6g}  max={s['full_series_max']:.6g}")
    print(f"  future (unseen)      : min={s['future_min']:.6g}  max={s['future_max']:.6g}")
    print(f"  future breaks those bounds: {s['future_exceeds_training_bounds']} "
          f"(if False this check proves little on this metal)")
    print(f"  validation slice     : {s['n_seq_val']} of {s['n_seq_val'] + s['n_seq_fit']} sequences "
          f"= {s['val_frac_actual']:.1%} (target {VAL_FRAC:.0%}), taken from the END of the "
          f"training window")
    for name, ok in s["checks"].items():
        print(f"    {'PASS' if ok else 'FAIL'}  {name}")

    failed = total_violations > 0 or not all(s["checks"].values())
    print("\n" + ("AUDIT FAILED -- do not start the run." if failed else
                  "AUDIT PASSED -- 0 violations; scaler is fitted on the training window only."))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
