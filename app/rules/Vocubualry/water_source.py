from app.extensions import db

class WaterSource(db.Model):
    __tablename__ = "water_source"
    id = db.Column(db.Integer, primary_key=True)
    water_source = db.Column(db.String(100), nullable=False)

