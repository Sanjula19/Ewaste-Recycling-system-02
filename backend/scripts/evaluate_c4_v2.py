"""
scripts/evaluate_c4_v2.py
--------------------------
Leakage-free, walk-forward evaluation for the Component 4 paper.
Supersedes scripts/evaluate_c4.py (kept untouched; its outputs are in results_v1/).

Run from backend/ with the project venv:

    python scripts/evaluate_c4_v2.py --dry-run --metals nickel --max-retrains 2 --out results_v2_dryrun
    python scripts/evaluate_c4_v2.py                  # full run (resumable)
    python scripts/evaluate_c4_v2.py --analysis-only  # re-run tables/figures from caches

WHAT CHANGED VS THE TRAINING NOTEBOOK / v1 (leakage fixes)
  (a) Early stopping validates on the LAST 10% of each training window,
      not on the test set (the notebook passed the test set as validation_data).
  (b) The min-max scaler is fitted on the training window only, then applied
      to later data (the notebook fitted it on the whole series).
  (c) The ARIMA order is selected with pmdarima.auto_arima on the training
      window only (the saved .pkl orders were selected on train, but the saved
      weights were refit on train+test).
  (d) Walk-forward: LSTM is retrained and the ARIMA order re-selected every
      RETRAIN_EVERY observations using ONLY data up to that retrain index r.

FROZEN DESIGN CHOICES (not tunable after seeing results)
  * LSTM: window 60; LSTM(64, l2 1e-4) -> BatchNorm -> Dropout(0.2) -> Dense(32, relu)
    -> Dense(1); Adam(1e-3), Huber loss, <=50 epochs, batch 32,
    EarlyStopping(val_loss, patience 10, restore best), ReduceLROnPlateau(0.2, 5, 1e-4).
  * Decision rule: tau = max(floor, MAPE_inner/100), floor 2%, 95% interval,
    H=30 inner holdout, K=90 horizon (Eq. 4 and 5 of the paper). Unchanged.
  * Decision date t uses the model trained at the latest retrain index r with
    r <= t - 30, so the inner 30-day holdout that sets tau is out-of-sample for
    the LSTM. Asserted in code (train_end <= t - HOLDOUT).
  * At each t, ARIMA is re-estimated (fixed order from the latest selection) on
    data up to t; LSTM weights stay frozen between retrains but its input window
    is the 60 observations up to t.
  * LSTM interval: forecast -/+ z * sd, where sd is the std of one-step residuals
    on that model's validation slice (constant width, as in the notebook).
  * Exit policy for every HOLD: target = p0*(1+tau); sell on the first day within
    90 observations with price >= target (at that day's price), else on day 90.
    A SELL realises 0 (cash at p0), so per-decision value is comparable across rules.
  * Sensitivity grid (pre-registered): floor in {0,1,2,3}% x interval in {95,80,68}%.

Outputs -> backend/<out>/  (default results_v2/). Model/decision caches ->
backend/models_walkforward/ so a crash resumes.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import random
import shutil
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from importlib import metadata
import multiprocessing as mp

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import norm

import data_loader
from data_loader import (SUPPORTED_METALS, USD_INR_RATE_HISTORICAL,
                         load_metal_series_raw, native_to_usd_per_kg, native_unit)

# --------------------------------------------------------------------------- constants
HOLDOUT = 30
HORIZON = 90
WINDOW = 60
EPOCHS = 50
BATCH = 32
VAL_FRAC = 0.10
FLOOR_DEFAULT = 0.02
LEVEL_DEFAULT = 0.95
FLOORS = [0.0, 0.01, 0.02, 0.03]            # pre-registered
LEVELS = [0.95, 0.80, 0.68]                 # pre-registered
SEED = 42
RETRAIN_EVERY = 126
START_OFFSET = 504
SPACING = 30
LEVEL_KEY = {0.95: "95", 0.80: "80", 0.68: "68"}
ALPHA = {0.95: 0.05, 0.80: 0.20, 0.68: 0.32}
Z = {lv: float(norm.ppf(0.5 + lv / 2)) for lv in LEVELS}

# --------------------------------------------------------------------------- small helpers

def seed_all(seed: int):
    import tensorflow as tf
    random.seed(seed)
    np.random.seed(seed)
    tf.keras.utils.set_random_seed(seed)


def to_scaled(x, lo, hi):
    return (np.asarray(x, dtype=float) - lo) / (hi - lo if hi > lo else 1.0)


def to_native(x, lo, hi):
    return np.asarray(x, dtype=float) * (hi - lo if hi > lo else 1.0) + lo


def mape(actual, pred):
    actual, pred = np.asarray(actual, float), np.asarray(pred, float)
    return float(np.mean(np.abs((actual - pred) / actual)) * 100)


def rmse(actual, pred):
    actual, pred = np.asarray(actual, float), np.asarray(pred, float)
    return float(np.sqrt(np.mean((actual - pred) ** 2)))


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * (c - h), 100 * (c + h))


def make_sequences(s: np.ndarray):
    X = np.lib.stride_tricks.sliding_window_view(s, WINDOW)[:-1]
    y = s[WINDOW:]
    return X[..., None].astype("float32"), y.astype("float32")


# --------------------------------------------------------------------------- models

def build_model():
    from tensorflow.keras import Sequential, Input, regularizers
    from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
    from tensorflow.keras.optimizers import Adam
    m = Sequential([
        Input((WINDOW, 1)),
        LSTM(64, return_sequences=False, kernel_regularizer=regularizers.l2(1e-4)),
        BatchNormalization(),
        Dropout(0.2),
        Dense(32, activation="relu"),
        Dense(1, activation="linear", name="LSTM_EWaste"),
    ])
    m.compile(optimizer=Adam(learning_rate=1e-3), loss="huber", metrics=["mae"])
    return m


class Bundle:
    """A trained LSTM plus its frozen metadata (scaler bounds, residual sd, order)."""

    def __init__(self, model, meta):
        import tensorflow as tf
        self.model, self.meta = model, meta
        self._f = tf.function(lambda x: self.model(x, training=False), reduce_retracing=True)

    def step(self, window):
        return float(self._f(window).numpy()[0, 0])


def lstm_path(bundle: Bundle, hist_scaled: np.ndarray, steps: int) -> np.ndarray:
    w = hist_scaled[-WINDOW:].reshape(1, WINDOW, 1).astype("float32")
    out = []
    for _ in range(steps):
        p = bundle.step(w)
        out.append(p)
        w = np.roll(w, -1, axis=1)
        w[0, -1, 0] = p
    return np.array(out)


def arima_forecast(hist_scaled: np.ndarray, order, steps: int, alphas=()):
    from statsmodels.tsa.arima.model import ARIMA
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = ARIMA(hist_scaled, order=tuple(order)).fit(method_kwargs={"warn_convergence": False})
        fc = fit.get_forecast(steps=steps)
        mean = np.asarray(fc.predicted_mean)
        lows = {a: np.asarray(fc.conf_int(alpha=a))[:, 0] for a in alphas}
        highs = {a: np.asarray(fc.conf_int(alpha=a))[:, 1] for a in alphas}
    return mean, lows, highs


def select_order(train_scaled: np.ndarray):
    import pmdarima as pm
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = pm.auto_arima(train_scaled, start_p=1, start_q=1, test="adf", max_p=3, max_q=3,
                          m=1, d=None, seasonal=False, trace=False, error_action="ignore",
                          suppress_warnings=True, stepwise=True)
    return tuple(int(v) for v in m.order)


def get_model(vals: np.ndarray, r: int, cache_dir: str, seed: int, log=print):
    """
    Train (or load) the walk-forward model whose training window is vals[:r+1].
    Everything (scaler, validation slice, ARIMA order) uses only that window.
    """
    import tensorflow as tf
    os.makedirs(cache_dir, exist_ok=True)
    mpath, jpath = os.path.join(cache_dir, f"r{r}.keras"), os.path.join(cache_dir, f"r{r}.json")
    if os.path.isfile(mpath) and os.path.isfile(jpath):
        with open(jpath) as f:
            meta = json.load(f)
        model = tf.keras.models.load_model(mpath, compile=False)
        return Bundle(model, meta), 0.0, False

    t0 = time.time()
    train = vals[: r + 1]
    lo, hi = float(train.min()), float(train.max())
    s = to_scaled(train, lo, hi)
    X, y = make_sequences(s)
    n_val = max(1, int(round(len(X) * VAL_FRAC)))
    X_tr, y_tr, X_va, y_va = X[:-n_val], y[:-n_val], X[-n_val:], y[-n_val:]

    seed_all(seed)
    model = build_model()
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    hist = model.fit(
        X_tr, y_tr.reshape(-1, 1), epochs=EPOCHS, batch_size=min(BATCH, len(X_tr)),
        validation_data=(X_va, y_va.reshape(-1, 1)), verbose=0,
        callbacks=[EarlyStopping(monitor="val_loss", patience=10, restore_best_weights=True),
                   ReduceLROnPlateau(monitor="val_loss", factor=0.2, patience=5, min_lr=1e-4)])
    resid = y_va - model.predict(X_va, verbose=0).ravel()
    order = select_order(s)
    meta = {
        "train_end": int(r), "n_train_obs": int(len(train)), "lo": lo, "hi": hi,
        "sd_scaled": float(np.std(resid)), "arima_order": list(order),
        "epochs_run": int(len(hist.history["loss"])), "n_seq_fit": int(len(X_tr)),
        "n_seq_val": int(n_val), "seed": seed,
        "best_val_loss": float(min(hist.history["val_loss"])),
        "train_seconds": round(time.time() - t0, 1),
    }
    model.save(mpath)
    with open(jpath, "w") as f:
        json.dump(meta, f)
    return Bundle(model, meta), time.time() - t0, True


# --------------------------------------------------------------------------- Table V (holdout, retrained on series[:-30])

def holdout_eval(metal: str, vals: np.ndarray, dates, cache_root: str, seed: int, log=print):
    n = len(vals)
    cache_dir = os.path.join(cache_root, metal, "holdout30")
    r = n - HOLDOUT - 1                       # training window = vals[:n-30]
    bundle, secs, trained = get_model(vals, r, cache_dir, seed, log)
    m = bundle.meta
    assert m["train_end"] == n - HOLDOUT - 1
    lo, hi, order = m["lo"], m["hi"], tuple(m["arima_order"])
    s_train = to_scaled(vals[:n - HOLDOUT], lo, hi)
    actual = vals[n - HOLDOUT:]

    a_mean, a_lo, a_hi = arima_forecast(s_train, order, HOLDOUT, alphas=(0.05,))
    l_mean = lstm_path(bundle, s_train, HOLDOUT)
    l_lo = l_mean - Z[0.95] * m["sd_scaled"]
    l_hi = l_mean + Z[0.95] * m["sd_scaled"]
    persist = np.full(HOLDOUT, s_train[-1])

    def usd(x):
        return native_to_usd_per_kg(metal, pd.Series(to_native(x, lo, hi))).to_numpy()

    act_usd = native_to_usd_per_kg(metal, pd.Series(actual)).to_numpy()
    res = {
        "metal": metal, "arima_order": str(order),
        "arima_mape": mape(act_usd, usd(a_mean)), "lstm_mape": mape(act_usd, usd(l_mean)),
        "persistence_mape": mape(act_usd, usd(persist)),
        "arima_rmse": rmse(act_usd, usd(a_mean)), "lstm_rmse": rmse(act_usd, usd(l_mean)),
        "persistence_rmse": rmse(act_usd, usd(persist)),
        "lstm_epochs": m["epochs_run"], "train_obs": m["n_train_obs"],
    }
    sel = "ARIMA" if res["arima_mape"] <= res["lstm_mape"] else "LSTM"
    res["selected"] = sel
    res["selected_mape"] = res[f"{sel.lower()}_mape"]
    res["selected_rmse"] = res[f"{sel.lower()}_rmse"]
    res["tau_pct"] = max(FLOOR_DEFAULT * 100, res["selected_mape"])
    res["beats_persistence"] = bool(res["selected_mape"] < res["persistence_mape"])
    np.savez(os.path.join(cache_dir, "arrays.npz"),
             dates=np.array([str(d.date()) for d in dates[n - HOLDOUT:]]),
             observed=act_usd, arima=usd(a_mean), arima_lo=usd(a_lo[0.05]), arima_hi=usd(a_hi[0.05]),
             lstm=usd(l_mean), lstm_lo=usd(l_lo), lstm_hi=usd(l_hi), persistence=usd(persist))
    return res


# --------------------------------------------------------------------------- walk-forward decisions

def plan(n: int, start: int, spacing: int, retrain_every: int, max_retrains=None):
    t_list = list(range(start, n - HORIZON, spacing))            # t <= n-91 -> full 90d future
    r0 = start - HOLDOUT
    r_list = []
    k = 0
    while r0 + k * retrain_every <= (t_list[-1] - HOLDOUT if t_list else -1):
        r_list.append(r0 + k * retrain_every)
        k += 1
    if max_retrains is not None:
        # keep only the decisions served by the first K retrains: t - 30 < r_K
        r_list = r_list[:max_retrains]
        t_list = [t for t in t_list if t - HOLDOUT < r0 + max_retrains * retrain_every]
    return t_list, r_list


def model_index(t: int, r_list: list[int]) -> int:
    ok = [i for i, r in enumerate(r_list) if r <= t - HOLDOUT]
    return ok[-1]


def decide(metal: str, vals: np.ndarray, t: int, bundle: Bundle):
    m = bundle.meta
    assert m["train_end"] <= t - HOLDOUT, "LEAKAGE: model trained on data inside the inner holdout"
    lo, hi, order = m["lo"], m["hi"], tuple(m["arima_order"])
    hist = vals[: t + 1]
    s = to_scaled(hist, lo, hi)

    # 1) inner 30-day holdout -> select model, tau, persistence baseline
    inner_train, inner_actual = s[:-HOLDOUT], hist[-HOLDOUT:]
    a_in, _, _ = arima_forecast(inner_train, order, HOLDOUT)
    l_in = lstm_path(bundle, inner_train, HOLDOUT)
    mape_a = mape(inner_actual, to_native(a_in, lo, hi))
    mape_l = mape(inner_actual, to_native(l_in, lo, hi))
    persist = mape(inner_actual, np.full(HOLDOUT, hist[-HOLDOUT - 1]))
    selected = "ARIMA" if mape_a <= mape_l else "LSTM"
    sel_mape = mape_a if selected == "ARIMA" else mape_l

    # 2) 90-day forecast with the selected model
    alphas = tuple(ALPHA[lv] for lv in LEVELS)
    if selected == "ARIMA":
        mean_s, lows, _ = arima_forecast(s, order, HORIZON, alphas=alphas)
        lo_native = {LEVEL_KEY[lv]: to_native(lows[ALPHA[lv]], lo, hi).tolist() for lv in LEVELS}
    else:
        mean_s = lstm_path(bundle, s, HORIZON)
        lo_native = {LEVEL_KEY[lv]: to_native(mean_s - Z[lv] * m["sd_scaled"], lo, hi).tolist() for lv in LEVELS}
    return {
        "metal": metal, "t": int(t), "train_end": m["train_end"], "order": list(order),
        "selected": selected, "arima_inner_mape": mape_a, "lstm_inner_mape": mape_l,
        "persistence_inner_mape": persist, "sel_mape": sel_mape,
        "p0": float(hist[-1]), "mean": to_native(mean_s, lo, hi).tolist(), "lo": lo_native,
        "future": vals[t + 1: t + 1 + HORIZON].tolist(),
    }


def walk_worker(job: dict):
    """One metal: train/load walk-forward models and compute every decision point (resumable)."""
    os.environ["OMP_NUM_THREADS"] = "1"
    import tensorflow as tf
    tf.config.threading.set_intra_op_parallelism_threads(job["tf_threads"])
    tf.config.threading.set_inter_op_parallelism_threads(1)
    metal = job["metal"]
    series = load_metal_series_raw(metal)
    vals = series.to_numpy()
    t_list, r_list = plan(len(vals), job["start"], job["spacing"], job["retrain_every"], job["max_retrains"])
    if job.get("max_decisions"):
        t_list = t_list[: job["max_decisions"]]
    cache_dir = os.path.join(job["cache"], metal, f"o{job['start']}_p{job['retrain_every']}")
    os.makedirs(cache_dir, exist_ok=True)
    dpath = os.path.join(cache_dir, "decisions.jsonl")
    done = set()
    if os.path.isfile(dpath):
        with open(dpath) as f:
            for line in f:
                if line.strip():
                    done.add(json.loads(line)["t"])

    stats_ = {"metal": metal, "n_decisions_planned": len(t_list), "n_retrains_planned": len(r_list),
              "trainings_done": 0, "train_seconds": 0.0, "decisions_done": 0, "decision_seconds": 0.0,
              "failed": 0}
    cur_k, bundle = None, None
    with open(dpath, "a") as out:
        for t in t_list:
            if t in done:
                continue
            k = model_index(t, r_list)
            if k != cur_k:
                bundle, secs, trained = get_model(vals, r_list[k], cache_dir, job["seed"])
                if trained:
                    stats_["trainings_done"] += 1
                    stats_["train_seconds"] += secs
                    print(f"[{metal}] retrain {k + 1}/{len(r_list)} r={r_list[k]} "
                          f"epochs={bundle.meta['epochs_run']} order={tuple(bundle.meta['arima_order'])} "
                          f"{secs:.0f}s", flush=True)
                cur_k = k
            t0 = time.time()
            try:
                rec = decide(metal, vals, t, bundle)
                rec["date"] = str(series.index[t].date())
                rec["model_k"] = k
            except AssertionError:
                raise
            except Exception as exc:  # numerical failure at one date: record, don't hide
                rec = {"metal": metal, "t": int(t), "date": str(series.index[t].date()),
                       "failed": True, "error": repr(exc)[:200]}
                stats_["failed"] += 1
            out.write(json.dumps(rec) + "\n")
            out.flush()
            stats_["decisions_done"] += 1
            stats_["decision_seconds"] += time.time() - t0
            if stats_["decisions_done"] % 10 == 0:
                print(f"[{metal}] decisions {stats_['decisions_done']}+{len(done)}/{len(t_list)}", flush=True)
    return stats_


def table5_worker(job: dict):
    os.environ["OMP_NUM_THREADS"] = "1"
    import tensorflow as tf
    tf.config.threading.set_intra_op_parallelism_threads(job["tf_threads"])
    tf.config.threading.set_inter_op_parallelism_threads(1)
    series = load_metal_series_raw(job["metal"])
    res = holdout_eval(job["metal"], series.to_numpy(), series.index, job["cache"], job["seed"])
    res["n_obs"] = len(series)
    print(f"[{job['metal']}] Table V done: ARIMA {res['arima_mape']:.2f} LSTM {res['lstm_mape']:.2f} "
          f"-> {res['selected']}", flush=True)
    return res


# --------------------------------------------------------------------------- analysis

def load_records(metal: str, job: dict):
    series = load_metal_series_raw(metal)
    t_list, r_list = plan(len(series), job["start"], job["spacing"], job["retrain_every"], job["max_retrains"])
    if job.get("max_decisions"):
        t_list = t_list[: job["max_decisions"]]
    dpath = os.path.join(job["cache"], metal, f"o{job['start']}_p{job['retrain_every']}", "decisions.jsonl")
    recs, failed = {}, 0
    if os.path.isfile(dpath):
        with open(dpath) as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    recs[r["t"]] = r
    keep = [recs[t] for t in t_list if t in recs and not recs[t].get("failed")]
    failed = sum(1 for t in t_list if t in recs and recs[t].get("failed"))
    missing = [t for t in t_list if t not in recs]
    return keep, failed, missing, series, t_list, r_list


def row_for(rec: dict, floor: float, level: float) -> dict:
    p0 = rec["p0"]
    mean = np.asarray(rec["mean"])
    lower = np.asarray(rec["lo"][LEVEL_KEY[level]])
    fut = np.asarray(rec["future"])
    tau = max(floor, rec["sel_mape"] / 100.0)
    k = int(np.argmax(mean))
    peak, lstar = float(mean[k]), float(lower[k])
    target = p0 * (1 + tau)
    hit_idx = np.flatnonzero(fut >= target)
    if hit_idx.size:
        i = int(hit_idx[0]); sell_px, hit = float(fut[i]), True
    else:
        i = HORIZON - 1; sell_px, hit = float(fut[-1]), False
    return {
        "metal": rec["metal"], "date": rec["date"], "t": rec["t"], "p0": p0,
        "selected": rec["selected"], "sel_mape": rec["sel_mape"],
        "arima_inner_mape": rec["arima_inner_mape"], "lstm_inner_mape": rec["lstm_inner_mape"],
        "persistence_mape": rec["persistence_inner_mape"],
        "beats_persistence": bool(rec["sel_mape"] < rec["persistence_inner_mape"]),
        "tau_pct": tau * 100, "peak_forecast": peak, "lower_at_peak": lstar,
        "hold_proposed": bool((lstar - p0) / p0 > tau), "hold_naive": bool(peak > p0),
        "target_hit": hit, "days_held": i + 1, "realised_gain_pct": (sell_px / p0 - 1) * 100,
        "rose_any_90d": bool(fut.max() > target), "rose_at_day90": bool(fut[-1] > target),
        "max_future_gain_pct": (float(fut.max()) / p0 - 1) * 100,
        "model_k": rec.get("model_k"), "arima_order": str(tuple(rec["order"])),
    }


def summarise(df: pd.DataFrame, col: str) -> dict:
    holds, sells = df[df[col]], df[~df[col]]
    n, k = len(holds), int(holds["target_hit"].sum())
    lo, hi = wilson(k, n)
    return {
        "decision_points": len(df), "holds": n, "target_hits": k,
        "hit_rate_pct": 100 * k / n if n else float("nan"), "ci95_lo": lo, "ci95_hi": hi,
        "mean_gain_pct": float(holds["realised_gain_pct"].mean()) if n else float("nan"),
        "median_gain_pct": float(holds["realised_gain_pct"].median()) if n else float("nan"),
        "mean_days_held": float(holds["days_held"].mean()) if n else float("nan"),
        "false_holds": n - k, "sells": len(sells), "missed_rises": int(sells["rose_any_90d"].sum()),
        "base_rate_pct": 100 * df["rose_any_90d"].mean() if len(df) else float("nan"),
        "holds_when_not_beating_persistence": int((holds["beats_persistence"] == False).sum()),
        "rose_at_day90_pct_of_holds": 100 * holds["rose_at_day90"].mean() if n else float("nan"),
    }


def per_decision_value(df: pd.DataFrame, col: str) -> np.ndarray:
    return np.where(df[col], df["realised_gain_pct"], 0.0)


def multiwindow_accuracy(df: pd.DataFrame) -> pd.DataFrame:
    """
    Accuracy across EVERY decision point, not just the final 30 observations.

    Table V reports one holdout at the end of each series, which is a single
    draw -- a model can look good or bad there by luck. These are the same
    three forecasters scored on the 30-day inner holdout of all ~85 decision
    points per metal, so the comparison against the no-change baseline rests
    on the whole decade rather than one month of it.
    """
    rows = []
    for metal, g in df.groupby("metal"):
        rows.append({
            "metal": metal,
            "decision_points": len(g),
            "first_decision": g["date"].min(),
            "last_decision": g["date"].max(),
            "arima_mean_inner_mape": float(g["arima_inner_mape"].mean()),
            "lstm_mean_inner_mape": float(g["lstm_inner_mape"].mean()),
            "persistence_mean_inner_mape": float(g["persistence_mape"].mean()),
            "selected_mean_inner_mape": float(g["sel_mape"].mean()),
            "arima_median_inner_mape": float(g["arima_inner_mape"].median()),
            "lstm_median_inner_mape": float(g["lstm_inner_mape"].median()),
            "persistence_median_inner_mape": float(g["persistence_mape"].median()),
            "pct_points_selected_beats_persistence": float(100 * g["beats_persistence"].mean()),
            "pct_points_arima_selected": float(100 * (g["selected"] == "ARIMA").mean()),
            "mean_margin_vs_persistence_pp": float((g["persistence_mape"] - g["sel_mape"]).mean()),
        })
    return pd.DataFrame(rows)


def table6_per_metal_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Table VI broken out by metal, with each metal's decision date range."""
    rows = []
    for metal, g in df.groupby("metal"):
        s = summarise(g, "hold_proposed")
        n = summarise(g, "hold_naive")
        vp = per_decision_value(g, "hold_proposed")
        vn = per_decision_value(g, "hold_naive")
        rows.append({
            "metal": metal, "decision_points": len(g),
            "first_decision": g["date"].min(), "last_decision": g["date"].max(),
            "holds_proposed": s["holds"], "hits_proposed": s["target_hits"],
            "hit_rate_pct": s["hit_rate_pct"], "ci95_lo": s["ci95_lo"], "ci95_hi": s["ci95_hi"],
            "mean_gain_pct": s["mean_gain_pct"], "median_gain_pct": s["median_gain_pct"],
            "mean_days_held": s["mean_days_held"],
            "holds_when_not_beating_persistence": s["holds_when_not_beating_persistence"],
            "mean_value_per_decision_pct": float(vp.mean()),
            "base_rate_pct": s["base_rate_pct"],
            "holds_naive": n["holds"], "hits_naive": n["target_hits"],
            "hit_rate_naive_pct": n["hit_rate_pct"],
            "mean_value_naive_per_decision_pct": float(vn.mean()),
        })
    return pd.DataFrame(rows)


