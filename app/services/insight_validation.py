"""Checks every AI insight must pass before it is shown (task insights, farm report).

An insight is dropped (with a logged reason) when it:
  - cites no evidence, or a signal id that does not exist;
  - names a date that is not in the dates of the signals it cites (shared date guard);
  - breaks the style rules: "I understand" / "I know", "must" / "you must", or claims to have changed
    the plan itself ("I've moved…", "I have created…") – the AI recommends, it never decides;
  - talks about leaves / stems / wilting on a bare field (nothing sown there);
  - is a leaked model draft, or (inside crop_scope) names a crop the user doesn't have
    (app.utils.ai_text_guard).
"""
from __future__ import annotations

import re
import threading
from contextlib import contextmanager
from datetime import date

from app.utils.date_guard import dates_outside

_STYLE = [
    (re.compile(r"\bI (?:understand|know)\b", re.I), '"I understand / I know"'),
    (re.compile(r"\byou must\b", re.I), '"you must"'),
    (re.compile(r"\bmust\b", re.I), '"must" (say "needs to be done before …")'),
    (re.compile(r"\bI(?:'ve| have)? (?:moved|changed|rescheduled|postponed|created|added|deleted|cancelled|"
                r"removed)\b", re.I), "decides instead of recommending"),
]
# Same list as the chatbot eval's PLANT_TERMS.
_PLANT = re.compile(r"\b(?:leaf|leaves|stems?|wilt\w*|stunted|yellowing)\b", re.I)
_ID = re.compile(r"S\d+", re.I)


def evidence_ids(raw) -> list[str]:
    """['S1', 'S3'] from ["S1", "[S3]", "s3"] or "S1, S3"."""
    if isinstance(raw, str):
        raw = [raw]
    out = []
    for x in raw or []:
        for m in _ID.findall(str(x)):
            sid = m.upper()
            if sid not in out:
                out.append(sid)
    return out


_scope = threading.local()


@contextmanager
def crop_scope(user_id: int):
    """While active, style_problem() also rejects crops the user doesn't have (ai_text_guard)."""
    from app.utils import ai_text_guard
    try:
        _scope.value = ai_text_guard.user_scope(user_id)
    except Exception:
        _scope.value = None
    try:
        yield
    finally:
        _scope.value = None


def style_problem(text: str) -> str | None:
    from app.utils import ai_text_guard
    for pat, label in _STYLE:
        if pat.search(text or ""):
            return label
    problem = ai_text_guard.draft_problem(text)          # leaked model drafts
    if problem:
        return problem
    scope = getattr(_scope, "value", None)
    if scope:
        return ai_text_guard.crop_problem(text, scope["allowed_crops"],
                                          set(scope["known_crops"]) | set(ai_text_guard._EXTRA_CROPS),
                                          scope["field_names"], scope.get("not_feasible_crops", ()))
    return None


def check(texts: list[str], evidence: list[str], signals_by_id: dict, bare_fields: set,
          extra_dates: tuple = ()) -> str | None:
    """None if the item may be shown, else the reason it is dropped."""
    if not evidence:
        return "no evidence"
    unknown = [e for e in evidence if e not in signals_by_id]
    if unknown:
        return f"unknown evidence {', '.join(unknown)}"
    text = " ".join(t for t in texts if t)
    allowed = {date.fromisoformat(d) for e in evidence for d in signals_by_id[e]["dates"]} | set(extra_dates)
    outside = dates_outside(text, allowed)
    if outside:
        return "date not in its evidence: " + ", ".join(f"{d}/{m}" for d, m in outside)
    problem = style_problem(text)
    if problem:
        return f"style: {problem}"
    if _PLANT.search(text):
        cited_fields = {f for e in evidence for f in signals_by_id[e]["sources"]["fields"]}
        if (cited_fields & bare_fields) or (not cited_fields and bare_fields):
            return "plant terms (leaves/stems) on a bare field"
    return None


def based_on(evidence: list[str], signals_by_id: dict, limit: int = 4) -> list[str]:
    """Short evidence labels for the UI: 'Sow Cotton 9 May', 'showers 7–8 May'."""
    labels = []
    for e in evidence:
        for label in signals_by_id[e]["labels"][:2]:
            if label not in labels:
                labels.append(label)
    return labels[:limit]
