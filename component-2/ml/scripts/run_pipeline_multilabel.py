"""
run_pipeline_multilabel.py
===========================
Multi-Label Gas Mixture Classification Pipeline
E-Waste Toxic Gas Detection System

WHAT'S DIFFERENT FROM run_pipeline.py:
  - Uses MultiLabelBinarizer instead of LabelEncoder
  - Uses MultiOutputClassifier(RandomForestClassifier) for multi-label
  - Evaluates using Hamming Loss, Jaccard Score, per-label F1
  - Output: list of detected gases, e.g. ['CO', 'H2S']
  - Saves multilabel_rf_v1.pkl + multilabel_binarizer.pkl

NOVEL CONTRIBUTION:
  Detects COMBINATIONS of toxic gases simultaneously.
  Standard single-label systems cannot do this.
  E.g. Li-ion battery burning on PCB → CO + H2S detected together.

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
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.preprocessing import MinMaxScaler, MultiLabelBinarizer
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier, ClassifierChain
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import (
    hamming_loss, jaccard_score,
    f1_score, accuracy_score,
    classification_report
)

warnings.filterwarnings('ignore')

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent.parent
DATA_DIR    = ROOT / 'datasets'
MODEL_DIR   = ROOT / 'models'
SAVE_DIR    = ROOT / 'results'
SPLIT_DIR   = DATA_DIR / 'processed' / 'train_test_split'
BACKEND_DIR = ROOT.parent / 'backend' / 'ml_models'

for d in [MODEL_DIR, SAVE_DIR, SPLIT_DIR,
          SAVE_DIR / 'confusion_matrices', BACKEND_DIR]:
    d.mkdir(parents=True, exist_ok=True)

FEATURE_NAMES = ['mq2_ppm', 'mq7_ppm', 'mq135_ppm', 'mq303_ppm',
                 'mq136_ppm', 'temperature_c', 'humidity_pct']
TARGET_COL    = 'gas_class'

# All possible gas labels (individual)
GAS_LABELS = ['AMMONIA', 'BENZENE', 'CLEAN', 'CO', 'H2S', 'LPG', 'MERCURY']

# ── STEP 1: Load Multi-Label Dataset ───────────────────────────────────────
print("=" * 60)
print("STEP 1: LOADING MULTI-LABEL DATASET")
print("=" * 60)

# Prefer the mixture dataset if available
multilabel_path = DATA_DIR / 'collected' / 'lab_readings_multilabel.csv'
fallback_path   = DATA_DIR / 'collected' / 'lab_readings.csv'

if multilabel_path.exists():
    df = pd.read_csv(multilabel_path)
    print(f"[OK] Loaded mixture dataset: {len(df)} rows")
elif fallback_path.exists():
    df = pd.read_csv(fallback_path)
    print(f"[OK] Loaded base dataset (no mixtures yet): {len(df)} rows")
    print("     Run generate_mixtures.py first for full multi-label training")
else:
    print("[ERROR] No dataset found. Run merge_datasets.py and generate_mixtures.py first.")
    exit(1)

# ── STEP 2: Parse Multi-Label Target Column ─────────────────────────────────
print("\n" + "=" * 60)
print("STEP 2: MULTI-LABEL PREPROCESSING")
print("=" * 60)

df = df[FEATURE_NAMES + [TARGET_COL]].dropna()
df.drop_duplicates(inplace=True)

# Parse gas_class: "CO+H2S" → ["CO", "H2S"] | "CO" → ["CO"]
def parse_labels(label_str):
    """Split 'CO+H2S' into ['CO', 'H2S'] and 'CO' into ['CO']"""
    return [g.strip() for g in str(label_str).split('+') if g.strip()]

df['label_list'] = df[TARGET_COL].apply(parse_labels)

# Show distribution
print(f"[OK] Total rows: {len(df)}")
print(f"     Single-gas rows: {(~df[TARGET_COL].str.contains('+', regex=False)).sum()}")
print(f"     Mixture rows:    {(df[TARGET_COL].str.contains('+', regex=False)).sum()}")
print()
print("     Class distribution:")
for cls, cnt in df[TARGET_COL].value_counts().items():
    kind = "MIX" if '+' in str(cls) else "GAS"
    print(f"       [{kind}] {cls:<22}: {cnt}")

# ── Binarize labels ─────────────────────────────────────────────────────────
mlb = MultiLabelBinarizer(classes=GAS_LABELS)
Y   = mlb.fit_transform(df['label_list'])
X   = df[FEATURE_NAMES].values

print(f"\n[OK] MultiLabelBinarizer fitted")
print(f"     Labels: {mlb.classes_.tolist()}")
print(f"     Y shape: {Y.shape}  (rows x gas_labels)")

# Save binarizer — backend uses this for decoding predictions
joblib.dump(mlb, MODEL_DIR / 'multilabel_binarizer.pkl')
print(f"[OK] multilabel_binarizer.pkl saved")

# ── Train/Test Split ────────────────────────────────────────────────────────
X_train, X_test, Y_train, Y_test = train_test_split(
    X, Y, test_size=0.2, random_state=42)

# Scale features
scaler = MinMaxScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)
joblib.dump(scaler, MODEL_DIR / 'scaler.pkl')
print(f"[OK] MinMaxScaler saved")
print(f"     Train: {X_train_s.shape} | Test: {X_test_s.shape}")

# ── STEP 3: Train Multi-Label Models ───────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 3: TRAINING MULTI-LABEL MODELS")
print("=" * 60)
print()
print("  Strategy: MultiOutputClassifier trains one binary classifier")
print("  per gas label, then combines predictions.")
print("  This allows detecting multiple gases simultaneously.")
print()

ML_MODELS = {
    'MultiLabel RF (MultiOutput)': MultiOutputClassifier(
        RandomForestClassifier(
            n_estimators=200, class_weight='balanced',
            random_state=42, n_jobs=-1),
        n_jobs=-1
    ),
    'MultiLabel RF (ChainOrder)': ClassifierChain(
        RandomForestClassifier(
            n_estimators=100, class_weight='balanced',
            random_state=42, n_jobs=-1),
        order='random', random_state=42
    ),
    'MultiLabel DT (MultiOutput)': MultiOutputClassifier(
        DecisionTreeClassifier(
            max_depth=12, class_weight='balanced', random_state=42),
        n_jobs=-1
    ),
}

results = {}
for name, model in ML_MODELS.items():
    t0 = time.perf_counter()
    model.fit(X_train_s, Y_train)
    t1 = time.perf_counter()

    Y_pred = model.predict(X_test_s)

    # Multi-label metrics
    hl   = hamming_loss(Y_test, Y_pred)           # lower is better
    jacc = jaccard_score(Y_test, Y_pred, average='samples', zero_division=0)
    f1_m = f1_score(Y_test, Y_pred, average='macro',   zero_division=0)
    f1_w = f1_score(Y_test, Y_pred, average='weighted', zero_division=0)
    # Exact match (subset accuracy)
    exact = accuracy_score(Y_test, Y_pred)

    results[name] = {
        'model':        model,
        'hamming_loss': hl,
        'jaccard':      jacc,
        'f1_macro':     f1_m,
        'f1_weighted':  f1_w,
        'exact_match':  exact,
        'Y_pred':       Y_pred,
        'train_time':   t1 - t0,
    }

    print(f"  {name}")
    print(f"    Hamming Loss:   {hl:.4f}  (lower=better, 0=perfect)")
    print(f"    Jaccard Score:  {jacc*100:.2f}%")
    print(f"    F1 Weighted:    {f1_w*100:.2f}%")
    print(f"    Exact Match:    {exact*100:.2f}%")
    print(f"    Train time:     {t1-t0:.1f}s")
    print()

# ── STEP 4: Select Best Model ───────────────────────────────────────────────
print("=" * 60)
print("STEP 4: BEST MODEL SELECTION")
print("=" * 60)

# Rank by Jaccard Score (best for multi-label)
best_name = max(results, key=lambda k: results[k]['jaccard'])
best      = results[best_name]
print(f"[OK] Best model: {best_name}")
print(f"     Jaccard Score: {best['jaccard']*100:.2f}%")
print(f"     Hamming Loss:  {best['hamming_loss']:.4f}")
print(f"     F1 Weighted:   {best['f1_weighted']*100:.2f}%")

# Save all models
MODEL_FILE_MAP = {
    'MultiLabel RF (MultiOutput)': 'multilabel_rf_multioutput.pkl',
    'MultiLabel RF (ChainOrder)':  'multilabel_rf_chain.pkl',
    'MultiLabel DT (MultiOutput)': 'multilabel_dt_multioutput.pkl',
}
for mname, fname in MODEL_FILE_MAP.items():
    joblib.dump(results[mname]['model'], MODEL_DIR / fname)
    sz = (MODEL_DIR / fname).stat().st_size / 1024
    print(f"  [OK] {fname} ({sz:.1f} KB)")

# Save best as the primary model used by backend
joblib.dump(best['model'], MODEL_DIR / 'multilabel_rf_v1.pkl')
shutil.copy2(MODEL_DIR / 'multilabel_rf_v1.pkl',    BACKEND_DIR / 'multilabel_rf_v1.pkl')
shutil.copy2(MODEL_DIR / 'multilabel_binarizer.pkl', BACKEND_DIR / 'multilabel_binarizer.pkl')
shutil.copy2(MODEL_DIR / 'scaler.pkl',               BACKEND_DIR / 'scaler.pkl')
print(f"\n[OK] Best model exported to backend/ml_models/")

# ── STEP 5: Evaluation Table ────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 5: EVALUATION TABLE")
print("=" * 60)

eval_rows = []
for name, r in results.items():
    eval_rows.append({
        'Model':            name,
        'Hamming Loss':     round(r['hamming_loss'], 4),
        'Jaccard (%)':      round(r['jaccard'] * 100, 2),
        'F1 Weighted (%)':  round(r['f1_weighted'] * 100, 2),
        'Exact Match (%)':  round(r['exact_match'] * 100, 2),
        'Train Time (s)':   round(r['train_time'], 2),
    })

eval_df = pd.DataFrame(eval_rows).sort_values('Jaccard (%)', ascending=False)
eval_df.to_csv(SAVE_DIR / 'multilabel_comparison_table.csv', index=False)
print(eval_df.to_string(index=False))

# Per-label F1 breakdown for best model
print()
print(f"  Per-label F1 (Best: {best_name}):")
print(f"  {'Gas Label':<12} {'F1':>8}")
print("  " + "-" * 22)
per_label_f1 = f1_score(Y_test, best['Y_pred'], average=None, zero_division=0)
for label, score in zip(GAS_LABELS, per_label_f1):
    bar = '#' * int(score * 20)
    print(f"  {label:<12} {score*100:>6.2f}%  {bar}")

# ── STEP 6: Figures ─────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 6: GENERATING FIGURES")
print("=" * 60)

# ── Figure 1: Per-label F1 bar chart ──────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
colors = ['#22c55e' if f >= 0.85 else '#f59e0b' if f >= 0.60 else '#ef4444'
          for f in per_label_f1]
bars = ax.bar(GAS_LABELS, per_label_f1 * 100, color=colors, edgecolor='white')
for bar, v in zip(bars, per_label_f1):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
            f'{v*100:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')
ax.set_ylim(0, 115)
ax.set_ylabel('F1 Score (%)', fontsize=11)
ax.set_title('Per-Label F1 Score — Multi-Label Gas Classifier\n'
             f'Best Model: {best_name}', fontsize=12, fontweight='bold')
ax.axhline(85, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='85% target')
ax.legend(fontsize=9)
plt.tight_layout()
plt.savefig(SAVE_DIR / 'multilabel_per_label_f1.png', dpi=150, bbox_inches='tight')
plt.close()
print("[OK] Per-label F1 chart saved")

# ── Figure 2: Label co-occurrence heatmap ─────────────────────────────────
cooccur = Y_test.T @ Y_test   # label co-occurrence matrix
fig, ax = plt.subplots(figsize=(8, 6))
mask = np.eye(len(GAS_LABELS), dtype=bool)   # mask diagonal
sns.heatmap(cooccur, annot=True, fmt='d', cmap='Blues',
            xticklabels=GAS_LABELS, yticklabels=GAS_LABELS,
            ax=ax, mask=mask, linewidths=0.5)
ax.set_title('Gas Label Co-occurrence Matrix\n(How often two gases appear together)',
             fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig(SAVE_DIR / 'label_cooccurrence_heatmap.png', dpi=150, bbox_inches='tight')
plt.close()
print("[OK] Label co-occurrence heatmap saved")

# ── Figure 3: Model comparison bar chart ──────────────────────────────────
model_names_short = ['RF MultiOutput', 'RF ChainOrder', 'DT MultiOutput']
jacc_scores = [results[n]['jaccard'] * 100 for n in ML_MODELS]
fig, ax = plt.subplots(figsize=(9, 5))
bar_colors = ['#3b82f6', '#8b5cf6', '#f59e0b']
bars = ax.bar(model_names_short, jacc_scores, color=bar_colors, edgecolor='white')
for bar, v in zip(bars, jacc_scores):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
            f'{v:.2f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')
ax.set_ylim(0, 110)
ax.set_ylabel('Jaccard Score (%)', fontsize=11)
ax.set_title('Multi-Label Model Comparison — Jaccard Score\n'
             '(Measures overlap between predicted and true label sets)',
             fontsize=12, fontweight='bold')
ax.axhline(80, color='gray', linestyle='--', linewidth=1, alpha=0.5)
plt.tight_layout()
plt.savefig(SAVE_DIR / 'multilabel_model_comparison.png', dpi=150, bbox_inches='tight')
plt.close()
print("[OK] Multi-label model comparison chart saved")

# ── STEP 7: Save Model Card ─────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 7: SAVING MODEL CARD")
print("=" * 60)

model_card = {
    'model_name':       'EWaste Toxic Gas Multi-Label Classifier',
    'model_version':    'multilabel_rf_v1',
    'classification':   'multi-label',
    'algorithm':        'MultiOutputClassifier(RandomForestClassifier)',
    'novel_feature':    'Detects gas MIXTURES simultaneously (e.g. CO+H2S)',
    'features':         FEATURE_NAMES,
    'gas_labels':       GAS_LABELS,
    'mixture_classes':  [f"{a}+{b}" for a, b, *_ in [
        ('CO','H2S'), ('CO','BENZENE'), ('CO','MERCURY'),
        ('H2S','BENZENE'), ('AMMONIA','CO'),
        ('AMMONIA','H2S'), ('MERCURY','BENZENE')]],
    'performance': {
        'hamming_loss':      round(best['hamming_loss'], 4),
        'jaccard_score_pct': round(best['jaccard'] * 100, 2),
        'f1_weighted_pct':   round(best['f1_weighted'] * 100, 2),
        'exact_match_pct':   round(best['exact_match'] * 100, 2),
    },
    'inference_output_example': {
        'raw_sensor_input': {
            'mq2_ppm': 35.2, 'mq7_ppm': 88.1, 'mq135_ppm': 11.4,
            'mq303_ppm': 0.005, 'mq136_ppm': 3.8,
            'temperature_c': 29.1, 'humidity_pct': 64.0
        },
        'detected_gases':  ['CO', 'H2S'],
        'is_mixture':      True,
        'confidence_per_label': {
            'CO': 0.87, 'H2S': 0.76, 'BENZENE': 0.02,
            'AMMONIA': 0.01, 'LPG': 0.0, 'MERCURY': 0.03, 'CLEAN': 0.0
        }
    },
    'artifacts': {
        'model':              'multilabel_rf_v1.pkl',
        'binarizer':          'multilabel_binarizer.pkl',
        'scaler':             'scaler.pkl',
    }
}

card_path = MODEL_DIR / 'model_card.json'
with open(card_path, 'w') as f:
    json.dump(model_card, f, indent=2)
shutil.copy2(card_path, BACKEND_DIR / 'model_card.json')
print("[OK] model_card.json updated with multi-label metadata")

# ── FINAL SUMMARY ─────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("MULTI-LABEL PIPELINE COMPLETE!")
print("=" * 60)
print(f"  Best Model:    {best_name}")
print(f"  Jaccard Score: {best['jaccard']*100:.2f}%")
print(f"  Hamming Loss:  {best['hamming_loss']:.4f}")
print(f"  F1 Weighted:   {best['f1_weighted']*100:.2f}%")
print()
print("  What this means:")
print("    Given 7 sensor readings, the model can now output")
print("    e.g. ['CO', 'H2S'] when both gases are present.")
print("    Standard systems can only output one gas at a time.")
print()
print("  Files exported to backend/ml_models/:")
print("    multilabel_rf_v1.pkl")
print("    multilabel_binarizer.pkl")
print("    scaler.pkl")
print("    model_card.json")
print()
print("  Figures saved to results/:")
for p in sorted(SAVE_DIR.glob('multilabel*.png')) + \
         sorted(SAVE_DIR.glob('label_co*.png')):
    print(f"    {p.name}")
print()
print("Next step: Build the FastAPI backend (Step 3)")
