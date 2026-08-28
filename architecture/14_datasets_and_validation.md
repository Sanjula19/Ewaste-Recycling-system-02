# 14 — Datasets and Validation Plan

## 14.1 Dataset Summary

| # | Dataset | Source | Samples | Use Case |
|---|---------|--------|---------|----------|
| D1 | UCI Gas Sensor Array Drift | UCI ML Repository | 13,910 | Primary ML training |
| D2 | MQ Sensor 2023 | Mendeley Data | ~2,000 | MQ-specific patterns |
| D3 | UCI Gas Sensor + Concentration | UCI ML Repository | ~4,000 | ppm validation |
| D4 | WHO Safety Limits (manual CSV) | WHO/NIOSH/OSHA | 6 records | Threshold calibration |
| D5 | Self-collected Lab Data | Lab simulation | 200+ | Novel contribution |

---

## 14.2 Dataset Details

### D1 — UCI Gas Sensor Array Drift Dataset
```
URL:     https://archive.ics.uci.edu/dataset/270
Classes: 6 gases (Ethanol, Ethylene, Ammonia, Acetaldehyde, Acetone, Toluene)
Format:  Text files → convert to CSV
Sensors: 16 MOX sensors (we use analog subset)
Purpose: Training multi-class classifier on real sensor array data
Action:  Map their gas labels to our 7 classes during preprocessing
```

### D2 — MQ Sensor Dataset 2023 (Mendeley)
```
URL:     https://data.mendeley.com/datasets/jmhr42p7sf/1
Classes: Multiple gas types from MQ sensor readings
Format:  CSV
Purpose: MQ-specific sensor response patterns
Action:  Directly usable; filter to our target gas classes
```

### D3 — UCI Gas Sensor + Concentration
```
URL:     https://archive.ics.uci.edu/dataset/1081
Classes: Gas type + concentration in ppm
Format:  CSV
Purpose: Validation of ppm conversion accuracy
Action:  Cross-validate our sensor conversion formulas
```

### D4 — WHO Safety Limits CSV (Manual)
```
Source:  WHO Air Quality Guidelines + NIOSH Pocket Guide + OSHA PEL
Format:  Manual CSV creation (see template below)
Purpose: Populate who_thresholds.json knowledge base
```

### D5 — Self-Collected Lab Data (Novel Contribution)
```
Method:  Lab simulation near e-waste items
         → CRT monitor near sensors
         → PCB burning
         → Battery charging
Setup:   ESP32 logging to CSV via Serial port
Samples: Minimum 200 (target: 500)
Purpose: Novel dataset; validate real-world performance
         Cite in paper as primary novel contribution
```

---

## 14.3 WHO Limits CSV Template (`data/who_thresholds.csv`)

```csv
gas_class,gas_name,sensor,who_limit,niosh_rel,osha_pel,unit,source
CO,Carbon Monoxide,mq7,25,35,50,ppm,WHO AQG 2021 / NIOSH PG
LPG,Liquefied Petroleum Gas,mq2,21000,21000,21000,ppm,"LEL-based, OSHA 29 CFR 1910.106"
BENZENE,Benzene,mq135,0.1,0.1,1.0,ppm,"NIOSH lowest feasible, OSHA PEL"
AMMONIA,Ammonia,mq135,25,25,50,ppm,"NIOSH REL, OSHA PEL 1910.1000"
MERCURY,Mercury Vapor,mq303,0.025,0.05,0.1,mg/m3,"WHO acute 1hr, NIOSH REL"
H2S,Hydrogen Sulphide,mq136,1,1,20,ppm,"NIOSH ceiling 10min, OSHA PEL"
```

---

## 14.4 Dataset Preprocessing Pipeline

```python
# ml/scripts/preprocess.py

## Step 1: Load and label all datasets
datasets = {
    'uci_drift':    load_uci_drift('datasets/raw/uci_gas_sensor_drift/'),
    'mq_2023':      load_csv('datasets/raw/mq_sensor_2023/data.csv'),
    'collected':    load_csv('datasets/collected/lab_readings.csv'),
}

## Step 2: Standardize column names
#  All datasets must have: [mq2, mq7, mq135, mq303, mq136, temp, hum, label]

## Step 3: Label encoding
LABEL_MAP = {
    'CO':       0,
    'LPG':      1,
    'BENZENE':  2,
    'AMMONIA':  3,
    'MERCURY':  4,
    'H2S':      5,
    'CLEAN':    6,
}

## Step 4: Handle missing values
df.fillna(df.median(), inplace=True)   # Median imputation for sensor values

## Step 5: Remove outliers (IQR method)
Q1 = df.quantile(0.25)
Q3 = df.quantile(0.75)
IQR = Q3 - Q1
df = df[~((df < (Q1 - 1.5*IQR)) | (df > (Q3 + 1.5*IQR))).any(axis=1)]

## Step 6: Normalize (MinMaxScaler)
from sklearn.preprocessing import MinMaxScaler
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)

## Step 7: Train/Test split
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42, stratify=y
)

## Step 8: Handle imbalance (if needed)
from imblearn.over_sampling import SMOTE
smote = SMOTE(random_state=42)
X_train_res, y_train_res = smote.fit_resample(X_train, y_train)
```

