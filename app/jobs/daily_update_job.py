from app.services.field_service import field_service
from app.agents.coordinator_agent import CoordinatorAgent


class DailyUpdateJob:
    @staticmethod
    def run() -> list[dict]:
        results = []
        active_fields = field_service.get_active_fields()

        for field in active_fields:
            result = CoordinatorAgent.handle_daily_system_update(field["id"])
            results.append(result)

        return results