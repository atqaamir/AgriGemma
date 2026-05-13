from app.extensions import db


class CropSoilCompatibilityRulebook(db.Model):
    __tablename__ = "crop_soil_compatibility_rulebook"

    id = db.Column(db.Integer, primary_key=True)
    crop_id      = db.Column(db.Integer, nullable=False)
    soil_type_id = db.Column(db.Integer, nullable=False)

    score = db.Column(db.Float, nullable=False)

    def get_score(rulebook, crop_id, soil_type_id):
        pass

    def in_range(rulebook, *keys, column, value):
        pass
