
import requests
from bs4 import BeautifulSoup

def test_enam():
    url = "https://enam.gov.in/web/dashboard/trade-data"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print(f"Fetching {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            tables = soup.find_all('table')
            
            # Print table content
            if tables:
                rows = tables[0].find_all('tr')
                print(f"Table has {len(rows)} rows")
                for i, row in enumerate(rows[:10]):
                    cols = [c.get_text(strip=True) for c in row.find_all(['td', 'th'])]
                    print(f"Row {i}: {cols}")
            else:
                 print("No tables found")
                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()
    test_enam()
