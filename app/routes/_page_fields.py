from flask import Blueprint, request, jsonify, render_template
from marshmallow import ValidationError

from app.services.domain_service.field_service import FieldService
from app.schemas.field_schema import (
    FieldDetailSchema,
    FieldCardSchema,
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


@fields_bp.route("/fields/vocabulary", methods=["GET"])
def get_field_vocabulary():
    return jsonify(FieldService.get_vocabulary()), 200


# ── Field collection endpoints ────────────────────────────────────────────────

@fields_bp.route("/fields", methods=["GET"])
def get_fields():
    """All fields with their field-category tasks."""
    fields = FieldService.get_all_fields()

    all_tasks = []
    for field in fields:
        all_tasks.extend(t for t in field.tasks if t.task_category == "field")
    unique_tasks = list({t.id: t for t in all_tasks}.values())

    return jsonify({
        "field_cards": field_card_schema.dump(fields),
        "field_task_cards": task_card_schema.dump(unique_tasks),
    }), 200


@fields_bp.route("/fields/active", methods=["GET"])
def get_active_fields():
    """Active fields together with their pending field-category tasks."""
    result = FieldService.get_active_fields_with_tasks()
    return jsonify({
        "field_cards": field_card_schema.dump(result["fields"]),
        "field_task_cards": task_card_schema.dump(result["tasks"]),
    }), 200


# ── Field-task endpoints (no field_id) ───────────────────────────────────────

@fields_bp.route("/fields/tasks", methods=["GET"])
def get_all_field_tasks():
    """All tasks whose task_category is 'field'."""
    tasks = FieldService.get_all_field_tasks()
    return jsonify(task_card_schema.dump(tasks)), 200


@fields_bp.route("/fields/tasks/pending", methods=["GET"])
def get_pending_field_tasks():
    """All incomplete tasks whose task_category is 'field'."""
    tasks = FieldService.get_pending_field_tasks()
    return jsonify(task_card_schema.dump(tasks)), 200


# ── Single-field endpoints ────────────────────────────────────────────────────

@fields_bp.route("/fields/<int:field_id>", methods=["GET"])
def get_field(field_id):
    """Field detail including all its tasks."""
    field = FieldService.get_field_by_id(field_id)
    if not field:
        return jsonify({"error": "Field not found"}), 404
    return jsonify(field_detail_schema.dump(field)), 200


@fields_bp.route("/fields/<int:field_id>/tasks/pending", methods=["GET"])
def get_pending_tasks_by_field(field_id):
    """Pending tasks for a specific field."""
    field = FieldService.get_field_by_id(field_id)
    if not field:
        return jsonify({"error": "Field not found"}), 404
    tasks = FieldService.get_pending_tasks_by_field_id(field_id)
    return jsonify(task_card_schema.dump(tasks)), 200


@fields_bp.route("/fields/<int:field_id>", methods=["PUT"])
def update_field(field_id):
    field = FieldService.get_field_by_id(field_id)
    if not field:
        return jsonify({"error": "Field not found"}), 404

    data = request.get_json() or {}
    try:
        valid_data = field_create_schema.load(data)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    updated = FieldService.update_field(field_id, valid_data)
    return jsonify(field_detail_schema.dump(updated)), 200


@fields_bp.route("/fields", methods=["POST"])
def create_field():
    data = request.get_json() or {}
    try:
        valid_data = field_create_schema.load(data)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    field = FieldService.create_field(valid_data)
    return jsonify(field_detail_schema.dump(field)), 201


@fields_bp.route("/fields/<int:field_id>", methods=["DELETE"])
def delete_field(field_id):
    field = FieldService.delete_field(field_id)
    if not field:
        return jsonify({"error": "Field not found"}), 404
    return jsonify({"message": "Field deleted successfully"}), 200