def run_tests(df: pd.DataFrame, seed: int) -> dict:
    out = {}
    hp, hn = df[df.hold_proposed], df[df.hold_naive]
    a, b = int(hp.target_hit.sum()), len(hp) - int(hp.target_hit.sum())
    c, d = int(hn.target_hit.sum()), len(hn) - int(hn.target_hit.sum())
    if len(hp) and len(hn):
        odds, p = stats.fisher_exact([[a, b], [c, d]], alternative="greater")
        out["fisher_one_sided_p"] = float(p)
        out["fisher_table"] = [[a, b], [c, d]]
    else:
        out["fisher_one_sided_p"] = float("nan")
    out["fisher_note"] = ("proposed holds are a subset of naive holds, and 90-day windows 30 days apart "
                          "overlap, so the Fisher p-value is optimistic (samples not independent); see "
                          "non-overlapping subsample p-values")
    # robustness: non-overlapping 90-day subsamples (every 3rd decision per metal)
    sub = {}
    for off in range(3):
        parts = [g.sort_values("t").iloc[off::3] for _, g in df.groupby("metal")]
        s = pd.concat(parts)
        sp, sn = s[s.hold_proposed], s[s.hold_naive]
        pa, pb = int(sp.target_hit.sum()), len(sp) - int(sp.target_hit.sum())
        na, nb = int(sn.target_hit.sum()), len(sn) - int(sn.target_hit.sum())
        pv = float(stats.fisher_exact([[pa, pb], [na, nb]], alternative="greater")[1]) if len(sp) and len(sn) else float("nan")
        sub[f"offset{off}"] = {"n": len(s), "holds_proposed": len(sp), "hits_proposed": pa,
                               "holds_naive": len(sn), "hits_naive": na, "fisher_one_sided_p": pv}
    out["non_overlapping_subsamples"] = sub
    # paired test on per-decision realised value (sell = 0)
    vp, vn = per_decision_value(df, "hold_proposed"), per_decision_value(df, "hold_naive")
    diff = vp - vn
    out["mean_value_proposed_pct"] = float(vp.mean())
    out["mean_value_naive_pct"] = float(vn.mean())
    out["mean_paired_diff_pct"] = float(diff.mean())
    if np.any(diff != 0):
        out["wilcoxon_two_sided_p"] = float(stats.wilcoxon(diff, zero_method="wilcox").pvalue)
        out["paired_t_two_sided_p"] = float(stats.ttest_1samp(diff, 0.0).pvalue)
    else:
        out["wilcoxon_two_sided_p"] = float("nan")
        out["paired_t_two_sided_p"] = float("nan")
    rng = np.random.default_rng(seed)
    boots = rng.choice(diff, size=(10000, len(diff)), replace=True).mean(axis=1)
    out["paired_diff_bootstrap95"] = [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]
    out["n_decisions_where_rules_differ"] = int((diff != 0).sum())
    return out


