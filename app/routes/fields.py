from flask import Blueprint, request, jsonify
from app.services.field_service import FieldService
from app.schemas.field_schema import FieldSchema

fields_bp = Blueprint("fields_bp", __name__)

fields_schema = FieldSchema(many=True)

@fields_bp.route("/api/fields", methods=["GET"])
def get_fields():
    fields = FieldService.get_all_fields()
    return jsonify(fields_schema.dump(fields)), 200


@fields_bp.route("/api/fields/<int:field_id>", methods=["GET"])
def get_field(field_id):
    field = FieldService.get_field_by_id(field_id)

    if not field:
        return jsonify({"error": "field not found"}), 404

    return jsonify(fields_schema.dump(field)), 200


@fields_bp.route("/api/fields", methods=["POST"])
def create_field():
    data = request.get_json()

    errors = fields_schema.validate(data)
    if errors:
        return jsonify(errors), 400

    field = FieldService.create_field(data)
    return jsonify(fields_schema.dump(field)), 201
