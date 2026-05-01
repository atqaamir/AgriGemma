"""
Export SmartFarming DB data as Unsloth-ready training examples.

Output format: ShareGPT JSONL  (works with Unsloth's apply_chat_template)
    {"conversations": [
        {"from": "system", "value": "..."},
        {"from": "human", "value": "..."},
        {"from": "gpt",   "value": "..."}
    ]}

Usage
-----
    python export_training_data.py

Output
------
    training_data/farming_dataset.jsonl   — all synthesised + real examples
    training_data/stats.txt               — row counts per source
"""

import json
import os
from pathlib import Path
from app import create_app
from app.extensions import db
from app.models.task import Task
from app.models.crop import Crop
from app.models.field import Field
from app.models.notification import Notification
from app.models.chat import Conversation, ChatMessage

# ── Constants ──────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are an expert agricultural advisor embedded in a smart farming app. "
    "You help farmers with crop health, field management, irrigation, fertilisation, "
    "pest control, weather adaptation, and task planning. "
    "Give practical, concise, actionable advice. "
    "When you reference specific crops or fields, use the context provided."
)

OUT_DIR = Path("training_data")
OUT_FILE = OUT_DIR / "farming_dataset.jsonl"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _entry(human: str, gpt: str) -> dict:
    return {
        "conversations": [
            {"from": "system", "value": SYSTEM_PROMPT},
            {"from": "human", "value": human.strip()},
            {"from": "gpt",   "value": gpt.strip()},
        ]
    }


def _health_label(status: str | None) -> str:
    return (status or "unknown").lower()


def _stage_label(stage: str | None) -> str:
    return (stage or "unknown growth stage").lower()


# ── Source 1: Tasks ────────────────────────────────────────────────────────────

def from_tasks() -> list[dict]:
    examples = []
    tasks = Task.query.all()

    for t in tasks:
        if not t.description:
            continue

        crop_ctx = f" for {t.crop.name}" if t.crop else ""
        field_ctx = f" in {t.field.name}" if t.field else ""
        priority_ctx = f" (priority: {t.priority})" if t.priority else ""

        human = (
            f"I have a {t.task_type or 'farming'} task{crop_ctx}{field_ctx}"
            f"{priority_ctx}: \"{t.title}\". What does this involve and how should I approach it?"
        )

        output_parts = [t.description]
        if t.notes:
            output_parts.append(f"\nNotes: {t.notes}")

        examples.append(_entry(human, "\n".join(output_parts)))

        # Second angle: ask about priority
        if t.priority in ("high", "critical"):
            human2 = (
                f"Why is \"{t.title}\"{crop_ctx}{field_ctx} considered {t.priority} priority?"
            )
            gpt2 = (
                f"This task is marked {t.priority} priority because it directly affects crop "
                f"performance or field health. {t.description}"
            )
            examples.append(_entry(human2, gpt2))

    return examples


# ── Source 2: Crop health ──────────────────────────────────────────────────────

_CROP_ADVICE = {
    "healthy": (
        "The crop is in good condition. Continue current irrigation and fertilisation schedule. "
        "Scout weekly for early signs of pests or disease to maintain this status."
    ),
    "alert": (
        "The crop needs attention. Inspect for water stress, nutrient deficiency, or early disease. "
        "Increase monitoring frequency to every 2–3 days and address the root cause promptly."
    ),
    "critical": (
        "Immediate intervention required. Identify whether the issue is water stress, disease, "
        "pests, or nutrient deficiency and apply targeted treatment within 24 hours. "
        "Document observations for ongoing tracking."
    ),
}

def from_crops() -> list[dict]:
    examples = []
    crops = Crop.query.all()

    for c in crops:
        field_name = c.field.name if c.field else "the field"
        status = _health_label(c.current_health_status)
        stage = _stage_label(c.current_growth_stage)
        water = f"{c.currently_water_requirement:.1f} mm/day" if c.currently_water_requirement else "unknown"

        # Health status question
        human = (
            f"My {c.name} crop in {field_name} is at the {stage} stage "
            f"with a health status of '{status}'. What should I do?"
        )
        gpt = _CROP_ADVICE.get(status, f"Monitor the {c.name} crop closely and consult field observations.")
        examples.append(_entry(human, gpt))

        # Water requirement question
        if c.currently_water_requirement:
            human2 = f"How much water does my {c.name} need at the {stage} stage?"
            gpt2 = (
                f"{c.name} at the {stage} stage currently requires approximately {water}. "
                f"Adjust based on recent rainfall, soil moisture readings, and temperature. "
                f"Reduce if soil moisture exceeds 70%; increase during heat stress."
            )
            examples.append(_entry(human2, gpt2))

        # Growth stage question
        human3 = f"What are the key management priorities for {c.name} during the {stage} stage?"
        stage_advice = {
            "seedling":    "Focus on establishment: consistent moisture, weed control, and protection from pests.",
            "vegetative":  "Prioritise nitrogen supply, adequate irrigation, and canopy monitoring.",
            "flowering":   "Avoid water stress during pollination. Monitor for pests and fungal disease closely.",
            "ripening":    "Reduce irrigation gradually. Monitor grain fill and plan harvest logistics.",
        }
        gpt3 = stage_advice.get(stage, f"Monitor {c.name} closely and maintain standard care routines.")
        examples.append(_entry(human3, gpt3))

    return examples


