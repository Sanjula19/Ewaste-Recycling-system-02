"""
TRIAL_FORCE_DECISION -- the bench-trial decision override.

Two things have to hold, and they pull in opposite directions:

  ON   every response and every manifest entry is marked forced, and the
       decision and actuator are the forced ones, so an actuation test can
       be run on demand instead of waiting for the market to produce a
       HOLD.

  OFF  the behaviour is byte-for-byte what it was. In particular the
       compact response must not gain a `forced` key, because an ESP32
       parses it with a fixed-size ArduinoJson buffer and
       tests/test_iot_compact_contract.py pins its size.

The second is the one worth guarding: a trial feature that quietly
changes the firmware contract when switched off would be worse than not
having it.
"""

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from routers import iot  # noqa: E402
from schemas import IoTIngestPayload  # noqa: E402
from services import manifest_service  # noqa: E402


@pytest.fixture(autouse=True)
def pinned_fx(monkeypatch):
    from services import fx_service
    monkeypatch.setattr(fx_service, "get_fx_rates", lambda: {
        "usd_lkr": 300.0, "usd_inr": 90.0,
        "as_of": "2026-01-01T00:00:00Z", "source": "fallback"})


@pytest.fixture(autouse=True)
def clean_ledger():
    """Each test reads only its own entries."""
    manifest_service.reset()
    yield
    manifest_service.reset()


@pytest.fixture(autouse=True)
def forcing_off_by_default(monkeypatch):
    monkeypatch.delenv("TRIAL_FORCE_DECISION", raising=False)


def _ingest(material="copper", weight=2.5, compact=True):
    return iot.ingest_telemetry(
        IoTIngestPayload(device_id="bench", weight_kg=weight, known_material=material),
        compact=compact,
    )


def _entries():
    return manifest_service.summary()["entries"]


# ----------------------------------------------------------------- parsing

def test_unset_and_empty_mean_off(monkeypatch):
    assert iot.trial_force_decision() is None
    monkeypatch.setenv("TRIAL_FORCE_DECISION", "")
    assert iot.trial_force_decision() is None
    monkeypatch.setenv("TRIAL_FORCE_DECISION", "   ")
    assert iot.trial_force_decision() is None


@pytest.mark.parametrize("raw,expected", [
    ("HOLD", "HOLD"), ("hold", "HOLD"), ("  HoLd  ", "HOLD"),
    ("SELL", "SELL NOW"), ("sell", "SELL NOW"), ("SELL NOW", "SELL NOW"),
])
def test_accepted_values(monkeypatch, raw, expected):
    monkeypatch.setenv("TRIAL_FORCE_DECISION", raw)
    assert iot.trial_force_decision() == expected


@pytest.mark.parametrize("raw", ["PYROLYSIS", "yes", "1", "true", "HOLD ON", "SEL"])
def test_unrecognised_value_raises_rather_than_falling_back_to_off(monkeypatch, raw):
    """
    A typo must not read as "off". An operator who believes forcing is on
    would otherwise record real model decisions as forced trials, which is
    the exact contamination this flag exists to prevent.
    """
    monkeypatch.setenv("TRIAL_FORCE_DECISION", raw)
    with pytest.raises(ValueError) as exc:
        iot.trial_force_decision()
    assert "TRIAL_FORCE_DECISION" in str(exc.value)


# --------------------------------------------------------------------- off

def test_off_adds_no_forced_key_anywhere(monkeypatch):
    compact = _ingest(compact=True)
    assert "forced" not in compact
    full = _ingest(compact=False)
    assert "forced" not in full


def test_off_leaves_the_decision_to_the_model(monkeypatch):
    compact = _ingest()
    assert compact["decision"] in ("SELL NOW", "HOLD")
    # And the actuator matches that decision, not a forced one.
    assert compact["actuator"] == iot._actuator_for(compact["decision"])


def test_off_marks_no_manifest_entry_forced():
    _ingest()
    entries = _entries()
    assert len(entries) == 1
    assert entries[0]["forced"] is False
    assert manifest_service.summary()["forced_entries"] == 0