# --------------------------------------------------------------------------- output writers (IEEE style, no colour)

def f2(x, nd=2):
    return "--" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{nd}f}"


def write_tex_table5(df: pd.DataFrame, path: str):
    lines = [r"\begin{table}[!t]", r"\caption{Holdout Forecast Accuracy (Last 30 Observations, Models Retrained Without the Holdout)}",
             r"\label{tab:holdout}", r"\centering", r"\footnotesize", r"\setlength{\tabcolsep}{3pt}",
             r"\begin{tabular}{lccccccc}", r"\hline",
             r"Metal & ARIMA order & ARIMA & LSTM & Persist. & Selected & RMSE & $\tau$ \\",
             r" & & MAPE (\%) & MAPE (\%) & MAPE (\%) & & (USD/kg) & (\%) \\", r"\hline"]
    for _, r in df.iterrows():
        lines.append(f"{r.metal.capitalize()} & {r.arima_order} & {f2(r.arima_mape)} & {f2(r.lstm_mape)} & "
                     f"{f2(r.persistence_mape)} & {r.selected} & {f2(r.selected_rmse, 3)} & {f2(r.tau_pct)} \\\\")
    lines += [r"\hline", r"\end{tabular}", r"\end{table}"]
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def write_tex_table6(summ: dict, path: str, n_points: int):
    lines = [r"\begin{table}[!t]", r"\caption{Hold Decisions Under a Take-Profit Exit (" + f"{n_points}" + r" Walk-Forward Decision Points)}",
             r"\label{tab:decisions}", r"\centering", r"\footnotesize", r"\setlength{\tabcolsep}{2.5pt}",
             r"\begin{tabular}{lcccccccc}", r"\hline",
             r"Rule & Holds & Hit (\%) & 95\% CI & Gain (\%) & Days & False & Sells & Missed \\", r"\hline"]
    short = {"Naive (peak above current price)": "Naive", "Proposed, (4) and (5)": "Proposed"}
    for name, s in summ.items():
        lines.append(f"{short.get(name, name)} & {s['holds']} & {f2(s['hit_rate_pct'], 1)} & "
                     f"[{f2(s['ci95_lo'], 1)}, {f2(s['ci95_hi'], 1)}] & {f2(s['mean_gain_pct'])} & "
                     f"{f2(s['mean_days_held'], 1)} & {s['false_holds']} & {s['sells']} & {s['missed_rises']} \\\\")
    lines += [r"\hline", r"\end{tabular}", r"\end{table}"]
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


