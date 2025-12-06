import requests
from bs4 import BeautifulSoup
from datetime import datetime

def test_scraper():
    print("🌍 Testing Agmarknet Scraper")
    print("=" * 50)
    
    # Try to get data for a specific state (e.g., UP) and date
    date_str = datetime.now().strftime("%d-%b-%Y")
    
    # URL with params - this is a guess at the format based on common ASP.NET patterns
    # We'll try to fetch the "Daily Prices" page
    url = "https://agmarknet.gov.in/SearchCmmMkt.aspx"
    
    params = {
        'Tx_Commodity': '0',
        'Tx_State': 'UP', # Uttar Pradesh
        'Tx_District': '0',
        'Tx_Market': '0',
        'DateFrom': date_str,
        'DateTo': date_str,
        'Fr_Date': date_str,
        'To_Date': date_str,
        'Tx_Trend': '0',
        'Tx_CommodityHead': '--Select--',
        'Tx_StateHead': 'Uttar+Pradesh',
        'Tx_DistrictHead': '--Select--',
        'Tx_MarketHead': '--Select--'
    }
    
    print(f"Fetching {url} with params for {date_str}...")
    
    try:
        response = requests.get(url, params=params, timeout=15, verify=False)
        print(f"Status Code: {response.status_code}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for the grid/table
        table = soup.find('table', {'id': 'cphBody_GridPriceData'})
        
        if table:
            print("✅ Found Price Table!")
            rows = table.find_all('tr')
            print(f"Found {len(rows)} rows")
            
            # Print first few rows
            for i, row in enumerate(rows[:5]):
                cols = [ele.text.strip() for ele in row.find_all('td')]
                if cols:
                    print(f"Row {i}: {cols}")
        else:
            print("❌ Price Table NOT found.")
            # Check if there's an error message
            error = soup.find('span', {'id': 'cphBody_lblError'})
            if error:
                print(f"Error on page: {error.text}")
            else:
                print("No specific error found, but table is missing.")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    test_scraper()
