import requests

def test_enam_via_backend():
    url = "http://127.0.0.1:8000/api/market-prices/?location=Pune"
    print(f"Fetching from Agri Advisory Backend: {url}")
    try:
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            crops = data.get('crops', data.get('top_crops', []))
            print(f"Backend gracefully returned {len(crops)} crops using realtime APIs/fallback.")
            for i, crop in enumerate(crops[:5]):
                print(f"Crop {i+1}: {crop.get('name', crop.get('crop_name'))} - ₹{crop.get('current_price', crop.get('modal_price'))} (Source: {crop.get('source', 'Real-time API/Fallback')})")
        else:
            print("Failed to fetch from backend")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_enam_via_backend()
