"""
Builds a compact rulebook snapshot for the active crops on a farm.

The snapshot is injected into Gemma's prompt so it can cite specific rules
when explaining task recommendations — e.g. why irrigation is needed in May.

All lookups are wrapped in try/except so a missing or unseeded rulebook
table never breaks the chatbot.
"""
import logging
from datetime import date

from app.services.rule_base_service import rule_base_service
from app.rules.vocabulary.mappings import SEASON_MONTHS, get_id_maps

logger = logging.getLogger(__name__)

_SEASON_ID_MAP = get_id_maps()["Season"]   # {"Rainy": 1, "Winter": 2, ...}


def _current_season_id(month: int) -> int:
    for name, rng in SEASON_MONTHS.items():
        start, end = rng["start"], rng["end"]
        if start <= end:
            if start <= month <= end:
                return _SEASON_ID_MAP[name]
        else:                               # wraps year, e.g. Winter Nov–Mar
            if month >= start or month <= end:
                return _SEASON_ID_MAP[name]
    return _SEASON_ID_MAP.get("Summer", 3)


def _moisture_band(pct: float) -> str:
    if pct < 30:
        return "below_30"
    if pct <= 60:
        return "30_60"
    return "above_60"


def _rainfall_band(mm: float) -> str:
    if mm < 10:
        return "below_10"
    if mm <= 50:
        return "10_50"
    return "above_50"


class RulesContextService:

    @staticmethod
    def build_for_crops(crops_data: list, weather: dict) -> str:
        """
        Return a formatted rules block ready for injection into the Gemma prompt.

        crops_data — list of dicts, each with keys:
            name, growth_stage, crop_name_id, growth_stage_id,
            soil_type_id, moisture_level
        weather — the weather sub-dict from ContextAggregationService
        """
        if not crops_data:
            return ""

        month = date.today().month
        season_id = _current_season_id(month)
        rainfall_mm = weather.get("current", {}).get("rainfall_mm", 0.0)

        sections = []

        for crop in crops_data:
            crop_id  = crop.get("crop_name_id")
            stage_id = crop.get("growth_stage_id")
            soil_id  = crop.get("soil_type_id")
            moisture = crop.get("moisture_level") or 0.0
            label    = f"{crop.get('name', '?')} ({crop.get('growth_stage', '?')} stage)"

            if not crop_id:
                continue

            lines = [label]

            # -- Irrigation frequency ------------------------------------------
            try:
                freq = (
                    rule_base_service.get_irrigation_frequency_by_crop_stage_soil(
                        crop_id, stage_id, soil_id
                    )
                    if stage_id and soil_id else None
                )
                if freq and freq.recommended_frequency:
                    lines.append(
                        f"  Irrigation frequency rule: every {freq.recommended_frequency} days"
                    )
            except Exception as exc:
                logger.debug("rules_ctx: irrigation_freq — %s", exc)

            # -- Optimal moisture range ----------------------------------------
            try:
                wc = (
                    rule_base_service.get_water_climate_by_crop_stage_soil(
                        crop_id, stage_id, soil_id
                    )
                    if stage_id and soil_id else None
                )
                if wc and wc.soil_moisture_min is not None:
                    lines.append(
                        f"  Optimal soil moisture: {wc.soil_moisture_min:.0f}–{wc.soil_moisture_max:.0f}%"
                        f"  (field is at {moisture:.0f}% right now)"
                    )
            except Exception as exc:
                logger.debug("rules_ctx: water_climate — %s", exc)

            # -- Soil moisture action for current reading ----------------------
            try:
                m_action = rule_base_service.get_soil_moisture_action_by_crop_and_range(
                    crop_id, _moisture_band(moisture)
                )
                if m_action:
                    steps = [s.strip() for s in m_action.actions.split(";") if s.strip()]
                    lines.append(f"  Soil moisture ({_moisture_band(moisture)}): {m_action.reasoning}")
                    if steps:
                        lines.append("    Actions: " + "; ".join(steps[:3]))
            except Exception as exc:
                logger.debug("rules_ctx: soil_moisture_action — %s", exc)

            # -- Rainfall action for current forecast --------------------------
            try:
                r_action = rule_base_service.get_rainfall_action_by_crop_and_range(
                    crop_id, _rainfall_band(rainfall_mm)
                )
                if r_action:
                    lines.append(
                        f"  Rainfall rule ({_rainfall_band(rainfall_mm)} mm): {r_action.reasoning}"
                    )
            except Exception as exc:
                logger.debug("rules_ctx: rainfall_action — %s", exc)

            # -- Season action -------------------------------------------------
            try:
                s_action = rule_base_service.get_season_action_by_crop_and_season(
                    crop_id, season_id
                )
                if s_action:
                    lines.append(f"  Season rule: {s_action.reasoning}")
            except Exception as exc:
                logger.debug("rules_ctx: season_action — %s", exc)

            if len(lines) > 1:          # at least one rule was found
                sections.append("\n".join(lines))

        if not sections:
            return ""

        return (
            "RULEBOOK DATA (cite these numbers when explaining why a task was created):\n"
            + "\n\n".join(sections)
        )
