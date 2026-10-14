"""
Realistic E-Waste Sensor Data Generator
========================================
Converts / augments synthetic "lab_readings.csv" to look like real ESP32
+ MQ-sensor data collected in a Sri Lanka lab environment.

What makes real MQ-sensor data different from synthetic:
  1. WIDER variance  — lab conditions change; sensors drift
  2. SENSOR DRIFT    — baseline creeps up slowly over time
  3. WARMUP NOISE    — first readings within a session are noisier
  4. CROSS-SENSITIVITY — e.g. LPG raises MQ-135 slightly too
  5. ADC QUANTISATION — ESP32 12-bit (0-4095), causes stepped values
  6. HUMIDITY/TEMP EFFECT — high humidity suppresses raw ADC reads
  7. ZERO CLIPPING   — some readings are truly 0 when gas absent
  8. OUTLIERS        — occasional spike, just like real hardware

Generates:
  - component-2/ml/datasets/collected/realistic_lab_readings.csv      (single-label)
  - component-2/ml/datasets/collected/realistic_lab_readings_multi.csv (multilabel)

Run:
  python component-2/ml/scripts/generate_realistic_data.py
  (from the repo root)

Author : Auto-generated for Sanjula / Component-2 E-Waste project
"""

import numpy as np
import pandas as pd
import os
import random
from datetime import datetime, timedelta

# ── reproducibility ──────────────────────────────────────────────────────────
SEED = 42
np.random.seed(SEED)
random.seed(SEED)

# ── output paths ─────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR  = os.path.join(SCRIPT_DIR, "..", "datasets", "collected")
OUT_SINGLE   = os.path.join(DATASET_DIR, "realistic_lab_readings.csv")
OUT_MULTI    = os.path.join(DATASET_DIR, "realistic_lab_readings_multi.csv")

# ── how many rows to generate per class ──────────────────────────────────────
ROWS_PER_CLASS = 200   # single-label classes × this = total rows


# =============================================================================
# Sensor physics: realistic ppm ranges from actual ESP32 + MQ hardware
# Based on your lab_reading.csv real data and MQ sensor datasheets
# =============================================================================

# Each class: dict of sensor → (mean, std, min_clip, max_clip)
# These ranges are calibrated to match what was seen in lab_reading.csv
GAS_PROFILES = {
    "CLEAN": {
        "mq2_ppm":     (4.5,   3.0,   0.5,   12.0),
        "mq7_ppm":     (3.5,   2.5,   0.5,   10.0),
        "mq135_ppm":   (3.2,   2.0,   0.3,    9.0),
        "mq136_ppm":   (0.10,  0.05,  0.02,   0.30),
        "temperature_c":(27.5, 2.5,   22.0,   35.0),
        "humidity_pct": (62.0,  8.0,  44.0,   92.0),
    },
    "CO": {
        # High MQ-7; MQ-2 elevated; MQ-135 mild
        "mq2_ppm":     (30.0,  14.0,   2.0,   70.0),
        "mq7_ppm":     (82.0,  28.0,  22.0,  145.0),
        "mq135_ppm":   (9.5,   6.0,   0.0,   26.0),
        "mq136_ppm":   (0.30,  0.18,  0.0,    0.65),
        "temperature_c":(28.5,  3.5,  20.0,   36.0),
        "humidity_pct": (64.0,  10.0, 43.0,   95.0),
    },
    "LPG": {
        # Very high MQ-2; MQ-7 low; MQ-135 low
        "mq2_ppm":     (220.0, 75.0,  50.0,  410.0),
        "mq7_ppm":     (10.0,   6.5,   0.0,   22.0),
        "mq135_ppm":   (8.0,   5.0,   0.0,   18.0),
        "mq136_ppm":   (0.20,  0.12,  0.0,    0.55),
        "temperature_c":(27.5,  4.0,  20.0,   37.0),
        "humidity_pct": (64.0,  12.0, 36.0,   88.0),
    },
    "BENZENE": {
        # High MQ-135; MQ-2 mild
        "mq2_ppm":     (15.0,  8.0,   0.0,   30.0),
        "mq7_ppm":     (9.5,   5.0,   1.5,   18.0),
        "mq135_ppm":   (47.0,  18.0,  17.0,  92.0),
        "mq136_ppm":   (0.40,  0.18,  0.0,    0.75),
        "temperature_c":(29.0,  3.5,  22.0,   35.0),
        "humidity_pct": (66.0,  10.0, 43.0,   90.0),
    },
    "AMMONIA": {
        # High MQ-135; MQ-7 low; MQ-2 mild
        "mq2_ppm":     (12.0,  3.5,   5.0,   20.0),
        "mq7_ppm":     (5.5,   2.0,   1.5,   10.0),
        "mq135_ppm":   (60.0,  9.0,  38.0,   80.0),
        "mq136_ppm":   (0.30,  0.10,  0.08,   0.55),
        "temperature_c":(29.0,  2.5,  24.0,   35.0),
        "humidity_pct": (68.0,  7.0,  55.0,   80.0),
    },
    "H2S": {
        # High MQ-136; MQ-2/MQ-7 mild
        "mq2_ppm":     (10.0,  2.0,   6.0,   15.0),
        "mq7_ppm":     (7.0,   2.0,   3.5,   12.5),
        "mq135_ppm":   (9.0,   2.0,   5.0,   14.0),
        "mq136_ppm":   (3.8,   0.7,   2.5,    5.5),
        "temperature_c":(29.5,  2.5,  25.0,   35.0),
        "humidity_pct": (67.5,  4.5,  60.0,   75.0),
    },
}

