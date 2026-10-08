"""
Change 3 was a pure efficiency change: preload artifacts at startup, call
the LSTM directly instead of through predict() in the 90-step recursive
loop, and key the cache on the latest price date. None of that may move a
number.

results_v2/forecast_baseline_pre_change3.json was recorded immediately
before those edits (scripts/forecast_snapshot.py). This recomputes every
figure -- 90 forecast points with bounds, both MAPEs, the decision, the
operator action -- and compares to 1e-6.

Also covers the cache itself: a forecast must be reused while the latest
price date is unchanged, and recomputed as soon as it moves.
"""

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

BASELINE = BACKEND / "results_v2" / "forecast_baseline_pre_change3.json"
TOL = 1e-6


def _diffs(path, expected, actual, out):
    if isinstance(expected, bool) or isinstance(actual, bool):
        if expected != actual:
            out.append((path, expected, actual))
    elif isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        if math.isnan(expected) != math.isnan(actual):
            out.append((path, expected, actual))
        elif not math.isnan(expected) and abs(expected - actual) > TOL:
            out.append((path, expected, actual))
    elif isinstance(expected, dict):
        for k in set(expected) | set(actual or {}):
            _diffs(f"{path}.{k}", expected.get(k), (actual or {}).get(k), out)
    elif isinstance(expected, list):
        if len(expected) != len(actual or []):
            out.append((path, f"len {len(expected)}", f"len {len(actual or [])}"))
        else:
            for i, (e, a) in enumerate(zip(expected, actual)):
                _diffs(f"{path}[{i}]", e, a, out)
    elif expected != actual:
        out.append((path, expected, actual))


@pytest.fixture(scope="module")
def baseline():
    if not BASELINE.is_file():
        pytest.skip("pre-Change-3 baseline not recorded")
    return json.loads(BASELINE.read_text())


def test_every_forecast_figure_is_unchanged(baseline, monkeypatch):
    monkeypatch.setenv("MODEL_DIR", baseline["model_dir"])
    from services import forecast_service
    from forecast_snapshot import snapshot

    forecast_service.clear_cache()
    current = snapshot(list(baseline["metals"].keys()))

    out = []
    for metal, expected in baseline["metals"].items():
        _diffs(metal, expected, current["metals"].get(metal), out)
    assert not out, "forecast output changed:\n" + "\n".join(
        f"  {p}: {e!r} -> {a!r}" for p, e, a in out[:20])


def test_baseline_actually_covers_the_numbers(baseline):
    """Guards against the comparison above passing on an empty snapshot."""
    assert len(baseline["metals"]) == 6
    for metal, row in baseline["metals"].items():
        assert len(row["series"]) == 90, metal
        assert row["mape"] is not None
        assert row["recommendation"] in {"SELL NOW", "HOLD"}


# ------------------------------------------------------------------- cache

def _history(dates, values):
    return pd.Series([float(v) for v in values], index=pd.to_datetime(dates))


@pytest.fixture
def counting_model(monkeypatch):
    from services import forecast_service as fs

    calls = []

    def fake(metal):
        calls.append(metal)
        mean = np.linspace(10.0, 11.0, fs.HORIZON_DAYS)
        return (fs.ForecastPath(mean=mean, lower=mean - 1, upper=mean + 1,
                                model_used="stub", persistence_mape=9.0), 1.0, 0.1)

    monkeypatch.setattr(fs, "_select_pretrained_forecast", fake)
    fs.clear_cache()
    yield fs, calls
    fs.clear_cache()


def test_same_latest_date_is_served_from_cache(counting_model):
    fs, calls = counting_model
    h = _history(["2024-08-27", "2024-08-28", "2024-08-29"], [1, 2, 3])
    for _ in range(5):
        fs._model_path_cached("nickel", h)
    assert len(calls) == 1


def test_new_latest_date_invalidates(counting_model):
    fs, calls = counting_model
    h1 = _history(["2024-08-27", "2024-08-28", "2024-08-29"], [1, 2, 3])
    h2 = _history(["2024-08-27", "2024-08-28", "2024-08-29", "2024-08-30"], [1, 2, 3, 4])
    fs._model_path_cached("nickel", h1)
    fs._model_path_cached("nickel", h1)
    assert len(calls) == 1
    fs._model_path_cached("nickel", h2)
    assert len(calls) == 2, "a new daily price must force a recompute"
    fs._model_path_cached("nickel", h2)
    assert len(calls) == 2


def test_backfill_at_same_last_date_invalidates(counting_model):
    """Same last date, more observations -- history was rewritten."""
    fs, calls = counting_model
    h1 = _history(["2024-08-28", "2024-08-29"], [2, 3])
    h2 = _history(["2024-08-26", "2024-08-27", "2024-08-28", "2024-08-29"], [1, 1, 2, 3])
    fs._model_path_cached("nickel", h1)
    fs._model_path_cached("nickel", h2)
    assert len(calls) == 2


def test_model_dir_is_part_of_the_key(counting_model, monkeypatch):
    fs, calls = counting_model
    h = _history(["2024-08-28", "2024-08-29"], [2, 3])
    monkeypatch.setenv("MODEL_DIR", "models")
    fs._model_path_cached("nickel", h)
    monkeypatch.setenv("MODEL_DIR", "models_v2")
    fs._model_path_cached("nickel", h)
    assert len(calls) == 2, "switching MODEL_DIR must not reuse the other folder's forecast"


def test_cache_holds_one_entry_per_metal(counting_model):
    """A moving date must replace a metal's entry, not pile up beside it."""
    fs, _ = counting_model
    for day in range(1, 8):
        fs._model_path_cached("nickel", _history(
            [f"2024-08-{day:02d}", f"2024-08-{day + 1:02d}"], [1, 2]))
    assert len(fs._model_cache) == 1


# ------------------------------------------------- preload / direct call

def test_warmup_loads_every_artifact(monkeypatch):
    from services import pretrained_models as pm

    monkeypatch.setenv("MODEL_DIR", "models_v2")
    if not (BACKEND / "models_v2" / "arima_nickel.pkl").is_file():
        pytest.skip("models_v2/ not built")
    pm.clear_cache()
    loaded = pm.warmup(["nickel"])
    assert set(loaded["nickel"]) == {"arima", "lstm", "scaler", "meta"}
    assert pm._registry, "warmup must leave the artifacts in the registry"


def test_direct_call_matches_predict(monkeypatch):
    """
    The 90-step loop swapped model.predict() for a traced direct call. Both
    run the same inference-mode graph in float32, so a one-step prediction
    must agree exactly, not approximately.
    """
    from services import pretrained_models as pm

    monkeypatch.setenv("MODEL_DIR", "models_v2")
    pm.clear_cache()
    model = pm._load_lstm_model("nickel")
    if model is None:
        pytest.skip("models_v2/ LSTM not available")

    scaler, raw = pm._fit_matching_scaler("nickel")
    window = scaler.transform(raw.to_numpy().reshape(-1, 1))[-pm.WINDOW_SIZE:]
    x = window.reshape(1, pm.WINDOW_SIZE, 1)

    via_predict = float(model.predict(x, verbose=0)[0, 0])
    via_call = float(pm._lstm_step_fn("nickel", model)(x.astype(np.float32)).numpy()[0, 0])
    assert via_call == via_predict
