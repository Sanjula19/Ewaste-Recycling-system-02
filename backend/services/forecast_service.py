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
import math
import warnings
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

import data_loader
from data_loader import load_metal_series, SUPPORTED_METALS
from materials_db import OUT_OF_SCOPE_METALS
from services import fx_service, influx_client, pretrained_models
from schemas import ForecastRequest, ForecastResponse, ForecastDataPoint, FXInfo

HORIZON_DAYS = 90
BACKTEST_HOLDOUT_DAYS = 30
HOLD_THRESHOLD_PCT = 2.0  # peak must beat current price by more than this to recommend HOLD

# Older than this and the price being valued is not today's price, so the
# response says so rather than letting a dashboard imply otherwise.
STALE_AFTER_DAYS = 7

# How far a live tick may sit from the CSV's last close before the two are
# treated as different sources rather than the same price. Above this they
# are not interchangeable, and silently taking one as P0 while forecasting
# from the other would value a batch against a number the model never saw.
SOURCE_AGREEMENT_PCT = 0.5


@dataclass
class PriceContext:
    """Where P0 came from, how old it is, and whether anything disagrees."""
    history: pd.Series          # the series the forecast is actually built on
    current_price: float
    last_price_date: pd.Timestamp
    data_age_days: int
    stale_data: bool
    price_source: str           # "live" | "historical"
    data_warning: str | None

try:
    from statsmodels.tsa.arima.model import ARIMA
    HAS_STATSMODELS = True
except ImportError:  # pragma: no cover
    HAS_STATSMODELS = False


NO_SIGNAL_REASON = (
    "The model does not outperform a no-change forecast on recent data, so "
    "holding is not recommended."
)


@dataclass
class ForecastPath:
    mean: np.ndarray      # length = horizon
    lower: np.ndarray
    upper: np.ndarray
    model_used: str
    # MAPE of a no-change (persistence) forecast on the SAME holdout the
    # selected model's MAPE was measured on, or None when no such baseline
    # is available (legacy model folder, or the live-fit fallback).
    persistence_mape: float | None = None


def has_signal(mape: float, persistence_mape: float | None) -> bool:
    """
    Is there anything to forecast?

    A model that cannot beat "tomorrow's price is today's price" on recent
    data has no demonstrated predictive signal, and a HOLD issued off its
    90-day path is a guess dressed up as a decision. This is the gate for
    that case; see generate_recommendation().

    Returns True when no baseline is available, so the check can only ever
    veto a HOLD on evidence, never on a missing number.
    """
    if persistence_mape is None or math.isnan(persistence_mape) or math.isnan(mape):
        return True
    return mape < persistence_mape


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