---

## 14.5 Validation Plan

### 14.5.1 ML Model Validation

| Test | Method | Acceptance Criteria |
|------|--------|---------------------|
| Accuracy | 80/20 split + 5-fold CV | RF Accuracy > 90% |
| F1-Score | Weighted F1 on test set | F1 > 0.88 |
| Class-wise recall | Per-class recall | No class < 0.80 recall |
| Confusion matrix | Visual heatmap | No critical mis-classification (e.g., Mercury→CLEAN) |
| Inference time | `time.perf_counter()` | < 200ms per sample |

### 14.5.2 System Integration Validation

| Test | Method | Acceptance Criteria |
|------|--------|---------------------|
| End-to-end latency | Timestamp at sensor → dashboard | < 5 seconds total |
| MQTT reliability | 100 messages; count received | > 99% delivery rate |
| Threshold accuracy | Known ppm vs WHO limit | 100% correct assignment |
| Alert generation | 20 RED-level test cases | 100% alert trigger rate |
| Dashboard refresh | Visual confirmation | Live update within 5 sec |

### 14.5.3 Sensor Validation

| Test | Method | Acceptance Criteria |
|------|--------|---------------------|
| Sensor response | Known gas concentration applied | Within ±15% of reference |
| Warm-up time | Compare reading before/after warm-up | Stable after 60 sec |
| Cross-sensitivity | Apply one gas; check other sensors | Primary sensor shows >3× response vs others |

### 14.5.4 Knowledge Base Validation

| Test | Method | Acceptance Criteria |
|------|--------|---------------------|
| Gas→device lookup | 7 gas classes tested | 100% correct mapping |
| WHO limit lookup | 6 gases × 3 limits | 100% correct values |
| Action completeness | Expert review | All actions meet NIOSH/WHO guidance |

---

## 14.6 Test Case Template (`docs/validation/test_cases.md`)

```markdown
## TC-001: CO Detection and Alert
- **Input:** mq7_ppm = 45 (exceeds NIOSH TWA of 35 ppm)
- **Expected Gas Class:** CO
- **Expected Risk Level:** RED
- **Expected Source Device:** PCBs / Soldering
- **Expected Action:** "Evacuate area" present in action list
- **Expected End-to-End Latency:** < 5 seconds
- **Result:** [PASS / FAIL]
- **Actual Values:** [fill after testing]

## TC-002: Mercury Vapor Detection and Alert
- **Input:** mq303_ppm = 0.06 mg/m³ (exceeds WHO limit of 0.025 mg/m³)
- **Expected Gas Class:** Mercury Vapor
- **Expected Risk Level:** RED
- **Expected Source Device:** CRT Monitor
- **Expected Exceeded By:** ~140%
- **Result:** [PASS / FAIL]

## TC-003: Clean Air — No Alert
- **Input:** All sensors at baseline (clean air)
- **Expected Gas Class:** CLEAN
- **Expected Risk Level:** GREEN
- **Expected Alerts Generated:** 0
- **Result:** [PASS / FAIL]
```

---

## 14.7 Data Collection Protocol (Self-Collected Dataset)

```markdown
## Lab Data Collection Protocol

### Setup
1. Place ESP32 + sensors on breadboard in lab
2. Ensure 60-second warm-up completed
3. Ensure clean air baseline recorded (30 samples labelled "CLEAN")

### Collection Sessions (per gas)
For each target gas (CO, Benzene, Ammonia, Mercury, H2S, LPG):
1. Introduce gas source near sensor array
2. Record 30-50 readings at 5-second intervals
3. Label all readings with gas class
4. Allow sensors to return to clean air baseline before next session

### Recording Format
Timestamp, mq2_ppm, mq7_ppm, mq135_ppm, mq303_ppm, mq136_ppm, temp_c, hum_pct, gas_class

### Safety
⚠️ Conduct all gas exposure tests in a well-ventilated area or fume hood
⚠️ Use appropriate PPE during collection
⚠️ Keep quantities minimal and controlled
```
