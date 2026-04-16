from app.extensions import db

class Field(db.Model):
    __tablename__ = "field"

    id = db.Column(db.Integer, primary_key=True)

    crop_id = db.Column(db.Integer, db.ForeignKey("crop.id"), nullable=True)
    crop = db.relationship("Crop", backref="fields", foreign_keys=[crop_id])

    name = db.Column(db.String(100), nullable=False)
    acreage = db.Column(db.Float, nullable=True)
    growth_stage = db.Column(db.String(100), nullable=True)
    health_status = db.Column(db.String(100), nullable=True)
    field_score = db.Column(db.Float, nullable=True)
    moisture_level = db.Column(db.Float, nullable=True)
    heat_level = db.Column(db.Float, nullable=True)
    stress_risk = db.Column(db.Float, nullable=True)
    disease_risk = db.Column(db.String(100), nullable=True)

    currently_active = db.Column(db.Boolean, default=True, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)