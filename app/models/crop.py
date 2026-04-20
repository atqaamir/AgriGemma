from app.extensions import db


class Crop(db.Model):
    __tablename__ = "crop"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    growth_stage = db.Column(db.String(50), nullable=True)
    health_status = db.Column(db.String(50), nullable=True)
    planting_date = db.Column(db.Date, nullable=True)
    soil_type = db.Column(db.String(50), nullable=True)
    water_requirement = db.Column(db.Float, nullable=True)

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