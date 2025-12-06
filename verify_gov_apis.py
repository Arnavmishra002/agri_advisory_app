import requests
import json

def test_apis():
    print("🌍 Testing Government API Endpoints")
    print("=" * 50)
    
    # Agmarknet
    url = "https://agmarknet.gov.in/api/price"
    print(f"\nTesting Agmarknet: {url}")
    try:
        response = requests.get(url, timeout=10, verify=False)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            try:
                data = response.json()
                print("Response is JSON")
                print(str(data)[:200])
            except:
                print("Response is NOT JSON")
                print(response.text[:200])
        else:
            print("Failed to connect")
    except Exception as e:
        print(f"Error: {e}")

    # e-NAM
    url = "https://enam.gov.in/api/market-prices"
    print(f"\nTesting e-NAM: {url}")
    try:
        response = requests.get(url, timeout=10, verify=False)
        print(f"Status Code: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

    # Data.gov.in (Agmarknet) - usually requires key
    url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?api-key=YOUR_KEY&format=json&limit=10"
    print(f"\nTesting Data.gov.in (Agmarknet): {url}")
    try:
        response = requests.get(url, timeout=10, verify=False)
        print(f"Status Code: {response.status_code}")
        print(response.text[:200])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    test_apis()
