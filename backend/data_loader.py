"""
data_loader.py
---------------
Loads and cleans the raw commodity CSVs into a normalized format:
DataFrame/Series indexed by date (ascending), values in USD/kg.

Serves two roles now:
  1. Historical training data for the ARIMA model (statsmodels needs a
     reasonably long daily series; the InfluxDB bucket described in your
     .env is meant for *live* ticks going forward, not 10 years of backfill).
  2. A fallback "current price" source when InfluxDB has no data yet for a
     metal (e.g. in dev, or before your ingestion job has run) -- see
     services/forecast_service.py.

FINAL SCOPE: this component covers exactly six metals -- aluminium,
nickel, steel, lead, zinc, copper. Gold and silver are NOT in
MATERIAL_CONFIG. The unused CSVs (Refined_Gold, Silver) are left in
data/ untouched in case another component still needs them.

DATA-PROVENANCE NOTE (read before citing these numbers in your report):
The "*_Historical_Data.csv" files are investing.com / MCX (Multi Commodity
Exchange of India) style exports. They are NOT all in the same currency or
unit. Cross-checking the price magnitudes against known world commodity
prices:

    File                 Native unit (inferred)   Sanity check
    -------------------  ------------------------ ---------------------------
    Aluminium            INR per kg                ~228 INR/kg ~= $2.7/kg  OK
    Copper                INR per kg                ~800 INR/kg ~= $9.6/kg  OK
    Lead                  INR per kg                ~185 INR/kg ~= $2.2/kg  OK
    Zinc                  INR per kg                 ~270 INR/kg ~= $3.2/kg  OK
    Nickel                INR per kg                ~1,428 INR/kg ~= $17/kg OK
    Steel Scrap Futures   USD per metric ton         ~$350/ton               OK

This matches your own dataset list, which cites an MCX-sourced Kaggle set
(MCX trades in INR) -- so converting to USD (and then LKR) is a required
step before these numbers mean anything on a single dashboard, not
optional cleanup.

USD_INR_RATE_HISTORICAL below is a single constant, used only to normalize
the multi-year *historical* INR series into USD for model training. It is
intentionally separate from the *live* USD/LKR and USD/INR rates used for
current-price display (see services/fx_service.py) -- for a fully rigorous
backtest you would instead join a historical daily USD/INR series (e.g.
another Pink Sheet-style export) so each day's INR price is converted at
that day's rate rather than one flat constant. Flagged here rather than
hidden.
"""

from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Literal
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Used only to normalize historical INR series for model training.
# Live display rates come from services/fx_service.py instead.
USD_INR_RATE_HISTORICAL = 87.5  # approx. average over the CSVs' 2014-2024 span

Unit = Literal["INR_per_kg", "USD_per_ton"]


@dataclass(frozen=True)
class MetalConfig:
    filename: str
    date_format: str
    native_unit: Unit


# Final scope: aluminium, copper, lead, nickel, zinc, steel.
# Gold and silver are explicitly NOT in this component's metals list.
MATERIAL_CONFIG: dict[str, MetalConfig] = {
    "aluminium": MetalConfig("Aluminium_Historical_Data.csv", "%d-%m-%Y", "INR_per_kg"),
    "aluminum":  MetalConfig("Aluminium_Historical_Data.csv", "%d-%m-%Y", "INR_per_kg"),
    "copper":    MetalConfig("Copper_Historical_Data.csv", "%d-%m-%Y", "INR_per_kg"),
    "lead":      MetalConfig("Lead_Historical_Data.csv", "%d-%m-%Y", "INR_per_kg"),
    "nickel":    MetalConfig("Nickel_Historical_Data.csv", "%d-%m-%Y", "INR_per_kg"),
    "zinc":      MetalConfig("Zinc_Historical_Data.csv", "%d-%m-%Y", "INR_per_kg"),
    "steel":       MetalConfig("Steel_Scrap_Futures_Historical_Data.csv", "%m/%d/%Y", "USD_per_ton"),
    "steel_scrap": MetalConfig("Steel_Scrap_Futures_Historical_Data.csv", "%m/%d/%Y", "USD_per_ton"),
}

