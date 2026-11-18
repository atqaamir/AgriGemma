"""
Task and notification intelligence prompts — Gemma 4 optimized.

All prompts are redesigned for Gemma 4's prompting behaviour:
  - Role in one line (not a paragraph)
  - Data in labelled compact sections (not JSON dumps)
  - Task instruction: one clear imperative sentence
  - Output format immediately after the instruction
  - No "HOW TO RESPOND:" meta-sections — Gemma ignores them and wastes tokens
  - Token budgets enforced via truncate()

Prompt 1: build_task_reasoning_prompt     — single task "Why?" explanation
Prompt 2: build_alerts_batch_explanation_prompt — batch of alerts (notifications)
"""

from __future__ import annotations

from app.services.intelligence_service.context.token_budget import (
    BUDGET_TASK_EXPLAIN,
    BUDGET_ALERTS_BATCH,
    BUDGET_RULES_IN_TASK,
    BUDGET_RULES_IN_ALERT,
    truncate,
)
from app.services.intelligence_service.prompts.components import (
    alert_block,
    rules_block,
)


# ── Shared ─────────────────────────────────────────────────────────────────────

def _weather_line(current: dict) -> str:
    temp      = current.get("temp") or current.get("temperature_c") or "?"
    rain      = current.get("rainfall_mm") or current.get("precipitation_mm") or 0
    condition = current.get("condition") or "?"
    humidity  = current.get("humidity") or "?"
    return f"{temp}°C, {condition}, {humidity}% humid, {rain}mm rain"


# ── Prompt 1: Critical Task Reasoning ─────────────────────────────────────────

def build_task_reasoning_prompt(task: dict, context: dict) -> str:
    """
    Explain in 2-3 sentences why a single critical task was recommended.
    Caller: route that handles farmer tapping "Why?" on a task card.
    Target: ≤ 900 chars total.

    task    — {title, description, priority, due_date, field_name, crop_name, is_overdue}
    context — {farmer_name, weather, rules}
    """
    farmer   = context.get("farmer_name") or "Farmer"
    current  = (context.get("weather") or {}).get("current") or {}
    rules    = context.get("rules") or ""

    priority = (task.get("priority") or "?").upper()
    title    = task.get("title") or "?"
    field    = task.get("field_name") or "your field"
    crop     = task.get("crop_name") or ""
    desc     = task.get("description") or "No reason recorded."
    due      = task.get("due_date") or ""
    overdue  = task.get("is_overdue", False)

    location_part = f", crop {crop}" if crop else ""
    due_part      = f", due {due}" if due else ""
    overdue_flag  = " [OVERDUE]" if overdue else ""
    weather_line  = _weather_line(current) if current else "no weather data"
    rules_part    = f"\n{rules_block(rules, BUDGET_RULES_IN_TASK)}" if rules else ""

    prompt = (
        f"Farm advisor for {farmer}.\n"
        f"Task: {title} [{priority}]{overdue_flag}{due_part}\n"
        f"Field: {field}{location_part}\n"
        f"Recorded reason: {truncate(desc, 120)}\n"
        f"Weather: {weather_line}{rules_part}\n\n"
        f"Write 2-3 sentences to {farmer} explaining exactly why this task is urgent now. "
        f"Name the field, cite the specific number (moisture %, temperature, or rule threshold) "
        f"that triggered it, and end with one concrete action for today."
    )
    return truncate(prompt, BUDGET_TASK_EXPLAIN)


# ── Prompt 2: Notification / Alert Reasoning ───────────────────────────────────

def build_alerts_batch_explanation_prompt(alerts: list, context: dict) -> str:
    """
    Explain a batch of alerts in one message.
    Caller: AlertService in the coordinator pipeline.
    Target: ≤ 1000 chars total.
    """
    farmer  = context.get("farmer_name") or "Farmer"
    current = (context.get("weather") or {}).get("current") or {}
    rules   = context.get("rules") or ""

    alerts_text  = alert_block(alerts or [], limit=4)
    weather_line = _weather_line(current) if current else "no weather data"
    rules_part   = f"\n{rules_block(rules, BUDGET_RULES_IN_ALERT)}" if rules else ""

    prompt = (
        f"Farm advisor for {farmer}.\n"
        f"{alerts_text}\n"
        f"Weather: {weather_line}{rules_part}\n\n"
        f"Address {farmer} by name. For each alert write 1-2 sentences "
        f"explaining the exact reading that triggered it. "
        f"End with the single most important action right now."
    )
    return truncate(prompt, BUDGET_ALERTS_BATCH)


# Backward-compat alias used by AlertService
build_alert_explanation_prompt = build_alerts_batch_explanation_prompt
