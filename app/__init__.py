from flask import Flask
from config import Config
from app.extensions import db, migrate, admin
from flask_admin.contrib.sqla import ModelView
from app.models.crop import Crop
from app.models.field import Field
from app.models.notification import Notification
from app.routes import register_routes
from app.jobs.scheduler import start_scheduler


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    admin.init_app(app)
    admin.add_view(ModelView(Crop, db.session))
    admin.add_view(ModelView(Field, db.session))
    admin.add_view(ModelView(Notification, db.session))
    register_routes(app)

    with app.app_context():
        db.create_all()

    _register_ai_provider()
    start_scheduler(app)

    return app


def _register_ai_provider() -> None:
    """
    Register the AI provider. Set USE_PLACEHOLDER_AI=true in environment to use placeholder.
    This makes it easy to test without Gemma:
        export USE_PLACEHOLDER_AI=true
        flask run
    """
    import os
    from app.services.ai_model_service import ai_model_service

    use_placeholder = os.getenv("USE_PLACEHOLDER_AI", "false").lower() == "true"

    if use_placeholder:
        from app.services.ai_model_service.placeholder_provider import PlaceholderProvider
        ai_model_service.register_provider(PlaceholderProvider())
    else:
        from app.services.ai_model_service.Gemma.gemma_provider import GemmaProvider
        ai_model_service.register_provider(GemmaProvider())