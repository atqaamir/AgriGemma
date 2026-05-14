from app.extensions import db


class FertilizationCalendarRulebook(db.Model):
    __tablename__ = "fertilization_calendar_rulebook"

    id                = db.Column(db.Integer, primary_key=True)
    crop_id           = db.Column(db.Integer, nullable=False)
    days_after_sowing = db.Column(db.Integer, nullable=False)