def generate_recommendation(
    current_price: float,
    path: ForecastPath,
    last_date: pd.Timestamp,
    mape: float = 0.0,
) -> dict:
    """
    Sell/Hold, judged against the model's own demonstrated reliability
    rather than one flat number.

    Two rules, both aimed at not calling a decision on noise:

    1. The bar a predicted gain has to clear is the LARGER of the fixed
       hold threshold and this metal's backtested MAPE. Steel backtests
       at ~3.5% error, so a 2% predicted rise there is well inside the
       model's own margin -- reporting that as HOLD dresses up noise as
       a decision. Copper backtests near 1.2%, so its bar stays at the
       2% floor.

    2. The comparison uses the forecast's LOWER confidence bound, not
       the mean. HOLD therefore means "even on the pessimistic path,
       waiting still beats selling today" -- a claim worth acting on,
       where "the midpoint might beat today" is not.

    The effect is fewer HOLDs, each better founded. Every figure behind
    the call is in recommendation_reason so it can be defended.

    3. Before either of those is consulted: if the selected model does not
       beat a no-change forecast on the same holdout its MAPE came from,
       there is no demonstrated signal to hold on, and the answer is SELL
       NOW regardless of what the 90-day path says. A model worse than
       "price stays put" can still draw a rising curve; that curve is not
       evidence. This gate is skipped when no baseline is available.
    """
    if not has_signal(mape, path.persistence_mape):
        return {
            "recommendation": "SELL NOW",
            "recommendation_reason": (
                f"{NO_SIGNAL_REASON} On the 30-day holdout the selected model "
                f"({path.model_used}) scored {mape:.2f}% MAPE against "
                f"{path.persistence_mape:.2f}% for a no-change forecast, so its "
                f"90-day path carries no information a flat line would not."
            ),
            "expected_peak_price": None,
            "expected_peak_date": None,
            "profit_if_sell": None,   # filled in by caller (needs weight_kg)
            "operator_action": "ROUTE_TO_MARKET_SALE",
            "operator_action_note": "Route this batch to the market liquidation bin for immediate sale.",
        }

    peak_idx = int(np.argmax(path.mean))
    peak_price = float(path.mean[peak_idx])
    confident_peak = float(path.lower[peak_idx])   # pessimistic case at the peak
    peak_date = (last_date + timedelta(days=peak_idx + 1)).strftime("%Y-%m-%d")

    threshold_pct = max(HOLD_THRESHOLD_PCT, mape)
    required_price = current_price * (1 + threshold_pct / 100)
    basis = "model error (MAPE)" if mape > HOLD_THRESHOLD_PCT else "fixed floor"

    if confident_peak > required_price:
        return {
            "recommendation": "HOLD",
            "recommendation_reason": (
                f"Even the lower confidence bound of the 90-day forecast reaches "
                f"~{confident_peak:.2f} USD/kg by {peak_date} "
                f"({((confident_peak / current_price) - 1) * 100:.1f}% above today's "
                f"{current_price:.2f}), clearing the {threshold_pct:.2f}% bar set by "
                f"{basis}. Holding is worth the wait."
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
            f"No confident rise in the 90-day forecast: the pessimistic case peaks at "
            f"~{confident_peak:.2f} USD/kg (mean ~{peak_price:.2f}) against today's "
            f"{current_price:.2f}, short of the {threshold_pct:.2f}% bar set by {basis}. "
            f"Any projected gain sits inside the model's own error -- liquidate at today's price."
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

    With a models_v2-style folder the MAPE being compared is each model's
    error on a 30-day holdout it was retrained without, rather than on a
    window inside its own training data -- so this picks the model that is
    actually more accurate out of sample, which is not the same winner.
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
        model_used=best.model_used, persistence_mape=best.persistence_mape,
    )
    return path, best.mape, best.rmse


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

#: metal -> (cache key, result). One entry per metal, so a new key for a
#: metal replaces its old entry instead of accumulating alongside it.
_model_cache: dict[str, tuple[tuple, tuple]] = {}


def _cache_key(metal: str, history: pd.Series) -> tuple:
    """
    (metal, model folder, latest price date, number of observations).

    The forecast is a function of the model artifacts and the price history,
    and nothing else, so those are what it is keyed on:

      * model folder -- switching MODEL_DIR must not serve a forecast
        produced by the other folder's models.
      * latest price date -- the one thing that changes in normal operation.
        A new daily price arrives, the date moves, the entry is recomputed.
      * observation count -- catches a backfill that rewrote earlier history
        without moving the last date.

    This replaced a 15-minute TTL, which had both failure modes at once: it
    recomputed six unchanged forecasts every quarter hour, and it could
    still serve a stale forecast for up to 15 minutes after a new price
    landed.
    """
    last = history.index[-1]
    return (metal, pretrained_models.models_dir(),
            str(pd.Timestamp(last).date()), int(len(history)))


def _model_path_cached(key: str, history: pd.Series) -> tuple[ForecastPath, float, float]:
    """
    Resolving a metal's forecast path -- loading the pretrained model,
    running the recursive 90-day loop, and scoring it -- is far too slow to
    redo per request: an IoT scan would sit there for seconds, well past the
    ESP32's 5s HTTP timeout, so the terminal could never get an answer.

    Cached per metal against _cache_key(). The *price* is deliberately not
    cached -- build_price_path() re-reads it each call, so a live InfluxDB
    tick is still picked up immediately.
    """
    ck = _cache_key(key, history)
    hit = _model_cache.get(key)
    if hit is not None and hit[0] == ck:
        return hit[1]

    pretrained = _select_pretrained_forecast(key)
    if pretrained is not None:
        result = pretrained
    else:
        result = (fit_forecast(history, horizon=HORIZON_DAYS), *backtest(history))

    _model_cache[key] = (ck, result)
    return result


def clear_cache() -> None:
    """Drop cached forecasts (and the loaded artifacts behind them)."""
    _model_cache.clear()
    pretrained_models.clear_cache()


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
    ctx = resolve_price_context(key)
    path, mape, rmse = _model_path_cached(key, ctx.history)
    return path, mape, rmse, ctx.history, ctx.current_price, ctx.price_source == "live"


def resolve_price_context(key: str) -> PriceContext:
    """
    Pin P0 and the forecast to ONE price series, and say which.

    The forecast is produced by the pretrained models, which read the
    configured dataset (data_loader, DATA_VERSION) directly. So the series
    below is that same dataset -- not whatever InfluxDB happens to hold.

    That matters now that the dataset has changed: an InfluxDB seeded from
    the old MCX/INR export would hand back a price on a different basis
    from the series the model was trained on, and taking it as P0 while
    forecasting from the new one would value a batch against a number the
    model has never seen. Rather than mix them, a live tick is used only
    when it agrees with the dataset's own last close to within
    SOURCE_AGREEMENT_PCT; otherwise the dataset wins and the disagreement
    is reported on the response.
    """
    history = load_metal_series(key)
    csv_last = float(history.iloc[-1])
    last_date = pd.Timestamp(history.index[-1])

    price_source, warning = "historical", None
    current_price = csv_last

    live_price = influx_client.query_latest_price(key)
    if live_price is not None:
        drift_pct = abs(live_price - csv_last) / csv_last * 100 if csv_last else float("inf")
        if drift_pct <= SOURCE_AGREEMENT_PCT:
            current_price, price_source = float(live_price), "live"
        else:
            warning = (
                f"InfluxDB returned {live_price:.4f} USD/kg for {key} while the "
                f"{data_loader.data_version()} dataset's last close ({last_date.date()}) is "
                f"{csv_last:.4f} -- {drift_pct:.1f}% apart, so these are different price "
                f"sources. The forecast is built on the {data_loader.data_version()} series, "
                f"so that series' price is used for P0 too; the live tick is ignored rather "
                f"than mixed in. Re-seed InfluxDB from the current dataset "
                f"(scripts/seed_influxdb.py) to use live prices again."
            )

    age = max(0, (pd.Timestamp.utcnow().tz_localize(None).normalize() - last_date.normalize()).days)
    stale = age > STALE_AFTER_DAYS
    if stale:
        stale_note = (f"Latest {key} price is from {last_date.date()}, {age} days old; "
                      f"this is not a current market price.")
        warning = f"{warning} {stale_note}" if warning else stale_note

    return PriceContext(history=history, current_price=current_price, last_price_date=last_date,
                        data_age_days=age, stale_data=stale, price_source=price_source,
                        data_warning=warning)


def forecast_dates(last_date: pd.Timestamp, horizon: int = HORIZON_DAYS) -> list[pd.Timestamp]:
    """
    The next `horizon` BUSINESS days after the last observed price.

    These series are exchange closes, so they have no weekend observations
    and the model's step is one trading day, not one calendar day. Dating
    the path in calendar days stretched a 90-step forecast across ~128
    trading days and put a third of the points on days the market is shut.
    """
    return list(pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=horizon))


