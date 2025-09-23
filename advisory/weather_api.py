import requests
from django.conf import settings

class WeatherAPI:
    def __init__(self):
        self.api_key = settings.WEATHER_API_KEY
        self.base_url = settings.WEATHER_API_BASE_URL

    def get_current_weather(self, location):
        endpoint = f"{self.base_url}/current.json"
        params = {
            "key": self.api_key,
            "q": location
        }
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status() # Raise an exception for HTTP errors
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching weather data: {e}")
            return None

    def get_forecast_weather(self, location, days=3):
        endpoint = f"{self.base_url}/forecast.json"
        params = {
            "key": self.api_key,
            "q": location,
            "days": days
        }
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching weather data: {e}")
            return None
