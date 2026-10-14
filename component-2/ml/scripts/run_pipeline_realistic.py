"""
run_pipeline_realistic.py
==========================
Retrains the ML pipeline using the realistic augmented dataset.
Uses 6 features (NO mq303_ppm, NO MERCURY class) to match the
deployed model contract and the real ESP32 sensor hardware.

Features: mq2_ppm, mq7_ppm, mq135_ppm, mq136_ppm, temperature_c, humidity_pct
Classes:  AMMONIA, BENZENE, CLEAN, CO, H2S, LPG

Run from repo root:
  python component-2/ml/scripts/run_pipeline_realistic.py
"""

import sys, time, warnings, json, shutil
from pathlib import Path
from collections import Counter

import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.metrics import (accuracy_score, f1_score, confusion_matrix,
                             hamming_loss, jaccard_score)
try:
    from imblearn.over_sampling import SMOTE
    HAS_SMOTE = True
except ImportError:
    HAS_SMOTE = False

warnings.filterwarnings('ignore')

# ── Paths ─────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent.parent
DATA_DIR    = ROOT / 'datasets'
MODEL_DIR   = ROOT / 'models'
SAVE_DIR    = ROOT / 'results'
SPLIT_DIR   = DATA_DIR / 'processed' / 'train_test_split'
BACKEND_DIR = ROOT.parent / 'backend' / 'ml_models'

for d in [MODEL_DIR, SAVE_DIR, SPLIT_DIR, SAVE_DIR / 'confusion_matrices', BACKEND_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Feature contract (MUST match ml_service.py FEATURE_ORDER) ────────────
FEATURE_NAMES = ['mq2_ppm', 'mq7_ppm', 'mq135_ppm', 'mq136_ppm',
                 'temperature_c', 'humidity_pct']
TARGET_COL    = 'gas_class'

# Single-label classes (no MERCURY — sensor not available in Sri Lanka)
SINGLE_LABEL_CLASSES = {'AMMONIA', 'BENZENE', 'CLEAN', 'CO', 'H2S', 'LPG'}

# Multi-label classes (mixtures + single)
MULTI_LABEL_CLASSES  = {
    'AMMONIA', 'BENZENE', 'CLEAN', 'CO', 'H2S', 'LPG',
    'CO+H2S', 'CO+BENZENE', 'H2S+BENZENE', 'AMMONIA+CO', 'AMMONIA+H2S',
}


# =============================================================================
# STEP 1 — Load Data
# =============================================================================
print("=" * 60)
print("STEP 1: LOADING REALISTIC DATASET")
print("=" * 60)

realistic_path = DATA_DIR / 'collected' / 'realistic_lab_readings.csv'
fallback_path  = DATA_DIR / 'collected' / 'lab_reading.csv'

if realistic_path.exists():
    df = pd.read_csv(realistic_path)
    print(f"[OK] Loaded realistic dataset: {len(df)} rows from {realistic_path.name}")
elif fallback_path.exists():
    df = pd.read_csv(fallback_path)
    print(f"[OK] Loaded fallback dataset: {len(df)} rows from {fallback_path.name}")
else:
    print("[ERR] No dataset found. Run generate_realistic_data.py first.")
    sys.exit(1)

# Drop any columns not in our feature set + target
available = [c for c in FEATURE_NAMES if c in df.columns]
if len(available) < len(FEATURE_NAMES):
    missing = set(FEATURE_NAMES) - set(df.columns)
    print(f"[ERR] Missing columns: {missing}")
    sys.exit(1)

df = df[FEATURE_NAMES + [TARGET_COL]].dropna()

# Keep only single-label classes
df = df[df[TARGET_COL].isin(SINGLE_LABEL_CLASSES)].copy()
df.drop_duplicates(inplace=True)
print(f"     After filter: {len(df)} rows | Classes: {df[TARGET_COL].value_counts().to_dict()}")


# =============================================================================
# STEP 2 — Preprocess
# =============================================================================
print("\n" + "=" * 60)
print("STEP 2: PREPROCESSING")
print("=" * 60)

le = LabelEncoder()
y  = le.fit_transform(df[TARGET_COL])
X  = df[FEATURE_NAMES].values.astype(np.float32)
joblib.dump(le, MODEL_DIR / 'label_encoder.pkl')
print(f"[OK] LabelEncoder | Classes: {list(le.classes_)}")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y)

scaler = MinMaxScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)
joblib.dump(scaler, MODEL_DIR / 'scaler.pkl')
print(f"[OK] MinMaxScaler | Train: {X_train_s.shape}, Test: {X_test_s.shape}")