# --------------------------------------------------------------------------- figures

def setup_mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "serif", "font.serif": ["Times New Roman", "STIXGeneral", "DejaVu Serif"],
        "mathtext.fontset": "stix", "font.size": 8, "axes.labelsize": 8, "xtick.labelsize": 8,
        "ytick.labelsize": 8, "legend.fontsize": 7, "axes.linewidth": 0.6, "lines.linewidth": 1.0,
        "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.bbox": "standard",   # exact 3.5 in column width
        "axes.grid": False,
    })
    return plt


def fig4(cache_root: str, out_dir: str, plt, metal="nickel"):
    z = np.load(os.path.join(cache_root, metal, "holdout30", "arrays.npz"))
    x = np.arange(1, len(z["observed"]) + 1)
    fig, ax = plt.subplots(figsize=(3.5, 2.4), layout="constrained")
    ax.plot(x, z["observed"], color="black", lw=1.4, label="Observed")
    ax.plot(x, z["arima"], color="0.35", ls="--", label="ARIMA")
    ax.plot(x, z["lstm"], color="0.35", ls="-.", label="LSTM")
    ax.plot(x, z["persistence"], color="0.55", ls=":", lw=1.2, label="Persistence")
    return fig, ax, z, x


def finish_fig4(fig, ax, z, x, selected: str, out_dir: str, metal: str = "nickel"):
    lo, hi = (z["arima_lo"], z["arima_hi"]) if selected == "ARIMA" else (z["lstm_lo"], z["lstm_hi"])
    ax.fill_between(x, lo, hi, color="0.85", lw=0, label=f"95% band ({selected})")
    ax.set_xlabel("Holdout day")
    ax.set_ylabel("Price (USD/kg)")
    ax.legend(frameon=False, ncol=2, loc="best")
    fig.savefig(os.path.join(out_dir, f"fig4_holdout_{metal}.pdf"))


