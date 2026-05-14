from app.services.domain_service.notification_service import NotificationService

class NotificationAgent:
    def __init__(self):
        self.notification_service = NotificationService()

    def generate_notifications(self, user_id, tag):
        return self.notification_service.generate_notifications(user_id, tag=tag)