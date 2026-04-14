import requests
import os

"""

API_KEY = os.getenv("WEATHER_API_KEY")


# SWAP WITH REAL API LATER

def get_weather(location):
    url = f"http://api.weatherapi.com/v1/current.json?key={API_KEY}&q={location}"
    res = requests.get(url)
    return res.json()
"""
def get_weather(location: str) -> dict:
    return {
        "location": location,
        "current": {
            "temperature_c": 37,
            "condition": "Hot and sunny",
            "humidity": 42,
            "wind_kph": 14,
        },
        "forecast": [
            {"day": "Today", "max_temp_c": 37, "min_temp_c": 26, "rain_chance": 10},
            {"day": "Tomorrow", "max_temp_c": 39, "min_temp_c": 27, "rain_chance": 5},
            {"day": "Day After", "max_temp_c": 35, "min_temp_c": 25, "rain_chance": 60},
        ],
        "rain_expected": False,
        "heatwave_risk": True,
    }