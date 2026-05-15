from ._page_dashboard import dashboard_bp
from ._page_fields import fields_bp
from ._page_crops import crops_bp
from ._page_tasks import tasks_bp
from ._page_seasonal_plan import seasonal_plan_bp
from .weather import weather_bp
from .chatbot import chatbot_bp
from .notifications import notifications_bp

from .test_ai import test_ai_bp


def register_routes(app):
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(fields_bp, url_prefix="/myfields")
    app.register_blueprint(crops_bp, url_prefix="/mycrops")
    app.register_blueprint(tasks_bp, url_prefix="/mytasks")
    app.register_blueprint(seasonal_plan_bp)
    app.register_blueprint(weather_bp, url_prefix="/weather")
    app.register_blueprint(chatbot_bp, url_prefix="/chatbot")
    app.register_blueprint(notifications_bp, url_prefix="/notifications")
    app.register_blueprint(test_ai_bp, url_prefix="/test/ai")
