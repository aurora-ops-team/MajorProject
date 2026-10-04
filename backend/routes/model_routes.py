"""
model_routes.py

Serves actual training results (ModelTraining/reports + plots) to the
Model Training & Performance Center page. Does not need live telemetry.
"""

from flask import Blueprint, jsonify, send_from_directory

import config
from services import model_service

model_bp = Blueprint("model_routes", __name__)


@model_bp.route("/api/models")
def list_models():
    return jsonify({
        "models": model_service.list_models(),
        "best_models": model_service.best_models(),
    })


@model_bp.route("/api/models/<model_name>")
def model_detail(model_name):
    model = model_service.get_model(model_name)
    if not model:
        return jsonify({"error": "unknown model"}), 404
    return jsonify(model)


@model_bp.route("/api/models/plots/<path:filename>")
def model_plot(filename):
    return send_from_directory(config.PLOTS_DIR, filename)
