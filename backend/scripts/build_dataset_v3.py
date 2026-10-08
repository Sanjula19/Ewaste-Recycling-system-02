"""
scripts/build_dataset_v3.py
---------------------------
Turns the Investing.com exports in backend/data/source_v3/ into clean
USD/kg daily series in backend/data/v3/.

    cd backend
    venv/Scripts/python.exe scripts/build_dataset_v3.py
    venv/Scripts/python.exe scripts/build_dataset_v3.py --unit copper=USD_per_kg

Nothing in backend/data/ outside data/v3/ is written, and nothing is ever
deleted -- the v1 MCX files stay exactly where they are.

WHY THERE IS NO INR ANYWHERE IN HERE
The v1 series were MCX exports in INR/kg, divided by one flat constant
(data_loader.USD_INR_RATE_HISTORICAL = 87.5) to reach USD -- a known
weakness, since one rate was applied across a decade of history. These
files are already USD, so that constant must not appear in this pipeline
at all. This module deliberately does not import it, and ALLOWED_UNITS
below is the complete set of conversions that can be applied.

DATES ARE DECIDED, NOT GUESSED
The exports are not in one format: at the time of writing, five files use
MM/DD/YYYY and the copper file uses DD-MM-YYYY. Rather than assume, the
day/month position is settled by exclusion -- whichever field exceeds 12
somewhere in the file must be the day. If neither does (a file covering
less than ~13 days of a month), the file is REJECTED rather than parsed on
a coin flip; pass --date-format metal=%d-%m-%Y to resolve it by hand.

UNITS
All six current exports are LME-style contracts quoted in USD per metric
tonne, including copper -- its prices are in the thousands with two
decimals, matching the other five.

That is NOT a safe assumption to carry forward. Investing.com publishes
copper on two pages: "Copper Futures" (COMEX) is quoted in USD per POUND
with four decimals and a 0.0005 tick, while the LME page is USD per
tonne. An earlier download of this same filename was the COMEX one. A
pound file converted as tonnes lands 2,204x off.

So the unit is not trusted blindly: check_unit_plausibility() below
converts with the configured unit and rejects the result if the series
does not land in the range industrial metals actually occupy, naming the
unit that would fit instead. Combined with the printed USD/tonne figures,
a wrong unit should be loud rather than silent. --unit overrides any of
this without a code edit.
"""

from __future__ import annotations

import argparse
import csv
import glob
import os
import re
import sys
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BACKEND_DIR, "data", "source_v3")
OUT_DIR = os.path.join(BACKEND_DIR, "data", "v3")

# The only conversions this pipeline may apply. USD in, USD/kg out.
ALLOWED_UNITS = {
    "USD_per_tonne": 1.0 / 1000.0,             # metric tonne -> kg
    "USD_per_pound": 2.2046226218487757,       # lb -> kg (1 kg = 2.2046... lb)
    "USD_per_kg": 1.0,
}

GAP_TRADING_DAYS = 5        # flag a hole longer than this many business days
JUMP_PCT = 15.0             # flag a single-day move this large, never drop it

# The range industrial base metals plausibly occupy in USD/kg, wide enough
# to hold everything here (steel scrap ~0.18 at the bottom, the 2022 nickel
# squeeze ~62 at the top) and far too narrow to survive a 1000x or 2204x
# unit error. Used only to reject a converted series, never to alter one.
PLAUSIBLE_USD_KG = (0.05, 200.0)


@dataclass
class SourceSpec:
    patterns: list[str]
    contract: str
    unit: str | None = None            # None -> infer from the file
    date_format: str | None = None     # None -> decide by exclusion


