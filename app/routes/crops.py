from flask import Blueprint, request, jsonify
from app.services.crop_service import CropService
from app.schemas.crop_schema import CropSchema

crop_bp = Blueprint('crops', __name__)
schema = CropSchema()
many_schema = CropSchema(many=True)

@crop_bp.route('/crops', methods=['POST'])
def create_crop():
    data = schema.load(request.json)
    crop = CropService.create_crop(data)
    return schema.dump(crop), 201

@crop_bp.route('/crops', methods=['GET'])
def get_crops():
    crops = CropService.get_all_crops()
    return many_schema.dump(crops)

@crop_bp.route('/crops/<int:id>', methods=['GET'])
def get_crop(id):
    crop = CropService.get_crop_by_id(id)
    return schema.dump(crop)