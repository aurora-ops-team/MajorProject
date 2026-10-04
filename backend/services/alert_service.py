"""
alert_service.py

Turns a (telemetry, prediction) pair into human-readable, prioritised
alerts, and keeps the alert queue's operator-facing lifecycle
(OPEN -> ACKNOWLEDGED -> INVESTIGATING -> RESOLVED) entirely in backend
state, per the integration plan ("do not keep these statuses only in
browser JavaScript").

Design choice: rather than appending a brand-new alert row every 30
seconds (which would flood the queue with duplicates for a condition
that hasn't changed), each satellite has at most one *active* alert at
a time. While the satellite's priority stays non-NORMAL, that alert's
live fields (score, confidence, deviation, timestamp) are refreshed in
place. If the satellite recovers to NORMAL, the active alert is
auto-resolved. Every open/resolve/refresh is still visible through the
API and the operator's own acknowledge/investigate/resolve actions are
always preserved.
"""

import threading
from datetime import datetime, timezone

import config
from services import incident_service

_lock = threading.RLock()  # reentrant: _new_alert_id() is called while evaluate() already holds this lock
_alerts = {}          # alert_id -> alert dict
_active_by_sat = {}    # satellite_id -> alert_id of the current active alert
_next_id = 1

RECOMMENDED_ACTIONS = {
    "battery_voltage": "Check battery state and solar charging",
    "solar_panel_temperature": "Inspect thermal control condition and radiator performance",
    "orbital_altitude": "Verify orbital maneuver history and station-keeping",
    "attitude_control_error": "Investigate attitude control subsystem",
    "data_transmission_rate": "Inspect communication subsystem",
    "thermal_control_status": "Inspect thermal control loop and heater duty cycle",
}

ISSUE_TEXT = {
    "battery_voltage": "Battery voltage abnormality",
    "solar_panel_temperature": "Solar panel over/under-temperature",
    "orbital_altitude": "Orbital altitude deviation",
    "attitude_control_error": "Attitude control pointing error",
    "data_transmission_rate": "Downlink throughput degradation",
    "thermal_control_status": "Thermal control system degraded",
}


def _deviation_pct(feature, value):
    r = config.FEATURE_RANGES[feature]
    if not r.get("is_risk_factor", True):
        return 0.0  # informational field only (e.g. orbital_altitude) -- never drives an alert
    if feature == "thermal_control_status":
        return 0.0 if int(value) == 1 else 100.0
    lo, hi = r["min"], r["max"]
    if value < lo:
        return (value - lo) / lo * 100 if lo else 0.0
    if value > hi:
        return (value - hi) / hi * 100 if hi else 0.0
    return 0.0


def _format_value(feature, value):
    r = config.FEATURE_RANGES[feature]
    if feature == "thermal_control_status":
        return "NOMINAL" if int(value) == 1 else "DEGRADED"
    return f"{value:.2f} {r['unit']}".strip()


def _expected_range_text(feature):
    r = config.FEATURE_RANGES[feature]
    if feature == "thermal_control_status":
        return "NOMINAL"
    if feature == "attitude_control_error":
        return f"< {r['max']}{r['unit']}"
    return f"{r['min']} – {r['max']} {r['unit']}".strip()


def worst_parameter(telemetry: dict):
    """Returns (feature, deviation_pct) for the feature furthest outside its envelope."""
    worst_feat, worst_dev = None, 0.0
    for feat in config.FEATURE_RANGES:
        dev = _deviation_pct(feat, telemetry[feat])
        if abs(dev) > abs(worst_dev):
            worst_feat, worst_dev = feat, dev
    return worst_feat, worst_dev


def comparison_table(telemetry: dict):
    """Full parameter-by-parameter comparison used by the Anomalies page."""
    rows = []
    for feat, r in config.FEATURE_RANGES.items():
        dev = _deviation_pct(feat, telemetry[feat])
        if dev == 0:
            status = "NORMAL"
        elif abs(dev) < 10:
            status = "MEDIUM"
        else:
            status = "HIGH" if abs(dev) < 30 else "CRITICAL"
        rows.append({
            "parameter": r["label"],
            "feature": feat,
            "current": _format_value(feat, telemetry[feat]),
            "expected": _expected_range_text(feat),
            "deviation": f"{dev:+.1f}%" if feat != "thermal_control_status" else ("—" if dev == 0 else "—"),
            "status": status,
        })
    return rows


def _new_alert_id():
    global _next_id
    with _lock:
        alert_id = f"ALT-{_next_id:04d}"
        _next_id += 1
    return alert_id


