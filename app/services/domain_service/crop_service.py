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

    @staticmethod
    def get_crop_health(crop):
        if crop.health_status == "good":
            return "Healthy"
        elif crop.health_status == "warning":
            return "Needs attention"
        return "At risk"

    @staticmethod
    def needs_irrigation(crop):
        return crop.water_requirement > 50
    
    @staticmethod
    def get_active_crop_for_field(crop, field_id):
        crops = CropRepository.get_all().filter(crop.fields.any(id=field_id), crop.currently_active == True).all()
        return crops[0] if crops else None

    @staticmethod
    def get_currently_active_crops():
        crops = CropRepository.get_all()

        # If repository returns a SQLAlchemy query
        if hasattr(crops, "filter_by"):
            # Check if crops have a 'currently_active' field, if not, return all
            try:
                return crops.filter_by(currently_active=True).all()
            except:
                return crops if isinstance(crops, list) else crops.all()

        # If repository returns a Python list, return all (no filtering available)
        return crops

    @staticmethod
    def get_active_crops_with_tasks():
        crops = CropService.get_currently_active_crops()

        all_tasks = []
        seen_task_ids = set()

        for crop in crops:
            for task in crop.tasks:
                if task.id not in seen_task_ids and task.task_category == 'crop':
                    seen_task_ids.add(task.id)
                    all_tasks.append(task)

        return {
            "crops": crops,
            "tasks": all_tasks,
        }



