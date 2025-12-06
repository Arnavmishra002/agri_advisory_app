import requests
import urllib3

urllib3.disable_warnings()

def test_endpoints():
    endpoints = [
        "https://agmarknet.gov.in/api/price?state=Delhi",
        "https://enam.gov.in/api/market-prices?location=Delhi",
        "https://mausam.imd.gov.in/api/weather?lat=28.61&lon=77.20"
    ]

    print("Testing Government API Endpoints...")
    for url in endpoints:
        print(f"\nTarget: {url}")
        try:
            # Match the new settings in ultra_dynamic_government_api.py
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/json,application/xml;q=0.9,*/*;q=0.8',
                'Referer': 'https://agmarknet.gov.in/'
            }
            response = requests.get(url, timeout=25, verify=False, headers=headers)
            print(f"Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('Content-Type')}")
            if response.status_code == 200:
                try:
                    print("JSON Body Preview:", str(response.json())[:100])
                except:
                    print("Body is not JSON. Preview:", response.text[:200])
        except Exception as e:
            print(f"Failed: {e}")

if __name__ == "__main__":
    test_endpoints()
