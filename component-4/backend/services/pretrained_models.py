"""
services/pretrained_models.py
--------------------------------
Loads and runs YOUR already-trained models (arima_{metal}_model.pkl,
lstm_{metal}_model.h5) instead of fitting fresh -- this is the "use my
saved models" path you asked for, built directly from your
ewaste_preprocessing.py / ewaste_model_training.py / the Colab export.

WHERE THE FILES GO: models/<name>.pkl and models/<name>.h5 -- see
models/README.md. If a file for a given metal isn't there, or the
tensorflow/statsmodels dependency isn't installed, every function here
returns None and forecast_service.py transparently falls back to fitting
ARIMA live from the CSVs (the path that already worked before you sent
these files). Nothing hard-fails for a missing model.

TWO IMPORTANT DETAILS CARRIED OVER EXACTLY FROM YOUR PIPELINE, NOT
RE-DERIVED:

1. Your MinMaxScaler was fit on the RAW native-currency 'Price' column
   (INR/kg for most metals, USD/ton for steel) -- BEFORE any USD
   conversion, and on the FULL series (train+test), not train-only. A
   pretrained model's inverse-transformed output therefore comes back in
   that same native unit, not USD/kg. `_native_forecast_to_usd_kg()`
   below applies data_loader.native_to_usd_per_kg() as the final step,
   exactly once, right after inverse-transforming.

2. Your `train_arima()` fits ARIMA TWICE: once on train-only (to get
   test-period predictions for MAPE/RMSE, never saved), and again on the
   FULL series (train+test) -- that second fit is `fit_full`, the object
   actually pickled. This means the saved .pkl has no honest holdout of
   its own. To still report a real (not fabricated) accuracy number, this
   module refits an ARIMA of the SAME order (read back off the pickled
   model via `.model.order`) on a train-only split and backtests that,
   mirroring what your notebook printed to the console but didn't save.

WINDOW_SIZE=60 and the LSTM forecast-confidence-band formula
(mean +/- 1.96 x residual_std, constant width, not growing with the
horizon) are copied as-is from your train_lstm() -- a known simplification
in the original notebook, not something introduced here. Flagged in
README as a nice follow-up (growing the band with sqrt(step) is more
statistically correct) rather than silently "fixed" here.
"""

from __future__ import annotations
import os
import pickle
import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from data_loader import load_metal_series_raw, native_to_usd_per_kg

logger = logging.getLogger("ecovision.pretrained_models")

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")
WINDOW_SIZE = 60          # must match your ewaste_model_training.py WINDOW_SIZE
TRAIN_RATIO = 0.80        # must match your ewaste_preprocessing.py TRAIN_RATIO
FORECAST_HORIZON = 90

try:
    from statsmodels.tsa.arima.model import ARIMA
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

try:
    import tensorflow as tf
    HAS_TENSORFLOW = True
except ImportError:
    HAS_TENSORFLOW = False


@dataclass
class PretrainedForecast:
    mean_usd_kg: np.ndarray
    lower_usd_kg: np.ndarray
    upper_usd_kg: np.ndarray
    mape: float
    rmse: float
    model_used: str


def _arima_path(metal: str) -> str:
    return os.path.join(MODELS_DIR, f"arima_{metal.lower()}_model.pkl")


def _lstm_path(metal: str) -> str:
    return os.path.join(MODELS_DIR, f"lstm_{metal.lower()}_model.h5")


def has_pretrained_arima(metal: str) -> bool:
    return os.path.isfile(_arima_path(metal))


def has_pretrained_lstm(metal: str) -> bool:
    return os.path.isfile(_lstm_path(metal))


# ---------------------------------------------------------------------------
# Scaler replication -- must exactly match ewaste_preprocessing.run_pipeline()
# ---------------------------------------------------------------------------

def _fit_matching_scaler(metal: str) -> tuple[MinMaxScaler, pd.Series]:
    """
    Refits a MinMaxScaler(0,1) on the FULL raw native-price series for
    `metal`, matching ewaste_preprocessing.run_pipeline() exactly (fit on
    df[['Price']] before the train/test split). Since MinMaxScaler only
    needs the data's min/max, refitting on the same source CSV reproduces
    the identical scaler the training notebook used -- no need for you to
    separately export scaler.pkl per metal.
    """
    raw = load_metal_series_raw(metal)  # ascending, native units
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaler.fit(raw.to_numpy().reshape(-1, 1))
    return scaler, raw


