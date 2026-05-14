"""
Task and notification intelligence prompts — provider-agnostic.

All functions return a plain string for ai_model_service.complete().

  Prompt 1 — build_task_reasoning_prompt
      "Why was this specific critical task recommended?"
      Caller: route that handles farmer tapping "Why?" on a task card.

  Prompt 2 — build_notification_reasoning_prompt
      "Why did I get this alert / notification?"
      Caller: route that handles farmer tapping a notification bell item.
      Variant: build_alerts_batch_explanation_prompt — same intent, multiple alerts at once,
               used by AlertService in the coordinator pipeline.

  Prompt 3 — build_critical_tasks_overview_prompt
      One or two sentences explaining why critical tasks exist today.
      Caller: Tasks page header banner.
      Output: plain text string.

  Prompt 4 — build_dashboard_summary_prompt
      Full farm overview: weather + critical tasks + risks + insights.
      Caller: Dashboard page AI widget (TaskIntelligenceService).
      Output: JSON string — {summary, priority_level, recommendations,
                             urgent_actions, risks, insights}

  Helpers (not user-facing prompts):
      build_weather_change_prompt — explains why tasks changed after a weather update.
      Used by AdvisoryService in the daily-update coordinator flow.
"""

import json


# ── Prompt 1: Critical Task Reasoning ─────────────────────────────────────────

def build_task_reasoning_prompt(task: dict, context: dict) -> str:
    """
    Explain in plain language why a single critical task was recommended.

    task     — {title, description, priority, due_date, field_name, crop_name, is_overdue}
    context  — {farmer_name, weather, rules}
    """
    farmer_name = context.get("farmer_name", "Farmer")
    current = context.get("weather", {}).get("current", {})
    rules = context.get("rules", "")

    weather_line = (
        f"{current.get('temp', '?')}°C, {current.get('condition', 'unknown')}, "
        f"humidity {current.get('humidity', '?')}%, rainfall {current.get('rainfall_mm', 0)}mm"
    ) if current else "no weather data"

    description = task.get("description") or "No reason recorded."
    due = f" — due {task.get('due_date')}" if task.get("due_date") else ""
    overdue_flag = " ⚠ OVERDUE" if task.get("is_overdue") else ""
    field = task.get("field_name") or "your field"
    crop = task.get("crop_name") or "your crop"
    rules_block = f"\nRULEBOOK DATA:\n{rules}" if rules else ""

    return f"""You are a trusted farm advisor speaking directly to {farmer_name}.

The farmer is asking WHY this task was recommended:

  Task   : {task.get("title", "?")} [{task.get("priority", "?").upper()}]{due}{overdue_flag}
  Field  : {field}
  Crop   : {crop}
  Reason : {description}

Current weather: {weather_line}{rules_block}

HOW TO RESPOND:
- If the timing feels unusual, open with "I know {farmer_name}..." or "I understand {farmer_name}..."
- In 2-3 sentences explain the specific condition (weather reading, soil level, seasonal rule) that triggered this task
- Cite the exact number from the reason or rulebook above — no generalities
- End with one concrete action for today

Explanation:""".strip()


# ── Prompt 2: Notification Reasoning ──────────────────────────────────────────

def build_notification_reasoning_prompt(notification: dict, context: dict) -> str:
    """
    Explain why a single alert or notification was triggered.

    notification — {message, level, type, field_name}
    context      — {farmer_name, weather, rules}
    """
    farmer_name = context.get("farmer_name", "Farmer")
    current = context.get("weather", {}).get("current", {})
    rules = context.get("rules", "")

    weather_line = (
        f"{current.get('temp', '?')}°C, {current.get('condition', 'unknown')}, "
        f"humidity {current.get('humidity', '?')}%, rainfall {current.get('rainfall_mm', 0)}mm"
    ) if current else "no weather data"

    field = notification.get("field_name") or "your farm"
    level = (notification.get("level") or "medium").upper()
    ntype = notification.get("type") or "general"
    rules_block = f"\nRULEBOOK DATA:\n{rules}" if rules else ""

    return f"""You are a trusted farm advisor talking directly to {farmer_name}.

Explain why this {level} alert appeared:

  Alert  : {notification.get("message", "?")}
  Field  : {field}
  Type   : {ntype}

Current weather: {weather_line}{rules_block}

HOW TO RESPOND:
- Address {farmer_name} by name
- In 2-3 sentences explain the exact reading (temperature, moisture %, rainfall mm) that triggered this
- Tell them the single most important action to take right now
- Warm and direct — no formal report language

Explanation:""".strip()


