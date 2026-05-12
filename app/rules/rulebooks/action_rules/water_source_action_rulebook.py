from app.extensions import db


class WaterSourceActionRulebook(db.Model):
    __tablename__ = "water_source_action_rulebook"

    id              = db.Column(db.Integer, primary_key=True)
    crop_id         = db.Column(db.Integer, nullable=False)
    water_source_id = db.Column(db.Integer, nullable=False)

    feasibility = db.Column(db.String(20), nullable=False)
    reasoning   = db.Column(db.Text,       nullable=False)
    actions     = db.Column(db.Text,       nullable=False)

    def get_action(rulebook, crop_id, water_source_id):
        pass
