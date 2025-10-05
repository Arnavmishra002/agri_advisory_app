import requests
from django.conf import settings
from django.core.cache import caches
# Government APIs are now integrated directly in the service classes

weather_cache = caches['weather_cache']

class ExternalWeatherAPI:
    def __init__(self):
        self.api_key = settings.WEATHER_API_KEY
        self.base_url = settings.WEATHER_API_BASE_URL

    def get_current_weather(self, location):
        cache_key = f"current_weather_{location.replace(' ', '_').lower()}"
        cached_data = weather_cache.get(cache_key)
        if cached_data:
            return cached_data

        endpoint = f"{self.base_url}/current.json"
        params = {
            "key": self.api_key,
            "q": location
        }
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status() # Raise an exception for HTTP errors
            data = response.json()
            weather_cache.set(cache_key, data)
            return data
        except requests.exceptions.RequestException as e:
            print(f"Error fetching weather data: {e}")
            return None

    def get_forecast_weather(self, location, days=3):
        cache_key = f"forecast_weather_{location.replace(' ', '_').lower()}_{days}_days"
        cached_data = weather_cache.get(cache_key)
        if cached_data:
            return cached_data

        endpoint = f"{self.base_url}/forecast.json"
        params = {
            "key": self.api_key,
            "q": location,
            "days": days
        }
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            weather_cache.set(cache_key, data)
            return data
        except requests.exceptions.RequestException as e:
            print(f"Error fetching weather data: {e}")
            return None

class MockWeatherAPI:
    def __init__(self):
        self.imd_api = IMDWeatherAPI()  # Government API integration
    
    def get_current_weather(self, latitude, longitude, language):
        # Try to get data from IMD API first
        try:
            imd_data = self.imd_api.get_current_weather(latitude, longitude, language)
            if "error" not in imd_data:
                return imd_data
        except Exception as e:
            print(f"IMD API unavailable, using mock data: {e}")
        
        # Fallback to mock data
        return self._get_mock_weather_data(latitude, longitude, language)
    
    def _get_mock_weather_data(self, latitude, longitude, language):
        # Dummy weather data based on general location for demo
        if language == 'hi':
            city_name = "दिल्ली"
            condition_text = "साफ़ धुप"
            temp_c = 28
            humidity = 60
            wind_kph = 15
            wind_dir = "उत्तर"
        else:
            city_name = "Delhi"
            condition_text = "Clear Sky"
            temp_c = 28
            humidity = 60
            wind_kph = 15
            wind_dir = "North"

        return {
            "location": {
                "name": city_name,
                "region": "Delhi",
                "country": "India",
                "lat": latitude,
                "lon": longitude,
                "tz_id": "Asia/Kolkata",
                "localtime_epoch": 1678886400,
                "localtime": "2023-03-15 10:00"
            },
            "current": {
                "last_updated_epoch": 1678886400,
                "last_updated": "2023-03-15 10:00",
                "temp_c": temp_c,
                "temp_f": round(temp_c * 9/5 + 32, 2),
                "is_day": 1,
                "condition": {
                    "text": condition_text,
                    "icon": "//cdn.weatherapi.com/weather/64x64/day/113.png",
                    "code": 1000
                },
                "wind_mph": round(wind_kph / 1.609, 2),
                "wind_kph": wind_kph,
                "wind_degree": 360,
                "wind_dir": wind_dir,
                "pressure_mb": 1012.0,
                "pressure_in": 29.88,
                "precip_mm": 0.0,
                "precip_in": 0.0,
                "humidity": humidity,
                "cloud": 0,
                "feelslike_c": temp_c,
                "feelslike_f": round(temp_c * 9/5 + 32, 2),
                "vis_km": 10.0,
                "vis_miles": 6.0,
                "uv": 6.0,
                "gust_mph": 10.5,
                "gust_kph": 16.9
            }
        }

    def get_forecast_weather(self, latitude, longitude, language, days=3):
        # Mock forecast data
        if language == 'hi':
            city_name = "दिल्ली"
            condition_text = "आंशिक रूप से बादल छाए रहेंगे"
        else:
            city_name = "Delhi"
            condition_text = "Partly cloudy"

        return {
            "location": {
                "name": city_name,
                "region": "Delhi",
                "country": "India",
                "lat": latitude,
                "lon": longitude,
                "tz_id": "Asia/Kolkata",
                "localtime_epoch": 1678886400,
                "localtime": "2023-03-15 10:00"
            },
            "current": {
                "last_updated_epoch": 1678886400,
                "last_updated": "2023-03-15 10:00",
                "temp_c": 25,
                "temp_f": 77,
                "is_day": 1,
                "condition": {
                    "text": condition_text,
                    "icon": "//cdn.weatherapi.com/weather/64x64/day/116.png",
                    "code": 1003
                },
                "wind_mph": 8.1,
                "wind_kph": 13.0,
                "wind_degree": 270,
                "wind_dir": "W",
                "pressure_mb": 1010.0,
                "pressure_in": 29.83,
                "precip_mm": 0.0,
                "precip_in": 0.0,
                "humidity": 50,
                "cloud": 25,
                "feelslike_c": 26.5,
                "feelslike_f": 79.7,
                "vis_km": 10.0,
                "vis_miles": 6.0,
                "uv": 5.0,
                "gust_mph": 12.0,
                "gust_kph": 19.3
            },
            "forecast": {
                "forecastday": [
                    {
                        "date": "2023-03-15",
                        "day": {
                            "maxtemp_c": 28,
                            "mintemp_c": 18,
                            "condition": {"text": condition_text, "icon": "//cdn.weatherapi.com/weather/64x64/day/116.png"}
                        }
                    },
                    {
                        "date": "2023-03-16",
                        "day": {
                            "maxtemp_c": 29,
                            "mintemp_c": 19,
                            "condition": {"text": condition_text, "icon": "//cdn.weatherapi.com/weather/64x64/day/116.png"}
                        }
                    }
                ]
            }
        }
