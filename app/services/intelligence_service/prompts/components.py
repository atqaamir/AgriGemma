"""
Reusable Gemma-optimized prompt components.

Each function accepts a data dict and returns a compact labelled string
(or empty string when data is absent — callers skip empty blocks).

Design rules for Gemma 4:
  - Labelled sections [LIKE THIS] — not JSON blobs
  - One fact per line with exactly the signal Gemma needs
  - No prose filler ("the following shows...", "as you can see...")
  - Numbers always inline (moisture 28%, not "moisture level is 28 percent")
  - Empty string on missing data — never inject "N/A" placeholders
"""

from __future__ import annotations

from app.services.intelligence_service.context.token_budget import truncate, BUDGET_TASK_DESC


# ── Weather ────────────────────────────────────────────────────────────────────

def weather_block(weather: dict, days: int = 3) -> str:
    """Current conditions + N forecast days."""
    if not weather:
        return ""

    current  = weather.get("current") or {}
    forecast = (weather.get("forecast") or [])[:days]
    lines    = []

    if current:
        temp      = current.get("temp") or current.get("temperature_c") or "?"
        condition = current.get("condition") or "?"
        humidity  = current.get("humidity", "?")
        rain      = current.get("rainfall_mm") or current.get("precipitation_mm") or 0
        lines.append(f"  Now: {temp}°C, {condition}, {humidity}% humid, {rain}mm rain")

    if weather.get("heatwave_risk"):
        lines.append("  ⚠ Heatwave risk active")
    if weather.get("rain_expected") and not any(
        (f.get("rain_chance") or 0) >= 60 for f in forecast[:2]
    ):
        lines.append("  Rain expected soon")

    if forecast:
        fc_parts = []
        for f in forecast:
            day  = f.get("day") or f.get("date") or "?"
            cond = f.get("condition") or "?"
            rc   = f.get("rain_chance")
            tmax = f.get("max_temp_c")
            seg  = f"{day}: {cond}"
            if tmax is not None:
                seg += f" {tmax}°C"
            if rc is not None:
                seg += f" {rc}%🌧" if rc >= 40 else f" {rc}% rain"
            fc_parts.append(seg)
        lines.append("  Forecast: " + " | ".join(fc_parts))

    return "[WEATHER]\n" + "\n".join(lines) if lines else ""


def weather_signals(weather: dict, fields: list) -> str:
    """
    Actionable signals derived from the forecast.
    HIGH PRIORITY — Gemma should lead with these when present.
    Returns empty string when no actionable signal exists.
    """
    if not weather:
        return ""

    current   = weather.get("current") or {}
    forecast  = weather.get("forecast") or []
    heatwave  = weather.get("heatwave_risk", False)
    rain_soon = weather.get("rain_expected", False)
    temp      = current.get("temp") or current.get("temperature_c") or 0

    signals = []

    # Rain incoming → skip/reduce irrigation
    rain_days = [f for f in forecast[:3] if (f.get("rain_chance") or 0) >= 60]
    if rain_days:
        days_str = " & ".join(d.get("day", "?") for d in rain_days[:2])
        signals.append(f"RAIN INCOMING ({days_str}): skip/reduce irrigation — natural moisture coming")
    elif rain_soon:
        signals.append("RAIN EXPECTED: hold off irrigation until after rainfall")

    # Heatwave → urgent irrigation, no fertilizing
    if heatwave:
        signals.append(f"HEATWAVE ({temp}°C): increase irrigation frequency, avoid fertilizing during peak heat")
        for f in (fields or []):
            m = f.get("moisture_level") or 0
            if m < 40:
                signals.append(f"  → {f.get('name','?')}: moisture {m:.0f}% — irrigate urgently")

    # Dry window → harvest opportunity
    dry = [f for f in forecast[:4] if (f.get("rain_chance") or 0) < 25]
    if len(dry) >= 2:
        signals.append(
            f"DRY WINDOW ({dry[0].get('day','?')}–{dry[1].get('day','?')}): "
            "good window for harvesting ready crops"
        )
    elif forecast and (forecast[0].get("rain_chance") or 0) >= 60:
        signals.append("HARVEST CAUTION: rain today — delay grain harvest if possible")

    # Extreme heat → delay planting
    hot_days = [f for f in forecast[:3] if (f.get("max_temp_c") or 0) > 38]
    if hot_days:
        signals.append(
            f"PLANTING CAUTION: extreme heat ({hot_days[0].get('max_temp_c')}°C on "
            f"{hot_days[0].get('day','?')}) — delay sowing heat-sensitive crops"
        )

    if not signals:
        return ""

    return "[WEATHER SIGNALS — act on these first]\n" + "\n".join(f"  {s}" for s in signals)


