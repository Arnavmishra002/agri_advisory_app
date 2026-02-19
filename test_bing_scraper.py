
import requests
from bs4 import BeautifulSoup
import re

def test_bing():
    query = "wheat price in punjab today mandi"
    url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print(f"Searching Bing: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text()
        
        # Look for price patterns
        # Rs. 2,275 or 2275/Quintal
        price_patterns = [
            r"Rs\.?\s*([\d,]+)",
            r"₹\s*([\d,]+)",
            r"([\d,]+)\s*/\s*Quintal"
        ]
        
        found_price = False
        for pattern in price_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                val_str = match.group(1).replace(',', '')
                if val_str.isdigit():
                    val = float(val_str)
                    if 1000 < val < 10000: # Reasonable range for Wheat
                        print(f"✅ Found Price: {val} (Context: {match.group(0)})")
                        found_price = True
                        break
            if found_price: break
            
        if not found_price:
            print("❌ No valid price found in Bing results.")
            # Print snippet
            print(text[:500])
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_bing()
