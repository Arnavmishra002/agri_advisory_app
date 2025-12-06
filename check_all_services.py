import os
import sys
import django
import json
import time

# Redirect output to file
log_file = open('verification_report.txt', 'w', encoding='utf-8')
sys.stdout = log_file

# Setup Django environment
sys.path.append('c:\\AI\\agri_advisory_app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

import logging
logging.disable(logging.CRITICAL)
from advisory.services.ultra_dynamic_government_api import UltraDynamicGovernmentAPI

def verify_services():
    print("\n" + "="*50)
    print("VERIFYING REAL-TIME GOVERNMENT SERVICES")
    print("="*50)
    
    api = UltraDynamicGovernmentAPI()
    location = "Delhi"
    lat, lon = 28.6139, 77.2090
    
    # 1. Comprehensive Data Fetch (Simulating Dashboard Load)
    print(f"\n[TEST 1] Testing Comprehensive Real-Time Data for {location}...")
    start_time = time.time()
    try:
        data = api.get_comprehensive_government_data(location=location, lat=lat, lon=lon)
        duration = time.time() - start_time
        
        if data and data.get('status') == 'success':
            print(f"✅ [SUCCESS] Data received in {duration:.2f}s")
            gov_data = data.get('government_data', {})
            
            # Verify Weather
            weather = gov_data.get('weather', {})
            if weather:
                print(f"   - Weather Keys: {list(weather.keys())}")
                print(f"   - Weather: Current Temp: {weather.get('temperature')}")
                print(f"   - Source: {weather.get('data_source')}")
            else:
                print(f"   ❌ Weather data missing (gov_data keys: {list(gov_data.keys())})")

            # Verify Market Prices (from comprehensive)
            market = gov_data.get('market_prices', {})
            if market:
                # In comprehensive, it returns market_data dict which has keys like "Wheat": {...}
                # It does NOT use the V2 list structure.
                print(f"   - Market Data Keys: {list(market.keys())[:5]}") 
                if market:
                    first_crop = list(market.keys())[0]
                    # Check if it's a list or dict
                    if isinstance(market, dict) and isinstance(market.get(first_crop), dict):
                         print(f"     Sample: {first_crop} - ₹{market[first_crop].get('current_price')}")
                    elif isinstance(market, list):
                         print(f"     Market data is list: {market[0]}")
            else:
                print("   ❌ Market data missing in comprehensive response")

            # Verify Schemes
            schemes = gov_data.get('government_schemes', {})
            if schemes:
                central = schemes.get('central_schemes', [])
                print(f"   - Govt Schemes: Found {len(central)} central schemes")
                if central:
                    print(f"     Sample: {central[0].get('name')}")
            else:
                print("   ❌ Scheme data missing")
                
        else:
            print(f"❌ [FAIL] Status: {data.get('status') if data else 'None'}")
            
    except Exception as e:
        print(f"❌ [ERROR] Checks failed: {e}")

    # 2. Market Prices V2 (Specific API with Enhanced Logic)
    print(f"\n[TEST 2] Testing Enhanced Market Prices V2...")
    try:
        data = api.get_market_prices_v2(location=location, latitude=lat, longitude=lon)
        if data and data.get('status') == 'success':
            prices = data.get('market_prices', {})
            crops = prices.get('crops', [])
            mandis = prices.get('nearby_mandis', [])
            
            print(f"✅ [SUCCESS] Retrieved Market V2 Data")
            print(f"   - Source: {data.get('data_source')}")
            print(f"   - Crops Listed: {len(crops)}")
            print(f"   - Mandis Found: {len(mandis)}")
            
            if crops:
                print("   - Sample Crop Data:")
                for crop in crops[:3]:
                    print(f"     • {crop.get('crop_name')} ({crop.get('crop_name_hindi')}): ₹{crop.get('current_price')} | Trend: {crop.get('trend')}")
            
            if mandis:
                print("   - Nearby Mandis:")
                for mandi in mandis[:2]:
                    print(f"     • {mandi.get('name')} ({mandi.get('distance')}) - {mandi.get('status')}")
        else:
             print(f"❌ [FAIL] Status: {data.get('status') if data else 'None'}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ [ERROR] Market V2 failed: {e}")

    # 3. Crop Recommendations (Direct ICAR Check)
    print(f"\n[TEST 3] Testing Crop Recommendations Integration...")
    try:
        data = api._fetch_crop_recommendations(location)
        if data and data.get('status') == 'success':
             recs = data.get('data', {}).get('recommendations', [])
             print(f"✅ [SUCCESS] ICAR Recommendations: {len(recs)} crops found")
             if recs:
                 print(f"   - Top Rec: {recs[0].get('crop_name')} (Score: {recs[0].get('suitability_score')})")
        else:
             print("❌ [FAIL] direct crop fetch failed")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ [ERROR] Crop Recs failed: {e}")

    print("\n" + "="*50)
    print("VERIFICATION COMPLETE")
    print("="*50)

if __name__ == "__main__":
    verify_services()
