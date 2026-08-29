# Component 3 Contract — Smart Process Optimization (Wisu)

> **EXPECTED C3 CONTRACT — implementation currently unavailable in this repository.**
>
> Everything below describes the interface Component 3 is *supposed* to expose,
> as specified for Step 5 integration and as already assumed by Component 3's
> own frontend code (`component-3/frontend/src/services/api.js`,
> `component-3/frontend/src/components/InputForm.jsx`). **No backend in this
> repository implements it.**
>
> The code currently sitting at `component-3/backend/` is a copy of the
> Component 2 toxic-gas-detection backend (`/api/v1/health`,
> `/api/v1/readings`, `/api/v1/predict` for gas classification, etc.) and is
> **not** the Smart Process Optimization service. Do not call it expecting
> the contract below — it will 404 or return unrelated gas-sensor data.
>
> The real implementation is intended to live at
> `https://github.com/visuddika/Recerch_Smart-process-optimization-System.git`
> (branch `main`), but as of this writing that repository is empty (no
> commits). Step 5 orchestration cannot be built against Component 3 until
> real code exists there.

Base URL (local, once real): `http://localhost:8003`

---

## GET /api/health *(expected)*

Expected to return a simple service-alive payload, analogous to Component 1/4's health checks. Exact shape unconfirmed.

---

## GET /api/materials *(expected)*

Expected to return the list of materials the optimization engine actually supports (used by the frontend's material picker). Exact shape unconfirmed — must be used to validate `material_name` before calling `/api/optimize` once real.

---

## POST /api/optimize *(expected)*

**Expected request:**
```json
{
  "material_name": "PET Water Bottles",
  "weight_kg": 5.0,
  "moisture_condition": "Wet"
}
```

| Field | Type | Notes |
|---|---|---|
| `material_name` | string | Must be a value returned by `/api/materials` — not to be invented |
| `weight_kg` | float | Unit assumed kg per the field name; unconfirmed against real implementation |
| `moisture_condition` | string | Expected values seen in the existing frontend: `"Dry"` / `"Wet"` (`InputForm.jsx`) |

**Expected response:** unconfirmed. The existing frontend (`ResultCard.jsx`) implies a "process recipe" style result, but the exact field names have not been confirmed against a real backend.

---

## GET /api/history *(expected)*

Expected to return previously computed optimization results. Exact shape unconfirmed.

---

## Open questions (cannot be answered without the real implementation)

- How is `moisture_condition` obtained — supplied by the caller, or read internally from a physical moisture/SHEF sensor?
- Exact response schema of `/api/optimize` (recipe fields, decision logic outputs, MCDM/rule-engine results, etc.)
- Database/storage used for `/api/history`
- Required environment variables
- Whether the current `component-3/frontend/` is actually compatible with the real backend once it exists, or was built against a differently-shaped assumed contract

These must be re-inspected once real Component 3 code is available, per `integration/INTEGRATION_STATUS.md`.
