"""
run_pipeline.py
=================
Runs the complete ML pipeline end-to-end using Python scripts.
Equivalent to running all 7 notebooks in order.
Use this for quick verification without Jupyter.

Author: Sanjula Madushanka | Final Year Research Y4S2
"""

import sys
import time
import warnings
import json
import shutil
from pathlib import Path
from collections import Counter

import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use('Agg')   # Non-interactive backend (no GUI)
import matplotlib.pyplot as plt

from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, confusion_matrix, classification_report)
try:
    from imblearn.over_sampling import SMOTE
    HAS_IMBLEARN = True
except ImportError:
    HAS_IMBLEARN = False
    print("[!] imbalanced-learn not installed - SMOTE disabled")

warnings.filterwarnings('ignore')

# ─── Paths ─────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent
DATA_DIR   = ROOT / 'datasets'
MODEL_DIR  = ROOT / 'models'
SAVE_DIR   = ROOT / 'results'
SPLIT_DIR  = DATA_DIR / 'processed' / 'train_test_split'
BACKEND_DIR = ROOT.parent / 'backend' / 'ml_models'

for d in [MODEL_DIR, SAVE_DIR, SPLIT_DIR, SAVE_DIR / 'confusion_matrices', BACKEND_DIR]:
    d.mkdir(parents=True, exist_ok=True)

FEATURE_NAMES = ['mq2_ppm', 'mq7_ppm', 'mq135_ppm', 'mq303_ppm', 'mq136_ppm',
                 'temperature_c', 'humidity_pct']
TARGET_COL    = 'gas_class'

# ─── STEP 1: Generate/Load Dataset ─────────────────────────────────────────
print("=" * 60)
print("STEP 1: LOADING DATASET")
print("=" * 60)

collected_path = DATA_DIR / 'collected' / 'lab_readings.csv'

if collected_path.exists():
    df = pd.read_csv(collected_path)
    print(f"[OK] Loaded existing dataset: {len(df)} rows")
else:
    print("[i]  No collected data found. Generating DEMO dataset...")
    np.random.seed(42)
    n_per_class = 150

    profiles = {
        'CO':      {'mq2': (30, 15),  'mq7': (80, 25),   'mq135': (10, 5),   'mq303': (0.005, 0.002), 'mq136': (0.3,  0.15)},
        'LPG':     {'mq2': (200, 80), 'mq7': (10, 5),    'mq135': (8,  4),   'mq303': (0.004, 0.002), 'mq136': (0.2,  0.1)},
        'BENZENE': {'mq2': (15, 8),   'mq7': (8,  4),    'mq135': (45, 15),  'mq303': (0.006, 0.003), 'mq136': (0.4,  0.2)},
        'AMMONIA': {'mq2': (12, 6),   'mq7': (6,  3),    'mq135': (60, 20),  'mq303': (0.004, 0.002), 'mq136': (0.3,  0.15)},
        'MERCURY': {'mq2': (8,  4),   'mq7': (5,  2.5),  'mq135': (6,  3),   'mq303': (0.05,  0.02),  'mq136': (0.2,  0.1)},
        'H2S':     {'mq2': (10, 5),   'mq7': (7,  3.5),  'mq135': (9,  4.5), 'mq303': (0.005, 0.002), 'mq136': (3.5,  1.2)},
        'CLEAN':   {'mq2': (3,  1.5), 'mq7': (2,  1),    'mq135': (3,  1.5), 'mq303': (0.001, 0.0005),'mq136': (0.1,  0.05)},
    }

    rows = []
    for label, p in profiles.items():
        for _ in range(n_per_class):
            rows.append({
                'mq2_ppm':       max(0, np.random.normal(*p['mq2'])),
                'mq7_ppm':       max(0, np.random.normal(*p['mq7'])),
                'mq135_ppm':     max(0, np.random.normal(*p['mq135'])),
                'mq303_ppm':     max(0, np.random.normal(*p['mq303'])),
                'mq136_ppm':     max(0, np.random.normal(*p['mq136'])),
                'temperature_c': np.random.normal(28, 3),
                'humidity_pct':  float(np.clip(np.random.normal(65, 10), 30, 95)),
                'gas_class':     label
            })

    df = pd.DataFrame(rows)
    collected_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(collected_path, index=False)
    print(f"[OK] Demo dataset created: {len(df)} rows, saved to {collected_path}")

print(f"     Shape: {df.shape}, Classes: {df[TARGET_COL].value_counts().to_dict()}")

# ─── STEP 2: Preprocessing ─────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 2: PREPROCESSING")
print("=" * 60)