def pick_fig4_metal(t5: pd.DataFrame) -> tuple[str, float]:
    """
    The metal whose selected model beats the no-change baseline by the
    widest margin on the Table V holdout.

    Chosen by a stated rule rather than by eye, so the figure cannot be the
    one that happened to look best. The margin is in percentage points of
    MAPE: persistence minus selected, larger is better.
    """
    margins = (t5["persistence_mape"] - t5["selected_mape"])
    i = int(margins.idxmax())
    return str(t5.loc[i, "metal"]), float(margins.loc[i])


def fig5(df: pd.DataFrame, recs_by_key: dict, series_by_metal: dict, out_dir: str, plt):
    hp = df[df.hold_proposed].copy()
    if hp.empty:
        return None
    med = hp.realised_gain_pct.median()
    hp["dist"] = (hp.realised_gain_pct - med).abs()
    pick = hp.sort_values(["dist", "t"]).iloc[0]
    rec = recs_by_key[(pick.metal, int(pick.t))]
    metal, t = pick.metal, int(pick.t)
    conv = lambda a: native_to_usd_per_kg(metal, pd.Series(np.asarray(a, float))).to_numpy()
    vals = series_by_metal[metal].to_numpy()
    hist = conv(vals[t - 59: t + 1])
    mean, lower, fut = conv(rec["mean"]), conv(rec["lo"]["95"]), conv(rec["future"])
    p0 = float(conv([rec["p0"]])[0])
    tau = pick.tau_pct / 100
    k = int(np.argmax(rec["mean"]))
    fig, ax = plt.subplots(figsize=(3.5, 2.9), layout="constrained")
    ax.plot(np.arange(-59, 1), hist, color="0.4", lw=1.0, label="Observed (history)")
    xs = np.arange(1, HORIZON + 1)
    ax.plot(xs, fut, color="black", lw=1.4, label="Actual path")
    ax.plot(xs, mean, color="0.35", ls="--", label="Forecast mean")
    ax.plot(xs, lower, color="0.55", ls="-.", label="Lower 95% bound")
    ax.plot([k + 1], [lower[k]], marker="v", color="black", ms=4, ls="none", label="Lower bound at peak")
    ax.hlines(p0 * (1 + tau), 0, HORIZON, color="black", ls=":", lw=1.0, label=r"Target $p_0(1+\tau)$")
    ax.axvline(0, color="0.75", lw=0.6)
    ax.set_xlabel("Days from decision date")
    ax.set_ylabel("Price (USD/kg)")
    hh, ll = ax.get_legend_handles_labels()
    fig.legend(hh, ll, loc="outside lower center", ncol=3, frameon=False, handlelength=1.8, columnspacing=1.0)
    fig.savefig(os.path.join(out_dir, "fig5_hold_example.pdf"))
    return {"metal": metal, "date": pick.date, "tau_pct": float(pick.tau_pct),
            "target_hit": bool(pick.target_hit), "realised_gain_pct": float(pick.realised_gain_pct),
            "days_held": int(pick.days_held), "selected": pick.selected,
            "selection_rule": "proposed-rule HOLD whose realised gain is closest to the median over all proposed HOLDs"}


