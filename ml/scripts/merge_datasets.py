"""
merge_datasets.py
==================
Loads all 4 real datasets (D1, D2, D3, D5), maps them to our 7-column
standard format, merges them, and saves as the final training CSV.

Mappings:
  D1 (UCI Gas Sensor Drift)     → gas class label from numeric ID
  D2 (MQ135SensorData)          → Gas1-Gas6 → sensor columns
  D3 (gsalc UCI concentration)  → gas name column → class label
  D5 (lab_readings.csv)         → already in correct format

Author: Sanjula Madushanka | Final Year Research Y4S2
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT         = Path(__file__).parent.parent
RAW_DIR      = ROOT / 'datasets' / 'raw'
COLLECTED    = ROOT / 'datasets' / 'collected' / 'lab_readings.csv'
OUTPUT_PATH  = ROOT / 'datasets' / 'collected' / 'lab_readings.csv'  # overwrite with merged

FEATURE_COLS = ['mq2_ppm', 'mq7_ppm', 'mq135_ppm', 'mq303_ppm', 'mq136_ppm',
                'temperature_c', 'humidity_pct']
TARGET_COL   = 'gas_class'

# ── Gas class mapping ──────────────────────────────────────────────────────
# D1: UCI Gas Sensor Drift → 6 classes (1-indexed)
D1_CLASS_MAP = {
    1: 'ETHANOL',    # Ethanol
    2: 'ETHYLENE',   # Ethylene — we'll group as BENZENE (VOC group)
    3: 'AMMONIA',    # Ammonia
    4: 'ACETALDEHYDE', # map → BENZENE (VOC)
    5: 'ACETONE',    # map → BENZENE (VOC)
    6: 'TOLUENE',    # map → BENZENE (VOC)
}
# For our system's 7 classes, simplify D1 to usable classes
D1_USABLE_CLASSES = {
    3: 'AMMONIA',   # Direct match
}

# D2: MQ Sensor Dataset → 7 numeric classes
D2_CLASS_MAP = {
    0: 'CLEAN',
    1: 'CO',
    2: 'LPG',
    3: 'AMMONIA',
    4: 'BENZENE',
    5: 'H2S',
    6: 'MERCURY',
}

# D3: gsalc.csv → gas name string
D3_CLASS_MAP = {
    'ethanol':       'BENZENE',     # VOC family
    'acetaldehyde':  'BENZENE',
    'acetone':       'BENZENE',
    'ammonia':       'AMMONIA',
    'toluene':       'BENZENE',
    'co':            'CO',
    'carbon monoxide': 'CO',
    'ethylene':      'BENZENE',
    'methane':       'LPG',
    'lpg':           'LPG',
    'clean air':     'CLEAN',
    'clean':         'CLEAN',
}

VALID_CLASSES = {'CO', 'LPG', 'BENZENE', 'AMMONIA', 'MERCURY', 'H2S', 'CLEAN'}

parts = []
print("=" * 60)
print("DATASET MERGER")
print("=" * 60)

# ── D5: Load existing collected / demo data ────────────────────────────────
print("\n[D5] Loading lab_readings.csv ...")
if COLLECTED.exists():
    d5 = pd.read_csv(COLLECTED)
    # Keep only needed columns
    cols_present = [c for c in FEATURE_COLS + [TARGET_COL] if c in d5.columns]
    d5 = d5[cols_present]
    # Fill missing sensor cols with median
    for col in FEATURE_COLS:
        if col not in d5.columns:
            d5[col] = 0.0
    d5 = d5[FEATURE_COLS + [TARGET_COL]].dropna(subset=[TARGET_COL])
    d5 = d5[d5[TARGET_COL].isin(VALID_CLASSES)]
    d5['source'] = 'D5_collected'
    parts.append(d5)
    print(f"     Rows: {len(d5)} | Classes: {d5[TARGET_COL].value_counts().to_dict()}")
else:
    print("     [SKIP] lab_readings.csv not found")

# ── D2: MQ Sensor 2023 CSV ─────────────────────────────────────────────────
print("\n[D2] Loading MQ135SensorData.csv ...")
d2_path = RAW_DIR / 'mq_sensor_2023' / 'MQ135SensorData.csv'
if d2_path.exists():
    d2_raw = pd.read_csv(d2_path)
    print(f"     Raw rows: {len(d2_raw)} | Columns: {d2_raw.columns.tolist()}")

    d2_raw.columns = d2_raw.columns.str.strip()
    d2_rows = []
    for _, row in d2_raw.iterrows():
        cls_num = int(row.get('Class', -1))
        if cls_num not in D2_CLASS_MAP:
            continue
        gas_class = D2_CLASS_MAP[cls_num]

        # Map 6 raw gas channels to our 5 sensors
        # MQ Sensor dataset has Gas1-Gas6 (analog values 0-1023 range)
        # Map: Gas1→mq2, Gas2→mq7, Gas3→mq135, Gas4→mq303, Gas5→mq136
        # Scale raw analog (0-1023) → approximate ppm using ratio
        g1 = float(row.get('Gas1', 0))
        g2 = float(row.get('Gas2', 0))
        g3 = float(row.get('Gas3', 0))
        g4 = float(row.get('Gas4', 0))
        g5 = float(row.get('Gas5', 0))

        # Normalize to rough ppm scale (divide by 1023, multiply by typical max)
        d2_rows.append({
            'mq2_ppm':       g1 / 1023.0 * 300,
            'mq7_ppm':       g2 / 1023.0 * 150,
            'mq135_ppm':     g3 / 1023.0 * 100,
            'mq303_ppm':     g4 / 1023.0 * 0.1,
            'mq136_ppm':     g5 / 1023.0 * 5,
            'temperature_c': 28.0 + np.random.normal(0, 1),
            'humidity_pct':  65.0 + np.random.normal(0, 5),
            TARGET_COL:      gas_class,
            'source':        'D2_mq_sensor',
        })

    d2 = pd.DataFrame(d2_rows)
    # Sample max 300 per class to avoid overwhelming the dataset
    d2 = d2.groupby(TARGET_COL, group_keys=False).apply(
        lambda x: x.sample(min(len(x), 300), random_state=42)
    ).reset_index(drop=True)

    parts.append(d2[FEATURE_COLS + [TARGET_COL, 'source']])
    print(f"     Used rows: {len(d2)} | Classes: {d2[TARGET_COL].value_counts().to_dict()}")
else:
    print("     [SKIP] File not found")

# ── D1: UCI Gas Sensor Drift .dat files ────────────────────────────────────
print("\n[D1] Loading UCI Gas Sensor Drift .dat files ...")
d1_dir = RAW_DIR / 'uci_gas_sensor_drift'
d1_files = sorted(d1_dir.glob('*.dat'))
if d1_files:
    d1_rows = []
    for dat_file in d1_files:
        with open(dat_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Format: class;concentration feat1:val1 feat2:val2 ...
                parts_line = line.split(';')
                if len(parts_line) < 2:
                    continue
                cls_id = int(float(parts_line[0]))
                if cls_id not in D1_USABLE_CLASSES:
                    continue  # Only use classes we can map
                gas_class = D1_USABLE_CLASSES[cls_id]
                # Parse features: "1:val1 2:val2 ..."
                feat_str = parts_line[1].strip()
                feat_parts = feat_str.split()
                feats = {}
                for fp in feat_parts:
                    if ':' in fp:
                        k, v = fp.split(':', 1)
                        feats[int(k)] = float(v)
                # D1 has 128 features from 8 metal oxide sensors × 16 statistics
                # Use features 1-8 (steady-state mean values per sensor)
                f1 = feats.get(1, 0)   # Sensor 1 → mq2 proxy
                f2 = feats.get(2, 0)   # Sensor 2 → mq7 proxy
                f3 = feats.get(9, 0)   # Sensor 3 (second batch) → mq135 proxy
                f4 = feats.get(17, 0)  # Sensor 3 → mq303 proxy
                f5 = feats.get(25, 0)  # Sensor 4 → mq136 proxy

                # Normalize to ppm-like scale
                d1_rows.append({
                    'mq2_ppm':       abs(f1) / 1000.0 * 30,
                    'mq7_ppm':       abs(f2) * 5,
                    'mq135_ppm':     abs(f3) * 5,
                    'mq303_ppm':     abs(f4) * 0.001,
                    'mq136_ppm':     abs(f5) * 0.5,
                    'temperature_c': 28.0 + np.random.normal(0, 1),
                    'humidity_pct':  65.0 + np.random.normal(0, 5),
                    TARGET_COL:      gas_class,
                    'source':        'D1_uci_drift',
                })

    if d1_rows:
        d1 = pd.DataFrame(d1_rows)
        d1 = d1.groupby(TARGET_COL, group_keys=False).apply(
            lambda x: x.sample(min(len(x), 200), random_state=42)
        ).reset_index(drop=True)
        parts.append(d1[FEATURE_COLS + [TARGET_COL, 'source']])
        print(f"     Used rows: {len(d1)} | Classes: {d1[TARGET_COL].value_counts().to_dict()}")
    else:
        print("     [SKIP] No usable classes found in D1")
else:
    print("     [SKIP] No .dat files found")

# ── D3: UCI Gas + Concentration ────────────────────────────────────────────
print("\n[D3] Loading gsalc.csv ...")
d3_path = RAW_DIR / 'uci_gas_concentration' / 'gsalc.csv'
if d3_path.exists():
    d3_raw = pd.read_csv(d3_path, header=0)
    # Col 0 = gas name, Col 1 = concentration, remaining = sensor time series
    gas_col  = d3_raw.columns[0]   # 'ethanol'
    conc_col = d3_raw.columns[1]   # '100ppb' etc
    sensor_cols = d3_raw.columns[2:]

    d3_rows = []
    for _, row in d3_raw.iterrows():
        gas_name  = str(row[gas_col]).strip().lower()
        gas_class = D3_CLASS_MAP.get(gas_name)
        if not gas_class:
            continue

        # Use mean, std, min, max of sensor time-series as features
        vals = pd.to_numeric(row[sensor_cols], errors='coerce').dropna().values
        if len(vals) < 10:
            continue

        # Map to our 5 sensor slots using quartile splits of the time-series
        n = len(vals)
        q = n // 5
        d3_rows.append({
            'mq2_ppm':       float(np.mean(vals[:q])) * 50,
            'mq7_ppm':       float(np.mean(vals[q:2*q])) * 30,
            'mq135_ppm':     float(np.mean(vals[2*q:3*q])) * 80,
            'mq303_ppm':     float(np.mean(vals[3*q:4*q])) * 0.05,
            'mq136_ppm':     float(np.mean(vals[4*q:])) * 3,
            'temperature_c': 28.0 + np.random.normal(0, 1),
            'humidity_pct':  65.0 + np.random.normal(0, 5),
            TARGET_COL:      gas_class,
            'source':        'D3_uci_conc',
        })

    if d3_rows:
        d3 = pd.DataFrame(d3_rows)
        d3 = d3.groupby(TARGET_COL, group_keys=False).apply(
            lambda x: x.sample(min(len(x), 200), random_state=42)
        ).reset_index(drop=True)
        parts.append(d3[FEATURE_COLS + [TARGET_COL, 'source']])
        print(f"     Used rows: {len(d3)} | Classes: {d3[TARGET_COL].value_counts().to_dict()}")
    else:
        print("     [SKIP] No usable classes found in D3")
else:
    print("     [SKIP] gsalc.csv not found")

# ── Merge all parts ────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("MERGING DATASETS")
print("=" * 60)

if not parts:
    print("[ERROR] No data loaded. Check file paths.")
    exit(1)

merged = pd.concat(parts, ignore_index=True)
merged = merged[FEATURE_COLS + [TARGET_COL]]
merged = merged[merged[TARGET_COL].isin(VALID_CLASSES)]
merged.dropna(inplace=True)
merged.drop_duplicates(inplace=True)

print(f"\nTotal merged rows: {len(merged)}")
print(f"Class distribution:")
for cls, cnt in merged[TARGET_COL].value_counts().items():
    bar = '#' * (cnt // 10)
    print(f"  {cls:<10}: {cnt:>4}  {bar}")

# ── Save merged dataset ─────────────────────────────────────────────────────
# Backup original first
backup_path = COLLECTED.parent / 'lab_readings_DEMO_BACKUP.csv'
if COLLECTED.exists() and not backup_path.exists():
    import shutil
    shutil.copy2(COLLECTED, backup_path)
    print(f"\n[OK] Demo data backed up to: lab_readings_DEMO_BACKUP.csv")

merged.to_csv(OUTPUT_PATH, index=False)
print(f"[OK] Merged dataset saved to: {OUTPUT_PATH}")
print(f"     Size: {OUTPUT_PATH.stat().st_size / 1024:.1f} KB")
print()
print("Next: Run python scripts/run_pipeline.py to train on real data")
