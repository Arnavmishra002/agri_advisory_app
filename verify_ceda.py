import requests

def test_ceda_api():
    print("🌍 Testing CEDA API")
    print("=" * 50)
    
    # Base URL from search results
    base_url = "https://api.ceda.ashoka.edu.in/v1"
    
    # Try to fetch commodities or markets
    endpoints = [
        f"{base_url}/commodities",
        f"{base_url}/geography",
        f"{base_url}/prices" # Hypothetical
    ]
    
    for url in endpoints:
        print(f"\nTesting: {url}")
        try:
            response = requests.get(url, timeout=10, verify=False)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                try:
                    data = response.json()
                    print("✅ Response is JSON")
                    print(str(data)[:200])
                except:
                    print("⚠️ Response is NOT JSON")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    test_ceda_api()