def fig6(sens: pd.DataFrame, out_dir: str, plt):
    fig, ax = plt.subplots(figsize=(3.5, 2.7), layout="constrained")
    shades = {0.0: "white", 0.01: "0.75", 0.02: "0.45", 0.03: "black"}
    marks = {0.95: "o", 0.80: "s", 0.68: "^"}
    prop = sens[sens.rule == "proposed"]
    for _, r in prop.iterrows():
        if r.holds == 0 or np.isnan(r.hit_rate_pct):
            continue
        default = (abs(r.floor - FLOOR_DEFAULT) < 1e-9) and (abs(r.level - LEVEL_DEFAULT) < 1e-9)
        ax.plot(r.holds, r.hit_rate_pct, marker=marks[r.level], ms=8 if default else 5.5,
                mfc=shades[r.floor], mec="black", mew=1.6 if default else 0.7, ls="none")
    nv = sens[(sens.rule == "naive") & (np.isclose(sens.floor, FLOOR_DEFAULT))]
    if len(nv):
        ax.plot(nv.holds.iloc[0], nv.hit_rate_pct.iloc[0], marker="*", ms=9, mfc="white", mec="black", ls="none")
    from matplotlib.lines import Line2D
    h = [Line2D([], [], marker=marks[l], mfc="0.6", mec="black", ls="none", ms=5, label=f"{int(l * 100)}% interval") for l in LEVELS]
    h += [Line2D([], [], marker="o", mfc=shades[f], mec="black", ls="none", ms=5, label=f"floor {int(f * 100)}%") for f in FLOORS]
    h += [Line2D([], [], marker="*", mfc="white", mec="black", ls="none", ms=8, label="naive rule"),
          Line2D([], [], marker="o", mfc="0.45", mec="black", mew=1.6, ls="none", ms=7, label="default (2%, 95%)")]
    ax.set_xlabel("Number of holds issued")
    ax.set_ylabel("Hold precision (target hit, %)")
    ax.legend(handles=h, frameon=False, ncol=2, loc="best", handletextpad=0.3, columnspacing=0.8)
    fig.savefig(os.path.join(out_dir, "fig6_sensitivity.pdf"))