def build_alerts_batch_explanation_prompt(alerts: list, context: dict) -> str:
    """
    Explain a batch of alerts in one message.
    Used by AlertService when the coordinator generates multiple alerts at once.
    """
    farmer_name = context.get("farmer_name", "Farmer")
    current = context.get("weather", {}).get("current", {})
    rules = context.get("rules", "")

    alert_lines = "\n".join([
        f"  [{a.get('level', 'medium').upper()}] {a.get('message', '')} "
        f"(field: {a.get('field_name', 'your farm')}, type: {a.get('type', 'general')})"
        for a in (alerts or [])
    ]) or "  No alerts."

    weather_line = (
        f"{current.get('temp', '?')}°C, {current.get('condition', 'unknown')}, "
        f"humidity {current.get('humidity', '?')}%, rainfall {current.get('rainfall_mm', 0)}mm"
    ) if current else "no weather data"

    rules_block = f"\nRULEBOOK CONTEXT:\n{rules}" if rules else ""

    return f"""You are a trusted farm advisor talking directly to {farmer_name}.

These alerts have been detected on the farm:
{alert_lines}

Current weather: {weather_line}{rules_block}

HOW TO RESPOND:
- Address {farmer_name} by name, warmly and directly
- For each alert explain in 1-2 sentences the exact reading that triggered it
- End with the single most important action to take right now
- No formal report language

Response:""".strip()


# Alias kept for backward compat with AlertService
build_alert_explanation_prompt = build_alerts_batch_explanation_prompt


# ── Prompt 3: Critical Tasks Overview ─────────────────────────────────────────

def build_critical_tasks_overview_prompt(tasks: list, context: dict) -> str:
    """
    1-2 sentence plain-language summary of WHY critical tasks exist today.
    Used as the Tasks page header banner. Returns plain text, not JSON.

    tasks   — list of task dicts (title, description, priority, due_date, field_name, is_overdue)
    context — {farmer_name, weather, rules}
    """
    farmer_name = context.get("farmer_name", "Farmer")
    current = context.get("weather", {}).get("current", {})
    rules = context.get("rules", "")

    critical = [t for t in (tasks or []) if t.get("priority") in ("critical", "high")]
    overdue_count = sum(1 for t in critical if t.get("is_overdue"))

    task_lines = "\n".join([
        f"  [{t.get('priority', '?').upper()}] {t.get('title', '?')}"
        + (f" on {t['field_name']}" if t.get("field_name") else "")
        + (f"\n    → {t['description'][:90]}" if t.get("description") else "")
        for t in critical[:6]
    ]) or "  No critical tasks."

    weather_line = (
        f"{current.get('temp', '?')}°C, {current.get('condition', 'unknown')}, "
        f"humidity {current.get('humidity', '?')}%, rainfall {current.get('rainfall_mm', 0)}mm"
    ) if current else "no weather data"

    overdue_note = f"\n{overdue_count} task(s) are OVERDUE." if overdue_count else ""
    rules_block = f"\nRULEBOOK DATA:\n{rules}" if rules else ""

    return f"""You are a trusted farm advisor summarizing the situation for {farmer_name}.

Critical and high-priority tasks right now:
{task_lines}{overdue_note}

Current weather: {weather_line}{rules_block}

Write exactly 1-2 sentences explaining the KEY reason these tasks are urgent today.
Reference a specific weather reading, soil condition, or seasonal rule number.
No bullet points. No lists. Plain, direct language addressed to the farmer.

Summary:""".strip()


# ── Prompt 4: Dashboard Summary ───────────────────────────────────────────────

