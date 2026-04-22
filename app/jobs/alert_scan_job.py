from app.services.field_service import field_service
from app.services.alert_service import alert_service


class AlertScanJob:
    @staticmethod
    def run() -> list[dict]:
        results = []
        active_fields = field_service.get_active_fields()

        for field in active_fields:
            alerts = alert_service.scan_and_create_alerts(field["id"])
            results.append({
                "field_id": field["id"],
                "alerts_created": alerts,
            })

        return results