# --------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metals", nargs="*", default=SUPPORTED_METALS)
    ap.add_argument("--start-offset", type=int, default=START_OFFSET)
    ap.add_argument("--spacing", type=int, default=SPACING)
    ap.add_argument("--retrain-every", type=int, default=RETRAIN_EVERY)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--tf-threads", type=int, default=1)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", default="results_v2")
    ap.add_argument("--cache", default="models_walkforward")
    ap.add_argument("--compare-with", default="results_v1",
                    help="earlier results dir to tabulate side by side (comparison only, "
                         "never an input to anything computed here)")
    ap.add_argument("--max-retrains", type=int, default=None)
    ap.add_argument("--max-decisions", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true", help="time a small slice, print runtime estimate, exit")
    ap.add_argument("--analysis-only", action="store_true")
    args = ap.parse_args()

    out_dir = os.path.join(BACKEND_DIR, args.out)
    cache = os.path.join(BACKEND_DIR, args.cache)
    os.makedirs(out_dir, exist_ok=True)
    v1, v1_copy = os.path.join(BACKEND_DIR, "results"), os.path.join(BACKEND_DIR, "results_v1")
    if os.path.isdir(v1) and not os.path.isdir(v1_copy):
        shutil.copytree(v1, v1_copy)

    job_base = {"start": args.start_offset, "spacing": args.spacing, "retrain_every": args.retrain_every,
                "max_retrains": args.max_retrains, "max_decisions": args.max_decisions, "cache": cache,
                "seed": args.seed, "tf_threads": args.tf_threads}
    os.environ["OMP_NUM_THREADS"] = "1"
    t_start = time.time()
    t5_results, walk_stats = [], []

    if not args.analysis_only:
        ctx = mp.get_context("spawn")
        if args.dry_run:
            for m in args.metals:
                walk_stats.append(walk_worker({**job_base, "metal": m}))
        else:
            with ProcessPoolExecutor(max_workers=args.workers, mp_context=ctx) as ex:
                f5 = [ex.submit(table5_worker, {**job_base, "metal": m}) for m in args.metals]
                fw = [ex.submit(walk_worker, {**job_base, "metal": m}) for m in args.metals]
                t5_results = [f.result() for f in f5]
                walk_stats = [f.result() for f in fw]

    if args.dry_run:
        tr = sum(s["train_seconds"] for s in walk_stats) / max(1, sum(s["trainings_done"] for s in walk_stats))
        de = sum(s["decision_seconds"] for s in walk_stats) / max(1, sum(s["decisions_done"] for s in walk_stats))
        tot_r = tot_d = 0
        for m in SUPPORTED_METALS:
            n = len(load_metal_series_raw(m))
            t_list, r_list = plan(n, args.start_offset, args.spacing, args.retrain_every, None)
            tot_r += len(r_list) + 1                       # +1: the Table V model per metal
            tot_d += len(t_list)
        serial = tot_r * tr + tot_d * de
        par = serial / min(args.workers, 6) * 1.15
        print(f"\nDRY RUN: avg train {tr:.0f}s/retrain, avg decision {de:.1f}s/point "
              f"(tf_threads={args.tf_threads}, measured on {args.metals})")
        print(f"FULL RUN: {tot_r} trainings + {tot_d} decision points over 6 metals")
        print(f"ESTIMATE: serial {serial / 60:.0f} min; with {args.workers} workers ~{par / 60:.0f} min")
        return

    # ------------------------------------------------------------------ analysis
    t5_cache = []
    for m in args.metals:                                                   # reload Table V from caches
        series = load_metal_series_raw(m)
        res = next((r for r in t5_results if r["metal"] == m), None)
        if res is None:
            os.environ["OMP_NUM_THREADS"] = "1"
            res = holdout_eval(m, series.to_numpy(), series.index, cache, args.seed)
            res["n_obs"] = len(series)
        t5_cache.append(res)
    t5 = pd.DataFrame(t5_cache)
    t5.to_csv(os.path.join(out_dir, "table5_accuracy.csv"), index=False)
    write_tex_table5(t5, os.path.join(out_dir, "table5_accuracy.tex"))

    all_recs, rows_default, failed_total, missing_total = [], [], 0, 0
    ds_rows, series_by_metal, recs_by_key = [], {}, {}
    for m in args.metals:
        recs, failed, missing, series, t_list, r_list = load_records(m, job_base)
        series_by_metal[m] = series
        failed_total += failed
        missing_total += len(missing)
        for r in recs:
            recs_by_key[(m, r["t"])] = r
        all_recs += recs
        ds_rows.append({
            "metal": m, "native_unit": native_unit(m), "first_date": str(series.index[0].date()),
            "last_date": str(series.index[-1].date()), "n_obs": len(series),
            "first_decision_date": str(series.index[t_list[0]].date()) if t_list else "",
            "last_decision_date": str(series.index[t_list[-1]].date()) if t_list else "",
            "n_retrains": len(r_list), "n_decision_points": len(recs), "n_failed_points": failed,
            "n_missing_points": len(missing)})
    pd.DataFrame(ds_rows).to_csv(os.path.join(out_dir, "dataset_summary.csv"), index=False)
    if missing_total:
        print(f"WARNING: {missing_total} planned decision points are missing from the cache; "
              f"re-run without --analysis-only to finish them.")
    if not all_recs:
        print("No decision records to analyse.")
        return

    df = pd.DataFrame([row_for(r, FLOOR_DEFAULT, LEVEL_DEFAULT) for r in all_recs]).sort_values(["metal", "t"])
    df.to_csv(os.path.join(out_dir, "decisions_raw.csv"), index=False)
    summ = {"Naive (peak above current price)": summarise(df, "hold_naive"),
            "Proposed, (4) and (5)": summarise(df, "hold_proposed")}
    t6 = pd.DataFrame(summ).T
    t6.index.name = "rule"
    t6.to_csv(os.path.join(out_dir, "table6_decisions.csv"))
    write_tex_table6(summ, os.path.join(out_dir, "table6_decisions.tex"), len(df))
    per_metal = {m: {"proposed": summarise(g, "hold_proposed"), "naive": summarise(g, "hold_naive")}
                 for m, g in df.groupby("metal")}
    json.dump(per_metal, open(os.path.join(out_dir, "table6_per_metal.json"), "w"), indent=2, default=float)
    tests = run_tests(df, args.seed)
    json.dump(tests, open(os.path.join(out_dir, "tests.json"), "w"), indent=2, default=float)

    # sensitivity (reuses stored forecasts; only bounds/decisions are recomputed)
    sens_rows = []
    for fl in FLOORS:
        for lv in LEVELS:
            d = pd.DataFrame([row_for(r, fl, lv) for r in all_recs])
            s = summarise(d, "hold_proposed")
            sens_rows.append({"rule": "proposed", "floor": fl, "level": lv, **s})
        d = pd.DataFrame([row_for(r, fl, LEVEL_DEFAULT) for r in all_recs])
        sens_rows.append({"rule": "naive", "floor": fl, "level": np.nan, **summarise(d, "hold_naive")})
    sens = pd.DataFrame(sens_rows)
    sens.to_csv(os.path.join(out_dir, "sensitivity.csv"), index=False)

    # multi-window accuracy and per-metal Table VI
    mw = multiwindow_accuracy(df)
    mw.to_csv(os.path.join(out_dir, "multiwindow_accuracy.csv"), index=False)
    t6_metal = table6_per_metal_frame(df)
    t6_metal.to_csv(os.path.join(out_dir, "table6_per_metal.csv"), index=False)

    # Side-by-side with an earlier run (comparison only). Tries both naming
    # conventions: v1 wrote table4_holdout/table5_decisions, v2 onwards
    # write table5_accuracy/table6_decisions.
    prev_dir = args.compare_with if os.path.isabs(args.compare_with) else os.path.join(BACKEND_DIR, args.compare_with)
    prev_tag = os.path.basename(prev_dir.rstrip("/\\")) or "prev"
    this_tag = os.path.basename(out_dir.rstrip("/\\"))
    cmp_rows = []
    prev_t5 = next((p for p in (os.path.join(prev_dir, "table5_accuracy.csv"),
                                os.path.join(prev_dir, "table4_holdout.csv")) if os.path.isfile(p)), None)
    if prev_t5:
        o = pd.read_csv(prev_t5).set_index("metal")
        for _, r in t5.iterrows():
            if r.metal in o.index:
                row = {"metal": r.metal}
                for col in ("arima_mape", "lstm_mape", "persistence_mape", "selected", "tau_pct"):
                    row[f"{prev_tag}_{col}"] = o.loc[r.metal, col] if col in o.columns else None
                    row[f"{this_tag}_{col}"] = r[col]
                cmp_rows.append(row)
        pd.DataFrame(cmp_rows).to_csv(
            os.path.join(out_dir, f"comparison_{prev_tag}_vs_{this_tag}_table5.csv"), index=False)

    prev_t6 = next((p for p in (os.path.join(prev_dir, "table6_decisions.csv"),
                                os.path.join(prev_dir, "table5_decisions.csv")) if os.path.isfile(p)), None)
    if prev_t6:
        o = pd.read_csv(prev_t6, index_col=0)
        rows = []
        for name in ("Naive (peak above current price)", "Proposed, (4) and (5)"):
            if name in o.index:
                def prev(*names):
                    for c in names:
                        if c in o.columns:
                            return o.loc[name, c]
                    return None
                rows.append({
                    "rule": name,
                    f"{prev_tag}_points": prev("decision_points"),
                    f"{prev_tag}_holds": prev("holds", "holds_issued"),
                    f"{prev_tag}_hits": prev("target_hits", "correct_holds"),
                    f"{prev_tag}_hit_rate_pct": prev("hit_rate_pct", "hold_precision_pct"),
                    f"{prev_tag}_mean_gain_pct": prev("mean_gain_pct"),
                    f"{this_tag}_points": summ[name]["decision_points"],
                    f"{this_tag}_holds": summ[name]["holds"],
                    f"{this_tag}_hits": summ[name]["target_hits"],
                    f"{this_tag}_hit_rate_pct": summ[name]["hit_rate_pct"],
                    f"{this_tag}_mean_gain_pct": summ[name]["mean_gain_pct"],
                })
        pd.DataFrame(rows).to_csv(
            os.path.join(out_dir, f"comparison_{prev_tag}_vs_{this_tag}_table6.csv"), index=False)

    # figures
    plt = setup_mpl()
    fig4_metal, fig4_margin = pick_fig4_metal(t5)
    fig4_selected = t5.set_index("metal").loc[fig4_metal, "selected"]
    fig, ax, z, x = fig4(cache, out_dir, plt, metal=fig4_metal)
    finish_fig4(fig, ax, z, x, fig4_selected, out_dir, metal=fig4_metal)
    fig5_info = fig5(df, recs_by_key, series_by_metal, out_dir, plt)
    fig6(sens, out_dir, plt)

    # run metadata
    def ver(p):
        try:
            return metadata.version(p)
        except Exception:
            return None
    # Whether any currency conversion is actually applied on this dataset.
    # v3 is already USD/kg, so native_to_usd_per_kg is the identity and the
    # old flat INR constant plays no part -- recorded as such rather than
    # reprinting 87.5 as though it had been used.
    conv_factors = {m: float(native_to_usd_per_kg(m, 1.0)) for m in args.metals}
    inr_applied = any(f != 1.0 for f in conv_factors.values())

    meta = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "runtime_s_this_invocation": round(time.time() - t_start),
        "data_version": data_loader.data_version(),
        "data_source": ("data/v3/<metal>.csv, already USD/kg"
                        if data_loader.data_version() == "v3" else "data/<metal>_Historical_Data.csv"),
        "unit_conversion_applied_per_metal": conv_factors,
        "settings": {"holdout": HOLDOUT, "horizon": HORIZON, "window": WINDOW, "epochs_max": EPOCHS,
                     "batch": BATCH, "val_frac": VAL_FRAC, "floor_default": FLOOR_DEFAULT,
                     "level_default": LEVEL_DEFAULT, "floors_grid": FLOORS, "levels_grid": LEVELS,
                     "start_offset_obs": args.start_offset, "spacing_obs": args.spacing,
                     "retrain_every_obs": args.retrain_every, "max_retrains": args.max_retrains,
                     "usd_inr_constant": USD_INR_RATE_HISTORICAL if inr_applied else None,
                     "usd_inr_constant_applied": inr_applied, "z_values": Z},
        "seeds": {"base_seed": args.seed, "applied_via": "random.seed, np.random.seed, tf.keras.utils.set_random_seed before every training"},
        "versions": {"python": platform.python_version(), "os": platform.platform(),
                     **{p: ver(p) for p in ["numpy", "pandas", "scipy", "statsmodels", "pmdarima", "tensorflow",
                                            "keras", "scikit-learn", "matplotlib"]}},
        "leakage_controls": ["scaler fit on training window only", "early stopping validated on last 10% of training window",
                             "ARIMA order via auto_arima on training window only", "model for decision t trained with train_end <= t-30 (asserted)",
                             "LSTM band sd from validation residuals only"],
        "n_decision_points": len(df), "n_failed_points": failed_total, "n_missing_points": missing_total,
        "fig4_metal": fig4_metal, "fig4_selection_rule": (
            "metal whose selected model beats the no-change baseline by the largest MAPE "
            "margin on the Table V holdout"),
        "fig4_margin_pp": fig4_margin, "fig4_selected_model": fig4_selected,
        "multiwindow_accuracy": mw.to_dict(orient="records"),
        "fig5_example": fig5_info,
        "table6": summ, "tests": tests,
        "holds_when_selected_not_beating_persistence": {
            "proposed": summ["Proposed, (4) and (5)"]["holds_when_not_beating_persistence"],
            "naive": summ["Naive (peak above current price)"]["holds_when_not_beating_persistence"]},
        "share_decisions_selected_beats_persistence_pct": float(100 * df.beats_persistence.mean()),
    }
    json.dump(meta, open(os.path.join(out_dir, "run_meta.json"), "w"), indent=2, default=str)

    print("\n=========== TABLE V (retrained on series[:-30]) ===========")
    print(t5[["metal", "arima_order", "arima_mape", "lstm_mape", "persistence_mape", "selected",
              "selected_rmse", "tau_pct", "beats_persistence"]].to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    print("\n=========== MULTI-WINDOW ACCURACY (all decision points) ===========")
    print(mw[["metal", "decision_points", "first_decision", "last_decision",
              "arima_mean_inner_mape", "lstm_mean_inner_mape", "persistence_mean_inner_mape",
              "selected_mean_inner_mape", "pct_points_selected_beats_persistence",
              "pct_points_arima_selected"]].to_string(index=False, float_format=lambda v: f"{v:.2f}"))

    print("\n=========== TABLE VI (walk-forward, take-profit exit) ===========")
    print(t6[["decision_points", "holds", "target_hits", "hit_rate_pct", "ci95_lo", "ci95_hi", "mean_gain_pct",
              "median_gain_pct", "mean_days_held", "false_holds", "sells", "missed_rises", "base_rate_pct",
              "holds_when_not_beating_persistence"]].to_string(float_format=lambda v: f"{v:.2f}"))
    print("\n=========== TABLE VI PER METAL ===========")
    print(t6_metal[["metal", "decision_points", "first_decision", "last_decision", "holds_proposed",
                    "hits_proposed", "hit_rate_pct", "ci95_lo", "ci95_hi", "mean_gain_pct",
                    "median_gain_pct", "holds_when_not_beating_persistence",
                    "mean_value_per_decision_pct", "base_rate_pct"]]
          .to_string(index=False, float_format=lambda v: f"{v:.2f}"))

    print("\nTESTS:", json.dumps(tests, indent=1, default=float))
    print(f"\nFigure 4 metal: {fig4_metal} ({fig4_selected}), margin vs no-change "
          f"{fig4_margin:.2f} pp -- the largest of the six")
    print(f"Data version: {data_loader.data_version()}; unit conversion applied: {inr_applied}")
    print(f"\nDecision points: {len(df)} (failed {failed_total}, missing {missing_total}). Outputs: {out_dir}")


if __name__ == "__main__":
    main()
