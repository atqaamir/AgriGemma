from .main import main_bp
from .fields import fields_bp
from .crops import crops_bp
from .tasks import tasks_bp
from .weather import weather_bp
from .chatbot import chatbot_bp

def register_routes(app):
    app.register_blueprint(main_bp)
    app.register_blueprint(fields_bp, url_prefix="/fields")
    app.register_blueprint(crops_bp, url_prefix="/crops")
    app.register_blueprint(tasks_bp, url_prefix="/tasks")
    app.register_blueprint(weather_bp, url_prefix="/weather")
    app.register_blueprint(chatbot_bp, url_prefix="/chatbot")
    app.register_blueprint(dashboard_bp)