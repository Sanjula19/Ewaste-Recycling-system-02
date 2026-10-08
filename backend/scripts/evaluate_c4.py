"""
scripts/evaluate_c4.py
-----------------------
Reproducible evaluation for the Component 4 paper (Sections V-B.1 and V-B.2).

Run from the backend/ folder with the project venv:

    python scripts/evaluate_c4.py                 # everything
    python scripts/evaluate_c4.py --step 15       # denser decision points
    python scripts/evaluate_c4.py --metals copper steel
    python scripts/evaluate_c4.py --skip-decisions   # Table 4 only (fast)

PART A  (Table 4) -- 30-day holdout, SAME protocol for both models
    * Last H=30 observations are withheld.
    * ARIMA: order read from the saved .pkl, refit on data before the cutoff,
      30-step forecast.
    * LSTM : saved .h5, recursive 30-step forecast from the 60 values before
      the cutoff (same recursion as the deployed service).
    * Also reports a persistence baseline (last value carried forward) so the
      reader can see whether either model beats "no change".
    * Selected model = lower MAPE; tau = max(2%, MAPE_selected)  [Eq. 4].

PART B  (Table 5) -- rolling-origin decision evaluation
    * Decision dates lie in the final 20% of each series only. The saved LSTMs
      are assumed trained on the first 80% (TRAIN_RATIO), so those dates are
      out-of-sample for them.
    * At each date t only data up to t is used. ARIMA is refit (fixed order).
      Model selection at t uses a 30-day backtest ending at t, exactly as the
      deployed service does.
    * Proposed rule : HOLD iff (L* - P0)/P0 > tau            [Eq. 5]
      Naive rule    : HOLD iff peak point forecast > P0
    * Ground truth (as defined in the paper): a HOLD is correct if the actual
      price rose by more than tau within the next 90 days. A stricter
      "price at day 90" criterion is reported alongside.

Outputs go to backend/results/ (CSV, LaTeX rows, JSON metadata).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import sys
import time
import warnings
from datetime import datetime

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import numpy as np
import pandas as pd

from data_loader import (MATERIAL_CONFIG, SUPPORTED_METALS, USD_INR_RATE_HISTORICAL,
                         load_metal_series_raw, native_to_usd_per_kg)
from services import pretrained_models as pm

from statsmodels.tsa.arima.model import ARIMA

HOLDOUT = 30
HORIZON = 90
WINDOW = pm.WINDOW_SIZE
TRAIN_RATIO = pm.TRAIN_RATIO
FLOOR_PCT = 2.0           # must equal forecast_service.HOLD_THRESHOLD_PCT
BAND_LOOKBACK = 120       # trailing points for the LSTM residual std at an origin
RESULTS_DIR = os.path.join(BACKEND_DIR, "results")


# ---------------------------------------------------------------------------
# Forecasting primitives (all in SCALED units; the scaler is linear, so ratios
# such as MAPE are identical in native units and in USD/kg)
# ---------------------------------------------------------------------------

def arima_forecast(hist: np.ndarray, order, steps: int):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = ARIMA(hist, order=order).fit()
        sf = fit.get_forecast(steps=steps).summary_frame(alpha=0.05)
    return sf["mean"].to_numpy(), sf["mean_ci_lower"].to_numpy(), sf["mean_ci_upper"].to_numpy()


def _lstm_step(model, window: np.ndarray) -> float:
    return float(model(window, training=False).numpy()[0, 0])


def lstm_forecast_mean(model, hist: np.ndarray, steps: int) -> np.ndarray:
    window = hist[-WINDOW:].reshape(1, WINDOW, 1).astype("float32")
    out = []
    for _ in range(steps):
        p = _lstm_step(model, window)
        out.append(p)
        window = np.roll(window, -1, axis=1)
        window[0, -1, 0] = p
    return np.array(out)


def lstm_resid_std(model, hist: np.ndarray) -> float:
    """One-step residual std over the trailing BAND_LOOKBACK points of `hist`."""
    seg = hist[-(BAND_LOOKBACK + WINDOW):]
    X = np.array([seg[i:i + WINDOW] for i in range(len(seg) - WINDOW)], dtype="float32")[..., None]
    y = seg[WINDOW:]
    pred = model(X, training=False).numpy().ravel()
    return float(np.std(y - pred))


def mape(actual: np.ndarray, pred: np.ndarray) -> float:
    return float(np.mean(np.abs((actual - pred) / actual)) * 100)


def rmse(actual: np.ndarray, pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((actual - pred) ** 2)))


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * (c - h), 100 * (c + h))


# ---------------------------------------------------------------------------
# Part A
# ---------------------------------------------------------------------------

def part_a(metal: str, model, order, scaler, scaled: np.ndarray, raw: pd.Series) -> dict:
    cut = len(scaled) - HOLDOUT
    actual_native = raw.to_numpy()[cut:]
    actual_usd = native_to_usd_per_kg(metal, pd.Series(actual_native)).to_numpy()

    def to_usd(scaled_vals):
        native = scaler.inverse_transform(np.asarray(scaled_vals).reshape(-1, 1)).ravel()
        return native_to_usd_per_kg(metal, pd.Series(native)).to_numpy()

    a_mean, _, _ = arima_forecast(scaled[:cut], order, HOLDOUT)
    l_mean = lstm_forecast_mean(model, scaled[:cut], HOLDOUT)
    persist = np.full(HOLDOUT, scaled[cut - 1])

    res = {
        "metal": metal,
        "n_obs": len(scaled),
        "start": raw.index[0].strftime("%Y-%m-%d"),
        "end": raw.index[-1].strftime("%Y-%m-%d"),
        "arima_order": str(tuple(order)),
        "arima_mape": mape(actual_usd, to_usd(a_mean)),
        "lstm_mape": mape(actual_usd, to_usd(l_mean)),
        "persistence_mape": mape(actual_usd, to_usd(persist)),
        "arima_rmse": rmse(actual_usd, to_usd(a_mean)),
        "lstm_rmse": rmse(actual_usd, to_usd(l_mean)),
    }
    sel = "ARIMA" if res["arima_mape"] <= res["lstm_mape"] else "LSTM"
    res["selected"] = sel
    res["selected_mape"] = res[f"{sel.lower()}_mape"]
    res["selected_rmse"] = res[f"{sel.lower()}_rmse"]
    res["tau_pct"] = max(FLOOR_PCT, res["selected_mape"])
    res["beats_persistence"] = res["selected_mape"] < res["persistence_mape"]
    return res


# ---------------------------------------------------------------------------
# Part B
# ---------------------------------------------------------------------------

def decide_at(origin_idx: int, model, order, scaler, scaled: np.ndarray, raw_native: np.ndarray):
    """Run the deployed decision pipeline using only data up to origin_idx."""
    hist = scaled[: origin_idx + 1]
    inv = lambda v: scaler.inverse_transform(np.asarray(v).reshape(-1, 1)).ravel()

    # 1. 30-day backtest ending at the origin -> pick the model, set tau
    bt_train, bt_actual = hist[:-HOLDOUT], inv(hist[-HOLDOUT:])
    bt_a = inv(arima_forecast(bt_train, order, HOLDOUT)[0])
    bt_l = inv(lstm_forecast_mean(model, bt_train, HOLDOUT))
    m_a, m_l = mape(bt_actual, bt_a), mape(bt_actual, bt_l)
    selected = "ARIMA" if m_a <= m_l else "LSTM"
    sel_mape = m_a if selected == "ARIMA" else m_l
    tau = max(FLOOR_PCT, sel_mape) / 100.0

    # 2. 90-day forecast with the selected model
    if selected == "ARIMA":
        mean, lower, _ = arima_forecast(hist, order, HORIZON)
    else:
        mean = lstm_forecast_mean(model, hist, HORIZON)
        sd = lstm_resid_std(model, hist)
        lower = mean - 1.96 * sd
    mean, lower = inv(mean), inv(lower)

    p0 = float(raw_native[origin_idx])
    k = int(np.argmax(mean))
    peak, lstar = float(mean[k]), float(lower[k])

    hold_proposed = (lstar - p0) / p0 > tau
    hold_naive = peak > p0

    future = raw_native[origin_idx + 1: origin_idx + 1 + HORIZON]
    rose_any = bool(future.max() > p0 * (1 + tau))      # paper's criterion
    rose_end = bool(future[-1] > p0 * (1 + tau))        # stricter criterion
    return {
        "selected": selected, "sel_mape": sel_mape, "tau_pct": tau * 100,
        "p0": p0, "peak_fc": peak, "lower_at_peak": lstar,
        "hold_proposed": hold_proposed, "hold_naive": hold_naive,
        "rose_any_90d": rose_any, "rose_at_day90": rose_end,
        "max_future_gain_pct": (float(future.max()) / p0 - 1) * 100,
    }


def part_b(metal: str, model, order, scaler, scaled: np.ndarray, raw: pd.Series, step: int):
    n = len(scaled)
    split = int(n * TRAIN_RATIO)
    first = split + max(WINDOW, HOLDOUT + 1) + 1
    origins = list(range(first, n - HORIZON - 1, step))
    rows, failures = [], 0
    raw_native = raw.to_numpy()
    for j, i in enumerate(origins, 1):
        try:
            r = decide_at(i, model, order, scaler, scaled, raw_native)
        except Exception as exc:  # pragma: no cover
            failures += 1
            print(f"    ! {metal} origin {i} failed: {exc}")
            continue
        r.update(metal=metal, date=raw.index[i].strftime("%Y-%m-%d"))
        rows.append(r)
        print(f"    [{metal}] {j}/{len(origins)} {r['date']} {r['selected']:5s} "
              f"tau={r['tau_pct']:.2f}% proposed={'HOLD' if r['hold_proposed'] else 'SELL'} "
              f"naive={'HOLD' if r['hold_naive'] else 'SELL'} rose={r['rose_any_90d']}", flush=True)
    return rows, failures


def summarise_rule(df: pd.DataFrame, col: str) -> dict:
    holds = df[df[col]]
    sells = df[~df[col]]
    k, n = int(holds["rose_any_90d"].sum()), len(holds)
    k2 = int(holds["rose_at_day90"].sum())
    lo, hi = wilson(k, n)
    return {
        "decision_points": len(df),
        "holds_issued": n,
        "correct_holds": k,
        "hold_precision_pct": (100 * k / n) if n else float("nan"),
        "precision_ci95_lo": lo, "precision_ci95_hi": hi,
        "correct_holds_day90": k2,
        "hold_precision_day90_pct": (100 * k2 / n) if n else float("nan"),
        "sells_issued": len(sells),
        "sells_correct": int((~sells["rose_any_90d"]).sum()),
        "base_rate_rise_pct": 100 * df["rose_any_90d"].mean(),
    }


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def f2(x):
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.2f}"


def write_latex_table4(df: pd.DataFrame, path: str):
    with open(path, "w", encoding="utf-8") as f:
        for _, r in df.iterrows():
            f.write(f"{r['metal'].capitalize()} & {r['arima_mape']:.2f} & {r['lstm_mape']:.2f} & "
                    f"{r['selected']} & {r['selected_rmse']:.4f} & {r['tau_pct']:.2f} \\\\\n")


def write_latex_table5(summ: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        for name, s in summ.items():
            f.write(f"{name} & {s['holds_issued']} & {s['correct_holds']} & "
                    f"{f2(s['hold_precision_pct'])} & {s['sells_issued']} \\\\\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metals", nargs="*", default=SUPPORTED_METALS)
    ap.add_argument("--step", type=int, default=30, help="days between decision dates")
    ap.add_argument("--skip-decisions", action="store_true")
    args = ap.parse_args()

    os.makedirs(RESULTS_DIR, exist_ok=True)
    t0 = time.time()
    table4, all_rows, failures = [], [], 0

    for metal in args.metals:
        print(f"\n=== {metal} ===", flush=True)
        if not (pm.has_pretrained_arima(metal) and pm.has_pretrained_lstm(metal)):
            print("  missing .pkl or .h5 -- skipped")
            continue
        fit_full = pm._load_arima_fit(metal)
        model = pm._load_lstm_model(metal)
        order = fit_full.model.order
        scaler, raw = pm._fit_matching_scaler(metal)
        scaled = scaler.transform(raw.to_numpy().reshape(-1, 1)).ravel()

        a = part_a(metal, model, order, scaler, scaled, raw)
        table4.append(a)
        print(f"  ARIMA{order} MAPE={a['arima_mape']:.2f}%  LSTM MAPE={a['lstm_mape']:.2f}%  "
              f"persistence={a['persistence_mape']:.2f}%  -> {a['selected']}, tau={a['tau_pct']:.2f}%")

        if not args.skip_decisions:
            rows, bad = part_b(metal, model, order, scaler, scaled, raw, args.step)
            all_rows += rows
            failures += bad

    t4 = pd.DataFrame(table4)
    t4.to_csv(os.path.join(RESULTS_DIR, "table4_holdout.csv"), index=False)
    write_latex_table4(t4, os.path.join(RESULTS_DIR, "table4_rows.tex"))

    summ = {}
    if all_rows:
        dp = pd.DataFrame(all_rows)
        dp.to_csv(os.path.join(RESULTS_DIR, "decision_points.csv"), index=False)
        summ = {"Naive (peak above current price)": summarise_rule(dp, "hold_naive"),
                "Proposed, (4) and (5)": summarise_rule(dp, "hold_proposed")}
        pd.DataFrame(summ).T.to_csv(os.path.join(RESULTS_DIR, "table5_decisions.csv"))
        write_latex_table5(summ, os.path.join(RESULTS_DIR, "table5_rows.tex"))
        per_metal = {m: {"proposed": summarise_rule(g, "hold_proposed"),
                         "naive": summarise_rule(g, "hold_naive")} for m, g in dp.groupby("metal")}
        with open(os.path.join(RESULTS_DIR, "table5_per_metal.json"), "w") as f:
            json.dump(per_metal, f, indent=2)

    import statsmodels, tensorflow as tf
    meta = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "runtime_s": round(time.time() - t0),
        "python": platform.python_version(), "os": platform.platform(),
        "numpy": np.__version__, "pandas": pd.__version__,
        "statsmodels": statsmodels.__version__, "tensorflow": tf.__version__,
        "holdout_days": HOLDOUT, "horizon_days": HORIZON, "lstm_window": WINDOW,
        "train_ratio": TRAIN_RATIO, "floor_pct": FLOOR_PCT, "decision_step_days": args.step,
        "usd_inr_constant": USD_INR_RATE_HISTORICAL,
        "failed_decision_points": failures,
        "table5_summary": summ,
    }
    with open(os.path.join(RESULTS_DIR, "run_metadata.json"), "w") as f:
        json.dump(meta, f, indent=2, default=str)

    print("\n================ TABLE 4 ================")
    cols = ["metal", "start", "end", "n_obs", "arima_mape", "lstm_mape", "persistence_mape",
            "selected", "selected_rmse", "tau_pct"]
    print(t4[cols].to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    if summ:
        print("\n================ TABLE 5 ================")
        print(pd.DataFrame(summ).T[["decision_points", "holds_issued", "correct_holds",
                                    "hold_precision_pct", "precision_ci95_lo", "precision_ci95_hi",
                                    "hold_precision_day90_pct", "sells_issued",
                                    "base_rate_rise_pct"]].to_string(float_format=lambda v: f"{v:.1f}"))
    print(f"\nFiles written to {RESULTS_DIR}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
