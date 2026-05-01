from app.extensions import db

class GrowthStage(db.Model):
    __tablename__ = "growth_stage"
    id = db.Column(db.Integer, primary_key=True)
    growth_stage = db.Column(db.String(100), nullable=False)

