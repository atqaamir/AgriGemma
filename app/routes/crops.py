from flask import Blueprint, request, jsonify, render_template
from marshmallow import ValidationError

from app.services.domain_service.crop_service import CropService
from app.schemas.crop_schema import (
    CropCardSchema,
    CropDetailSchema,
    MyCropsPageSchema,
    CreateCropSchema,
)
from app.schemas.task_schema import TaskCardSchema

crops_bp = Blueprint("crops_bp", __name__)

crop_card_schema = CropCardSchema(many=True)
crop_detail_schema = CropDetailSchema()
crop_create_schema = CreateCropSchema()
task_card_schema = TaskCardSchema(many=True)
my_crops_page_schema = MyCropsPageSchema()

@crops_bp.route("/", methods=["GET"])
def crops_page():
    return render_template("crops.html")


@crops_bp.route("/crops", methods=["GET"])
def get_crops():
    crops = CropService.get_all_crops()

    all_tasks = []
    for crop in crops:
        all_tasks.extend([t for t in crop.tasks if t.task_category == 'crop'])

    unique_tasks = list({task.id: task for task in all_tasks}.values())

    result = {
        "crop_cards": crop_card_schema.dump(crops),
        "crop_task_cards": task_card_schema.dump(unique_tasks),
    }

    return jsonify(result), 200


@crops_bp.route("/crops/<int:crop_id>", methods=["GET"])
def get_crop(crop_id):
    crop = CropService.get_crop_by_id(crop_id)

    if not crop:
        return jsonify({"error": "Crop not found"}), 404

    return jsonify(crop_detail_schema.dump(crop)), 200


@crops_bp.route("/crops/active", methods=["GET"])
def get_active_crops():
    result = CropService.get_active_crops_with_tasks()

    response = {
        "crop_cards": crop_card_schema.dump(result["crops"]),
        "crop_task_cards": task_card_schema.dump(result["tasks"]),
    }

    return jsonify(response), 200


@crops_bp.route("/crops", methods=["POST"])
def create_crop():
    data = request.get_json() or {}

    try:
        valid_data = crop_create_schema.load(data)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    crop = CropService.create_crop(valid_data)
    return jsonify(crop_detail_schema.dump(crop)), 201