def _train_test_split(raw: pd.Series, train_ratio: float = TRAIN_RATIO) -> tuple[pd.Series, pd.Series]:
    split_idx = int(len(raw) * train_ratio)
    return raw.iloc[:split_idx], raw.iloc[split_idx:]


# ---------------------------------------------------------------------------
# ARIMA
# ---------------------------------------------------------------------------

def _load_arima_fit(metal: str):
    if not HAS_STATSMODELS or not has_pretrained_arima(metal):
        return None
    try:
        with open(_arima_path(metal), "rb") as f:
            return pickle.load(f)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to load pretrained ARIMA for %s: %s", metal, exc)
        return None


def forecast_with_pretrained_arima(metal: str, horizon: int = FORECAST_HORIZON) -> PretrainedForecast | None:
    fit_full = _load_arima_fit(metal)
    if fit_full is None:
        return None

    scaler, raw = _fit_matching_scaler(metal)
    order = fit_full.model.order  # (p, d, q) actually used at training time

    # --- Forecast (using the saved full-series fit, as your pipeline intended) ---
    fc = fit_full.get_forecast(steps=horizon)
    summary = fc.summary_frame(alpha=0.05)
    mean_scaled = summary["mean"].to_numpy().reshape(-1, 1)
    lower_scaled = summary["mean_ci_lower"].to_numpy().reshape(-1, 1)
    upper_scaled = summary["mean_ci_upper"].to_numpy().reshape(-1, 1)

    mean_native = scaler.inverse_transform(mean_scaled).ravel()
    lower_native = scaler.inverse_transform(lower_scaled).ravel()
    upper_native = scaler.inverse_transform(upper_scaled).ravel()

    mean_usd = native_to_usd_per_kg(metal, pd.Series(mean_native)).to_numpy()
    lower_usd = native_to_usd_per_kg(metal, pd.Series(lower_native)).to_numpy()
    upper_usd = native_to_usd_per_kg(metal, pd.Series(upper_native)).to_numpy()

    # --- Honest backtest: refit the SAME order on a train-only split ---
    mape, rmse = _backtest_arima_order(metal, order)

    return PretrainedForecast(
        mean_usd_kg=mean_usd, lower_usd_kg=lower_usd, upper_usd_kg=upper_usd,
        mape=mape, rmse=rmse, model_used=f"ARIMA{order} (pretrained)",
    )


def _backtest_arima_order(metal: str, order: tuple[int, int, int], holdout_ratio: float = 1 - TRAIN_RATIO) -> tuple[float, float]:
    scaler, raw = _fit_matching_scaler(metal)
    train_raw, test_raw = _train_test_split(raw)
    train_scaled = scaler.transform(train_raw.to_numpy().reshape(-1, 1)).ravel()

    try:
        fit = ARIMA(train_scaled, order=order).fit(method_kwargs={"warn_convergence": False})
        fc_scaled = fit.get_forecast(steps=len(test_raw)).predicted_mean.reshape(-1, 1)
        pred_native = scaler.inverse_transform(fc_scaled).ravel()
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("ARIMA backtest refit failed for %s: %s", metal, exc)
        return float("nan"), float("nan")

    pred_usd = native_to_usd_per_kg(metal, pd.Series(pred_native)).to_numpy()
    actual_usd = native_to_usd_per_kg(metal, test_raw).to_numpy()

    n = min(len(pred_usd), len(actual_usd))
    pred_usd, actual_usd = pred_usd[:n], actual_usd[:n]
    mape = float(np.mean(np.abs((actual_usd - pred_usd) / actual_usd)) * 100)
    rmse = float(np.sqrt(np.mean((actual_usd - pred_usd) ** 2)))
    return round(mape, 2), round(rmse, 4)


# ---------------------------------------------------------------------------
# LSTM
# ---------------------------------------------------------------------------

