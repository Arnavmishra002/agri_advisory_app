
import os
import django
import sys
import logging

# Setup Django environment
sys.path.append('c:\\AI\\agri_advisory_app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from advisory.services.accurate_location_api import AccurateLocationAPI

# Configure logging to print to console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_reverse_geocode():
    api = AccurateLocationAPI()
    
    # Test coordinates (Delhi)
    lat = 28.6139
    lon = 77.2090
    
    print(f"Testing reverse geocode for {lat}, {lon}...")
    try:
        result = api.reverse_geocode(lat, lon)
        print("\nAPI Result:")
        print(result)
        
        if result.get('status') == 'success':
            print("\n✅ API Call Successful")
            location = result.get('location', {})
            print(f"Location Name: {location.get('name')}")
            print(f"City: {location.get('city')}")
            print(f"State: {location.get('state')}")
        else:
            print("\n❌ API Call Failed")
            print(f"Error: {result.get('message')}")
            
    except Exception as e:
        print(f"\n❌ Exception occurred: {e}")

    print("\n" + "="*50 + "\n")
    
    # Test Village (Punsari, Gujarat)
    # Lat/Lon approx: 23.473324, 73.047905
    print("Testing Village Detection (Punsari, Gujarat)...")
    try:
        result = api.reverse_geocode(23.473324, 73.047905)
        print("\nAPI Result:")
        print(result)
        
        if result.get('status') == 'success':
            print("\n✅ Village Detection Successful")
            location = result.get('location', {})
            print(f"Location Name: {location.get('name')}")
            print(f"City/Village: {location.get('city')}")
            print(f"State: {location.get('state')}")
            print(f"District: {location.get('district')}")
        else:
            print("\n❌ Village Detection Failed")
    except Exception as e:
        print(f"\n❌ Exception: {e}")

if __name__ == "__main__":
    test_reverse_geocode()
