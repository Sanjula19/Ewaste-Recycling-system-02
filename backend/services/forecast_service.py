"""
services/forecast_service.py
------------------------------
Builds a ForecastResponse for one metal: 90-day price path, Sell/Hold
recommendation, and dual-currency figures.

Model: ARIMA via statsmodels, order chosen by a small AIC grid search
(p,d,q each in 0..2). If statsmodels isn't installed, or a numerical fit
fails on a particular series, this falls back automatically to a
dependency-free AR(5)-on-first-differences model fit with plain
numpy least squares, so the endpoint never hard-fails for lack of a
heavy dependency. `model_used` in the response tells you honestly which
path actually ran, and MAPE/RMSE are computed the same way (a real 30-day
holdout backtest) regardless of which model produced them -- not
hardcoded placeholder numbers.

HOLD Command Upgrade: a HOLD recommendation now also returns
`operator_action = "CRUSH_AND_COMPRESS"` with a human-readable note, so the
dashboard (and eventually the MG996R crusher servo in your IoT design) has
a concrete next step instead of a bare status label.
"""

from __future__ import annotations
import itertools
import warnings
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from data_loader import load_metal_series, SUPPORTED_METALS
from materials_db import OUT_OF_SCOPE_METALS
from services import fx_service, influx_client, pretrained_models
from schemas import ForecastRequest, ForecastResponse, ForecastDataPoint, FXInfo

HORIZON_DAYS = 90
BACKTEST_HOLDOUT_DAYS = 30
HOLD_THRESHOLD_PCT = 2.0  # peak must beat current price by more than this to recommend HOLD

try:
    from statsmodels.tsa.arima.model import ARIMA
    HAS_STATSMODELS = True
except ImportError:  # pragma: no cover
    HAS_STATSMODELS = False


@dataclass
class ForecastPath:
    mean: np.ndarray      # length = horizon
    lower: np.ndarray
    upper: np.ndarray
    model_used: str


# ---------------------------------------------------------------------------
# Model fitting
# ---------------------------------------------------------------------------

def _fit_arima(series: pd.Series, horizon: int) -> ForecastPath | None:
    if not HAS_STATSMODELS or len(series) < 60:
        return None
    values = series.values.astype(float)
    best_aic, best_fit = np.inf, None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for p, d, q in itertools.product(range(3), range(2), range(3)):
            if p == 0 and q == 0:
                continue
            try:
                model = ARIMA(values, order=(p, d, q))
                fit = model.fit()
                if fit.aic < best_aic:
                    best_aic, best_fit = fit.aic, fit
            except Exception:
                continue
    if best_fit is None:
        return None
    forecast = best_fit.get_forecast(steps=horizon)
    summary = forecast.summary_frame(alpha=0.05)
    return ForecastPath(
        mean=summary["mean"].to_numpy(),
        lower=summary["mean_ci_lower"].to_numpy(),
        upper=summary["mean_ci_upper"].to_numpy(),
        model_used="ARIMA",
    )