def _load_lstm_model(metal: str):
    if not HAS_TENSORFLOW or not has_pretrained_lstm(metal):
        return None
    try:
        return tf.keras.models.load_model(_lstm_path(metal))
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to load pretrained LSTM for %s: %s", metal, exc)
        return None


def _create_sequences(data: np.ndarray, window_size: int) -> tuple[np.ndarray, np.ndarray]:
    X, y = [], []
    for i in range(len(data) - window_size):
        X.append(data[i:i + window_size, :])
        y.append(data[i + window_size, 0])
    return np.array(X), np.array(y)


def forecast_with_pretrained_lstm(metal: str, horizon: int = FORECAST_HORIZON) -> PretrainedForecast | None:
    model = _load_lstm_model(metal)
    if model is None:
        return None

    scaler, raw = _fit_matching_scaler(metal)
    train_raw, test_raw = _train_test_split(raw)
    train_scaled = scaler.transform(train_raw.to_numpy().reshape(-1, 1))
    test_scaled = scaler.transform(test_raw.to_numpy().reshape(-1, 1))
    full_scaled = np.concatenate([train_scaled, test_scaled])

    if len(full_scaled) <= WINDOW_SIZE:
        logger.warning("Not enough history for LSTM window on %s -- skipping.", metal)
        return None

    # --- Residual std from the test window, for a (constant-width) confidence band ---
    error_std_scaled = 0.0
    if len(test_scaled) > WINDOW_SIZE:
        X_test, y_test = _create_sequences(test_scaled, WINDOW_SIZE)
        if len(X_test) > 0:
            test_pred_scaled = model.predict(X_test, verbose=0)
            residuals = y_test.reshape(-1, 1) - test_pred_scaled
            error_std_scaled = float(np.std(residuals))

    # --- Recursive multi-step forecast, exactly as train_lstm() does it ---
    last_window = full_scaled[-WINDOW_SIZE:]
    current_input = last_window.reshape(1, WINDOW_SIZE, 1)
    forecast_scaled = []
    for _ in range(horizon):
        next_pred = model.predict(current_input, verbose=0)[0, 0]
        forecast_scaled.append(next_pred)
        current_input = np.roll(current_input, -1, axis=1)
        current_input[0, -1, 0] = next_pred

    forecast_scaled = np.array(forecast_scaled).reshape(-1, 1)
    mean_native = scaler.inverse_transform(forecast_scaled).ravel()

    lower_scaled = (forecast_scaled.ravel() - 1.96 * error_std_scaled).reshape(-1, 1)
    upper_scaled = (forecast_scaled.ravel() + 1.96 * error_std_scaled).reshape(-1, 1)
    lower_native = scaler.inverse_transform(lower_scaled).ravel()
    upper_native = scaler.inverse_transform(upper_scaled).ravel()

    mean_usd = native_to_usd_per_kg(metal, pd.Series(mean_native)).to_numpy()
    lower_usd = native_to_usd_per_kg(metal, pd.Series(lower_native)).to_numpy()
    upper_usd = native_to_usd_per_kg(metal, pd.Series(upper_native)).to_numpy()

    mape, rmse = float("nan"), float("nan")
    if len(test_scaled) > WINDOW_SIZE and len(X_test) > 0:
        test_pred_native = scaler.inverse_transform(test_pred_scaled).ravel()
        test_pred_usd = native_to_usd_per_kg(metal, pd.Series(test_pred_native)).to_numpy()
        test_actual_native = scaler.inverse_transform(y_test.reshape(-1, 1)).ravel()
        test_actual_usd = native_to_usd_per_kg(metal, pd.Series(test_actual_native)).to_numpy()
        mape = float(np.mean(np.abs((test_actual_usd - test_pred_usd) / test_actual_usd)) * 100)
        rmse = float(np.sqrt(np.mean((test_actual_usd - test_pred_usd) ** 2)))

    return PretrainedForecast(
        mean_usd_kg=mean_usd, lower_usd_kg=lower_usd, upper_usd_kg=upper_usd,
        mape=round(mape, 2), rmse=round(rmse, 4), model_used="LSTM (pretrained)",
    )
