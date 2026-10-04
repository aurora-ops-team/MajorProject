"""
decision_service.py

Rule-based layer that sits after the two ML models and turns
(health_prediction, anomaly_status) into a single final priority the
rest of the app (alerts, incidents, dashboards) can use.

Base mapping (matches the Alert Center's 4-level scheme):

    Healthy   + Normal  -> NORMAL   (no active alert)
    Healthy   + Anomaly -> LOW
    Unhealthy + Normal  -> MEDIUM
    Unhealthy + Anomaly -> CRITICAL

Escalation: an Unhealthy + Normal case is escalated from MEDIUM to HIGH
when the health classifier's confidence is very high (>= HIGH_CONFIDENCE_THRESHOLD),
since a confident "Unhealthy" call with no corroborating anomaly still
warrants closer attention than an ordinary MEDIUM.
"""

import config


def decide(health: dict, anomaly: dict) -> dict:
    is_healthy = health["health_prediction"] == "Healthy"
    is_anomaly = anomaly["anomaly_status"] == "Anomaly"
    confidence = health["health_confidence"] / 100.0

    if is_healthy and not is_anomaly:
        priority = "NORMAL"
        condition = "Nominal"
    elif is_healthy and is_anomaly:
        priority = "LOW"
        condition = "Minor Deviation"
    elif (not is_healthy) and not is_anomaly:
        priority = "HIGH" if confidence >= config.HIGH_CONFIDENCE_THRESHOLD else "MEDIUM"
        condition = "Degraded"
    else:
        priority = "CRITICAL"
        condition = "Critical"

    return {
        "priority": priority,
        "condition": condition,
    }
