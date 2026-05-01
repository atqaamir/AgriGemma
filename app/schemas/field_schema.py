from marshmallow import Schema, fields, validate
from app.schemas.task_schema import TaskCardSchema


class CreateFieldSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    acreage = fields.Float(allow_none=True)
    growth_stage = fields.Str(allow_none=True)
    health_status = fields.Str(allow_none=True)
    field_score = fields.Float(allow_none=True)
    health_percentage = fields.Float(allow_none=True)
    moisture_level = fields.Float(allow_none=True)
    heat_level = fields.Float(allow_none=True)
    stress_risk = fields.Float(allow_none=True)
    disease_risk = fields.Str(allow_none=True)
    currently_active = fields.Bool(load_default=True)
    user_id = fields.Int(allow_none=True)


class FieldCardSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    acreage = fields.Float()
    growth_stage = fields.Str()
    health_status = fields.Str()
    field_score = fields.Float()
    moisture_level = fields.Float()
    heat_level = fields.Float()
    currently_active = fields.Bool()

    crop = fields.Method("get_crop")
    task_count = fields.Method("get_task_count")
    pending_task_count = fields.Method("get_pending_task_count")
    tasks_preview = fields.Method("get_tasks_preview")

    def get_crop(self, obj):
        if obj.crop:
            return {"id": obj.crop.id, "name": obj.crop.name}
        return None

    def get_task_count(self, obj):
        return len(obj.tasks)

    def get_pending_task_count(self, obj):
        return len([t for t in obj.tasks if not t.completed])

    def get_tasks_preview(self, obj):
        pending = [t for t in obj.tasks if not t.completed][:3]
        return TaskCardSchema(many=True).dump(pending)


class FieldDetailSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    acreage = fields.Float(allow_none=True)
    growth_stage = fields.Str(allow_none=True)
    health_status = fields.Str(allow_none=True)
    field_score = fields.Float(allow_none=True)
    health_percentage = fields.Float(allow_none=True)
    moisture_level = fields.Float(allow_none=True)
    heat_level = fields.Float(allow_none=True)
    stress_risk = fields.Float(allow_none=True)
    disease_risk = fields.Str(allow_none=True)
    currently_active = fields.Bool()

    crop = fields.Method("get_crop")
    tasks = fields.Method("get_tasks")

    def get_crop(self, obj):
        if obj.crop:
            return {"id": obj.crop.id, "name": obj.crop.name}
        return None

    def get_tasks(self, obj):
        return TaskCardSchema(many=True).dump(obj.tasks)


class MyFieldsPageSchema(Schema):
    field_cards = fields.List(fields.Nested(FieldCardSchema))
    field_task_cards = fields.List(fields.Nested(TaskCardSchema))
