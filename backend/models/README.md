# models/ — your trained model artifacts go here

Drop your files in directly, using this naming convention (matches what
`services/pretrained_models.py` looks for):

```
models/
├── arima_aluminium_model.pkl
├── lstm_aluminium_model.h5
├── arima_copper_model.pkl
├── lstm_copper_model.h5
├── arima_lead_model.pkl
├── lstm_lead_model.h5
├── arima_nickel_model.pkl
├── lstm_nickel_model.h5
├── arima_steel_model.pkl
├── lstm_steel_model.h5
├── arima_zinc_model.pkl
├── lstm_zinc_model.h5
└── reference/
    └── thermodynamic_properties_db.json   (already included -- see below)
```

Your `arima_gold_model.pkl` / `lstm_gold_model.h5` and
`arima_silver_model.pkl` / `lstm_silver_model.h5` are fine to leave out —
gold and silver are out of scope for this component, so they're never
looked up.

## How these get used

`POST /api/forecast/` now tries, in order:

1. **Your saved model** — if `arima_<metal>_model.pkl` and/or
   `lstm_<metal>_model.h5` exist, they're loaded, run for a 90-day
   forecast, and backtested for a real MAPE/RMSE (see
   `services/pretrained_models.py` docstring for exactly how — it
   replicates your `ewaste_preprocessing.py` scaler and
   `ewaste_model_training.py` forecasting logic, not an approximation of
   it). If both a `.pkl` and `.h5` exist for a metal, whichever backtests
   with the lower MAPE is used, and `model_used` in the response tells
   you which one won.
2. **Live fit** — if neither file is present (or `tensorflow`/`statsmodels`
   aren't installed), the endpoint fits ARIMA fresh from `data/*.csv`
   instead, exactly like before you sent these files. Nothing breaks
   either way.

## Which folder is served: `MODEL_DIR`

`services/pretrained_models.py` reads its artifacts from the folder named
by the `MODEL_DIR` environment variable, relative to `backend/`. It
defaults to `models`, so everything above describes the behaviour when
`MODEL_DIR` is unset.

`MODEL_DIR=models_v2` serves the retrained, leakage-free models instead
(`scripts/train_production_v2.py`, same recipe as
`scripts/evaluate_c4_v2.py`). Both naming conventions are accepted —
`arima_<metal>_model.pkl` / `lstm_<metal>_model.h5` here, and
`arima_<metal>.pkl` / `lstm_<metal>.keras` in `models_v2/`.

The one behavioural difference is the scaler. This folder has no
`scaler_<metal>.pkl`, so the backend refits a `MinMaxScaler` on the full
series at request time — which is what the original notebook did, and
which re-derives the scaling bounds from data outside the model's
training window. `models_v2/` ships the scaler that training actually
fitted, and the backend loads it instead of refitting. Same story for the
LSTM band width (`meta_<metal>.json` → `lstm.sd_scaled`).

## `reference/thermodynamic_properties_db.json`

This is the actual database your `strategic_disposition.py` generated
from the MatWeb/EPA WARM CSVs (trimmed here to the entries relevant to
this component's 3 in-scope residuals, plus a few for context — the full
50+-material version is what you already have from your own Colab run).
`materials_db.py` pulls its PVC / Polystyrene / Contaminated Glass
numbers straight from this file's values rather than re-estimating them.
