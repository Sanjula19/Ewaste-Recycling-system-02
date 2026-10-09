# Component 4 — Numbers for the Conference Paper

**Component:** Predictive Economic Valuation & Strategic Disposition Terminal
**Project:** R26-IT-015 — AI-Powered Automated Waste Segregation & E-Waste Recycling System
**Compiled:** 2026-10-09
**Authoritative run:** `backend/results_v3/` (run_at `2026-10-09T07:24:43`, runtime 22,832 s ≈ 6 h 20 m)

Every figure below is copied from a file in this repository, or recomputed from one.
Items **12, 13 and 15 have no measured data yet** — see §12–15. Nothing in this
document is estimated, rounded up, or filled in from a similar project.

> **Use `results_v3`, not `results_v2` or `results_v1`.** v1 converted a decade of
> MCX INR prices at one flat rate (87.5 INR/USD); v2 inherited that. v3 is built from
> native-USD exports with no FX constant anywhere in the pipeline. Model selection
> flips between v2 and v3 for aluminium and copper (LSTM to ARIMA), so mixing runs
> will produce a table that contradicts itself.

---

## 1. Actual metal price dataset

Daily settlement/closing prices exported from **Investing.com**, one contract per
metal, cleaned and converted to **USD/kg** by `backend/scripts/build_dataset_v3.py`.

- Raw exports: `backend/data/source_v3/*.csv`
- Built series: `backend/data/v3/<metal>.csv` (columns `date,price_usd_kg`)
- Build provenance: `backend/data/v3/dataset_summary.csv`

| Metal | Contract | Source file | Quoted unit | Conversion to USD/kg |
|---|---|---|---|---|
| Aluminium | Aluminium (LME) | `Aluminium Historical Data.csv` | USD/tonne | x0.001 |
| Copper | Copper Futures (COMEX) | `Copper Futures Historical Data.csv` | **USD/pound** | x2.2046226218 |
| Lead | Lead Futures (LME) | `Lead Futures Historical Data.csv` | USD/tonne | x0.001 |
| Nickel | Nickel Futures (LME) | `Nickel Futures Historical Data.csv` | USD/tonne | x0.001 |
| Steel | Steel Scrap Futures | `Steel Scrap Futures Historical Data (1).csv` | USD/tonne | x0.001 |
| Zinc | Zinc Futures (LME) | `Zinc Futures Historical Data .csv` | USD/tonne | x0.001 |

The quote unit is **inferred per file and sanity-checked**, not assumed: a median
above 150 USD can only be a per-tonne quote, while copper's 4-decimal prices with
volume on 97% of rows identify the COMEX per-pound tick. A converted series is
rejected if it falls outside 0.05-200 USD/kg. Date order (MM/DD vs DD-MM) is settled
by exclusion — whichever field exceeds 12 somewhere in the file is the day; five
files are `%m/%d/%Y`, copper is `%d-%m-%Y`.

**Data quality, as built:** 0 missing prices, 0 zero prices, 0 negative prices across
all six series. 1 duplicate date dropped (nickel). Gaps over 5 trading days: 5
(nickel only). Single-day moves over 15%: copper 1, nickel 4, steel 4 — all flagged,
none removed.

### Unit label — bug found and fixed 2026-10-09

The v3 output files used to print `native_unit = INR_per_kg` (and `USD_per_ton` for
steel), because `evaluate_c4_v2.py:829` and `train_production_v2.py:145` both read
`MATERIAL_CONFIG[m].native_unit` — the **v1** table — instead of the config resolved
for the active `DATA_VERSION`. **The prices were always correct**; only the printed
label was wrong (`run_meta.json` records a conversion factor of 1.0 for all six metals,
and the decision prices are plainly USD/kg — nickel 7.59-49.78, steel 0.238-0.636).

Fixed as follows:

- `data_loader.native_unit(metal)` added — returns the unit for whichever dataset
  `data_version()` selects (`USD_per_kg` under v3, the v1 table under v1). Both scripts
  now call it, and neither imports `MATERIAL_CONFIG` any more.
- The already-generated labels were corrected in place, so no 6-hour re-run was needed:
  6 rows in `results_v3/dataset_summary.csv`, and 12 occurrences across
  `models_v3/meta_*.json` + `models_v3/training_meta.json`. **Only that one field was
  touched** — every other value in those files is byte-identical, confirmed by diff.
