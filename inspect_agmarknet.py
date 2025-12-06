import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings()

def inspect_agmarknet():
    # Attempt to hit the search page or a known query URL
    # URL found in common scraping examples or by analyzing the site structure (inference)
    url = "https://agmarknet.gov.in/SearchCmmMkt.aspx"
    
    print(f"Inspecting {url}...")
    try:
        response = requests.get(url, timeout=10, verify=False)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            print("Page Title:", soup.title.string.strip() if soup.title else "No Title")
            
            # Check for form fields to understand what to POST
            form = soup.find('form')
            if form:
                print(f"Form found: {form.get('action')}")
                inputs = form.find_all('input')
                print(f"Found {len(inputs)} inputs. First 5 names:")
                for i in inputs[:5]:
                    print(f" - {i.get('name')}")
            
            # Try a direct GET with params if possible (often .aspx supports this)
            # Example: ?Tx_Commodity=23&Tx_State=DL&Tx_District=1&Tx_Market=0&DateFrom=...&DateTo=...&Fr_Date=...&To_Date=...&Tx_Trend=0&Tx_CommodityHead=Wheat&Tx_StateHead=NCT of Delhi&Tx_DistrictHead=Delhi&Tx_MarketHead=Azadpur
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_agmarknet()
