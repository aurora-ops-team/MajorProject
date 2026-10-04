"""
satellite_routes.py

Dashboard, per-satellite telemetry/history, and anomaly-detection
endpoints. All data comes from services.simulation_service's live
in-memory state (backend-controlled 30-second simulation) plus
services.history_service for past samples.
"""

from flask import Blueprint, jsonify, request

import config
from services.simulation_service import simulation
from services import history_service, alert_service

satellite_bp = Blueprint("satellite_routes", __name__)


def _satellite_summary(sat_id):
    state = simulation.get_satellite_state(sat_id)
    pred = state["prediction"]
    return {
        "id": sat_id,
        "telemetry": state["telemetry"],
        "health_prediction": pred.get("health_prediction"),
        "health_confidence": pred.get("health_confidence"),
        "anomaly_status": pred.get("anomaly_status"),
        "anomaly_score": pred.get("anomaly_score_display"),
        "priority": pred.get("priority"),
        "condition": pred.get("condition"),
        "last_updated": state["last_updated"],
        "current_row": state["current_row"],
    }


@satellite_bp.route("/api/dashboard")
def dashboard():
    sats = [_satellite_summary(sat_id) for sat_id in config.SATELLITE_CSV]
    fleet = {
        "total_satellites": len(sats),
        "healthy": sum(1 for s in sats if s["priority"] == "NORMAL"),
        "warning": sum(1 for s in sats if s["priority"] in ("LOW", "MEDIUM")),
        "critical": sum(1 for s in sats if s["priority"] in ("HIGH", "CRITICAL")),
    }
    active_alerts = [a for a in alert_service.list_alerts() if a["status"] != "RESOLVED"]
    return jsonify({
        "last_updated": max((s["last_updated"] for s in sats if s["last_updated"]), default=None),
        "fleet": fleet,
        "satellites": sats,
        "active_alerts": len(active_alerts),
        "telemetry_interval_seconds": config.TELEMETRY_INTERVAL_SECONDS,
    })


@satellite_bp.route("/api/satellites")
def list_satellites():
    return jsonify({"satellites": [_satellite_summary(sat_id) for sat_id in config.SATELLITE_CSV]})


@satellite_bp.route("/api/satellite/<satellite_id>")
def satellite_detail(satellite_id):
    if satellite_id not in config.SATELLITE_CSV:
        return jsonify({"error": "unknown satellite"}), 404
    return jsonify(_satellite_summary(satellite_id))


@satellite_bp.route("/api/satellite/<satellite_id>/telemetry")
def satellite_telemetry(satellite_id):
    if satellite_id not in config.SATELLITE_CSV:
        return jsonify({"error": "unknown satellite"}), 404
    state = simulation.get_satellite_state(satellite_id)
    telemetry = state["telemetry"]
    annotated = {}
    for feat, value in telemetry.items():
        r = config.FEATURE_RANGES.get(feat)
        if not r:
            annotated[feat] = {"value": value}
            continue
        if not r.get("is_risk_factor", True):
            ok = True
        elif feat == "thermal_control_status":
            ok = int(value) == 1
        else:
            ok = r["min"] <= value <= r["max"]
        annotated[feat] = {"value": value, "unit": r["unit"], "status": "NORMAL" if ok else "ABNORMAL"}
    return jsonify({"id": satellite_id, "telemetry": annotated, "last_updated": state["last_updated"]})


@satellite_bp.route("/api/satellite/<satellite_id>/history")
def satellite_history(satellite_id):
    if satellite_id not in config.SATELLITE_CSV:
        return jsonify({"error": "unknown satellite"}), 404
    limit = request.args.get("limit", default=100, type=int)
    return jsonify({"id": satellite_id, "history": history_service.get_history(satellite_id, limit)})


# ---------------------------------------------------------------------
# Anomaly Detection Center
# ---------------------------------------------------------------------
@satellite_bp.route("/api/anomalies")
def anomalies_summary():
    result = []
    for sat_id in config.SATELLITE_CSV:
        summary = _satellite_summary(sat_id)
        hist = history_service.get_history(sat_id, limit=config.HISTORY_MAX_LENGTH)
        anomaly_count = sum(1 for h in hist if h["prediction"].get("anomaly_status") == "Anomaly")
        result.append({
            "id": sat_id,
            "health_prediction": summary["health_prediction"],
            "anomaly_status": summary["anomaly_status"],
            "anomaly_score": summary["anomaly_score"],
            "priority": summary["priority"],
            "anomaly_count": anomaly_count,
            "last_updated": summary["last_updated"],
        })
    return jsonify({"model": "Isolation Forest", "satellites": result})


@satellite_bp.route("/api/anomalies/<satellite_id>")
def anomalies_detail(satellite_id):
    if satellite_id not in config.SATELLITE_CSV:
        return jsonify({"error": "unknown satellite"}), 404
    state = simulation.get_satellite_state(satellite_id)
    hist = history_service.get_history(satellite_id, limit=config.HISTORY_MAX_LENGTH)
    events = [
        {
            "timestamp": h["timestamp"],
            "row": h["row"],
            "anomaly_score": h["prediction"].get("anomaly_score_display"),
            "health_prediction": h["prediction"].get("health_prediction"),
            "priority": h["prediction"].get("priority"),
        }
        for h in hist if h["prediction"].get("anomaly_status") == "Anomaly"
    ]
    comparison = alert_service.comparison_table(state["telemetry"]) if state["telemetry"] else []
    return jsonify({
        "id": satellite_id,
        "current": _satellite_summary(satellite_id),
        "events": list(reversed(events))[:50],
        "comparison_table": comparison,
        "model": "Isolation Forest",
    })


@satellite_bp.route("/api/anomalies/<satellite_id>/history")
def anomalies_parameter_history(satellite_id):
    if satellite_id not in config.SATELLITE_CSV:
        return jsonify({"error": "unknown satellite"}), 404
    parameter = request.args.get("parameter", default="battery_voltage")
    limit = request.args.get("limit", default=100, type=int)
    if parameter not in config.FEATURE_ORDER:
        return jsonify({"error": "unknown parameter"}), 400
    return jsonify({
        "id": satellite_id,
        "parameter": parameter,
        "history": history_service.get_parameter_history(satellite_id, parameter, limit),
    })
