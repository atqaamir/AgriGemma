from marshmallow import Schema, fields
from .crop_schema import CropMiniSchema

class FieldSchema(Schema):
    id = fields.Int(dump_only=True)
    crop = fields.Nested(CropMiniSchema)

    name = fields.Str(required=True)
    acreage = fields.Float()
    growth_stage = fields.Str()
    health_status = fields.Str()
    field_score = fields.Float()
    moisture_level = fields.Float()
    heat_level = fields.Float()
    stress_risk = fields.Float()
    disease_risk = fields.Str()

    currently_active = fields.Bool()

    user_id = fields.Int()