"""
incident_service.py

The Resolution Center does not run another ML model (per the
integration plan) -- it simply consumes alerts. Whenever an alert
reaches HIGH or CRITICAL priority, an incident is opened here with a
rule-based probable cause and recommended action list. The operator
then moves the incident through its stages via
POST /api/incidents/<id>/status.
"""

import threading
from datetime import datetime, timezone

STAGES = ["Detected", "Prioritized", "Investigating", "Action Recommended", "Resolved"]

_lock = threading.RLock()  # reentrant: sync_from_alert() calls _new_id() while already holding this lock
_incidents = {}          # incident_id -> incident dict
_by_alert = {}            # alert_id -> incident_id
_next_id = 1

CAUSE_TEXT = {
    "Electrical Power": "Possible power subsystem degradation or abnormal battery discharge, potentially aggravated by reduced solar array efficiency.",
    "Thermal Control": "Possible radiator surface degradation or a stuck thermal louver reducing heat rejection capacity.",
    "Attitude Control": "Possible reaction wheel momentum saturation or star-tracker measurement dropout.",
    "Communications": "Possible antenna misalignment or RF front-end degradation affecting downlink throughput.",
    "Orbit / GNC": "Possible orbital perturbation or station-keeping maneuver drift outside the nominal band.",
    "General": "Telemetry deviation detected across multiple subsystems; further investigation required.",
}


def _new_id():
    global _next_id
    with _lock:
        incident_id = f"INC-{_next_id:04d}"
        _next_id += 1
    return incident_id


def sync_from_alert(alert):
    """Create/advance/resolve the incident tied to this alert, if any."""
    with _lock:
        existing_id = _by_alert.get(alert["id"])

        if alert["status"] == "RESOLVED":
            if existing_id:
                inc = _incidents[existing_id]
                inc["stage"] = 4
                inc["status"] = "Resolved"
            return

        if alert["priority"] not in ("HIGH", "CRITICAL"):
            return

        if existing_id:
            inc = _incidents[existing_id]
            inc["severity"] = alert["priority"]
            inc["issue"] = alert["issue"]
            inc["subsystem"] = alert["subsystem"]
            inc["recommended_action"] = alert["recommended_action"]
            return

        incident_id = _new_id()
        subsystem = alert["subsystem"]
        incident = {
            "id": incident_id,
            "alert_id": alert["id"],
            "satellite": alert["satellite"],
            "issue": alert["issue"],
            "subsystem": subsystem,
            "severity": alert["priority"],
            "stage": 0,
            "status": STAGES[0],
            "opened_at": alert.get("opened_at", datetime.now(timezone.utc).isoformat()),
            "problem": (f"{alert['parameter']} reading of {alert['current']} is outside the "
                        f"expected range of {alert['expected']} ({alert['deviation']} deviation)."),
            "cause": CAUSE_TEXT.get(subsystem, CAUSE_TEXT["General"]),
            "recommended_action": alert["recommended_action"],
            "actions": [
                f"Review {subsystem.lower()} telemetry trend over the last several orbital cycles",
                alert["recommended_action"],
                "Correlate with any concurrent anomalies on other subsystems",
                "Re-run health prediction after the next telemetry cycle to confirm recovery",
            ],
        }
        _incidents[incident_id] = incident
        _by_alert[alert["id"]] = incident_id


def list_incidents():
    with _lock:
        return sorted(_incidents.values(), key=lambda i: i["opened_at"], reverse=True)


def get_incident(incident_id):
    with _lock:
        return _incidents.get(incident_id)


def set_stage(incident_id, stage_index):
    with _lock:
        inc = _incidents.get(incident_id)
        if not inc:
            return None
        stage_index = max(0, min(len(STAGES) - 1, stage_index))
        inc["stage"] = stage_index
        inc["status"] = STAGES[stage_index]
        return inc
