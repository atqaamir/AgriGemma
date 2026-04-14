from datetime import datetime
from app.extensions import db


class FarmMap(db.Model):
    __tablename__ = "farm_maps"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)

    # Optional image or rendered map path
    image_url = db.Column(db.String(255), nullable=True)

    # Optional center point for displaying map
    center_lat = db.Column(db.Float, nullable=True)
    center_lng = db.Column(db.Float, nullable=True)
    zoom_level = db.Column(db.Integer, nullable=True, default=15)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    fields = db.relationship(
        "FieldBoundary",
        backref="farm_map",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "image_url": self.image_url,
            "center_lat": self.center_lat,
            "center_lng": self.center_lng,
            "zoom_level": self.zoom_level,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "fields": [field.to_dict() for field in self.fields],
        }