df = df[FEATURE_NAMES + [TARGET_COL]].dropna()
df.drop_duplicates(inplace=True)
print(f"[OK] After clean: {len(df)} rows")

le = LabelEncoder()
y = le.fit_transform(df[TARGET_COL])
X = df[FEATURE_NAMES].values
joblib.dump(le, MODEL_DIR / 'label_encoder.pkl')
print(f"[OK] LabelEncoder saved | Classes: {list(le.classes_)}")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y)

scaler = MinMaxScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)
joblib.dump(scaler, MODEL_DIR / 'scaler.pkl')
print(f"[OK] MinMaxScaler saved")
print(f"     Train: {X_train_s.shape} | Test: {X_test_s.shape}")

# SMOTE
if HAS_IMBLEARN:
    class_counts = Counter(y_train)
    ratio = max(class_counts.values()) / max(min(class_counts.values()), 1)
    if ratio > 2.0:
        min_count = min(class_counts.values())
        smote = SMOTE(random_state=42, k_neighbors=min(5, min_count - 1))
        X_train_s, y_train = smote.fit_resample(X_train_s, y_train)
        print(f"[OK] SMOTE applied | New training size: {len(X_train_s)}")

pd.DataFrame(X_train_s, columns=FEATURE_NAMES).to_csv(SPLIT_DIR / 'X_train.csv', index=False)
pd.DataFrame(X_test_s,  columns=FEATURE_NAMES).to_csv(SPLIT_DIR / 'X_test.csv',  index=False)
pd.DataFrame(y_train,    columns=['label']).to_csv(SPLIT_DIR / 'y_train.csv', index=False)
pd.DataFrame(y_test,     columns=['label']).to_csv(SPLIT_DIR / 'y_test.csv',  index=False)
print("[OK] Splits saved to datasets/processed/train_test_split/")

# ─── STEP 3: Train All 4 Models ────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 3: TRAINING MODELS")
print("=" * 60)

MODELS = {
    'Random Forest': RandomForestClassifier(
        n_estimators=200, class_weight='balanced', random_state=42, n_jobs=-1),
    'SVM': SVC(
        kernel='rbf', C=10, gamma='scale', class_weight='balanced',
        probability=True, random_state=42),
    'Decision Tree': DecisionTreeClassifier(
        max_depth=10, class_weight='balanced', random_state=42),
    'Naive Bayes': GaussianNB(),
}

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
results = {}

for name, model in MODELS.items():
    t0 = time.perf_counter()
    cv_scores = cross_val_score(model, X_train_s, y_train, cv=cv,
                                scoring='f1_weighted', n_jobs=-1)
    model.fit(X_train_s, y_train)
    t1 = time.perf_counter()

    y_pred = model.predict(X_test_s)
    acc = accuracy_score(y_test, y_pred)
    f1w = f1_score(y_test, y_pred, average='weighted', zero_division=0)

    results[name] = {
        'model':      model,
        'cv_mean':    cv_scores.mean(),
        'cv_std':     cv_scores.std(),
        'test_acc':   acc,
        'f1_weighted':f1w,
        'y_pred':     y_pred,
        'cm':         confusion_matrix(y_test, y_pred),
        'train_time': t1 - t0,
    }
    print(f"  {name:<20}: CV={cv_scores.mean()*100:.2f}% "
          f"TestAcc={acc*100:.2f}%  F1={f1w*100:.2f}%  ({t1-t0:.1f}s)")

# ─── STEP 4: Save Models ────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 4: SAVING MODELS")
print("=" * 60)

FILE_MAP = {
    'Random Forest': 'random_forest_v1.pkl',
    'SVM':           'svm_v1.pkl',
    'Decision Tree': 'decision_tree_v1.pkl',
    'Naive Bayes':   'naive_bayes_v1.pkl',
}
for name, fname in FILE_MAP.items():
    path = MODEL_DIR / fname
    joblib.dump(results[name]['model'], path)
    print(f"  [OK] {fname} ({path.stat().st_size/1024:.1f} KB)")

# ─── STEP 5: Evaluation & Comparison Table ──────────────────────────────────
print("\n" + "=" * 60)
print("STEP 5: EVALUATION RESULTS")
print("=" * 60)

rows = []
for name, r in results.items():
    rows.append({
        'Model':           name,
        'CV Acc (%)':      round(r['cv_mean'] * 100, 2),
        'Test Acc (%)':    round(r['test_acc'] * 100, 2),
        'F1 Weighted (%)': round(r['f1_weighted'] * 100, 2),
        'Train Time (s)':  round(r['train_time'], 2),
    })

