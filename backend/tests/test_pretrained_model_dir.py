"""
Covers the MODEL_DIR switch and, more importantly, that inference uses the
scaler SAVED at training time instead of refitting one on the full series.

The refit-vs-load distinction is invisible in today's numbers (the v2
production models are trained on every observation, so a refitted scaler
lands on the same min/max). It stops being invisible the moment the CSVs
gain a new high or low, which is exactly when a silent regression here
would start skewing every forecast. Hence a test that pins the behaviour
with a scaler whose bounds deliberately differ from the data's.
"""

import importlib
import json
import pickle
import sys
from pathlib import Path

import joblib
import pytest
from sklearn.preprocessing import MinMaxScaler

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


@pytest.fixture
def pm():
    import services.pretrained_models as module
    return importlib.reload(module)


def test_default_model_dir_is_models_with_legacy_names(pm, monkeypatch):
    monkeypatch.delenv("MODEL_DIR", raising=False)
    assert Path(pm.models_dir()).resolve() == (BACKEND / "models").resolve()
    assert Path(pm._arima_path("steel")).name == "arima_steel_model.pkl"
    assert Path(pm._lstm_path("steel")).name == "lstm_steel_model.h5"
    # The legacy folder ships no scaler, so the refit fallback stays in play.
    assert pm._scaler_path("steel") is None


def test_models_v2_resolves_new_names_and_extra_artifacts(pm, monkeypatch):
    monkeypatch.setenv("MODEL_DIR", "models_v2")
    if not (BACKEND / "models_v2" / "arima_nickel.pkl").is_file():
        pytest.skip("models_v2/ not built; run scripts/train_production_v2.py")
    assert Path(pm.models_dir()).resolve() == (BACKEND / "models_v2").resolve()
    assert Path(pm._arima_path("nickel")).name == "arima_nickel.pkl"
    assert Path(pm._lstm_path("nickel")).name == "lstm_nickel.keras"
    assert Path(pm._scaler_path("nickel")).name == "scaler_nickel.pkl"
    meta = pm.load_training_meta("nickel")
    assert meta["lstm"]["sd_scaled"] > 0
    assert len(meta["arima_order"]) == 3


def test_saved_scaler_is_loaded_not_refitted(pm, monkeypatch, tmp_path):
    """A saved scaler with bounds unlike the data's must survive unchanged."""
    sentinel = MinMaxScaler(feature_range=(0, 1))
    sentinel.fit([[0.0], [12345.0]])          # nothing like any real series
    joblib.dump(sentinel, tmp_path / "scaler_nickel.pkl")
    monkeypatch.setenv("MODEL_DIR", str(tmp_path))

    scaler, raw = pm._fit_matching_scaler("nickel")

    assert scaler.data_min_[0] == 0.0
    assert scaler.data_max_[0] == 12345.0
    assert raw.min() != 0.0                   # refitting would have used this
    assert not raw.empty


def test_missing_scaler_falls_back_to_refit(pm, monkeypatch, tmp_path):
    monkeypatch.setenv("MODEL_DIR", str(tmp_path))
    scaler, raw = pm._fit_matching_scaler("nickel")
    assert scaler.data_min_[0] == pytest.approx(float(raw.min()))
    assert scaler.data_max_[0] == pytest.approx(float(raw.max()))


def test_unreadable_scaler_falls_back_instead_of_raising(pm, monkeypatch, tmp_path):
    (tmp_path / "scaler_nickel.pkl").write_bytes(b"not a pickle")
    monkeypatch.setenv("MODEL_DIR", str(tmp_path))
    scaler, raw = pm._fit_matching_scaler("nickel")
    assert scaler.data_max_[0] == pytest.approx(float(raw.max()))


def test_training_meta_covers_all_six_metals():
    path = BACKEND / "models_v2" / "training_meta.json"
    if not path.is_file():
        pytest.skip("models_v2/ not built; run scripts/train_production_v2.py")
    from data_loader import SUPPORTED_METALS

    meta = json.loads(path.read_text())
    assert sorted(meta["arima_order_per_metal"]) == sorted(SUPPORTED_METALS)
    assert sorted(meta["data_end_dates"]) == sorted(SUPPORTED_METALS)
    assert meta["versions"]["tensorflow"]
    assert meta["settings"]["window"] == 60
    assert meta["settings"]["val_frac"] == 0.10


def test_v2_arima_pickle_carries_its_selected_order():
    path = BACKEND / "models_v2" / "arima_nickel.pkl"
    if not path.is_file():
        pytest.skip("models_v2/ not built; run scripts/train_production_v2.py")
    meta = json.loads((BACKEND / "models_v2" / "meta_nickel.json").read_text())
    with open(path, "rb") as f:
        fit = pickle.load(f)
    # forecast_service reads the order back off the pickle; it must match the
    # order auto_arima actually selected during training.
    assert list(fit.model.order) == meta["arima_order"]
