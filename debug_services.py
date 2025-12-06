import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_mandi_api():
    print("\n--- Testing Mandi API (Ghazipur Mandi) ---")
    try:
        # Test with a real mandi name
        url = f"{BASE_URL}/api/market-prices/?location=Delhi&mandi=Ghazipur%20Mandi"
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if 'market_prices' in data:
                print(f"Market Prices Keys: {list(data['market_prices'].keys())}")
                
                # Check nearby mandis
                if 'nearby_mandis' in data['market_prices']:
                    mandis = [m['name'] for m in data['market_prices']['nearby_mandis']]
                    print(f"Nearby Mandis: {mandis}")
                
                if 'top_crops' in data['market_prices']:
                    print(f"Top Crops Count: {len(data['market_prices']['top_crops'])}")
                    print(json.dumps(data['market_prices']['top_crops'][:1], indent=2))
                else:
                    print("No 'top_crops' in market_prices")
            else:
                print("No 'market_prices' key in response")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

def test_weather_api():
    print("\n--- Testing Weather API (7-day Forecast) ---")
    try:
        url = f"{BASE_URL}/api/weather/?location=Delhi"
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if 'forecast_7_days' in data:
                print(f"7-day Forecast Count: {len(data['forecast_7_days'])}")
            else:
                print("No 'forecast_7_days' found in response!")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_mandi_api()
    test_weather_api()
