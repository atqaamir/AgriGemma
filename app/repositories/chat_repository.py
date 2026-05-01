from datetime import datetime
from app.models.chat import Conversation, ChatMessage
from app.extensions import db


class ChatRepository:
    """Repository for chat message and conversation persistence."""

    # ── Conversations ──────────────────────────────────────────────────────

    @staticmethod
    def create_conversation(user_id: int, title: str = None, context: dict = None) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(user_id=user_id, title=title, context=context)
        db.session.add(conversation)
        db.session.commit()
        return conversation

    @staticmethod
    def get_conversation(conversation_id: int) -> Conversation:
        """Get a conversation by ID."""
        return Conversation.query.get(conversation_id)

    @staticmethod
    def get_user_conversations(user_id: int, limit: int = 20) -> list:
        """Get recent conversations for a user."""
        return (
            Conversation.query.filter_by(user_id=user_id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def update_conversation_title(conversation_id: int, title: str) -> Conversation:
        """Update conversation title."""
        conversation = Conversation.query.get(conversation_id)
        if conversation:
            conversation.title = title
            db.session.commit()
        return conversation

    @staticmethod
    def update_conversation_context(conversation_id: int, context: dict) -> Conversation:
        """Update conversation context snapshot."""
        conversation = Conversation.query.get(conversation_id)
        if conversation:
            conversation.context = context
            db.session.commit()
        return conversation

    @staticmethod
    def delete_conversation(conversation_id: int) -> bool:
        """Delete a conversation and all its messages."""
        conversation = Conversation.query.get(conversation_id)
        if conversation:
            db.session.delete(conversation)
            db.session.commit()
            return True
        return False

    # ── Messages ───────────────────────────────────────────────────────────

    @staticmethod
    def create_message(
        conversation_id: int,
        sender: str,
        message: str,
        metadata: dict = None,
    ) -> ChatMessage:
        """Create a new chat message."""
        chat_message = ChatMessage(
            conversation_id=conversation_id,
            sender=sender,
            message=message,
            metadata_=metadata,
        )
        db.session.add(chat_message)
        db.session.commit()
        return chat_message

    @staticmethod
    def get_messages(conversation_id: int, limit: int = 100) -> list:
        """Get messages for a conversation."""
        return (
            ChatMessage.query.filter_by(conversation_id=conversation_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_message(message_id: int) -> ChatMessage:
        """Get a specific message."""
        return ChatMessage.query.get(message_id)

    @staticmethod
    def delete_message(message_id: int) -> bool:
        """Delete a message."""
        message = ChatMessage.query.get(message_id)
        if message:
            db.session.delete(message)
            db.session.commit()
            return True
        return False
