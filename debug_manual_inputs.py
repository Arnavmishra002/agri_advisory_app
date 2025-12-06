import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_mandi_search():
    print("\n--- Testing Mandi Search (Location: Delhi) ---")
    try:
        # Test searching for mandis in Delhi
        url = f"{BASE_URL}/api/realtime-gov/mandi_search/?location=Delhi&q=Azadpur"
        print(f"Requesting: {url}")
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Response Keys:", list(data.keys()))
            if 'results' in data:
                print(f"Results Count: {len(data['results'])}")
                print(json.dumps(data['results'], indent=2))
            else:
                print("No 'results' key in response")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")

def test_crop_search():
    print("\n--- Testing Crop Search (Query: Wheat) ---")
    try:
        # Test searching for a crop
        url = f"{BASE_URL}/api/realtime-gov/crop_search/?crop=Wheat&location=Delhi"
        print(f"Requesting: {url}")
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Response Keys:", list(data.keys()))
            if 'comprehensive_analysis' in data:
                print("Found comprehensive_analysis")
            elif 'available_crops' in data:
                print(f"Available Crops: {data['available_crops']}")
            else:
                print("Unexpected response structure")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_mandi_search()
    test_crop_search()
