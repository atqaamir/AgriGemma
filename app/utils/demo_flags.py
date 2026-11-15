"""Live-demo switches, read from the environment.

DEMO_ADMIN_ENABLED (default off): Flask-Admin (/admin), the "Refresh Data" reseed
(POST /mytasks/<id>/run-refresh-data) and the AI prompt test page (/test/ai). Only
"true" turns them on, so a forgotten variable on Render keeps them off.

SIMULATOR_COOLDOWN_SECONDS (default 30): minimum time between two Weather Change
Simulator runs per user (each run makes an AI call). 0 disables the cooldown.
"""
import os
import threading
import time

_last_run = {}            # user_id -> time.monotonic() of the last accepted run (1 gunicorn worker)
_lock = threading.Lock()


def admin_enabled() -> bool:
    return (os.getenv("DEMO_ADMIN_ENABLED") or "").strip().lower() == "true"


def simulator_cooldown_seconds() -> int:
    raw = (os.getenv("SIMULATOR_COOLDOWN_SECONDS") or "").strip()
    try:
        return max(0, int(raw)) if raw else 30
    except ValueError:
        return 30


def simulator_wait_seconds(user_id: int) -> int:
    """0 = the simulator may run now (the run is recorded); else seconds left to wait."""
    cooldown = simulator_cooldown_seconds()
    now = time.monotonic()
    with _lock:
        last = _last_run.get(user_id)
        if cooldown and last is not None and now - last < cooldown:
            return max(1, int(cooldown - (now - last) + 0.999))
        _last_run[user_id] = now
        return 0
