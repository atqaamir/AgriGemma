import logging
from flask import Flask
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
from app.extensions import db, migrate, admin
from flask_admin.contrib.sqla import ModelView
from app.models.crop import Crop
from app.models.field import Field
from app.models.notification import Notification
from app.models.task import Task
from app.rules.vocabulary.crop_names import CropNames
from app.rules.vocabulary.growth_stage import GrowthStage
from app.rules.vocabulary.soil_type import Soil_Type
from app.rules.vocabulary.water_source import WaterSource
from app.rules.rulebooks.action_rules.soil_action_rulebook import SoilActionRulebook
from app.rules.rulebooks.compatibility_rules.crop_soil_compatibility_rulebook import CropSoilCompatibilityRulebook
from app.rules.rulebooks.threshold_rules.irrigation_calender_rulebook import IrrigationCalenderRulebook
from app.models.seasonal_plan import SeasonalPlan
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
    admin.add_view(ModelView(CropNames, db.session))
    admin.add_view(ModelView(WaterSource, db.session))
    admin.add_view(ModelView(IrrigationCalenderRulebook, db.session))
    admin.add_view(ModelView(CropSoilCompatibilityRulebook, db.session))
    admin.add_view(ModelView(SoilActionRulebook, db.session))
    admin.add_view(ModelView(SeasonalPlan, db.session))

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
        USE_LITERT=true           → Gemma via MediaPipe LiteRT (.task file, mobile/Linux)
        USE_GOOGLE_AI=true        → Dual Gemma 4 setup (Kaggle hackathon mode):
                                      Chatbot      : Google AI Studio cloud  (gemma-4-26b-a4b-it)
                                      Intelligence : Ollama local on-device  (gemma4)
                                    Requires: GOOGLE_API_KEY  (free at aistudio.google.com/apikey)
                                              Ollama running  (ollama pull gemma4)
                                    Optional: GOOGLE_AI_MODEL (default: gemma-4-26b-a4b-it)
                                              OLLAMA_MODEL    (default: gemma4)
        default                   → Ollama local inference only (gemma4)
                                    Install: https://ollama.com/download
                                    Then:    ollama pull gemma4
    """
    import os
    from app.services.ai_model_service import ai_model_service

    if os.getenv("USE_PLACEHOLDER_AI", "false").lower() == "true":
        from app.services.ai_model_service.placeholder_provider import PlaceholderProvider
        ai_model_service.register_provider(PlaceholderProvider())

    elif os.getenv("USE_LITERT", "false").lower() == "true":
        from app.services.ai_model_service.Gemma.gemma_provider import GemmaProvider
        ai_model_service.register_provider(GemmaProvider())

    elif os.getenv("USE_GOOGLE_AI", "false").lower() == "true":
        # Chatbot  → Google AI Studio (Gemma 4 cloud, streaming, low-latency)
        # Intelligence → Ollama local (Gemma 4 on-device: task/notification/summary prompts)
        #   This dual setup means background intelligence works fully OFFLINE — farmers
        #   in low-connectivity areas still get task explanations and alerts.
        from app.services.ai_model_service.Gemma.google_ai_provider import GoogleAIProvider
        from app.services.ai_model_service.Gemma.ollama_provider import OllamaProvider
        chatbot_model = os.getenv("GOOGLE_AI_MODEL", "gemma-4-26b-a4b-it")
        ai_model_service.register_provider(GoogleAIProvider(model=chatbot_model))
        ai_model_service.register_fast_provider(OllamaProvider())   # local Gemma 4

    else:
        from app.services.ai_model_service.Gemma.ollama_provider import OllamaProvider
        ai_model_service.register_provider(OllamaProvider())