SOURCES: dict[str, SourceSpec] = {
    "aluminium": SourceSpec(["Aluminium*Historical*Data*.csv", "Aluminum*Historical*Data*.csv"],
                            "Aluminium (LME)"),
    "copper":    SourceSpec(["Copper*Futures*Historical*Data*.csv"],
                            "Copper Futures"),
    "lead":      SourceSpec(["Lead*Futures*Historical*Data*.csv"], "Lead Futures (LME)"),
    "nickel":    SourceSpec(["Nickel*Futures*Historical*Data*.csv"], "Nickel Futures (LME)"),
    "steel":     SourceSpec(["Steel*Scrap*Futures*Historical*Data*.csv"], "Steel Scrap Futures"),
    "zinc":      SourceSpec(["Zinc*Futures*Historical*Data*.csv"], "Zinc Futures (LME)"),
}

# Above this, a base-metal quote can only be per tonne: the dearest metal
# here is nickel, and even its 2022 squeeze peak is ~62 USD/kg.
PER_TONNE_FLOOR = 150.0


class BuildError(Exception):
    pass


# --------------------------------------------------------------------- parsing

def find_source(spec: SourceSpec) -> str:
    """The one file matching this metal, tolerating a '(1)' re-download suffix."""
    hits = sorted({p for pat in spec.patterns for p in glob.glob(os.path.join(SRC_DIR, pat))})
    if not hits:
        raise BuildError(f"no file in {SRC_DIR} matching {spec.patterns}")
    if len(hits) > 1:
        raise BuildError(f"{len(hits)} files match {spec.patterns}: "
                         f"{[os.path.basename(h) for h in hits]} -- remove the stale one")
    return hits[0]


def decide_date_format(raw: pd.Series) -> tuple[str, str]:
    """
    Settle day-vs-month by exclusion across the whole column.

    Returns (strptime format, the evidence for it). Raises when the column
    cannot be decided from its own contents -- a guess here silently
    reorders the entire series, so it is not worth making one.
    """
    sep = "/" if raw.iloc[0].count("/") == 2 else "-"
    parts = raw.str.split(re.escape(sep), regex=True, expand=True)
    if parts.shape[1] != 3:
        raise BuildError(f"dates are not three fields separated by '{sep}': {raw.iloc[0]!r}")
    a, b = parts[0].astype(int), parts[1].astype(int)
    a_big, b_big = int((a > 12).sum()), int((b > 12).sum())

    if a_big and b_big:
        raise BuildError(f"both date fields exceed 12 ({a_big} and {b_big} rows) -- "
                         f"the column is not one consistent format")
    if a_big:
        return f"%d{sep}%m{sep}%Y", f"field 1 exceeds 12 on {a_big} row(s), field 2 never does"
    if b_big:
        return f"%m{sep}%d{sep}%Y", f"field 2 exceeds 12 on {b_big} row(s), field 1 never does"
    raise BuildError("neither date field ever exceeds 12, so day and month are "
                     "indistinguishable -- pass --date-format <metal>=<fmt>")


