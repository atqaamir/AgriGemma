from app.extensions import db


class IrrigationFrequencyCompatibilityRulebook(db.Model):
    __tablename__ = "irrigation_frequency_compatibility_rulebook"

    id = db.Column(db.Integer, primary_key=True)
    crop_id = db.Column(db.Integer, nullable=False)

    irr_freq_below_2 = db.Column(db.Float)
    irr_freq_3_4     = db.Column(db.Float)
    irr_freq_above_5 = db.Column(db.Float)

    def get_score(rulebook, crop_id, range_label):
        pass

    def in_range(rulebook, *keys, column, value):
        pass
