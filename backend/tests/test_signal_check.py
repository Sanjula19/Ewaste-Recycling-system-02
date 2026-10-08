"""
Change 1 -- the "no forecastable signal" check.

A model that cannot beat a no-change forecast on the holdout its MAPE came
from has shown no predictive signal, so a HOLD off its 90-day path is not
evidence-based. These tests pin that gate, including that it cannot fire
when there is no baseline to compare against.

The synthetic path below is deliberately one that WOULD earn a HOLD: a
rising forecast whose lower 95% bound at the peak clears the tau bar. Only
the persistence baseline changes between the two cases, so anything that
differs in the outcome is the signal check and nothing else.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from services import forecast_service as fs  # noqa: E402
from routers.iot import _actuator_for  # noqa: E402

CURRENT_PRICE = 100.0
LAST_DATE = pd.Timestamp("2024-08-29")
NO_SIGNAL_SENTENCE = (
    "The model does not outperform a no-change forecast on recent data, so "
    "holding is not recommended."
)


def rising_path(persistence_mape):
    """A 90-day forecast rising to 110, lower bound 105 at the peak."""
    mean = np.linspace(100.0, 110.0, fs.HORIZON_DAYS)
    lower = mean - 5.0
    return fs.ForecastPath(mean=mean, lower=lower, upper=mean + 5.0,
                           model_used="ARIMA(1, 1, 1) (pretrained)",
                           persistence_mape=persistence_mape)


# --------------------------------------------------------------- has_signal

@pytest.mark.parametrize("mape, persistence, expected", [
    (2.40, 5.80, True),     # copper: model clearly better than no-change
    (3.13, 2.99, False),    # nickel: model worse than no-change
    (3.36, 3.36, False),    # zinc: ARIMA(0,1,0) IS a random walk -- a tie is not a win
    (1.00, 1.01, True),
])
def test_has_signal_truth_table(mape, persistence, expected):
    assert fs.has_signal(mape, persistence) is expected


@pytest.mark.parametrize("persistence", [None, float("nan")])
def test_no_baseline_means_the_check_cannot_veto(persistence):
    """Missing baseline must not be read as 'no signal'."""
    assert fs.has_signal(3.0, persistence) is True


def test_nan_mape_does_not_veto():
    assert fs.has_signal(float("nan"), 3.0) is True


# ------------------------------------------------- the gate in the decision

def test_signal_true_still_holds():
    rec = fs.generate_recommendation(CURRENT_PRICE, rising_path(5.80), LAST_DATE, mape=1.0)
    assert rec["recommendation"] == "HOLD"
    assert rec["operator_action"] == "CRUSH_AND_COMPRESS"
    assert rec["expected_peak_price"] is not None


def test_signal_false_forces_sell_on_the_same_path():
    rec = fs.generate_recommendation(CURRENT_PRICE, rising_path(0.5), LAST_DATE, mape=1.0)
    assert rec["recommendation"] == "SELL NOW"
    assert rec["recommendation_reason"].startswith(NO_SIGNAL_SENTENCE)
    # Peak figures are withheld: the whole point is that this path is not
    # something to act on.
    assert rec["expected_peak_price"] is None
    assert rec["expected_peak_date"] is None


def test_no_signal_uses_the_normal_sell_actuator():
    rec = fs.generate_recommendation(CURRENT_PRICE, rising_path(0.5), LAST_DATE, mape=1.0)
    assert rec["operator_action"] == "ROUTE_TO_MARKET_SALE"
    assert _actuator_for(rec["recommendation"]) == _actuator_for("SELL NOW")
    assert _actuator_for(rec["recommendation"]) == {
        "led": "green", "gate_angle": 30, "crush": False, "beep_ms": 120}


def test_missing_baseline_leaves_the_hold_intact():
    """Legacy model folders have no persistence figure; HOLD must survive."""
    rec = fs.generate_recommendation(CURRENT_PRICE, rising_path(None), LAST_DATE, mape=1.0)
    assert rec["recommendation"] == "HOLD"


# ------------------------------------------------------------- end to end

@pytest.fixture
def pinned_fx(monkeypatch):
    from services import fx_service
    monkeypatch.setattr(fx_service, "get_fx_rates", lambda: {
        "usd_lkr": 300.0, "usd_inr": 90.0,
        "as_of": "2026-01-01T00:00:00Z", "source": "fallback"})


@pytest.fixture
def v2_models(monkeypatch):
    """
    Pin MODEL_DIR for the tests below instead of inheriting whatever the
    shell exported. Only models_v2/ ships the holdout metrics the signal
    check needs, so letting these read an ambient MODEL_DIR made them pass
    or fail on the environment rather than on the code.
    """
    if not (BACKEND / "models_v2" / "meta_zinc.json").is_file():
        pytest.skip("models_v2/ not built; run scripts/train_production_v2.py")
    monkeypatch.setenv("MODEL_DIR", "models_v2")
    fs.clear_cache()
    yield
    fs.clear_cache()


def _force_persistence(monkeypatch, metal, persistence_mape):
    """Rewrite just the holdout baseline in the loaded training record."""
    from services import pretrained_models as pm
    real = pm.load_training_meta(metal)
    if real is None or "holdout30" not in real:
        pytest.skip("models_v2/ holdout metrics not present")
    patched = dict(real)
    patched["holdout30"] = dict(real["holdout30"], persistence_mape=persistence_mape)
    monkeypatch.setattr(pm, "load_training_meta",
                        lambda m, _p=patched, _t=metal: _p if m == _t else real)
    fs.clear_cache()
    return real


@pytest.mark.parametrize("persistence_mape, expected_signal", [(99.0, True), (0.01, False)])
def test_response_carries_signal_and_persistence(monkeypatch, pinned_fx, v2_models,
                                                 persistence_mape, expected_signal):
    from schemas import ForecastRequest

    _force_persistence(monkeypatch, "nickel", persistence_mape)
    resp = fs.calculate_forecast(ForecastRequest(metal="nickel", weight_kg=100))

    assert resp.signal is expected_signal
    assert resp.persistence_mape == pytest.approx(persistence_mape)
    if not expected_signal:
        assert resp.recommendation == "SELL NOW"
        assert resp.recommendation_reason.startswith(NO_SIGNAL_SENTENCE)
        assert resp.operator_action == "ROUTE_TO_MARKET_SALE"
    fs.clear_cache()


def test_market_overview_item_exposes_signal(monkeypatch, pinned_fx, v2_models):
    from services import market_service

    item = market_service._build_item("zinc", {
        "usd_lkr": 300.0, "usd_inr": 90.0,
        "as_of": "2026-01-01T00:00:00Z", "source": "fallback"})
    assert isinstance(item.signal, bool)
    assert item.persistence_mape is not None
    # zinc's selected ARIMA order is (0,1,0) -- a random walk, which cannot
    # beat the random-walk baseline, so this is the real no-signal case.
    assert item.signal is False
    assert item.recommendation == "SELL NOW"
