"""
retrain_without_mercury.py
===========================
Retrains both single-label and multi-label models WITHOUT MQ-303 sensor / MERCURY class.
6 features, 6 gas classes.

Author: Sanjula Madushanka | Final Year Research Y4S2
"""

import time
import json
import shutil
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import joblib

from sklearn.preprocessing import MinMaxScaler, LabelEncoder, MultiLabelBinarizer
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.multioutput import MultiOutputClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report,
    hamming_loss, jaccard_score
)

warnings.filterwarnings('ignore')

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent.parent
DATA_DIR    = ROOT / 'datasets'
MODEL_DIR   = ROOT / 'models'
SAVE_DIR    = ROOT / 'results'
BACKEND_DIR = ROOT.parent / 'backend' / 'ml_models'

for d in [MODEL_DIR, SAVE_DIR, BACKEND_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# NEW: 6 features (no mq303_ppm)
FEATURE_NAMES = ['mq2_ppm', 'mq7_ppm', 'mq135_ppm', 'mq136_ppm', 'temperature_c', 'humidity_pct']
TARGET_COL    = 'gas_class'

# NEW: 6 gas classes (no MERCURY)
GAS_LABELS = ['AMMONIA', 'BENZENE', 'CLEAN', 'CO', 'H2S', 'LPG']

print("=" * 70)
print("RETRAINING ML MODELS — WITHOUT MQ-303 SENSOR / MERCURY CLASS")
print("  Features: 6 (mq2, mq7, mq135, mq136, temp, humidity)")
print("  Classes:  6 (AMMONIA, BENZENE, CLEAN, CO, H2S, LPG)")
print("=" * 70)

# ══════════════════════════════════════════════════════════════════════════
# PART A: SINGLE-LABEL MODEL (RandomForest, SVM, DT, NB)
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("PART A: SINGLE-LABEL CLASSIFICATION")
print("=" * 70)

# Load dataset
single_path = DATA_DIR / 'collected' / 'lab_readings.csv'
if single_path.exists():
    df_single = pd.read_csv(single_path)
else:
    # Fallback to multilabel dataset, filter single-gas rows only
    df_single = pd.read_csv(DATA_DIR / 'collected' / 'lab_readings_multilabel.csv')
    df_single = df_single[~df_single[TARGET_COL].str.contains(r'\+', regex=True)]

print(f"[OK] Loaded single-label data: {len(df_single)} rows")

# Filter out MERCURY rows
df_single = df_single[df_single[TARGET_COL] != 'MERCURY']
print(f"[OK] After removing MERCURY: {len(df_single)} rows")

# Drop mq303_ppm column if it exists
if 'mq303_ppm' in df_single.columns:
    df_single = df_single.drop(columns=['mq303_ppm'])

# Select features + target, clean
df_single = df_single[FEATURE_NAMES + [TARGET_COL]].dropna()
df_single.drop_duplicates(inplace=True)
print(f"[OK] After clean: {len(df_single)} rows")
print(f"     Classes: {df_single[TARGET_COL].value_counts().to_dict()}")

# Encode labels
le = LabelEncoder()
y = le.fit_transform(df_single[TARGET_COL])
X = df_single[FEATURE_NAMES].values
print(f"[OK] LabelEncoder classes: {list(le.classes_)}")

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y)

# Scale features
scaler = MinMaxScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)

print(f"[OK] MinMaxScaler fitted on {X_train_s.shape[1]} features")
print(f"     Train: {X_train_s.shape} | Test: {X_test_s.shape}")

# Train 4 models
MODELS = {
    'Random Forest': RandomForestClassifier(n_estimators=200, class_weight='balanced', random_state=42, n_jobs=-1),
    'Decision Tree':  DecisionTreeClassifier(max_depth=12, class_weight='balanced', random_state=42),
    'SVM':           SVC(kernel='rbf', class_weight='balanced', random_state=42, probability=True),
    'Naive Bayes':   GaussianNB(),
}

single_results = {}
print("\n--- Training Single-Label Models ---")
for name, model in MODELS.items():
    t0 = time.perf_counter()
    model.fit(X_train_s, y_train)
    t1 = time.perf_counter()
    
    y_pred = model.predict(X_test_s)
    acc  = accuracy_score(y_test, y_pred)
    f1_w = f1_score(y_test, y_pred, average='weighted', zero_division=0)
    prec = precision_score(y_test, y_pred, average='weighted', zero_division=0)
    rec  = recall_score(y_test, y_pred, average='weighted', zero_division=0)
    
    # Cross-validation
    cv_scores = cross_val_score(model, X_train_s, y_train, cv=StratifiedKFold(5), scoring='accuracy')
    
    single_results[name] = {
        'model': model,
        'accuracy': acc,
        'f1_weighted': f1_w,
        'precision': prec,
        'recall': rec,
        'cv_mean': cv_scores.mean(),
        'cv_std': cv_scores.std(),
        'train_time': t1 - t0,
        'y_pred': y_pred,
    }
    
    print(f"  {name}: Acc={acc*100:.2f}%, F1={f1_w*100:.2f}%, CV={cv_scores.mean()*100:.2f}% (+/-{cv_scores.std()*100:.2f})")

