"""Dates written in AI text: find them so a guard can drop text that names a date the facts
don't contain (plan task explanations, task insights, farm report)."""
import re

_MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
_MON = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"
# A month followed by a number with a unit is not a date: "8 May 4 mm" is not "May 4".
_NOT_UNIT = r"(?!\s*(?:mm|cm|m\b|°|%|h\b|hours?\b|kg|km|days?\b))"
DATE_PATTERNS = [
    (re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?" + _MON, re.I), "dm"),    # 9 May, 9th May
    (re.compile(r"\b" + _MON + r"\s+(\d{1,2})(?:st|nd|rd|th)?\b" + _NOT_UNIT, re.I), "md"),   # May 9, May 9th
    (re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b"), "ymd"),                          # 2027-05-09
    (re.compile(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b"), "d/m"),                   # 09/05, 09/05/2027
]
# The other end of a range: "7–8 May" / "7 and 8 May" (→ 7 May), "May 7–8" (→ 8 May).
_SEP = r"\s*(?:–|—|-|to|and|&)\s*"
_RANGES = [
    (re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?" + _SEP + r"\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?" + _MON, re.I),
     "first"),
    (re.compile(r"\b" + _MON + r"\s+\d{1,2}(?:st|nd|rd|th)?" + _SEP + r"(\d{1,2})(?:st|nd|rd|th)?\b" + _NOT_UNIT, re.I),
     "second"),
]


def dates_in(text: str) -> list[tuple[int, int]]:
    """(day, month) of every date written in the text, including both ends of a range.
    Numbers with units (50 mm, 30 °C, 8 h) are not dates."""
    found = []
    for pat, kind in DATE_PATTERNS:
        for m in pat.finditer(text or ""):
            try:
                if kind == "dm":
                    d, mo = int(m.group(1)), _MONTHS.index(m.group(2).lower()[:3]) + 1
                elif kind == "md":
                    mo, d = _MONTHS.index(m.group(1).lower()[:3]) + 1, int(m.group(2))
                elif kind == "ymd":
                    mo, d = int(m.group(2)), int(m.group(3))
                else:
                    d, mo = int(m.group(1)), int(m.group(2))
            except ValueError:
                continue
            if 1 <= d <= 31 and 1 <= mo <= 12:
                found.append((d, mo))
    for pat, kind in _RANGES:
        for m in pat.finditer(text or ""):
            if kind == "first":
                d, mo = int(m.group(1)), _MONTHS.index(m.group(2).lower()[:3]) + 1
            else:
                d, mo = int(m.group(2)), _MONTHS.index(m.group(1).lower()[:3]) + 1
            if 1 <= d <= 31:
                found.append((d, mo))
    return found


def dates_outside(text: str, allowed) -> list[tuple[int, int]]:
    """(day, month) of every date in the text that is not in `allowed` (dates or (day, month))."""
    ok = {(a.day, a.month) if hasattr(a, "day") else tuple(a) for a in allowed}
    return [dm for dm in dates_in(text) if dm not in ok]