- `results_v1/`, `results_v2/`, `models/` and `models_v2/` were deliberately left alone:
  they were produced from the v1 MCX data, where `INR_per_kg` / `USD_per_ton` is the
  correct label.

**The unit to state in the paper is USD/kg for all six metals.** Verified: `pytest`
64 passed, 0 failed after the change.

### Related bug, NOT fixed — flagged only

`services/pretrained_models.py:160` has the same root cause in a different place:
`_series_signature()` stats `DATA_DIR/MATERIAL_CONFIG[metal].filename`, i.e. the **v1**
CSV, even when v3 is active — so appending a row to a v3 series does not invalidate the
cached scaler. Impact today is limited (models_v3 ships saved scalers, which are the
source of truth), but the no-saved-scaler fallback path is exactly what that signature
exists to protect. It does not affect any number in this document.

---

## 2. Dataset date range

| Metal | First date | Last date | Span |
|---|---|---|---|
| Aluminium | 2014-06-16 | 2026-10-08 | 12.3 y |
| Copper | 2014-01-02 | 2026-10-08 | 12.8 y |
| Lead | 2014-01-02 | 2026-10-08 | 12.8 y |
| Nickel | 2014-01-02 | 2026-10-08 | 12.8 y |
| Steel | 2015-11-24 | **2025-10-29** | 9.9 y |
| Zinc | 2014-01-02 | 2026-10-08 | 12.8 y |

**Overall: 2014-01-02 to 2026-10-08.** Steel's export ends 2025-10-29 — that contract's
series simply stops there, which is why its last decision point is 2025-05-22 and it
contributes 64 decision points rather than ~88. Worth one sentence in the paper so a
reviewer does not read it as a dropped series.

---

## 3. Number of observations

| Metal | Observations (trading days) | In source | Train obs (Table V) |
|---|---|---|---|
| Aluminium | 3,115 | 3,115 | 3,085 |
| Copper | 3,312 | 3,312 | 3,282 |
| Lead | 3,227 | 3,227 | 3,197 |
| Nickel | 3,134 | 3,135 | 3,104 |
| Steel | 2,507 | 2,507 | 2,477 |
| Zinc | 3,229 | 3,229 | 3,199 |
| **Total** | **18,524** | 18,525 | — |

One nickel row was lost to a duplicate date; every other source row survived cleaning.

---

## 4, 5, 6. ARIMA MAPE, LSTM MAPE, and selected model per metal

### Table V — 30-day out-of-sample holdout

Source: `backend/results_v3/table5_accuracy.csv` (and `.tex`, ready to `\input`).
Models retrained on `series[:-30]`; MAPE in %, RMSE in USD/kg.

| Metal | ARIMA order | ARIMA MAPE | LSTM MAPE | Persistence MAPE | **Selected** | Selected RMSE | tau (%) | Beats persistence |
|---|---|---|---|---|---|---|---|---|
| Aluminium | (0,1,0) | **2.032** | 7.342 | 2.032 | ARIMA | 0.0770 | 2.032 | No (tie) |
| Copper | (0,1,1) | **1.319** | 15.729 | 1.317 | ARIMA | 0.2465 | 2.000 | No |
| Lead | (0,1,0) | **1.120** | 3.457 | 1.120 | ARIMA | 0.0266 | 2.000 | No (tie) |
| Nickel | (3,1,0) | **3.852** | 5.752 | 3.578 | ARIMA | 0.7581 | 3.852 | No |
| Steel | (2,1,2) | **2.159** | 7.171 | 2.187 | ARIMA | 0.0088 | 2.159 | **Yes** |
| Zinc | (0,1,0) | **1.734** | 5.241 | 1.734 | ARIMA | 0.0861 | 2.000 | No (tie) |
| **Mean** | — | **2.036** | **7.449** | **1.995** | **ARIMA 6/6** | — | — | **1/6** |

LSTM epochs actually run (early stopping, max 50): aluminium 31, copper 30, lead 28,
nickel 41, steel 28, zinc 22.

### Walk-forward — all 501 decision points

Source: `backend/results_v3/multiwindow_accuracy.csv`. Mean inner-holdout MAPE (%)
across every decision point for that metal.

