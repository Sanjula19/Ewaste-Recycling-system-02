# 06 — Machine Learning Pipeline Architecture

## 6.1 ML Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ML PIPELINE (OFFLINE PHASE)                      │
│                                                                     │
│  [Raw Datasets]                                                     │
│    UCI Gas Sensor Drift    ─────┐                                   │
│    MQ Sensor 2023 (Mendeley)   ├──► MERGE & LABEL ──► combined.csv │
│    UCI Gas + Concentration ────┘                                    │
│    Your Collected Data ────────────────────────────────────────────►│
│                                          │                          │
│                                          ▼                          │
│                              ┌─────────────────────┐               │
│                              │  01: DATA EXPLORATION│               │
│                              │  - Distribution plots│               │
│                              │  - Correlation matrix│               │
│                              │  - Missing value check│              │
│                              │  - Class balance check│              │
│                              └───────────┬──────────┘               │
│                                          │                          │
│                                          ▼                          │
│                              ┌─────────────────────┐               │
│                              │  02: PREPROCESSING  │               │
│                              │  - Handle NaN values │               │
│                              │  - Remove outliers   │               │
│                              │  - Normalize (MinMax)│               │
│                              │  - Encode labels     │               │
│                              │  - Train/Test split  │               │
│                              │    (80% / 20%)       │               │
│                              └───────────┬──────────┘               │
│                                          │                          │
│                                          ▼                          │
│                              ┌─────────────────────┐               │
│                              │  03: FEATURE ENG.   │               │
│                              │  - Select: 7 features│               │
│                              │    [MQ2, MQ7, MQ135, │               │
│                              │     MQ303, MQ136,    │               │
│                              │     temp, humidity]  │               │
│                              │  - Optional PCA      │               │
│                              │  - Feature importance│               │
│                              └───────────┬──────────┘               │
│                                          │                          │
│                              ┌───────────▼──────────┐               │
│                              │  04: MODEL TRAINING  │               │
│                   ┌──────────┴──────────────────────┴─────────┐    │
│                   │                                            │    │
│            ┌──────▼──────┐  ┌──────────┐  ┌────┐  ┌───────┐ │    │
│            │ Random      │  │  SVM     │  │ DT │  │  NB   │ │    │
│            │ Forest ★   │  │(RBF/Lin) │  │    │  │       │ │    │
│            │             │  │          │  │    │  │       │ │    │
│            │n_estimators │  │ C, gamma │  │max_│  │var_   │ │    │
│            │= 100-500    │  │ tuned    │  │dep │  │smooth │ │    │
│            └──────┬──────┘  └────┬─────┘  └──┬─┘  └──┬────┘ │    │
│                   └──────────────┴────────────┴────────┘      │    │
│                              │  05: EVALUATION              ◄──┘    │
│                              │                                     │
│                              │  Metrics per model:                 │
│                              │  - Accuracy                         │
│                              │  - Precision (per class)            │
│                              │  - Recall (per class)               │
│                              │  - F1-Score (macro + weighted)      │
│                              │  - Confusion Matrix                 │
│                              │  - ROC-AUC (one-vs-rest)           │
│                              │  - Training time                    │
│                              │  - Inference time                   │
│                              │                                     │
│                              ▼                                     │
│                    ┌──────────────────┐                            │
│                    │ 06: BEST MODEL   │                            │
│                    │ SELECTION        │                            │
│                    │                  │                            │
│                    │ Primary: RF      │                            │
│                    │ (highest F1)     │                            │
│                    └────────┬─────────┘                            │
│                             │                                      │
│                             ▼                                      │
│                    ┌──────────────────┐                            │
│                    │ 07: EXPORT       │                            │
│                    │ random_forest.pkl│                            │
│                    │ label_encoder.pkl│                            │
│                    │ scaler.pkl       │                            │
│                    └─────────────────-┘                            │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼ (copy to backend/ml_models/)
┌─────────────────────────────────────────────────────────────────────┐
│                    ML PIPELINE (ONLINE/INFERENCE PHASE)             │
│                                                                     │
│  Live sensor reading → FastAPI → ml_service.py                     │
│    1. Load scaler.pkl → normalize input                             │
│    2. Load random_forest.pkl → predict                              │
│    3. Load label_encoder.pkl → decode class                         │
│    4. Return: class label + confidence probability                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6.2 Target Classes (Gas Labels)

| Label | Gas | Likely Sensors Active |
|-------|-----|-----------------------|
| `CO` | Carbon Monoxide | MQ-7 (primary), MQ-2 |
| `LPG` | LPG / Propane / Methane | MQ-2 (primary) |
| `BENZENE` | Benzene / VOC | MQ-135 (primary) |
| `AMMONIA` | Ammonia | MQ-135 (secondary mode) |
| `MERCURY` | Mercury Vapor | MQ-303 (primary) |
| `H2S` | Hydrogen Sulphide | MQ-136 (primary) |
| `CLEAN` | Clean air / No gas | All sensors low |

