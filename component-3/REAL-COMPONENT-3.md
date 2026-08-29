# Component 3 — Real Smart Process Optimization Backend

Status: **REAL implementation confirmed and runtime-tested** (Step 5A / Step 10 follow-up,
2026-08-29). This replaces the earlier toxic-gas-clone backend described in
`integration/contracts/component3-contract.md` and `integration/INTEGRATION_STATUS.md`
(those documents are now historical — see the note at the end of this file).

---

## Actual backend structure

```
component-3/backend/
    app/
        __init__.py
        config.py                  # Firebase init, data-file paths
        main.py                    # FastAPI app, router registration
        api/
            routes/
                health.py           # GET  /health
                materials.py        # GET  /materials
                optimize.py         # POST /optimize
                history.py          # GET  /history
                sensor.py           # POST /api/sensor/moisture, GET /api/sensor/moisture/latest
        data/
            chemical_agent_map.json
            recycling_benchmark.csv
            safety_rules.json
            (component3_training_v2.csv — NOT present, see Known Gaps)
        models/
            load_models.py
            material_model/
                load_models.py
                model.pkl            # Decision Tree
                encoders.pkl
                scaler.pkl
                target_encoder.pkl
        schemas/
            input_schema.py         # OptimizeRequest
            output_schema.py        # OptimizeResponse
        services/
            optimization_service.py  # Model 1 — Decision Tree
            energy_service.py        # Model 2 — MCDM
            safety_service.py        # Model 3 — Rule-based safety
            process_plan_service.py  # Combines all three into final recipe
            firestore_service.py     # Persistence
        utils/
            feature_engineering.py
            validators.py
        firebase_key.json           # REAL credential — gitignored, not in the image
    requirements.txt
```

This matches the structure the task described. No rearrangement was needed.

## Start command

```bash
cd component-3/backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8003
```

Port is set purely via the `--port` flag, same pattern as the other components — `config.py` has no port setting of its own.

## API endpoints (actually tested — see Test Results below)

| Method | Path | Registered via |
|---|---|---|
| GET | `/api/health` | `health.router`, prefix `/api` |
| GET | `/api/materials` | `materials.router`, prefix `/api` |
| GET | `/api/history?limit=20` | `history.router`, prefix `/api` (reads Firestore) |
| POST | `/api/optimize` | `optimize.router`, prefix `/api` |
| POST | `/api/sensor/moisture` | `sensor.router` (path is absolute in the decorator) |
| GET | `/api/sensor/moisture/latest` | `sensor.router` (path is absolute in the decorator) |

All match the API the task and the existing frontend expect.

### `/api/optimize` — real request schema (`schemas/input_schema.py`)

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
Only `material_name`, `weight_kg`, `moisture_condition` are required by the schema; everything else is optional with defaults. **In practice `waste_type` should be supplied** — the Decision Tree step (`load_models.predict_method`) calls `encoders["category"].transform([waste_type])`, and passing `None` will raise an encoder error. `process_plan_service.py` has a separate fallback that fills in `waste_type` from a training CSV when absent, but that fallback only runs *after* the Decision Tree step already needed it.

### `/api/optimize` — real response schema (`schemas/output_schema.py`)

Input echo (`material_name`, `waste_type`, `weight_kg`, `moisture_condition`) plus:
- **Decision Tree**: `recommended_method` (`"Mechanical"` or `"Thermal"`)
- **MCDM**: `optimal_temp_c`, `processing_time_min`, `energy_kwh`, `recycling_efficiency_pct`
- **Rule-based safety**: `safety_status`, `pre_drying_required`, `toxicity_level`
- Pre-drying detail (when required): `pre_drying_temp_c`, `pre_drying_time_min`, `pre_drying_action`
- Chemical agent info: `chemical_agent`, `chemical_concentration`, `chemical_purpose`, `handling_note`
- Cooling: `cooling_time_min`, `cooling_method`, `target_temp_c`
- Metadata: `batch_id`, `timestamp`, `doc_id` (Firestore document id)

No fields beyond what the real code returns are documented here.

## Database / storage

**Firestore** (Google Cloud), via `firebase-admin`, initialized in `app/config.py` from `app/firebase_key.json`. Two collections: `optimization_requests` (raw input log) and `optimization_results` (full recipe + timestamp, read back by `/api/history`). If the key file is missing or Firebase init fails, `firestore_service.py` catches the error and returns `None`/`[]` — **`/api/optimize` still returns a full result even without Firestore**, it just can't persist or list history. No local database (no SQLite, no relational DB) — this is a clean break from the old (wrong) backend's SQLite usage.

## Environment variables

