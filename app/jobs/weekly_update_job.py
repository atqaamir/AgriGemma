from app.services.field_service import field_service
from app.agents.coordinator_agent import CoordinatorAgent


class WeeklyUpdateJob:
    @staticmethod
    def run() -> list[dict]:
        results = []
        active_fields = field_service.get_active_fields()

        for field in active_fields:
            result = CoordinatorAgent.handle_weekly_planning(field["id"])
            results.append(result)

        return results