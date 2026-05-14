import requests
import os
from datetime import date, timedelta

"""
API_KEY = os.getenv("WEATHER_API_KEY")

# SWAP WITH REAL API LATER

def get_weather(location):
    url = f"http://api.weatherapi.com/v1/current.json?key={API_KEY}&q={location}"
    res = requests.get(url)
    return res.json()
"""

# Realistic 7-day dummy data for Lahore (hot season, rain front mid-week).
# Covers the full range of adaptation signals: heatwave, rain, dry harvest window.
_DUMMY_FORECASTS = [
    # day,          max,  min,  rain%, condition,        humidity, wind
    ("Today",        38,   26,    5,  "Hot and Sunny",       38,   12),
    ("Tomorrow",     39,   27,    8,  "Hot and Sunny",       35,   10),
    ("Day 3",        37,   26,   20,  "Partly Cloudy",       45,   14),
    ("Day 4",        33,   24,   65,  "Thunderstorms",       72,   22),
    ("Day 5",        31,   23,   70,  "Rainy",               78,   18),
    ("Day 6",        34,   24,   25,  "Cloudy",              60,   16),
    ("Day 7",        36,   25,   10,  "Mostly Sunny",        48,   13),
]


def get_weather(location: str, n: int = 7) -> dict:
    today = date.today()
    forecast = []
    for i, (label, max_t, min_t, rain_chance, condition, humidity, wind) in enumerate(_DUMMY_FORECASTS[:n]):
        forecast.append({
            "day": label,
            "date": str(today + timedelta(days=i)),
            "max_temp_c": max_t,
            "min_temp_c": min_t,
            "rain_chance": rain_chance,
            "condition": condition,
            "humidity": humidity,
            "wind_kph": wind,
        })

    # Derive top-level flags from the first 3 days
    near_forecast = forecast[:3]
    rain_expected = any(f["rain_chance"] >= 60 for f in near_forecast)
    heatwave_risk = any(f["max_temp_c"] >= 38 for f in near_forecast)

    return {
        "location": location,
        "current": {
            "temperature_c": forecast[0]["max_temp_c"] - 1,
            "condition": forecast[0]["condition"],
            "humidity": forecast[0]["humidity"],
            "wind_kph": forecast[0]["wind_kph"],
            "rainfall_mm": 0 if forecast[0]["rain_chance"] < 40 else 4,
        },
        "forecast": forecast,
        "rain_expected": rain_expected,
        "heatwave_risk": heatwave_risk,
    }


# ── Climate profiles (monthly averages) ───────────────────────────────────────
# Each entry: (month_num, name, avg_max_c, avg_min_c, avg_rainfall_mm,
#              avg_rain_days, condition, farming_notes)