def load_clean(metal: str, path: str, spec: SourceSpec) -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    for col in ("Date", "Price"):
        if col not in df.columns:
            raise BuildError(f"missing required column {col!r}; found {list(df.columns)}")

    raw = df["Date"].astype(str).str.strip()
    if spec.date_format:
        fmt, evidence = spec.date_format, "given on the command line"
    else:
        fmt, evidence = decide_date_format(raw)
    dates = pd.to_datetime(raw, format=fmt, errors="coerce")
    if dates.isna().any():
        bad = raw[dates.isna()].head(5).tolist()
        raise BuildError(f"{int(dates.isna().sum())} date(s) unparseable as {fmt}: {bad}")

    price = pd.to_numeric(
        df["Price"].astype(str).str.replace(",", "", regex=False).str.replace('"', "", regex=False),
        errors="coerce")

    out = pd.DataFrame({"date": dates, "price_native": price})
    n_raw = len(out)
    n_missing = int(out["price_native"].isna().sum())
    n_zero = int((out["price_native"] == 0).sum())
    n_negative = int((out["price_native"] < 0).sum())

    out = out.dropna(subset=["price_native"])
    out = out[out["price_native"] > 0]
    out = out.sort_values("date", kind="mergesort")
    n_dupes = int(out["date"].duplicated().sum())
    out = out.drop_duplicates(subset="date", keep="first").reset_index(drop=True)

    # Unit: inferred from this file unless pinned on the command line, then
    # sanity-checked either way.
    median_native = float(out["price_native"].median())
    decimals = int(df["Price"].astype(str).str.split(".").str[-1].str.len().mode().iloc[0])
    vol = df["Vol."].fillna("").astype(str).str.strip() if "Vol." in df.columns else pd.Series([""])
    vol_fraction = float((vol != "").mean())

    if spec.unit:
        unit, unit_evidence = spec.unit, "given on the command line"
    else:
        unit, unit_evidence = infer_unit(median_native, decimals, vol_fraction)
    check_unit_plausibility(metal, median_native, unit)

    factor = ALLOWED_UNITS[unit]
    out["price_usd_kg"] = out["price_native"] * factor

    return out, {
        "date_format": fmt, "date_format_evidence": evidence, "rows_in": n_raw,
        "missing": n_missing, "zero": n_zero, "negative": n_negative, "duplicate_dates": n_dupes,
        "unit": unit, "unit_evidence": unit_evidence, "conversion_factor": factor,
        "decimals": decimals, "vol_fraction": vol_fraction,
    }


# --------------------------------------------------------------------- checks

def infer_unit(median_native: float, decimals: int, vol_fraction: float) -> tuple[str, str]:
    """
    Work out the quote unit from the file itself, and say what decided it.

    This is inferred rather than configured because the same Investing.com
    filename has delivered two different instruments on different days: the
    LME copper page (USD/tonne, two decimals, sparse volume) and the COMEX
    "Copper Futures" page (USD/pound, four decimals from the 0.0005 tick,
    volume on every row). A hardcoded unit is therefore wrong roughly half
    the time, and wrong by a factor of 2,204.

    Returns (unit, evidence). Raises when the evidence does not settle it,
    because a 50/50 guess here silently poisons every downstream number.
    """
    if median_native > PER_TONNE_FLOOR:
        return "USD_per_tonne", (f"median price {median_native:,.2f} is above "
                                 f"{PER_TONNE_FLOOR:,.0f}, so the quote is per tonne")
    if decimals >= 4:
        return "USD_per_pound", (f"median price {median_native:,.4f} with {decimals} decimals and "
                                 f"volume on {vol_fraction:.0%} of rows -- the COMEX per-pound tick")
    raise BuildError(
        f"cannot tell the unit from the file: median price {median_native:,.4f} with "
        f"{decimals} decimals, volume on {vol_fraction:.0%} of rows. That is too small "
        f"to be per tonne and lacks the per-pound tick. Pass --unit <metal>=<unit> "
        f"explicitly, one of {sorted(ALLOWED_UNITS)}.")


def check_unit_plausibility(metal: str, median_native: float, unit: str) -> None:
    """
    Reject a conversion whose result is not a price any industrial metal has.

    The failure this exists for is silent: the same Investing.com filename
    has already delivered both a COMEX USD-per-pound export and an LME
    USD-per-tonne one. Converting the tonne file as pounds overstates it by
    2,204x, and nothing downstream would complain -- it would just train on
    nonsense. A magnitude check cannot tell 2% from 2%, but it catches every
    error of this kind, which are the ones that matter here.
    """
    lo, hi = PLAUSIBLE_USD_KG
    got = median_native * ALLOWED_UNITS[unit]
    if lo <= got <= hi:
        return
    fits = [u for u, f in ALLOWED_UNITS.items() if lo <= median_native * f <= hi]
    hint = (f" The file does fit {fits[0]} ({median_native * ALLOWED_UNITS[fits[0]]:,.4f} USD/kg); "
            f"rerun with --unit {metal}={fits[0]} if that is right."
            if len(fits) == 1 else
            f" Candidate units that would fit: {fits or 'none'}.")
    raise BuildError(
        f"unit {unit} gives a median of {got:,.4f} USD/kg, outside the plausible "
        f"{lo}-{hi} USD/kg range for an industrial metal (median source price "
        f"{median_native:,.4f}).{hint}")


