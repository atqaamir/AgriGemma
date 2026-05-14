from app.extensions import db


class WaterSourceCompatibilityRulebook(db.Model):
    __tablename__ = "water_source_compatibility_rulebook"

    id = db.Column(db.Integer, primary_key=True)
    crop_id          = db.Column(db.Integer, nullable=False)
    water_source_id  = db.Column(db.Integer, nullable=False)

    score       = db.Column(db.Float,     nullable=False)
    feasibility = db.Column(db.String(20), nullable=False)

    def get_score(rulebook, crop_id, water_source_id):
        pass

    def in_range(rulebook, *keys, column, value):
        pass
