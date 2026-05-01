from marshmallow import Schema, fields, validate


class TaskCardSchema(Schema):
    id = fields.Int()
    title = fields.Str()
    priority = fields.Str()
    due_date = fields.Date(allow_none=True)
    completed = fields.Bool()
    task_type = fields.Str(allow_none=True)
    task_category = fields.Str(allow_none=True)
    field_name = fields.Method("get_field_name")
    crop_name = fields.Method("get_crop_name")

    def get_field_name(self, obj):
        return obj.field.name if obj.field else None

    def get_crop_name(self, obj):
        return obj.crop.name if obj.crop else None


class TaskDetailSchema(Schema):
    id = fields.Int()
    title = fields.Str()
    priority = fields.Str()
    created_at = fields.DateTime(allow_none=True)
    due_date = fields.Date(allow_none=True)
    completed = fields.Bool()

    task_type = fields.Str(allow_none=True)
    task_category = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    notes = fields.Str(allow_none=True)

    crop_id = fields.Int(allow_none=True)
    field_id = fields.Int(allow_none=True)

    crop_name = fields.Method("get_crop_name")
    field_name = fields.Method("get_field_name")

    def get_crop_name(self, obj):
        return obj.crop.name if obj.crop else None

    def get_field_name(self, obj):
        return obj.field.name if obj.field else None


class CreateTaskSchema(Schema):
    title = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    priority = fields.Str(
        required=True,
        validate=validate.OneOf(["critical", "high", "medium", "low"])
    )
    due_date = fields.Date(allow_none=True)
    completed = fields.Bool(load_default=False)

    task_type = fields.Str(allow_none=True)
    task_category = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    notes = fields.Str(allow_none=True)

    crop_id = fields.Int(allow_none=True)
    field_id = fields.Int(allow_none=True)


class UpdateTaskSchema(Schema):
    title = fields.Str(validate=validate.Length(min=1, max=200))
    priority = fields.Str(validate=validate.OneOf(["critical", "high", "medium", "low"]))
    due_date = fields.Date(allow_none=True)
    completed = fields.Bool()

    task_type = fields.Str(allow_none=True)
    task_category = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    notes = fields.Str(allow_none=True)

    crop_id = fields.Int(allow_none=True)
    field_id = fields.Int(allow_none=True)
