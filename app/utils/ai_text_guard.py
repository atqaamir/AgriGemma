"""Checks for AI text shown to users (notifications, task "Why" texts, alert explanations,
task insights, farm report). A text that fails is not shown; the caller uses its rule-based
text instead.

Rejected:
  - drafts / leaked reasoning: bullet lines like "* User:", "* Role:", "* Constraints:",
    "*Attempt 1 (Mental Draft)*", "Checking against constraints", self-check lines
    ("2-3 sentences? Yes"). Single words like "attempt" or "draft" in a normal sentence pass.
  - crops the user does not grow (not in the active plan, or Not Feasible). Field names are
    removed before the check, so "Punjab Wheat Belt" is allowed text.
  - "you must".
  - with an unusual forecast: cheerful phrases ("beautiful day", "everything is looking good",
    "perfect", "nothing to worry about").
  - optionally a date that is not in the facts.
"""
from __future__ import annotations

import logging
import re

from app.utils.date_guard import dates_outside

logger = logging.getLogger(__name__)

_LABELS = (r"User|Role|Context|Constraints?|Current Weather|Weather|Plan Adjustments?|Tone|Persona|Audience|"
           r"Goal|Task|Output|Format|Instructions?|Facts|Length|Style")
_DRAFT = [
    (re.compile(r"^\s*[*\-•]\s+\**\s*(?:" + _LABELS + r")\s*\**\s*:", re.I | re.M), "prompt-analysis bullet"),
    (re.compile(r"\*+\s*Attempt\s+\d+|\bAttempt\s+\d+\s*[(:*]", re.I), "draft attempt"),
    (re.compile(r"\bMental\s+Draft\b", re.I), "mental draft"),
    (re.compile(r"\bChecking\s+against\s+(?:the\s+)?constraints\b", re.I), "constraint check"),
    (re.compile(r"\bRefining\s+for\s+(?:tone|style|constraints|length)\b", re.I), "refining note"),
    (re.compile(r"\(\s*Closer\s+to\s+final\s*\)|\bFinal\s+(?:Polish|Version|Draft|Output)\s*[:*)]", re.I),
     "draft version"),
    (re.compile(r"^\s*[*\-•]\s+[^\n]{0,80}\?\s+(?:Yes|No)\b", re.I | re.M), "self-check line"),
]
_MUST = re.compile(r"\byou must\b", re.I)
_CHEERFUL = re.compile(
    r"\b(?:beautiful|lovely|great|wonderful|perfect)\s+day\b|\bperfect\b|"
    r"\beverything(?:'s|\s+is)?\s+(?:looking|looks|is)\s+(?:good|great|fine)\b|"
    r"\ball\s+good\b|\bnothing\s+to\s+worry\b|\bno\s+need\s+to\s+worry\b|\benjoy\s+(?:these|the|your)\b",
    re.I)
# Crops the app knows besides the crop_names table (the AI may still name them).
_EXTRA_CROPS = ("wheat", "rice", "maize", "corn", "cotton", "sugarcane", "barley", "sorghum", "millet",
                "potato", "potatoes", "tomato", "tomatoes", "soybean", "mustard", "canola")


def draft_problem(text: str) -> str | None:
    for pat, label in _DRAFT:
        if pat.search(text or ""):
            return f"leaked draft ({label})"
    return None


_NOT_GROWN = re.compile(r"not\s+feasible|not\s+planned|not\s+suitable|not\s+grown|not\s+in\s+(?:the|your)\s+plan|"
                        r"isn't\s+planned|skip", re.I)


def crop_problem(text: str, allowed: set, known: set, field_names=(), not_feasible=()) -> str | None:
    """A crop name in the text that is not one of the user's crops. A Not Feasible crop of the
    plan may be named in a sentence that says so ("Rice is not feasible this season")."""
    t = text or ""
    for name in sorted(field_names, key=len, reverse=True):
        if name:
            t = re.sub(re.escape(name), " ", t, flags=re.I)
    allowed_l = {a.lower() for a in allowed}
    if "maize" in allowed_l:
        allowed_l.add("corn")
    nf_l = {c.lower() for c in not_feasible}
    for c in sorted({k.lower() for k in known}, key=lambda x: (-len(x), x)):
        if c in allowed_l or (c.endswith("es") and c[:-2] in allowed_l) or (c.endswith("s") and c[:-1] in allowed_l):
            continue
        pat = re.compile(r"\b" + re.escape(c) + r"(?:s|es)?\b", re.I)
        for sentence in re.split(r"(?<=[.!?;])\s+|\n+", t):
            if pat.search(sentence) and not (c in nf_l and _NOT_GROWN.search(sentence)):
                return f"names a crop the user does not grow ({c})"
    return None


def problem(text: str, *, allowed_crops=None, known_crops=None, field_names=(), not_feasible_crops=(),
            verdict: str | None = None, allowed_dates=None) -> str | None:
    """None if the text may be shown, else why not."""
    if not (text or "").strip():
        return "empty"
    p = draft_problem(text)
    if p:
        return p
    if _MUST.search(text):
        return '"you must"'
    if verdict == "unusual":
        m = _CHEERFUL.search(text)
        if m:
            return f'cheerful tone with an unusual forecast ("{m.group(0)}")'
    if allowed_crops is not None:
        p = crop_problem(text, set(allowed_crops), set(known_crops or ()) | set(_EXTRA_CROPS), field_names,
                         not_feasible_crops)
        if p:
            return p
    if allowed_dates is not None:
        outside = dates_outside(text, allowed_dates)
        if outside:
            return "date not in the facts: " + ", ".join(f"{d}/{m}" for d, m in outside)
    return None


def user_scope(user_id: int) -> dict:
    """The user's crops (active plan, not Not Feasible), all known crop names and the user's
    field names – keyword arguments for problem()."""
    from app.models.field import Field
    from app.models.seasonal_plan import SeasonalPlan
    from app.rules.vocabulary.crop_names import CropNames

    allowed, not_feasible = set(), set()
    plan = SeasonalPlan.query.filter_by(user_id=user_id, currently_active=True).first()
    for e in (plan.entries if plan else []):
        if e.crop_name_rel:
            (not_feasible if e.feasibility == "Not Feasible" else allowed).add(e.crop_name_rel.name)
    return {"allowed_crops": allowed, "not_feasible_crops": not_feasible - allowed,
            "known_crops": {c.name for c in CropNames.query.all() if c.name},
            "field_names": [f.name for f in Field.query.filter_by(user_id=user_id).all() if f.name]}


def check_for_user(text: str, user_id: int, label: str = "AI text", **kwargs) -> str | None:
    """problem() with the user's crops and fields; logs a rejection."""
    try:
        scope = user_scope(user_id)
    except Exception as exc:                      # no DB scope: still check drafts / tone
        logger.warning("AI text guard: no crop scope for user %s (%s)", user_id, exc)
        scope = {}
    p = problem(text, **{**scope, **kwargs})
    if p:
        logger.warning("AI text guard: %s rejected for user %s – %s: %r", label, user_id, p, (text or "")[:200])
    return p
