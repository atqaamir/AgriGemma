""" Keeps track of the crops being cultivated, their current growth stages, current health status, and other relevant information. """
from app.extensions import db


class Crop(db.Model):
    __tablename__ = "crop"

    id = db.Column(db.Integer, primary_key=True)
    crop_name_id = db.Column(db.Integer, db.ForeignKey("crop_names.id"))
    currently_active = db.Column(db.Boolean, default=True, nullable=False)
    current_health_status = db.Column(db.String(50), nullable=True)
    planting_date = db.Column(db.Date, nullable=True)
    currently_water_requirement = db.Column(db.Float, nullable=True)
    current_growth_stage_id = db.Column(db.Integer, db.ForeignKey("growth_stage.id"))
    field_id = db.Column(db.Integer, db.ForeignKey("field.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Relationships
    tasks = db.relationship("Task", backref="crop", lazy="select", foreign_keys="Task.crop_id")
    crop_name_rel = db.relationship("CropNames", foreign_keys=[crop_name_id], lazy="joined")
    growth_stage_rel = db.relationship("GrowthStage", foreign_keys=[current_growth_stage_id], lazy="joined")

    # Compatibility properties so code using old field names continues to work
    @property
    def name(self):
        return self.crop_name_rel.name if self.crop_name_rel else None

    @property
    def growth_stage(self):
        return self.growth_stage_rel.name if self.growth_stage_rel else None

    @property
    def health_status(self):
        return self.current_health_status

    @property
    def water_requirement(self):
        return self.currently_water_requirement

    @property
    def soil_type(self):
        return None

    def __repr__(self):
        return f"<Crop {self.id} - {self.name}>"