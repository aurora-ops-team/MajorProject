"""Read-only chatbot endpoint."""

from flask import Blueprint, jsonify, request

import config
from services import chat_service

chat_bp = Blueprint("chat_routes", __name__)


@chat_bp.route("/api/chat/status")
def chat_status():
    configured = (
        config.CHAT_PROVIDER == "openai-compatible"
        and bool(config.CHAT_API_URL)
        and bool(config.CHAT_API_KEY)
        and bool(config.CHAT_MODEL)
    )
    return jsonify({
        "provider": "llm" if configured else "fallback",
        "configured": configured,
    })


@chat_bp.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json(silent=True)
    try:
        messages = chat_service.validate_messages(body.get("messages") if isinstance(body, dict) else None)
        return jsonify(chat_service.reply(messages))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
