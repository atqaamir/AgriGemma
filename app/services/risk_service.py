import json
from datetime import date, timedelta

from app.utils.enums_ import Status, ChangeStatus
from app.repositories.weather_repository import WeatherRepository
from app.repositories.forecast_repository import ForecastRepository
from app.services.domain_service.user_service import UserService
from app.rules.rule_engine.rule_engine import RuleEngine


# Sweet-spot thresholds for NO_CHANGE.
# Within the same band AND diff ≤ threshold → negligible (NO_CHANGE).
# Within the same band AND diff >  threshold → notable but no band shift (NO_IMPACT).
# Band changes are always significant regardless of diff size.
#
# Values chosen to reflect real daily forecast-vs-observation noise in Pakistan:
#   temperature : ±1.5 °C  — typical 1-day NWP correction
#   humidity    : ±4 %     — natural diurnal swing
#   rainfall    : ±3 mm    — drizzle-vs-trace ambiguity
#   sunlight    : ±0.5 h   — half-hour cloud-cover variation
NEGLIGIBLE = {
    "temperature": 1.5,
    "humidity":    4.0,
    "rainfall":    3.0,
    "sunlight":    0.5,
}

WEATHER_FACTORS = [
    ("temperature", "avg_temperature_c"),
    ("humidity",    "humidity"),
    ("rainfall",    "rainfall_mm"),
    ("sunlight",    "sunlight_hours"),
]

_SEVERITY = [
    ChangeStatus.NO_CHANGE,
    ChangeStatus.NO_IMPACT,
    ChangeStatus.IMPACT_PLAN,
    ChangeStatus.IMPACT_TASKS,
]


def _escalate(current: ChangeStatus, new: ChangeStatus) -> ChangeStatus:
    return new if _SEVERITY.index(new) > _SEVERITY.index(current) else current


class RiskService:

    def assess_risk(
        self,
        user_id: int,
        tag: str = "risk_assessment",
        as_of_date: date = None,
    ) -> tuple:
        """Returns (Status, ChangeStatus, detail_dict)."""
        if as_of_date is None:
            as_of_date = date.today()
        detail = self.assess_weather_change(user_id, as_of_date)
        return Status.SUCCESS, detail["overall_change_status"], detail

    def assess_weather_change(self, user_id: int, as_of_date: date) -> dict:
        """
        Compare weather (baseline) vs weather_forecast for the user's region
        from as_of_date to as_of_date + 6.  Dates before as_of_date are skipped.

        Impact levels
        -------------
        NO_CHANGE     — same band AND diff ≤ NEGLIGIBLE threshold
        NO_IMPACT     — same band AND diff >  NEGLIGIBLE threshold
        IMPACT_PLAN   — band changed on a future date (after as_of_date)
        IMPACT_TASKS  — band changed on as_of_date itself
                        (IMPACT_TASKS implies the weekly plan is also affected)

        Output: one finding per date (not per factor).
        Each finding carries the worst status for that date plus a factor breakdown.
        """
        end_date = as_of_date + timedelta(days=6)

        user_location = UserService.get_user_location(user_id)
        if not user_location:
            return {
                "overall_change_status": ChangeStatus.NO_CHANGE,
                "as_of_date":      as_of_date.isoformat(),
                "end_date":        end_date.isoformat(),
                "regions_checked": [],
                "findings":        [],
            }

        region = user_location
        findings     = []
        worst_status = ChangeStatus.NO_CHANGE

        baseline_by_date = {
            r.date: r
            for r in WeatherRepository.get_by_region_and_date_range(
                region, as_of_date, end_date
            )
        }
        forecast_by_date = {
            r.date: r
            for r in ForecastRepository.get_by_region_and_date_range(
                region, as_of_date, end_date
            )
        }

        for check_date in sorted(set(baseline_by_date) & set(forecast_by_date)):
            baseline = baseline_by_date[check_date]
            forecast = forecast_by_date[check_date]
            is_today = check_date == as_of_date

            date_status      = ChangeStatus.NO_CHANGE
            affected_factors = []

            for factor, attr in WEATHER_FACTORS:
                b_val = getattr(baseline, attr, None)
                f_val = getattr(forecast, attr, None)
                if b_val is None or f_val is None:
                    continue

                diff         = abs(f_val - b_val)
                b_band       = RuleEngine.classify_value_bands(factor, b_val)
                f_band       = RuleEngine.classify_value_bands(factor, f_val)
                band_changed = b_band != f_band

                if not band_changed and diff <= NEGLIGIBLE[factor]:
                    factor_status = ChangeStatus.NO_CHANGE
                elif not band_changed:
                    factor_status = ChangeStatus.NO_IMPACT
                elif is_today:
                    factor_status = ChangeStatus.IMPACT_TASKS
                else:
                    factor_status = ChangeStatus.IMPACT_PLAN

                if factor_status == ChangeStatus.NO_CHANGE:
                    continue

                affected_factors.append({
                    "factor":         factor,
                    "baseline_value": round(b_val, 2),
                    "forecast_value": round(f_val, 2),
                    "difference":     round(diff, 2),
                    "baseline_band":  b_band,
                    "forecast_band":  f_band,
                    "band_changed":   band_changed,
                    "factor_status":  factor_status.value,
                })
                date_status = _escalate(date_status, factor_status)

            if date_status == ChangeStatus.NO_CHANGE:
                continue  # all factors negligible — skip this date

            # Persist change metadata to the baseline weather row
            baseline_row = baseline_by_date[check_date]
            change_level = (
                "high" if date_status in (ChangeStatus.IMPACT_PLAN, ChangeStatus.IMPACT_TASKS)
                else "low"
            )
            changes_payload = [
                {"change_type": f["factor"], "new_value": f["forecast_value"]}
                for f in affected_factors
                if f["band_changed"]
            ]
            WeatherRepository.update(baseline_row, {
                "change_level": change_level,
                "changes":      json.dumps(changes_payload) if changes_payload else None,
            })

            findings.append({
                "region":   region,
                "date":     check_date.isoformat(),
                "is_today": is_today,
                "status":   date_status.value,
                "factors":  affected_factors,
            })
            worst_status = _escalate(worst_status, date_status)

        return {
            "overall_change_status": worst_status,
            "as_of_date":      as_of_date.isoformat(),
            "end_date":        end_date.isoformat(),
            "regions_checked": [region],
            "findings":        findings,
        }
