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
    usd_inr: float                 # kept because the v1 price CSVs are INR-denominated
    as_of: str                     # ISO8601 date of the rate actually used (== rate_date)
    # "live" is retained only so an older cached payload still validates;
    # the live path now reports the provider it actually came from.
    source: Literal["exchangerate-api", "live", "cached", "fallback"]

    # --- ExchangeRate-API fields ---
    # rate_date is the provider's own time_last_update_utc, NOT when we
    # fetched it; fetched_at is when we did. They can differ by a day, and
    # conflating them would overstate how fresh the number is.
    rate: Optional[float] = None            # USD -> LKR, same as usd_lkr
    rate_date: Optional[str] = None
    fetched_at: Optional[str] = None        # None when serving the constant
    provider: Optional[str] = None
    provider_url: Optional[str] = None      # attribution required by the provider


class FacilityMatch(BaseModel):
    """
    DEPRECATED. Superseded by FacilityRef, which carries the operator,
    town, technology, status and source_url that a dispatch note needs.
    Kept because the IoT compact contract and older dashboard builds read
    it; populated from the recommendation (or, when there is none, the
    alternative) so it never goes empty while a caller still depends on it.
    """
    name: str
    facility_type: str             # technology, in the old free-text form
    latitude: float
    longitude: float
    distance_km: float
    feed_in_tariff_lkr_per_kwh: Optional[float] = None


class FacilityRef(BaseModel):
    """One facility on the register, as returned to a caller."""
    id: str
    name: str
    operator: str
    town: str
    district: str
    technology: Literal["pyrolysis", "incineration_wte", "mechanical_recycling"]
    status: Literal["operational", "unconfirmed"]
    # Convenience mirror of `status` so the dashboard can render a badge
    # without re-encoding the rule that drives it.
    unconfirmed: bool
    distance_km: Optional[float] = None       # straight-line km from the origin
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    exports_electricity: bool = False
    tariff_lkr_per_kwh: Optional[float] = None
    source_url: Optional[str] = None
    coordinates_source: str = ""
    last_verified: str = ""


class FacilityExclusion(BaseModel):
    """
    A facility the register holds but routing could not use. Returned so a
    missing plant is visible rather than silently absent.
    """
    id: str
    name: str
    operator: str
    town: str
    technology: str
    status: str
    source_url: Optional[str] = None
    reason: str


class OriginRef(BaseModel):
    """Where distances were measured from."""
    name: str
    latitude: float
    longitude: float
    source: Literal["local_authority", "request_override", "default"]
    district: Optional[str] = None


class ElectricityValue(BaseModel):
    """
    Indicative value of electricity the receiving plant would generate,
    plus the grid CO2 that displaces.

    Reported ONLY when the plant exports electricity AND its tariff is
    sourced on the register. Everywhere else `reported` is False and
    `not_reported_reason` says which condition failed, so a blank figure
    is never mistaken for a zero one.
    """
    reported: bool
    label: str
    not_reported_reason: Optional[str] = None
    facility_name: Optional[str] = None
    energy_kwh: Optional[float] = None
    tariff_lkr_per_kwh: Optional[float] = None
    value_lkr: Optional[float] = None
    grid_co2_avoided_kg: Optional[float] = None


class PyrolysisProducts(BaseModel):
    """
    What a pyrolysis batch yields, by mass. No monetary figure: the oil,
    gas and char are not sold at a price this system knows, so `value` is
    the string "not estimated" rather than a number nobody can defend.
    """
    bio_oil_liters: float
    bio_oil_kg: float
    syngas_kg: float
    char_kg: float
    oil_pct: float
    gas_pct: float
    char_pct: float
    value: str = "not estimated"
    value_note: str


# ---------------------------------------------------------------------------
# /disposition
# ---------------------------------------------------------------------------