| Metal | Points | ARIMA | LSTM | Persistence | Selected | % points ARIMA chosen | % points selected beats persistence |
|---|---|---|---|---|---|---|---|
| Aluminium | 85 | 3.579 | 9.353 | 3.578 | 3.183 | 85.9 | 24.7 |
| Copper | 91 | 3.903 | 10.163 | 3.902 | 3.472 | 83.5 | 26.4 |
| Lead | 88 | 3.350 | 6.892 | 3.357 | 2.845 | 78.4 | 31.8 |
| Nickel | 85 | 6.087 | 10.637 | 6.123 | 4.840 | 80.0 | 36.5 |
| Steel | 64 | 4.858 | 10.899 | 4.858 | 4.435 | 78.1 | 45.3 |
| Zinc | 88 | 4.328 | 10.548 | 4.330 | 3.890 | 83.0 | 44.3 |
| **Pooled** | **501** | **4.318** | **9.693** | **4.325** | **3.741** | **81.6** | **34.3** |

**Selected model, stated two ways** — the paper needs both, because they differ:

- **Table V holdout: ARIMA for all six metals.** The LSTM is selected for none.
- **Walk-forward: ARIMA at 409 of 501 points (81.6%), LSTM at 92 (18.4%).**

### Three things the paper must not overclaim

1. **ARIMA barely separates from a no-change baseline.** Mean selected MAPE 2.036%
   vs persistence 1.995% — persistence is *better on average* on the holdout, and the
   selected model beats it on **only 1 of 6 metals** (steel, by 0.028 pp). Over the
   walk-forward it wins at 34.3% of points. These series are near-random-walk at a
   30-90 day horizon; that is the honest finding, and `fig4` was chosen on exactly
   this criterion (steel, the largest margin, +0.0278 pp).
2. **The LSTM loses on every metal** — 7.449% vs 2.036% mean, and 3.7x worse pooled.
   Copper is the worst at 15.73%.
3. **All 13 proposed-rule HOLDs come from an LSTM-selected point** (see §8). The rule
   needs the lower confidence bound at the forecast peak to clear `p0(1+tau)`; ARIMA's
   interval widens with horizon and almost never clears it, while the LSTM's
   constant-width band can. So the rule that fires is driven by the *weaker* model —
   a reviewer will spot this, so address it rather than leave it implicit.

---

## 7. Actual threshold values

### Decision rule (Eq. 4 and 5), from `backend/scripts/evaluate_c4_v2.py`

```
tau = max(floor, MAPE_inner / 100)        floor = 0.02  (2%)
HOLD  <=>  (L*(k) - p0) / p0  >  tau      L* = lower 95% bound at the forecast peak
                                          k  = argmax of the mean forecast path
target = p0 * (1 + tau)
```

| Parameter | Value |
|---|---|
| Floor on tau (`FLOOR_DEFAULT`) | **0.02 (2%)** |
| Confidence level (`LEVEL_DEFAULT`) | **0.95** -> z = 1.959964 |
| Inner holdout H (`HOLDOUT`) | **30** observations |
| Decision horizon K (`HORIZON`) | **90** observations |
| LSTM input window | **60** observations |
| Max epochs / batch / val fraction | 50 / 32 / 0.10 |
| Retrain interval | every **126** observations |
| First decision offset | **504** observations |
| Decision spacing | **30** observations |
| Random seed | **42** |
| Pre-registered floor grid | {0, 1, 2, 3}% |
| Pre-registered level grid | {95, 80, 68}% -> z = 1.959964 / 1.281552 / 0.994458 |

**Realised tau per metal (Table V):** aluminium 2.032%, copper 2.000%, lead 2.000%,
nickel 3.852%, steel 2.159%, zinc 2.000%. The 2% floor binds for three of six.
**Across the 501 decision points:** tau ranges 2.000%-22.614%, mean 3.873%.

### Firmware thresholds, from `Mayashi-IOT-handoff/main/main.ino`

| Threshold | Value | Basis |
|---|---|---|
| Item-arrival trigger (`TRIGGER_DROP`) | Clear < **0.60** x empty-plate baseline | Relative, so it adapts to room light |
| Colour settle delay (`SETTLE_MS`) | **800 ms** | Illuminator ramps ~1 s; raw counts climbed 8,384 to 13,000 over 15 samples (27 Aug) |
| Colour samples averaged | **5** | — |
| Copper r/c minimum | **0.55** | Measured 26-27 Aug |
| Copper b/c **band** | **0.20 - 0.35** | A floor alone misreads bright neutrals, whose r/c (0.569) equals copper's |
| Bin-full lockout (`BIN_FULL_CM`) | **7.5 cm** | Measured against the real bin |
| Bin re-check interval | **4,000 ms** | Runs independently of the scan cycle |
| IR debounce | **150 ms** | Signal chatters at the edge of detection range |
| Gate home / release angle | **90 deg / 60 deg** | 90 deg confirmed in `ServoAngleTest.ino`; 60 deg is still a placeholder |
| Crusher stroke | press **120 deg**, release **20 deg** | Fixed in `runCrusher()` |
| HTTP timeout | **30,000 ms** | First request loads the model (~13 s) |
| Placeholder weight | **2.5 kg** | Only Component 3 has a load cell |

