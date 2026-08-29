"""
routers/iot.py
-----------------
The IoT hardware described in your proposal (ESP32 + TCS34725 + load cell +
HC-SR04 + servos) has NOT been built yet. This router defines the contract
it will POST to once it exists, so the backend is ready ahead of the
hardware rather than the other way around. Nothing here talks to real
hardware -- there is none yet.

POST /api/iot/ingest
    Body: {device_id, bin_id, weight_kg, color: {r,g,b,lux}, known_material?}
    - If `known_material` is supplied (e.g. entered by an operator on the
      dashboard, or eventually handed off from Component 1/2's own
      classifier), it's used directly -- this is the recommended path.
    - Otherwise, a DELIBERATELY MINIMAL colour heuristic is applied: your
      own design doc calls out "TCS34725 ... verifies reddish Copper", so
      that specific case (high R, low G/B, decent brightness) is
      implemented. A bright, near-neutral-grey reading is guessed as bare
      Aluminium. Anything else is NOT guessed -- three colour channels
      genuinely cannot distinguish most e-waste materials (that's Component
      1/2's job, or an operator's), so the endpoint returns a 422 asking
      for `known_material` rather than silently fabricating a
      classification. Replace `_classify_by_color` wholesale once the real
      classifier exists.

POST /api/iot/bin-status
    Body: {bin_id, distance_cm, full_threshold_cm}
    Ultrasonic reading -> lockout flag. Crossing into "full" is logged;
    the actual PDF is generated on request via GET /api/manifest/pdf
    (see routers/manifest.py), not held in memory here.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from schemas import IoTIngestPayload, BinStatusPayload, DispositionRequest, ForecastRequest
from materials_db import resolve_material, OUT_OF_SCOPE_METALS
from services.forecast_service import calculate_forecast
from services.disposition_service import calculate_disposition
from services import manifest_service

router = APIRouter()

_bin_state: dict[str, dict] = {}

# Most recent scan, kept so the dashboard's live terminal view has
# something to poll. Only ever one entry -- this is a "what just
# happened" window, not a history; the manifest ledger is the history.
_last_scan: dict | None = None

# Gate angles match RoutingGateTest.ino so the firmware and the bench
# test agree on where each bin sits. Tune both together if the chute
# geometry changes.
_GATE_MARKET = 30
_GATE_COMPACTOR = 90
_GATE_PYROLYSIS = 150


def _actuator_for(decision: str) -> dict:
    """
    Maps a decision onto the physical actions the ESP32 has to take.
    Doing this server-side keeps the firmware dumb -- it just obeys,
    rather than duplicating the routing rules in C++ where they would
    drift out of step with the backend.

    LED colours follow report section 6.1: green = SELL, yellow = HOLD /
    crushing, red = bin full. Red is deliberately NOT issued here -- it
    belongs to the bin-full lockout, not to any scan outcome.
    """
    if decision == "SELL NOW":
        return {"led": "green", "gate_angle": _GATE_MARKET, "crush": False, "beep_ms": 120}
    if decision == "HOLD":
        return {"led": "yellow", "gate_angle": _GATE_COMPACTOR, "crush": True, "beep_ms": 120}
    # Polymers have no sell/hold question -- they are routed onward to
    # pyrolysis. Green reads as "dispatched", consistent with SELL.
    return {"led": "green", "gate_angle": _GATE_PYROLYSIS, "crush": False, "beep_ms": 120}


def _classify_by_color(color) -> str | None:
    """Minimal, explicitly-limited placeholder -- see module docstring."""
    if color is None:
        return None
    r, g, b, lux = color.r, color.g, color.b, color.lux
    brightness = (r + g + b) / 3
    if lux < 5:  # nothing on the scale bed
        return None
    if r > 140 and r > g * 1.3 and r > b * 1.3:
        return "copper"
    if brightness > 170 and abs(r - g) < 20 and abs(g - b) < 20:
        return "aluminium"
    return None


@router.post("/ingest")
def ingest_telemetry(payload: IoTIngestPayload, compact: bool = False) -> dict:
    """
    `compact=true` returns only what an ESP32 needs to act on -- a few
    hundred bytes instead of the full response, which embeds a 90-point
    forecast series (~14 KB) that exists purely to draw the dashboard's
    chart. A microcontroller has no use for it and parsing it wastes
    memory it does not have. The dashboard keeps calling this endpoint
    without the flag and is unaffected.
    """
    material = payload.known_material or _classify_by_color(payload.color)
    if material is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "Could not confidently classify this reading from colour alone "
                "(this endpoint's colour heuristic only recognises reddish-copper "
                "and bright-neutral-aluminium). Pass `known_material` explicitly, "
                "e.g. from an operator entry or Component 1/2's classifier."
            ),
        )

    key = material.strip().lower()
    if key in OUT_OF_SCOPE_METALS:
        raise HTTPException(status_code=400, detail=f"'{material}' is out of scope for this component.")

    try:
        route, _ = resolve_material(material)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    global _last_scan
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    locked = _bin_state.get(payload.bin_id or "bin-01", {}).get("locked", False)

    if route == "recyclable_metal":
        forecast = calculate_forecast(ForecastRequest(metal=material, weight_kg=payload.weight_kg))
        manifest_service.log_forecast(forecast)

        decision = forecast.recommendation
        summary = {
            "classified_as": material,
            "decision": decision,
            "price_lkr_per_kg": forecast.unit_price_lkr,
            "value_lkr": forecast.profit_if_sell_lkr or forecast.expected_peak_price_lkr,
            "weight_kg": forecast.weight_kg,
            "actuator": _actuator_for(decision),
            "locked": locked,
            "at": now_iso,
        }
        _last_scan = summary
        return summary if compact else {
            "classified_as": material, "endpoint": "forecast", "result": forecast
        }

    disposition = calculate_disposition(
        DispositionRequest(
            waste_type=material,
            weight_kg=payload.weight_kg,
            latitude=payload.latitude,
            longitude=payload.longitude,
        )
    )
    manifest_service.log_disposition(disposition)

    summary = {
        "classified_as": material,
        "decision": "PYROLYSIS",
        "energy_kwh": disposition.energy_recovery_kwh,
        "value_lkr": disposition.estimated_revenue_lkr,
        "weight_kg": disposition.weight_kg,
        "facility": disposition.nearest_treatment_facility.name if disposition.nearest_treatment_facility else None,
        "actuator": _actuator_for("PYROLYSIS"),
        "locked": locked,
        "at": now_iso,
    }
    _last_scan = summary
    return summary if compact else {
        "classified_as": material, "endpoint": "disposition", "result": disposition
    }


@router.get("/last-scan")
def get_last_scan() -> dict:
    """
    The most recent scan, for the dashboard's live terminal view to poll.
    Returns `{"scan": null}` before anything has been scanned so the page
    can show a "waiting for item" state rather than erroring.
    """
    return {"scan": _last_scan}


@router.post("/bin-status")
def bin_status(payload: BinStatusPayload) -> dict:
    is_full = payload.distance_cm < payload.full_threshold_cm
    previous = _bin_state.get(payload.bin_id, {"locked": False})

    _bin_state[payload.bin_id] = {"locked": is_full, "distance_cm": payload.distance_cm}

    just_locked = is_full and not previous["locked"]
    return {
        "bin_id": payload.bin_id,
        "locked": is_full,
        "just_locked": just_locked,
        "message": (
            "SYSTEM LOCKOUT: DISPATCH REQUIRED -- manifest ready at GET /api/manifest/pdf"
            if is_full
            else "OK"
        ),
    }


@router.get("/bin-status/{bin_id}")
def get_bin_status(bin_id: str) -> dict:
    return _bin_state.get(bin_id, {"locked": False, "distance_cm": None})
