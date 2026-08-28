"""
verify_data.py  —  Quick Data Quality Check
============================================
Run this after any collection session to verify your CSV is valid.

Usage:
  python scripts/verify_data.py
"""

import pandas as pd
import numpy as np
from pathlib import Path

CSV_PATH     = Path(__file__).parent.parent / 'datasets' / 'collected' / 'lab_readings.csv'
VALID_CLASSES = ['CLEAN', 'CO', 'LPG', 'BENZENE', 'AMMONIA', 'MERCURY', 'H2S']
FEATURE_COLS  = ['mq2_ppm', 'mq7_ppm', 'mq135_ppm', 'mq303_ppm', 'mq136_ppm',
                 'temperature_c', 'humidity_pct']

print("=" * 55)
print("  DATA QUALITY REPORT")
print("=" * 55)

if not CSV_PATH.exists():
    print("[ERROR] File not found:", CSV_PATH)
    exit(1)

df = pd.read_csv(CSV_PATH)
print(f"File : {CSV_PATH.name}")
print(f"Rows : {len(df)}")
print(f"Cols : {df.columns.tolist()}")
print()

# ── 1. Class distribution ──────────────────────────────────
print("-- Class Distribution --")
if 'gas_class' in df.columns:
    counts = df['gas_class'].value_counts()
    for cls in VALID_CLASSES:
        n   = counts.get(cls, 0)
        bar = "#" * (n // 2)
        ok  = "[OK]"  if n >= 30 else ("[LOW]" if n > 0 else "[MISSING]")
        print(f"  {cls:<10} {n:>4} rows  {bar}  {ok}")
    print()
    unknown = [c for c in df['gas_class'].unique() if c not in VALID_CLASSES]
    if unknown:
        print(f"[!] Unknown class labels found: {unknown}")
        print("    Fix: rename to one of:", VALID_CLASSES)
else:
    print("[ERROR] No 'gas_class' column found!")

# ── 2. Missing values ─────────────────────────────────────
print("-- Missing Values --")
missing = df.isnull().sum()
if missing.sum() == 0:
    print("  [OK] No missing values")
else:
    for col, n in missing[missing > 0].items():
        print(f"  [!] {col}: {n} missing")
print()

# ── 3. Numeric range check ────────────────────────────────
print("-- Sensor Value Ranges --")
range_rules = {
    'mq2_ppm':       (0, 2000,  "MQ-2 LPG/Smoke"),
    'mq7_ppm':       (0, 1000,  "MQ-7 CO"),
    'mq135_ppm':     (0, 500,   "MQ-135 VOC/NH3"),
    'mq303_ppm':     (0, 1.0,   "MQ-303 Mercury"),
    'mq136_ppm':     (0, 20,    "MQ-136 H2S"),
    'temperature_c': (10, 50,   "Temperature"),
    'humidity_pct':  (10, 100,  "Humidity"),
}
for col, (lo, hi, name) in range_rules.items():
    if col not in df.columns:
        print(f"  [MISSING COL] {col}")
        continue
    numeric = pd.to_numeric(df[col], errors='coerce')
    out = numeric[(numeric < lo) | (numeric > hi)].count()
    mn, mx = numeric.min(), numeric.max()
    flag = "[OK]" if out == 0 else f"[!] {out} out-of-range rows"
    print(f"  {name:<20}: min={mn:>9.4f}  max={mx:>9.4f}  {flag}")
print()

# ── 4. Duplicate check ───────────────────────────────────
dups = df.duplicated().sum()
print(f"-- Duplicates: {dups} --")
if dups > 0:
    print(f"  [!] {dups} duplicate rows found -- will be removed during preprocessing")
else:
    print("  [OK] No duplicates")
print()

# ── 5. Final verdict ──────────────────────────────────────
print("=" * 55)
has_all_classes = all(df['gas_class'].value_counts().get(c, 0) >= 10
                      for c in VALID_CLASSES) if 'gas_class' in df.columns else False
total = len(df)

if total >= 210 and has_all_classes:
    print("  VERDICT: READY TO TRAIN")
    print(f"  {total} rows, all classes present")
elif total >= 50:
    print("  VERDICT: PARTIAL - can train but collect more for better accuracy")
    print(f"  {total} rows collected so far")
else:
    print("  VERDICT: NOT ENOUGH DATA YET")
    print(f"  Need at least 210 rows (30 per class)")
print()
print("  Run pipeline: python scripts/run_pipeline.py")
print("=" * 55)
