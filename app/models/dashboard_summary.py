from datetime import datetime, timezone
from app.extensions import db


class DashboardSummary(db.Model):
    __tablename__ = "dashboard_summary"

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    summary      = db.Column(db.Text, nullable=False)
    is_fallback  = db.Column(db.Boolean, default=False)
    generated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
