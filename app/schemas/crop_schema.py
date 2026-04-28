from marshmallow import Schema, fields, validate
from app.schemas.task_schema import TaskCardSchema


class CreateCropSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    growth_stage = fields.Str(allow_none=True)
    health_status = fields.Str(allow_none=True)
    planting_date = fields.Date(allow_none=True)
    soil_type = fields.Str(allow_none=True)
    water_requirement = fields.Float(allow_none=True)
    currently_active = fields.Bool(allow_none=False)



class CropCardSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    growth_stage = fields.Str(allow_none=True)
    health_status = fields.Str(allow_none=True)
    planting_date = fields.Date(allow_none=True)
    currently_active = fields.Bool(allow_none=False)

    field_count = fields.Method("get_field_count")
    field_name = fields.Method("get_field_names")
    task_count = fields.Method("get_task_count")
    pending_task_count = fields.Method("get_pending_task_count")
    tasks_preview = fields.Method("get_tasks_preview")

    def get_field_count(self, obj):
        return len(obj.fields)
    
    def get_field_names(self, obj):
        return [field.name for field in obj.fields]

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
    currently_active = fields.Bool(allow_none=False)

    related_fields = fields.Method("get_related_fields")
    tasks = fields.Method("get_tasks")


    def get_related_fields(self, obj):
        return [
            {
                "id": field.id,
                "name": field.name,
                "acreage": field.acreage,
                "currently_active": field.currently_active,
            }
            for field in obj.fields
        ]

    def get_tasks(self, obj):
        return TaskCardSchema(many=True).dump(obj.tasks)
    
class MyCropsPageSchema(Schema):
    crop_cards = fields.List(fields.Nested(CropCardSchema))
    crop_task_cards = fields.List(fields.Nested(TaskCardSchema))