**None.** `config.py` reads no environment variables at all — it locates `firebase_key.json` by a fixed path relative to itself. There is no `.env` / `.env.example` for this backend (the old ones were removed along with the wrong backend and nothing replaced them, since there's nothing to configure).

## IoT / moisture handling

- `moisture_condition` is normally supplied by the caller (manual form input), per the request schema.
- **Exception**: for `waste_type == "Plastic"` specifically, `optimize.py` overrides the caller's `moisture_condition` with a live reading from `app/api/routes/sensor.py`'s in-memory `latest_sensor_data`, if one has been received. That module exposes `POST /api/sensor/moisture` for an ESP32 (SHEF capacitive moisture sensor) to push readings, and `GET /api/sensor/moisture/latest` for the frontend to poll the current value. The response's `moisture_source` field (`"sensor"` or `"manual"`) tells you which path was used.
- Sensor state is **in-memory only** (a plain dict) — it resets on every server restart, and is not persisted to Firestore itself.

## Frontend compatibility

**Already fully compatible — no frontend changes made.** `component-3/frontend/src/services/api.js` calls exactly `${BASE_URL}/api/{optimize,history,health,materials}` and `${BASE_URL}/api/sensor/moisture/latest`, where `BASE_URL` defaults to `http://127.0.0.1:8003` (and `component-3/frontend/.env` already sets `REACT_APP_API_BASE_URL=http://localhost:8003`). Every one of those paths matches a route this real backend actually registers. The frontend was evidently built against this real backend from the start — it was the backend that was wrong, not the frontend.

## Docker status

- `component-3/backend/Dockerfile` — entry point/port unchanged (`uvicorn app.main:app --host 0.0.0.0 --port 8003`), `COPY app/` + `requirements.txt` only (no `knowledge_base/`/`ml_models/` — those belonged to the old backend and no longer exist), healthcheck path `/api/health`.
- `component-3/backend/.dockerignore` — excludes `app/firebase_key.json` explicitly, so the real credential is never baked into the image even though it sits inside `app/` on disk.
- **`docker-compose.yml` updated (Step 5B):** removed the stale `DATABASE_URL` environment variable and the `component3-db-data` SQLite volume (both belonged to the old backend and are meaningless for Firestore). Added a read-only bind mount, `./component-3/backend/app/firebase_key.json:/app/app/firebase_key.json:ro`, so the real credential can be supplied to the container at runtime without ever being copied into the image or committed to git. If that file doesn't exist on the host machine, Docker creates an empty directory at the mount target instead of failing — the backend's existing Firebase-init error handling then degrades gracefully (logs an error, disables persistence) rather than crashing, exactly as it does when run outside Docker without the key.
- `docker compose build component3` / `up -d component3` — **not run**. Docker is not available in this sandbox (confirmed absent from both Bash and PowerShell in Steps 5A and 5B). Verified instead by running the real backend directly with `uvicorn` and by running the gateway locally against it — see the contract doc's confirmed responses.

## Known gaps (discovered, not fabricated or fixed)

1. **`component3_training_v2.csv` is missing.** `process_plan_service.py` looks for it in `app/data/` or `../../../ml_training/material_model/dataset/` to build `waste_type`/`toxicity` lookup maps; neither path exists in this repo. The code has an explicit fallback hardcoded map and logs `"WARNING: training CSV not found — using fallback map"` — confirmed in the live server log. It does not crash, but the fallback map only covers 14 materials, a superset of (but not verified identical to) the 8 in `/api/materials`.
2. **`model.pkl` etc. were trained with scikit-learn 1.8.0**, but `requirements.txt` pins `scikit-learn==1.3.2`. Loading works and predictions are produced, but scikit-learn logs an `InconsistentVersionWarning` on every startup. Not fixed here (a version/dependency change is outside this step's "don't change business logic" scope) — flagging for you to decide whether to re-pin or retrain.
3. **`app/main.py` registers each of `optimize`, `history`, `health`, `materials` twice** — once with `prefix="/api"`, then again (plus `sensor`) with no prefix, via a duplicated import block that reads as a copy-paste edit (complete with an inline Sinhala comment marking where `sensor` was added). This creates harmless duplicate routes at the un-prefixed paths (e.g. `/health` in addition to `/api/health`) but does not break the required `/api/*` endpoints. Not fixed here, since it isn't required for port-8003 compatibility — flagging it since it's clearly unintentional.
4. **A stray `component-3/backend/app/services/api.js`** exists — a near-duplicate of the frontend's own `api.js`, hardcoded to `http://localhost:8000/api` (an old, wrong port). It's inert (Python never imports `.js` files) but will get copied into the Docker image by `COPY app/ ./app/`. Left in place, not deleted, since it causes no functional problem and wasn't asked for.
5. **`GET /api/health` returns `{"status": "ok", ...}`**, not `{"status": "healthy"}` as assumed in the task description. Documented as the real, actual response — not changed to match the assumption.

## Historical note

`integration/contracts/component3-contract.md` and `integration/INTEGRATION_STATUS.md` were updated in Step 5B to describe this real backend instead of the previous (wrong) one.
