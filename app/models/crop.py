""" Keeps track of the crops being cultivated, their current growth stages, current health status, and other relevant information. """
from app.extensions import db


class Crop(db.Model):
    __tablename__ = "crop"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)  
    current_growth_stage = db.Column(db.String(50), nullable=True)
    current_health_status = db.Column(db.String(50), nullable=True)
    planting_date = db.Column(db.Date, nullable=True)
    soil_type = db.Column(db.String(50), nullable=True)
    currently_active = db.Column(db.Boolean, default=True, nullable=False)

    currently_active = db.Column(db.Boolean, default=True, nullable=False)

    fields = db.relationship(
        "Field",
        back_populates="crop",
        foreign_keys="Field.crop_id",
        lazy="select",
    )

    tasks = db.relationship(
        "Task",
        back_populates="crop",
        foreign_keys="Task.crop_id",
        lazy="select",
    )

    def __repr__(self):
        return f"<Crop {self.id} - {self.name}>"