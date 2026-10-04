"""
prediction_service.py

Loads the shared preprocessor + the Random Forest health classifier and
turns one telemetry row into a Healthy / Unhealthy prediction with a
confidence percentage.

satellite_health convention used by the training scripts (see
step2/preprocessing.py and ModelTraining/rf.py): 1 = Healthy, 0 = Unhealthy.
"""

import joblib
import pandas as pd

import config

_preprocessor = joblib.load(config.PREPROCESSOR_PATH)
_rf_model = joblib.load(config.RF_MODEL_PATH)

# Index of the "Healthy" (1) class in predict_proba's output columns
_HEALTHY_CLASS_INDEX = list(_rf_model.classes_).index(1)


def _to_dataframe(telemetry: dict) -> pd.DataFrame:
    row = {feat: telemetry[feat] for feat in config.FEATURE_ORDER}
    return pd.DataFrame([row])[config.FEATURE_ORDER]


def predict_health(telemetry: dict) -> dict:
    """
    Returns:
        {
          "health_prediction": "Healthy" | "Unhealthy",
          "health_confidence": float (0-100, confidence in the predicted class)
        }
    """
    raw = _to_dataframe(telemetry)
    scaled = _preprocessor.transform(raw)
    scaled_df = pd.DataFrame(scaled, columns=_rf_model.feature_names_in_)

    proba = _rf_model.predict_proba(scaled_df)[0]
    healthy_proba = float(proba[_HEALTHY_CLASS_INDEX])
    prediction = "Healthy" if healthy_proba >= 0.5 else "Unhealthy"
    confidence = healthy_proba if prediction == "Healthy" else (1 - healthy_proba)

    return {
        "health_prediction": prediction,
        "health_confidence": round(confidence * 100, 1),
        "healthy_probability": round(healthy_proba * 100, 1),
    }