# ── Fields ─────────────────────────────────────────────────────────────────────

def field_block(fields: list, limit: int = 4) -> str:
    """Compact field conditions — moisture, health, risk flags."""
    if not fields:
        return ""

    lines = []
    for f in fields[:limit]:
        name     = f.get("name") or "?"
        moisture = f.get("moisture_level")
        health   = f.get("health_status") or "?"
        disease  = f.get("disease_risk")
        stress   = f.get("stress_risk")

        parts = [f"  {name}:"]
        if moisture is not None:
            parts.append(f"moisture {moisture:.0f}%")
        parts.append(f"health {health}")
        if disease is not None and str(disease).lower() not in ("none", "low", "", "0", "0.0"):
            parts.append(f"disease-risk {disease}")
        if stress is not None and str(stress).lower() not in ("none", "low", "", "0", "0.0"):
            parts.append(f"stress {stress}")
        lines.append(" ".join(parts))

    return "[FIELDS]\n" + "\n".join(lines)


# ── Crops ──────────────────────────────────────────────────────────────────────

def crop_block(crops: list, limit: int = 4) -> str:
    """Compact crop status — name, field, stage, moisture, water needs."""
    if not crops:
        return ""

    lines = []
    for c in crops[:limit]:
        name      = c.get("name") or "?"
        stage     = c.get("growth_stage") or "?"
        field_nm  = c.get("field_name") or ""
        moisture  = c.get("moisture_level")
        water_req = c.get("water_requirement") or ""

        line = f"  {name}"
        if field_nm:
            line += f" ({field_nm})"
        line += f": {stage} stage"
        if moisture is not None:
            line += f", soil {moisture:.0f}%"
        if water_req and str(water_req).lower() not in ("none", "?", ""):
            line += f", water-need {water_req}"
        lines.append(line)

    return "[CROPS]\n" + "\n".join(lines)


# ── Tasks ──────────────────────────────────────────────────────────────────────

def task_block(tasks: dict, limit: int = 6, show_description: bool = True) -> str:
    """
    Compact task list with overdue/critical badges.
    Overdue tasks always rendered first (sorted by context_builder).
    """
    if not tasks:
        return ""

    pending = tasks.get("pending_list") or []
    if not pending:
        return ""

    counts = []
    if tasks.get("pending_count"):
        counts.append(f"{tasks['pending_count']} pending")
    if tasks.get("overdue_count"):
        counts.append(f"{tasks['overdue_count']} overdue")
    if tasks.get("critical_count"):
        counts.append(f"{tasks['critical_count']} critical")

    header = "[TASKS] " + ", ".join(counts) if counts else "[TASKS]"
    lines  = [header]

    for t in pending[:limit]:
        priority = (t.get("priority") or "medium").upper()
        title    = t.get("title") or "?"
        location = t.get("field_name") or t.get("crop_name") or ""
        due      = t.get("due_date") or ""
        overdue  = t.get("is_overdue", False)
        desc     = t.get("description") or ""

        badge = f"[{priority}]" + ("⚠" if overdue else "")
        line  = f"  {badge} {title}"
        if location:
            line += f" — {location}"
        if due and not overdue:
            line += f" (due {due})"
        elif overdue:
            line += " [OVERDUE]"
        lines.append(line)

        if show_description and desc:
            lines.append(f"    → {truncate(desc, BUDGET_TASK_DESC)}")

    return "\n".join(lines)


