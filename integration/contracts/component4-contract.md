# Component 4 Contract — Predictive Economic Valuation (Mayashi)

**Status: CONFIRMED REAL** — extracted directly from
`component-4/backend/main.py`, `component-4/backend/routers/{forecast,disposition}.py`,
and `component-4/backend/schemas/__init__.py`.

Base URL (local): `http://localhost:8004`

---

## GET /api/health

**Response (200):**
```json
{
  "status": "ok",
  "component": "Smart Valuation & Material Routing - EWaste Dashboard"
}
```

---

## POST /api/forecast/

90-day ARIMA price forecast + Sell/Hold recommendation for a recyclable metal.

**Request (`ForecastRequest`):**
```json
{
  "metal": "copper",
  "weight_kg": 500
}
```

| Field | Type | Notes |
|---|---|---|
| `metal` | string | Must resolve (case-insensitive) to one of the 6 supported metals — see below. Anything else raises `KeyError`/`ValueError` → HTTP 400. |
| `weight_kg` | float | Must be `> 0` |

**Supported metals** (from `materials_db.py`, also queryable at `GET /api/forecast/supported-metals`):
`aluminium` (or `aluminum`), `nickel`, `steel` (or `steel scrap`/`steel_scrap`), `lead`, `zinc`, `copper`.
**Out of scope (explicitly rejected):** `gold`, `silver`.

**Response (200) — `ForecastResponse`:**
```json
{
  "metal": "copper",
  "current_price": 0.0,
  "current_price_lkr": 0.0,
  "forecast_90d": [
    {"date": "...", "price": 0.0, "price_lkr": 0.0, "lower_bound": 0.0, "upper_bound": 0.0, "lower_bound_lkr": 0.0, "upper_bound_lkr": 0.0}
  ],
  "recommendation": "SELL NOW",
  "recommendation_reason": "...",
  "profit_if_sell": 0.0,
  "profit_if_sell_lkr": 0.0,
  "expected_peak_price": null,
  "expected_peak_price_lkr": null,
  "expected_peak_date": null,
  "mape": 0.0,
  "rmse": 0.0,
  "model_used": "ARIMA",
  "weight_kg": 500,
  "unit_price": 0.0,
  "unit_price_lkr": 0.0,
  "operator_action": "ROUTE_TO_MARKET_SALE",
  "operator_action_note": "...",
  "fx": {"usd_lkr": 0.0, "usd_inr": 0.0, "as_of": "...", "source": "live"}
}
```
`recommendation` is `"SELL NOW"` or `"HOLD"`. `operator_action` is `"ROUTE_TO_MARKET_SALE"` or `"CRUSH_AND_COMPRESS"`. `profit_if_sell*` populated only when SELL; `expected_peak_*` populated only when HOLD.

**Error (400):** invalid/unsupported `metal` → `{"detail": "<message>"}`

---

## GET /api/forecast/supported-metals

**Response (200):**
```json
{ "metals": ["aluminium", "nickel", "steel", "lead", "zinc", "copper"] }
```
(Exact list sourced from `data_loader.SUPPORTED_METALS` at runtime.)

---

## POST /api/disposition/

Energy recovery / disposition routing for non-recyclable residual waste (also accepts a recyclable metal name, but the code comments say such requests "should really be routed to `/api/forecast`" instead).

**Request (`DispositionRequest`):**
```json
{
  "waste_type": "pvc plastic",
  "weight_kg": 10.0,
  "facility_name": "Urban Recycling Facility",
  "batch_id": null,
  "latitude": null,
  "longitude": null
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `waste_type` | string | yes | Must resolve via `materials_db.resolve_material()` — see supported values below |
| `weight_kg` | float | yes | Must be `> 0` |
| `facility_name` | string | no | Default `"Urban Recycling Facility"` |
| `batch_id` | string | no | |
| `latitude` / `longitude` | float | no | Used for nearest-treatment-facility routing; defaults to central Colombo if omitted |

**Supported `waste_type` values** (from `materials_db.py`):
- Non-recyclables (pyrolysis/thermal route): `pvc plastic`, `pvc`, `polystyrene`, `contaminated glass`, `glass`
- Recyclable metals (accepted but flagged `is_recyclable: true` — intended for `/api/forecast` instead): `aluminium`/`aluminum`, `nickel`, `steel`/`steel scrap`/`steel_scrap`, `lead`, `zinc`, `copper`
- Anything else → `KeyError` → HTTP 400

**Response (200) — `DispositionResponse`:**
```json
{
  "waste_type": "pvc plastic",
  "weight_kg": 10.0,
  "is_recyclable": false,
  "disposition_route": "Pyrolysis Processing",
  "thermal_classification": "combustible",
  "energy_recovery_kwh": 0.0,
  "energy_breakdown": {
    "bio_oil_liters": 0.0, "syngas_kwh": 0.0, "char_kg": 0.0,
    "total_kwh": 0.0, "yield_efficiency_pct": 0.0
  },
  "gross_energy_kwh": 0.0,
  "wasted_energy_kwh": null,
  "lhv_mj_kg": 20.0,
  "process_efficiency": 0.67,
  "landfill_diverted": true,
  "co2_avoided_kg": 0.0,
  "manifest_id": "...",
  "timestamp": "...",
  "facility_name": "Urban Recycling Facility",
  "nearest_treatment_facility": {
    "name": "...", "facility_type": "Pyrolysis / RDF",
    "latitude": 0.0, "longitude": 0.0, "distance_km": 0.0,
    "feed_in_tariff_lkr_per_kwh": null
  },
  "estimated_revenue_usd": 0.0,
  "estimated_revenue_lkr": 0.0,
  "fx": {"usd_lkr": 0.0, "usd_inr": 0.0, "as_of": "...", "source": "live"}
}
```
`thermal_classification` is `"combustible"` or `"inert_heat_sink"` (glass — `energy_recovery_kwh` is **negative** for heat-sink materials, since heating inert glass to pyrolysis temperature costs energy rather than recovering it).

**Error (400):** unrecognised/out-of-scope `waste_type` → `{"detail": "<message>"}`

---

## Notes for downstream integration

- Component 4 is a **terminal consumer** with two mutually-exclusive input shapes. A caller must decide *before* calling which endpoint applies — there is no single "just call C4" endpoint.
- `metal` (forecast) and `waste_type` (disposition) vocabularies do not overlap except that disposition also accepts metal names (discouraged by the code's own docstring).
- Any material name not in the above lists cannot be safely mapped to either endpoint — must be treated as **C4_NOT_APPLICABLE**, not guessed.
