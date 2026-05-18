"""
Farm intent classifier — keyword-based, sub-millisecond, no AI call needed.

classify(message) -> IntentResult

Primary intent drives which data sources get fetched.
Secondary intents enrich context for compound questions.

Design constraints (Gemma optimization):
  - Zero AI calls — intent detection must never burn prompt tokens
  - Weighted partial-substring matching → confident results without NLP libraries
  - Specificity wins: disease/irrigation beat weather when both score
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FarmIntent(str, Enum):
    GREETING      = "greeting"
    IRRIGATION    = "irrigation"
    WEATHER       = "weather"
    HARVEST       = "harvest"
    FERTILIZATION = "fertilization"
    SOIL          = "soil"
    TASK          = "task"
    ALERT         = "alert"
    PLANTING      = "planting"
    GENERAL       = "general"


@dataclass(frozen=True)
class IntentResult:
    primary:    FarmIntent
    secondary:  list[FarmIntent]
    confidence: float   # 0.0 – 1.0
    method:     str     # always "keyword"

    def all_intents(self) -> list[FarmIntent]:
        seen, result = set(), []
        for i in [self.primary] + list(self.secondary):
            if i not in seen:
                result.append(i)
                seen.add(i)
        return result

    def has(self, intent: FarmIntent) -> bool:
        return intent in self.all_intents()


_GREETING_EXACT: frozenset[str] = frozenset({
    "hi", "hello", "hey", "hiya", "howdy", "salam", "assalam", "assalamualaikum",
    "good morning", "good afternoon", "good evening", "good day",
    "who are you", "who are you?", "what are you", "what are you?",
    "what can you do", "what can you do?", "help", "start",
})

def _is_greeting(text: str) -> bool:
    """True for short openers and identity questions that need no farm data."""
    stripped = text.strip().rstrip("!?.").lower()
    if stripped in _GREETING_EXACT:
        return True
    # Short messages (≤4 words) with no farm keyword are likely greetings
    words = stripped.split()
    return len(words) <= 4 and not any(
        kw in stripped for kw in (
            "crop", "field", "soil", "water", "irrigat", "weather", "task",
            "fertili", "harvest", "pest", "disease", "plant", "alert",
        )
    )


# (intent, weight, substrings_to_match)
# Longer, more specific substrings = fewer false positives.
# Weight > 1.0 marks a domain-specific signal (not just a common word).
_SIGNALS: list[tuple[FarmIntent, float, tuple[str, ...]]] = [
    (FarmIntent.IRRIGATION, 1.3, (
        "irrigat", "should i water", "water my", "water the crop",
        "drip system", "sprinkler", "flood irrigat",
        "water stress", "water need", "watering schedule",
        "soil moisture", "field dry", "field wet", "too dry",
    )),
    (FarmIntent.WEATHER, 1.0, (
        "weather", "forecast", "rain tomorrow", "will it rain",
        "temperature today", "humidity", "heatwave", "heat wave",
        "frost", "wind speed", "cloudy", "sunny", "monsoon",
        "storm", "how hot",
    )),
    (FarmIntent.HARVEST, 1.3, (
        "harvest", "when to pick", "ready to harvest", "time to harvest",
        "ripening", "matured", "collect crop", "crop ready",
        "reap", "yield this season", "when should i cut",
    )),
    (FarmIntent.FERTILIZATION, 1.3, (
        "fertili", "npk", "nitrogen", "phosphorus", "potassium",
        "compost", "manure", "urea", "feed my crop", "nutrient",
        "deficiency", "fertilizer burn", "micronutrient",
    )),
    (FarmIntent.SOIL, 1.0, (
        "soil type", "soil ph", "ground ph", "organic matter",
        "soil quality", "clay soil", "sandy soil", "loam soil",
        "topsoil", "soil health", "soil texture",
    )),
    (FarmIntent.TASK, 0.9, (
        "my task", "pending task", "overdue task", "urgent task",
        "what should i do today", "work schedule", "task list",
        "critical task", "what's due", "what is due",
        "tasks due", "tasks are due", "which task", "any task",
        "show task", "list task", "how many task", "task today",
        "due today", "due this week", "need to do", "tasks", "task", "priority", "critical"
    )),
    (FarmIntent.ALERT, 1.1, (
        "alert", "notification", "warning i got", "why did i get",
        "why am i getting", "alarm", "got this alert",
        "why this warning",
    )),
    (FarmIntent.PLANTING, 1.2, (
        "what should i grow", "what can i grow", "what to grow", "what to plant",
        "what should i plant", "which crop", "which crops", "recommend a crop",
        "suggest a crop", "best crop", "good crop to grow", "what crop",
        "should i sow", "what to sow", "planning to plant", "thinking of planting",
        "new crop", "next crop", "start planting", "start growing",
        "suitable crop", "crop for this season", "crop for this weather",
        "considering the weather", "if weather improves", "crop", "rice", "maize", "cotton"
    )),
]

# More specific intents that "absorb" a WEATHER primary if both score.
# Rationale: "will rain affect my irrigation?" is IRRIGATION, not WEATHER.
_SPECIFICITY_ORDER = (
  
    FarmIntent.IRRIGATION,
    FarmIntent.HARVEST,
    FarmIntent.FERTILIZATION,
    FarmIntent.SOIL,
    FarmIntent.TASK,
    FarmIntent.ALERT,
)


def classify(message: str) -> IntentResult:
    """
    Classify a farmer message into primary + up to 2 secondary intents.
    Runs in < 1ms. No AI call, no external dependency.
    """
    text = message.lower()

    if _is_greeting(text):
        return IntentResult(
            primary=FarmIntent.GREETING,
            secondary=[],
            confidence=1.0,
            method="keyword",
        )
    scores: dict[FarmIntent, float] = {}

    for intent, weight, keywords in _SIGNALS:
        hit = sum(weight for kw in keywords if kw in text)
        if hit:
            scores[intent] = scores.get(intent, 0.0) + hit

    if not scores:
        return IntentResult(
            primary=FarmIntent.GENERAL,
            secondary=[],
            confidence=0.0,
            method="keyword",
        )

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary_intent, primary_score = ranked[0]
    total = sum(s for _, s in ranked)
    confidence = round(primary_score / total, 2)

    # Promote a specific intent over WEATHER if both scored
    if primary_intent == FarmIntent.WEATHER:
        for specific in _SPECIFICITY_ORDER:
            if specific in scores and scores[specific] >= primary_score * 0.6:
                # Swap: specific becomes primary, weather becomes secondary
                primary_intent = specific
                primary_score  = scores[specific]
                break

    # Secondary: any other intent with score >= 65% of primary score
    threshold = primary_score * 0.65
    secondary = [
        i for i, s in ranked
        if i != primary_intent and s >= threshold
    ][:2]

    return IntentResult(
        primary=primary_intent,
        secondary=secondary,
        confidence=confidence,
        method="keyword",
    )
