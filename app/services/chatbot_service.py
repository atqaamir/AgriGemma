"""
Chatbot Service - Main orchestration layer for farmer chatbot.
Manages conversation context, integrates with AI model, and handles farming knowledge.
"""
import json
import logging
from datetime import datetime

from app.services.ai_model_service import ai_model_service
from app.services.farming_knowledge_base import FarmingKnowledgeBase
from app.services.context_aggregation_service import ContextAggregationService
from app.repositories.chat_repository import ChatRepository

logger = logging.getLogger(__name__)


class ChatbotService:
    """
    Smart agricultural chatbot that provides context-aware farming advice.

    Features:
    - Aggregates farmer context (fields, crops, tasks, weather)
    - Integrates farming knowledge base
    - Maintains conversation history
    - Generates AI-powered recommendations
    - Provider-agnostic (works with any AI backend)
    """

    # System prompt template for the chatbot
    SYSTEM_PROMPT_TEMPLATE = """You are an expert agricultural advisor with deep knowledge of farming practices.
You are helping a farmer with their farm management and decision-making.

{knowledge_base}

FARMER CONTEXT:
{farmer_context}

Your responsibilities:
1. Provide practical, actionable farming advice
2. Use the knowledge base to give informed recommendations
3. Consider the farmer's current situation (fields, crops, weather, tasks)
4. Be specific and avoid generic advice
5. Explain reasoning behind recommendations
6. Ask clarifying questions if needed
7. Provide both immediate actions and long-term strategies

Format your response as helpful, conversational advice. Be friendly and supportive."""

    @staticmethod
    def get_or_create_conversation(user_id: int, conversation_id: int = None) -> int:
        """Get existing conversation or create new one."""
        if conversation_id:
            conversation = ChatRepository.get_conversation(conversation_id)
            if conversation and conversation.user_id == user_id:
                return conversation.id

        # Create new conversation with current context
        context = ContextAggregationService.build_task_context(user_id)
        conversation = ChatRepository.create_conversation(
            user_id=user_id,
            title="Farm Chat",  # Will be auto-updated
            context=context,
        )
        return conversation.id

    @staticmethod
    def send_message(user_id: int, conversation_id: int, user_message: str) -> dict:
        """
        Process user message and generate AI response.

        Returns:
            {
                "conversation_id": int,
                "message_id": int,
                "user_message": str,
                "bot_message": str,
                "timestamp": str,
                "metadata": dict
            }
        """
        # Validate conversation belongs to user
        conversation = ChatRepository.get_conversation(conversation_id)
        if not conversation or conversation.user_id != user_id:
            raise ValueError("Invalid conversation")

        # Store user message
        user_msg = ChatRepository.create_message(
            conversation_id=conversation_id,
            sender="user",
            message=user_message,
        )

        # Get conversation history for context
        messages = ChatRepository.get_messages(conversation_id)
        history = "\n".join([f"{m.sender.upper()}: {m.message}" for m in messages[:-1]])  # Exclude current

        # Build context
        farmer_context = ContextAggregationService.build_task_context(user_id)
        knowledge_base = FarmingKnowledgeBase.to_prompt_context()

        # Build system prompt
        farmer_context_str = ChatbotService._format_farmer_context(farmer_context)
        system_prompt = ChatbotService.SYSTEM_PROMPT_TEMPLATE.format(
            knowledge_base=knowledge_base,
            farmer_context=farmer_context_str,
        )

        # Build full prompt with history
        full_prompt = f"""{system_prompt}

CONVERSATION HISTORY:
{history}

USER: {user_message}

ADVISOR: """

        # Get AI response
        try:
            bot_response = ai_model_service.complete(full_prompt)
            is_fallback = False
        except Exception as exc:
            logger.warning("AI model failed: %s", exc)
            bot_response = ChatbotService._build_fallback_response(user_message, farmer_context)
            is_fallback = True

        # Store bot message
        bot_msg = ChatRepository.create_message(
            conversation_id=conversation_id,
            sender="bot",
            message=bot_response,
            metadata={
                "is_fallback": is_fallback,
                "model": "fallback" if is_fallback else ai_model_service.get_provider().name,
                "generated_at": datetime.utcnow().isoformat(),
            },
        )

        # Update conversation title if first message
        if len(messages) == 1:  # Just user message
            title = ChatbotService._generate_title(user_message)
            ChatRepository.update_conversation_title(conversation_id, title)

        return {
            "conversation_id": conversation_id,
            "user_message_id": user_msg.id,
            "bot_message_id": bot_msg.id,
            "user_message": user_msg.message,
            "bot_message": bot_msg.message,
            "timestamp": bot_msg.created_at.isoformat(),
            "metadata": bot_msg.metadata_,
        }

    @staticmethod
    def get_conversation_messages(conversation_id: int, user_id: int) -> list:
        """Get all messages for a conversation."""
        conversation = ChatRepository.get_conversation(conversation_id)
        if not conversation or conversation.user_id != user_id:
            raise ValueError("Invalid conversation")

        messages = ChatRepository.get_messages(conversation_id)
        return [
            {
                "id": msg.id,
                "sender": msg.sender,
                "message": msg.message,
                "timestamp": msg.created_at.isoformat(),
                "metadata": msg.metadata_,
            }
            for msg in messages
        ]

    @staticmethod
    def get_conversations(user_id: int, limit: int = 10) -> list:
        """Get user's recent conversations."""
        conversations = ChatRepository.get_user_conversations(user_id, limit)
        return [
            {
                "id": conv.id,
                "title": conv.title or "Farm Chat",
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "message_count": len(conv.messages),
            }
            for conv in conversations
        ]

    @staticmethod
    def delete_conversation(conversation_id: int, user_id: int) -> bool:
        """Delete a conversation."""
        conversation = ChatRepository.get_conversation(conversation_id)
        if not conversation or conversation.user_id != user_id:
            raise ValueError("Invalid conversation")
        return ChatRepository.delete_conversation(conversation_id)

    # ── Private helpers ────────────────────────────────────────────────────

    @staticmethod
    def _format_farmer_context(context: dict) -> str:
        """Format farmer context for prompt."""
        farm = context.get("farm", {})
        tasks = context.get("tasks", {})
        weather = context.get("weather", {})

        return f"""
Farm Overview:
- Active fields: {farm.get('active_fields', 0)}
- Total crops: {farm.get('total_crops', 0)}

Task Status:
- Pending: {tasks.get('pending_count', 0)}
- Overdue: {tasks.get('overdue_count', 0)}
- Completed: {tasks.get('completed_count', 0)}

Active Fields:
{ChatbotService._format_fields(farm.get('active_fields_data', []))}

Current Weather:
{ChatbotService._format_weather(weather)}
"""

    @staticmethod
    def _format_fields(fields: list) -> str:
        """Format field information."""
        if not fields:
            return "  No active fields"
        return "\n".join([
            f"  - {f.get('name')}: {f.get('crop', 'unknown')} "
            f"(health: {f.get('health_status', 'unknown')}, "
            f"moisture: {f.get('moisture_level', 'N/A')}%)"
            for f in fields
        ])

    @staticmethod
    def _format_weather(weather: dict) -> str:
        """Format weather information."""
        current = weather.get("current", {})
        forecast = weather.get("forecast", [])

        result = f"  Temperature: {current.get('temp', 'N/A')}°C, "
        result += f"Humidity: {current.get('humidity', 'N/A')}%, "
        result += f"Condition: {current.get('condition', 'unknown')}"

        if forecast:
            result += "\n  Forecast: " + ", ".join([
                f"{f.get('date')}: {f.get('condition')}"
                for f in forecast[:3]
            ])

        return result

    @staticmethod
    def _generate_title(first_message: str) -> str:
        """Generate conversation title from first message."""
        if len(first_message) > 50:
            return first_message[:47] + "..."
        return first_message

    @staticmethod
    def _build_fallback_response(user_message: str, context: dict) -> str:
        """Build fallback response when AI is unavailable."""
        # Rule-based response when AI fails
        message_lower = user_message.lower()
        farm = context.get("farm", {})
        tasks = context.get("tasks", {})

        if any(word in message_lower for word in ["water", "irrigat", "moisture"]):
            if farm.get("active_fields_data"):
                field = farm["active_fields_data"][0]
                moisture = field.get("moisture_level", 0)
                if moisture < 30:
                    return (
                        f"Your {field.get('name')} has low soil moisture ({moisture}%). "
                        "I recommend increasing irrigation frequency. "
                        "Check field conditions and adjust watering schedule accordingly."
                    )
            return "To optimize irrigation, monitor soil moisture regularly and water when it drops below 30%."

        if any(word in message_lower for word in ["disease", "pest", "health", "sick"]):
            return (
                "For disease and pest management:\n"
                "1. Scout fields regularly for symptoms\n"
                "2. Identify problems early\n"
                "3. Apply appropriate treatments\n"
                "4. Consider preventive measures like crop rotation\n"
                "Please describe what you're seeing for specific recommendations."
            )

        if any(word in message_lower for word in ["task", "todo", "work", "do"]):
            return (
                f"You have {tasks.get('pending_count', 0)} pending tasks. "
                "Prioritize based on urgency and seasonality. "
                "Would you like help planning your work schedule?"
            )

        if any(word in message_lower for word in ["plant", "crop", "sow", "seed"]):
            return (
                "Consider these factors when planning planting:\n"
                "1. Soil temperature (crop-specific minimums)\n"
                "2. Weather forecast\n"
                "3. Soil preparation and fertilization\n"
                "4. Pest and disease history\n"
                "What crop are you considering?"
            )

        return (
            "I'm here to help with your farming questions about irrigation, diseases, pests, "
            "planting, fertilization, and task management. What would you like to know?"
        )
