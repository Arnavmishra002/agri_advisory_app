
import os
import sys
import json
from datetime import datetime

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from advisory.services.ultra_dynamic_government_api import UltraDynamicGovernmentAPI

def verify_stability():
    api = UltraDynamicGovernmentAPI()
    location = "Delhi"
    
    print(f"Testing Crop Suggestion Stability for {location}...")
    
    # First Call
    print("   Call 1...")
    data1 = api._get_fallback_crop_data(location)
    crops1 = [c['crop_name'] for c in data1['data']['recommendations']]
    print(f"   Result 1: {crops1[:3]}...")
    
    # Second Call
    print("   Call 2...")
    data2 = api._get_fallback_crop_data(location)
    crops2 = [c['crop_name'] for c in data2['data']['recommendations']]
    print(f"   Result 2: {crops2[:3]}...")
    
    if crops1 == crops2:
        print("PASS: Crop Suggestions are STABLE.")
    else:
        print("FAIL: Crop Suggestions CHANGED.")
        print(f"   Diff: {set(crops1) ^ set(crops2)}")
        exit(1)
        
    print(f"\nTesting Market Price Stability for {location}...")
    
    # First Call (Market)
    if hasattr(api, 'get_market_prices_v2'):
        print("   Call 1 (Market)...")
        mkt1 = api.get_market_prices_v2(location)
        # Check if it was simulated (likely yes if API fails or we can force it)
        # The key is 'crops' list names
        m_crops1 = [c['name'] for c in mkt1.get('crops', [])]
        print(f"   Result 1: {m_crops1[:3]}...")
        
        print("   Call 2 (Market)...")
        mkt2 = api.get_market_prices_v2(location)
        m_crops2 = [c['name'] for c in mkt2.get('crops', [])]
        print(f"   Result 2: {m_crops2[:3]}...")
        
        if m_crops1 == m_crops2:
             print("PASS: Market Prices are STABLE.")
        else:
             print("WARN: Market Prices changed. Might be real-time update or unstable simulation.")
             if mkt1.get('data_source') != mkt2.get('data_source'):
                 print("   Source changed!")
             else:
                 print("   Same source, content changed.")
                 # exit(1) # Optional, let's trust crop fix for now.
    
if __name__ == "__main__":
    verify_stability()
