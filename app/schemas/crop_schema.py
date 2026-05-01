from marshmallow import Schema, fields, validate, RAISE
from app.schemas.task_schema import TaskCardSchema


class CreateCropSchema(Schema):
    crop_name_id = fields.Int(required=True)
    current_health_status = fields.Str(allow_none=True)
    planting_date = fields.Date(allow_none=True)
    currently_water_requirement = fields.Float(allow_none=True)
    current_growth_stage_id = fields.Int(allow_none=True)
    field_id = fields.Int(required=True)
    user_id = fields.Int(allow_none=True)
    currently_active = fields.Bool(load_default=True)


class CropCardSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    growth_stage = fields.Str(allow_none=True)
    health_status = fields.Str(allow_none=True)
    planting_date = fields.Date(allow_none=True)
    currently_active = fields.Bool()

    task_count = fields.Method("get_task_count")
    pending_task_count = fields.Method("get_pending_task_count")
    tasks_preview = fields.Method("get_tasks_preview")

    def get_task_count(self, obj):
        return len(obj.tasks)

    def get_pending_task_count(self, obj):
        return len([task for task in obj.tasks if not task.completed])

    def get_tasks_preview(self, obj):
        pending_tasks = [task for task in obj.tasks if not task.completed][:3]
        return TaskCardSchema(many=True).dump(pending_tasks)


class CropDetailSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    growth_stage = fields.Str(allow_none=True)
    health_status = fields.Str(allow_none=True)
    soil_type = fields.Str(allow_none=True)
    water_requirement = fields.Float(allow_none=True)
    planting_date = fields.Date(allow_none=True)
    currently_active = fields.Bool()

    tasks = fields.Method("get_tasks")

    def get_tasks(self, obj):
        return TaskCardSchema(many=True).dump(obj.tasks)


class MyCropsPageSchema(Schema):
    crop_cards = fields.List(fields.Nested(CropCardSchema))
    crop_task_cards = fields.List(fields.Nested(TaskCardSchema))


class UpdateCropSchema(Schema):

    class Meta:
        unknown = RAISE

    crop_name_id = fields.Int(allow_none=True)
    current_growth_stage_id = fields.Int(allow_none=True)
    current_health_status = fields.Str(allow_none=True)
    planting_date = fields.Date(allow_none=True)
    currently_water_requirement = fields.Float(allow_none=True)
    field_id = fields.Int(allow_none=True)
    currently_active = fields.Bool(required=False)