# Mixture profiles — used for multi-label CSV
MIXTURE_PROFILES = {
    "CO+H2S": {
        "mq2_ppm":     (27.0,  3.5,  20.0,   35.0),
        "mq7_ppm":     (64.0,  6.0,  48.0,   80.0),
        "mq135_ppm":   (12.5,  1.5,   9.0,   16.0),
        "mq136_ppm":   (2.1,   0.25,  1.7,    2.8),
        "temperature_c":(35.0,  1.0,  33.0,   37.0),
        "humidity_pct": (79.0,  2.5,  73.0,   85.0),
    },
    "CO+BENZENE": {
        "mq2_ppm":     (28.0,  2.5,  22.0,   33.0),
        "mq7_ppm":     (56.0,  6.0,  44.0,   68.0),
        "mq135_ppm":   (34.0,  3.0,  26.0,   42.0),
        "mq136_ppm":   (0.42,  0.05,  0.34,   0.52),
        "temperature_c":(35.0,  1.0,  33.0,   37.0),
        "humidity_pct": (79.5,  2.0,  74.0,   85.0),
    },
    "H2S+BENZENE": {
        "mq2_ppm":     (9.5,   1.5,   6.0,   13.5),
        "mq7_ppm":     (7.5,   2.0,   4.0,   12.0),
        "mq135_ppm":   (40.0,  5.0,  28.0,   55.0),
        "mq136_ppm":   (3.5,   0.5,   2.5,    5.0),
        "temperature_c":(29.0,  2.0,  24.0,   34.0),
        "humidity_pct": (66.0,  6.0,  54.0,   78.0),
    },
    "AMMONIA+CO": {
        "mq2_ppm":     (22.0,  4.0,  12.0,   32.0),
        "mq7_ppm":     (55.0,  8.0,  38.0,   72.0),
        "mq135_ppm":   (52.0,  6.0,  38.0,   68.0),
        "mq136_ppm":   (0.30,  0.08,  0.15,   0.48),
        "temperature_c":(29.5,  2.0,  24.0,   35.0),
        "humidity_pct": (67.0,  6.0,  54.0,   80.0),
    },
    "AMMONIA+H2S": {
        "mq2_ppm":     (11.0,  2.0,   7.0,   16.0),
        "mq7_ppm":     (6.0,   2.0,   3.0,   11.0),
        "mq135_ppm":   (58.0,  6.0,  44.0,   74.0),
        "mq136_ppm":   (3.5,   0.6,   2.4,    5.0),
        "temperature_c":(29.5,  2.0,  24.0,   35.0),
        "humidity_pct": (67.0,  5.0,  57.0,   78.0),
    },
}


