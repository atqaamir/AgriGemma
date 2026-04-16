from app.extensions import db

class Crop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    field_id = db.Column(db.Integer, db.ForeignKey('field.id'))
    planting_date = db.Column(db.Date)
    growth_stage = db.Column(db.String(50))
    health_status = db.Column(db.String(20))
    soil_type = db.Column(db.String(50))
    water_requirement = db.Column(db.Float)