def find_gaps(dates: pd.Series, max_days: int = GAP_TRADING_DAYS) -> list[dict]:
    d = dates.dt.date.to_numpy()
    gaps = []
    for prev, nxt in zip(d[:-1], d[1:]):
        bdays = int(np.busday_count(prev, nxt))
        if bdays > max_days:
            gaps.append({"from": str(prev), "to": str(nxt), "trading_days": bdays,
                         "calendar_days": (nxt - prev).days})
    return gaps


def find_jumps(df: pd.DataFrame, pct: float = JUMP_PCT) -> list[dict]:
    chg = df["price_usd_kg"].pct_change() * 100
    hits = chg.abs() > pct
    return [{"date": str(df["date"].iloc[i].date()),
             "prev_usd_kg": round(float(df["price_usd_kg"].iloc[i - 1]), 6),
             "usd_kg": round(float(df["price_usd_kg"].iloc[i]), 6),
             "change_pct": round(float(chg.iloc[i]), 2)}
            for i in np.flatnonzero(hits.to_numpy())]


# --------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metals", nargs="*", default=sorted(SOURCES))
    ap.add_argument("--unit", action="append", default=[],
                    metavar="METAL=UNIT", help=f"override a unit; one of {sorted(ALLOWED_UNITS)}")
    ap.add_argument("--date-format", action="append", default=[],
                    metavar="METAL=FMT", help="override date parsing, e.g. copper=%%d-%%m-%%Y")
    ap.add_argument("--out", default=OUT_DIR)
    args = ap.parse_args()

    for item in args.unit:
        metal, _, unit = item.partition("=")
        if unit not in ALLOWED_UNITS:
            raise SystemExit(f"unknown unit {unit!r}; allowed: {sorted(ALLOWED_UNITS)}")
        if metal not in SOURCES:
            raise SystemExit(f"unknown metal {metal!r}; known: {sorted(SOURCES)}")
        SOURCES[metal].unit = unit
    for item in args.date_format:
        metal, _, fmt = item.partition("=")
        SOURCES[metal].date_format = fmt

    os.makedirs(args.out, exist_ok=True)
    summary_rows, all_gaps, all_jumps, failures = [], {}, {}, {}

    for metal in args.metals:
        spec = SOURCES[metal]
        try:
            path = find_source(spec)
            df, info = load_clean(metal, path, spec)
            if df.empty:
                raise BuildError("no usable rows after cleaning")
        except BuildError as exc:
            failures[metal] = str(exc)
            print(f"[{metal}] FAILED: {exc}", flush=True)
            continue

        gaps, jumps = find_gaps(df["date"]), find_jumps(df)
        all_gaps[metal], all_jumps[metal] = gaps, jumps

        df[["date", "price_usd_kg"]].assign(
            date=df["date"].dt.strftime("%Y-%m-%d"),
            price_usd_kg=df["price_usd_kg"].round(6),
        ).to_csv(os.path.join(args.out, f"{metal}.csv"), index=False)

        summary_rows.append({
            "metal": metal,
            "source_file": os.path.basename(path),
            "contract": spec.contract,
            "original_unit": info["unit"],
            "unit_evidence": info["unit_evidence"],
            "conversion_factor": info["conversion_factor"],
            "date_format": info["date_format"],
            "date_format_evidence": info["date_format_evidence"],
            "first_date": str(df["date"].iloc[0].date()),
            "last_date": str(df["date"].iloc[-1].date()),
            "rows": len(df),
            "rows_in_source": info["rows_in"],
            "missing_prices": info["missing"],
            "zero_prices": info["zero"],
            "negative_prices": info["negative"],
            "duplicate_dates_dropped": info["duplicate_dates"],
            "gaps_over_5_trading_days": len(gaps),
            "jumps_over_15_pct": len(jumps),
            "latest_usd_kg": round(float(df["price_usd_kg"].iloc[-1]), 4),
            "latest_usd_tonne": round(float(df["price_usd_kg"].iloc[-1]) * 1000, 2),
        })

    if summary_rows:
        with open(os.path.join(args.out, "dataset_summary.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(summary_rows[0]))
            w.writeheader()
            w.writerows(summary_rows)

    # ------------------------------------------------------------- report
    print("\n=========== DATASET SUMMARY (v3) ===========")
    hdr = f"{'metal':10s} {'unit':14s} {'factor':>12s} {'first':>10s} {'last':>10s} {'rows':>6s} {'gaps':>5s} {'jumps':>6s}"
    print(hdr)
    print("-" * len(hdr))
    for r in summary_rows:
        print(f"{r['metal']:10s} {r['original_unit']:14s} {r['conversion_factor']:12.8f} "
              f"{r['first_date']:>10s} {r['last_date']:>10s} {r['rows']:6d} "
              f"{r['gaps_over_5_trading_days']:5d} {r['jumps_over_15_pct']:6d}")

    print("\n=========== HOW EACH FILE WAS READ ===========")
    for r in summary_rows:
        print(f"  {r['metal']:10s} {r['source_file']}")
        print(f"             dates {r['date_format']:12s} -- {r['date_format_evidence']}")
        print(f"             unit  {r['original_unit']:14s} -- {r['unit_evidence']}")

    print("\n=========== LATEST PRICE (sanity-check these) ===========")
    print(f"{'metal':10s} {'USD/kg':>12s} {'USD/tonne':>14s}   source quote")
    for r in summary_rows:
        native = r["latest_usd_kg"] / r["conversion_factor"]
        unit_short = {"USD_per_tonne": "USD/t", "USD_per_pound": "USD/lb", "USD_per_kg": "USD/kg"}[r["original_unit"]]
        print(f"{r['metal']:10s} {r['latest_usd_kg']:12.4f} {r['latest_usd_tonne']:14,.2f}"
              f"   {native:,.4f} {unit_short}  ({r['last_date']})")

    for metal, gaps in all_gaps.items():
        if gaps:
            print(f"\n--- {metal}: {len(gaps)} gap(s) longer than {GAP_TRADING_DAYS} trading days")
            for g in gaps[:25]:
                print(f"      {g['from']} -> {g['to']}  ({g['trading_days']} trading days, "
                      f"{g['calendar_days']} calendar)")
            if len(gaps) > 25:
                print(f"      ... and {len(gaps) - 25} more")

    flagged = {m: j for m, j in all_jumps.items() if j}
    if flagged:
        print(f"\n--- single-day moves over {JUMP_PCT}% -- REVIEW, NOT REMOVED")
        for metal, jumps in flagged.items():
            for j in jumps[:25]:
                print(f"      {metal:10s} {j['date']}  {j['prev_usd_kg']:.4f} -> {j['usd_kg']:.4f} "
                      f"USD/kg  ({j['change_pct']:+.2f}%)")
            if len(jumps) > 25:
                print(f"      {metal}: ... and {len(jumps) - 25} more")
    else:
        print(f"\nNo single-day move exceeded {JUMP_PCT}%.")

    if failures:
        print("\n--- FAILED")
        for metal, why in failures.items():
            print(f"      {metal}: {why}")

    short = [r for r in summary_rows if r["rows"] < 200]
    if short:
        print("\n*** WARNING: these series are far too short to train or evaluate on.")
        print("***          Window is 60 observations and the inner holdout is 30.")
        for r in short:
            print(f"      {r['metal']:10s} {r['rows']:5d} rows  "
                  f"({r['first_date']} -> {r['last_date']})")

    print(f"\nWrote {len(summary_rows)} series to {args.out}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
