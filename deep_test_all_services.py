import os
import django
import sys
import json
import time

# Setup Django environment
sys.path.append('c:\\AI\\agri_advisory_app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from advisory.services.ultra_dynamic_government_api import UltraDynamicGovernmentAPI
from advisory.services.comprehensive_crop_recommendations import ComprehensiveCropRecommendations

def test_all_services():
    print("Starting Comprehensive Service Verification")
    print("=" * 60)
    
    api = UltraDynamicGovernmentAPI()
    current_location = "Delhi"
    
    # ---------------------------------------------------------
    # 1. Weather Service Verification
    # ---------------------------------------------------------
    print("\n1. Testing WEATHER Service...")
    try:
        weather_data = api.get_weather_data(location=current_location)
        if weather_data.get('status') == 'success':
            data = weather_data.get('data', {})
            temp = data.get('temperature', 'N/A')
            cond = data.get('condition', 'N/A')
            forecast = data.get('forecast', [])
            print(f"   Success! Temp: {temp}C, Condition: {ascii(cond)}")
            print(f"   Forecast Days: {len(forecast)}")
            if len(forecast) > 0:
                print(f"      - Tomorrow: {ascii(forecast[0].get('condition', 'Unknown'))}")
        else:
            print(f"   Failed: {weather_data}")
    except Exception as e:
        print(f"   Exception: {e}")

    # ---------------------------------------------------------
    # 2. Market Prices Verification
    # ---------------------------------------------------------
    print("\n2. Testing MARKET PRICES Service...")
    try:
        market_data = api.get_market_prices_v2(location=current_location)
        print(f"DEBUG MARKET: {market_data.keys()}")
        if 'data' in market_data:
             print(f"DEBUG MARKET DATA KEYS: {market_data['data'].keys()}")
        
        if market_data.get('status') == 'success':
            commodities = market_data.get('data', {}).get('commodities', [])
            mandi = market_data.get('data', {}).get('mandi', 'Unknown')
            print(f"   Success! Mandi: {mandi}")
            print(f"   Commodities Found: {len(commodities)}")
            if len(commodities) > 0:
                print(f"      - {commodities[0]['commodity']}: INR {commodities[0]['modal_price']}/Q")
                print(f"      - {commodities[-1]['commodity']}: INR {commodities[-1]['modal_price']}/Q")
        else:
            print(f"   Failed: {market_data}")
    except Exception as e:
        print(f"   Exception: {e}")

    # ---------------------------------------------------------
    # 3. Government Schemes Verification
    # ---------------------------------------------------------
    print("\n3. Testing GOVERNMENT SCHEMES Service...")
    try:
        # Note: calling internal method or public if available. _fetch_government_schemes is internal.
        # But get_comprehensive_government_data calls it. Let's use get_comprehensive_government_data logic or call internal for unit test.
        # Let's call internal for direct verification.
        schemes_data = api._fetch_government_schemes(location=current_location)
        print(f"DEBUG SCHEMES: {schemes_data.keys()}")
        if 'data' in schemes_data:
             print(f"DEBUG SCHEMES DATA KEYS: {schemes_data['data'].keys()}")
        
        if schemes_data.get('status') == 'success':
            schemes = schemes_data.get('data', {}).get('central_schemes', [])
            print(f"   Success! Schemes Found: {len(schemes)}")
            if len(schemes) > 0:
                print(f"      - {schemes[0].get('name', 'Unknown')}")
        else:
            print(f"   Failed: {schemes_data}")
    except Exception as e:
        print(f"   Exception: {e}")

    # ---------------------------------------------------------
    # 4. Crop Recommendations Verification
    # ---------------------------------------------------------
    print("\n4. Testing CROP RECOMMENDATIONS Service (95+ DB)...")
    try:
        # Using the comprehensive method directly to see full output
        crop_data = api._get_fallback_crop_data(location=current_location)
        if crop_data.get('status') == 'success':
            recs = crop_data.get('data', {}).get('recommendations', [])
            season = crop_data.get('data', {}).get('season', 'Unknown')
            region = crop_data.get('data', {}).get('region', 'Unknown')
            print(f"   Success! Season: {season}, Region: {region}")
            print(f"   Recommendations: {len(recs)}")
            if len(recs) > 0:
                top = recs[0]
                print(f"      - Top Crop: {ascii(top.get('crop_name'))}")
                print(f"      - Suitability: {top.get('suitability_score')}%")
                print(f"      - Profit: INR {top.get('profit_per_hectare')}")
                
                # Check for icons logic simulation (frontend does icons, but let's check category)
                print(f"      - Category: {top.get('category', 'N/A')}")
        else:
            print(f"   Failed: {crop_data}")
    except Exception as e:
        print(f"   Exception: {e}")

    print("\n" + "=" * 60)
    print("[OK] Verification Complete")

if __name__ == "__main__":
    test_all_services()
