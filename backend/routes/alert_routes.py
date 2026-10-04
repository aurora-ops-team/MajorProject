"""
alert_routes.py

Alert Center + Resolution Center endpoints. Alert/incident state lives
in services.alert_service / services.incident_service (backend-owned,
per the integration plan) so it is consistent across every connected
client and every page.
"""

from flask import Blueprint, jsonify, request

from services import alert_service, incident_service

alert_bp = Blueprint("alert_routes", __name__)

VALID_STATUSES = {"OPEN", "ACKNOWLEDGED", "INVESTIGATING", "RESOLVED"}


@alert_bp.route("/api/alerts")
def list_alerts():
    return jsonify({"alerts": alert_service.list_alerts()})


@alert_bp.route("/api/alerts/<alert_id>")
def alert_detail(alert_id):
    alert = alert_service.get_alert(alert_id)
    if not alert:
        return jsonify({"error": "unknown alert"}), 404
    return jsonify(alert)


@alert_bp.route("/api/alerts/<alert_id>/acknowledge", methods=["POST"])
def acknowledge(alert_id):
    alert = alert_service.set_status(alert_id, "ACKNOWLEDGED")
    if not alert:
        return jsonify({"error": "unknown alert"}), 404
    return jsonify(alert)


@alert_bp.route("/api/alerts/<alert_id>/investigate", methods=["POST"])
def investigate(alert_id):
    alert = alert_service.set_status(alert_id, "INVESTIGATING")
    if not alert:
        return jsonify({"error": "unknown alert"}), 404
    return jsonify(alert)


@alert_bp.route("/api/alerts/<alert_id>/resolve", methods=["POST"])
def resolve(alert_id):
    alert = alert_service.set_status(alert_id, "RESOLVED")
    if not alert:
        return jsonify({"error": "unknown alert"}), 404
    return jsonify(alert)


# ---------------------------------------------------------------------
# Incidents / Resolution Center
# ---------------------------------------------------------------------
@alert_bp.route("/api/incidents")
def list_incidents():
    return jsonify({"incidents": incident_service.list_incidents()})


@alert_bp.route("/api/incidents/<incident_id>")
def incident_detail(incident_id):
    incident = incident_service.get_incident(incident_id)
    if not incident:
        return jsonify({"error": "unknown incident"}), 404
    return jsonify(incident)


@alert_bp.route("/api/incidents/<incident_id>/status", methods=["POST"])
def incident_status(incident_id):
    body = request.get_json(silent=True) or {}
    stage = body.get("stage")
    if stage is None:
        return jsonify({"error": "missing 'stage' (integer 0-4)"}), 400
    incident = incident_service.set_stage(incident_id, int(stage))
    if not incident:
        return jsonify({"error": "unknown incident"}), 404
    return jsonify(incident)
