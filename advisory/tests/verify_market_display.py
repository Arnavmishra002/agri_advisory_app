
import os
import django
import sys
from unittest.mock import patch, MagicMock

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from advisory.services.ultra_dynamic_government_api import UltraDynamicGovernmentAPI

def verify_market_keys():
    service = UltraDynamicGovernmentAPI()
    
    # Mock _fetch_market_prices to return None (Force Fallback)
    with patch.object(service, '_fetch_market_prices', return_value=None):
        print("Testing Fallback (Simulation)...")
        data = service.get_market_prices_v2("Delhi")
        
        if data['status'] != 'success':
            print("FAILED: Status not success")
            return
            
        crops = data['market_prices']['crops']
        if not crops:
            print("FAILED: No crops returned")
            return
            
        first_crop = crops[0]
        print(f"Keys found: {list(first_crop.keys())}")
        
        required_keys = ['name', 'profit_margin', 'current_price', 'msp']
        missing = [k for k in required_keys if k not in first_crop]
        
        if missing:
            print(f"FAILED: Missing keys for Frontend: {missing}")
        else:
            print("SUCCESS: All Frontend keys present for Simulation.")

    # Mock _fetch_market_prices to return Real Data structural equivalent
    real_data_mock = {
        'status': 'success',
        'data': {
            'Wheat': {'current_price': 2500, 'msp': 2125}
        }
    }
    with patch.object(service, '_fetch_market_prices', return_value=real_data_mock):
        print("\nTesting Real Data Normalization...")
        data = service.get_market_prices_v2("Delhi")
        
        crops = data['market_prices']['crops']
        first_crop = crops[0]
        print(f"Keys found: {list(first_crop.keys())}")
        
        missing = [k for k in required_keys if k not in first_crop]
        
        if missing:
            print(f"FAILED: Missing keys for Frontend in Real Data: {missing}")
        else:
            print("SUCCESS: All Frontend keys present for Real Data.")

if __name__ == "__main__":
    verify_market_keys()
