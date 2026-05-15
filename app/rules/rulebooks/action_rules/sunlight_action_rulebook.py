from app.extensions import db


class SunlightActionRulebook(db.Model):
    __tablename__ = "sunlight_action_rulebook"

    id             = db.Column(db.Integer, primary_key=True)
    crop_id        = db.Column(db.Integer, nullable=False)
    growth_stage_id = db.Column(db.Integer, nullable=False)
    sunlight_range = db.Column(db.String(20), nullable=False)

    feasibility = db.Column(db.String(20), nullable=False)
    reasoning   = db.Column(db.Text,       nullable=False)
    actions     = db.Column(db.Text,       nullable=False)

    def get_action(rulebook, crop_id, sunlight_range):
        pass