**Measured colour signatures (26-27 Aug):**

| Material | r/c | g/c | b/c |
|---|---|---|---|
| Copper | 0.569 | 0.293 | 0.248 |
| Brown cardboard | 0.515 | 0.295 | 0.197 |
| Yellow | 0.507 | 0.306 | 0.177 |
| Bright neutral | 0.569 | 0.477 | 0.462 |

### Process constants (`backend/materials_db.py`)

Pyrolysis efficiency eta = **0.67**; process temperature **500 C**; ambient **25 C**;
pyrolysis-oil density **0.90 kg/L**. `E_rec = M x LHV x eta`. LHV (MJ/kg): PP/polypropylene
42.0, polystyrene 40.0, PVC 20.0 (reference only — not read on the mechanical route),
glass 0.0 (inert heat sink, density 2.52 g/cc, c 0.84 J/g-C).

---

## 8. Sell/Hold evaluation results

Source: `backend/results_v3/table6_decisions.csv` (and `.tex`).
Exit policy for every HOLD: sell on the first of 90 days at or above `p0(1+tau)`, else
on day 90. A SELL realises 0 (cash at `p0`), so per-decision value is comparable.

| Rule | Points | HOLDs | Target hits | Hit rate | Wilson 95% CI | Mean gain | Median gain | Mean days held | False holds | SELLs | Missed rises |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Naive (peak > current) | 501 | 120 | 88 | **73.33%** | [64.79, 80.43] | +0.616% | +2.879% | 38.9 | 32 | 381 | 293 |
| **Proposed, Eq. (4)+(5)** | 501 | **13** | **10** | **76.92%** | [49.74, 91.82] | +0.221% | +2.803% | 29.8 | **3** | 488 | 371 |

Base rate (any 90-day window reaching the target): **76.05%**.

**The headline result is selectivity, not accuracy.** The proposed rule holds 13 times
where naive holds 120 — it cuts false holds from 32 to 3, and it never holds at a point
where the selected model fails to beat persistence (naive does so 35 times). But:

- The hit-rate gain (76.92% vs 73.33%) is **not significant**: Fisher one-sided
  **p = 0.538**, and the CI spans [49.74, 91.82] on n = 13. Non-overlapping subsamples
  give p = 0.636 / 0.592 / 0.754.
- The proposed rule's 76.92% is **statistically indistinguishable from the 76.05% base
  rate.** State this plainly.
- **On realised value the proposed rule is worse than naive**: mean value +0.0057% vs
  +0.1475%, paired difference -0.1417%, **Wilcoxon p = 0.0065** (paired t p = 0.432,
  bootstrap 95% CI [-0.479, +0.215], n = 107 decisions where the rules differ). The
  rule buys precision and discipline at a cost in expected value.
- `fisher_note` in the results file records the caveat: proposed holds are a subset of
  naive holds, and 90-day windows spaced 30 days apart overlap, so the Fisher p-value
  is optimistic.

### All 13 proposed-rule HOLDs

From `backend/results_v3/decisions_raw.csv`. Note the `selected` column — **every one
is LSTM.**