_CLIMATE_PROFILES = {
    "lahore": {
        "region": "Punjab, Pakistan",
        "climate_type": "Semi-arid continental",
        "monthly": [
            (1,  "January",   19,  6,  18,  3, "Cool and Dry",    "Wheat growing; light frost risk; minimal irrigation needed"),
            (2,  "February",  22,  9,  22,  4, "Mild",            "Wheat tillering; mustard flowering; prepare for spring planting"),
            (3,  "March",     28, 14,  28,  5, "Warm and Windy",  "Wheat heading; sow summer vegetables; increase irrigation"),
            (4,  "April",     35, 20,  16,  3, "Hot and Dry",     "Wheat harvest window; sow cotton and maize; watch for aphids"),
            (5,  "May",       40, 26,   8,  2, "Very Hot",        "Complete wheat harvest; heavy irrigation critical; avoid new sowing"),
            (6,  "June",      42, 29,  18,  3, "Extreme Heat",    "Cotton growing; pre-monsoon dust storms; irrigate every 5–7 days"),
            (7,  "July",      37, 28, 120, 12, "Monsoon",         "Rice planting; reduce irrigation; high fungal disease and pest risk"),
            (8,  "August",    36, 27, 110, 11, "Peak Monsoon",    "Monitor drainage; peak fungal risk; avoid field work after rain"),
            (9,  "September", 35, 25,  55,  6, "Late Monsoon",    "Monsoon tapering; maize and kharif harvest; prepare rabi beds"),
            (10, "October",   33, 19,  12,  2, "Post-Monsoon",    "Best wheat sowing window; rabi season; ideal field conditions"),
            (11, "November",  27, 12,   5,  1, "Cool and Dry",    "Peak wheat sowing; excellent harvest conditions; low disease risk"),
            (12, "December",  21,  7,  14,  3, "Cold",            "Wheat germination; protect from frost; very low irrigation needed"),
        ],
        "best_sowing_months": [10, 11],
        "best_harvest_months": [4, 5],
        "monsoon_months": [7, 8, 9],
        "heat_peak_months": [5, 6],
    },
    "karachi": {
        "region": "Sindh, Pakistan",
        "climate_type": "Hot arid coastal",
        "monthly": [
            (1,  "January",   26, 13,   3,  1, "Mild and Sunny",  "Good growing season; sow vegetables; minimal irrigation"),
            (2,  "February",  28, 15,   8,  1, "Warm and Sunny",  "Ideal conditions; diverse crop planting; low pest pressure"),
            (3,  "March",     31, 20,   8,  1, "Warm",            "Plant heat-tolerant crops; increase irrigation as heat rises"),
            (4,  "April",     34, 24,   3,  0, "Hot and Dry",     "High irrigation demand; harvest winter crops"),
            (5,  "May",       36, 27,   2,  0, "Very Hot",        "Extreme irrigation; limit to heat-hardy crops only"),
            (6,  "June",      36, 29,  18,  2, "Hot and Humid",   "Pre-monsoon humidity; watch for fungal issues; limit sowing"),
            (7,  "July",      33, 27,  80,  8, "Monsoon",         "Reduce irrigation; high disease risk; drainage essential"),
            (8,  "August",    32, 27,  68,  7, "Monsoon",         "Peak humidity; fungal diseases; avoid soil disturbance"),
            (9,  "September", 33, 26,  22,  3, "Post-Monsoon",    "Monsoon tapering; good for kharif harvest; prepare rabi beds"),
            (10, "October",   34, 23,   2,  0, "Warm and Dry",    "Excellent planting window; sow winter vegetables and wheat"),
            (11, "November",  31, 18,   2,  0, "Mild",            "Best growing conditions; high yield potential; low irrigation"),
            (12, "December",  28, 14,   4,  1, "Cool and Sunny",  "Peak vegetable season; sow cool-season crops"),
        ],
        "best_sowing_months": [10, 11, 12],
        "best_harvest_months": [3, 4],
        "monsoon_months": [7, 8],
        "heat_peak_months": [5, 6],
    },
    "islamabad": {
        "region": "Punjab/KPK, Pakistan",
        "climate_type": "Humid subtropical",
        "monthly": [
            (1,  "January",   13,  3,  58,  6, "Cold and Rainy",  "Wheat growing; frost risk; minimal field work"),
            (2,  "February",  15,  5,  68,  7, "Cool and Rainy",  "Wheat growing; soil moisture adequate; prepare for spring"),
            (3,  "March",     21, 10,  73,  8, "Mild with Rain",  "Wheat heading; spring sowing begins; good soil moisture"),
            (4,  "April",     27, 14,  58,  7, "Warm with Rain",  "Wheat heading; plant vegetables and maize; monitor pests"),
            (5,  "May",       33, 19,  38,  6, "Hot and Humid",   "Wheat harvest; pre-monsoon showers; sow kharif crops"),
            (6,  "June",      37, 23,  68,  7, "Hot and Stormy",  "Kharif planting; pre-monsoon storms; irrigate between rains"),
            (7,  "July",      34, 24, 280, 18, "Heavy Monsoon",   "Rice growing; very high rain; reduce all irrigation; drainage critical"),
            (8,  "August",    33, 24, 308, 19, "Peak Monsoon",    "Peak rainfall; flood risk; fungal disease maximum; avoid field work"),
            (9,  "September", 30, 20, 108, 10, "Monsoon",         "Rain tapering; maize harvest; prepare rabi fields after drainage"),
            (10, "October",   26, 13,  28,  3, "Mild and Dry",    "Wheat sowing; ideal conditions; soil workable"),
            (11, "November",  20,  7,  18,  2, "Cool and Dry",    "Wheat germination; low irrigation; plant winter vegetables"),
            (12, "December",  15,  3,  35,  4, "Cold",            "Wheat growing; frost possible; protect sensitive crops"),
        ],
        "best_sowing_months": [10, 11],
        "best_harvest_months": [5, 9],
        "monsoon_months": [7, 8, 9],
        "heat_peak_months": [6, 7],
    },
}

_MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _match_location(location: str) -> str:
    """Return the best-matching climate profile key, defaulting to 'lahore'."""
    key = location.lower().strip()
    for profile_key in _CLIMATE_PROFILES:
        if profile_key in key or key in profile_key:
            return profile_key
    return "lahore"


def get_yearly_climate(location: str) -> dict:
    """Return full 12-month climate profile for the given location."""
    profile_key = _match_location(location)
    profile = _CLIMATE_PROFILES[profile_key]
    months = [
        {
            "month": m[0],
            "name": m[1],
            "avg_max_temp_c": m[2],
            "avg_min_temp_c": m[3],
            "avg_rainfall_mm": m[4],
            "avg_rain_days": m[5],
            "condition": m[6],
            "farming_notes": m[7],
        }
        for m in profile["monthly"]
    ]
    return {
        "location": location,
        "region": profile["region"],
        "climate_type": profile["climate_type"],
        "months": months,
        "best_sowing_months": [_MONTH_NAMES[m] for m in profile["best_sowing_months"]],
        "best_harvest_months": [_MONTH_NAMES[m] for m in profile["best_harvest_months"]],
        "monsoon_months": [_MONTH_NAMES[m] for m in profile["monsoon_months"]],
        "heat_peak_months": [_MONTH_NAMES[m] for m in profile["heat_peak_months"]],
    }


def get_monthly_climate(location: str, month: int) -> dict:
    """Return climate data for a specific month (1–12)."""
    profile_key = _match_location(location)
    profile = _CLIMATE_PROFILES[profile_key]
    row = next((m for m in profile["monthly"] if m[0] == month), profile["monthly"][0])
    return {
        "location": location,
        "region": profile["region"],
        "month": row[0],
        "name": row[1],
        "avg_max_temp_c": row[2],
        "avg_min_temp_c": row[3],
        "avg_rainfall_mm": row[4],
        "avg_rain_days": row[5],
        "condition": row[6],
        "farming_notes": row[7],
    }