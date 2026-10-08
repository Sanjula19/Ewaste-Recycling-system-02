"""
The compact IoT response is a wire contract with firmware.

POST /api/iot/ingest?compact=true is what the ESP32 parses with a
fixed-size ArduinoJson buffer. Adding, renaming, reordering or inflating a
field there means reflashing the device, so this compares the live response
against a golden recorded from the shipped behaviour (tests/data/
iot_compact_golden.json) rather than trusting review to catch it.

Values are expected to change -- that is what the decision logic is for.
The field names, their order, the nested actuator keys and the overall size
are what must not.
"""

import json
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

GOLDEN_PATH = BACKEND / "tests" / "data" / "iot_compact_golden.json"
SIZE_TOLERANCE_BYTES = 120   # a decision flip swaps which value field is populated


@pytest.fixture(autouse=True)
def pinned_model_dir(monkeypatch):
    """
    Serve the contract from a known folder rather than whatever MODEL_DIR the
    shell happens to export, so the size assertions are about the response
    and not about the environment. Falls back to the default folder when
    models_v2/ has not been built -- the contract holds for both.
    """
    from services import forecast_service
    if (BACKEND / "models_v2" / "meta_nickel.json").is_file():
        monkeypatch.setenv("MODEL_DIR", "models_v2")
    forecast_service.clear_cache()
    yield
    forecast_service.clear_cache()


@pytest.fixture
def pinned_fx(monkeypatch):
    from services import fx_service
    monkeypatch.setattr(fx_service, "get_fx_rates", lambda: {
        "usd_lkr": 300.0, "usd_inr": 90.0,
        "as_of": "2026-01-01T00:00:00Z", "source": "fallback"})


@pytest.fixture
def golden():
    if not GOLDEN_PATH.is_file():
        pytest.skip("compact golden not recorded")
    return json.loads(GOLDEN_PATH.read_text())


def _compact(metal, weight_kg=12.5):
    from routers.iot import ingest_telemetry
    from schemas import IoTIngestPayload

    out = dict(ingest_telemetry(
        IoTIngestPayload(device_id="esp32-01", bin_id="bin-01",
                         weight_kg=weight_kg, known_material=metal),
        compact=True))
    out.pop("at")          # a timestamp, never stable
    return out


@pytest.mark.parametrize("metal", ["nickel", "copper"])
def test_field_names_and_order_are_unchanged(golden, pinned_fx, metal):
    if metal not in golden:
        pytest.skip(f"{metal} not in golden")
    live = _compact(metal)
    assert list(live.keys()) == golden[metal]["keys_in_order"]
    assert list(live["actuator"].keys()) == golden[metal]["actuator_keys_in_order"]


@pytest.mark.parametrize("metal", ["nickel", "copper"])
def test_types_are_unchanged(golden, pinned_fx, metal):
    if metal not in golden:
        pytest.skip(f"{metal} not in golden")
    live, ref = _compact(metal), golden[metal]["value"]
    for k, expected in ref.items():
        if isinstance(expected, dict):
            for ak, av in expected.items():
                assert type(live[k][ak]) is type(av), f"actuator.{ak} type changed"
        else:
            # value_lkr swaps between profit and peak figures with the
            # decision, but stays a number either way.
            assert type(live[k]) is type(expected) or (
                isinstance(expected, (int, float)) and isinstance(live[k], (int, float))
            ), f"{k} type changed"


@pytest.mark.parametrize("metal", ["nickel", "copper"])
def test_size_stays_in_the_firmware_s_budget(golden, pinned_fx, metal):
    if metal not in golden:
        pytest.skip(f"{metal} not in golden")
    live = len(json.dumps(_compact(metal)))
    ref = len(json.dumps(golden[metal]["value"]))
    assert abs(live - ref) <= SIZE_TOLERANCE_BYTES, (
        f"compact response went from {ref} to {live} bytes")
    assert live < 512, "compact response must stay well under a 512-byte buffer"


def test_full_response_only_gained_fields(pinned_fx):
    """The non-compact response may grow, never shrink or rename."""
    from routers.iot import ingest_telemetry
    from schemas import IoTIngestPayload

    full = ingest_telemetry(
        IoTIngestPayload(device_id="esp32-01", weight_kg=12.5, known_material="nickel"),
        compact=False)
    assert set(full.keys()) == {"classified_as", "endpoint", "result"}
    body = full["result"].model_dump()
    pre_existing = {
        "metal", "current_price", "current_price_lkr", "forecast_90d",
        "recommendation", "recommendation_reason", "profit_if_sell",
        "profit_if_sell_lkr", "expected_peak_price", "expected_peak_price_lkr",
        "expected_peak_date", "mape", "rmse", "model_used", "weight_kg",
        "unit_price", "unit_price_lkr", "operator_action",
        "operator_action_note", "fx",
    }
    assert pre_existing <= set(body), "a pre-existing response field disappeared"
    assert {"persistence_mape", "signal"} <= set(body)


def test_hold_actuator_shape_is_preserved():
    """
    No metal currently earns a HOLD, so the yellow/crush branch is exercised
    directly -- it is still live code the firmware must handle.
    """
    from routers.iot import _actuator_for

    hold = _actuator_for("HOLD")
    assert list(hold.keys()) == ["led", "gate_angle", "crush", "beep_ms"]
    assert hold == {"led": "yellow", "gate_angle": 90, "crush": True, "beep_ms": 120}
