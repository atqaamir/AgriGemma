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
Prompt 2: build_notification_reasoning_prompt — single alert explanation
          build_alerts_batch_explanation_prompt — batch of alerts
Prompt 3: build_critical_tasks_overview_prompt — tasks-page banner (1–2 sentences)
Prompt 4: build_dashboard_summary_prompt  — full farm JSON intelligence
Helper:   build_weather_change_prompt     — weather-triggered advisory
"""

from __future__ import annotations

from app.services.intelligence_service.context.token_budget import (
    BUDGET_TASK_EXPLAIN,
    BUDGET_TASK_UPDATE,
    BUDGET_ALERT_EXPLAIN,
    BUDGET_ALERTS_BATCH,
    BUDGET_OVERVIEW_PROMPT,
    BUDGET_DASHBOARD_PROMPT,
    BUDGET_WEATHER_CHANGE,
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
    task_block,
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


def build_task_update_reasoning_prompt(task: dict, context: dict) -> str:
    """
    Explain in 2-3 sentences why a task's priority or status was changed.
    Caller: any service that updates a task and wants to inform the farmer why.
    Target: ≤ 950 chars total.

    task    — {title, description, priority, old_priority, due_date,
               field_name, crop_name, is_overdue, change_reason}
    context — {farmer_name, weather, rules}
    """
    farmer  = context.get("farmer_name") or "Farmer"
    current = (context.get("weather") or {}).get("current") or {}
    rules   = context.get("rules") or ""

    title        = task.get("title") or "?"
    new_priority = (task.get("priority") or "?").upper()
    old_priority = (task.get("old_priority") or "").upper()
    field        = task.get("field_name") or "your field"
    crop         = task.get("crop_name") or ""
    desc         = task.get("description") or "No reason recorded."
    due          = task.get("due_date") or ""
    overdue      = task.get("is_overdue", False)
    change_reason = task.get("change_reason") or ""

    priority_line = (
        f"{old_priority} → {new_priority}" if old_priority else new_priority
    )
    location_part  = f", crop {crop}" if crop else ""
    due_part       = f", due {due}" if due else ""
    overdue_flag   = " [OVERDUE]" if overdue else ""
    weather_line   = _weather_line(current) if current else "no weather data"
    rules_part     = f"\n{rules_block(rules, BUDGET_RULES_IN_TASK)}" if rules else ""
    change_part    = f"\nReason for change: {truncate(change_reason, 100)}" if change_reason else ""

    prompt = (
        f"Farm advisor for {farmer}.\n"
        f"Task: {title} [priority: {priority_line}]{overdue_flag}{due_part}\n"
        f"Field: {field}{location_part}\n"
        f"Recorded reason: {truncate(desc, 120)}{change_part}\n"
        f"Weather: {weather_line}{rules_part}\n\n"
        f"Write 2-3 sentences to {farmer} explaining what changed and why the priority "
        f"shifted to {new_priority}. Name the field, cite the exact reading "
        f"(moisture %, temperature, or rule threshold) that drove the change, "
        f"and end with one concrete action for today."
    )
    return truncate(prompt, BUDGET_TASK_UPDATE)


# ── Prompt 2: Notification / Alert Reasoning ───────────────────────────────────

def build_notification_reasoning_prompt(notification: dict, context: dict) -> str:
    """
    Explain why a single alert was triggered.
    Caller: route that handles farmer tapping a notification bell item.
    Target: ≤ 850 chars total.

    notification — {message, level, type, field_name}
    context      — {farmer_name, weather, rules}
    """
    farmer  = context.get("farmer_name") or "Farmer"
    current = (context.get("weather") or {}).get("current") or {}
    rules   = context.get("rules") or ""

    level = (notification.get("level") or "medium").upper()
    msg   = notification.get("message") or "?"
    field = notification.get("field_name") or "your farm"
    ntype = notification.get("type") or "general"

    weather_line = _weather_line(current) if current else "no weather data"
    rules_part   = f"\n{rules_block(rules, BUDGET_RULES_IN_ALERT)}" if rules else ""

    prompt = (
        f"Farm advisor for {farmer}.\n"
        f"Alert [{level}]: {msg}\n"
        f"Field: {field}, type: {ntype}\n"
        f"Weather: {weather_line}{rules_part}\n\n"
        f"Write 2-3 sentences to {farmer} explaining the exact reading (temperature, "
        f"moisture %, or rainfall mm) that triggered this alert, "
        f"then state the single most important action to take right now."
    )
    return truncate(prompt, BUDGET_ALERT_EXPLAIN)


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


# ── Prompt 3: Critical Tasks Overview ─────────────────────────────────────────

def build_critical_tasks_overview_prompt(tasks: list, context: dict) -> str:
    """
    Structured critical-task overview for the tasks page banner.
    Output format (markdown):
      ## [Heading]
      [One-sentence overview]
      **[Task]** ([Field]) — [PRIORITY]
      [Why it's critical today — cite a specific number.]
      → [2-3 word fix]
    Target: ≤ 1600 chars total prompt.

    tasks   — list of task dicts (title, description, priority, due_date, field_name, is_overdue)
    context — {farmer_name, weather, rules}
    """
    farmer  = context.get("farmer_name") or "Farmer"
    current = (context.get("weather") or {}).get("current") or {}
    rules   = context.get("rules") or ""

    critical = [t for t in (tasks or []) if t.get("priority") in ("critical", "high")]
    overdue  = sum(1 for t in critical if t.get("is_overdue"))
    count    = len(critical)

    task_lines = "\n".join(
        "  [{p}]{ov} {title}{field}{due}{desc}".format(
            p=t.get("priority", "?").upper(),
            ov=" [OVERDUE]" if t.get("is_overdue") else "",
            title=t.get("title", "?"),
            field=f" — {t['field_name']}" if t.get("field_name") else "",
            due=f" (due {t['due_date']})" if t.get("due_date") else "",
            desc=f": {truncate(t['description'], 80)}" if t.get("description") else "",
        )
        for t in critical[:5]
    ) or "  None"

    weather_line = _weather_line(current) if current else "no weather data"
    overdue_note = f" {overdue} overdue." if overdue else ""
    rules_part   = f"\n{rules_block(rules, 200)}" if rules else ""

    prompt = (
        f"Farm advisor for {farmer}.\n"
        f"Today: {count} critical/high-priority tasks.{overdue_note}\n"
        f"Weather: {weather_line}{rules_part}\n\n"
        f"Tasks:\n{task_lines}\n\n"
        f"Write a farm alert for {farmer} using EXACTLY this format — no extra text:\n\n"
        f"## [8-word-max heading that captures the main risk today]\n\n"
        f"[One sentence addressed to {farmer}: what is urgent today and the single most important reason why — cite one specific number.]\n\n"
        f"For EACH task listed above:\n"
        f"**[Task title]**[( Field name)] — [CRITICAL or HIGH][, OVERDUE if applicable]\n"
        f"[1-2 sentences: what this task is and the exact reason it cannot wait — cite a number (moisture %, °C, days overdue, or rule threshold).]\n"
        f"→ [2-3 word action]\n"
    )
    return truncate(prompt, BUDGET_OVERVIEW_PROMPT)


# ── Prompt 3b: Dashboard One-liner ────────────────────────────────────────────

def build_dashboard_oneliner_prompt(context: dict) -> str:
    """
    One-sentence AI summary for the Dashboard page header card.
    Runs on Ollama (local Gemma 4) — must be very compact.
    Target: ≤ 500 chars total prompt, ≤ 1 sentence output.

    context — {farmer_name, weather, tasks, farm} subset
    """
    farmer   = context.get("farmer_name") or "Farmer"
    weather  = context.get("weather") or {}
    tasks    = context.get("tasks") or {}
    farm     = context.get("farm") or {}

    current  = (weather.get("current") or {})
    temp     = current.get("temp") or current.get("temperature_c") or "?"
    rain     = current.get("rainfall_mm") or 0
    heatwave = weather.get("heatwave_risk", False)

    pending  = tasks.get("pending_count") or 0
    overdue  = tasks.get("overdue_count") or 0
    critical = tasks.get("critical_count") or 0
    fields   = farm.get("active_fields") or 0
    crops    = farm.get("total_crops") or 0

    status_parts = [f"{fields} fields, {crops} crops"]
    if overdue:
        status_parts.append(f"{overdue} overdue tasks")
    elif critical:
        status_parts.append(f"{critical} critical tasks")
    elif pending:
        status_parts.append(f"{pending} pending tasks")

    weather_note = ""
    if heatwave:
        weather_note = f" Heatwave risk at {temp}°C."
    elif (weather.get("rain_expected") or rain > 20):
        weather_note = f" Rain expected ({rain}mm today)."
    else:
        weather_note = f" Current temp {temp}°C."

    status = ", ".join(status_parts) + "." + weather_note

    prompt = (
        f"Farm advisor for {farmer}. Farm status: {status}\n\n"
        f"Write exactly ONE sentence (max 20 words) summarising the most important "
        f"thing {farmer} should know right now. Be specific. No greeting."
    )
    return truncate(prompt, 500)


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


# ── Advisory helper ────────────────────────────────────────────────────────────

def build_weather_change_prompt(
    farmer_name: str,
    new_tasks: list,
    weather: dict,
    rules: str = "",
) -> str:
    """
    Explain to the farmer why tasks changed after a weather update.
    Caller: AdvisoryService in the daily-update coordinator flow.
    Target: ≤ 950 chars total.
    """
    current  = (weather or {}).get("current") or {}
    forecast = (weather or {}).get("forecast") or []

    task_lines = "\n".join(
        "  [{p}] {title}{desc}".format(
            p=t.get("priority", "medium").upper(),
            title=t.get("title", "?"),
            desc=f": {truncate(t['description'], 70)}" if t.get("description") else "",
        )
        for t in (new_tasks or [])[:5]
    ) or "  No new tasks"

    fc_text = " | ".join(
        f"{f.get('date', f.get('day','?'))}: {f.get('condition','?')}"
        for f in forecast[:3]
    ) or "no forecast"

    weather_line = _weather_line(current) if current else "no data"
    rules_part   = f"\n{rules_block(rules, 200)}" if rules else ""

    prompt = (
        f"Farm advisor for {farmer_name}.\n"
        f"New tasks assigned after weather update:\n{task_lines}\n"
        f"Current weather: {weather_line}\n"
        f"Forecast: {fc_text}{rules_part}\n\n"
        f"Start with 'I know {farmer_name}...' or 'I understand {farmer_name}...'. "
        f"In 2-3 sentences explain exactly what the weather data shows that made these "
        f"tasks necessary — cite the specific reading. "
        f"End with one sentence of practical encouragement."
    )
    return truncate(prompt, BUDGET_WEATHER_CHANGE)


# ── Backward-compat wrapper ────────────────────────────────────────────────────

class TaskIntelligencePromptBuilder:
    """Thin wrapper retained for backward compatibility with TaskIntelligenceService."""

    @staticmethod
    def build(context: dict) -> str:
        return build_dashboard_summary_prompt(context)