| Metal | Date | p0 (USD/kg) | Selected | tau (%) | Hit | Days held | Realised gain (%) |
|---|---|---|---|---|---|---|---|
| Aluminium | 2019-01-21 | 1.8515 | LSTM | 2.846 | yes | 2 | +3.08 |
| Copper | 2018-08-15 | 5.6615 | LSTM | 5.297 | yes | 7 | +5.47 |
| Copper | 2024-07-08 | 10.1809 | LSTM | 2.444 | no | 90 | -6.49 |
| Lead | 2018-08-09 | 2.1073 | LSTM | 2.000 | no | 90 | -7.24 |
| Lead | 2022-07-12 | 1.9385 | LSTM | 3.889 | yes | 6 | +4.85 |
| Nickel | 2018-11-02 | 11.9375 | LSTM | 5.950 | yes | 62 | +6.18 |
| Nickel | 2020-02-24 | 12.4300 | LSTM | 2.000 | yes | 5 | +2.17 |
| Steel | 2021-12-03 | 0.4540 | LSTM | 2.000 | yes | 1 | +2.64 |
| Steel | 2022-01-19 | 0.4690 | LSTM | 2.374 | yes | 9 | +6.18 |
| Steel | 2022-05-30 | 0.4840 | LSTM | 19.161 | no | 90 | **-23.86** |
| Steel | 2023-08-09 | 0.3570 | LSTM | 4.584 | yes | 16 | +4.90 |
| Zinc | 2019-04-25 | 2.7475 | LSTM | 2.000 | yes | 3 | +2.80 |
| Zinc | 2019-10-15 | 2.4380 | LSTM | 2.000 | yes | 7 | +2.17 |

The three misses are the entire downside, and one of them (steel 2022-05-30, tau = 19.16%)
accounts for most of it — a 19% target set by a 19% inner MAPE is the rule failing
safe-ward in a volatile window. Mean gain is dragged from strongly positive to +0.221%
by that single decision. Say so; it is more defensible than a reviewer finding it.

### Sensitivity (pre-registered grid, 4 floors x 3 levels)

Source: `backend/results_v3/sensitivity.csv`, plotted in `fig6_sensitivity.pdf`.

| Floor | Level | HOLDs | Hit rate | Wilson 95% CI |
|---|---|---|---|---|
| 2% | **95%** (default) | **13** | **76.92%** | [49.74, 91.82] |
| 2% | 80% | 14 | 78.57% | [52.41, 92.43] |
| 2% | 68% | 15 | 80.00% | [54.81, 92.95] |
| 0% / 1% | 95% | 13 | 76.92% | [49.74, 91.82] |
| 3% | 95% | 11 | 72.73% | [43.43, 90.25] |
| 3% | 80% | 14 | 71.43% | [45.35, 88.28] |
| 3% | 68% | 15 | 73.33% | [48.05, 89.10] |
| naive @2% | — | 120 | 73.33% | [64.79, 80.43] |

The 0% and 1% floors give results identical to 2% — the floor only binds where inner
MAPE is already under the floor, and loosening the interval to 68% adds two holds and
~3 pp of hit rate. The conclusion is stable across the grid; no cell is dramatically
better, which is the useful thing to report.

### Figure 5 worked example

Zinc, 2019-04-25, tau = 2.0%, LSTM selected, target hit, +2.803% in 3 days — the
proposed HOLD whose realised gain is closest to the median. `fig5_hold_example.pdf`.

---

## 9. Number of historical decision points

**501 total.** 0 failed, 0 missing.

| Metal | Decision points | First decision | Last decision | Retrains |
|---|---|---|---|---|
| Aluminium | 85 | 2016-06-13 | 2026-06-03 | 21 |
| Copper | 91 | 2015-12-31 | 2026-05-12 | 22 |
| Lead | 88 | 2015-12-30 | 2026-04-30 | 21 |
| Nickel | 85 | 2015-12-30 | 2026-05-06 | 21 |
| Steel | 64 | 2017-11-22 | 2025-05-22 | 16 |
| Zinc | 88 | 2015-12-29 | 2026-04-28 | 21 |
| **Total** | **501** | 2015-12-29 | 2026-06-03 | **122** |

Points are spaced 30 observations apart, starting 504 observations into each series.
Because the evaluation horizon is 90 days, **consecutive windows overlap** — this is
why the significance tests are reported with the non-overlapping subsample p-values
alongside them.

---

## 10. Hold precision

**Hold precision = 76.92% (10 of 13), Wilson 95% CI [49.74%, 91.82%].**

| Quantity | Proposed | Naive |
|---|---|---|
| Hold precision (hit rate) | **76.92%** (10/13) | 73.33% (88/120) |
| Wilson 95% CI | [49.74, 91.82] | [64.79, 80.43] |
| False holds | **3** | 32 |
| Holds where selected model loses to persistence | **0** | 35 |
| Holds still above target at day 90 | 46.15% | 43.33% |
| Base rate (same windows) | 76.05% | 76.05% |

