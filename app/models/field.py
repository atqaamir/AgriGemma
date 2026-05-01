"""Keeps track of the fields that the user has added to the system, along with their details and associated crop information."""
from app.extensions import db


class Field(db.Model):
    __tablename__ = "field"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    acreage = db.Column(db.Float, nullable=True)
    health_status = db.Column(db.String(100), nullable=True)
    field_score = db.Column(db.Float, nullable=True)
    health_percentage = db.Column(db.Float, nullable=True)
    moisture_level = db.Column(db.Float, nullable=True)
    heat_level = db.Column(db.Float, nullable=True)
    stress_risk = db.Column(db.Float, nullable=True)
    disease_risk = db.Column(db.String(50), nullable=True)
    water_source_id = db.Column(db.Integer, db.ForeignKey("water_source.id"))
    soil_type_id = db.Column(db.Integer, db.ForeignKey("soil_type.id"))

    currently_active = db.Column(db.Boolean, default=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    crops = db.relationship("Crop", backref="field", lazy="select")
    tasks = db.relationship("Task", backref="field", lazy="select", foreign_keys="Task.field_id")

    @property
    def crop(self):
        active = [c for c in self.crops if c.currently_active]
        return active[0] if active else (self.crops[0] if self.crops else None)

    def __repr__(self):
        return f"<Field {self.id} - {self.name}>"
