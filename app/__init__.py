import logging
from flask import Flask
from config import Config
from app.utils import clock, demo_flags

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
from app.models.seasonal_plan import SeasonalPlanEntry
from app.models.weekly_plan import WeeklyPlan, WeeklyPlanEntry
from app.models.weather_forecast import WeatherForecast
from app.models.weather import Weather
from app.rules.rulebooks.threshold_rules.irrigation_frequency_rulebook import IrrigationFrequencyRulebook
from app.routes import register_routes
from app.jobs.scheduler import start_scheduler


def create_app():
    # A non-empty invalid DEMO_TODAY stops startup here; empty means the real date.
    clock.demo_today()

    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    # Flask-Admin gives full edit access without login: only when DEMO_ADMIN_ENABLED=true.
    if demo_flags.admin_enabled():
        admin.init_app(app)
        admin.add_view(ModelView(Crop, db.session))
        admin.add_view(ModelView(Field, db.session))
        admin.add_view(ModelView(Task, db.session))
        class ReadOnlyNotificationView(ModelView):
            can_delete = False
            can_create = False
            can_edit   = False
            column_list = ("id", "user_id", "notification_type", "is_read", "title", "message", "created_at")
            column_default_sort = ("created_at", True)
        admin.add_view(ReadOnlyNotificationView(Notification, db.session))
        admin.add_view(ModelView(CropNames, db.session))
        admin.add_view(ModelView(WaterSource, db.session))
        admin.add_view(ModelView(IrrigationCalenderRulebook, db.session))
        admin.add_view(ModelView(CropSoilCompatibilityRulebook, db.session))
        admin.add_view(ModelView(SoilActionRulebook, db.session))
        admin.add_view(ModelView(SeasonalPlan, db.session))
        admin.add_view(ModelView(SeasonalPlanEntry, db.session))
        admin.add_view(ModelView(WeeklyPlan, db.session))
        admin.add_view(ModelView(WeeklyPlanEntry, db.session))
        admin.add_view(ModelView(WeatherForecast, db.session))
        admin.add_view(ModelView(Weather, db.session, endpoint="weather_admin"))
        admin.add_view(ModelView(GrowthStage, db.session))
        admin.add_view(ModelView(IrrigationFrequencyRulebook, db.session))

    register_routes(app)

    @app.route("/health")
    def health():
        # Uptime ping target (keeps Render awake); no database access.
        return "ok", 200, {"Content-Type": "text/plain; charset=utf-8"}

    @app.route("/favicon.ico")
    def favicon():
        # Browsers ask for /favicon.ico on every page; serve the SVG leaf (no 404 in the console).
        return app.send_static_file("favicon.svg"), 200, {"Content-Type": "image/svg+xml",
                                                          "Cache-Control": "public, max-age=86400"}

    @app.context_processor
    def inject_current_user():
        # No auth yet — hardcoded to user 1. Replace with session/flask-login when auth is added.
        return {"current_user_id": 1}

    @app.context_processor
    def inject_demo_admin():
        return {"demo_admin_enabled": demo_flags.admin_enabled()}

    @app.context_processor
    def inject_chat_provider():
        return {"chat_provider": _chat_provider_kind()}

    @app.context_processor
    def inject_app_today():
        demo = clock.demo_today()
        return {"app_today": clock.today().isoformat(), "demo_today": demo,
                "demo_season": clock.cropping_season(demo) if demo else None}

    with app.app_context():
        db.create_all()

    _register_ai_provider()
    start_scheduler(app)

    return app


def _chat_provider_kind() -> str:
    """Which provider answers the chat, in the same order as _register_ai_provider():
    "placeholder", "local" (LiteRT or Ollama on the device) or "google"."""
    import os
    flag = lambda name, default="false": os.getenv(name, default).lower() == "true"
    if flag("USE_PLACEHOLDER_AI"):
        return "placeholder"
    if flag("USE_LITERT"):
        return "local"
    if flag("USE_GOOGLE_AI"):
        return "google"          # the chatbot always uses Google AI in this mode
    return "local"               # default: Ollama


def _register_ai_provider() -> None:
    """
    Provider selection via environment variables:

        USE_PLACEHOLDER_AI=true   → rule-based placeholder (no model needed)
        USE_LITERT=true           → Gemma via MediaPipe LiteRT (.task file, mobile/Linux)
        USE_GOOGLE_AI=true        → Chatbot always uses Google AI Studio.
                                    Intelligence provider depends on OLLAMA_ENABLED:
                                      OLLAMA_ENABLED=true  (default): Dual setup —
                                        Chatbot      : Google AI Studio cloud  (gemma-4-26b-a4b-it)
                                        Intelligence : Ollama local on-device  (gemma4)
                                      OLLAMA_ENABLED=false: Google AI for everything —
                                        Chatbot      : Google AI Studio cloud
                                        Intelligence : Google AI Studio cloud (JSON mode)
                                    Requires: GOOGLE_API_KEY  (free at aistudio.google.com/apikey)
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
        from app.services.ai_model_service.Gemma.google_ai_provider import GoogleAIProvider
        google_provider = GoogleAIProvider(model=os.getenv("GOOGLE_AI_MODEL", "gemma-4-26b-a4b-it"))

        ai_model_service.register_provider(google_provider)  # chatbot always uses Google AI

        if os.getenv("OLLAMA_ENABLED", "true").lower() == "false":
            # Ollama disabled — intelligence also uses Google AI
            ai_model_service.register_fast_provider(google_provider)
        else:
            # Ollama enabled — intelligence runs locally on Ollama
            from app.services.ai_model_service.Gemma.ollama_provider import OllamaProvider
            ai_model_service.register_fast_provider(OllamaProvider())

    else:
        from app.services.ai_model_service.Gemma.ollama_provider import OllamaProvider
        ai_model_service.register_provider(OllamaProvider())