import json
import logging

from flask import Blueprint, request, jsonify, render_template, Response, stream_with_context
from marshmallow import Schema, fields, ValidationError

logger = logging.getLogger(__name__)

from app.services.intelligence_service.chatbot_service.chatbot_service import ChatbotService

chatbot_bp = Blueprint("chatbot", __name__)

# Schemas
class SendMessageSchema(Schema):
    conversation_id = fields.Int(required=True)
    message = fields.Str(required=True, validate=lambda x: 1 <= len(x) <= 2000)
    language = fields.Str(load_default='en', validate=lambda x: x in ('en', 'ur'))


class MessageResponseSchema(Schema):
    id = fields.Int()
    sender = fields.Str()
    message = fields.Str()
    timestamp = fields.Str()
    metadata = fields.Dict(allow_none=True)


class ConversationSchema(Schema):
    id = fields.Int()
    title = fields.Str()
    created_at = fields.Str()
    updated_at = fields.Str()
    message_count = fields.Int()


send_message_schema = SendMessageSchema()
message_response_schema = MessageResponseSchema()
conversations_schema = ConversationSchema(many=True)

USER_ID = 1  # TODO: Replace with auth session user_id


# ── Pages ──────────────────────────────────────────────────────────────────

@chatbot_bp.route("/", methods=["GET"])
def chatbot_page():
    """Render chatbot page."""
    return render_template("chatbot.html")


# ── Conversations ──────────────────────────────────────────────────────────

@chatbot_bp.route("/conversations", methods=["GET"])
def get_conversations():
    """Get user's recent conversations."""
    limit = request.args.get("limit", 10, type=int)
    conversations = ChatbotService.get_conversations(USER_ID, limit)
    return jsonify({"conversations": conversations}), 200


@chatbot_bp.route("/conversations", methods=["POST"])
def create_conversation():
    """Create a new conversation."""
    try:
        conversation_id = ChatbotService.get_or_create_conversation(USER_ID)
        return jsonify({"conversation_id": conversation_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@chatbot_bp.route("/conversations/<int:conversation_id>", methods=["GET"])
def get_conversation(conversation_id):
    """Get conversation with all messages."""
    try:
        messages = ChatbotService.get_conversation_messages(conversation_id, USER_ID)
        conversations = ChatbotService.get_conversations(USER_ID, 1)
        current = next((c for c in conversations if c["id"] == conversation_id), None)

        return jsonify({
            "conversation": current,
            "messages": messages,
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@chatbot_bp.route("/conversations/<int:conversation_id>", methods=["DELETE"])
def delete_conversation(conversation_id):
    """Delete a conversation."""
    try:
        ChatbotService.delete_conversation(conversation_id, USER_ID)
        return jsonify({"message": "Conversation deleted"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ── Messages ───────────────────────────────────────────────────────────────

@chatbot_bp.route("/send", methods=["POST"])
def send_message():
    """Send a message and get AI response."""
    data = request.get_json() or {}

    try:
        valid_data = send_message_schema.load(data)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    conversation_id = valid_data["conversation_id"]
    message = valid_data["message"]

    try:
        result = ChatbotService.send_message(USER_ID, conversation_id, message,
                                             valid_data.get("language", "en"))
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@chatbot_bp.route("/messages/<int:conversation_id>", methods=["GET"])
def get_messages(conversation_id):
    """Get messages for a conversation."""
    try:
        messages = ChatbotService.get_conversation_messages(conversation_id, USER_ID)
        return jsonify({"messages": messages}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@chatbot_bp.route("/send/stream", methods=["POST"])
def send_message_stream():
    """Send a message and receive pipeline status + AI response as SSE events."""
    data = request.get_json() or {}
    try:
        valid_data = send_message_schema.load(data)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    def generate():
        try:
            yield from ChatbotService.send_message_stream(
                USER_ID, valid_data["conversation_id"], valid_data["message"],
                valid_data.get("language", "en"),
            )
        except Exception as exc:
            logger.error("SSE route crashed: %s", exc, exc_info=True)
            yield f"event: error\ndata: {json.dumps({'message': 'Something went wrong on the server.'})}\n\n"

    return Response(
        stream_with_context(generate()),
        content_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@chatbot_bp.route("/setup-demo", methods=["POST"])
def setup_demo():
    """Seed the weather-change demo scenario (pre-rain tasks done, irrigation tasks pending).

    After calling this, ask the chatbot:
        "Why are you asking me to do irrigation tasks in May?"
    """
    from app.services.demo_scenario_service import DemoScenarioService
    try:
        result = DemoScenarioService.setup(USER_ID)
        return jsonify(result), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400