def build_dashboard_summary_prompt(context: dict) -> str:
    """
    Full farm intelligence overview: predicted weather + critical tasks.
    Used on the Dashboard page AI widget (via TaskIntelligenceService).
    Returns a JSON string — the caller must parse it.

    Output schema:
      {summary, priority_level, recommendations, urgent_actions, risks, insights}
    """
    farm = context.get("farm", {})
    tasks = context.get("tasks", {})
    alerts = context.get("alerts", [])
    weather = context.get("weather", {})
    rules = context.get("rules", "")

    rules_section = f"\n=== RULEBOOK DATA ===\n{rules}" if rules else ""

    return f"""You are an expert agricultural AI assistant analyzing a farm's current status.

Reference real field/crop names, cite actual numbers, flag genuine risks only.

=== FARM STATUS ===
Active Fields : {farm.get("active_fields", 0)} / {farm.get("total_fields", 0)}
Active Crops  : {farm.get("total_crops", 0)}

Fields:
{json.dumps(farm.get("active_fields_data", []), indent=2)}

Crops:
{json.dumps(farm.get("active_crops_data", []), indent=2)}

=== TASK STATUS ===
Pending: {tasks.get("pending_count", 0)}  Overdue: {tasks.get("overdue_count", 0)}  Critical: {tasks.get("critical_count", 0)}  High: {tasks.get("high_priority_count", 0)}

Pending Tasks (descriptions explain why each was created):
{json.dumps(tasks.get("pending_list", []), indent=2)}

=== ACTIVE ALERTS ===
{json.dumps(alerts, indent=2) if alerts else "No active alerts."}

=== WEATHER ===
{json.dumps(weather, indent=2) if weather else "No weather data."}{rules_section}

=== OUTPUT — return ONLY this JSON, no markdown ===
{{
  "summary": "<2-3 sentences: current farm state and what this week's weather means for the crops>",
  "priority_level": "<critical|high|medium|low>",
  "recommendations": [
    "<actionable recommendation naming a specific field or crop>",
    "<actionable recommendation>",
    "<actionable recommendation>"
  ],
  "urgent_actions": [
    "<immediate action — omit this list when no overdue tasks, no critical tasks, no high alerts>"
  ],
  "risks": [
    {{
      "risk": "<risk naming a specific field or crop>",
      "severity": "<high|medium|low>",
      "mitigation": "<one concrete step>"
    }}
  ],
  "insights": [
    {{
      "insight": "<observation citing a specific number from rulebook or sensor data>",
      "category": "<weather|irrigation|disease|harvest|labor|resource|anomaly>"
    }}
  ]
}}

Rules:
- urgent_actions only when overdue > 0, critical tasks present, or high-severity alerts present
- Always name specific fields and crops — never say "your field"
- Each string 1-2 sentences max
- When rulebook data present, cite exact numbers (moisture ranges, irrigation frequency) in insights""".strip()


# ── Advisory helper (not a user-facing prompt) ────────────────────────────────

def build_weather_change_prompt(
    farmer_name: str,
    new_tasks: list,
    weather: dict,
    rules: str = "",
) -> str:
    """
    Explain to the farmer why their task list changed after a weather update.
    Called by AdvisoryService in the daily-update coordinator flow (not user-triggered).
    """
    current = weather.get("current", {})
    forecast = weather.get("forecast", [])

    task_lines = "\n".join([
        f"  [{t.get('priority', 'medium').upper()}] {t.get('title', '?')}"
        + (f"\n    → {t.get('description', '')[:100]}" if t.get("description") else "")
        for t in (new_tasks or [])[:6]
    ]) or "  No new tasks."

    fc_text = ", ".join([
        f"{f.get('date', f.get('day', '?'))}: {f.get('condition', '?')}"
        for f in forecast[:4]
    ]) if forecast else "no forecast available"

    weather_line = (
        f"{current.get('temp', '?')}°C, {current.get('condition', 'unknown')}, "
        f"humidity {current.get('humidity', '?')}%, rainfall {current.get('rainfall_mm', 0)}mm"
    ) if current else "no current weather data"

    rules_block = f"\nRULEBOOK DATA:\n{rules}" if rules else ""

    return f"""You are a trusted farm advisor talking directly to {farmer_name}.

The farm's weather has changed and new tasks have been assigned. Explain why.

NEW TASKS ASSIGNED:
{task_lines}

WEATHER THAT TRIGGERED THIS CHANGE:
Current: {weather_line}
Forecast: {fc_text}{rules_block}

HOW TO RESPOND:
- Start with "I know {farmer_name}..." or "I understand {farmer_name}..." — acknowledge that the timing may feel unusual
- In 2-3 sentences explain exactly what the weather data shows that made these tasks necessary
- Cite the specific temperature, humidity, rainfall, or soil reading
- End with one sentence of practical encouragement

Response:""".strip()


# ── Backward-compat wrapper ────────────────────────────────────────────────────

class TaskIntelligencePromptBuilder:
    """Thin wrapper kept for backward compat with TaskIntelligenceService."""

    @staticmethod
    def build(context: dict) -> str:
        return build_dashboard_summary_prompt(context)
