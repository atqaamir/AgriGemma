from datetime import timedelta, date
from app.repositories.crop_repository import CropRepository
from app.services.domain_service.task_service import TaskService
from app.rules.vocabulary.crop_names import CropNames
from app.rules.vocabulary.growth_stage import GrowthStage

# Keyed by crop_name_id: 1=Maize, 2=Rice, 3=Cotton
CROP_DURATION_DAYS = {
    1: 120,   # Maize
    2: 180,   # Rice
    3: 220,   # Cotton
}
DEFAULT_DURATION_DAYS = 150


class CropService:

    @staticmethod
    def _calc_harvest_date(crop_name_id, planting_date):
        if not planting_date or not crop_name_id:
            return None
        duration = CROP_DURATION_DAYS.get(crop_name_id, DEFAULT_DURATION_DAYS)
        return planting_date + timedelta(days=duration)

    @staticmethod
    def create_crop(data: dict):
        if data.get('planting_date') and not data.get('expected_harvest_date'):
            data['expected_harvest_date'] = CropService._calc_harvest_date(
                data.get('crop_name_id'), data['planting_date']
            )
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
            # recalculate harvest date if planting date or crop name changed
            if 'planting_date' in data or 'crop_name_id' in data:
                planting = data.get('planting_date') or crop.planting_date
                name_id = data.get('crop_name_id') or crop.crop_name_id
                data['expected_harvest_date'] = CropService._calc_harvest_date(name_id, planting)
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
    def get_active_crops_by_user(user_id: int) -> list:
        """Get active crops for a specific user."""
        crops = CropRepository.get_by_user_id(user_id)
        return [c for c in crops if c.currently_active]

    @staticmethod
    def calculate_growth_progress(crop) -> int:
        """Returns 0-100 percentage of how far through its growth cycle a crop is."""
        if not crop.planting_date or not crop.expected_harvest_date:
            return 0
        today = date.today()
        total_days = (crop.expected_harvest_date - crop.planting_date).days
        elapsed = (today - crop.planting_date).days
        if total_days <= 0 or elapsed <= 0:
            return 0
        return min(round((elapsed / total_days) * 100), 100)

    @staticmethod
    def needs_irrigation(crop) -> bool:
        """Heuristic: flag crops whose water requirement exceeds 700 mm (high demand)."""
        return bool(
            crop.currently_water_requirement and crop.currently_water_requirement > 700.0
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
    def get_vocabulary() -> dict:
        crop_names = [{"id": c.id, "name": c.name} for c in CropNames.query.order_by(CropNames.name).all()]
        growth_stages = [{"id": g.id, "name": g.name} for g in GrowthStage.query.order_by(GrowthStage.id).all()]
        return {"crop_names": crop_names, "growth_stages": growth_stages}

    @staticmethod
    def get_crops_by_user(user_id: int) -> list:
        return CropRepository.get_by_user_id(user_id)

    @staticmethod
    def get_pending_tasks_by_crop_id(crop_id: int) -> list:
        crop = CropRepository.get_by_id(crop_id)
        if not crop:
            return []
        return TaskService.get_pending_tasks_for_crop(crop_id)