# =============================================================================
# Realism helpers
# =============================================================================

def _adc_quantise(value, sensor="mq2"):
    """
    Simulate ESP32 12-bit ADC quantisation artefact.
    The ppm values come from converting raw ADC; the ADC has discrete steps.
    We add tiny quantisation noise to mimic this.
    """
    # ADC step noise: ±0.5–2% of value, rounded to 2 decimal places
    noise_pct = np.random.uniform(0.005, 0.02)
    quantised = value * (1 + np.random.choice([-1, 1]) * noise_pct)
    return round(quantised, 2)


def _apply_humidity_suppression(values, humidity):
    """
    High humidity (>70%) suppresses MQ sensor sensitivity slightly.
    Effect: reading drops ~3-8% when humidity > 70%.
    """
    if humidity > 70:
        factor = 1.0 - np.random.uniform(0.03, 0.08)
        for key in ["mq2_ppm", "mq7_ppm", "mq135_ppm", "mq136_ppm"]:
            if key in values:
                values[key] = max(0.0, values[key] * factor)
    return values


def _apply_sensor_drift(values, row_idx, total_rows):
    """
    Simulate slow sensor baseline drift over a measurement session.
    Drift: +0 to +5% linear increase over the session for MQ sensors.
    """
    drift_factor = 1.0 + 0.05 * (row_idx / max(total_rows, 1))
    for key in ["mq2_ppm", "mq7_ppm", "mq135_ppm", "mq136_ppm"]:
        if key in values:
            values[key] = values[key] * drift_factor
    return values


def _apply_warmup_noise(values, row_idx):
    """
    First ~15 readings of a session are noisier (sensor not yet stable).
    """
    if row_idx < 15:
        extra_noise = (15 - row_idx) / 15.0 * 0.15  # up to 15% extra noise
        for key in ["mq2_ppm", "mq7_ppm", "mq135_ppm", "mq136_ppm"]:
            if key in values:
                values[key] *= (1 + np.random.uniform(-extra_noise, extra_noise))
                values[key] = max(0.0, values[key])
    return values


def _apply_cross_sensitivity(values, gas_class):
    """
    MQ sensors cross-react to other gases.
    E.g. LPG trace elevates MQ-135; CO elevates MQ-2 slightly.
    """
    cs = {
        "LPG":     {"mq135_ppm": 1.08},
        "CO":      {"mq2_ppm": 1.06},
        "BENZENE": {"mq7_ppm": 1.05},
        "H2S":     {"mq135_ppm": 1.04, "mq2_ppm": 1.03},
        "AMMONIA": {"mq7_ppm": 1.04},
    }
    if gas_class in cs:
        for sensor, factor in cs[gas_class].items():
            if sensor in values:
                values[sensor] *= factor
    return values


def _random_zero_clip(values, gas_class):
    """
    Occasionally a sensor reads 0 (disconnection artefact or true zero).
    Only happens on non-primary sensors for each gas class.
    Probability: ~3%
    """
    non_primary = {
        "CLEAN":   ["mq2_ppm", "mq7_ppm", "mq135_ppm", "mq136_ppm"],
        "CO":      ["mq2_ppm", "mq135_ppm", "mq136_ppm"],
        "LPG":     ["mq7_ppm", "mq135_ppm", "mq136_ppm"],
        "BENZENE": ["mq2_ppm", "mq7_ppm", "mq136_ppm"],
        "AMMONIA": ["mq2_ppm", "mq7_ppm", "mq136_ppm"],
        "H2S":     ["mq2_ppm", "mq7_ppm", "mq135_ppm"],
    }
    candidates = non_primary.get(gas_class, [])
    for sensor in candidates:
        if sensor in values and np.random.random() < 0.03:
            values[sensor] = 0.0
    return values


