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
Prompt 4: build_dashboard_summary_prompt  — full farm JSON intelligence
"""

from __future__ import annotations

from app.services.intelligence_service.context.token_budget import (
    BUDGET_TASK_EXPLAIN,
    BUDGET_ALERTS_BATCH,
    BUDGET_DASHBOARD_PROMPT,
    BUDGET_RULES_IN_TASK,
    BUDGET_RULES_IN_ALERT,
    BUDGET_RULES_IN_DASHBOARD,
    truncate,
)
from app.services.intelligence_service.prompts.components import (
    weather_block,
    weather_signals,
    field_block,
    crop_block,
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


# ── Prompt 4: Dashboard Summary ───────────────────────────────────────────────

_DASHBOARD_OUTPUT_SCHEMA = """{
  "summary": "<1-2 sentences: current farm state + the single most urgent action today>",
  "priority_level": "<critical|high|medium|low>",
  "recommendations": [
    "<actionable step naming a specific field or crop>",
    "<actionable step>",
    "<actionable step>"
  ],
  "urgent_actions": [
    "<immediate action — include ONLY if overdue tasks, critical tasks, or high alerts exist>"
  ],
  "risks": [
    {"risk": "<name specific field or crop>", "severity": "<high|medium|low>", "mitigation": "<one concrete step>"}
  ],
  "insights": [
    {"insight": "<cite an exact number from the data>", "category": "<weather|irrigation|disease|harvest|labor|resource|anomaly>"}
  ]
}"""


def build_dashboard_summary_prompt(context: dict) -> str:
    """
    Full farm intelligence overview — weather + critical tasks + risks + insights.
    Caller: Dashboard page AI widget (TaskIntelligenceService).
    Output: JSON string — caller must parse it.
    Target: ≤ 2800 chars total.

    Uses compact labelled sections instead of raw JSON dumps.
    Gemma produces more reliable JSON when input is compact text, not nested JSON.
    """
    farm    = context.get("farm") or {}
    tasks   = context.get("tasks") or {}
    alerts  = context.get("alerts") or []
    weather = context.get("weather") or {}
    rules   = context.get("rules") or ""

    # Farm summary
    active_f  = farm.get("active_fields") or 0
    total_f   = farm.get("total_fields") or 0
    total_c   = farm.get("total_crops") or 0
    farm_line = f"{active_f}/{total_f} fields active, {total_c} crops"

    # Task summary
    pending  = tasks.get("pending_count") or 0
    overdue  = tasks.get("overdue_count") or 0
    critical = tasks.get("critical_count") or 0
    high     = tasks.get("high_priority_count") or 0
    task_summary = f"{pending} pending, {overdue} overdue, {critical} critical, {high} high"

    # Critical/high tasks — compact text, not JSON
    top_tasks = [
        t for t in (tasks.get("pending_list") or [])
        if t.get("priority") in ("critical", "high")
    ][:6]

    task_lines = "\n".join(
        "  [{p}]{ov} {title}{loc}{desc}".format(
            p=t["priority"].upper(),
            ov="⚠" if t.get("is_overdue") else "",
            title=t.get("title", "?"),
            loc=(
                f" — {t.get('field_name') or t.get('crop_name', '')}"
                if (t.get("field_name") or t.get("crop_name")) else ""
            ),
            desc=(f": {truncate(t['description'], 60)}" if t.get("description") else ""),
        )
        for t in top_tasks
    ) or "  None"

    # Component blocks
    fields_data = farm.get("active_fields_data") or []
    crops_data  = farm.get("active_crops_data") or []
    wx_signals  = weather_signals(weather, fields_data)
    wx_text     = weather_block(weather, days=3) if weather else "[WEATHER] No data"
    fields_text = field_block(fields_data, limit=4)
    crops_text  = crop_block(crops_data, limit=4)
    alerts_text = alert_block(alerts, limit=3) if alerts else ""
    rules_text  = rules_block(rules, BUDGET_RULES_IN_DASHBOARD) if rules else ""

    # Assemble data block
    sections = [
        f"Farm: {farm_line}",
        f"Tasks: {task_summary}",
        f"Priority tasks:\n{task_lines}",
    ]
    for blk in (wx_signals, wx_text, fields_text, crops_text, alerts_text, rules_text):
        if blk:
            sections.append(blk)

    data_limit = (BUDGET_DASHBOARD_PROMPT * 2) // 3
    data_block = truncate("\n\n".join(sections), data_limit)

    prompt = (
        f"Agricultural AI analysing farm status.\n\n"
        f"{data_block}\n\n"
        f"Return ONLY this JSON — no markdown fences, no explanation:\n"
        f"{_DASHBOARD_OUTPUT_SCHEMA}\n\n"
        f"Constraints: name specific fields/crops everywhere. "
        f"urgent_actions only when overdue>0, critical tasks exist, or high-severity alerts. "
        f"summary max 2 sentences. cite exact numbers from the data."
    )
    return truncate(prompt, BUDGET_DASHBOARD_PROMPT)


# ── Backward-compat wrapper ────────────────────────────────────────────────────

class TaskIntelligencePromptBuilder:
    """Thin wrapper retained for backward compatibility with TaskIntelligenceService."""

    @staticmethod
    def build(context: dict) -> str:
        return build_dashboard_summary_prompt(context)
