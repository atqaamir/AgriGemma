from app.extensions import db


class PhActionRulebook(db.Model):
    __tablename__ = "ph_action_rulebook"

    id          = db.Column(db.Integer, primary_key=True)
    crop_id     = db.Column(db.Integer, nullable=False)
    ph_category = db.Column(db.String(20), nullable=False)

    feasibility = db.Column(db.String(20), nullable=False)
    reasoning   = db.Column(db.Text,       nullable=False)
    actions     = db.Column(db.Text,       nullable=False)

    def get_action(rulebook, crop_id, ph_category):
        pass
