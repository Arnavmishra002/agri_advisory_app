
import time
import sys
import os

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from advisory.services.accurate_location_api import accurate_location_api
from advisory.rate_limiters import nominatim_limiter

def test_rate_limiting():
    print("Testing Rate Limiting (Nominatim: 1 req/sec)...")
    
    start_time = time.time()
    
    # Make 3 fast calls. 
    # Call 1: Instant
    # Call 2: Wait 1s
    # Call 3: Wait 1s
    # Total time should be at least 2.0 seconds.
    
    print("   Call 1...")
    accurate_location_api._detect_via_geocoding("Delhi")
    
    print("   Call 2 (Should wait)...")
    accurate_location_api._detect_via_geocoding("Mumbai")
    
    print("   Call 3 (Should wait)...")
    accurate_location_api._detect_via_geocoding("Pune")
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"Total Duration: {duration:.2f} seconds")
    
    if duration >= 2.0:
        print("PASS: Rate Limiting WORKING. Delays were applied.")
    else:
        print("FAIL: Rate Limiting FAILED. Too fast!")
        exit(1)

if __name__ == "__main__":
    test_rate_limiting()
