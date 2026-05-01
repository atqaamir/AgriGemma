import json


class TaskIntelligencePromptBuilder:
    """
    Isolated prompt factory for the task intelligence pipeline.
    Keeping prompt logic here means the rest of the system never
    contains raw strings — swap or version prompts in one place.
    """

    @staticmethod
    def build(context: dict) -> str:
        farm = context.get("farm", {})
        tasks = context.get("tasks", {})
        alerts = context.get("alerts", [])
        weather = context.get("weather", {})

        return f"""You are an expert agricultural AI assistant analyzing a farm's current operational status.

Analyze the data below and produce a structured intelligence overview for the farmer.
Be specific, reference real field/crop names, and flag genuine risks only.

=== FARM STATUS ===
Active Fields : {farm.get("active_fields", 0)} / {farm.get("total_fields", 0)}
Active Crops  : {farm.get("total_crops", 0)}

Fields:
{json.dumps(farm.get("active_fields_data", []), indent=2)}

Crops:
{json.dumps(farm.get("active_crops_data", []), indent=2)}

=== TASK STATUS ===
Pending   : {tasks.get("pending_count", 0)}
Overdue   : {tasks.get("overdue_count", 0)}
Critical  : {tasks.get("critical_count", 0)}
High      : {tasks.get("high_priority_count", 0)}

Pending Task List:
{json.dumps(tasks.get("pending_list", []), indent=2)}

=== ACTIVE ALERTS ===
{json.dumps(alerts, indent=2) if alerts else "No active alerts."}

=== WEATHER CONTEXT ===
{json.dumps(weather, indent=2) if weather else "No weather data available."}

=== OUTPUT FORMAT ===
Return ONLY a JSON object with this exact schema — no markdown, no extra text:
{{
  "summary": "<2-3 sentences describing the current farm operational state>",
  "priority_level": "<critical|high|medium|low>",
  "recommendations": [
    "<specific, actionable recommendation>",
    "<specific, actionable recommendation>",
    "<specific, actionable recommendation>"
  ],
  "urgent_actions": [
    "<immediate action required — empty list if none>"
  ],
  "risks": [
    {{
      "risk": "<risk description referencing field/crop names>",
      "severity": "<high|medium|low>",
      "mitigation": "<concrete mitigation step>"
    }}
  ],
  "insights": [
    {{
      "insight": "<observation about current farm state>",
      "category": "<weather|irrigation|disease|harvest|labor|resource|anomaly>"
    }}
  ]
}}

Rules:
- urgent_actions must only appear when overdue > 0, critical tasks exist, or high-severity alerts exist
- Mention specific field and crop names wherever possible
- Keep each string concise (1-2 sentences max)
- severity in risks must match the actual data severity""".strip()
