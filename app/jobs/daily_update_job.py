from app.services.field_service import FieldService
from app.agents.coordinator_agent import CoordinatorAgent


class DailyUpdateJob:
    @staticmethod
    def run() -> list[dict]:
        results = []
        payload = FieldService.get_active_fields_with_tasks()
        active_fields = payload["fields"]

        print(f"Found active fields with tasks: {(active_fields)}")

        for field in active_fields:
            print("Processing daily update for field", field)
            result = CoordinatorAgent().handle_daily_system_update(crop_id=field.crop_id, field_id=field.id)

            results.append(result)

        return results