**Total classes: 7** (multi-class classification)

---

## 6.3 Feature Vector

```python
features = [
    mq2_ppm,       # Feature 1: LPG/Smoke indicator
    mq7_ppm,       # Feature 2: CO indicator
    mq135_ppm,     # Feature 3: VOC/NH3/Benzene indicator
    mq303_ppm,     # Feature 4: Mercury/Alcohol indicator
    mq136_ppm,     # Feature 5: H2S indicator
    temperature_c, # Feature 6: Environmental context
    humidity_pct   # Feature 7: Environmental context
]
# Shape: (1, 7) → predict → (1,) class label
```

---

## 6.4 Model Hyperparameter Search Space

### Random Forest (GridSearchCV)
```python
param_grid = {
    'n_estimators': [100, 200, 300, 500],
    'max_depth': [None, 10, 20, 30],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4],
    'max_features': ['sqrt', 'log2'],
    'class_weight': [None, 'balanced']
}
cv = StratifiedKFold(n_splits=5)
scoring = 'f1_weighted'
```

### SVM (GridSearchCV)
```python
param_grid = {
    'C': [0.1, 1, 10, 100],
    'gamma': ['scale', 'auto', 0.001, 0.01],
    'kernel': ['rbf', 'linear'],
    'class_weight': [None, 'balanced']
}
```

### Decision Tree (GridSearchCV)
```python
param_grid = {
    'max_depth': [3, 5, 10, 15, None],
    'criterion': ['gini', 'entropy'],
    'min_samples_split': [2, 5, 10],
    'class_weight': [None, 'balanced']
}
```

---

## 6.5 Evaluation Metrics — Justification

| Metric | Why It Matters for This Research |
|--------|----------------------------------|
| **Accuracy** | Overall correctness — baseline metric |
| **F1-Score (weighted)** | Handles class imbalance — primary metric |
| **Precision** | False positive rate — important: wrong gas ID wastes resources |
| **Recall** | False negative rate — critical: missing Mercury/H2S is dangerous |
| **Confusion Matrix** | Shows which gases are confused (e.g., CO vs LPG) |
| **ROC-AUC** | Probability quality — model confidence calibration |
| **Inference Time** | Must be <200ms for real-time system |

---

## 6.6 Expected Results Table Template (for your paper)

| Model | Accuracy | Precision | Recall | F1 (Weighted) | Inference Time |
|-------|----------|-----------|--------|---------------|----------------|
| Random Forest | ~XX% | ~XX% | ~XX% | ~XX% | ~Xms |
| SVM (RBF) | ~XX% | ~XX% | ~XX% | ~XX% | ~Xms |
| Decision Tree | ~XX% | ~XX% | ~XX% | ~XX% | ~Xms |
| Naive Bayes | ~XX% | ~XX% | ~XX% | ~XX% | ~Xms |

> Fill this table after running `05_model_evaluation.ipynb`

---

## 6.7 Class Imbalance Handling Strategy

```
If training data is imbalanced (e.g., CLEAN >> MERCURY):

Step 1: Visualize class distribution in 01_data_exploration.ipynb
Step 2: Apply SMOTE (Synthetic Minority Over-sampling Technique)
  → from imblearn.over_sampling import SMOTE
  → smote = SMOTE(random_state=42)
  → X_res, y_res = smote.fit_resample(X_train, y_train)

Step 3: Or use class_weight='balanced' in Random Forest

Step 4: Report class distribution BEFORE and AFTER in results section
```

---

## 6.8 Model Persistence Format

```python
import joblib

# Save
joblib.dump(rf_model,      'models/random_forest_v1.pkl')
joblib.dump(label_encoder, 'models/label_encoder.pkl')
joblib.dump(scaler,        'models/scaler.pkl')

# Load in FastAPI
rf_model      = joblib.load('ml_models/random_forest_v1.pkl')
label_encoder = joblib.load('ml_models/label_encoder.pkl')
scaler        = joblib.load('ml_models/scaler.pkl')

# Inference
features_scaled = scaler.transform([[mq2, mq7, mq135, mq303, mq136, temp, hum]])
pred_idx        = rf_model.predict(features_scaled)[0]
pred_label      = label_encoder.inverse_transform([pred_idx])[0]
confidence      = rf_model.predict_proba(features_scaled).max()
```

---

## 6.9 Novel Feature — Multi-Label Gas Mixture Detection

