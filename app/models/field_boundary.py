from datetime import datetime
from app.extensions import db


class FieldBoundary(db.Model):
    __tablename__ = "field_boundaries"

    id = db.Column(db.Integer, primary_key=True)

    farm_map_id = db.Column(db.Integer, db.ForeignKey("farm_maps.id"), nullable=False)
    field_id = db.Column(db.Integer, db.ForeignKey("field.id"), nullable=True)

    name = db.Column(db.String(100), nullable=False)

    # JSON string of polygon coordinates
    # Example:
    # [[31.5204, 74.3587], [31.5208, 74.3592], [31.5201, 74.3598]]
    polygon_coordinates = db.Column(db.Text, nullable=False)

    color = db.Column(db.String(20), nullable=True)
    area_acres = db.Column(db.Float, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "farm_map_id": self.farm_map_id,
            "field_id": self.field_id,
            "name": self.name,
            "polygon_coordinates": self.polygon_coordinates,
            "color": self.color,
            "area_acres": self.area_acres,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }