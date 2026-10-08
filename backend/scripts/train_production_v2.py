"""
scripts/train_production_v2.py
------------------------------
Retrains the six production models with the leakage-free pipeline of
scripts/evaluate_c4_v2.py and writes them to backend/models_v2/.

The training code is not re-implemented here: build_model(), seed_all(),
make_sequences(), select_order(), to_scaled() and the constants
(WINDOW/EPOCHS/BATCH/VAL_FRAC/SEED) are IMPORTED from evaluate_c4_v2, so the
architecture, optimiser, loss, callbacks, validation split and seeds cannot
drift away from the evaluated ones. The only difference is the training
window: evaluate_c4_v2 trains on vals[:r+1] at each walk-forward index r,
while this script trains once per metal on the whole available series
(r = n-1), which is what a production model should see.

    cd backend
    venv/Scripts/python.exe scripts/train_production_v2.py
    venv/Scripts/python.exe scripts/train_production_v2.py --metals nickel

Artifacts per metal, in backend/models_v2/:
    arima_<metal>.pkl    statsmodels ARIMAResults, order from auto_arima,
                         fitted on the MinMax-scaled full series
    lstm_<metal>.keras   the Keras model, native format
    scaler_<metal>.pkl   the fitted sklearn MinMaxScaler (joblib)
    meta_<metal>.json    per-metal training record, incl. sd_scaled for the
                         LSTM interval and the selected ARIMA order
    training_meta.json   one roll-up for all metals (settings, seeds, data
                         end dates, library versions, ARIMA order per metal)

Nothing in backend/models/ is touched.
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import platform
import sys
import time
import warnings
from datetime import datetime
from importlib import metadata

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, os.path.join(BACKEND_DIR, "scripts"))

import joblib
import numpy as np
from sklearn.preprocessing import MinMaxScaler

from data_loader import SUPPORTED_METALS, USD_INR_RATE_HISTORICAL, MATERIAL_CONFIG, load_metal_series_raw

# The training recipe itself -- imported, never re-typed.
from evaluate_c4_v2 import (BATCH, EPOCHS, HOLDOUT, HORIZON, SEED, VAL_FRAC, WINDOW,
                            build_model, holdout_eval, make_sequences, seed_all,
                            select_order, to_scaled)

HOLDOUT_KEYS = ("arima_order", "arima_mape", "lstm_mape", "persistence_mape",
                "arima_rmse", "lstm_rmse", "persistence_rmse", "selected",
                "selected_mape", "selected_rmse", "tau_pct", "beats_persistence",
                "lstm_epochs", "train_obs")


def holdout30_metrics(metal: str, seed: int, cache_root: str) -> dict:
    """
    Honest 30-day holdout accuracy for this pipeline (Table V of the paper).

    The production models are trained on every observation, so they have no
    holdout of their own. evaluate_c4_v2.holdout_eval trains a twin on
    series[:-30] with the identical recipe and scores ARIMA, LSTM and a
    no-change (persistence) baseline on the withheld 30 observations, in
    USD/kg -- that twin is how the production model's accuracy is honestly
    estimated. Loads from models_walkforward/<metal>/holdout30/ when the
    twin is already cached, so this is normally free.

    The backend reads these numbers to pick ARIMA vs LSTM and to run the
    no-forecastable-signal check, instead of the in-sample 80/20 split it
    used to select on.
    """
    series = load_metal_series_raw(metal)
    res = holdout_eval(metal, series.to_numpy(), series.index, cache_root, seed)
    out = {k: res[k] for k in HOLDOUT_KEYS}
    out["holdout_obs"] = HOLDOUT
    out["note"] = ("models retrained on series[:-30]; arima_order here is the order "
                   "auto_arima picked on that window, which can differ from the "
                   "production order selected on the full series")
    return out


def train_one(metal: str, out_dir: str, seed: int, cache_root: str) -> dict:
    """Train ARIMA + LSTM for one metal on its full series and save the artifacts."""
    import tensorflow as tf
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    from statsmodels.tsa.arima.model import ARIMA

    t0 = time.time()
    series = load_metal_series_raw(metal)
    vals = series.to_numpy()

    # --- scaler: fitted on the training data only, which here IS the whole
    # series. Saved so inference never refits it (see pretrained_models.py).
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaler.fit(vals.reshape(-1, 1))
    lo, hi = float(scaler.data_min_[0]), float(scaler.data_max_[0])
    s = to_scaled(vals, lo, hi)          # identical to scaler.transform(), same lo/hi

    # --- LSTM (same code path as evaluate_c4_v2.get_model) -----------------
    X, y = make_sequences(s)
    n_val = max(1, int(round(len(X) * VAL_FRAC)))
    X_tr, y_tr, X_va, y_va = X[:-n_val], y[:-n_val], X[-n_val:], y[-n_val:]

    seed_all(seed)
    model = build_model()
    hist = model.fit(
        X_tr, y_tr.reshape(-1, 1), epochs=EPOCHS, batch_size=min(BATCH, len(X_tr)),
        validation_data=(X_va, y_va.reshape(-1, 1)), verbose=0,
        callbacks=[EarlyStopping(monitor="val_loss", patience=10, restore_best_weights=True),
                   ReduceLROnPlateau(monitor="val_loss", factor=0.2, patience=5, min_lr=1e-4)])
    resid = y_va - model.predict(X_va, verbose=0).ravel()
    sd_scaled = float(np.std(resid))

    # Native .keras only: pretrained_models._lstm_path() prefers it, and a
    # legacy .h5 twin of the same weights would just be a second source of
    # truth to keep in sync.
    model.save(os.path.join(out_dir, f"lstm_{metal}.keras"))

    # --- ARIMA: order on the scaled series via auto_arima, then the fit ----
    order = select_order(s)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = ARIMA(s, order=order).fit(method_kwargs={"warn_convergence": False})
    with open(os.path.join(out_dir, f"arima_{metal}.pkl"), "wb") as f:
        pickle.dump(fit, f)

    joblib.dump(scaler, os.path.join(out_dir, f"scaler_{metal}.pkl"))

    meta = {
        "metal": metal,
        "native_unit": MATERIAL_CONFIG[metal].native_unit,
        "n_obs": int(len(vals)),
        "first_date": str(series.index[0].date()),
        "last_date": str(series.index[-1].date()),
        "train_end_index": int(len(vals) - 1),
        "scaler": {"type": "sklearn.MinMaxScaler", "feature_range": [0, 1],
                   "data_min": lo, "data_max": hi, "fitted_on": "full training series (native units)"},
        "lstm": {"window": WINDOW, "n_seq_fit": int(len(X_tr)), "n_seq_val": int(n_val),
                 "epochs_run": int(len(hist.history["loss"])),
                 "best_val_loss": float(min(hist.history["val_loss"])),
                 "sd_scaled": sd_scaled,
                 "sd_scaled_source": "std of one-step residuals on the last 10% validation slice"},
        "arima_order": list(order),
        "arima_aic": float(fit.aic),
        "seed": seed,
        "train_seconds": round(time.time() - t0, 1),
        "holdout30": holdout30_metrics(metal, seed, cache_root),
    }
    with open(os.path.join(out_dir, f"meta_{metal}.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"[{metal}] n={len(vals)} epochs={meta['lstm']['epochs_run']} order={order} "
          f"sd_scaled={sd_scaled:.5f} {meta['train_seconds']:.0f}s", flush=True)
    return meta


def refresh_meta(metal: str, out_dir: str, seed: int, cache_root: str) -> dict:
    """
    Recompute only the holdout30 block of an already-trained metal, leaving
    its weights, scaler and ARIMA pickle untouched. Lets the honest holdout
    metrics be added to models that are already in place without retraining
    them (which would be a no-op at this seed anyway, but would rewrite
    artifacts the backend is serving).
    """
    path = os.path.join(out_dir, f"meta_{metal}.json")
    with open(path) as f:
        meta = json.load(f)
    meta["holdout30"] = holdout30_metrics(metal, seed, cache_root)
    with open(path, "w") as f:
        json.dump(meta, f, indent=2)
    h = meta["holdout30"]
    print(f"[{metal}] holdout30 ARIMA {h['arima_mape']:.2f} LSTM {h['lstm_mape']:.2f} "
          f"persistence {h['persistence_mape']:.2f} -> {h['selected']} "
          f"(beats persistence: {h['beats_persistence']})", flush=True)
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metals", nargs="*", default=SUPPORTED_METALS)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", default="models_v2")
    ap.add_argument("--cache", default="models_walkforward",
                    help="where holdout_eval's retrained-on-series[:-30] twins are cached")
    ap.add_argument("--refresh-meta-only", action="store_true",
                    help="recompute holdout30 metrics for already-trained models; do not retrain")
    args = ap.parse_args()

    out_dir = os.path.join(BACKEND_DIR, args.out)
    cache_root = os.path.join(BACKEND_DIR, args.cache)
    os.makedirs(out_dir, exist_ok=True)
    t_start = time.time()

    if args.refresh_meta_only:
        metas = [refresh_meta(m, out_dir, args.seed, cache_root) for m in args.metals]
    else:
        metas = [train_one(m, out_dir, args.seed, cache_root) for m in args.metals]

    def ver(p):
        try:
            return metadata.version(p)
        except Exception:
            return None

    roll = {
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "trained_by": "scripts/train_production_v2.py",
        "training_code_imported_from": "scripts/evaluate_c4_v2.py",
        "runtime_s": round(time.time() - t_start),
        "settings": {
            "window": WINDOW, "epochs_max": EPOCHS, "batch": BATCH, "val_frac": VAL_FRAC,
            "lstm_architecture": "LSTM(64, l2 1e-4) -> BatchNorm -> Dropout(0.2) -> Dense(32, relu) -> Dense(1)",
            "optimizer": "Adam(learning_rate=1e-3)", "loss": "huber", "metrics": ["mae"],
            "early_stopping": {"monitor": "val_loss", "patience": 10, "restore_best_weights": True},
            "reduce_lr_on_plateau": {"monitor": "val_loss", "factor": 0.2, "patience": 5, "min_lr": 1e-4},
            "validation_split": "last 10% of the training data (chronological, never the future)",
            "scaler": "sklearn MinMaxScaler(0,1) fitted on the training data only, saved per metal",
            "arima_auto_arima": {"start_p": 1, "start_q": 1, "test": "adf", "max_p": 3, "max_q": 3,
                                 "d": None, "m": 1, "seasonal": False, "stepwise": True},
            "arima_fit": "statsmodels ARIMA(order).fit() on the MinMax-scaled full series",
            "training_window": "ALL available observations per metal (no holdout withheld)",
            "inference_horizon": HORIZON, "evaluation_holdout_in_paper": HOLDOUT,
            "usd_inr_constant": USD_INR_RATE_HISTORICAL,
        },
        "seeds": {"base_seed": args.seed,
                  "applied_via": "random.seed, np.random.seed, tf.keras.utils.set_random_seed before building the model"},
        "leakage_controls": [
            "MinMaxScaler fitted on training data only and SAVED, so inference does not refit it",
            "early stopping validated on the last 10% of the training data, never on future data",
            "ARIMA order selected by auto_arima on the training data only",
            "LSTM interval sd taken from validation residuals, not from data the model was scored on",
        ],
        "note": ("These are production models: they are trained on every observation, so they have no "
                 "holdout of their own. The honest accuracy figures for this pipeline are the retrained "
                 "last-30-observation holdout in results_v2/table5_accuracy.csv."),
        "arima_order_per_metal": {m["metal"]: m["arima_order"] for m in metas},
        "holdout30_per_metal": {
            m["metal"]: {k: m["holdout30"][k] for k in
                         ("selected", "selected_mape", "persistence_mape", "beats_persistence")}
            for m in metas if "holdout30" in m},
        "data_end_dates": {m["metal"]: m["last_date"] for m in metas},
        "data_start_dates": {m["metal"]: m["first_date"] for m in metas},
        "n_obs_per_metal": {m["metal"]: m["n_obs"] for m in metas},
        "versions": {"python": platform.python_version(), "os": platform.platform(),
                     **{p: ver(p) for p in ["numpy", "pandas", "scipy", "statsmodels", "pmdarima",
                                            "tensorflow", "keras", "scikit-learn", "joblib"]}},
        "per_metal": {m["metal"]: m for m in metas},
    }
    with open(os.path.join(out_dir, "training_meta.json"), "w") as f:
        json.dump(roll, f, indent=2)
    print(f"\nWrote {len(metas)} metals to {out_dir} in {roll['runtime_s']}s")


if __name__ == "__main__":
    main()
