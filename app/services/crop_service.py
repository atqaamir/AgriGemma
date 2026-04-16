from app.repositories.crop_repository import CropRepository

class CropService:

    @staticmethod
    def create_crop(data):
        return CropRepository.create(data)

    @staticmethod
    def get_all_crops():
        return CropRepository.get_all()

    @staticmethod
    def get_crop_by_id(crop_id):
        return CropRepository.get_by_id(crop_id)

    @staticmethod
    def delete_crop(crop_id):
        crop = CropRepository.get_by_id(crop_id)
        if crop:
            CropRepository.delete(crop)
        return crop

    def get_crop_health(crop):
        if crop.health_status == "good":
            return "Healthy"
        elif crop.health_status == "warning":
            return "Needs attention"
        return "At risk"

    def needs_irrigation(crop):
            return crop.water_requirement > 50



