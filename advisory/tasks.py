from celery import shared_task
import logging

from .services.weather_api import ExternalWeatherAPI, MockWeatherAPI
from .services.market_api import get_market_prices, get_trending_crops
from .models import Crop, User
from .services.notifications import send_push_notification

logger = logging.getLogger(__name__)

@shared_task
def update_weather_data():
    logger.info("Starting scheduled weather data update...")
    # In a real scenario, you'd iterate through known farmer locations or popular regions
    # For now, let's use a dummy location
    location = "Delhi, India"
    latitude = 28.7041
    longitude = 77.1025

    weather_api = MockWeatherAPI() # Use the actual ExternalWeatherAPI in production
    
    try:
        current_weather = weather_api.get_current_weather(location)
        if current_weather:
            temp_c = current_weather['current']['temp_c']
            condition = current_weather['current']['condition']['text']
            weather_alert_message = f"Weather Alert for {location}: Current temperature is {temp_c}°C with {condition}."
            logger.info(weather_alert_message)

            # Send push notification for weather update (to all active users for simplicity)
            # In a real app, you'd filter users by location preference
            # user_ids = [str(user.id) for user in User.objects.filter(is_active=True)]
            # For now, a placeholder user ID
            dummy_user_id = "farmer123"
            send_push_notification([dummy_user_id], "Weather Update", weather_alert_message, {"type": "weather_alert", "location": location})
        else:
            logger.warning(f"Failed to get current weather for {location}.")

        forecast_weather = weather_api.get_forecast_weather(location, days=7)
        if forecast_weather:
            logger.info(f"Successfully updated 7-day forecast for {location}.")
        else:
            logger.warning(f"Failed to get forecast weather for {location}.")

    except Exception as e:
        logger.error(f"Error during weather data update: {e}")
    logger.info("Finished scheduled weather data update.")

@shared_task
def update_market_data():
    logger.info("Starting scheduled market data update...")
    # In a real scenario, iterate through relevant market locations and product types
    # For now, let's use dummy parameters
    latitude = 28.7041
    longitude = 77.1025
    language = 'en'
    product_type = 'Wheat' # Example product

    try:
        market_prices = get_market_prices(latitude, longitude, language, product_type)
        if market_prices:
            price_info = market_prices.get('price_info', 'N/A')
            market_alert_message = f"Market Update for {product_type} in Delhi: {price_info}"
            logger.info(market_alert_message)

            # Send push notification for market update
            dummy_user_id = "farmer123"
            send_push_notification([dummy_user_id], "Market Price Update", market_alert_message, {"type": "market_update", "product": product_type})
        else:
            logger.warning(f"Failed to get market prices for {product_type} in Delhi.")

        trending_crops = get_trending_crops(latitude, longitude, language)
        if trending_crops:
            logger.info(f"Successfully updated trending crops data.")
            trending_crops_list = [crop.get('name', '') for crop in trending_crops.get('trending_crops', [])[:3]]
            if trending_crops_list:
                trending_message = f"Trending crops: {', '.join(trending_crops_list)}."
                dummy_user_id = "farmer123"
                send_push_notification([dummy_user_id], "Trending Crops", trending_message, {"type": "trending_crops"})

        else:
            logger.warning(f"Failed to get trending crops data.")

    except Exception as e:
        logger.error(f"Error during market data update: {e}")
    logger.info("Finished scheduled market data update.")
