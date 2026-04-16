from marshmallow import Schema, fields

class FieldSchema(Schema):
    id = fields.Int(dump_only=True)
    crop_type = fields.Str()
    name = fields.Str(required=True)
    size = fields.Float()
    growth_stage = fields.Str()
    health_status = fields.Str()
    field_score = fields.Float()
    moisture_level = fields.Float()
    heat_level = fields.Float()
    stress_risk = fields.Float()
    disease_risk = fields.Str()
    user_id = fields.Int()