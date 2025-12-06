import requests

def test_legacy_urls():
    print("🌍 Testing Legacy Agmarknet URLs")
    print("=" * 50)
    
    urls = [
        "https://agmarknet.gov.in/PriceTrends/SA_Pri_Month.aspx",
        "https://agmarknet.gov.in/MarketProfile/MarketProfile.aspx",
        "https://agmarknet.gov.in/SearchCmmMkt.aspx" # The one that failed before (SPA)
    ]
    
    for url in urls:
        print(f"\nTesting: {url}")
        try:
            response = requests.get(url, timeout=10, verify=False)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                if 'ASP.NET' in response.text or '__VIEWSTATE' in response.text:
                    print("✅ Found ASP.NET WebForm!")
                elif '<div id="root">' in response.text:
                    print("⚠️ Found React App (SPA)")
                else:
                    print("❓ Unknown Content Type")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    test_legacy_urls()
