from marshmallow import Schema, fields

class CropSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    soil_type = fields.Str()
    water_requirement = fields.Float()