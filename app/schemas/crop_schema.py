from marshmallow import Schema, fields


class CropSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    field_id = fields.Int(allow_none=True)
    planting_date = fields.Date(allow_none=True)
    growth_stage = fields.Str(allow_none=True)
    health_status = fields.Str(allow_none=True)
    soil_type = fields.Str(allow_none=True)
    water_requirement = fields.Float(allow_none=True)

class CropMiniSchema(Schema):
    id = fields.Int()
    name = fields.Str()