from flask import Blueprint, request, jsonify
from app.services.chatbot_service import get_chat_response

chatbot_bp = Blueprint("chatbot", __name__)

@chatbot_bp.route("/", methods=["POST"])
def chat():
    data = request.json
    response = get_chat_response(data["message"])
    return jsonify(response)