class DispositionRequest(BaseModel):
    waste_type: str = Field(..., description="Type of residual waste")
    weight_kg: float = Field(..., gt=0, description="Weight of waste in kg")
    facility_name: Optional[str] = "Urban Recycling Facility"
    batch_id: Optional[str] = None
    local_authority: Optional[str] = Field(
        None,
        description="The operator's local authority, as named in "
                    "backend/data/local_authorities.json. Routing measures from "
                    "here. Falls back to DEFAULT_LOCAL_AUTHORITY from the "
                    "environment when omitted.",
    )
    latitude: Optional[float] = Field(
        None, description="Optional origin latitude. Overrides local_authority when "
                          "both are given -- an operator with a real GPS reading "
                          "should not be forced onto a town centroid."
    )
    longitude: Optional[float] = Field(
        None, description="Optional origin longitude. See latitude."
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
    #
    # "thermal_recovery" was removed with contaminated glass: it existed
    # only for the inert heat-sink route, which no longer has a material.
    disposition_method: Literal["pyrolysis", "mechanical"] = "pyrolysis"
    dispatch_note: Optional[str] = None   # operator instruction for the mechanical route

    # DEPRECATED, and now always "combustible" when present. The
    # "inert_heat_sink" case went with glass.
    thermal_classification: Optional[Literal["combustible"]] = None

    energy_recovery_kwh: float     # energy CONTENT recovered, kWh; never negative now
    energy_breakdown: EnergyBreakdown
    gross_energy_kwh: Optional[float] = None
    lhv_mj_kg: float
    process_efficiency: float
    landfill_diverted: bool        # Always True for our system

    # Grid CO2 displaced, kg. Non-zero ONLY where the receiving plant
    # exports electricity on a sourced tariff -- see ElectricityValue.
    # A pyrolysis batch reports 0.0 here, with the reason in `electricity`.
    co2_avoided_kg: float

    manifest_id: str
    timestamp: str
    facility_name: str

    # --- Facility routing from the operator's local authority ----------
    origin: Optional[OriginRef] = None
    recommended_facility: Optional[FacilityRef] = None
    alternative_facility: Optional[FacilityRef] = None
    facilities_excluded: List[FacilityExclusion] = Field(default_factory=list)
    # Set when no facility of the recommended technology is both
    # coordinated and operational. The recommendation is then None, and
    # this says which rule blocked it.
    recommendation_blocked_reason: Optional[str] = None

    # --- Value and emissions -------------------------------------------
    electricity: Optional[ElectricityValue] = None
    pyrolysis_products: Optional[PyrolysisProducts] = None

    # --- DEPRECATED -----------------------------------------------------
    # nearest_treatment_facility: use recommended_facility (falls back to
    #   alternative_facility when there is no recommendation).
    # estimated_revenue_*: waste streams carry no revenue. Retained as
    #   None because routers/iot.py reads estimated_revenue_lkr into the
    #   compact wire contract the firmware parses; removing it would mean
    #   reflashing the ESP32.
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

    # --- No-forecastable-signal check ---
    # persistence_mape: error of a no-change forecast on the same 30-day
    # holdout `mape` was measured on. None when the model folder ships no
    # holdout metrics, in which case the check is not applied.
    # signal: False means the model did not beat that no-change baseline,
    # and the recommendation is forced to SELL NOW.
    persistence_mape: Optional[float] = None
    signal: bool = True

    # --- Data freshness ---
    # The price being valued is the last observation in the configured
    # dataset, which is not necessarily today. Stated outright so a
    # dashboard cannot present a year-old close as a live quote.
    last_price_date: Optional[str] = None       # YYYY-MM-DD
    data_age_days: Optional[int] = None
    stale_data: bool = False                    # True when data_age_days > 7
    data_warning: Optional[str] = None          # staleness and/or source conflict

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
    # Same pairs as ForecastResponse -- see the notes there.
    persistence_mape: Optional[float] = None
    signal: bool = True
    last_price_date: Optional[str] = None
    data_age_days: Optional[int] = None
    stale_data: bool = False
    data_warning: Optional[str] = None


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
