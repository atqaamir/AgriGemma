from app.services.alert_service import AlertService

class AlertAgent:
    def __init__(self):
        self.alert_service = AlertService()

    def generate_alerts(self, user_id, tag):
        return self.alert_service.generate_alerts(user_id, tag=tag)