def test_off_compact_response_keys_and_order_are_unchanged(monkeypatch):
    """
    The firmware's wire contract. test_iot_compact_contract.py pins this
    against a recorded golden; this asserts the trial flag did not disturb
    it while off.
    """
    compact = _ingest()
    assert list(compact.keys()) == [
        "classified_as", "decision", "price_lkr_per_kg", "value_lkr",
        "weight_kg", "actuator", "locked", "at",
    ]


# ---------------------------------------------------------------------- on

@pytest.mark.parametrize("raw,expected", [("HOLD", "HOLD"), ("SELL", "SELL NOW")])
def test_on_returns_the_forced_decision(monkeypatch, raw, expected):
    monkeypatch.setenv("TRIAL_FORCE_DECISION", raw)
    compact = _ingest()
    assert compact["decision"] == expected
    assert compact["forced"] is True


def test_on_returns_the_actuator_for_the_forced_decision(monkeypatch):
    """A forced HOLD must actually drive the crusher -- that is the point."""
    monkeypatch.setenv("TRIAL_FORCE_DECISION", "HOLD")
    hold = _ingest()
    assert hold["actuator"] == iot._actuator_for("HOLD")
    assert hold["actuator"]["crush"] is True
    assert hold["actuator"]["led"] == "yellow"

    monkeypatch.setenv("TRIAL_FORCE_DECISION", "SELL")
    sell = _ingest()
    assert sell["actuator"] == iot._actuator_for("SELL NOW")
    assert sell["actuator"]["crush"] is False
    assert sell["actuator"]["led"] == "green"


def test_on_marks_the_full_response_too(monkeypatch):
    monkeypatch.setenv("TRIAL_FORCE_DECISION", "HOLD")
    assert _ingest(compact=False)["forced"] is True


def test_on_marks_the_manifest_entry_and_books_no_value(monkeypatch):
    monkeypatch.setenv("TRIAL_FORCE_DECISION", "SELL")
    _ingest()
    entries = _entries()
    assert len(entries) == 1
    e = entries[0]
    assert e["forced"] is True
    assert "FORCED TRIAL" in e["route_or_recommendation"]
    # A forced trial realised nothing. Letting it contribute to the cycle
    # total is the mixing the flag exists to prevent.
    assert e["value_lkr"] == 0.0
    s = manifest_service.summary()
    assert s["forced_entries"] == 1
    assert s["total_value_lkr"] == 0.0


def test_on_records_what_the_rig_did_not_what_the_model_said(monkeypatch):
    """
    Forced SELL streams as metal_sale and forced HOLD as metal_hold,
    regardless of the model, because that is what physically happened.
    """
    monkeypatch.setenv("TRIAL_FORCE_DECISION", "HOLD")
    _ingest()
    assert _entries()[0]["stream"] == "metal_hold"

    manifest_service.reset()
    monkeypatch.setenv("TRIAL_FORCE_DECISION", "SELL")
    _ingest()
    assert _entries()[0]["stream"] == "metal_sale"


def test_on_still_marks_a_polymer_even_though_the_decision_is_unchanged(monkeypatch):
    """
    Forcing SELL/HOLD on a polymer is meaningless, so PYROLYSIS stands --
    but while the flag is on nothing from this endpoint is a clean record,
    so it is still marked.
    """
    monkeypatch.setenv("TRIAL_FORCE_DECISION", "HOLD")
    out = _ingest(material="polystyrene")
    assert out["decision"] == "PYROLYSIS"
    assert out["forced"] is True
    assert _entries()[0]["forced"] is True
    assert manifest_service.summary()["forced_entries"] == 1


def test_forced_and_real_entries_are_distinguishable_in_one_cycle(monkeypatch):
    """
    The worst case the flag guards against: a session where someone forgot
    to switch it off partway. Both rows must still be separable.
    """
    _ingest()                                             # real
    monkeypatch.setenv("TRIAL_FORCE_DECISION", "HOLD")
    _ingest()                                             # forced
    monkeypatch.delenv("TRIAL_FORCE_DECISION")
    _ingest()                                             # real again

    entries = _entries()
    assert [e["forced"] for e in entries] == [False, True, False]
    assert manifest_service.summary()["forced_entries"] == 1