# Best single-label model
best_single_name = max(single_results, key=lambda k: single_results[k]['f1_weighted'])
best_single = single_results[best_single_name]
print(f"\n[BEST] {best_single_name}: F1={best_single['f1_weighted']*100:.2f}%")

# Save all single-label models
MODEL_FILES = {
    'Random Forest': 'random_forest_v1.pkl',
    'Decision Tree': 'decision_tree_v1.pkl',
    'SVM':           'svm_v1.pkl',
    'Naive Bayes':   'naive_bayes_v1.pkl',
}
for mname, fname in MODEL_FILES.items():
    joblib.dump(single_results[mname]['model'], MODEL_DIR / fname)

# Save scaler, label encoder, and best model to backend
joblib.dump(scaler, MODEL_DIR / 'scaler.pkl')
joblib.dump(le, MODEL_DIR / 'label_encoder.pkl')

shutil.copy2(MODEL_DIR / 'random_forest_v1.pkl', BACKEND_DIR / 'random_forest_v1.pkl')
shutil.copy2(MODEL_DIR / 'scaler.pkl',           BACKEND_DIR / 'scaler.pkl')
shutil.copy2(MODEL_DIR / 'label_encoder.pkl',     BACKEND_DIR / 'label_encoder.pkl')

print(f"[OK] Saved single-label models + scaler + label_encoder")

# Print classification report for best model
print(f"\n--- Classification Report ({best_single_name}) ---")
print(classification_report(y_test, best_single['y_pred'], target_names=le.classes_))


# ══════════════════════════════════════════════════════════════════════════
# PART B: MULTI-LABEL MODEL
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("PART B: MULTI-LABEL CLASSIFICATION")
print("=" * 70)

# Load multilabel dataset
multi_path = DATA_DIR / 'collected' / 'lab_readings_multilabel.csv'
df_multi = pd.read_csv(multi_path)
print(f"[OK] Loaded multi-label data: {len(df_multi)} rows")

# Remove rows containing MERCURY in gas_class
df_multi = df_multi[~df_multi[TARGET_COL].str.contains('MERCURY', na=False)]
print(f"[OK] After removing MERCURY rows: {len(df_multi)} rows")

# Drop mq303_ppm column
if 'mq303_ppm' in df_multi.columns:
    df_multi = df_multi.drop(columns=['mq303_ppm'])

# Select features + target, clean
df_multi = df_multi[FEATURE_NAMES + [TARGET_COL]].dropna()
df_multi.drop_duplicates(inplace=True)
print(f"[OK] After clean: {len(df_multi)} rows")
print(f"     Classes remaining:")
for cls, cnt in df_multi[TARGET_COL].value_counts().items():
    kind = "MIX" if '+' in str(cls) else "GAS"
    print(f"       [{kind}] {cls:<22}: {cnt}")

# Parse multi-labels
def parse_labels(label_str):
    return [g.strip() for g in str(label_str).split('+') if g.strip()]

df_multi['label_list'] = df_multi[TARGET_COL].apply(parse_labels)

# Binarize labels
mlb = MultiLabelBinarizer(classes=GAS_LABELS)
Y   = mlb.fit_transform(df_multi['label_list'])
X   = df_multi[FEATURE_NAMES].values

print(f"\n[OK] MultiLabelBinarizer fitted")
print(f"     Labels: {mlb.classes_.tolist()}")
print(f"     Y shape: {Y.shape}")

# Train/test split
X_train_m, X_test_m, Y_train_m, Y_test_m = train_test_split(
    X, Y, test_size=0.2, random_state=42)

# Use SAME scaler from single-label (already fitted)
X_train_ms = scaler.transform(X_train_m)
X_test_ms  = scaler.transform(X_test_m)

# Train multi-label model
print("\n--- Training Multi-Label Model ---")
ml_model = MultiOutputClassifier(
    RandomForestClassifier(
        n_estimators=200, class_weight='balanced',
        random_state=42, n_jobs=-1),
    n_jobs=-1
)

t0 = time.perf_counter()
ml_model.fit(X_train_ms, Y_train_m)
t1 = time.perf_counter()

Y_pred_m = ml_model.predict(X_test_ms)

# Multi-label metrics
hl   = hamming_loss(Y_test_m, Y_pred_m)
jacc = jaccard_score(Y_test_m, Y_pred_m, average='samples', zero_division=0)
f1_w = f1_score(Y_test_m, Y_pred_m, average='weighted', zero_division=0)
exact = accuracy_score(Y_test_m, Y_pred_m)

print(f"  MultiLabel RF (MultiOutput)")
print(f"    Hamming Loss:   {hl:.4f}")
print(f"    Jaccard Score:  {jacc*100:.2f}%")
print(f"    F1 Weighted:    {f1_w*100:.2f}%")
print(f"    Exact Match:    {exact*100:.2f}%")
print(f"    Train time:     {t1-t0:.1f}s")

