"""
anomaly_service.py

Loads the shared preprocessor + the Isolation Forest anomaly detector.

Isolation Forest convention (see ModelTraining/isolation_forest.py):
  - model.predict()  -> -1 = anomaly, 1 = normal
  - model.score_samples() -> higher = more normal, so we flip the sign:
    anomaly_score = -score_samples() -> higher = more anomalous.

The raw anomaly score for this dataset sits roughly in the 0.44-0.65
range (empirically, from scoring the full training corpus), so it is
also exposed as a 0-1 "display score" for gauges/badges in the UI.
"""

import joblib
import pandas as pd

import config

_preprocessor = joblib.load(config.PREPROCESSOR_PATH)
_iso_model = joblib.load(config.ISOLATION_FOREST_MODEL_PATH)

# Empirically observed raw-score bounds used only to rescale the score
# into a friendlier 0-1 range for the UI. Does not affect the actual
# Normal/Anomaly classification, which comes straight from the model.
_SCORE_FLOOR = 0.40
_SCORE_CEIL = 0.70


def _to_dataframe(telemetry: dict) -> pd.DataFrame:
    row = {feat: telemetry[feat] for feat in config.FEATURE_ORDER}
    return pd.DataFrame([row])[config.FEATURE_ORDER]


def predict_anomaly(telemetry: dict) -> dict:
    """
    Returns:
        {
          "anomaly_status": "Normal" | "Anomaly",
          "anomaly_score": float (raw isolation-forest score, higher = more anomalous),
          "anomaly_score_display": float (0-1 rescaled score for gauges/badges)
        }
    """
    raw = _to_dataframe(telemetry)
    scaled = _preprocessor.transform(raw)
    scaled_df = pd.DataFrame(scaled, columns=_iso_model.feature_names_in_)

    raw_pred = int(_iso_model.predict(scaled_df)[0])  # -1 or 1
    status = "Anomaly" if raw_pred == -1 else "Normal"

    raw_score = float(-_iso_model.score_samples(scaled_df)[0])
    display_score = (raw_score - _SCORE_FLOOR) / (_SCORE_CEIL - _SCORE_FLOOR)
    display_score = max(0.0, min(1.0, display_score))

    return {
        "anomaly_status": status,
        "anomaly_score": round(raw_score, 4),
        "anomaly_score_display": round(display_score, 3),
    }
