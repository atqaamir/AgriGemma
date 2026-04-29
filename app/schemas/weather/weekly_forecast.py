# app/schemas/weather/current_weather_profile_schema.py

from marshmallow import Schema, fields


class CurrentWeatherProfileSchema(Schema):

    id = fields.Int(dump_only=True)

    region = fields.Str(required=True)

    season = fields.Str(required=False, allow_none=True)

    avg_temperature_c = fields.Float(required=False, allow_none=True)

    avg_rainfall_mm = fields.Float(required=False, allow_none=True)

    avg_humidity = fields.Float(required=False, allow_none=True)

    notes = fields.Str(required=False, allow_none=True)

    created_at = fields.DateTime(dump_only=True)

    _start_index = fields.Int(required=False)

    _with_increments = fields.Int(required=False)


# =========================================================
# RESPONSE SCHEMAS
# =========================================================

class DailyForecastSchema(Schema):

    date = fields.Date(required=True)

    temperature_c = fields.Float(required=True)

    precipitation_mm = fields.Float(required=True)

    wind_speed_kph = fields.Float(required=True)


class WeeklyForecastResponseSchema(Schema):

    region = fields.Str(required=True)

    total_days = fields.Int(required=True)

    forecasts = fields.List(
        fields.Nested(DailyForecastSchema),
        required=True
    )


# =========================================================
# REQUEST SCHEMAS
# =========================================================

class ForecastFetchRequestSchema(Schema):

    region = fields.Str(required=True)

    days = fields.Int(required=False, load_default=7)