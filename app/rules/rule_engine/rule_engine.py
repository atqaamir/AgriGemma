# Generate crop rules knowlage base here
# This file contains logic ONLY

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

        # Step 6: Get Irigation frequency for crop
        irrigation_freq_rule = rule_base_service.get_irrigation_frequency_by_crop_stage_soil(crop_id, growth_stage_id, soil_type_id)
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
                        adjustments.append(f"{crop} is not well-suited to {context_name} {context_label} — irrigation frequency increased by {delta}")
                    elif adjustment == "decrease days":
                        plan["irrigation_frequency"] = max(0, (plan["irrigation_frequency"] or 0) - delta)
                        adjustments.append(f"{crop} is not well-suited to {context_name} {context_label} — irrigation frequency decreased by {delta}")

                # if "action_type": "sowing", "adjustment": "delay", "adjustment_type": "minimal" -> add +4 days to sowing date, for substantial add 1 week
                # cascades to harvesting, irrigation start, and fertilization dates
                elif action_type == "sowing" and adjustment == "delay":
                    days = 4 if adj_type == "minimal" else 7
                    plan["sowing"]                = _shift_date(plan["sowing"], days)
                    plan["harvesting"]            = _shift_date(plan["harvesting"], days)
                    plan["irrigation_start_date"] = _shift_date(plan["irrigation_start_date"], days)
                    plan["fertilization_date"]    = _shift_date(plan["fertilization_date"], days)
                    adjustments.append(f"{crop} sowing delayed by {days} days due to {context_name} {context_label} — harvesting, irrigation and fertilization dates shifted accordingly")

                elif action_type == "fertilization":
                    if adjustment == "increase quantity":
                        adjustments.append(f"{crop} requires increased fertilization on {context_name} {context_label}")
                    elif adjustment == "decrease quantity":
                        adjustments.append(f"{crop} requires reduced fertilization on {context_name} {context_label}")

                # if "action_type": "harvesting", "adjustment": "delay", "adjustment_type": "minimal" same as above add to harvesting date
                elif action_type == "harvesting" and adjustment == "delay":
                    days = 4 if adj_type == "minimal" else 7
                    plan["harvesting"] = _shift_date(plan["harvesting"], days)
                    adjustments.append(f"{crop} harvesting delayed by {days} days due to {context_name} {context_label}")

                # if "action_type": "avoid": nullify all dates
                # add "adjustments_to_make" "The crop and soil_type is extremely incompatible: Please consider a different field or a different crop"
                elif action_type == "avoid":
                    plan["sowing"]                = None
                    plan["harvesting"]            = None
                    plan["irrigation_start_date"] = None
                    plan["fertilization_date"]    = None
                    adjustments.append(f"{crop} is extremely incompatible with {context_name} {context_label} — please consider a different field or a different crop")
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

