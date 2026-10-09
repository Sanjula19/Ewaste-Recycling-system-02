# results_v2/ — leakage-free pipeline, still on the v1 INR dataset

**Superseded by results_v3 — kept for provenance; v1/v2 contain the leakage that was later corrected.**

Produced by `scripts/evaluate_c4_v2.py` against the **v1** price data.

## What v2 fixed, and what it did not

v2 is where the five leakage controls landed, and they are the reason v3's
numbers can be trusted:

1. Scaler fitted on the training window only.
2. Early stopping validated on the last 10% of the training window — the v1
   pipeline passed the test set as `validation_data`.
3. ARIMA order selected by `auto_arima` on the training window only.
4. Walk-forward: the model used for decision `t` is trained with
   `train_end <= t - 30`, asserted at runtime.
5. LSTM interval width from validation residuals only.

**But v2 still ran on the v1 dataset** — five of the six metals as MCX
exports in INR/kg, divided by one flat constant (87.5 INR/USD) applied
across a decade of history. That is the defect v3 exists to remove: it is
built from native-USD contracts with no FX constant anywhere in the path.

## Why the difference matters

Model selection *changes* between v2 and v3 for two metals — aluminium and
copper both flip from LSTM to ARIMA — so quoting a v2 figure beside a v3
one produces a table that contradicts itself.
`comparison_results_v2_vs_results_v3_table5.csv` in `results_v3/` shows the
whole comparison side by side.

## What is still live in here

Three files in this directory are **not** superseded and are referenced by
current work:

- `latency_before_after.csv` — the endpoint response-time benchmark
  (n = 50 warm requests per endpoint). This is the source for the paper's
  response-time figures; there is no v3 equivalent.
- `forecast_baseline_pristine.json`, `forecast_baseline_pre_change3.json` —
  golden baselines a regression test compares against. Do not regenerate
  them to "refresh" them; that would defeat their purpose.

`../results_v2_run_log.txt` and `../results_v2_analysis_log.txt` are
gitignored — regenerable transcripts, not results.

**For accuracy and decision figures, cite `results_v3/`.**
