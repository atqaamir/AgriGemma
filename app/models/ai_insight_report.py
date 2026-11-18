from datetime import datetime, timezone
from app.extensions import db


class AiInsightReport(db.Model):
    """One stored AI result per generate click: task insights (tasks page) or the farm report
    (dashboard). Replaces dashboard_summary / task_intelligence_summary (left in the DB unused;
    no DROP on the live Postgres).

    `signals` and `fingerprint_parts` record what the result was based on, so the page can say
    "Your farm changed since this report" without an AI call, and the next farm report can
    list what changed since this one.
    """
    __tablename__ = "ai_insight_report"

    id                = db.Column(db.Integer, primary_key=True)
    user_id           = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    kind              = db.Column(db.String(30), nullable=False)    # "task_insights" | "farm_report"
    data              = db.Column(db.Text, nullable=False)          # validated result (JSON)
    signals           = db.Column(db.Text, nullable=False)          # signals it was built from (JSON)
    fingerprint       = db.Column(db.String(64), nullable=False)    # hash of fingerprint_parts
    fingerprint_parts = db.Column(db.Text, nullable=False)          # {"date", "tasks", "plan"} (JSON)
    as_of_date        = db.Column(db.Date, nullable=False)          # demo date (clock.today())
    is_fallback       = db.Column(db.Boolean, default=False, nullable=False)   # basic summary, no AI
    latency_ms        = db.Column(db.Integer, nullable=True)        # AI call time
    model             = db.Column(db.String(100), nullable=True)    # provider / model name
    generated_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
