from app.services.field_service import FieldService
from app.services.alert_service import AlertService


class AlertScanJob:
    @staticmethod
    def run() -> list[dict]:
        results = []
        payload = FieldService.get_active_fields_with_tasks()
        active_fields = payload["fields"]

        for field in active_fields:
            alerts = AlertService().scan_and_create_alerts(field.id)
            results.append({
                "field_id": field["id"],
                "alerts_created": alerts,
            })

        return results