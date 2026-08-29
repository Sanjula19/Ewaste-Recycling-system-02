"""
Dataset Download Helper
========================
E-Waste Toxic Gas Detection System
Author: Sanjula Madushanka

Run this script to verify your dataset downloads and prepare the data directory.

Datasets needed:
  D1: UCI Gas Sensor Array Drift  → manual download (see link below)
  D2: MQ Sensor 2023 (Mendeley)  → manual download (see link below)
  D3: UCI Gas + Concentration     → manual download (see link below)
  D4: WHO Limits CSV              → created automatically by this script

Usage:
  python scripts/prepare_datasets.py
"""

import os
import sys
import csv
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────────────────────
ROOT     = Path(__file__).parent.parent
RAW_DIR  = ROOT / 'datasets' / 'raw'
DATA_DIR = ROOT / 'datasets'

for d in [RAW_DIR / 'uci_gas_sensor_drift',
          RAW_DIR / 'mq_sensor_2023',
          RAW_DIR / 'uci_gas_concentration',
          DATA_DIR / 'collected',
          DATA_DIR / 'processed' / 'train_test_split']:
    d.mkdir(parents=True, exist_ok=True)

# ─── D4: Create WHO Limits CSV ───────────────────────────────────────────────
WHO_CSV = ROOT / '..' / 'data' / 'who_thresholds.csv'
WHO_CSV.parent.mkdir(parents=True, exist_ok=True)

WHO_ROWS = [
    ['gas_class', 'gas_name', 'sensor', 'who_limit', 'niosh_rel', 'osha_pel', 'unit', 'system_green', 'system_yellow', 'system_red', 'source'],
    ['CO',       'Carbon Monoxide',          'mq7',   25,    35,    50,    'ppm',    12.5,   25.0,   35.0,  'WHO AQG 2021 / NIOSH PG'],
    ['LPG',      'Liquefied Petroleum Gas',  'mq2',   21000, 21000, 21000, 'ppm',    500,    1000,   2100,  'OSHA 29 CFR 1910.106 LEL-based'],
    ['BENZENE',  'Benzene',                  'mq135', 0.1,   0.1,   1.0,   'ppm',    0.25,   0.5,    1.0,   'NIOSH lowest feasible / OSHA PEL'],
    ['AMMONIA',  'Ammonia',                  'mq135', 25,    25,    50,    'ppm',    12.5,   25.0,   50.0,  'NIOSH REL / OSHA 1910.1000'],
    ['MERCURY',  'Mercury Vapor',            'mq303', 0.025, 0.05,  0.1,   'mg_m3',  0.0125, 0.025,  0.05,  'WHO acute 1hr / NIOSH REL'],
    ['H2S',      'Hydrogen Sulphide',        'mq136', 1,     1,     20,    'ppm',    0.5,    1.0,    5.0,   'NIOSH ceiling 10min / OSHA PEL'],
    ['CLEAN',    'Clean Air',                'all',   9999,  9999,  9999,  'ppm',    9999,   9999,   9999,  'No hazard'],
]

with open(WHO_CSV, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerows(WHO_ROWS)

print(f'[OK] WHO limits CSV created: {WHO_CSV}')


# --- Create Lab Readings Template --------------------------------------------
TEMPLATE_PATH = DATA_DIR / 'collected' / 'lab_readings_TEMPLATE.csv'
TEMPLATE_HEADER = [
    'timestamp', 'mq2_ppm', 'mq7_ppm', 'mq135_ppm', 'mq303_ppm', 'mq136_ppm',
    'temperature_c', 'humidity_pct', 'gas_class', 'notes'
]
TEMPLATE_EXAMPLES = [
    ['2026-07-31T10:00:00', 3.0,   2.0,   3.0,   0.001, 0.08, 27.0, 60.0, 'CLEAN',   'Baseline clean air'],
    ['2026-07-31T10:05:00', 30.0,  85.0,  12.0,  0.005, 0.30, 29.5, 62.0, 'CO',      'PCB burning test'],
    ['2026-07-31T10:10:00', 8.5,   5.0,   6.2,   0.052, 0.21, 28.0, 65.0, 'MERCURY', 'CRT monitor near sensor'],
    ['2026-07-31T10:15:00', 10.0,  6.5,   9.0,   0.004, 3.8,  30.0, 68.0, 'H2S',     'Li-ion battery test'],
    ['2026-07-31T10:20:00', 210.0, 10.0,  8.5,   0.004, 0.20, 26.0, 58.0, 'LPG',     'Capacitor test'],
    ['2026-07-31T10:25:00', 15.0,  8.0,   46.0,  0.006, 0.40, 28.5, 63.0, 'BENZENE', 'Plastic burning'],
    ['2026-07-31T10:30:00', 12.0,  6.0,   62.0,  0.004, 0.30, 29.0, 66.0, 'AMMONIA', 'NiCd battery test'],
]

if not TEMPLATE_PATH.exists():
    with open(TEMPLATE_PATH, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(TEMPLATE_HEADER)
        writer.writerows(TEMPLATE_EXAMPLES)
    print(f'[OK] Lab readings template created: {TEMPLATE_PATH}')
else:
    print(f'[i]  Template already exists: {TEMPLATE_PATH}')


# --- Check for Dataset Files -------------------------------------------------
print('\n=== DATASET STATUS ===')

datasets = {
    'D1 UCI Gas Sensor Drift':    RAW_DIR / 'uci_gas_sensor_drift',
    'D2 MQ Sensor 2023':          RAW_DIR / 'mq_sensor_2023',
    'D3 UCI Gas + Concentration': RAW_DIR / 'uci_gas_concentration',
    'D4 WHO Limits CSV':          WHO_CSV,
    'D5 Self-collected data':     DATA_DIR / 'collected' / 'lab_readings.csv',
}

download_links = {
    'D1 UCI Gas Sensor Drift':    'https://archive.ics.uci.edu/dataset/270/gas+sensor+array+drift+dataset',
    'D2 MQ Sensor 2023':          'https://data.mendeley.com/datasets/jmhr42p7sf/1',
    'D3 UCI Gas + Concentration': 'https://archive.ics.uci.edu/dataset/1081',
    'D5 Self-collected data':     'Collect using ESP32 firmware -> copy CSV here',
}

all_ready = True
for name, path in datasets.items():
    if isinstance(path, Path) and path.is_dir():
        csv_files = list(path.glob('*.csv')) + list(path.glob('*.txt')) + list(path.glob('*.data'))
        status = f'[OK] {len(csv_files)} files' if csv_files else '[EMPTY] folder'
        if not csv_files:
            all_ready = False
    elif isinstance(path, Path) and path.is_file():
        status = f'[OK] {path.stat().st_size / 1024:.1f} KB'
    else:
        status = '[MISSING]'
        all_ready = False

    print(f'  {name:<30}: {status}')
    if '[MISSING]' in status or '[EMPTY]' in status:
        link = download_links.get(name, '')
        if link:
            print(f'    -> Download: {link}')
            print(f'    -> Place files in: {datasets[name]}')

print()
if all_ready:
    print('[OK] All datasets ready! Open 01_data_exploration.ipynb to begin.')
else:
    print('[!]  Some datasets missing. Download them and run this script again.')
    print()
    print('IMPORTANT: After downloading, place CSV/data files inside the')
    print('corresponding folder under ml/datasets/raw/')
    print()
    print('Alternatively: Run notebooks with DEMO data (auto-generated in notebook 01)')
    print('               Replace with real data when available')
