# results/ — v1 evaluation output

**Superseded by results_v3 — kept for provenance; v1/v2 contain the leakage that was later corrected.**

Produced by `scripts/evaluate_c4.py` (the original evaluator, itself
superseded by `scripts/evaluate_c4_v2.py`).

This directory is **byte-for-byte identical to `results_v1/`** — it is the
script's default output folder, and `results_v1/` is the copy kept once a
versioned naming scheme was adopted. They are one run, not two.

## Why these numbers must not be quoted

Two independent problems, both fixed in v3:

1. **Leakage.** The v1 pipeline fitted the min-max scaler on the whole
   series, passed the test set as the LSTM's `validation_data` for early
   stopping, and refitted saved ARIMA weights on train+test. Accuracy
   measured that way is optimistic by an unknown margin.
2. **A single flat exchange rate.** Five of the six metals were MCX exports
   in INR/kg, divided by one constant (87.5 INR/USD) across a decade of
   history. v3 is built from native-USD contracts with no FX constant
   anywhere in the path.

Model selection changes between the versions as a result, so mixing figures
from here with v3 produces a table that contradicts itself.

`run_log.txt` is gitignored — a regenerable transcript, not a result.

**Cite `results_v3/`.**
