"""
system_routes.py

Documentation-style endpoint for the System Information page. Static
project facts live here; live counts are pulled from the simulation
state so the page never drifts from actual behaviour.
"""

from flask import Blueprint, jsonify

import config
from services.simulation_service import simulation
from services import model_service, alert_service

system_bp = Blueprint("system_routes", __name__)


@system_bp.route("/api/system/info")
def system_info():
    states = simulation.get_all_states()
    active_alerts = [a for a in alert_service.list_alerts() if a["status"] != "RESOLVED"]
    any_critical = any(s["prediction"].get("priority") in ("HIGH", "CRITICAL") for s in states.values())

    return jsonify({
        "system_status": "Degraded" if any_critical else "Operational",
        "active_satellites": len(config.SATELLITE_CSV),
        "active_alerts": len(active_alerts),
        "telemetry_interval_seconds": config.TELEMETRY_INTERVAL_SECONDS,
        "feature_order": config.FEATURE_ORDER,
        "feature_ranges": config.FEATURE_RANGES,
        "active_models": {
            "health_prediction": model_service.BEST_HEALTH_MODEL,
            "anomaly_detection": model_service.BEST_ANOMALY_MODEL,
        },
        "trained_models": [m["name"] for m in model_service.list_models()],
        "dataset": {
            "source": "Self-generated / synthetic satellite telemetry (rule-based corrected labels)",
            "satellites": list(config.SATELLITE_CSV.keys()),
            "rows_per_satellite": {sat_id: simulation.row_count(sat_id) for sat_id in config.SATELLITE_CSV},
            "supervised_train_test": "7,200 train / 1,800 test rows (stratified 80/20 split)",
            "anomaly_train_rows": "4,480 healthy-only rows (Isolation Forest / One-Class SVM / Autoencoder)",
            "anomaly_eval_rows": "9,000 rows (full dataset, evaluation only)",
            "feature_count": len(config.FEATURE_ORDER),
        },
        "architecture": [
            "Satellite CSV files (SAT-01, SAT-02)",
            "Simulation Service (advances one row every 30s, backend-controlled)",
            "Feature extraction (7 telemetry features)",
            "Shared preprocessor (median-impute + StandardScaler, fit on training data only)",
            "Random Forest (health prediction) + Isolation Forest (anomaly detection), run in parallel",
            "Decision Engine (rule-based priority: NORMAL / LOW / MEDIUM / HIGH / CRITICAL)",
            "Alert Service + Incident Service (in-memory state, REST API)",
            "Frontend pages poll the REST API every 30 seconds",
        ],
    })