# SMOTE for imbalanced classes (shouldn't be needed with realistic data)
if HAS_SMOTE:
    counts = Counter(y_train)
    if max(counts.values()) / max(min(counts.values()), 1) > 2.0:
        min_c = min(counts.values())
        sm = SMOTE(random_state=42, k_neighbors=min(5, min_c - 1))
        X_train_s, y_train = sm.fit_resample(X_train_s, y_train)
        print(f"[OK] SMOTE -> {len(X_train_s)} training samples")


# =============================================================================
# STEP 3 — Train Single-Label Random Forest
# =============================================================================
print("\n" + "=" * 60)
print("STEP 3: TRAIN SINGLE-LABEL RANDOM FOREST")
print("=" * 60)

rf = RandomForestClassifier(
    n_estimators=300,
    max_depth=None,
    class_weight='balanced',
    random_state=42,
    n_jobs=-1,
)

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
t0 = time.perf_counter()
cv_scores = cross_val_score(rf, X_train_s, y_train, cv=cv,
                             scoring='f1_weighted', n_jobs=-1)
rf.fit(X_train_s, y_train)
t1 = time.perf_counter()

y_pred = rf.predict(X_test_s)
acc    = accuracy_score(y_test, y_pred)
f1w    = f1_score(y_test, y_pred, average='weighted', zero_division=0)

print(f"  CV F1 (5-fold): {cv_scores.mean()*100:.2f}% +/- {cv_scores.std()*100:.2f}%")
print(f"  Test Accuracy : {acc*100:.2f}%")
print(f"  Test F1 Weighted: {f1w*100:.2f}%")
print(f"  Train time    : {t1-t0:.1f}s")

joblib.dump(rf, MODEL_DIR / 'random_forest_v1.pkl')
print(f"[OK] random_forest_v1.pkl saved")


# =============================================================================
# STEP 4 — Train Multi-Label Random Forest (Mixtures)
# =============================================================================
print("\n" + "=" * 60)
print("STEP 4: TRAIN MULTI-LABEL RANDOM FOREST")
print("=" * 60)

multi_path = DATA_DIR / 'collected' / 'realistic_lab_readings_multi.csv'
if multi_path.exists():
    df_m = pd.read_csv(multi_path)
    df_m = df_m[df_m[TARGET_COL].isin(MULTI_LABEL_CLASSES)].copy()
    df_m = df_m[FEATURE_NAMES + [TARGET_COL]].dropna()

    # Convert compound class strings to list-of-labels
    def _split_labels(cls_str):
        return cls_str.split('+')

    df_m['label_list'] = df_m[TARGET_COL].apply(_split_labels)
    Xm = df_m[FEATURE_NAMES].values.astype(np.float32)
    Xm_s = scaler.transform(Xm)   # use same scaler fitted on training set

    mlb = MultiLabelBinarizer()
    Ym  = mlb.fit_transform(df_m['label_list'])

    Xm_tr, Xm_te, Ym_tr, Ym_te = train_test_split(
        Xm_s, Ym, test_size=0.2, random_state=42)

    multi_rf = MultiOutputClassifier(
        RandomForestClassifier(n_estimators=200, class_weight='balanced',
                               random_state=42, n_jobs=-1),
        n_jobs=-1,
    )
    t0 = time.perf_counter()
    multi_rf.fit(Xm_tr, Ym_tr)
    t1 = time.perf_counter()

    Ym_pred = multi_rf.predict(Xm_te)
    hl  = hamming_loss(Ym_te, Ym_pred)
    jac = jaccard_score(Ym_te, Ym_pred, average='samples', zero_division=0)
    print(f"  Hamming Loss  : {hl:.4f}")
    print(f"  Jaccard Score : {jac*100:.2f}%")
    print(f"  Labels        : {list(mlb.classes_)}")
    print(f"  Train time    : {t1-t0:.1f}s")

    joblib.dump(multi_rf, MODEL_DIR / 'multilabel_rf_v1.pkl')
    joblib.dump(mlb,      MODEL_DIR / 'multilabel_binarizer.pkl')
    print(f"[OK] multilabel_rf_v1.pkl + multilabel_binarizer.pkl saved")
else:
    print("[!] realistic_lab_readings_multi.csv not found — skipping multi-label")
    multi_rf = None
    mlb      = None


# =============================================================================
# STEP 5 — Confusion Matrix + Charts
# =============================================================================
print("\n" + "=" * 60)
print("STEP 5: FIGURES")
print("=" * 60)

import seaborn as sns

cm  = confusion_matrix(y_test, y_pred)
cm_pct = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis] * 100

fig, ax = plt.subplots(figsize=(9, 7))
sns.heatmap(cm_pct, annot=True, fmt='.1f', cmap='RdYlGn',
            xticklabels=le.classes_, yticklabels=le.classes_,
            ax=ax, vmin=0, vmax=100, linewidths=0.5,
            annot_kws={'size': 11})
