import pickle
import os
import numpy as np

BASE_DIR            = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH          = os.path.join(BASE_DIR, "model.pkl")
ENCODER_PATH        = os.path.join(BASE_DIR, "encoders.pkl")
SCALER_PATH         = os.path.join(BASE_DIR, "scaler.pkl")
TARGET_ENCODER_PATH = os.path.join(BASE_DIR, "target_encoder.pkl")

decision_tree_model = None
label_encoders      = None
feature_scaler      = None
target_encoder      = None


def load_all_models():
    global decision_tree_model, label_encoders, feature_scaler, target_encoder

    with open(MODEL_PATH, "rb") as f:
        decision_tree_model = pickle.load(f)

    with open(ENCODER_PATH, "rb") as f:
        label_encoders = pickle.load(f)

    with open(SCALER_PATH, "rb") as f:
        feature_scaler = pickle.load(f)

    with open(TARGET_ENCODER_PATH, "rb") as f:
        target_encoder = pickle.load(f)

    print(f"  model.pkl loaded - Classes: {list(decision_tree_model.classes_)}")
    print(f"  encoders.pkl loaded")
    print(f"  scaler.pkl loaded")
    print(f"  target_encoder.pkl loaded - Labels: {list(target_encoder.classes_)}")


def get_model():
    return decision_tree_model

def get_encoders():
    return label_encoders

def get_scaler():
    return feature_scaler

def get_target_encoder():
    return target_encoder


def predict_method(material_name, waste_type, weight_kg,
                   moisture_condition, moisture_pct, toxicity_level):

    model    = get_model()
    encoders = get_encoders()
    scaler   = get_scaler()
    t_enc    = get_target_encoder()

    mat_enc  = encoders["material"].transform([material_name])[0]
    mois_enc = encoders["moisture"].transform([moisture_condition])[0]
    cat_enc  = encoders["category"].transform([waste_type])[0]
    tox_enc  = encoders["toxicity"].transform([toxicity_level])[0]

    # numpy array — NOT DataFrame. Avoids sklearn version feature-name errors.
    features_array = np.array([[
        mat_enc, cat_enc, weight_kg, mois_enc, moisture_pct, tox_enc
    ]], dtype=float)

    features_scaled = scaler.transform(features_array)

    # model.predict() returns an encoded number (0 or 1) — decode it back
    # to the actual label string ("Mechanical" / "Thermal").
    predicted_encoded = model.predict(features_scaled)[0]
    method = t_enc.inverse_transform([predicted_encoded])[0]

    return str(method)