# Save multi-label model and binarizer
joblib.dump(ml_model, MODEL_DIR / 'multilabel_rf_v1.pkl')
joblib.dump(mlb,      MODEL_DIR / 'multilabel_binarizer.pkl')

shutil.copy2(MODEL_DIR / 'multilabel_rf_v1.pkl',    BACKEND_DIR / 'multilabel_rf_v1.pkl')
shutil.copy2(MODEL_DIR / 'multilabel_binarizer.pkl', BACKEND_DIR / 'multilabel_binarizer.pkl')

print(f"[OK] Saved multi-label model + binarizer")

# Per-label F1
print(f"\n  Per-label F1:")
per_label_f1 = f1_score(Y_test_m, Y_pred_m, average=None, zero_division=0)
for label, score in zip(GAS_LABELS, per_label_f1):
    bar = '#' * int(score * 20)
    print(f"    {label:<12} {score*100:>6.2f}%  {bar}")


# ══════════════════════════════════════════════════════════════════════════
# PART C: MODEL CARD
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SAVING MODEL CARD")
print("=" * 70)

# Build comparison table for single-label models
comparison = []
for name, r in single_results.items():
    comparison.append({
        'model': name,
        'accuracy_pct': round(r['accuracy'] * 100, 2),
        'f1_weighted_pct': round(r['f1_weighted'] * 100, 2),
        'precision_pct': round(r['precision'] * 100, 2),
        'recall_pct': round(r['recall'] * 100, 2),
        'cv_mean_pct': round(r['cv_mean'] * 100, 2),
        'cv_std_pct': round(r['cv_std'] * 100, 2),
    })

# Confusion matrix for best model
cm = confusion_matrix(y_test, best_single['y_pred'])

model_card = {
    'model_name': 'EWaste Toxic Gas Detection System — ML Pipeline',
    'version': 'v2.0_no_mercury',
    'description': 'Gas classification without MQ-303 sensor (Mercury unavailable in Sri Lanka)',
    'features': FEATURE_NAMES,
    'feature_count': len(FEATURE_NAMES),
    'gas_classes': GAS_LABELS,
    'class_count': len(GAS_LABELS),
    'single_label': {
        'best_model': best_single_name,
        'algorithm': 'RandomForestClassifier(n_estimators=200, class_weight=balanced)',
        'accuracy_pct': round(best_single['accuracy'] * 100, 2),
        'f1_weighted_pct': round(best_single['f1_weighted'] * 100, 2),
        'precision_pct': round(best_single['precision'] * 100, 2),
        'recall_pct': round(best_single['recall'] * 100, 2),
        'cv_mean_pct': round(best_single['cv_mean'] * 100, 2),
        'cv_std_pct': round(best_single['cv_std'] * 100, 2),
        'confusion_matrix': cm.tolist(),
        'comparison': comparison,
    },
    'multi_label': {
        'algorithm': 'MultiOutputClassifier(RandomForestClassifier(n_estimators=200))',
        'hamming_loss': round(hl, 4),
        'jaccard_score_pct': round(jacc * 100, 2),
        'f1_weighted_pct': round(f1_w * 100, 2),
        'exact_match_pct': round(exact * 100, 2),
        'per_label_f1': {label: round(score * 100, 2) for label, score in zip(GAS_LABELS, per_label_f1)},
        'supported_mixtures': ['CO+H2S', 'CO+BENZENE', 'H2S+BENZENE', 'AMMONIA+CO', 'AMMONIA+H2S'],
    },
    'artifacts': {
        'single_label_model': 'random_forest_v1.pkl',
        'multi_label_model': 'multilabel_rf_v1.pkl',
        'scaler': 'scaler.pkl',
        'label_encoder': 'label_encoder.pkl',
        'multilabel_binarizer': 'multilabel_binarizer.pkl',
    }
}

card_path = BACKEND_DIR / 'model_card.json'
with open(card_path, 'w') as f:
    json.dump(model_card, f, indent=2)
shutil.copy2(card_path, MODEL_DIR / 'model_card.json')

print(f"[OK] model_card.json saved")

# ── FINAL SUMMARY ─────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("RETRAINING COMPLETE!")
print("=" * 70)
print(f"  Features:          {len(FEATURE_NAMES)} (no MQ-303)")
print(f"  Gas Classes:       {len(GAS_LABELS)} (no MERCURY)")
print(f"  Best Single-Label: {best_single_name} — Acc={best_single['accuracy']*100:.2f}%, F1={best_single['f1_weighted']*100:.2f}%")
print(f"  Multi-Label RF:    Jaccard={jacc*100:.2f}%, Exact Match={exact*100:.2f}%")
print()
print("  Files exported to backend/ml_models/:")
for f in sorted(BACKEND_DIR.glob('*.pkl')) + sorted(BACKEND_DIR.glob('*.json')):
    sz = f.stat().st_size
    unit = 'KB' if sz < 1024*1024 else 'MB'
    val = sz/1024 if sz < 1024*1024 else sz/(1024*1024)
    print(f"    {f.name:<30} ({val:.1f} {unit})")