comp_df = pd.DataFrame(rows).sort_values('F1 Weighted (%)', ascending=False).reset_index(drop=True)
comp_df.to_csv(SAVE_DIR / 'model_comparison_table.csv', index=False)

print(comp_df.to_string(index=False))
print(f"\n[OK] Comparison table saved to results/model_comparison_table.csv")

# ─── STEP 6: Plot Confusion Matrix for Best Model ───────────────────────────
print("\n" + "=" * 60)
print("STEP 6: GENERATING FIGURES")
print("=" * 60)

import seaborn as sns
best_name = comp_df.iloc[0]['Model']
cm = results[best_name]['cm']

fig, ax = plt.subplots(figsize=(8, 6))
cm_pct = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis] * 100
sns.heatmap(cm_pct, annot=True, fmt='.1f', cmap='RdYlGn',
            xticklabels=le.classes_, yticklabels=le.classes_,
            ax=ax, vmin=0, vmax=100, linewidths=0.5,
            annot_kws={'size': 11})
ax.set_title(f'{best_name} - Confusion Matrix (%)\nTest Set', fontsize=13, fontweight='bold')
ax.set_xlabel('Predicted Label', fontsize=11)
ax.set_ylabel('True Label', fontsize=11)
ax.tick_params(axis='x', rotation=45)
plt.tight_layout()
plt.savefig(SAVE_DIR / 'confusion_matrices' / 'best_model_confusion.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"[OK] Confusion matrix saved for best model: {best_name}")

# Bar chart comparison
model_names = comp_df['Model'].tolist()
f1_scores   = comp_df['F1 Weighted (%)'].tolist()
fig, ax = plt.subplots(figsize=(9, 5))
colors = ['#ef4444', '#3b82f6', '#f59e0b', '#22c55e']
bars = ax.bar(model_names, f1_scores, color=colors, edgecolor='white')
for bar, v in zip(bars, f1_scores):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
            f'{v:.2f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')
ax.set_ylim(0, 110)
ax.set_ylabel('F1 Weighted (%)', fontsize=11)
ax.set_title('Model Comparison - F1 Weighted Score (Test Set)', fontsize=13, fontweight='bold')
ax.axhline(90, color='gray', linestyle='--', linewidth=1, alpha=0.6)
plt.tight_layout()
plt.savefig(SAVE_DIR / 'model_comparison_chart.png', dpi=150, bbox_inches='tight')
plt.close()
print("[OK] Model comparison chart saved")

# ─── STEP 7: Copy to Backend ────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 7: EXPORTING TO BACKEND")
print("=" * 60)

for artifact in ['random_forest_v1.pkl', 'scaler.pkl', 'label_encoder.pkl']:
    src = MODEL_DIR / artifact
    if src.exists():
        shutil.copy2(src, BACKEND_DIR / artifact)
        print(f"  [OK] Copied {artifact} -> backend/ml_models/")

# Model card
best_model = results[best_name]['model']
model_card = {
    'model_name':    'EWaste Toxic Gas Classifier',
    'model_version': 'rf_v1',
    'algorithm':     'Random Forest',
    'features':      FEATURE_NAMES,
    'classes':       list(le.classes_),
    'performance': {
        'test_accuracy_pct':  round(results[best_name]['test_acc'] * 100, 2),
        'test_f1_weighted':   round(results[best_name]['f1_weighted'] * 100, 2),
        'cv_f1_mean':         round(results[best_name]['cv_mean'] * 100, 2),
    },
    'artifacts': {
        'model':         'random_forest_v1.pkl',
        'scaler':        'scaler.pkl',
        'label_encoder': 'label_encoder.pkl',
    }
}
card_path = MODEL_DIR / 'model_card.json'
with open(card_path, 'w') as f:
    json.dump(model_card, f, indent=2)
shutil.copy2(card_path, BACKEND_DIR / 'model_card.json')
print("  [OK] model_card.json saved and exported")

# ─── FINAL SUMMARY ──────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("ML PIPELINE COMPLETE!")
print("=" * 60)
best = comp_df.iloc[0]
print(f"  Best Model:    {best['Model']}")
print(f"  Test Accuracy: {best['Test Acc (%)']:.2f}%")
print(f"  F1 Weighted:   {best['F1 Weighted (%)']:.2f}%")
print()
print("  Files created:")
for p in sorted(MODEL_DIR.glob('*.pkl')) + sorted(MODEL_DIR.glob('*.json')):
    print(f"    models/{p.name}")
for p in sorted(SAVE_DIR.glob('*.csv')) + sorted(SAVE_DIR.glob('*.png')):
    print(f"    results/{p.name}")
print()
print("Next step: Build the FastAPI backend")
