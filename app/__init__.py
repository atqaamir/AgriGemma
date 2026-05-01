from flask import Flask
from config import Config
from app.extensions import db, migrate, admin
from flask_admin.contrib.sqla import ModelView
from app.models.crop import Crop
from app.models.field import Field
from app.models.notification import Notification
from app.rules.vocabulary.crop_names import CropNames
from app.rules.vocabulary.growth_stage import GrowthStage
from app.rules.vocabulary.soil_type import Soil_Type
from app.rules.vocabulary.water_source import WaterSource
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
    Provider selection via environment variables:

        USE_PLACEHOLDER_AI=true   → rule-based placeholder (no model needed)
        USE_LITERT=true           → Gemma 4 via MediaPipe LiteRT (.task file, mobile/Linux)
        default                   → Ollama local inference (gemma3:4b)
                                    Install: https://ollama.com/download
                                    Then:    ollama pull gemma3:4b
    """
    import os
    from app.services.ai_model_service import ai_model_service

    if os.getenv("USE_PLACEHOLDER_AI", "false").lower() == "true":
        from app.services.ai_model_service.placeholder_provider import PlaceholderProvider
        ai_model_service.register_provider(PlaceholderProvider())

    elif os.getenv("USE_LITERT", "false").lower() == "true":
        from app.services.ai_model_service.Gemma.gemma_provider import GemmaProvider
        ai_model_service.register_provider(GemmaProvider())

    else:
        from app.services.ai_model_service.ollama_provider import OllamaProvider
        ai_model_service.register_provider(OllamaProvider())