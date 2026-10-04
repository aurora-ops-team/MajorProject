"""
app.py

Entry point for the AI-Based Autonomous Satellite Operation Assistant
backend.

Run with:
    cd backend
    pip install -r requirements.txt
    python app.py

The server starts on http://localhost:5000 and immediately begins the
30-second telemetry simulation for SAT-01 and SAT-02 (see
services/simulation_service.py). The frontend (in ../frontend) polls
the REST API defined in routes/ every 30 seconds to stay in sync.
"""

from flask import Flask, jsonify
from flask_cors import CORS

import config
from services.simulation_service import simulation
from routes.satellite_routes import satellite_bp
from routes.alert_routes import alert_bp
from routes.model_routes import model_bp
from routes.system_routes import system_bp
from routes.chat_routes import chat_bp


def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": config.CORS_ORIGINS}})

    app.register_blueprint(satellite_bp)
    app.register_blueprint(alert_bp)
    app.register_blueprint(model_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(chat_bp)

    @app.route("/api/health")
    def health_check():
        return jsonify({"status": "ok"})

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "not found"}), 404

    return app


app = create_app()

# Start the backend-controlled telemetry simulation as soon as the
# module is imported, whether run via `python app.py` or a WSGI server.
simulation.start()

if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG, use_reloader=False)
