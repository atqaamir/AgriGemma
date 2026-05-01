from datetime import datetime
from app.extensions import db


class Notification(db.Model):
    __tablename__ = "notification"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    # Longer AI-generated explanation shown in click-through modals.
    # Populated for critical and recommendation types only.
    detail = db.Column(db.Text, nullable=True)

    # info | warning | critical | recommendation
    notification_type = db.Column(db.String(30), nullable=False, default="info")

    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Optional back-link to the originating entity (task, field, crop…)
    entity_type = db.Column(db.String(50), nullable=True)
    entity_id = db.Column(db.Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<Notification {self.id} [{self.notification_type}] read={self.is_read}>"