# ── Source 3: Field health ─────────────────────────────────────────────────────

def from_fields() -> list[dict]:
    examples = []
    fields = Field.query.all()

    for f in fields:
        status = _health_label(f.health_status)
        moisture = f.moisture_level
        heat = f.heat_level
        stress = f.stress_risk
        score = f.field_score

        if moisture is None:
            continue

        # Moisture question
        human = (
            f"{f.name} has a moisture level of {moisture:.0f}% and a stress risk of "
            f"{stress:.0f}%. What irrigation action should I take?"
        )
        if moisture < 40:
            gpt = (
                f"Moisture is critically low at {moisture:.0f}%. Initiate an irrigation cycle "
                f"immediately targeting the drier zones. With stress risk at {stress:.0f}%, "
                f"delay will likely cause crop damage."
            )
        elif moisture < 55:
            gpt = (
                f"Moisture at {moisture:.0f}% is below the optimal range (55–70%). "
                f"Schedule irrigation within the next 12–24 hours. Monitor for wilting symptoms."
            )
        else:
            gpt = (
                f"Moisture at {moisture:.0f}% is within the healthy range. "
                f"No irrigation needed today. Re-check in 48 hours or after the next forecast."
            )
        examples.append(_entry(human, gpt))

        # Overall field health
        if score:
            human2 = f"My {f.name} has a field health score of {score:.0f}. How should I interpret this?"
            if score >= 85:
                gpt2 = (
                    f"A score of {score:.0f} indicates excellent field health. "
                    f"Maintain current management practices and continue regular monitoring."
                )
            elif score >= 65:
                gpt2 = (
                    f"A score of {score:.0f} indicates moderate health — some areas need attention. "
                    f"Review moisture, nutrient levels, and pest pressure. Target improvements to "
                    f"the lowest-performing zones first."
                )
            else:
                gpt2 = (
                    f"A score of {score:.0f} signals significant stress. Conduct a full field "
                    f"inspection immediately — check soil, drainage, crop symptoms, and recent "
                    f"weather impact. Prioritise corrective action."
                )
            examples.append(_entry(human2, gpt2))

    return examples


# ── Source 4: Notifications ────────────────────────────────────────────────────

def from_notifications() -> list[dict]:
    examples = []
    notifs = Notification.query.filter(Notification.detail.isnot(None)).all()

    for n in notifs:
        detail = (n.detail or "").strip()
        if len(detail) < 40:
            continue

        human = n.message.strip() if n.message else n.title
        examples.append(_entry(human, detail))

        # Flip angle: ask what to do about it
        if n.entity_type in ("crop", "field"):
            human2 = f"I received an alert: \"{n.title}\". What actions should I take?"
            examples.append(_entry(human2, detail))

    return examples


# ── Source 5: Real chat history ────────────────────────────────────────────────

def from_chat_history() -> list[dict]:
    examples = []
    conversations = Conversation.query.all()

    for conv in conversations:
        messages = (
            ChatMessage.query
            .filter_by(conversation_id=conv.id)
            .order_by(ChatMessage.created_at)
            .all()
        )

        # Walk paired user→bot turns
        i = 0
        while i < len(messages) - 1:
            user_msg = messages[i]
            bot_msg  = messages[i + 1]

            if user_msg.sender == "user" and bot_msg.sender == "bot":
                human = user_msg.message.strip()
                gpt   = bot_msg.message.strip()

                # Skip placeholder/offline responses
                if "[AI model offline" in gpt or len(gpt) < 20:
                    i += 2
                    continue

                examples.append(_entry(human, gpt))
                i += 2
            else:
                i += 1

    return examples


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    app = create_app()

    with app.app_context():
        OUT_DIR.mkdir(exist_ok=True)

        sources = {
            "tasks":         from_tasks(),
            "crops":         from_crops(),
            "fields":        from_fields(),
            "notifications": from_notifications(),
            "chat_history":  from_chat_history(),
        }

        all_examples = []
        stats_lines  = []

        for name, rows in sources.items():
            all_examples.extend(rows)
            stats_lines.append(f"{name:<20} {len(rows):>5} examples")

        stats_lines.append("-" * 27)
        stats_lines.append(f"{'TOTAL':<20} {len(all_examples):>5} examples")

        with open(OUT_FILE, "w", encoding="utf-8") as f:
            for ex in all_examples:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")

        stats_text = "\n".join(stats_lines)
        (OUT_DIR / "stats.txt").write_text(stats_text + "\n", encoding="utf-8")

        print(stats_text)
        print(f"\nSaved → {OUT_FILE}")
        print(
            "\nUnsloth usage:\n"
            "  dataset = load_dataset('json', data_files='training_data/farming_dataset.jsonl', split='train')\n"
            "  # Then pass to FastLanguageModel + SFTTrainer with formatting_func=apply_chat_template"
        )


if __name__ == "__main__":
    main()
