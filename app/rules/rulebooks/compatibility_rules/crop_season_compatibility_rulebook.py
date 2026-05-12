from app.extensions import db


class CropSeasonCompatibilityRulebook(db.Model):
    __tablename__ = "crop_season_compatibility_rulebook"

    id = db.Column(db.Integer, primary_key=True)
    crop_id = db.Column(db.Integer, nullable=False)
    season  = db.Column(db.String(50), nullable=False)

    score = db.Column(db.Float, nullable=False)

    def get_score(rulebook, crop_id, season):
        pass

    def in_range(rulebook, *keys, column, value):
        pass