Report it with the CI and with the base rate beside it. On n = 13 the interval is
~42 pp wide, and 76.05% of all windows reach the target anyway, so the precision
figure alone does not demonstrate skill. The defensible claims are the **10x reduction
in false holds (32 to 3)** and the **zero holds taken on a model that loses to
persistence** — both are large, both are properties of the rule, and neither depends
on the hit-rate difference being significant.

---

## 11. Residual routing test results

Two parts, and the paper should keep them apart.

### (a) Software routing — verified, deterministic

`backend/services/facility_service.py` ("Residual Pyrolysis Tracker") + `materials_db.py`.
Haversine great-circle distance from the default origin (central Colombo,
**6.9271 N, 79.8612 E**). Executed 2026-10-09; output reproduced verbatim:

| Input material | Route taken | Method | LHV (MJ/kg) | Destination selected | Distance |
|---|---|---|---|---|---|
| Polypropylene / PP | `pyrolysis` | pyrolysis | 42.0 | Kerawalapitiya WtE | 9.68 km |
| Polystyrene | `pyrolysis` | pyrolysis | 40.0 | Kerawalapitiya WtE | 9.68 km |
| Glass / contaminated glass | `thermal_recovery` | heat sink | 0.0 | Kerawalapitiya WtE | 9.68 km |
| PVC / PVC plastic | `mechanical_recycling` | mechanical | 20.0 (unused) | Ciyasa Plastics | 13.65 km |
| Copper, aluminium, steel, lead, zinc, nickel | `recyclable_metal` | to `/forecast` | — | not a residual | — |
| Gold, silver | **rejected** — out of scope | — | — | — | — |
| Unrecognised input | **rejected** — `KeyError` | — | — | — | — |

Facility register and full distance table from the default origin:

| Distance | Type | Facility | Feed-in tariff |
|---|---|---|---|
| **9.68 km** | Waste-to-Energy | Kerawalapitiya WtE (Western Power Company) — *nearest thermal* | not publicly disclosed |
| 13.21 km | Waste-to-Energy | Karadiyana WtE (Colombo South Waste Processing Facility) | 37.10 LKR/kWh |
| **13.65 km** | Mechanical Recycling | Ciyasa Plastics (Korathota, Kaduwela) — *nearest mechanical* | n/a |
| 32.40 km | Mechanical Recycling | Negombo Recycling Club Hub (Millaniya, Horana) | n/a |

All four are real operating Sri Lankan facilities, not placeholders. Coordinates for
the two recyclers are town-centre approximations. Distances are straight-line, not
road distance — adequate for "which plant is closer", not for logistics costing.
**7 of 7 residual inputs routed as specified; 3 of 3 out-of-scope inputs rejected.**

Note that PVC bypasses pyrolysis for mechanical recycling, and that the mechanical
route reports **0 kWh energy recovery by design** — shredding and granulating releases
no energy, so 0 is the correct answer rather than a gap in the model.

### (b) Physical routing — not implemented

The firmware runs a **single bin**. `GATE_HOME -> GATE_RELEASE -> GATE_HOME` is the same
motion for every item regardless of classification or SELL/HOLD decision; diverting to
separate bins is logged as a later step in `SENSOR_PIN_SUMMARY.md`. **There is no
physical residual-diversion result to report.** Describe the gate as a release
mechanism, not a diverter, or the paper will claim hardware that does not exist yet.

### (c) Backend verification

`python -m pytest tests/` — **64 passed, 0 failed** (28.67 s, run 2026-10-09). Covers
forecast equivalence, FX service, Influx client, the IoT compact contract, the
pretrained-model directory, and signal checks.

---

## 12. Actual terminal trials — NO DATA

**Nothing in this repository records a bench trial of the assembled terminal.** There
is no trial log, no item count, no per-trial outcome table.

What *is* in place (so the measurement is a bench session, not new development):

| Subsystem | State |
|---|---|
| TCS34725 colour sensor (GPIO 16/17) | Wired, passing, stable to <1% |
| FC-51 IR arrival trigger (GPIO 27) | Wired, passing, active LOW, 150 ms debounce |
| HC-SR04 bin level (TRIG 5 / ECHO 22, 1k/2k divider) | Wired, `USE_ULTRASONIC 1` |
| SG90 gate servo (GPIO 26) | Wired, `USE_GATE_SERVO 1`, 90 deg confirmed |
| MG996R crusher servo (GPIO 14) | Wired, `USE_CRUSHER 1` |
| Status LEDs (green 21, yellow 18, red 4) | Wired, boot self-test implemented |
| Wi-Fi to FastAPI round trip | Implemented in `main.ino` (768 lines) |
| Buzzer (GPIO 13) | **Not wired** (`USE_BUZZER 0`) |
| Load cell | **Not in this component** — weight comes from Component 3 |

