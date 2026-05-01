""" Keeps track of the crops being cultivated, their current growth stages, current health status, and other relevant information. """
from app.extensions import db


class Crop(db.Model):
    __tablename__ = "crop"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    currently_active = db.Column(db.Boolean, default=True, nullable=False)

    current_growth_stage = db.Column(db.String(50), nullable=True)
    current_health_status = db.Column(db.String(50), nullable=True)
    planting_date = db.Column(db.Date, nullable=True)
    currently_water_requirement = db.Column(db.Float, nullable=True)

    field_id = db.Column(db.Integer, db.ForeignKey("field.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    tasks = db.relationship("Task", backref="crop", lazy="select", foreign_keys="Task.crop_id")

    def __repr__(self):
        return f"<Crop {self.id} - {self.name}>"