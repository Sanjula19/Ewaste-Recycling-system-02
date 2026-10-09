"""
scripts/update_prices.py
------------------------
Appends a fresh Investing.com download onto the v3 series in
backend/data/v3/, so the dataset can be extended without rebuilding it
from scratch or retyping the parsing rules.

    cd backend
    venv/Scripts/python.exe scripts/update_prices.py --from-dir data/source_v3_new
    venv/Scripts/python.exe scripts/update_prices.py --from-dir <dir> --metals copper
    venv/Scripts/python.exe scripts/update_prices.py --from-dir <dir> --dry-run

Parsing is not reimplemented here: the date-format decision, unit
inference, plausibility guard and cleaning all come from
build_dataset_v3.py, so an export is read identically whether it arrives
in a full rebuild or an incremental update. That matters because the same
Investing.com filename has already delivered two different copper
instruments (COMEX per pound and LME per tonne).

THREE SAFETY RULES, because this writes over data models were trained on:

  1. OVERLAP. The new file must overlap the existing series on at least
     --min-overlap dates, and every overlapping date must agree to within
     --tolerance percent. No overlap means there is nothing to verify the
     two files are the same instrument, and a silent instrument swap is
     exactly the failure this guards against. Disagreement is reported
     per date and nothing is written.
  2. BACKUP. Every file about to change is copied to
     data/v3/backup/<metal>.<timestamp>.csv first.
  3. APPEND ONLY. Dates already present keep their existing value. A
     re-download that revises history will say so in the report rather
     than quietly rewriting rows the current models were fitted on.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from datetime import datetime

import pandas as pd

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, os.path.join(BACKEND_DIR, "scripts"))

from build_dataset_v3 import (ALLOWED_UNITS, BuildError, SOURCES, find_source, load_clean,
                              find_gaps, find_jumps)

V3_DIR = os.path.join(BACKEND_DIR, "data", "v3")
BACKUP_DIR = os.path.join(V3_DIR, "backup")
SUMMARY = os.path.join(V3_DIR, "dataset_summary.csv")
DEFAULT_TOLERANCE_PCT = 0.5
DEFAULT_MIN_OVERLAP = 3


def load_existing(metal: str) -> pd.DataFrame | None:
    path = os.path.join(V3_DIR, f"{metal}.csv")
    if not os.path.isfile(path):
        return None
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    return df.sort_values("date").reset_index(drop=True)


def compare_overlap(old: pd.DataFrame, new: pd.DataFrame, tolerance_pct: float) -> dict:
    merged = old.merge(new, on="date", how="inner", suffixes=("_old", "_new"))
    if merged.empty:
        return {"n": 0, "max_pct": None, "offenders": pd.DataFrame()}
    pct = (merged["price_usd_kg_new"] - merged["price_usd_kg_old"]).abs() / \
          merged["price_usd_kg_old"].abs() * 100
    merged["diff_pct"] = pct
    return {
        "n": len(merged),
        "max_pct": float(pct.max()),
        "mean_pct": float(pct.mean()),
        "offenders": merged[pct > tolerance_pct].sort_values("diff_pct", ascending=False),
        "first": merged["date"].min(), "last": merged["date"].max(),
    }


def backup(metal: str, stamp: str) -> str:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    src = os.path.join(V3_DIR, f"{metal}.csv")
    dst = os.path.join(BACKUP_DIR, f"{metal}.{stamp}.csv")
    shutil.copy2(src, dst)
    return dst


def update_summary(metal: str, df: pd.DataFrame) -> None:
    """Keep dataset_summary.csv's row for this metal in step with the file."""
    if not os.path.isfile(SUMMARY):
        return
    s = pd.read_csv(SUMMARY)
    if "metal" not in s.columns or metal not in set(s["metal"]):
        return
    i = s.index[s["metal"] == metal][0]
    latest = float(df["price_usd_kg"].iloc[-1])
    for col, val in (("last_date", str(df["date"].iloc[-1].date())),
                     ("first_date", str(df["date"].iloc[0].date())),
                     ("rows", len(df)),
                     ("latest_usd_kg", round(latest, 4)),
                     ("latest_usd_tonne", round(latest * 1000, 2))):
        if col in s.columns:
            s.loc[i, col] = val
    s.to_csv(SUMMARY, index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-dir", required=True,
                    help="directory of fresh Investing.com exports (same filenames as source_v3)")
    ap.add_argument("--metals", nargs="*", default=sorted(SOURCES))
    ap.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE_PCT,
                    help="max %% disagreement allowed on overlapping dates")
    ap.add_argument("--min-overlap", type=int, default=DEFAULT_MIN_OVERLAP)
    ap.add_argument("--unit", action="append", default=[], metavar="METAL=UNIT")
    ap.add_argument("--date-format", action="append", default=[], metavar="METAL=FMT")
    ap.add_argument("--dry-run", action="store_true", help="report, write nothing")
    args = ap.parse_args()

    for item in args.unit:
        metal, _, unit = item.partition("=")
        if unit not in ALLOWED_UNITS:
            raise SystemExit(f"unknown unit {unit!r}; allowed: {sorted(ALLOWED_UNITS)}")
        SOURCES[metal].unit = unit
    for item in args.date_format:
        metal, _, fmt = item.partition("=")
        SOURCES[metal].date_format = fmt

    src_dir = args.from_dir if os.path.isabs(args.from_dir) else os.path.join(BACKEND_DIR, args.from_dir)
    if not os.path.isdir(src_dir):
        raise SystemExit(f"no such directory: {src_dir}")

    # build_dataset_v3.find_source looks in its own SRC_DIR; point it here.
    import build_dataset_v3
    build_dataset_v3.SRC_DIR = src_dir

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    updated, skipped, refused = [], [], []

    for metal in args.metals:
        spec = SOURCES[metal]
        print(f"\n=========== {metal}")
        try:
            path = find_source(spec)
            new, info = load_clean(metal, path, spec)
        except BuildError as exc:
            print(f"  SKIP: {exc}")
            skipped.append((metal, str(exc)))
            continue
        new = new[["date", "price_usd_kg"]]
        print(f"  new file   : {os.path.basename(path)}")
        print(f"               {new['date'].iloc[0].date()} -> {new['date'].iloc[-1].date()}, "
              f"{len(new)} rows, unit {info['unit']} (x{info['conversion_factor']:.8g})")

        old = load_existing(metal)
        if old is None:
            print(f"  SKIP: data/v3/{metal}.csv does not exist -- run build_dataset_v3.py first")
            skipped.append((metal, "no existing series"))
            continue
        print(f"  existing   : {old['date'].iloc[0].date()} -> {old['date'].iloc[-1].date()}, "
              f"{len(old)} rows")

        ov = compare_overlap(old, new, args.tolerance)
        if ov["n"] < args.min_overlap:
            print(f"  REFUSED: only {ov['n']} overlapping date(s), need {args.min_overlap}. "
                  f"Without an overlap there is nothing to confirm this is the same instrument.")
            refused.append((metal, "insufficient overlap"))
            continue
        print(f"  overlap    : {ov['n']} dates {ov['first'].date()} -> {ov['last'].date()}, "
              f"max diff {ov['max_pct']:.4f}%, mean {ov['mean_pct']:.4f}% "
              f"(tolerance {args.tolerance}%)")
        if len(ov["offenders"]):
            print(f"  REFUSED: {len(ov['offenders'])} overlapping date(s) disagree by more than "
                  f"{args.tolerance}%. Nothing written.")
            for _, r in ov["offenders"].head(10).iterrows():
                print(f"      {r['date'].date()}  existing {r['price_usd_kg_old']:.6f}  "
                      f"new {r['price_usd_kg_new']:.6f}  ({r['diff_pct']:+.3f}%)")
            refused.append((metal, f"{len(ov['offenders'])} dates out of tolerance"))
            continue

        fresh = new[~new["date"].isin(set(old["date"]))]
        revised = len(new) - len(fresh) - 0
        if fresh.empty:
            print(f"  nothing new: all {len(new)} rows already present (latest "
                  f"{old['date'].iloc[-1].date()})")
            skipped.append((metal, "no new dates"))
            continue

        merged = pd.concat([old, fresh], ignore_index=True)
        merged = merged.sort_values("date").drop_duplicates(subset="date", keep="first")
        merged = merged.reset_index(drop=True)

        gaps = find_gaps(merged["date"])
        jumps = find_jumps(merged)
        new_jumps = [j for j in jumps if pd.Timestamp(j["date"]) >= fresh["date"].min()]
        print(f"  appending  : {len(fresh)} new row(s) "
              f"{fresh['date'].iloc[0].date()} -> {fresh['date'].iloc[-1].date()}")
        print(f"  kept as-is : {revised} overlapping row(s) left at their existing values")
        if new_jumps:
            print(f"  NOTE: {len(new_jumps)} single-day move(s) over 15% inside the new range "
                  f"-- review, not removed:")
            for j in new_jumps[:10]:
                print(f"      {j['date']}  {j['prev_usd_kg']:.4f} -> {j['usd_kg']:.4f} "
                      f"({j['change_pct']:+.2f}%)")
        if gaps:
            print(f"  NOTE: series now has {len(gaps)} gap(s) over 5 trading days "
                  f"(latest {gaps[-1]['from']} -> {gaps[-1]['to']})")

        if args.dry_run:
            print("  DRY RUN: nothing written")
            continue

        bak = backup(metal, stamp)
        out = merged.copy()
        out["date"] = out["date"].dt.strftime("%Y-%m-%d")
        out["price_usd_kg"] = out["price_usd_kg"].round(6)
        out.to_csv(os.path.join(V3_DIR, f"{metal}.csv"), index=False)
        update_summary(metal, merged)
        print(f"  backup     : {os.path.relpath(bak, BACKEND_DIR)}")
        print(f"  written    : data/v3/{metal}.csv now {len(merged)} rows, "
              f"latest {merged['date'].iloc[-1].date()} at "
              f"{merged['price_usd_kg'].iloc[-1]:.4f} USD/kg")
        updated.append((metal, len(fresh), str(merged["date"].iloc[-1].date())))

    # ------------------------------------------------------------- report
    print("\n=========== SUMMARY")
    for metal, n, last in updated:
        print(f"  updated  {metal:10s} +{n} rows, now through {last}")
    for metal, why in skipped:
        print(f"  skipped  {metal:10s} {why}")
    for metal, why in refused:
        print(f"  REFUSED  {metal:10s} {why}")

    if updated and not args.dry_run:
        print("\n" + "=" * 70)
        print("RETRAIN REQUIRED -- the models in models_v3/ were fitted on the previous")
        print("series, and their saved scalers carry the OLD min/max. Serving them against")
        print("the extended data mis-scales every input, silently.")
        print()
        print("  cd backend")
        print("  DATA_VERSION=v3 venv/Scripts/python.exe scripts/train_production_v2.py \\")
        print("      --out models_v3 --cache models_walkforward_v3")
        print()
        print("Then restart the backend. To refresh the paper's walk-forward numbers too:")
        print("  DATA_VERSION=v3 venv/Scripts/python.exe scripts/evaluate_c4_v2.py \\")
        print("      --out results_v4 --cache models_walkforward_v3 --compare-with results_v3")
        print("=" * 70)

    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
