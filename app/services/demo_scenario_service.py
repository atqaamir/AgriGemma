"""
Demo scenario: weather-driven task change.

Simulates a situation where the forecast shifted from heavy rainfall to an
extended dry spell.  Completed pre-rain tasks (drainage inspection, etc.) are
created alongside new irrigation tasks so the chatbot has the context it needs
to answer questions like "we have never done irrigation in May".

Usage:
    POST /chatbot/setup-demo
"""
from datetime import date, timedelta

from app.extensions import db
from app.models.task import Task


class DemoScenarioService:

    # Tasks that were created for the original rain forecast (now completed)
    _COMPLETED_PRE_RAIN = [
        {
            "title": "Inspect and clear drainage channels",
            "priority": "high",
            "task_type": "maintenance",
            "task_category": "field",
            "completed": True,
            "description": (
                "Created because of a 50mm+ rainfall forecast for 1–2 May. "
                "Drainage channels inspected and cleared to prevent waterlogging. "
                "Completed before the rain event."
            ),
        },
        {
            "title": "Pre-rain crop and field inspection",
            "priority": "medium",
            "task_type": "checkup",
            "task_category": "general",
            "completed": True,
            "description": (
                "Created for a pre-rainfall walkthrough before the expected 50mm+ event. "
                "Checked low-lying areas for waterlogging risk and secured loose equipment. "
                "Completed on 1 May."
            ),
        },
    ]

    # New tasks triggered by the dry-spell weather change
    _IRRIGATION_TASKS = [
        {
            "title": "Irrigate Maize — North Field (Zone A & B)",
            "priority": "high",
            "task_type": "irrigation",
            "task_category": "crop",
            "completed": False,
            "description": (
                "Weather change: forecast switched from 50mm rain to an extended dry spell "
                "with no rainfall expected for 10+ days (2–12 May). "
                "Soil moisture at 22% — below the critical 30% threshold for Maize. "
                "Irrigation required to prevent stress during the flowering stage."
            ),
        },
        {
            "title": "Increase irrigation frequency for Cotton — South Field",
            "priority": "high",
            "task_type": "irrigation",
            "task_category": "crop",
            "completed": False,
            "description": (
                "Extended dry spell (2–12 May) creates high risk of boll drop for Cotton "
                "currently in boll development stage. "
                "Increase cycle from 5-day to 3-day intervals. "
                "Monitor boll retention daily during the dry period."
            ),
        },
        {
            "title": "Inspect and activate irrigation pipe connections",
            "priority": "medium",
            "task_type": "maintenance",
            "task_category": "field",
            "completed": False,
            "description": (
                "Irrigation system has been idle since March rains. "
                "Check all drip lines, valves, and emitters for blockages before "
                "starting the new irrigation schedule triggered by the dry spell forecast."
            ),
        },
        {
            "title": "Monitor soil moisture daily — all active fields",
            "priority": "medium",
            "task_type": "checkup",
            "task_category": "field",
            "completed": False,
            "description": (
                "Track soil moisture every morning during the dry spell (2–12 May). "
                "Adjust irrigation volumes if readings drop below 25% or rise above 50%. "
                "Record readings in field notes for the season report."
            ),
        },
        {
            "title": "Check water storage levels and refill if needed",
            "priority": "medium",
            "task_type": "maintenance",
            "task_category": "field",
            "completed": False,
            "description": (
                "With 10+ days of no rainfall expected, on-farm water storage needs to "
                "cover full irrigation demand. Verify tank levels and arrange refill if "
                "below 60% capacity to avoid mid-spell shortages."
            ),
        },
    ]

    @classmethod
    def setup(cls, user_id: int) -> dict:
        today = date.today()
        titles = []

        for i, data in enumerate(cls._COMPLETED_PRE_RAIN):
            task = Task(
                user_id=user_id,
                due_date=today - timedelta(days=1),
                **data,
            )
            db.session.add(task)
            titles.append(f"[DONE] {data['title']}")

        for i, data in enumerate(cls._IRRIGATION_TASKS):
            task = Task(
                user_id=user_id,
                due_date=today + timedelta(days=i),
                **data,
            )
            db.session.add(task)
            titles.append(f"[PENDING] {data['title']}")

        db.session.commit()

        return {
            "created": len(titles),
            "tasks": titles,
            "scenario": (
                "Weather changed: 50mm+ rainfall forecast replaced by a 10-day dry spell "
                "(2–12 May). Pre-rain drainage tasks are marked complete. "
                "5 irrigation tasks created. "
                "Ask the chatbot: 'Why are you asking me to do irrigation in May?'"
            ),
        }
