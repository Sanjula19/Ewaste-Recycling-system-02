# results_v1/ — v1 evaluation output

**Superseded by results_v3 — kept for provenance; v1/v2 contain the leakage that was later corrected.**

Produced by `scripts/evaluate_c4.py` (the original evaluator, itself
superseded by `scripts/evaluate_c4_v2.py`).

This directory is **byte-for-byte identical to `results/`** — `results/` is
the script's default output folder and this is the copy kept once a
versioned naming scheme was adopted. One run, two folders.

## Why these numbers must not be quoted

Two independent problems, both fixed in v3:

1. **Leakage.** The scaler was fitted on the whole series, the LSTM's early
   stopping validated on the test set, and saved ARIMA weights were refitted
   on train+test. The resulting accuracy is optimistic by an unknown margin.
2. **A single flat exchange rate.** Five of six metals were MCX exports in
   INR/kg divided by one constant (87.5 INR/USD) across a decade. v3 uses
   native-USD contracts with no FX constant in the path.

`scripts/evaluate_c4_v2.py` documents the five specific leakage controls
that replaced the v1 pipeline, each asserted at runtime.

`run_log.txt` is gitignored — a regenerable transcript, not a result.

**Cite `results_v3/`.**
