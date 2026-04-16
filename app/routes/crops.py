from flask import Blueprint, request, jsonify, render_template
from app.services.crop_service import CropService
from app.schemas.crop_schema import CropSchema

crops_bp = Blueprint("crops_bp", __name__)

crop_schema = CropSchema()
crops_schema = CropSchema(many=True)


@crops_bp.route("/", methods=["GET"])
def crops_page():
    return render_template("crops.html")


@crops_bp.route("/crops", methods=["GET"])
def get_crops():
    crops = CropService.get_all_crops()
    return jsonify(crops_schema.dump(crops)), 200


@crops_bp.route("/crops/<int:crop_id>", methods=["GET"])
def get_crop(crop_id):
    crop = CropService.get_crop_by_id(crop_id)

    if not crop:
        return jsonify({"error": "Crop not found"}), 404

    return jsonify(crop_schema.dump(crop)), 200


@crops_bp.route("/crops", methods=["POST"])
def create_crop():
    data = request.get_json()

    errors = crop_schema.validate(data)
    if errors:
        return jsonify(errors), 400

    crop = CropService.create_crop(data)
    return jsonify(crop_schema.dump(crop)), 201

    