**To report this item:** run N items through the belt (N >= 30 for a usable proportion
CI; 50+ preferred) and log per item: timestamp, IR trigger fired, raw R/G/B/Clear,
classification, backend HTTP status, decision returned, LED lit, gate actuated, item
left the chute, bin distance. Report N, successes, failures, and the failure modes.
GPIO 19 and 23 are dead (driven without current-limiting resistors on 27 Aug) — do not
plan the rig around them.

---

## 13. Round-trip success rate — NO DATA

**Not measured.** The ESP32 -> Wi-Fi -> FastAPI -> decision -> LED/gate path is implemented
and was exercised during development, but no success/attempt counts were ever logged.

Report as `successes / attempts` with a Wilson 95% CI over the same trial set as §12.
Count a round trip as failed if the POST times out (30 s), returns non-2xx, or returns
a decision the actuators do not act on. Two known failure sources to log separately:
the backend laptop's IP changes on every hotspot reconnect, and the first request per
metal pays a ~13 s model load.

**Related integrated-stack result that *is* measured**
(`Ewaste-Recycling-system-02/FINAL-INTEGRATION-TEST.md`, 2026-08-29, 5 Docker
containers): 8 of 9 tests PASS. Component 4 health **PASS**; gateway health, gateway
routing to `/api/component4/*`, and the common dashboard all **PASS**. Component 1
**FAIL** (two ResNet50 `.keras` files absent from the repo). Component 3 passes health
only — the deployed backend there is a copy of Component 2's gas-detection service and
has no `/api/optimize`. This is a system-integration result, **not** a Component 4
hardware round-trip rate; do not present it as one.

---

## 14. Response time — software measured, end-to-end not

Measured with `backend/scripts/latency_bench.py` against a running backend, n = 50 warm
requests per endpoint, all six metals. Source: `backend/results_v2/latency_before_after.csv`.
Milliseconds.

| Endpoint | Cold | Mean | Median | p95 | Min | Max |
|---|---|---|---|---|---|---|
| `POST /api/forecast/` — before | 7,788.5 | 190.6 | 164.6 | 442.6 | 136.6 | 705.1 |
| **`POST /api/forecast/` — after** | **455.8** | **170.5** | **163.9** | **213.7** | 134.5 | 281.8 |
| `POST /api/iot/ingest?compact=true` — before | 228.0 | 169.1 | 163.3 | 215.6 | 136.2 | 281.9 |
| `POST /api/iot/ingest?compact=true` — after | 239.4 | 183.3 | 173.9 | 249.7 | 143.7 | 324.7 |

The headline is the **cold-start reduction: 7,788.5 ms to 455.8 ms (17.1x)** on the
forecast endpoint, with p95 roughly halved (442.6 to 213.7 ms). Warm means are flat
within noise; the ingest endpoint was not the target of the work and did not change
meaningfully. The cold call is reported separately on purpose — it pays for the
TensorFlow/Keras model load and the first 90-step recursive forecast, and averaging it
into the warm calls would hide both its cost and the improvement.

**What is missing:** the **ESP32 end-to-end latency** — IR trigger -> 800 ms settle ->
5 colour samples -> POST -> decision -> LED -> gate motion. Measure it with
`STEP_DELAY_MS = 0` (it is 1,200 ms for Serial-Monitor readability and would otherwise
dominate the figure) by timestamping trigger and gate-complete in the firmware.

---

## 15. Actuation accuracy — NO DATA

**Not measured.** No servo angle-error measurement, no release-success count, no
crusher-stroke verification exists in the repo. `ServoAngleTest.ino` confirms the gate
holds 90 deg on GPIO 26 (500-2400 us pulse range) but records no error figure, and
`GATE_RELEASE = 60 deg` is still flagged in-code as a placeholder to tune against the
real mechanism.

**To report this item,** pick one definition and state it:

- *Positional:* commanded vs measured angle over the range, mean absolute error in degrees; or
- *Functional:* items successfully released / items actuated, with a Wilson CI — the more
  meaningful figure for a single-bin gate, and measurable from the same trial set as §12.

