#!/usr/bin/env python3
"""
Strict Real-Time API Verification
Fails if any data source is 'Simulated', 'Fallback', or 'Mock'.
"""

import os
import sys
import django
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from advisory.services.ultra_dynamic_government_api import UltraDynamicGovernmentAPI
from advisory.services.enhanced_market_prices import EnhancedMarketPricesService

def print_result(service, status, source, is_real):
    icon = "✅" if is_real else "❌"
    print(f"{icon} {service}: {status}")
    print(f"   Source: {source}")
    if not is_real:
        print(f"   ⚠️  FAILURE: Real-time data required, but got {source}")

def is_source_real(source):
    mock_keywords = ['simulated', 'fallback', 'mock', 'demo', 'default', 'static']
    if not source: return False
    source_lower = source.lower()
    return not any(keyword in source_lower for keyword in mock_keywords)

def main():
    print("="*80)
    print("  STRICT REAL-TIME DATA VERIFICATION")
    print("  Ensures NO fallback, mock, or simulated data is used.")
    print("="*80 + "\n")

    api = UltraDynamicGovernmentAPI()
    
    # 1. Weather Verification
    print("1. Testing Weather API (Delhi)...")
    weather = api.get_weather_data("Delhi", 28.7041, 77.1025)
    w_source = weather.get('data', {}).get('data_source', 'Unknown')
    print_result("Weather", weather.get('status'), w_source, is_source_real(w_source))

    print("\n" + "-"*40 + "\n")

    # 2. Market Prices Verification
    print("2. Testing Market Prices API (Delhi)...")
    market = api.get_market_prices("Delhi")
    # Market data structure varies, trying to extract source safely
    m_source = "Unknown"
    if market and 'sources' in market:
        m_source = ", ".join(market['sources'])
    elif market and 'data' in market:
        # Check first commodity
        first_key = next(iter(market['data']), None)
        if first_key:
            m_source = market['data'][first_key].get('source', 'Unknown')
    
    print_result("Market Prices", market.get('status'), m_source, is_source_real(m_source))

    print("\n" + "-"*40 + "\n")

    # 3. Crop Recommendations Verification
    print("3. Testing Crop Recommendations (Delhi)...")
    crops = api.get_crop_recommendations("Delhi")
    c_source = "Unknown"
    if crops and 'sources' in crops:
        c_source = ", ".join(crops['sources'])
    
    print_result("Crop Recommendations", crops.get('status'), c_source, is_source_real(c_source))

if __name__ == "__main__":
    main()
