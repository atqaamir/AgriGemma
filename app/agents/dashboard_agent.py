from app.services.dashboard_service import DashboardService

class DashboardAgent:
    def __init__(self):
        self.dashboard_service = DashboardService()

    def refresh_dashboard(self, user_id):
        return self.dashboard_service.refresh_dashboard(user_id)