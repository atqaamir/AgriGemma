"""
Placeholder AI provider for testing and development.
Generates deterministic responses without requiring Gemma or external API.
Use in tests by calling: ai_model_service.register_provider(PlaceholderProvider())
"""
import json
from app.services.ai_model_service.ai_provider_interface import AIModelProvider


class PlaceholderProvider(AIModelProvider):
    """
    Mock AI provider that returns deterministic JSON responses.
    Useful for testing the full notification pipeline without external dependencies.
    """

    def __init__(self) -> None:
        self._call_count = 0

    @property
    def name(self) -> str:
        return "Placeholder (Testing)"

    def complete(self, prompt: str) -> str:
        """Return a valid intelligence JSON response regardless of prompt."""
        self._call_count += 1

        # Return deterministic but realistic task intelligence response
        response = {
            "summary": "Mock AI analysis: Farm health is good with 2 pending tasks and no critical issues.",
            "priority_level": "medium",
            "recommendations": [
                "Water Field A - soil moisture is below optimal (28%)",
                "Prepare Field B for planting - weather forecast shows clear conditions next 3 days",
                "Review pest control schedule - no recent incidents reported",
            ],
            "urgent_actions": [
                "Check irrigation on Field C - last watering was 4 days ago"
            ],
            "risks": [
                {
                    "risk": "Potential drought stress if irrigation delayed",
                    "severity": "high",
                    "mitigation": "Schedule immediate watering session"
                }
            ],
            "insights": [
                {
                    "insight": "Field A shows declining moisture trend - recommend daily monitoring",
                    "category": "irrigation"
                },
                {
                    "insight": "Optimal planting window for Field B closes in 5 days",
                    "category": "planting"
                }
            ]
        }

        return json.dumps(response)