SUPPORTED_METALS = sorted({"aluminium", "copper", "lead", "nickel", "zinc", "steel"})


def _clean_numeric(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace('"', "", regex=False)
        .astype(float)
    )


def _to_usd_per_kg(price: pd.Series, unit: Unit) -> pd.Series:
    if unit == "INR_per_kg":
        return price / USD_INR_RATE_HISTORICAL
    if unit == "USD_per_ton":
        return price / 1000.0  # metric ton -> kg
    raise ValueError(f"Unknown unit: {unit}")


def load_metal_series_raw(metal: str) -> pd.Series:
    """
    Daily price series in NATIVE units (ascending, deduped) -- i.e. exactly
    what's in the source CSV's 'Price' column, no currency/unit conversion
    applied. This matters for services/pretrained_models.py: your
    ewaste_preprocessing.run_pipeline() fits its MinMaxScaler on this raw
    'Price' column directly, so a pretrained .pkl/.h5 model's predictions
    come back in these same native units (INR/kg for most metals, USD/ton
    for steel) -- NOT in USD/kg. Convert with native_to_usd_per_kg() below
    before doing anything else with them.
    """
    key = metal.strip().lower()
    if key not in MATERIAL_CONFIG:
        raise ValueError(
            f"Unsupported metal '{metal}'. This component covers: {SUPPORTED_METALS}"
        )
    cfg = MATERIAL_CONFIG[key]
    path = os.path.join(DATA_DIR, cfg.filename)

    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    df["Date"] = pd.to_datetime(df["Date"], format=cfg.date_format)
    df["Price"] = _clean_numeric(df["Price"])
    df = df.sort_values("Date").drop_duplicates(subset="Date").set_index("Date")
    df["Price"].name = "price_native"
    return df["Price"]


def native_to_usd_per_kg(metal: str, value) -> "float | pd.Series":
    """Converts a raw native-unit price (or Series of them) to USD/kg."""
    key = metal.strip().lower()
    cfg = MATERIAL_CONFIG[key]
    return _to_usd_per_kg(value, cfg.native_unit)


def load_metal_series(metal: str) -> pd.Series:
    """Daily USD/kg series (ascending, deduped) for the requested metal."""
    raw = load_metal_series_raw(metal)
    usd_kg = native_to_usd_per_kg(metal, raw)
    usd_kg.name = "price_usd_kg"
    return usd_kg


def load_cmo_monthly() -> pd.DataFrame:
    """
    World Bank 'Pink Sheet' monthly commodity file -- 60+ years of context
    alongside the ~10 year daily MCX series above. Not used directly by the
    ARIMA model (too coarse), but useful for the report's long-run trend
    charts and for sanity-checking whether a forecast is consistent with the
    multi-decade macro cycle.
    """
    path = os.path.join(DATA_DIR, "CMO-Historical-Data-Monthly.csv")
    df = pd.read_csv(path, header=4)
    df = df.iloc[1:].reset_index(drop=True)  # drop the units row
    df = df.rename(columns={df.columns[0]: "period"})
    df["period"] = df["period"].astype(str).str.strip()
    df = df[df["period"].str.match(r"^\d{4}M\d{2}$", na=False)]
    df["date"] = pd.to_datetime(df["period"], format="%YM%m")
    for col in df.columns:
        if col not in ("period", "date"):
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "", regex=False), errors="coerce"
            )
    return df.set_index("date").drop(columns=["period"])


def load_cmo_annual() -> pd.DataFrame:
    """World Bank 'Pink Sheet' annual commodity file (same idea as monthly)."""
    path = os.path.join(DATA_DIR, "CMO-Historical-Data-Annual.csv")
    df = pd.read_csv(path, header=5)
    df = df.iloc[1:].reset_index(drop=True)
    df = df.rename(columns={df.columns[0]: "year"})
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)
    for col in df.columns:
        if col != "year":
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "", regex=False), errors="coerce"
            )
    return df.set_index("year")
