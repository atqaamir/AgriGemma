"""Demo clock: the single source of "today" for planning, weather, tasks, jobs and seeders.

Set DEMO_TODAY=YYYY-MM-DD in the environment to run the app on a simulated date
(e.g. a day in the Kharif season, which the rule base covers). Empty or unset
means the real date. Timestamps (created_at, job start/end) keep using the real clock.
"""
import os
from datetime import date, datetime


def demo_today() -> date | None:
    """The simulated date from DEMO_TODAY, or None when it is unset or empty.
    A non-empty invalid value raises ValueError."""
    raw = (os.getenv("DEMO_TODAY") or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValueError(f"DEMO_TODAY must be a date like 2027-05-05 (or empty), got {raw!r}") from None


def today() -> date:
    """Today's date for the app: DEMO_TODAY if set, else the real date."""
    return demo_today() or date.today()


def now() -> datetime:
    """The current time on today()'s date (real time of day)."""
    return datetime.combine(today(), datetime.now().time())


def cropping_season(d: date) -> str:
    """Pakistan's cropping season for a date: Kharif (Apr–Oct) or Rabi (Nov–Mar)."""
    return "Kharif" if 4 <= d.month <= 10 else "Rabi"
