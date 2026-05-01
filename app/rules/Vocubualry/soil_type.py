from app.extensions import db

class Soil_Type(db.Model):
    __tablename__ = "soil_type"
    id = db.Column(db.Integer, primary_key=True)
    soil_type = db.Column(db.String(100), nullable=False)