def evaluate(sat_id, telemetry, prediction, timestamp):
    priority = prediction["priority"]

    if priority == "NORMAL":
        with _lock:
            active_id = _active_by_sat.get(sat_id)
            if active_id and _alerts[active_id]["status"] != "RESOLVED":
                _alerts[active_id]["status"] = "RESOLVED"
                _alerts[active_id]["resolved_at"] = timestamp
                _alerts[active_id]["auto_resolved"] = True
                incident_service.sync_from_alert(_alerts[active_id])
                _active_by_sat[sat_id] = None
        return

    feat, dev = worst_parameter(telemetry)
    subsystem = config.FEATURE_RANGES[feat]["subsystem"] if feat else "General"
    issue = ISSUE_TEXT.get(feat, "Telemetry deviation detected")
    rationale = _build_rationale(priority, prediction, feat, dev)

    with _lock:
        active_id = _active_by_sat.get(sat_id)
        if active_id and _alerts[active_id]["status"] != "RESOLVED":
            alert = _alerts[active_id]
            alert["priority"] = priority
            alert["subsystem"] = subsystem
            alert["issue"] = issue
            alert["parameter"] = config.FEATURE_RANGES[feat]["label"] if feat else "—"
            alert["current"] = _format_value(feat, telemetry[feat]) if feat else "—"
            alert["expected"] = _expected_range_text(feat) if feat else "—"
            alert["deviation"] = f"{dev:+.1f}%" if feat else "—"
            alert["health_prediction"] = prediction["health_prediction"]
            alert["health_confidence"] = prediction["health_confidence"]
            alert["anomaly_status"] = prediction["anomaly_status"]
            alert["anomaly_score"] = prediction["anomaly_score_display"]
            alert["rationale"] = rationale
            alert["timestamp"] = timestamp
            alert["recommended_action"] = RECOMMENDED_ACTIONS.get(feat, "Review telemetry trend")
        else:
            alert_id = _new_alert_id()
            alert = {
                "id": alert_id,
                "satellite": sat_id,
                "priority": priority,
                "subsystem": subsystem,
                "issue": issue,
                "parameter": config.FEATURE_RANGES[feat]["label"] if feat else "—",
                "current": _format_value(feat, telemetry[feat]) if feat else "—",
                "expected": _expected_range_text(feat) if feat else "—",
                "deviation": f"{dev:+.1f}%" if feat else "—",
                "health_prediction": prediction["health_prediction"],
                "health_confidence": prediction["health_confidence"],
                "anomaly_status": prediction["anomaly_status"],
                "anomaly_score": prediction["anomaly_score_display"],
                "status": "OPEN",
                "rationale": rationale,
                "recommended_action": RECOMMENDED_ACTIONS.get(feat, "Review telemetry trend"),
                "timestamp": timestamp,
                "opened_at": timestamp,
            }
            _alerts[alert_id] = alert
            _active_by_sat[sat_id] = alert_id

        incident_service.sync_from_alert(_alerts[_active_by_sat[sat_id]])


def _build_rationale(priority, prediction, feat, dev):
    label = config.FEATURE_RANGES[feat]["label"] if feat else "telemetry"
    if priority == "CRITICAL":
        return (f"Critical priority assigned because the health classifier predicts Unhealthy "
                f"({prediction['health_confidence']}% confidence) while the anomaly detector "
                f"simultaneously flags this reading as anomalous. {label} shows the largest "
                f"deviation from its nominal envelope ({dev:+.1f}%), and the combination of a "
                f"confirmed anomaly with a degraded health prediction indicates an active fault "
                f"requiring immediate attention.")
    if priority == "HIGH":
        return (f"High priority assigned because the health classifier predicts Unhealthy with "
                f"high confidence ({prediction['health_confidence']}%), even though the anomaly "
                f"detector still reads Normal. {label} is the most deviated parameter "
                f"({dev:+.1f}%) and should be reviewed before it develops into a confirmed anomaly.")
    if priority == "MEDIUM":
        return (f"Medium priority assigned because the health classifier predicts Unhealthy "
                f"({prediction['health_confidence']}% confidence) while the anomaly detector "
                f"still reads Normal. {label} deviates {dev:+.1f}% from its nominal envelope; "
                f"monitor the trend.")
    return (f"Low priority assigned because the anomaly detector flagged this telemetry sample "
            f"as anomalous even though the health classifier still predicts Healthy "
            f"({prediction['health_confidence']}% confidence). {label} is the most deviated "
            f"parameter ({dev:+.1f}%); no immediate action required.")


# ---------------------------------------------------------------------
# Query + operator-action API used by routes/alert_routes.py
# ---------------------------------------------------------------------
def list_alerts():
    with _lock:
        return sorted(_alerts.values(), key=lambda a: a["timestamp"], reverse=True)


def get_alert(alert_id):
    with _lock:
        return _alerts.get(alert_id)


def set_status(alert_id, status):
    with _lock:
        alert = _alerts.get(alert_id)
        if not alert:
            return None
        alert["status"] = status
        if status == "RESOLVED":
            alert["resolved_at"] = datetime.now(timezone.utc).isoformat()
            sat_id = alert["satellite"]
            if _active_by_sat.get(sat_id) == alert_id:
                _active_by_sat[sat_id] = None
        incident_service.sync_from_alert(alert)
        return alert
