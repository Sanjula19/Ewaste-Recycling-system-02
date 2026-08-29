"""
ML Service -- E-Waste Toxic Gas Detection System
=================================================
Wraps the trained Random Forest models.
Feature order MUST match what the scaler was trained on:
  [mq2_ppm, mq7_ppm, mq135_ppm, mq136_ppm, temperature_c, humidity_pct]

IMPORTANT: Current models were trained on synthetic/simulated data.
Predictions are indicative only until real labeled experimental data is collected.
"""
import os
import joblib
import logging
from typing import Dict, Any, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Warning attached to every prediction until real-data models exist
MODEL_DATA_WARNING = (
    "Model trained on synthetic literature-based data. "
    "Predictions are indicative only. "
    "Do not use for safety-critical decisions until models are retrained on real labeled sensor data."
)

# Exact feature order -- must match scaler fit order
FEATURE_ORDER = ["mq2_ppm", "mq7_ppm", "mq135_ppm", "mq136_ppm", "temperature_c", "humidity_pct"]


class MLService:
    def __init__(self):
        self._rf_model = None
        self._scaler = None
        self._label_encoder = None
        self._multilabel_rf = None
        self._multilabel_binarizer = None
        self._is_loaded = False
        self._version = "none"

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    @property
    def version(self) -> str:
        return self._version

    def load_models(self):
        """Load models from disk. Called once at app startup."""
        try:
            model_dir = settings.model_dir
            rf_path = os.path.join(model_dir, "random_forest_v1.pkl")
            scaler_path = os.path.join(model_dir, "scaler.pkl")
            le_path = os.path.join(model_dir, "label_encoder.pkl")
            multi_rf_path = os.path.join(model_dir, "multilabel_rf_v1.pkl")
            multi_lb_path = os.path.join(model_dir, "multilabel_binarizer.pkl")

            primary_ok = all(os.path.exists(p) for p in [rf_path, scaler_path, le_path])
            if primary_ok:
                self._rf_model = joblib.load(rf_path)
                self._scaler = joblib.load(scaler_path)
                self._label_encoder = joblib.load(le_path)
                self._is_loaded = True
                self._version = "rf_v1"
                logger.info(f"[ML] Loaded primary models from {model_dir}")
            else:
                logger.warning(f"[ML] Primary models not found in {model_dir}")

            if os.path.exists(multi_rf_path) and os.path.exists(multi_lb_path):
                self._multilabel_rf = joblib.load(multi_rf_path)
                self._multilabel_binarizer = joblib.load(multi_lb_path)
                logger.info("[ML] Loaded multilabel models")
            else:
                logger.warning("[ML] Multilabel models not found")

        except Exception as e:
            logger.error(f"[ML] Error loading models: {e}")
            self._is_loaded = False

    def _build_feature_vector(self, mq2_ppm: float, mq7_ppm: float,
                               mq135_ppm: float, mq136_ppm: float,
                               temperature_c: float, humidity_pct: float) -> list:
        """Build feature vector in the exact order the scaler expects.
        6 features: [mq2_ppm, mq7_ppm, mq135_ppm, mq136_ppm, temperature_c, humidity_pct]
        """
        return [[mq2_ppm, mq7_ppm, mq135_ppm, mq136_ppm, temperature_c, humidity_pct]]

    def classify(
        self,
        mq2_ppm: float,
        mq7_ppm: float,
        mq135_ppm: float,
        mq136_ppm: float,
        temperature_c: float,
        humidity_pct: float,
    ) -> Dict[str, Any]:
        """
        Single-label classification.
        Returns dict with gas_class, confidence, model_version, model_data_warning.
        Returns error dict if model not loaded.
        """
        if not self._is_loaded:
            return {
                "model_loaded": False,
                "error": "No trained model is available.",
                "gas_class": None,
                "confidence": None,
                "model_version": "none",
            }

        try:
            features = self._build_feature_vector(
                mq2_ppm, mq7_ppm, mq135_ppm, mq136_ppm, temperature_c, humidity_pct
            )
            scaled = self._scaler.transform(features)
            pred_encoded = self._rf_model.predict(scaled)[0]
            gas_class = self._label_encoder.inverse_transform([pred_encoded])[0]
            probs = self._rf_model.predict_proba(scaled)[0]
            confidence = float(max(probs))

            return {
                "model_loaded": True,
                "gas_class": str(gas_class),
                "confidence": confidence,
                "model_version": self._version,
                "model_data_warning": MODEL_DATA_WARNING,
            }
        except Exception as e:
            logger.error(f"[ML] classify error: {e}")
            return {
                "model_loaded": False,
                "error": f"Prediction error: {e}",
                "gas_class": None,
                "confidence": None,
                "model_version": self._version,
            }

    def classify_multilabel(
        self,
        mq2_ppm: float,
        mq7_ppm: float,
        mq135_ppm: float,
        mq136_ppm: float,
        temperature_c: float,
        humidity_pct: float,
    ) -> List[str]:
        """
        Multi-label classification — returns list of detected gas labels.
        Returns empty list if multilabel model not loaded.
        """
        if not self._multilabel_rf or not self._multilabel_binarizer or not self._scaler:
            return []

        try:
            features = self._build_feature_vector(
                mq2_ppm, mq7_ppm, mq135_ppm, mq136_ppm, temperature_c, humidity_pct
            )
            scaled = self._scaler.transform(features)
            preds = self._multilabel_rf.predict(scaled)
            detected = self._multilabel_binarizer.inverse_transform(preds)[0]
            return list(detected)
        except Exception as e:
            logger.error(f"[ML] classify_multilabel error: {e}")
            return []


ml_service = MLService()
