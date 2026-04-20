from datetime import datetime
from app.extensions import db


class PesticideUse(db.Model):
    __tablename__ = "pesticide_use"

    id = db.Column(db.Integer, primary_key=True)

    pesticide_id = db.Column(db.Integer, db.ForeignKey("pesticide.id"), nullable=False)
    field_id = db.Column(db.Integer, db.ForeignKey("field.id"), nullable=False)
    crop_id = db.Column(db.Integer, db.ForeignKey("crop.id"), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    use_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    dosage_used = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    
    tasks = db.relationship(
        "Task",
        back_populates="pesticide",
        foreign_keys="Task.pesticide_id",
        lazy="select",
    )


    def to_dict(self):
        return {
            "id": self.id,
            "pesticide_id": self.pesticide_id,
            "field_id": self.field_id,
            "crop_id": self.crop_id,
            "user_id": self.user_id,
            "use_date": self.use_date.isoformat() if self.use_date else None,
            "dosage_used": self.dosage_used,
            "notes": self.notes,
        }