The IR sensor is already mounted to confirm the item left the chute, so the functional
definition needs no extra hardware. Power note for the methods section: servos run from
a **dedicated 5 V 3 A supply** with grounds tied — the L298N's 78M05 supplies only
500 mA, while the SG90 stalls at ~700 mA and the MG996R at ~2.5 A.

---

## 16. Final software versions

### Backend / modelling — the environment that produced `results_v3`

Recorded in `backend/results_v3/run_meta.json` and verified against the venv 2026-10-09.

| Component | Version |
|---|---|
| Python | **3.11.9** |
| OS | Windows-10-10.0.26300-SP0 |
| numpy | 1.26.4 |
| pandas | 2.2.2 |
| scipy | 1.13.1 |
| statsmodels | 0.14.2 |
| pmdarima | 2.0.4 |
| TensorFlow | 2.17.0 |
| Keras | 3.15.1 |
| scikit-learn | 1.5.2 |
| matplotlib | 3.11.2 |
| FastAPI | 0.115.0 |
| Uvicorn | 0.30.6 (standard) |
| Pydantic | 2.9.2 |
| requests | 2.32.3 |
| influxdb-client | 1.44.0 |
| reportlab | 4.2.2 |
| pytest | 9.1.1 |

Quote **Python 3.11.9** — the venv that produced the results.
`Mayashi-IOT-handoff/PROJECT_PROGRESS.md` mentions Python 3.13.2 and FastAPI 0.115.12
as what was on the laptop in August; neither produced these numbers.

### Frontend

React **18.3.1**, react-dom 18.3.1, react-router-dom 6.26.2, recharts 2.12.7,
lucide-react 0.383.0, Vite **5.4.6**, @vitejs/plugin-react 4.3.1.

### Firmware / embedded

ESP32 DevKit V1 (ESP32-D0WD-V3, 30-pin, MAC `04:b2:47:9c:f4:dc`), Arduino IDE **2.3.10**,
ESP32 core by Espressif **3.3.11**, CP210x USB-UART driver. Libraries: Adafruit
TCS34725, ESP32Servo (Harrington/Bennett — *not* the AVR-only stock `Servo`),
ArduinoJson, Wire, WiFi, HTTPClient. Serial 115200 baud.

### Reproducibility

Seed **42**, applied via `random.seed`, `np.random.seed` and
`tf.keras.utils.set_random_seed` before **every** training call.

**Leakage controls, as asserted in code** — worth a methods paragraph, since they are
the main methodological contribution over the original training notebook:

1. Scaler fitted on the training window only.
2. Early stopping validated on the last 10% of the training window — the notebook
   passed the test set as `validation_data`.
3. ARIMA order selected by `auto_arima` on the training window only.
4. The model used for decision `t` is trained with `train_end <= t - 30`, asserted at
   runtime, so the inner holdout that sets tau is genuinely out-of-sample for the LSTM.
5. LSTM interval width from validation residuals only.

---

## Files to pull into Overleaf

| File | Use |
|---|---|
| `backend/results_v3/table5_accuracy.tex` | Table V — accuracy, `\input` directly |
| `backend/results_v3/table6_decisions.tex` | Table VI — decisions, `\input` directly |
| `backend/results_v3/fig4_holdout_steel.pdf` | Fig. 4 — holdout fit (steel: largest margin over persistence) |
| `backend/results_v3/fig5_hold_example.pdf` | Fig. 5 — worked HOLD (zinc, 2019-04-25) |
| `backend/results_v3/fig6_sensitivity.pdf` | Fig. 6 — sensitivity grid |
| `backend/results_v3/dataset_summary.csv` | Dataset table — quotable as-is (unit label fixed, see §1) |
| `backend/results_v3/multiwindow_accuracy.csv` | Walk-forward accuracy table |
| `backend/results_v3/run_meta.json` | Reproducibility appendix |
| `backend/results_v3/tests.json` | Significance tests |
| `backend/results_v3/decisions_raw.csv` | All 501 decisions, if an appendix wants them |

## Outstanding before submission

1. **Bench trial session** — closes §12, §13, §15 and the end-to-end half of §14 in one sitting.
2. ~~Fix the `native_unit` label.~~ **Done 2026-10-09** — see §1. The dataset table should
   now read **USD/kg** for all six metals, and `results_v3/dataset_summary.csv` can be
   quoted as-is.
3. **Decide how to frame the persistence baseline.** 1 of 6 metals beaten on the holdout
   is the real result. Leading with selectivity and false-hold reduction is both honest
   and the stronger story.
