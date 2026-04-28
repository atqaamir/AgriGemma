from app.services.field_service import FieldService
from app.agents.coordinator_agent import CoordinatorAgent


class WeeklyUpdateJob:
    @staticmethod
    def run() -> list[dict]:
        results = []

        payload = FieldService.get_active_fields_with_tasks()
        active_fields = payload["fields"]

        for field in active_fields:
            result = CoordinatorAgent().handle_weekly_planning(crop_id=field.crop_id, field_id=field.id)
            results.append(result)

        return results