"""Live-demo switches, read from the environment.

DEMO_ADMIN_ENABLED (default off): Flask-Admin (/admin), the "Refresh Data" reseed
(POST /mytasks/<id>/run-refresh-data) and the AI prompt test page (/test/ai). Only
"true" turns them on, so a forgotten variable on Render keeps them off.

SIMULATOR_COOLDOWN_SECONDS (default 30): minimum time between two Weather Change
Simulator runs per user (each run makes an AI call). 0 disables the cooldown.

"Reset demo" (POST /mytasks/<id>/reset-demo) is allowed on the live demo: it only reseeds
the demo data, at most once per 60 s for the whole app.
"""
import os
import threading
import time

_last_run = {}            # user_id -> time.monotonic() of the last accepted run (1 gunicorn worker)
_last_reset = [None]      # time.monotonic() of the last accepted "Reset demo" (global: it reseeds everyone)
_lock = threading.Lock()
RESET_COOLDOWN_SECONDS = 60


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


def reset_wait_seconds() -> int:
    """0 = "Reset demo" may run now (the run is recorded); else seconds left to wait.
    Works without DEMO_ADMIN_ENABLED; one reset per RESET_COOLDOWN_SECONDS for the whole app."""
    now = time.monotonic()
    with _lock:
        last = _last_reset[0]
        if last is not None and now - last < RESET_COOLDOWN_SECONDS:
            return max(1, int(RESET_COOLDOWN_SECONDS - (now - last) + 0.999))
        _last_reset[0] = now
        return 0


def simulator_remaining(user_id: int) -> int:
    """Seconds until the simulator may run again for this user (read-only, nothing recorded)."""
    cooldown = simulator_cooldown_seconds()
    with _lock:
        last = _last_run.get(user_id)
    if not cooldown or last is None:
        return 0
    return max(0, int(cooldown - (time.monotonic() - last) + 0.999))


def reset_remaining() -> int:
    """Seconds until "Reset demo" may run again (read-only, nothing recorded)."""
    with _lock:
        last = _last_reset[0]
    if last is None:
        return 0
    return max(0, int(RESET_COOLDOWN_SECONDS - (time.monotonic() - last) + 0.999))