def _fit_naive_ar(series: pd.Series, horizon: int, ar_order: int = 5) -> ForecastPath:
    """
    Dependency-free fallback: AR(ar_order) on first differences, fit by
    ordinary least squares, forecast recursively. Confidence bounds use
    the in-sample residual std, widening with sqrt(step) as a simple
    random-walk-style uncertainty growth.
    """
    values = series.values.astype(float)
    diffs = np.diff(values)
    n = len(diffs)
    order = min(ar_order, max(1, n // 4))

    X = np.column_stack([diffs[i:n - order + i] for i in range(order)])
    y = diffs[order:]
    X = np.column_stack([X, np.ones(len(X))])  # intercept
    coeffs, *_ = np.linalg.lstsq(X, y, rcond=None)

    residuals = y - X @ coeffs
    resid_std = float(np.std(residuals)) if len(residuals) > 1 else abs(float(np.std(diffs)))

    history = list(diffs[-order:])
    last_level = values[-1]
    means = []
    for _ in range(horizon):
        window = np.array(history[-order:] + [1.0])
        next_diff = float(window @ coeffs)
        history.append(next_diff)
        last_level += next_diff
        means.append(last_level)

    means = np.array(means)
    step = np.sqrt(np.arange(1, horizon + 1))
    lower = means - 1.96 * resid_std * step
    upper = means + 1.96 * resid_std * step
    return ForecastPath(mean=means, lower=lower, upper=upper, model_used="ARIMA (naive AR fallback)")


def fit_forecast(series: pd.Series, horizon: int = HORIZON_DAYS) -> ForecastPath:
    result = _fit_arima(series, horizon)
    if result is not None:
        return result
    return _fit_naive_ar(series, horizon)


def backtest(series: pd.Series, holdout: int = BACKTEST_HOLDOUT_DAYS) -> tuple[float, float]:
    """Real backtested MAPE (%) and RMSE (USD/kg) on the last `holdout` points."""
    if len(series) <= holdout + 30:
        holdout = max(5, len(series) // 5)
    train, actual = series.iloc[:-holdout], series.iloc[-holdout:]
    path = fit_forecast(train, horizon=holdout)
    predicted = path.mean[: len(actual)]
    actual_vals = actual.to_numpy()
    mape = float(np.mean(np.abs((actual_vals - predicted) / actual_vals)) * 100)
    rmse = float(np.sqrt(np.mean((actual_vals - predicted) ** 2)))
    return round(mape, 2), round(rmse, 4)


# ---------------------------------------------------------------------------
# Sell / Hold decision + HOLD Command Upgrade
# ---------------------------------------------------------------------------

def generate_recommendation(current_price: float, path: ForecastPath, last_date: pd.Timestamp) -> dict:
    peak_idx = int(np.argmax(path.mean))
    peak_price = float(path.mean[peak_idx])
    peak_date = (last_date + timedelta(days=peak_idx + 1)).strftime("%Y-%m-%d")

    if peak_price > current_price * (1 + HOLD_THRESHOLD_PCT / 100):
        return {
            "recommendation": "HOLD",
            "recommendation_reason": (
                f"Prices are projected to rise {((peak_price / current_price) - 1) * 100:.1f}% "
                f"to ~{peak_price:.2f} USD/kg by {peak_date}, above the {HOLD_THRESHOLD_PCT}% "
                f"hold threshold."
            ),
            "expected_peak_price": round(peak_price, 4),
            "expected_peak_date": peak_date,
            "profit_if_sell": None,
            "operator_action": "CRUSH_AND_COMPRESS",
            "operator_action_note": (
                "Route this batch to the compaction bay: crush and compress into "
                "space-saving feedstock blocks while prices recover, ready for bulk "
                "dispatch to secondary-metal remake pipelines."
            ),
        }
    return {
        "recommendation": "SELL NOW",
        "recommendation_reason": (
            f"90-day forecast shows no rise beyond the {HOLD_THRESHOLD_PCT}% hold threshold "
            f"(projected peak ~{peak_price:.2f} USD/kg vs current {current_price:.2f} USD/kg) "
            f"-- liquidate at today's price."
        ),
        "expected_peak_price": None,
        "expected_peak_date": None,
        "profit_if_sell": None,  # filled in by caller (needs weight_kg)
        "operator_action": "ROUTE_TO_MARKET_SALE",
        "operator_action_note": "Route this batch to the market liquidation bin for immediate sale.",
    }


# ---------------------------------------------------------------------------
# Pretrained-model selection (your saved arima_*.pkl / lstm_*.h5)
# ---------------------------------------------------------------------------

def _select_pretrained_forecast(metal: str) -> tuple[ForecastPath, float, float] | None:
    """
    Tries your saved ARIMA and LSTM models for `metal` (see
    services/pretrained_models.py) and returns whichever backtests better
    (lower MAPE), matching the same comparison your own notebook did.
    Returns None if neither is available (missing file, or
    tensorflow/statsmodels not installed) -- caller falls back to a live
    fit in that case.
    """
    candidates = []
    arima_result = pretrained_models.forecast_with_pretrained_arima(metal)
    if arima_result is not None:
        candidates.append(arima_result)
    lstm_result = pretrained_models.forecast_with_pretrained_lstm(metal)
    if lstm_result is not None:
        candidates.append(lstm_result)

    if not candidates:
        return None

    def _sort_key(c):
        return c.mape if not np.isnan(c.mape) else float("inf")

    best = min(candidates, key=_sort_key)
    path = ForecastPath(
        mean=best.mean_usd_kg, lower=best.lower_usd_kg, upper=best.upper_usd_kg,
        model_used=best.model_used,
    )
    return path, best.mape, best.rmse


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

_MODEL_CACHE_TTL_SECONDS = 15 * 60
_model_cache: dict[str, tuple[float, tuple]] = {}


def _model_path_cached(key: str, history: pd.Series) -> tuple[ForecastPath, float, float]:
    """
    Resolving a metal's forecast path -- loading the pretrained .pkl/.h5,
    running the recursive 90-day loop, and backtesting it -- takes on the
    order of 15 seconds per metal, dominated by TensorFlow model load.

    That is fine once, but it was being redone on every single request.
    An IoT scan would sit there for 14s waiting, well past the ESP32's
    5s HTTP timeout, so the terminal could never get an answer at all.

    The underlying models and CSVs do not change between requests, so the
    result is cached per metal. The *price* is deliberately not cached --
    build_price_path() re-reads it each call, so a live InfluxDB tick is
    still picked up immediately.
    """
    import time

    now = time.time()
    hit = _model_cache.get(key)
    if hit is not None and (now - hit[0]) < _MODEL_CACHE_TTL_SECONDS:
        return hit[1]

    pretrained = _select_pretrained_forecast(key)
    if pretrained is not None:
        result = pretrained
    else:
        result = (fit_forecast(history, horizon=HORIZON_DAYS), *backtest(history))

    _model_cache[key] = (now, result)
    return result


def build_price_path(key: str) -> tuple[ForecastPath, float, float, pd.Series, float, bool]:
    """
    Shared price/model resolution used by both /api/forecast and the
    Market Overview (services/market_service.py): prefers your saved
    pretrained model (fast, already backtested), falls back to a live
    ARIMA/naive-AR fit otherwise. Returns
    (path, mape, rmse, history, current_price, is_live) where `is_live`
    tells the caller whether `current_price` came from a live InfluxDB
    tick (True) or the last historical CSV point (False) -- callers that
    display this to an operator should say so rather than presenting a
    possibly stale number as live.
    """
    # Prefer live data from InfluxDB; fall back to the historical CSV.
    history = influx_client.query_history(key)
    if history.empty:
        history = load_metal_series(key)

    live_price = influx_client.query_latest_price(key)
    is_live = live_price is not None
    current_price = live_price if is_live else float(history.iloc[-1])

    path, mape, rmse = _model_path_cached(key, history)

    return path, mape, rmse, history, current_price, is_live


def calculate_forecast(req: ForecastRequest) -> ForecastResponse:
    key = req.metal.strip().lower()
    if key in OUT_OF_SCOPE_METALS:
        raise ValueError(
            f"'{req.metal}' is out of scope for this component (gold and silver are excluded). "
            f"Supported metals: {SUPPORTED_METALS}"
        )
    if key not in SUPPORTED_METALS:
        raise ValueError(f"Unsupported metal '{req.metal}'. Supported: {SUPPORTED_METALS}")

    path, mape, rmse, history, current_price, _is_live = build_price_path(key)

    fx = fx_service.get_fx_rates()
    last_date = history.index[-1]

    forecast_points = []
    for i in range(HORIZON_DAYS):
        date_str = (last_date + timedelta(days=i + 1)).strftime("%Y-%m-%d")
        price = float(path.mean[i])
        lower = float(path.lower[i])
        upper = float(path.upper[i])
        forecast_points.append(
            ForecastDataPoint(
                date=date_str,
                price=round(price, 4),
                price_lkr=fx_service.to_lkr(price, fx),
                lower_bound=round(lower, 4),
                upper_bound=round(upper, 4),
                lower_bound_lkr=fx_service.to_lkr(lower, fx),
                upper_bound_lkr=fx_service.to_lkr(upper, fx),
            )
        )

    rec = generate_recommendation(current_price, path, last_date)
    if rec["recommendation"] == "SELL NOW":
        rec["profit_if_sell"] = round(current_price * req.weight_kg, 2)

    fx_info = FXInfo(**fx)

    return ForecastResponse(
        metal=key,
        current_price=round(current_price, 4),
        current_price_lkr=fx_service.to_lkr(current_price, fx),
        forecast_90d=forecast_points,
        recommendation=rec["recommendation"],
        recommendation_reason=rec["recommendation_reason"],
        profit_if_sell=rec["profit_if_sell"],
        profit_if_sell_lkr=(
            fx_service.to_lkr(rec["profit_if_sell"], fx) if rec["profit_if_sell"] is not None else None
        ),
        expected_peak_price=rec["expected_peak_price"],
        expected_peak_price_lkr=(
            fx_service.to_lkr(rec["expected_peak_price"], fx)
            if rec["expected_peak_price"] is not None
            else None
        ),
        expected_peak_date=rec["expected_peak_date"],
        mape=mape,
        rmse=rmse,
        model_used=path.model_used,
        weight_kg=req.weight_kg,
        unit_price=round(current_price, 4),
        unit_price_lkr=fx_service.to_lkr(current_price, fx),
        operator_action=rec["operator_action"],
        operator_action_note=rec["operator_action_note"],
        fx=fx_info,
    )
