
import os
import django
import sys

# Setup Django environment
sys.path.append('c:\\AI\\agri_advisory_app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from advisory.services.ultra_dynamic_government_api import UltraDynamicGovernmentAPI
import logging

# Configure logging to print to console
logging.basicConfig(level=logging.INFO)

def test_weather_api():
    print("Testing Weather API...")
    api = UltraDynamicGovernmentAPI()
    try:
        # Test with default location
        print("\nFetching weather for Delhi...")
        data = api.get_weather_data("Delhi")
        print("Result:", data)
        
        # Test with coordinates
        print("\nFetching weather for coordinates (28.6139, 77.2090)...")
        data = api.get_weather_data("Delhi", 28.6139, 77.2090)
        print("Result:", data)
        
    except Exception as e:
        print(f"\n❌ Error caught: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_weather_api()
