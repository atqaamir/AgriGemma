from app.extensions import db


class IrrigationCalenderRulebook(db.Model):
    __tablename__ = "irrigation_start_rulebook"

    id                = db.Column(db.Integer, primary_key=True)
    crop_id           = db.Column(db.Integer, nullable=False)
    days_after_sowing = db.Column(db.Integer, nullable=False)

    def get_start(rulebook, crop_id):
        pass