def _add_outlier_spike(values, gas_class):
    """
    ~2% chance of a spike (×2.0-3.0) on the primary sensor.
    Mimics real ESP32 glitches or brief gas concentration surges.
    """
    primary = {
        "CO": "mq7_ppm", "LPG": "mq2_ppm",
        "BENZENE": "mq135_ppm", "AMMONIA": "mq135_ppm",
        "H2S": "mq136_ppm", "CLEAN": "mq2_ppm",
    }
    if np.random.random() < 0.02:
        key = primary.get(gas_class, "mq2_ppm")
        values[key] *= np.random.uniform(2.0, 3.0)
    return values


# =============================================================================
# Core generator
# =============================================================================

def generate_single_label(n_per_class=ROWS_PER_CLASS):
    """Generate realistic single-label dataset."""
    records = []
    classes = list(GAS_PROFILES.keys())

    # Simulate timestamp — one reading every 5s during a lab session
    t0 = datetime(2026, 8, 1, 9, 0, 0)
    ts = t0

    row_idx = 0
    for gas_class in classes:
        profile = GAS_PROFILES[gas_class]
        session_rows = n_per_class

        for i in range(session_rows):
            # 1. Sample from Gaussian profile
            row = {}
            for feat, (mean, std, lo, hi) in profile.items():
                val = np.random.normal(mean, std)
                val = float(np.clip(val, lo, hi))
                row[feat] = round(val, 2)

            # 2. Apply realism layers
            row = _apply_cross_sensitivity(row, gas_class)
            row = _apply_humidity_suppression(row, row["humidity_pct"])
            row = _apply_sensor_drift(row, i, session_rows)
            row = _apply_warmup_noise(row, i)
            row = _random_zero_clip(row, gas_class)
            row = _add_outlier_spike(row, gas_class)

            # 3. ADC quantisation on ppm columns
            for k in ["mq2_ppm", "mq7_ppm", "mq135_ppm", "mq136_ppm"]:
                row[k] = _adc_quantise(row[k])
                row[k] = max(0.0, round(row[k], 4))

            row["temperature_c"] = round(row["temperature_c"], 2)
            row["humidity_pct"]   = round(row["humidity_pct"], 2)
            row["gas_class"] = gas_class
            row["timestamp"] = ts.strftime("%Y-%m-%dT%H:%M:%S")
            row["notes"] = f"Realistic augmented — {gas_class} exposure in Sri Lanka lab"

            records.append(row)
            ts += timedelta(seconds=5)
            row_idx += 1

        # Add a short break between sessions (simulate sensor cool-down)
        ts += timedelta(minutes=15)

    df = pd.DataFrame(records)
    # Reorder columns to match the original CSV format + new columns
    cols = [
        "timestamp",
        "mq2_ppm", "mq7_ppm", "mq135_ppm", "mq136_ppm",
        "temperature_c", "humidity_pct",
        "gas_class", "notes"
    ]
    df = df[cols]

    # Shuffle for training
    df = df.sample(frac=1, random_state=SEED).reset_index(drop=True)
    return df


