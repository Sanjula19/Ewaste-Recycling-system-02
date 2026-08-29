# Component 3 Contract — Smart Process Optimization (Wisu)

**Status: CONFIRMED REAL** — extracted from and verified against the actual
running backend at `component-3/backend/app/`, replaced in Step 5A and
Docker-configured in Step 5B. See `component-3/REAL-COMPONENT-3.md` for the
full structure, environment, and known gaps.

> History: this file previously documented an *expected but unimplemented*
> contract, because the backend that was in place at the time was a copy of
> Component 2's toxic-gas-detection service. That backend has been replaced
> with the real Smart Process Optimization implementation. This document now
> describes the real, running service.

Base URL (local): `http://localhost:8003`

---

## GET /api/health

**Response (200) — actually observed:**
```json
{
  "status": "ok",
  "component": "Component 3 - Smart Process Optimization Engine",
  "student": "IT22277640",
  "version": "1.0.0"
}
```

---

## GET /api/materials

**Response (200) — actually observed:**
```json
{
  "total": 8,
  "materials": [
    { "name": "Newspapers",        "waste_type": "Paper",   "category": "Paper",   "toxicity": "Low" },
    { "name": "Cardboard Boxes",   "waste_type": "Paper",   "category": "Paper",   "toxicity": "Low" },
    { "name": "Office Paper",      "waste_type": "Paper",   "category": "Paper",   "toxicity": "Low" },
    { "name": "PET Water Bottles", "waste_type": "Plastic", "category": "Plastic", "toxicity": "Low" },
    { "name": "Food Containers",   "waste_type": "Plastic", "category": "Plastic", "toxicity": "Low" },
    { "name": "Plastic Bags",      "waste_type": "Plastic", "category": "Plastic", "toxicity": "Low" },
    { "name": "Glass Bottles",     "waste_type": "Glass",   "category": "Glass",   "toxicity": "Low" },
    { "name": "Glass Jars",        "waste_type": "Glass",   "category": "Glass",   "toxicity": "Low" }
  ]
}
```
This list is hardcoded in `app/api/routes/materials.py`, not derived from a database.

---

## POST /api/optimize

**Request (`OptimizeRequest`):**
```json
{
  "material_name": "PET Water Bottles",
  "weight_kg": 5.0,
  "moisture_condition": "Wet",
  "waste_type": "Plastic",
  "moisture_pct": 50.0,
  "processing_priority": "balanced",
  "operator_id": null,
  "batch_id": null
}
```
Only `material_name`, `weight_kg`, `moisture_condition` are required by the schema. **In practice, also supply `waste_type`** — the Decision Tree step encodes it and will error on `None` (see `component-3/REAL-COMPONENT-3.md`, Known Gaps).

For `waste_type == "Plastic"` specifically, the backend overrides `moisture_condition` with a live SHEF sensor reading if one has been posted to `POST /api/sensor/moisture` — the response's `moisture_source` field tells you which value was actually used.

**Response (200) — actually observed** (for `material_name: "PET Water Bottles"`, `waste_type: "Plastic"`, `weight_kg: 5.0`, `moisture_condition: "Wet"`):
```json
{
  "material_name": "PET Water Bottles",
  "waste_type": "Plastic",
  "weight_kg": 5.0,
  "moisture_condition": "Wet",
  "recommended_method": "Thermal",
  "optimal_temp_c": 265.0,
  "processing_time_min": 45.0,
  "energy_kwh": 5.0,
  "recycling_efficiency_pct": 82.0,
  "safety_status": "WARNING",
  "pre_drying_required": true,
  "toxicity_level": "Low",
  "pre_drying_temp_c": 106.0,
  "pre_drying_time_min": 13.5,
  "pre_drying_action": "Apply controlled heat to remove moisture content",
  "chemical_agent": "None",
  "chemical_concentration": "None",
  "chemical_purpose": "No chemical required - Thermal melting",
  "handling_note": "Ensure proper ventilation during thermal processing",
  "cooling_time_min": 11.2,
  "cooling_method": "Controlled Cooling",
  "target_temp_c": 30.0,
  "batch_id": null,
  "timestamp": "2026-08-29T11:03:37.548308",
  "doc_id": "KjZuq4EpKOYwdrOiXxFb"
}
```
Field set is fixed by `app/schemas/output_schema.py` — values above are one real example, not a schema definition; see that file for which fields are always present vs. optional. `doc_id` is only populated when the Firestore write succeeds (see Storage below).

---

## GET /api/history

**Query param:** `limit` (default 20).

**Response (200):** `{"count": <int>, "results": [...]}` — each result is a previously saved `/api/optimize` response (plus a Firestore document `id`), read from the `optimization_results` Firestore collection. Returns `{"count": 0, "results": []}` if Firestore isn't connected — does not error.

---

## POST /api/sensor/moisture

ESP32 (SHEF capacitive moisture sensor) pushes readings here.

**Request:** `{"moisture_status": "Wet" | "Dry", "raw_value": <int>}`
**Response:** `{"status": "received", "data": {"moisture_status": ..., "raw_value": ..., "timestamp": "..."}}`

State is in-memory only — resets on server restart.

## GET /api/sensor/moisture/latest

**Response:** `{"moisture_status": "Dry", "raw_value": null, "timestamp": null}` until a reading has been posted.

---

## Storage

**Firestore** (Google Cloud), not SQLite/any local database. Requires a real service-account key at `app/firebase_key.json` (gitignored, never committed — see `component-3/REAL-COMPONENT-3.md` for the safe runtime-mount approach used in Docker). Without it, Firebase init fails gracefully at startup and `/api/optimize` still returns a full result, just without `doc_id`/history persistence.

## Known gaps

See `component-3/REAL-COMPONENT-3.md` for the full list (missing training CSV, a scikit-learn version mismatch warning, duplicate route registration in `main.py`, a stray inert `.js` file inside the backend). None of these prevent the endpoints above from working as documented.
