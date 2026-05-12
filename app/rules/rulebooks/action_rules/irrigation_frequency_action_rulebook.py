from app.extensions import db


class IrrigationFrequencyActionRulebook(db.Model):
    __tablename__ = "irrigation_frequency_action_rulebook"

    id             = db.Column(db.Integer, primary_key=True)
    crop_id        = db.Column(db.Integer, nullable=False)
    irr_freq_range = db.Column(db.String(20), nullable=False)

    feasibility = db.Column(db.String(20), nullable=False)
    reasoning   = db.Column(db.Text,       nullable=False)
    actions     = db.Column(db.Text,       nullable=False)

    def get_action(rulebook, crop_id, irr_freq_range):
        pass
