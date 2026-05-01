from datetime import datetime
from app.extensions import db


class Conversation(db.Model):
    __tablename__ = "conversation"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(200), nullable=True)  # Auto-generated from first message
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    context = db.Column(db.JSON, nullable=True)  # Stores context snapshot (fields, crops, tasks, weather)

    messages = db.relationship("ChatMessage", backref="conversation", cascade="all, delete-orphan", lazy=True)

    def __repr__(self) -> str:
        return f"<Conversation {self.id} user={self.user_id}>"


class ChatMessage(db.Model):
    __tablename__ = "chat_message"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversation.id"), nullable=False)
    sender = db.Column(db.String(20), nullable=False)  # "user" or "bot"
    message = db.Column(db.Text, nullable=False)
    # metadata_ for bot messages (reasoning, confidence, etc.)
    metadata_ = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<ChatMessage {self.id} [{self.sender}]>"