def generate_multilabel(n_per_mixture=100, n_single_label=50):
    """
    Generate realistic multi-label dataset.
    Includes both pure single-label rows and mixture rows.
    """
    records = []

    t0 = datetime(2026, 8, 2, 9, 0, 0)
    ts = t0

    # Single-label rows (from same profiles)
    for gas_class, profile in GAS_PROFILES.items():
        for i in range(n_single_label):
            row = {}
            for feat, (mean, std, lo, hi) in profile.items():
                val = np.random.normal(mean, std)
                row[feat] = round(float(np.clip(val, lo, hi)), 2)

            row = _apply_cross_sensitivity(row, gas_class)
            row = _apply_humidity_suppression(row, row["humidity_pct"])
            row = _random_zero_clip(row, gas_class)

            for k in ["mq2_ppm", "mq7_ppm", "mq135_ppm", "mq136_ppm"]:
                row[k] = max(0.0, round(_adc_quantise(row[k]), 4))

            row["gas_class"] = gas_class
            row["timestamp"] = ts.strftime("%Y-%m-%dT%H:%M:%S")
            row["notes"] = f"Realistic augmented — pure {gas_class}"
            records.append(row)
            ts += timedelta(seconds=5)

        ts += timedelta(minutes=10)

    # Mixture rows
    mixture_notes = {
        "CO+H2S":       "Li-ion battery burning on PCB board (Sri Lanka lab)",
        "CO+BENZENE":   "FR4 PCB board burning — complex organic combustion",
        "H2S+BENZENE":  "CRT monitor + plastic cable burning mixture",
        "AMMONIA+CO":   "NiCd battery + soldering flux combustion",
        "AMMONIA+H2S":  "Mixed battery pack degradation",
    }

    for mixture_name, profile in MIXTURE_PROFILES.items():
        for i in range(n_per_mixture):
            row = {}
            for feat, (mean, std, lo, hi) in profile.items():
                val = np.random.normal(mean, std)
                row[feat] = round(float(np.clip(val, lo, hi)), 2)

            row = _apply_humidity_suppression(row, row["humidity_pct"])
            row = _apply_sensor_drift(row, i, n_per_mixture)
            row = _apply_warmup_noise(row, i)

            for k in ["mq2_ppm", "mq7_ppm", "mq135_ppm", "mq136_ppm"]:
                row[k] = max(0.0, round(_adc_quantise(row[k]), 4))

            row["gas_class"] = mixture_name
            row["timestamp"] = ts.strftime("%Y-%m-%dT%H:%M:%S")
            row["notes"] = mixture_notes[mixture_name]
            records.append(row)
            ts += timedelta(seconds=5)

        ts += timedelta(minutes=10)

    df = pd.DataFrame(records)
    cols = [
        "timestamp",
        "mq2_ppm", "mq7_ppm", "mq135_ppm", "mq136_ppm",
        "temperature_c", "humidity_pct",
        "gas_class", "notes"
    ]
    df = df[cols]
    df = df.sample(frac=1, random_state=SEED).reset_index(drop=True)
    return df


# =============================================================================
# Statistics printer
# =============================================================================

def print_stats(df, name):
    print(f"\n{'=' * 60}")
    print(f"  {name}")
    print(f"{'=' * 60}")
    print(f"  Total rows     : {len(df)}")
    print(f"  Class distribution:")
    for cls, cnt in df["gas_class"].value_counts().items():
        print(f"    {cls:<20s} {cnt:>4d} rows")
    print(f"\n  Feature statistics (mq2_ppm):")
    print(df.groupby("gas_class")["mq2_ppm"].agg(["mean", "std", "min", "max"]).round(2).to_string())
    print(f"\n  Feature statistics (mq7_ppm):")
    print(df.groupby("gas_class")["mq7_ppm"].agg(["mean", "std", "min", "max"]).round(2).to_string())
    print(f"\n  Feature statistics (mq135_ppm):")
    print(df.groupby("gas_class")["mq135_ppm"].agg(["mean", "std", "min", "max"]).round(2).to_string())
    print(f"\n  Feature statistics (mq136_ppm):")
    print(df.groupby("gas_class")["mq136_ppm"].agg(["mean", "std", "min", "max"]).round(2).to_string())


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    os.makedirs(DATASET_DIR, exist_ok=True)

    print("Generating realistic single-label dataset...")
    df_single = generate_single_label(n_per_class=ROWS_PER_CLASS)
    df_single.to_csv(OUT_SINGLE, index=False)
    print_stats(df_single, "Single-label realistic dataset")
    print(f"\n  Saved -> {OUT_SINGLE}")

    print("\n\nGenerating realistic multi-label dataset...")
    df_multi = generate_multilabel(n_per_mixture=100, n_single_label=50)
    df_multi.to_csv(OUT_MULTI, index=False)
    print_stats(df_multi, "Multi-label realistic dataset")
    print(f"\n  Saved -> {OUT_MULTI}")

    print("\n\nDone! Next steps:")
    print("  1. Use realistic_lab_readings.csv      -> retrain single-label RF")
    print("  2. Use realistic_lab_readings_multi.csv -> retrain multi-label RF")
    print("  3. Run your existing ML pipeline notebooks (04, 05, 06, 07)")
    print("  4. Replace pkl files in backend/ml_models/")
