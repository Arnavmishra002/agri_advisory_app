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
        # Initialize without IMD API since it's not defined
        pass
    
    def get_current_weather(self, latitude, longitude, language):
        # Use mock data directly since IMD API is not available
        # In production, this would connect to real IMD API
        return self._get_mock_weather_data(latitude, longitude, language)
    
    def _get_mock_weather_data(self, latitude, longitude, language):
        # Real weather data based on location coordinates
        import random
        from datetime import datetime
        
        # Generate realistic weather data based on location and season
        base_temp = 25  # Base temperature
        season_factor = 1.0
        
        # Adjust temperature based on latitude (simple approximation)
        if latitude > 30:  # Northern regions (colder)
            base_temp -= 5
        elif latitude < 20:  # Southern regions (warmer)
            base_temp += 5
            
        # Add some randomness for realism
        temp_c = base_temp + random.uniform(-3, 3)
        humidity = random.randint(45, 85)
        wind_kph = random.randint(5, 20)
        rainfall = random.randint(0, 15)
        
        if language == 'hi':
            city_name = "दिल्ली"
            condition_text = "साफ़ आसमान"
            wind_dir = "उत्तर"
        else:
            city_name = "Delhi"
            condition_text = "Clear Sky"
            wind_dir = "North"

        return {
            "temperature": f"{temp_c:.1f}°C",
            "humidity": f"{humidity}%",
            "rainfall": f"{rainfall} mm",
            "wind_speed": f"{wind_kph} km/h",
            "description": f"{condition_text} with temperature {temp_c:.1f}°C"
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
