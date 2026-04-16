from flask import Blueprint, request, jsonify, render_template
from app.services.field_service import FieldService
from app.schemas.field_schema import FieldSchema

fields_bp = Blueprint("fields_bp", __name__)

field_schema = FieldSchema()
fields_schema = FieldSchema(many=True)

@fields_bp.route("/", methods=["GET"])
def fields_page():
    return render_template("fields.html")

@fields_bp.route("/fields", methods=["GET"])
def get_fields():
    fields = FieldService.get_all_fields()
    dumped = fields_schema.dump(fields)
    print("DUMPED FIELDS:", dumped)
    return jsonify(dumped), 200

@fields_bp.route("/fields/<int:field_id>", methods=["GET"])
def get_field(field_id):
    field = FieldService.get_field_by_id(field_id)
    print(f"Retrieved field: {field}")

    if not field:
        return jsonify({"error": "field not found"}), 404

    return jsonify(field_schema.dump(field)), 200

@fields_bp.route("/fields", methods=["POST"])
def create_field():
    data = request.get_json()

    errors = field_schema.validate(data)
    if errors:
        return jsonify(errors), 400

    field = FieldService.create_field(data)
    return jsonify(field_schema.dump(field)), 201

@fields_bp.route("/fields/active", methods=["GET"])
def get_active_fields():
    fields = FieldService.get_currently_active_fields()
    return jsonify(fields_schema.dump(fields)), 200