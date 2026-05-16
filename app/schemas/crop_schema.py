from marshmallow import Schema, fields, validate, RAISE
from app.schemas.task_schema import TaskCardSchema


class CreateCropSchema(Schema):
    crop_name_id = fields.Int(required=True)
    current_health_status = fields.Str(allow_none=True)
    planting_date = fields.Date(allow_none=True)
    expected_harvest_date = fields.Date(allow_none=True, load_default=None)
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
    expected_harvest_date = fields.Date(allow_none=True)
    currently_active = fields.Bool()

    growth_progress = fields.Method("get_growth_progress")
    field = fields.Method("get_field")
    task_count = fields.Method("get_task_count")
    pending_task_count = fields.Method("get_pending_task_count")
    tasks_preview = fields.Method("get_tasks_preview")

    def get_growth_progress(self, obj):
        from app.services.domain_service.crop_service import CropService
        return CropService.calculate_growth_progress(obj)

    def get_field(self, obj):
        if obj.field:
            return {"id": obj.field.id, "name": obj.field.name}
        return None

    def get_task_count(self, obj):
        return len([t for t in obj.tasks if t.task_category == 'crop'])

    def get_pending_task_count(self, obj):
        return len([t for t in obj.tasks if t.task_category == 'crop' and not t.completed])

    def get_tasks_preview(self, obj):
        pending = [t for t in obj.tasks if t.task_category == 'crop' and not t.completed][:3]
        return TaskCardSchema(many=True).dump(pending)


class CropDetailSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    crop_name_id = fields.Int(allow_none=True)
    growth_stage = fields.Str(allow_none=True)
    current_growth_stage_id = fields.Int(allow_none=True)
    health_status = fields.Str(allow_none=True)
    soil_type = fields.Str(allow_none=True)
    water_requirement = fields.Float(allow_none=True)
    planting_date = fields.Date(allow_none=True)
    expected_harvest_date = fields.Date(allow_none=True)
    currently_active = fields.Bool()
    field_id = fields.Int(allow_none=True)

    field = fields.Method("get_field")
    tasks = fields.Method("get_tasks")

    def get_field(self, obj):
        if obj.field:
            return {"id": obj.field.id, "name": obj.field.name}
        return None

    def get_tasks(self, obj):
        crop_tasks = [t for t in obj.tasks if t.task_category == 'crop']
        return TaskCardSchema(many=True).dump(crop_tasks)


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
    expected_harvest_date = fields.Date(allow_none=True)
    currently_water_requirement = fields.Float(allow_none=True)
    field_id = fields.Int(allow_none=True)
    currently_active = fields.Bool(required=False)