def calculate_forecast(req: ForecastRequest) -> ForecastResponse:
    key = req.metal.strip().lower()
    if key in OUT_OF_SCOPE_METALS:
        raise ValueError(
            f"'{req.metal}' is out of scope for this component (gold and silver are excluded). "
            f"Supported metals: {SUPPORTED_METALS}"
        )
    if key not in SUPPORTED_METALS:
        raise ValueError(f"Unsupported metal '{req.metal}'. Supported: {SUPPORTED_METALS}")

    ctx = resolve_price_context(key)
    path, mape, rmse = _model_path_cached(key, ctx.history)
    current_price = ctx.current_price

    fx = fx_service.get_fx_rates()
    last_date = ctx.last_price_date
    dates = forecast_dates(last_date, HORIZON_DAYS)

    forecast_points = []
    for i in range(HORIZON_DAYS):
        date_str = dates[i].strftime("%Y-%m-%d")
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

    rec = generate_recommendation(current_price, path, last_date, mape)
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
        persistence_mape=path.persistence_mape,
        signal=has_signal(mape, path.persistence_mape),
        last_price_date=last_date.strftime("%Y-%m-%d"),
        data_age_days=ctx.data_age_days,
        stale_data=ctx.stale_data,
        data_warning=ctx.data_warning,
        model_used=path.model_used,
        weight_kg=req.weight_kg,
        unit_price=round(current_price, 4),
        unit_price_lkr=fx_service.to_lkr(current_price, fx),
        operator_action=rec["operator_action"],
        operator_action_note=rec["operator_action_note"],
        fx=fx_info,
    )