ax.set_title('Random Forest — Confusion Matrix (%)\nRealistic Dataset', fontsize=13, fontweight='bold')
ax.set_xlabel('Predicted Label', fontsize=11)
ax.set_ylabel('True Label', fontsize=11)
ax.tick_params(axis='x', rotation=45)
plt.tight_layout()
plt.savefig(SAVE_DIR / 'confusion_matrices' / 'best_model_confusion.png', dpi=150, bbox_inches='tight')
plt.close()
print("[OK] Confusion matrix saved")


# =============================================================================
# STEP 6 — Export to Backend
# =============================================================================
print("\n" + "=" * 60)
print("STEP 6: EXPORT TO BACKEND ml_models/")
print("=" * 60)

artifacts = ['random_forest_v1.pkl', 'scaler.pkl', 'label_encoder.pkl']
if (MODEL_DIR / 'multilabel_rf_v1.pkl').exists():
    artifacts += ['multilabel_rf_v1.pkl', 'multilabel_binarizer.pkl']

for art in artifacts:
    src = MODEL_DIR / art
    if src.exists():
        shutil.copy2(src, BACKEND_DIR / art)
        print(f"  [OK] {art} -> backend/ml_models/ ({src.stat().st_size//1024} KB)")

# Model card
model_card = {
    "model_name":    "EWaste Toxic Gas Classifier (Realistic Data)",
    "version":       "rf_v2_realistic",
    "description":   "Trained on augmented realistic sensor data with 6 features. No MERCURY class (sensor unavailable).",
    "features":      FEATURE_NAMES,
    "feature_count": len(FEATURE_NAMES),
    "gas_classes":   list(le.classes_),
    "class_count":   len(le.classes_),
    "single_label": {
        "best_model":       "Random Forest",
        "algorithm":        "RandomForestClassifier(n_estimators=300, class_weight=balanced)",
        "cv_f1_mean_pct":   round(cv_scores.mean() * 100, 2),
        "cv_f1_std_pct":    round(cv_scores.std()  * 100, 2),
        "test_accuracy_pct":round(acc * 100, 2),
        "test_f1_weighted_pct": round(f1w * 100, 2),
    },
    "multi_label": {
        "algorithm":    "MultiOutputClassifier(RandomForestClassifier(n_estimators=200))",
        "hamming_loss": round(hl, 4) if multi_rf else None,
        "jaccard_score_pct": round(jac * 100, 2) if multi_rf else None,
        "labels":       list(mlb.classes_) if mlb else [],
        "supported_mixtures": ["CO+H2S","CO+BENZENE","H2S+BENZENE","AMMONIA+CO","AMMONIA+H2S"],
    },
    "artifacts": {
        "single_label_model": "random_forest_v1.pkl",
        "multi_label_model":  "multilabel_rf_v1.pkl",
        "scaler":             "scaler.pkl",
        "label_encoder":      "label_encoder.pkl",
        "multilabel_binarizer": "multilabel_binarizer.pkl",
    },
    "adc_calibration": {
        "mq2":  {"RL": 5.0,  "R0": 9.83,  "A": 574.25, "B": -2.222, "gas": "LPG/Smoke"},
        "mq7":  {"RL": 10.0, "R0": 10.0,  "A": 99.042, "B": -1.518, "gas": "CO"},
        "mq135":{"RL": 20.0, "R0": 76.63, "A": 110.47, "B": -2.862, "gas": "Benzene/NH3"},
        "mq136":{"RL": 10.0, "R0": 15.0,  "A": 36.737, "B": -3.536, "gas": "H2S"},
    },
}
card_path = MODEL_DIR / 'model_card.json'
with open(card_path, 'w') as f:
    json.dump(model_card, f, indent=2)
shutil.copy2(card_path, BACKEND_DIR / 'model_card.json')
print("[OK] model_card.json saved and exported")


# =============================================================================
# FINAL SUMMARY
# =============================================================================
print("\n" + "=" * 60)
print("REALISTIC ML PIPELINE COMPLETE!")
print("=" * 60)
print(f"  Best Model   : Random Forest (6 features)")
print(f"  Test Accuracy: {acc*100:.2f}%")
print(f"  F1 Weighted  : {f1w*100:.2f}%")
print(f"  Classes      : {list(le.classes_)}")
print()
print("  Models exported to backend/ml_models/:")
for art in artifacts:
    p = BACKEND_DIR / art
    if p.exists():
        print(f"    {art} ({p.stat().st_size//1024} KB)")
print()
print("Next: docker compose up --build  (or restart uvicorn)")
