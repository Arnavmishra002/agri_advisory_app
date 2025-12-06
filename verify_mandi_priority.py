import sys
import os
import django
from unittest.mock import MagicMock

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from advisory.services.ultra_dynamic_government_api import UltraDynamicGovernmentAPI

def verify_priority():
    api = UltraDynamicGovernmentAPI()
    
    # Mock _fetch_market_prices to simulate a successful API hit
    # This proves that IF the API works, it takes precedence
    mock_data = {
        'status': 'success',
        'data': {
            'RealTimeWheat': {'current_price': 5000, 'msp': 4000},
            'RealTimeRice': {'current_price': 6000, 'msp': 5000}
        }
    }
    api._fetch_market_prices = MagicMock(return_value=mock_data)
    
    print("Testing Mandi Priority Logic...")
    result = api.get_market_prices_v2("Delhi", mandi="Azadpur Test Mandi")
    
    # Check if _fetch_market_prices was called with the mandi
    api._fetch_market_prices.assert_called_with("Delhi", mandi_filter="Azadpur Test Mandi")
    print("✅ Logic Correct: _fetch_market_prices called with specific mandi.")
    
    # Check if the result contains the mocked data (RealTimeWheat) instead of simulated data
    crops = result.get('market_prices', {}).get('crops', [])
    crop_names = [c['crop_name'] for c in crops]
    
    if 'RealTimeWheat' in crop_names:
        print("✅ Priority Correct: Returned real-time API data over simulation.")
        print(f"   Source: {result.get('data_source')}")
    else:
        print("❌ FAILED: Returned simulation data instead of real API data.")
        print(f"   Crops found: {crop_names}")

if __name__ == "__main__":
    verify_priority()
