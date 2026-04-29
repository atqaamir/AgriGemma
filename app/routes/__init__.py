from .main import main_bp
from ._page_dashboard import dashboard_bp
from ._page_fields import fields_bp
from ._page_crops import crops_bp
from ._page_tasks import tasks_bp
from .weather import weather_bp
from .chatbot import chatbot_bp



def register_routes(app):
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(fields_bp, url_prefix="/myfields")
    app.register_blueprint(crops_bp, url_prefix="/mycrops")
    app.register_blueprint(tasks_bp, url_prefix="/mytasks")
    app.register_blueprint(weather_bp, url_prefix="/weather")
    app.register_blueprint(chatbot_bp, url_prefix="/chatbot")
