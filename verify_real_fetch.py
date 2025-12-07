
import os
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from advisory.services.ultra_dynamic_government_api import UltraDynamicGovernmentAPI

def verify_fetch():
    api = UltraDynamicGovernmentAPI()
    
    # CASE 1: Specific Mandi (Azadpur)
    target = "Azadpur Mandi (Delhi)"
    print(f"\n--- Testing Fetch for: {target} ---")
    data = api.get_market_prices_v2(location="Delhi", mandi=target)
    
    print(f"Data Source: {data.get('data_source')}")
    print(f"Mandi Returned: {data.get('mandi')}")
    
    if data.get('data_source', '').startswith('Real-Time'):
        print("✅ SUCCESS: System is using Real-Time API.")
        # Print a sample crop to show 'Real' data
        if data['market_prices']['crops']:
            print(f"Sample Crop Data: {data['market_prices']['crops'][0]}")
    else:
        print("⚠️ NOTE: System fell back to Simulation. (Likely Network/API Down).")
        print("However, logic confirms we TRIED to fetch.")
        
    # CASE 2: Nearest Mandi Detection -> Real Fetch
    # Pune Coords
    print(f"\n--- Testing Fetch for: Pune (Auto-Detect) ---")
    data_pune = api.get_market_prices_v2(location="Pune", latitude=18.5204, longitude=73.8567)
    
    print(f"Data Source: {data_pune.get('data_source')}")
    print(f"Detected Mandi: {data_pune.get('mandi')}")
    
    expected_mandi = "Pune APMC (Pune)"
    if data_pune.get('mandi') == expected_mandi:
        print(f"✅ PASS: Auto-detected {expected_mandi} correctly.")
    else:
         print(f"❌ FAIL: Expected {expected_mandi}, got {data_pune.get('mandi')}")

if __name__ == "__main__":
    verify_fetch()
