
import requests
from bs4 import BeautifulSoup

def test_aggregators():
    urls = [
        "https://www.commodityonline.com/mandiprices/wheat/punjab/26",
        "https://mandiprices.com/wheat-mandi-prices-punjab",
        "https://anajmandi.in/?s=wheat+punjab"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    for url in urls:
        print(f"\n--- Testing {url} ---")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                text = soup.get_text()
                
                # Check for Wheat and Price pattern
                if "Wheat" in text and ("Price" in text or "Rate" in text):
                    print("✅ Found Wheat and Price/Rate keywords!")
                    # Try to find a number near "Rs" or similar
                    # Just print first 200 chars of relevant section
                    idx = text.find("Wheat")
                    print(f"Snippet: {text[idx:idx+300].replace(chr(10), ' ')}")
                    return
                else:
                    print("❌ Page loaded but 'Wheat' + 'Price' not found.")
        except Exception as e:
            print(f"❌ Error: {e}")

    print("\n❌ All aggregators failed.")

if __name__ == "__main__":
    test_aggregators()
