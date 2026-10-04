"""
Central configuration for the AI-Based Autonomous Satellite Operation
Assistant backend.

Every path here is resolved relative to this file so the backend can be
started from any working directory (`python app.py` from inside `backend/`
or `python backend/app.py` from the project root both work).
"""

import os

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# ---------------------------------------------------------------------
# Data sources
# ---------------------------------------------------------------------
DATA_DIR = os.path.join(BASE_DIR, "data")
SATELLITE_CSV = {
    "SAT-01": os.path.join(DATA_DIR, "satellite_1_telemetry.csv"),
    "SAT-02": os.path.join(DATA_DIR, "satellite_2_telemetry.csv"),
}

# ---------------------------------------------------------------------
# Trained ML artifacts (copied from step2/artifacts and ModelTraining/artifacts)
# ---------------------------------------------------------------------
ARTIFACTS_DIR = os.path.join(BASE_DIR, "model_artifacts")
PREPROCESSOR_PATH = os.path.join(ARTIFACTS_DIR, "preprocessor.joblib")
RF_MODEL_PATH = os.path.join(ARTIFACTS_DIR, "model_rf.joblib")
ISOLATION_FOREST_MODEL_PATH = os.path.join(ARTIFACTS_DIR, "model_isolation_forest.joblib")

# All 6 trained models kept for the Model Performance page. Only Random
# Forest + Isolation Forest are actually used for live inference.
MODEL_ARTIFACT_PATHS = {
    "Random Forest": os.path.join(ARTIFACTS_DIR, "model_rf.joblib"),
    "XGBoost": os.path.join(ARTIFACTS_DIR, "model_xgboost.joblib"),
    "SVM": os.path.join(ARTIFACTS_DIR, "model_svm.joblib"),
    "Isolation Forest": os.path.join(ARTIFACTS_DIR, "model_isolation_forest.joblib"),
    "One-Class SVM": os.path.join(ARTIFACTS_DIR, "model_oneclass_svm.joblib"),
    "Autoencoder": os.path.join(ARTIFACTS_DIR, "model_autoencoder.joblib"),
}

REPORTS_DIR = os.path.join(BASE_DIR, "model_reports")
MODEL_REPORT_PATHS = {
    "Random Forest": os.path.join(REPORTS_DIR, "rf_report.txt"),
    "XGBoost": os.path.join(REPORTS_DIR, "xgboost_report.txt"),
    "SVM": os.path.join(REPORTS_DIR, "svm_report.txt"),
    "Isolation Forest": os.path.join(REPORTS_DIR, "isolation_forest_report.txt"),
    "One-Class SVM": os.path.join(REPORTS_DIR, "oneclass_svm_report.txt"),
    "Autoencoder": os.path.join(REPORTS_DIR, "autoencoder_report.txt"),
}

PLOTS_DIR = os.path.join(BASE_DIR, "model_plots")

# ---------------------------------------------------------------------
# The exact 7 telemetry features, in the order the preprocessor/models
# were trained on. Never reorder this list.
# ---------------------------------------------------------------------
FEATURE_ORDER = [
    "time_since_launch",
    "orbital_altitude",
    "battery_voltage",
    "solar_panel_temperature",
    "attitude_control_error",
    "data_transmission_rate",
    "thermal_control_status",
]

# Nominal operating envelopes used for highlighting / the anomaly
# comparison table / recommended-action rules.
#
# IMPORTANT: these are NOT arbitrary UI decoration -- they are the exact
# risk-factor cut points used by dataset_generation/regenerate_dataset.py
# to construct the true satellite_health label in the first place (see
# dataset_generation/dataset_regeneration_report.txt, section 2):
#   battery_voltage        < 22.02              -> low_battery risk
#   solar_panel_temperature < -40.11 or > 39.89  -> extreme_temperature risk
#   attitude_control_error  > 3.99               -> high_attitude_error risk
#   data_transmission_rate  < 28.14              -> low_transmission risk
#   thermal_control_status  == 0                 -> thermal_failure risk
#
# orbital_altitude was validated as NOT predictive of health at all
# (standardized mean gap of 0.0045 between classes, lowest Random Forest
# feature importance of all 7 features) -- it is kept here purely as an
# informational telemetry field with an envelope wide enough to span the
# full observed data range, so it is displayed but never mis-flagged as
# an anomaly driver.
FEATURE_RANGES = {
    "battery_voltage": {"label": "Battery Voltage", "unit": "V", "min": 22.02, "max": 30, "subsystem": "Electrical Power"},
    "solar_panel_temperature": {"label": "Solar Panel Temperature", "unit": "°C", "min": -40.11, "max": 39.89, "subsystem": "Thermal Control"},
    "orbital_altitude": {"label": "Orbital Altitude", "unit": "km", "min": 300, "max": 2000, "subsystem": "Orbit / GNC", "is_risk_factor": False},
    "attitude_control_error": {"label": "Attitude Control Error", "unit": "°", "min": 0, "max": 3.99, "subsystem": "Attitude Control"},
    "data_transmission_rate": {"label": "Data Transmission Rate", "unit": "Mbps", "min": 28.14, "max": 100, "subsystem": "Communications"},
    "thermal_control_status": {"label": "Thermal Control Status", "unit": "", "min": 1, "max": 1, "subsystem": "Thermal Control"},
}

# ---------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------
TELEMETRY_INTERVAL_SECONDS = 30
HISTORY_MAX_LENGTH = 500

# ---------------------------------------------------------------------
# Priority / decision engine
# Combines the supervised health prediction with the unsupervised
# anomaly result. See services/decision_service.py for the full logic
# including the confidence-based HIGH escalation.
# ---------------------------------------------------------------------
PRIORITY_LEVELS = ["NORMAL", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
HIGH_CONFIDENCE_THRESHOLD = 0.80  # health_confidence above this escalates MEDIUM -> HIGH

CORS_ORIGINS = "*"
HOST = "0.0.0.0"
PORT = 5000
DEBUG = True

# ---------------------------------------------------------------------
# Chat assistant
# ---------------------------------------------------------------------
CHAT_PROVIDER = os.getenv("AURORA_CHAT_PROVIDER", "fallback").lower()
CHAT_API_URL = os.getenv("AURORA_CHAT_API_URL", "")
CHAT_API_KEY = os.getenv("AURORA_CHAT_API_KEY", "")
CHAT_MODEL = os.getenv("AURORA_CHAT_MODEL", "")
CHAT_TIMEOUT_SECONDS = float(os.getenv("AURORA_CHAT_TIMEOUT_SECONDS", "15"))
CHAT_MAX_MESSAGE_LENGTH = 2000
CHAT_MAX_MESSAGES = 12
