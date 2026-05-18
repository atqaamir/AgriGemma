"""
Intent-aware context builder for the farm chatbot.

build_chatbot_context(user_id, intent_result) -> dict

Instead of fetching ALL farm data and passing it to Gemma (which wastes tokens
and degrades answer quality), this module fetches ONLY the data sources that
are relevant to the farmer's intent.

Architecture:
  IntentResult.primary → ContextSpec → selective DB fetches → flat context dict

The context dict is consumed by components.py to render the prompt block.
The dashboard pipeline continues to use ContextAggregationService (full fetch).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field as dc_field
from datetime import date

from app.services.intelligence_service.intent.intent_classifier import FarmIntent, IntentResult

logger = logging.getLogger(__name__)


@dataclass
class ContextSpec:
    """Declares which data sources a given intent requires."""
    needs_fields:   bool              = False
    needs_crops:    bool              = True   # always cheap
    needs_tasks:    bool              = False
    task_types:     frozenset[str]    = dc_field(default_factory=frozenset)
    needs_weather:  bool              = True
    forecast_days:  int               = 2
    needs_alerts:   bool              = False
    needs_rules:    bool              = False
    needs_climate:  bool              = False
    needs_seasonal: bool              = False
    max_tasks:      int               = 6
    max_fields:     int               = 4
    max_crops:      int               = 4


# ── Per-intent context specs ───────────────────────────────────────────────────

_SPECS: dict[FarmIntent, ContextSpec] = {
    FarmIntent.IRRIGATION: ContextSpec(
        needs_fields=True,
        needs_crops=True,
        needs_tasks=True,   task_types=frozenset({"irrigation"}),
        needs_weather=True, forecast_days=3,
        needs_alerts=True,
        needs_rules=True,
        max_tasks=5,
    ),
    FarmIntent.WEATHER: ContextSpec(
        needs_fields=False,
        needs_crops=True,
        needs_tasks=False,
        needs_weather=True, forecast_days=5,
        needs_alerts=False,
        needs_rules=False,
        needs_climate=True,
        max_crops=3,
    ),
    FarmIntent.HARVEST: ContextSpec(
        needs_fields=False,
        needs_crops=True,
        needs_tasks=True,   task_types=frozenset({"harvest", "general"}),
        needs_weather=True, forecast_days=4,
        needs_alerts=False,
        needs_rules=False,
        needs_climate=True,
        needs_seasonal=True,
        max_tasks=4,
    ),
    FarmIntent.FERTILIZATION: ContextSpec(
        needs_fields=False,
        needs_crops=True,
        needs_tasks=True,   task_types=frozenset({"fertilization"}),
        needs_weather=True, forecast_days=2,
        needs_alerts=False,
        needs_rules=True,
        max_tasks=4,
    ),
    FarmIntent.SOIL: ContextSpec(
        needs_fields=True,
        needs_crops=True,
        needs_tasks=False,
        needs_weather=False,
        needs_alerts=False,
        needs_rules=True,
        max_fields=4,
    ),
    FarmIntent.TASK: ContextSpec(
        needs_fields=False,
        needs_crops=False,
        needs_tasks=True,
        needs_weather=True, forecast_days=2,
        needs_alerts=False,
        needs_rules=False,
        max_tasks=8,
    ),
    FarmIntent.ALERT: ContextSpec(
        needs_fields=True,
        needs_crops=True,
        needs_tasks=True,   task_types=frozenset({"inspection", "general"}),
        needs_weather=True, forecast_days=2,
        needs_alerts=True,
        needs_rules=True,
        max_tasks=4,
    ),
    FarmIntent.PLANTING: ContextSpec(
        needs_fields=True,
        needs_crops=True,
        needs_tasks=False,
        needs_weather=True, forecast_days=5,
        needs_alerts=False,
        needs_rules=True,
        needs_climate=True,
        needs_seasonal=True,
        max_fields=4,
        max_crops=6,
    ),
    FarmIntent.GENERAL: ContextSpec(
        needs_fields=False,
        needs_crops=True,
        needs_tasks=True,
        needs_weather=True, forecast_days=2,
        needs_alerts=False,
        needs_rules=False,
        max_tasks=3,
        max_crops=4,
    ),
    FarmIntent.GREETING: ContextSpec(
        needs_crops=False,
        needs_weather=False,
    ),
}


# ── Public entry points ────────────────────────────────────────────────────────

def build_notification_context(user_id: int) -> dict:
    """
    Minimal context for the notification / alert pipeline.

    Fetches only what alert detection and the AI explanation prompt actually need:
      - farmer_name  → personalises the AI explanation
      - weather      → temperature + rainfall thresholds for alert detection
      - fields       → health_status for field-level alerts
      - crops        → crop_name_id, growth_stage_id, moisture_level for rulebook lookups
      - rules        → rulebook text injected into the AI explanation prompt

    Does NOT fetch: tasks, climate, seasonal plan, weekly plan, existing alerts.
    Returns a dict that is compatible with both _detect_from_context() (expects
    farm.active_crops_data / farm.active_fields_data) and build_alerts_batch_explanation_prompt()
    (expects farmer_name, weather, rules).
    """
    ctx: dict = {}

    ctx["farmer_name"] = _safe("farmer_name", _fetch_farmer_name, user_id)
    ctx["weather"]     = _safe("weather", _fetch_weather, user_id) or {}

    fields = _safe("fields", _fetch_fields) or []
    crops  = _safe("crops",  _fetch_crops)  or []

    # Keep the nested structure that _detect_from_context() expects
    ctx["farm"] = {
        "active_fields_data": fields,
        "active_crops_data":  crops,
    }

    # Rules only for the crops we have (for the AI explanation)
    ctx["rules"] = _safe("rules", _fetch_rules, crops, ctx["weather"]) or ""

    return ctx


def build_chatbot_context(user_id: int, intent_result: IntentResult) -> dict:
    """
    Fetch only the data sources needed for this intent combination.
    Returns a flat dict consumed by components.py renderers.
    """
    spec  = _merge_specs(intent_result)
    today = date.today()
    ctx: dict = {}

    ctx["farmer_name"] = _safe("farmer_name", _fetch_farmer_name, user_id)
    ctx["intent"]      = intent_result.primary.value

    if spec.needs_weather:
        weather = _safe("weather", _fetch_weather, user_id) or {}
        if "forecast" in weather:
            weather = dict(weather)
            weather["forecast"] = weather["forecast"][: spec.forecast_days]
        ctx["weather"] = weather

    if spec.needs_fields:
        ctx["fields"] = (_safe("fields", _fetch_fields) or [])[: spec.max_fields]

    if spec.needs_crops:
        ctx["crops"] = (_safe("crops", _fetch_crops) or [])[: spec.max_crops]

    if spec.needs_tasks:
        ctx["tasks"] = _safe(
            "tasks", _fetch_tasks, today, spec.task_types
        ) or {}

    if spec.needs_alerts:
        raw_fields = _safe("fields_raw", _fetch_fields_raw) or []
        ctx["alerts"] = (_safe("alerts", _fetch_alerts, raw_fields) or [])[:5]

    if spec.needs_rules:
        crops   = ctx.get("crops") or []
        weather = ctx.get("weather") or {}
        ctx["rules"] = _safe("rules", _fetch_rules, crops, weather) or ""

    if spec.needs_climate:
        ctx["climate"] = _safe("climate", _fetch_climate, user_id) or {}

    if spec.needs_seasonal:
        ctx["seasonal_plan"] = _safe("seasonal", _fetch_seasonal, user_id) or {}

    return ctx


# ── Spec merging ───────────────────────────────────────────────────────────────

def _merge_specs(intent_result: IntentResult) -> ContextSpec:
    """
    Merge primary + secondary intent specs.
    Booleans are OR'd; numeric limits take the maximum.
    """
    base = _SPECS.get(intent_result.primary, _SPECS[FarmIntent.GENERAL])
    if not intent_result.secondary:
        return base

    merged = ContextSpec(
        needs_fields=base.needs_fields,
        needs_crops=base.needs_crops,
        needs_tasks=base.needs_tasks,
        task_types=base.task_types,
        needs_weather=base.needs_weather,
        forecast_days=base.forecast_days,
        needs_alerts=base.needs_alerts,
        needs_rules=base.needs_rules,
        needs_climate=base.needs_climate,
        needs_seasonal=base.needs_seasonal,
        max_tasks=base.max_tasks,
        max_fields=base.max_fields,
        max_crops=base.max_crops,
    )
    for intent in intent_result.secondary:
        s = _SPECS.get(intent, _SPECS[FarmIntent.GENERAL])
        merged.needs_fields   = merged.needs_fields   or s.needs_fields
        merged.needs_crops    = merged.needs_crops    or s.needs_crops
        merged.needs_tasks    = merged.needs_tasks    or s.needs_tasks
        merged.task_types     = merged.task_types     | s.task_types
        merged.needs_weather  = merged.needs_weather  or s.needs_weather
        merged.forecast_days  = max(merged.forecast_days, s.forecast_days)
        merged.needs_alerts   = merged.needs_alerts   or s.needs_alerts
        merged.needs_rules    = merged.needs_rules    or s.needs_rules
        merged.needs_climate  = merged.needs_climate  or s.needs_climate
        merged.needs_seasonal = merged.needs_seasonal or s.needs_seasonal
        merged.max_tasks      = max(merged.max_tasks, s.max_tasks)
        merged.max_fields     = max(merged.max_fields, s.max_fields)
        merged.max_crops      = max(merged.max_crops, s.max_crops)

    return merged


# ── Safe wrapper ───────────────────────────────────────────────────────────────

def _safe(name: str, fn, *args):
    try:
        return fn(*args)
    except Exception as exc:
        logger.warning("context_builder[%s]: %s", name, exc)
        return None


# ── Data fetchers ──────────────────────────────────────────────────────────────

def _fetch_farmer_name(user_id: int) -> str:
    from app.services.domain_service.user_service import UserService
    user = UserService.get_user_by_id(user_id)
    return (user.name or "Farmer") if user else "Farmer"


def _fetch_weather(user_id: int) -> dict:
    from app.services.weather_service.forecast_service import ForecastService
    return ForecastService.get_current_summary(user_id) or {}


def _fetch_fields() -> list:
    from app.repositories.field_repository import FieldRepository
    return [
        {
            "id":           f.id,
            "name":         f.name,
            "health_status": f.health_status,
            "moisture_level": f.moisture_level,
            "heat_level":   f.heat_level,
            "stress_risk":  f.stress_risk,
            "disease_risk": f.disease_risk,
        }
        for f in FieldRepository.get_all_active()
    ]


def _fetch_fields_raw() -> list:
    from app.repositories.field_repository import FieldRepository
    return FieldRepository.get_all_active()


def _fetch_crops() -> list:
    from app.services.domain_service.crop_service import CropService
    return [
        {
            "id":             c.id,
            "name":           c.name,
            "growth_stage":   c.growth_stage,
            "health_status":  c.current_health_status,
            "water_requirement": c.currently_water_requirement,
            "crop_name_id":   c.crop_name_id,
            "growth_stage_id": c.current_growth_stage_id,
            "soil_type_id":   c.field.soil_type_id if c.field else None,
            "moisture_level": c.field.moisture_level if c.field else None,
            "field_name":     c.field.name if c.field else None,
        }
        for c in CropService.get_active_crops()
    ]


def _fetch_tasks(today: date, type_filter: frozenset[str]) -> dict:
    from app.repositories.task_repository import TaskRepository
    pending = list(TaskRepository.get_pending())

    if type_filter:
        filtered = [t for t in pending if t.task_type in type_filter]
        if filtered:
            pending = filtered

    overdue  = [t for t in pending if t.due_date and t.due_date < today]
    critical = [t for t in pending if t.priority == "critical"]

    # Prioritise: overdue → critical → high → due date
    def _sort_key(t):
        is_overdue  = bool(t.due_date and t.due_date < today)
        is_critical = t.priority == "critical"
        is_high     = t.priority == "high"
        return (not is_overdue, not is_critical, not is_high, t.due_date or date.max)

    pending.sort(key=_sort_key)

    return {
        "pending_count":       len(pending),
        "overdue_count":       len(overdue),
        "critical_count":      len(critical),
        "high_priority_count": sum(1 for t in pending if t.priority == "high"),
        "pending_list": [
            {
                "title":       t.title,
                "priority":    t.priority,
                "task_type":   t.task_type,
                "due_date":    str(t.due_date) if t.due_date else None,
                "field_name":  t.field.name if t.field else None,
                "crop_name":   t.crop.name if t.crop else None,
                "is_overdue":  bool(t.due_date and t.due_date < today),
                "description": t.description,
            }
            for t in pending
        ],
    }


def _fetch_alerts(active_fields: list) -> list:
    from app.services.domain_service.notification_service import NotificationService
    svc = NotificationService()
    seen, result = set(), []
    for f in active_fields:
        for a in svc.get_active_alerts(f.id):
            msg = a.get("message", "")
            if msg not in seen:
                result.append(a)
                seen.add(msg)
    return result


def _fetch_rules(crops: list, weather: dict) -> str:
    from app.services.rules_context_service import RulesContextService
    return RulesContextService.build_for_crops(crops, weather)


def _fetch_climate(user_id: int) -> dict:
    from app.services.weather_service.forecast_service import ForecastService
    return ForecastService.get_climate_context(user_id) or {}


def _fetch_seasonal(user_id: int) -> dict:
    from app.services.seasonal_planner_service import SeasonalPlannerService
    plan = SeasonalPlannerService.get_active_plan(user_id)
    if not plan:
        return {}
    entries = plan.entries or []
    return {
        "growth_stage_id": plan.growth_stage_id,
        "entries": [
            {
                "crop_id":              e.crop_name_id,
                "sowing":               e.sowing,
                "harvesting":           e.harvesting,
                "irrigation_frequency": e.irrigation_frequency,
                "adjustments":          e.adjustments_to_make,
            }
            for e in entries
        ],
    }
