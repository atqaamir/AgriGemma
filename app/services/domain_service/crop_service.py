from app.repositories.crop_repository import CropRepository
from app.services.domain_service.task_service import TaskService


class CropService:

    @staticmethod
    def create_crop(data: dict):
        return CropRepository.create(data)

    @staticmethod
    def delete_crop(crop_id: int):
        crop = CropRepository.get_by_id(crop_id)
        if crop:
            CropRepository.delete(crop)
        return crop

    @staticmethod
    def update_crop(crop_id: int, data: dict):
        crop = CropRepository.get_by_id(crop_id)
        if crop:
            CropRepository.update(crop, data)
        return crop

    @staticmethod
    def get_all_crops():
        return CropRepository.get_all()

    @staticmethod
    def get_crop_by_id(crop_id: int):
        return CropRepository.get_by_id(crop_id)

    @staticmethod
    def get_active_crops() -> list:
        return CropRepository.get_all().filter_by(currently_active=True).all()

    @staticmethod
    def needs_irrigation(crop) -> bool:
        """Heuristic: flag crops whose water requirement exceeds the threshold."""
        return bool(
            crop.currently_water_requirement and crop.currently_water_requirement > 5.0
        )

    @staticmethod
    def get_pending_tasks_active_crop() -> list:
        active_crops = CropService.get_active_crops()
        result = []
        for crop in active_crops:
            result.extend(TaskService.get_pending_tasks_for_crop(crop.id))
        return result

    @staticmethod
    def get_all_croptasks() -> list:
        all_tasks = []
        for crop in CropRepository.get_all():
            all_tasks.extend(TaskService.get_pending_tasks_for_crop(crop.id))
        return all_tasks

    @staticmethod
    def get_pending_tasks_by_crop_id(crop_id: int) -> list:
        crop = CropRepository.get_by_id(crop_id)
        if not crop:
            return []
        return TaskService.get_pending_tasks_for_crop(crop_id)