# ── Alerts ─────────────────────────────────────────────────────────────────────

def alert_block(alerts: list, limit: int = 4) -> str:
    """Compact active alerts."""
    if not alerts:
        return ""

    lines = ["[ALERTS]"]
    for a in alerts[:limit]:
        level = (a.get("level") or "medium").upper()
        msg   = a.get("message") or "?"
        field = a.get("field_name") or ""
        line  = f"  [{level}] {msg}"
        if field:
            line += f" ({field})"
        lines.append(line)

    return "\n".join(lines)


# ── Rules ──────────────────────────────────────────────────────────────────────

def rules_block(rules: str, max_chars: int = 450) -> str:
    """
    Compact rules block — strips the verbose header, hard-caps length.
    Gemma reads rules best as plain indented text (not JSON, not markdown table).
    """
    if not rules:
        return ""

    cleaned = rules.replace(
        "RULEBOOK DATA (cite these numbers when explaining why a task was created):", ""
    ).strip()

    return "[RULES]\n" + truncate(cleaned, max_chars)


# ── Climate ────────────────────────────────────────────────────────────────────

def climate_block(climate: dict, message: str = "") -> str:
    """
    Extract only the climate slice relevant to the farmer's message.
    Avoids dumping the full 12-month profile into the prompt.
    """
    if not climate:
        return ""

    m     = message.lower()
    parts = []
    region = climate.get("region") or ""

    _MONTH_NAMES = {
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
    }
    yearly = climate.get("yearly") or []

    def _month_by_name(name: str) -> dict | None:
        return next((md for md in yearly if md.get("name", "").lower() == name.lower()), None)

    def _month_line(md: dict, tag: str = "") -> str:
        sfx   = f" ({tag})" if tag else ""
        notes = md.get("farming_notes") or ""
        return (
            f"  {md.get('name','?')}{sfx}: "
            f"{md.get('avg_max_temp_c','?')}°C max, "
            f"{md.get('avg_rainfall_mm','?')}mm rain"
            + (f". {notes}" if notes else "")
        )

    # Specific month mentioned in message
    for mn in _MONTH_NAMES:
        if mn in m:
            md = _month_by_name(mn)
            if md:
                parts.append(_month_line(md))
            break

    # Sowing / planting intent
    if any(w in m for w in ("plant", "sow", "seed", "germina")):
        sow_months = climate.get("best_sowing_months") or []
        if sow_months:
            parts.append(f"  Best sowing: {', '.join(sow_months)}")
            for mn in sow_months[:2]:
                md = _month_by_name(mn)
                if md:
                    parts.append(_month_line(md))

    # Harvest intent
    if any(w in m for w in ("harvest", "pick", "ready", "ripen")):
        harv_months = climate.get("best_harvest_months") or []
        if harv_months:
            parts.append(f"  Best harvest: {', '.join(harv_months)}")
            for mn in harv_months[:2]:
                md = _month_by_name(mn)
                if md:
                    parts.append(_month_line(md))

    # Monsoon
    if any(w in m for w in ("monsoon", "rainy season", "when does it rain")):
        mon_months = climate.get("monsoon_months") or []
        if mon_months:
            parts.append(f"  Monsoon: {', '.join(mon_months)}")

    # Current month context (only if explicitly asked)
    if any(w in m for w in ("this month", "right now", "this season", "can i plant", "can i grow")):
        cur = climate.get("current_month")
        if cur:
            parts.append(_month_line(cur, "now"))
        nxt = climate.get("next_month")
        if nxt and any(w in m for w in ("plan", "next", "upcoming", "prepare")):
            parts.append(_month_line(nxt, "next month"))

    if not parts:
        return ""

    header = f"[CLIMATE — {region}]" if region else "[CLIMATE]"
    return header + "\n" + "\n".join(parts)
