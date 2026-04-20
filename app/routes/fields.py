from flask import Blueprint, request, jsonify, render_template

from app.services.field_service import FieldService
from app.schemas.field_schema import (
    FieldDetailSchema,
    FieldCardSchema,
    MyFieldsPageSchema,
    CreateFieldSchema,
)
from app.schemas.task_schema import TaskCardSchema

fields_bp = Blueprint("fields_bp", __name__)

field_detail_schema = FieldDetailSchema()
field_card_schema = FieldCardSchema(many=True)
field_create_schema = CreateFieldSchema()
task_card_schema = TaskCardSchema(many=True)


@fields_bp.route("/", methods=["GET"])
def fields_page():
    return render_template("fields.html")


@fields_bp.route("/fields", methods=["GET"])
def get_fields():
    fields = FieldService.get_all_fields()

    all_tasks = []
    for field in fields:
        all_tasks.extend(field.tasks)

    unique_tasks = list({task.id: task for task in all_tasks}.values())

    result = {
        "field_cards": field_card_schema.dump(fields),
        "field_task_cards": task_card_schema.dump(unique_tasks),
    }

    return jsonify(result), 200


@fields_bp.route("/fields/<int:field_id>", methods=["GET"])
def get_field(field_id):
    field = FieldService.get_field_by_id(field_id)

    if not field:
        return jsonify({"error": "Field not found"}), 404

    return jsonify(field_detail_schema.dump(field)), 200


@fields_bp.route("/fields", methods=["POST"])
def create_field():
    data = request.get_json() or {}

    try:
        valid_data = field_create_schema.load(data)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    field = FieldService.create_field(valid_data)
    return jsonify(field_detail_schema.dump(field)), 201


@fields_bp.route("/fields/active", methods=["GET"])
def get_active_fields():
    result = FieldService.get_active_fields_with_tasks()

    response = {
        "field_cards": field_card_schema.dump(result["fields"]),
        "field_task_cards": task_card_schema.dump(result["tasks"]),
    }

    return jsonify(response), 200