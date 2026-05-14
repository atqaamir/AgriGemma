"""
Token budget enforcement for Gemma-optimized prompts.

Gemma 4 effective prompt budgets by variant:
  - 1B  local  → ~512 tokens  ≈ 1 800 chars  (conservative)
  - 4B  local  → ~1 024 tokens ≈ 3 600 chars
  - 27B cloud  → ~4 096 tokens ≈ 14 400 chars

We target the 4B range by default so the same codebase runs well on both
local and cloud deployments without configuration.

Rule of thumb: 1 token ≈ 3.5 chars (English + numbers + punctuation).
All budgets are in characters. Use BUDGET_* constants everywhere so a
single config change adjusts all prompts simultaneously.
"""

from __future__ import annotations

from typing import Callable, TypeVar

T = TypeVar("T")

# ── Prompt-level char budgets (full prompt including instructions + data) ──────

BUDGET_CHATBOT_CONTEXT  = 1_600   # context block inside the chatbot prompt
BUDGET_CHATBOT_HISTORY  = 300     # compressed conversation history block
BUDGET_DASHBOARD_PROMPT = 2_800   # full dashboard intelligence prompt
BUDGET_TASK_EXPLAIN     = 900     # full single-task explanation prompt
BUDGET_ALERT_EXPLAIN    = 850     # full single-alert explanation prompt
BUDGET_ALERTS_BATCH     = 1_000   # full batch-alerts explanation prompt
BUDGET_OVERVIEW_PROMPT  = 750     # tasks-page banner prompt
BUDGET_WEATHER_CHANGE   = 950     # weather-triggered advisory prompt

# Per-section sub-budgets inside the chatbot context block
BUDGET_RULES_IN_CHATBOT    = 450
BUDGET_RULES_IN_DASHBOARD  = 450
BUDGET_RULES_IN_TASK       = 260
BUDGET_RULES_IN_ALERT      = 220
BUDGET_TASK_DESC           = 80   # individual task description truncation


# ── Core utilities ─────────────────────────────────────────────────────────────

def truncate(text: str, max_chars: int) -> str:
    """Hard-cap a text block. Appends ' [...]' if cut."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 6].rstrip() + " [...]"


def fit_list(
    items: list[T],
    formatter: Callable[[T], str],
    budget_chars: int,
    separator: str = "\n",
) -> list[str]:
    """
    Render as many list items as fit within budget_chars.
    Stops before exceeding the budget — never truncates mid-item.
    Returns list of formatted strings (caller joins them).
    """
    result: list[str] = []
    used = 0
    sep_len = len(separator)
    for item in items:
        line = formatter(item)
        cost = len(line) + (sep_len if result else 0)
        if used + cost > budget_chars:
            break
        result.append(line)
        used += cost
    return result


def chars_remaining(used: int, budget: int) -> int:
    """How many characters are left in a budget."""
    return max(0, budget - used)
