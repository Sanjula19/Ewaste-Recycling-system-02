"""
generate_mixtures.py
====================
Generates synthetic gas MIXTURE training samples.

Physics basis:
  MQ sensors have approximately additive responses — when two gases
  are present together, each sensor reads roughly the SUM of both
  individual gas contributions. This is the superposition principle
  used in e-nose research literature.

Mixture scenarios modelled (realistic e-waste situations):
  CO   + H2S      — Li-ion battery burning on a PCB board
  CO   + BENZENE  — PCB/FR4 board burning (complex organic combustion)
  CO   + MERCURY  — CRT monitor heating with PCB nearby
  H2S  + BENZENE  — Li-ion battery rupture + plastic insulation burn
  AMMONIA + CO    — NiCd battery + PCB burning
  AMMONIA + H2S   — Mixed battery types decomposing together

Output:
  Adds mixture rows to lab_readings.csv using gas_class labels like
  "CO+H2S", "CO+BENZENE" etc.

Author: Sanjula Madushanka | Final Year Research Y4S2
"""

import numpy as np
import pandas as pd
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT         = Path(__file__).parent.parent
CSV_PATH     = ROOT / 'datasets' / 'collected' / 'lab_readings.csv'
OUTPUT_PATH  = ROOT / 'datasets' / 'collected' / 'lab_readings_multilabel.csv'

FEATURE_COLS = ['mq2_ppm', 'mq7_ppm', 'mq135_ppm', 'mq303_ppm',
                'mq136_ppm', 'temperature_c', 'humidity_pct']

# ── Realistic e-waste mixture scenarios ────────────────────────────────────
# Format: (gas_A, gas_B, mix_ratio_A, mix_ratio_B, count, description)
MIXTURE_SCENARIOS = [
    ('CO',      'H2S',     0.7, 0.5, 80,
     'Li-ion battery burning on PCB board'),
    ('CO',      'BENZENE', 0.6, 0.6, 80,
     'FR4 PCB board burning — complex organic combustion'),
    ('CO',      'MERCURY', 0.6, 0.4, 60,
     'CRT monitor heating while PCB burns nearby'),
    ('H2S',     'BENZENE', 0.5, 0.6, 60,
     'Li-ion rupture + plastic insulation melting'),
    ('AMMONIA',  'CO',      0.5, 0.5, 60,
     'NiCd battery decomposing + PCB combustion'),
    ('AMMONIA',  'H2S',     0.6, 0.5, 50,
     'Mixed battery types decomposing together'),
    ('MERCURY',  'BENZENE', 0.4, 0.5, 40,
     'CRT monitor + plastic casing burning'),
]

np.random.seed(42)

print("=" * 60)
print("GAS MIXTURE DATA GENERATOR")
print("=" * 60)

# ── Load existing single-gas data ─────────────────────────────────────────
if not CSV_PATH.exists():
    print("[ERROR] lab_readings.csv not found. Run merge_datasets.py first.")
    exit(1)

df_orig = pd.read_csv(CSV_PATH)

# Normalise gas_class column — take only single-gas rows for profile extraction
single_gas_df = df_orig[~df_orig['gas_class'].str.contains(r'\+', na=False)].copy()
print(f"[OK] Loaded {len(single_gas_df)} single-gas rows as source profiles")

# ── Extract per-class statistics for realistic sampling ────────────────────
profiles = {}
for gas in single_gas_df['gas_class'].unique():
    subset = single_gas_df[single_gas_df['gas_class'] == gas][FEATURE_COLS]
    profiles[gas] = {
        'mean': subset.mean().values,
        'std':  subset.std().fillna(0).values,
    }
    print(f"  Profile [{gas}]: {len(subset)} source rows")

# ── Generate mixture rows ──────────────────────────────────────────────────
print()
print("Generating mixture samples...")
mixture_rows = []

for gas_a, gas_b, ratio_a, ratio_b, count, description in MIXTURE_SCENARIOS:
    if gas_a not in profiles or gas_b not in profiles:
        print(f"  [SKIP] {gas_a}+{gas_b} — one or both gases not in dataset")
        continue

    label = f"{gas_a}+{gas_b}"
    pa = profiles[gas_a]
    pb = profiles[gas_b]

    generated = 0
    for _ in range(count):
        # Sample a single reading from each pure gas profile
        sample_a = np.random.normal(pa['mean'], pa['std'] * 0.3)
        sample_b = np.random.normal(pb['mean'], pb['std'] * 0.3)

        # Additive mixture: weighted sum of both contributions
        # ratio_a / ratio_b control relative concentration strength
        mixture = (ratio_a * sample_a + ratio_b * sample_b)

        # Ensure physical plausibility (non-negative ppm values)
        mixture[:5] = np.clip(mixture[:5], 0, None)   # sensor readings >= 0
        mixture[5]  = float(np.clip(mixture[5], 20, 45))   # temp 20-45 C
        mixture[6]  = float(np.clip(mixture[6], 30, 95))   # humidity 30-95%

        row = dict(zip(FEATURE_COLS, mixture))
        row['gas_class'] = label
        row['notes']     = description
        mixture_rows.append(row)
        generated += 1

    print(f"  [{label:<20}]: {generated} rows  ({description})")

# ── Combine single-gas + mixture data ─────────────────────────────────────
df_mix = pd.DataFrame(mixture_rows)
df_combined = pd.concat([df_orig, df_mix], ignore_index=True)
df_combined.drop_duplicates(inplace=True)

# ── Save output ───────────────────────────────────────────────────────────
df_combined.to_csv(OUTPUT_PATH, index=False)

print()
print("=" * 60)
print("MIXTURE DATASET SUMMARY")
print("=" * 60)
print(f"  Single-gas rows : {len(df_orig)}")
print(f"  Mixture rows    : {len(df_mix)}")
print(f"  TOTAL           : {len(df_combined)}")
print()
print("  Class distribution:")
for cls, cnt in df_combined['gas_class'].value_counts().items():
    prefix = "  MIX " if '+' in str(cls) else "  GAS "
    print(f"{prefix} {cls:<22}: {cnt} rows")
print()
print(f"[OK] Saved to: {OUTPUT_PATH}")
print()
print("Next: Run python scripts/run_pipeline_multilabel.py")
