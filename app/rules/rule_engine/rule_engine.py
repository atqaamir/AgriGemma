# Generate crop rules knowlage base here
# This file contains logic ONLY

import json
import random
import calendar
from datetime import date, timedelta
from app.services.rule_base_service import rule_base_service


class RuleEngine:

    # @staticmethod
    # def evaluate_sowing(rain_mm: float, crop: str) -> dict:
    #     sowing_rules = rule_base_service.get_sowing_rules(crop)

    #     threshold = sowing_rules.get("rain_threshold_mm", 15)

    #     if rain_mm > threshold:
    #         return {
    #             "action": "delay_sowing",
    #             "reason": "heavy_rain",
    #             "risk": "high"
    #         }

    #     return {
    #         "action": "proceed",
    #         "risk": "low"
    #     }
    

    #     @staticmethod
    # def adjust_plan_for_rain(plan: dict, rain_mm: float, crop: str) -> dict:
    #     sowing_decision = RuleEngine.evaluate_sowing(rain_mm, crop)

    #     if sowing_decision["action"] == "delay_sowing":
    #         new_sowing = plan["sowing"] + timedelta(days=4)

    #         return {
    #             "old_plan": plan,
    #             "new_plan": {
    #                 **plan,
    #                 "sowing": new_sowing
    #             },
    #             "change": "sowing_delayed_due_to_rain"
    #         }

    #     return {
    #         "old_plan": plan,
    #         "new_plan": plan,
    #         "change": "no_change"
    #     }


    @staticmethod
    def generate_initial_plan(crop: str, soil_type: str, water_source: str, growth_stage: str = "Seedling") -> dict:

        def _random_date_in_month(year, month):
            days_in_month = calendar.monthrange(year, month)[1]
            return date(year, month, random.randint(1, days_in_month))

        def _month_set(start, end):
            if start <= end:
                return set(range(start, end + 1))
            return set(range(start, 13)) | set(range(1, end + 1))

        today = date.today()

        # Step 1: Best Suited Season for Crop Type
        best_season_crop_type = rule_base_service.get_best_season_by_crop_type(crop)

        # Step 2: Best Suited Season for Crop
        best_season_crop = rule_base_service.get_best_season_by_crop(crop)

        crop_type_id = rule_base_service.get_crop_type_by_crop(crop)
        crop_type_timeline = rule_base_service.get_timeline_by_crop_type(crop_type_id)

        # Step 3: Sowing & harvesting dates: Compare if same season above:
        if best_season_crop_type == best_season_crop:
            # Step 3a: Season months and crop_type months for sowing & Harvesting
            season_months = rule_base_service.get_month_by_season(best_season_crop_type)
            season_m_set = _month_set(season_months["start"], season_months["end"])
            crop_type_sow_set = _month_set(crop_type_timeline.sow_start_month, crop_type_timeline.sow_end_month)
            crop_type_harvest_set = _month_set(crop_type_timeline.harvest_start_month, crop_type_timeline.harvest_end_month)

                # Step 4: Compare if same:
            if season_m_set == crop_type_sow_set:
                    # Step 4a: Random date for sowing in the early month
                sowing_month = crop_type_timeline.sow_start_month
            else:
                    # Step 4b: Random date in the intersecting month
                sow_intersection = season_m_set & crop_type_sow_set
                sowing_month = min(sow_intersection) if sow_intersection else crop_type_timeline.sow_start_month

            if season_m_set == crop_type_harvest_set:
                    # Step 4a: Random date for harvesting in the early month
                harvesting_month = crop_type_timeline.harvest_start_month
            else:
                    # Step 4b: Random date in the intersecting month
                harvest_intersection = season_m_set & crop_type_harvest_set
                harvesting_month = min(harvest_intersection) if harvest_intersection else crop_type_timeline.harvest_start_month
        else:
            # Step 3b: Season months (according to crop instead of crop_type)
            season_months = rule_base_service.get_month_by_season(best_season_crop)
                #Step 4: Random date for sowing in the early month
            sowing_month = season_months["start"]
            harvesting_month = crop_type_timeline.harvest_start_month

        sowing_year = today.year if sowing_month >= today.month else today.year + 1
        harvest_year = sowing_year if harvesting_month >= sowing_month else sowing_year + 1
        sowing_date = _random_date_in_month(sowing_year, sowing_month)
        harvesting_date = _random_date_in_month(harvest_year, harvesting_month)

        crop_id = rule_base_service.get_crop_by_name(crop).id
        soil_type_id = rule_base_service.get_soil_by_name(soil_type).id
        growth_stage_id = rule_base_service.get_stage_by_name(growth_stage).id

        # Step 5: Get Irrigation timeline for crop
        irrigation_calendar = rule_base_service.get_irrigation_calendar_by_crop(crop_id)
        irrigation_start_date = (sowing_date + timedelta(days=irrigation_calendar.days_after_sowing)).strftime("%m/%d/%Y") if irrigation_calendar else None

        # Step 6: Get irrigation frequency for crop (fallback: stage+soil → stage → crop)
        irrigation_freq_rule = rule_base_service.get_irrigation_frequency_with_fallback(crop_id, growth_stage_id)
        irrigation_frequency = irrigation_freq_rule.recommended_frequency if irrigation_freq_rule else None

        fertilization_calendar = rule_base_service.get_fertilization_calendar_by_crop(crop_id)
        fertilization_date = (sowing_date + timedelta(days=fertilization_calendar.days_after_sowing)).strftime("%m/%d/%Y") if fertilization_calendar else None

        return {
            "crop": crop,
            "soil_type": soil_type,
            "water_source": water_source,
            "growth_stage": growth_stage,
            "sowing": sowing_date.strftime("%m/%d/%Y"),
            "harvesting": harvesting_date.strftime("%m/%d/%Y"),
            "irrigation_start_date": irrigation_start_date,
            "irrigation_frequency": irrigation_frequency,
            "fertilization_date": fertilization_date,
        }
    
    @staticmethod
    def adjust_initial_plan(initial_plan):
        import json

        def _parse_date(date_str):
            if not date_str:
                return None
            m, d, y = date_str.split('/')
            return date(int(y), int(m), int(d))

        def _fmt_date(d):
            return d.strftime("%m/%d/%Y") if d else None

        def _shift_date(date_str, days):
            parsed = _parse_date(date_str)
            return _fmt_date(parsed + timedelta(days=days)) if parsed else None

        def _apply_actions(actions_json, plan, crop, context_name, context_label, adjustments):
            """context_name  = e.g. 'Sandy' or 'River'
               context_label = 'soil type' | 'water source'
            """
            actions = json.loads(actions_json) if isinstance(actions_json, str) else actions_json

            # Loop over actions (as there might be more than one)
            for action in actions:
                action_type = action.get("action_type", "")
                adjustment  = action.get("adjustment", "")
                adj_type    = action.get("adjustment_type", "")

                # if "action_type": "irrigation" &
                #    "adjustment": "increase days"/"decrease days" &
                #    "adjustment_type": "minimal" -> increase irrigation_frequency +/- 2 (depending on increase or decrease)
                #    "adjustment_type": "significant" -> +/- 4
                #    add "adjustments_to_make": "increase/decrease irrigation days since {crop} is not compatible with {context_name}"
                if action_type == "irrigation":
                    delta = 2 if adj_type == "minimal" else 4
                    if adjustment == "increase days":
                        plan["irrigation_frequency"] = (plan["irrigation_frequency"] or 0) + delta
                        adjustments.append(f"{crop} is not well-suited to {context_name} {context_label} - irrigation frequency increased by {delta}")
                    elif adjustment == "decrease days":
                        plan["irrigation_frequency"] = max(0, (plan["irrigation_frequency"] or 0) - delta)
                        adjustments.append(f"{crop} is not well-suited to {context_name} {context_label} - irrigation frequency decreased by {delta}")

                # if "action_type": "sowing", "adjustment": "delay", "adjustment_type": "minimal" -> add +4 days to sowing date, for substantial add 1 week
                # cascades to harvesting, irrigation start, and fertilization dates
                elif action_type == "sowing" and adjustment == "delay":
                    days = 4 if adj_type == "minimal" else 7
                    plan["sowing"]                = _shift_date(plan["sowing"], days)
                    plan["harvesting"]            = _shift_date(plan["harvesting"], days)
                    plan["irrigation_start_date"] = _shift_date(plan["irrigation_start_date"], days)
                    plan["fertilization_date"]    = _shift_date(plan["fertilization_date"], days)
                    adjustments.append(f"{crop} sowing delayed by {days} days due to {context_name} {context_label} - harvesting, irrigation and fertilization dates shifted accordingly")

                elif action_type == "fertilization":
                    if adjustment == "increase quantity":
                        adjustments.append(f"{crop} requires increased fertilization on {context_name} {context_label}")
                    elif adjustment == "decrease quantity":
                        adjustments.append(f"{crop} requires reduced fertilization on {context_name} {context_label}")

                # if "action_type": "harvesting", "adjustment": "delay", "adjustment_type": "minimal" same as above add to harvesting date
                elif action_type == "harvesting" and adjustment == "delay":
                    days = 4 if adj_type == "minimal" else 7
                    plan["harvesting"] = _shift_date(plan["harvesting"], days)
                    adjustments.append(f"{crop} harvesting delayed by {days} days due to {context_name} {context_label} - please plan accordingly")

                # if "action_type": "avoid": nullify all dates
                # add "adjustments_to_make" "The crop and soil_type is extremely incompatible: Please consider a different field or a different crop"
                elif action_type == "avoid":
                    plan["sowing"]                = None
                    plan["harvesting"]            = None
                    plan["irrigation_start_date"] = None
                    plan["fertilization_date"]    = None
                    adjustments.append(f"{crop} is extremely incompatible with {context_name} {context_label} - please consider a different field or a different crop")
                    break

            return plan

        adjusted_plan        = dict(initial_plan)
        adjustments_to_make  = []

        crop         = adjusted_plan["crop"]
        soil_type    = adjusted_plan["soil_type"]
        water_source = adjusted_plan["water_source"]

        crop_id         = rule_base_service.get_crop_by_name(crop).id
        soil_type_id    = rule_base_service.get_soil_by_name(soil_type).id
        water_source_id = rule_base_service.get_water_source_by_name(water_source).id

        # Step 1: Check soil_type compatibility rulebook: if score<0.7 then needs adjustment
        #       Check for Crop-Soil_Type combination in actions rulebook -> get actions (json)
        soil_compat = rule_base_service.get_crop_soil_compatibility_by_crop_and_soil(crop_id, soil_type_id)
        if soil_compat and soil_compat.score < 0.7:
            soil_action = rule_base_service.get_soil_action_by_crop_and_soil(crop_id, soil_type_id)
            if soil_action and soil_action.actions:
                adjusted_plan = _apply_actions(soil_action.actions, adjusted_plan, crop, soil_type, "soil type", adjustments_to_make)

        # Step 2: Check water_source compatibility: if score <0.7 then needs adjustment
        #     same as above for crop_water source compatibility
        water_compat = rule_base_service.get_water_source_compatibility_by_crop_and_source(crop_id, water_source_id)
        if water_compat and water_compat.score < 0.7:
            water_action = rule_base_service.get_water_source_action_by_crop_and_source(crop_id, water_source_id)
            if water_action and water_action.actions:
                adjusted_plan = _apply_actions(water_action.actions, adjusted_plan, crop, water_source, "water source", adjustments_to_make)

        # adjusted plan has crop, soil_type, water_source, growth_stage, sowing, harvesting, irrigation start, irrigation_frequency, fertilization_start, adjustments_to_make
        adjusted_plan["adjustments_to_make"] = adjustments_to_make

        return adjusted_plan

    # ------------------------------------------------------------------ #
    #  Weekly Planner
    # ------------------------------------------------------------------ #

    @staticmethod
    def classify_value_bands(factor: str, value: float) -> str:
        """Map a numeric climate/soil reading to its rule-book band string.

        Clamps to the nearest defined band for out-of-range values.

        Bands per factor
        ----------------
        temperature   : "15-20" | "20-30" | "30-40"
        humidity      : "<40"   | "40-70" | ">70"
        soil_moisture : "<30"   | "30-60" | ">60"
        ph_level      : "<6.5"  | "6.5-7.5" | ">7.5"
        sunlight      : "<4"    | "4-8"   | ">8"
        rainfall      : "<50"   | "50-100" | "100-200" | "200-300" | ">300"
        """
        if factor == "temperature":
            if value <= 20:  return "15-20"
            if value <= 30:  return "20-30"
            return "30-40"

        if factor == "humidity":
            if value < 40:   return "<40"
            if value <= 70:  return "40-70"
            return ">70"

        if factor == "soil_moisture":
            if value < 30:   return "<30"
            if value <= 60:  return "30-60"
            return ">60"

        if factor == "ph_level":
            if value < 6.5:  return "<6.5"
            if value <= 7.5: return "6.5-7.5"
            return ">7.5"

        if factor == "sunlight":
            if value < 4:    return "<4"
            if value <= 8:   return "4-8"
            return ">8"

        if factor == "rainfall":
            if value < 50:   return "<50"
            if value < 100:  return "50-100"
            if value < 200:  return "100-200"
            if value < 300:  return "200-300"
            return ">300"

        raise ValueError(f"classify_value_bands: unknown factor '{factor}'")

    # ------------------------------------------------------------------ #

    @staticmethod
    def generate_weekly_plan(user_id: int, week_start_date: date) -> list:
        """Return raw weekly events (no climate adjustments) for all active crop
        entries in the user's active seasonal plan within the target week.

        Falls back to the Crop model if no active seasonal plan exists.

        Each item in the returned list has
        ──────────────────────────────────
        crop_id, crop_name, field_id, field_name,
        field_location, field_moisture, field_ph,   ← consumed by adjust_weekly_plan
        growth_stage_id, growth_stage,
        week_events: [{ event_type, date }]          ← sorted ascending by date
        """
        from app.models.seasonal_plan import SeasonalPlan
        from app.models.crop import Crop
        from app.models.field import Field

        week_end = week_start_date + timedelta(days=6)

        def _parse(s):
            """'MM/DD/YYYY' → date, or None."""
            if not s:
                return None
            m, d, y = s.split('/')
            return date(int(y), int(m), int(d))

        def _recurring_dates(start, interval_days, win_start, win_end):
            """All occurrences of a recurring event (start + n*interval) inside [win_start, win_end]."""
            if not start or interval_days <= 0 or start > win_end:
                return []
            results = []
            i = 0
            while True:
                d = start + timedelta(days=round(i * interval_days))
                if d > win_end:
                    break
                if d >= win_start:
                    results.append(d)
                i += 1
            return results

        result = []

        # ── Seasonal plan path ─────────────────────────────────────────────
        seasonal_plan = SeasonalPlan.query.filter_by(
            user_id=user_id, currently_active=True
        ).first()

        if seasonal_plan:
            for entry in seasonal_plan.entries:
                if not entry.sowing:          # infeasible entry — skip
                    continue

                field = Field.query.get(entry.field_id) if entry.field_id else None

                crop_obj        = rule_base_service.get_crop_by_id(entry.crop_id)
                crop_name       = crop_obj.name if crop_obj else f"Crop {entry.crop_id}"
                field_name      = field.name          if field else f"Field {entry.field_id}"
                field_location  = field.location      if field else None
                field_moisture  = field.moisture_level if field else None
                field_ph        = field.ph_level       if field else None

                growth_stage_id   = seasonal_plan.growth_stage_id
                growth_stage_obj  = rule_base_service.get_stage_by_id(growth_stage_id) if growth_stage_id else None
                growth_stage_name = growth_stage_obj.name if growth_stage_obj else None

                week_events = []

                # Sowing
                sowing = _parse(entry.sowing)
                if sowing and week_start_date <= sowing <= week_end:
                    week_events.append({"event_type": "sowing", "date": sowing.isoformat()})

                # Irrigation — evenly spaced from start date, N times / week
                irr_start = _parse(entry.irrigation_start_date)
                if irr_start and entry.irrigation_frequency and entry.irrigation_frequency > 0:
                    interval = 7.0 / entry.irrigation_frequency
                    for d in _recurring_dates(irr_start, interval, week_start_date, week_end):
                        week_events.append({"event_type": "irrigation", "date": d.isoformat()})

                # Fertilization — one-time event if it falls in the current week
                ferti_start = _parse(entry.fertilization_date)
                if ferti_start and week_start_date <= ferti_start <= week_end:
                    week_events.append({"event_type": "fertilization", "date": ferti_start.isoformat()})

                # Harvesting
                harvesting = _parse(entry.harvesting)
                if harvesting and week_start_date <= harvesting <= week_end:
                    week_events.append({"event_type": "harvesting", "date": harvesting.isoformat()})

                if not week_events:
                    continue

                week_events.sort(key=lambda e: e["date"])

                result.append({
                    "crop_id":        entry.crop_id,
                    "crop_name":      crop_name,
                    "field_id":       entry.field_id,
                    "field_name":     field_name,
                    "field_location": field_location,
                    "field_moisture": field_moisture,
                    "field_ph":       field_ph,
                    "growth_stage_id":  growth_stage_id,
                    "growth_stage":     growth_stage_name,
                    "week_events":      week_events,
                })

        # ── Crop model fallback ────────────────────────────────────────────
        # Runs when: (a) no active seasonal plan exists, OR (b) the seasonal
        # plan exists but none of its entries have events in the current week
        # (e.g. all dates are in the future / past).
        if not result:
            crops = Crop.query.filter_by(user_id=user_id, currently_active=True).all()
            for crop in crops:
                field      = Field.query.get(crop.field_id) if crop.field_id else None
                crop_obj   = rule_base_service.get_crop_by_id(crop.crop_name_id)
                crop_name  = crop_obj.name if crop_obj else f"Crop {crop.crop_name_id}"
                field_name = field.name if field else f"Field {crop.field_id}"

                planting   = crop.planting_date
                stage_id   = crop.current_growth_stage_id

                week_events = []

                # Sowing (planting date)
                if planting and week_start_date <= planting <= week_end:
                    week_events.append({"event_type": "sowing", "date": planting.isoformat()})

                # Irrigation — derive schedule from rulebook, fall back to every 3 days
                irr_cal = rule_base_service.get_irrigation_calendar_by_crop(crop.crop_name_id)
                irr_days_after = irr_cal.days_after_sowing if irr_cal else None

                freq_rule = rule_base_service.get_irrigation_frequency_with_fallback(
                    crop.crop_name_id, stage_id
                )
                frequency = freq_rule.recommended_frequency if freq_rule else None

                if planting and irr_days_after is not None:
                    irr_start = planting + timedelta(days=irr_days_after)
                elif planting:
                    irr_start = planting   # start from planting if no calendar entry
                else:
                    irr_start = None

                if irr_start:
                    interval = (7.0 / frequency) if (frequency and frequency > 0) else 3.0
                    for d in _recurring_dates(irr_start, interval, week_start_date, week_end):
                        week_events.append({"event_type": "irrigation", "date": d.isoformat()})

                # Fertilization — derive from rulebook, fall back to every 14 days from planting
                ferti_cal = rule_base_service.get_fertilization_calendar_by_crop(crop.crop_name_id)
                ferti_days_after = ferti_cal.days_after_sowing if ferti_cal else None

                if planting and ferti_days_after is not None:
                    ferti_start = planting + timedelta(days=ferti_days_after)
                elif planting:
                    ferti_start = planting
                else:
                    ferti_start = None

                # Fertilization — one-time event if it falls in the current week
                if ferti_start and week_start_date <= ferti_start <= week_end:
                    week_events.append({"event_type": "fertilization", "date": ferti_start.isoformat()})

                # Harvesting
                if crop.expected_harvest_date and week_start_date <= crop.expected_harvest_date <= week_end:
                    week_events.append({"event_type": "harvesting", "date": crop.expected_harvest_date.isoformat()})

                if not week_events:
                    continue

                week_events.sort(key=lambda e: e["date"])

                result.append({
                    "crop_id":        crop.crop_name_id,
                    "crop_name":      crop_name,
                    "field_id":       crop.field_id,
                    "field_name":     field_name,
                    "field_location": field.location       if field else None,
                    "field_moisture": field.moisture_level if field else None,
                    "field_ph":       field.ph_level       if field else None,
                    "growth_stage_id":  stage_id,
                    "growth_stage":     crop.growth_stage,
                    "week_events":      week_events,
                })

        return result

    # ------------------------------------------------------------------ #

    @staticmethod
    def adjust_weekly_plan(weekly_plan: list) -> list:
        """Apply climate action rules to each event in the weekly plan.

        For every event date, fetches the daily weather for the field's location,
        classifies all 6 factor values into bands, looks up the action rulebooks,
        and applies adjustments — mirroring adjust_initial_plan but for a live week.

        Key differences from adjust_initial_plan
        -----------------------------------------
        * "avoid" action_type  → max-delay + CRITICAL warning (no nullification —
          crop is already planted / activity must proceed).
        * Sowing / harvesting date shifts are applied per-event, not globally.
        * field_location / field_moisture / field_ph are stripped from final output.

        Returns the same list structure with climate_adjustments_made added
        to each week_event.
        """

        # Map factor → (weather model attribute, service lookup fn, human label)
        FACTORS = [
            ("temperature",   "avg_temperature_c",
             lambda c, g, b: rule_base_service.get_temperature_action_by_crop_and_range(c, g, b),
             "temperature"),
            ("humidity",      "humidity",
             lambda c, g, b: rule_base_service.get_humidity_action_by_crop_and_range(c, g, b),
             "humidity"),
            ("sunlight",      "sunlight_hours",
             lambda c, g, b: rule_base_service.get_sunlight_action_by_crop_and_range(c, g, b),
             "sunlight"),
            ("rainfall",      "rainfall_mm",
             lambda c, g, b: rule_base_service.get_rainfall_action_by_crop_and_range(c, g, b),
             "rainfall"),
            # Soil factors — value comes from Field, not weather row
            ("soil_moisture", None,
             lambda c, g, b: rule_base_service.get_soil_moisture_action_by_crop_and_range(c, g, b),
             "soil moisture"),
            ("ph_level",      None,
             lambda c, g, b: rule_base_service.get_ph_action_by_crop_and_category(c, g, b),
             "soil pH"),
        ]

        def _apply_action(action, adjusted_event, factor_label):
            """Apply a single action dict; return adjustment text (or None)."""
            action_type = action.get("action_type", "")
            adjustment  = action.get("adjustment", "")
            adj_type    = action.get("adjustment_type", "")
            event_type  = adjusted_event["event_type"]

            if action_type == "irrigation":
                delta = 1 if adj_type == "minimal" else 2
                if adjustment == "increase days":
                    return f"Increase irrigation frequency by {delta} day(s) this week"
                if adjustment == "decrease days":
                    return f"Decrease irrigation frequency by {delta} day(s) this week"

            elif action_type == "sowing" and adjustment == "delay" and event_type == "sowing":
                days = 4 if adj_type == "minimal" else 7
                if not adjusted_event.get("original_date"):
                    adjusted_event["original_date"] = adjusted_event["date"]
                adjusted_event["date"] = (
                    date.fromisoformat(adjusted_event["date"]) + timedelta(days=days)
                ).isoformat()
                return f"Sowing delayed by {days} days — unfavourable {factor_label} conditions"

            elif action_type == "harvesting" and adjustment == "delay" and event_type == "harvesting":
                days = 4 if adj_type == "minimal" else 7
                if not adjusted_event.get("original_date"):
                    adjusted_event["original_date"] = adjusted_event["date"]
                adjusted_event["date"] = (
                    date.fromisoformat(adjusted_event["date"]) + timedelta(days=days)
                ).isoformat()
                return f"Harvesting delayed by {days} days — unfavourable {factor_label} conditions"

            elif action_type == "fertilization":
                if adjustment == "increase quantity":
                    return f"Increase fertilization quantity — {factor_label} stress detected"
                if adjustment == "decrease quantity":
                    return f"Reduce fertilization quantity — {factor_label} conditions favour lower input"

            elif action_type == "monitoring":
                return f"[Monitor] {adjustment}"

            elif action_type == "spraying":
                return f"[Spray] {adjustment}"

            elif action_type == "avoid":
                # Crop is planted — apply max delay if applicable, issue critical warning
                if event_type in ("sowing", "harvesting"):
                    days = 7
                    if not adjusted_event.get("original_date"):
                        adjusted_event["original_date"] = adjusted_event["date"]
                    adjusted_event["date"] = (
                        date.fromisoformat(adjusted_event["date"]) + timedelta(days=days)
                    ).isoformat()
                return f"CRITICAL: {factor_label} conditions are severely unfavourable — immediate intervention required"

            return None

        adjusted_result = []

        for entry in weekly_plan:
            crop_id         = entry["crop_id"]
            growth_stage_id = entry.get("growth_stage_id")
            field_location  = entry.get("field_location")
            field_moisture  = entry.get("field_moisture")
            field_ph        = entry.get("field_ph")

            adjusted_entry = {k: v for k, v in entry.items()
                              if k not in ("field_location", "field_moisture", "field_ph")}
            adjusted_entry["week_events"] = []

            for event in entry["week_events"]:
                event_date    = date.fromisoformat(event["date"])
                adjusted_event = dict(event)           # work on a copy

                # Fetch daily weather for this field + date
                weather = rule_base_service.get_weather_by_region_and_date(
                    field_location, event_date
                ) if field_location else None

                climate_adjustments = []

                for factor, weather_attr, lookup_fn, factor_label in FACTORS:
                    # Resolve numeric value for this factor
                    if factor == "soil_moisture":
                        value = field_moisture
                    elif factor == "ph_level":
                        value = field_ph
                    elif weather and weather_attr:
                        value = getattr(weather, weather_attr, None)
                    else:
                        value = None

                    if value is None:
                        continue

                    band       = RuleEngine.classify_value_bands(factor, value)
                    action_rule = lookup_fn(crop_id, growth_stage_id, band)

                    if not action_rule:
                        continue

                    raw_actions = action_rule.actions
                    actions = (
                        json.loads(raw_actions)
                        if isinstance(raw_actions, str)
                        else (raw_actions or [])
                    )
                    if not actions:
                        continue

                    texts = []
                    for action in actions:
                        text = _apply_action(action, adjusted_event, factor_label)
                        if text:
                            texts.append(text)

                    if texts:
                        climate_adjustments.append({
                            "factor":     factor,
                            "reasoning":  getattr(action_rule, "reasoning", ""),
                            "adjustment": "; ".join(texts),
                        })

                # Generic fallback when all conditions are nominal
                if not climate_adjustments:
                    climate_adjustments.append({
                        "factor":     "general",
                        "reasoning":  "All climate conditions within acceptable ranges.",
                        "adjustment": "Proceed as planned; routine crop monitoring recommended",
                    })

                adjusted_event["climate_adjustments_made"] = climate_adjustments
                adjusted_entry["week_events"].append(adjusted_event)

            adjusted_result.append(adjusted_entry)

        return adjusted_result