> **Research Gap Addressed:** Existing gas detection systems classify only ONE gas at a time.
> In real e-waste environments, multiple gases are released simultaneously.
> This system uses **multi-label classification** to detect gas mixtures.

### 6.9.1 Problem with Single-Label Classification

```
Standard system:
  Input: [mq2=35, mq7=88, mq135=11, mq303=0.005, mq136=3.8, T=29, H=64]
  Output: "CO"   ← WRONG — H2S also present from the Li-ion battery

Multi-label system:
  Same input
  Output: ["CO", "H2S"]   ← CORRECT — both gases detected simultaneously
```

### 6.9.2 Real E-Waste Mixture Scenarios

| Mixture | Source Situation | Gases Released |
|---------|-----------------|----------------|
| `CO + H2S` | Li-ion battery burning on a PCB | CO from PCB, H2S from battery |
| `CO + BENZENE` | FR4 PCB board burning | CO + aromatic VOCs |
| `CO + MERCURY` | CRT monitor near burning PCB | CO from solder, Hg from CRT |
| `H2S + BENZENE` | Li-ion rupture + plastic melting | H2S from electrolyte, benzene from plastic |
| `AMMONIA + CO` | NiCd battery + PCB combustion | NH3 from battery, CO from PCB |
| `AMMONIA + H2S` | Mixed battery types decomposing | Both from battery chemicals |
| `MERCURY + BENZENE` | CRT + plastic casing burning | Hg vapor + plastic VOCs |

### 6.9.3 Multi-Label Architecture

```
                     7 sensor features
                          │
                          ▼
              ┌───────────────────────┐
              │  MinMaxScaler         │
              │  (same as single)     │
              └───────────┬───────────┘
                          │
                          ▼
       ┌──────────────────────────────────┐
       │  MultiOutputClassifier           │
       │  (one binary RF per gas label)   │
       │                                  │
       │  ┌──────┐ ┌──────┐ ┌──────┐     │
       │  │ CO?  │ │ H2S? │ │ LPG? │ ... │
       │  │  RF  │ │  RF  │ │  RF  │     │
       │  └──┬───┘ └──┬───┘ └──┬───┘     │
       │     │        │        │          │
       │  [0/1]    [0/1]    [0/1]         │
       └──────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  MultiLabelBinarizer  │
              │  decode binary output │
              └───────────┬───────────┘
                          │
                          ▼
          Output: ["CO", "H2S"]  ← Gas mixture detected
```

### 6.9.4 Multi-Label Evaluation Metrics

| Metric | Formula | Why Used |
|--------|---------|---------|
| **Hamming Loss** | fraction of wrong labels | Primary: measures per-label error |
| **Jaccard Score** | \|predicted ∩ true\| / \|predicted ∪ true\| | Best for multi-label overlap |
| **F1 Weighted** | weighted avg per-label F1 | Handles label imbalance |
| **Exact Match** | 100% correct label set | Strictest metric |

### 6.9.5 Multi-Label Model Persistence

```python
import joblib

# Save
joblib.dump(multilabel_model,    'models/multilabel_rf_v1.pkl')
joblib.dump(multilabel_binarizer,'models/multilabel_binarizer.pkl')
joblib.dump(scaler,              'models/scaler.pkl')

# Load in FastAPI
ml_model   = joblib.load('ml_models/multilabel_rf_v1.pkl')
binarizer  = joblib.load('ml_models/multilabel_binarizer.pkl')
scaler     = joblib.load('ml_models/scaler.pkl')

# Inference — returns LIST of detected gases
features_scaled = scaler.transform([[mq2, mq7, mq135, mq303, mq136, temp, hum]])
Y_pred_binary   = ml_model.predict(features_scaled)      # e.g. [[1, 0, 0, 1, 0, 0, 0]]
detected_gases  = binarizer.inverse_transform(Y_pred_binary)  # [('CO', 'H2S')]
is_mixture      = len(detected_gases[0]) > 1             # True

# Also get per-label probabilities (confidence)
if hasattr(ml_model, 'estimators_'):
    proba = {label: est.predict_proba(features_scaled)[0][1]
             for label, est in zip(binarizer.classes_, ml_model.estimators_)}
```

### 6.9.6 Data Generation for Mixture Training

Since real mixture lab readings require simultaneous gas exposure (complex to collect),
mixture training data is generated using the **sensor superposition principle**:

```
Mixture reading = ratio_A × pure_gas_A_reading + ratio_B × pure_gas_B_reading + noise
```

This is physically valid because MQ sensor responses are approximately additive
for low concentrations (established in e-nose literature).

Script: `ml/scripts/generate_mixtures.py`
Output: `ml/datasets/collected/lab_readings_multilabel.csv`

```
