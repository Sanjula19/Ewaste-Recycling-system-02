"""
schemas/__init__.py
---------------------
Pydantic request/response models for Component 4 -- Predictive Economic
Valuation & Strategic Disposition Dashboard (EcoVision backend).

This starts from your two original schema drafts (DispositionRequest /
DispositionResponse / EnergyBreakdown and ForecastRequest / ForecastResponse
/ ForecastDataPoint) and adds the fields needed for the upgrades you asked
for. Nothing in the original two drafts was removed or renamed -- only
added to:

  1. Metals scoped to exactly six: aluminium, nickel, steel, lead, zinc,
     copper. Gold and silver are not covered.
  2. Dual-currency pricing (USD + LKR) on every price figure, plus the FX
     rate actually used and when it was fetched, so the number is auditable
     in front of a municipal council rather than a black box.
  3. "HOLD" now carries a concrete operator_action (crush & compress into
     feedstock blocks) instead of just sitting there as a status label.
  4. Disposition responses carry a nearest-treatment-facility lookup and an
     estimated sale value of the recovered energy, for the "Residual
     Pyrolysis Tracker".
  5. IoT payload models for the ESP32 telemetry contract (hardware not
     built yet -- these define what the backend expects to receive once it
     is), plus a bin-fill lockout payload.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

class FXInfo(BaseModel):
    usd_lkr: float
    usd_inr: float                 # kept because the source price CSVs are INR-denominated
    as_of: str                     # ISO8601 timestamp of the rate actually used
    source: Literal["live", "cached", "fallback"]


class FacilityMatch(BaseModel):
    name: str
    facility_type: str             # "Waste-to-Energy" | "Pyrolysis / RDF"
    latitude: float
    longitude: float
    distance_km: float
    feed_in_tariff_lkr_per_kwh: Optional[float] = None


# ---------------------------------------------------------------------------
# /disposition
# ---------------------------------------------------------------------------

class DispositionRequest(BaseModel):
    waste_type: str = Field(..., description="Type of residual waste")
    weight_kg: float = Field(..., gt=0, description="Weight of waste in kg")
    facility_name: Optional[str] = "Urban Recycling Facility"
    batch_id: Optional[str] = None
    latitude: Optional[float] = Field(
        None, description="Source facility latitude, for nearest-treatment-plant routing. "
                           "Defaults to central Colombo if omitted."
    )
    longitude: Optional[float] = Field(
        None, description="Source facility longitude, for nearest-treatment-plant routing."
    )


class EnergyBreakdown(BaseModel):
    bio_oil_liters: float
    syngas_kwh: float
    char_kg: float
    total_kwh: float
    yield_efficiency_pct: float


class DispositionResponse(BaseModel):
    waste_type: str
    weight_kg: float
    is_recyclable: bool
    disposition_route: str         # e.g., "Pyrolysis Processing"

    # Which of the two treatment processes this batch goes through.
    # "mechanical" carries no energy figures at all -- shredding and
    # granulating releases nothing to account for, so zero there is the
    # honest answer rather than a missing value.
    disposition_method: Literal["pyrolysis", "mechanical", "thermal_recovery"] = "pyrolysis"
    dispatch_note: Optional[str] = None   # operator instruction for the mechanical route

    thermal_classification: Optional[Literal["combustible", "inert_heat_sink"]] = None
    energy_recovery_kwh: float     # NEGATIVE for inert_heat_sink materials -- see note below
    energy_breakdown: EnergyBreakdown
    gross_energy_kwh: Optional[float] = None    # combustible energy before any heat-sink deduction
    wasted_energy_kwh: Optional[float] = None   # energy spent heating an inert mass (glass) to process temp
    lhv_mj_kg: float
    process_efficiency: float
    landfill_diverted: bool        # Always True for our system
    co2_avoided_kg: float
    manifest_id: str
    timestamp: str
    facility_name: str

    # --- Residual Pyrolysis Tracker additions ---
    nearest_treatment_facility: Optional[FacilityMatch] = None
    estimated_revenue_usd: Optional[float] = None
    estimated_revenue_lkr: Optional[float] = None
    fx: Optional[FXInfo] = None


# ---------------------------------------------------------------------------
# /forecast
# ---------------------------------------------------------------------------

class ForecastRequest(BaseModel):
    metal: str = Field(
        ...,
        description="Metal type: aluminium, nickel, steel, lead, zinc, copper "
                    "(gold and silver are out of scope for this component)",
    )
    weight_kg: float = Field(..., gt=0, description="Weight of metal in kilograms")


class ForecastDataPoint(BaseModel):
    date: str
    price: float                           # USD/kg
    price_lkr: Optional[float] = None      # LKR/kg
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    lower_bound_lkr: Optional[float] = None
    upper_bound_lkr: Optional[float] = None


class ForecastResponse(BaseModel):
    metal: str
    current_price: float
    current_price_lkr: float
    forecast_90d: List[ForecastDataPoint]
    recommendation: str            # "SELL NOW" or "HOLD"
    recommendation_reason: str
    profit_if_sell: Optional[float] = None         # USD, only when SELL
    profit_if_sell_lkr: Optional[float] = None      # LKR, only when SELL
    expected_peak_price: Optional[float] = None     # USD, only when HOLD
    expected_peak_price_lkr: Optional[float] = None
    expected_peak_date: Optional[str] = None        # only when HOLD
    mape: float
    rmse: float
    model_used: str                # "ARIMA" or "LSTM" or "ARIMA+LSTM"
    weight_kg: float
    unit_price: float              # USD per kg
    unit_price_lkr: float          # LKR per kg

    # --- HOLD Command Upgrade ---
    operator_action: Literal["ROUTE_TO_MARKET_SALE", "CRUSH_AND_COMPRESS"]
    operator_action_note: str

    fx: FXInfo


# ---------------------------------------------------------------------------
# /market (Dashboard live Market Overview -- six in-scope metals only)
# ---------------------------------------------------------------------------

class MarketOverviewItem(BaseModel):
    metal: str
    current_price: float                   # USD/kg
    current_price_lkr: float                # LKR/kg
    day_change_pct: float                   # vs. the previous recorded data point
    recommendation: Literal["SELL NOW", "HOLD"]
    data_as_of: str                         # ISO8601 date of the price actually used
    price_source: Literal["live", "historical"]
    model_used: str
    mape: float


class MarketOverviewResponse(BaseModel):
    items: List[MarketOverviewItem]
    fx: FXInfo
    generated_at: str


# ---------------------------------------------------------------------------
# /iot (future ESP32 telemetry ingestion -- see routers/iot.py)
# ---------------------------------------------------------------------------

class ColorReading(BaseModel):
    r: int = Field(..., ge=0, le=255)
    g: int = Field(..., ge=0, le=255)
    b: int = Field(..., ge=0, le=255)
    lux: float


class IoTIngestPayload(BaseModel):
    device_id: str
    bin_id: Optional[str] = "bin-01"
    weight_kg: float = Field(..., gt=0)
    color: Optional[ColorReading] = None
    # Optional override: if Component 1/2's classifier (or a human operator
    # via the dashboard) already knows the material, skip the color-based
    # placeholder guess entirely.
    known_material: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class BinStatusPayload(BaseModel):
    bin_id: str = "bin-01"
    distance_cm: float = Field(..., description="Ultrasonic reading; lower = fuller")
    full_threshold_cm: float = 7.5
