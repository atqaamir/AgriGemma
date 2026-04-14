import requests
import os

API_KEY = os.getenv("WEATHER_API_KEY")

def get_weather(location):
    url = f"http://api.weatherapi.com/v1/current.json?key={API_KEY}&q={location}"
    res = requests.get(url)
    return res.json()