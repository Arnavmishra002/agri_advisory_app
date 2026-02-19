
import requests
from bs4 import BeautifulSoup
import re

def test_cc_scraper():
    base_url = "https://commoditiescontrol.com"
    list_url = f"{base_url}/eagritrader/revamp/commodity.php?cid=8"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print(f"Fetching list: {list_url}")
    try:
        response = requests.get(list_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # specific link pattern: India Wheat Market Prices ...
        # We look for "Wheat" and "Market Prices" in the link text
        # Link is in correct relative format
        
        links = soup.find_all('a', href=True)
        target_link = None
        
        for link in links:
            text = link.get_text().strip()
            if "Wheat" in text and "Market Prices" in text and "India" in text:
                print(f"Found Link: {text} -> {link['href']}")
                target_link = link['href']
                break
        
        if not target_link:
            print("❌ Could not find Wheat Market Prices link")
            return

        detail_url = f"{base_url}{target_link}"
        print(f"Fetching detail: {detail_url}")
        
        detail_resp = requests.get(detail_url, headers=headers, timeout=10)
        detail_soup = BeautifulSoup(detail_resp.content, 'html.parser')
        
        # Look for table
        tables = detail_soup.find_all('table')
        if not tables:
            print("❌ No tables found in detail page")
            # Maybe it's not a table but text?
            print(detail_soup.get_text()[:500])
            return

        print(f"Found {len(tables)} tables")
        
        # Usually the main data table is the one with many rows
        main_table = None
        for t in tables:
            if len(t.find_all('tr')) > 5:
                main_table = t
                break
        
        if main_table:
            rows = main_table.find_all('tr')
            print(f"Table has {len(rows)} rows. Sample:")
            for i, row in enumerate(rows[:5]):
                cols = [c.get_text(strip=True) for c in row.find_all(['td', 'th'])]
                print(f"Row {i}: {cols}")
        else:
             print("❌ No large data table found")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_cc_scraper()
