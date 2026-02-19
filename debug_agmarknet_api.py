
import requests
import json
from datetime import datetime, timedelta

def debug_api():
    base_url = "https://api.agmarknet.gov.in/v1/daily-price-arrival/report"
    headers = {
        'Origin': 'https://agmarknet.gov.in',
        'Referer': 'https://agmarknet.gov.in/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*'
    }
    
    # Use Session to maintain cookies
    session = requests.Session()
    session.headers.update(headers)
    
    # 1. Visit Home Page to get Cookies
    print("Visiting Home Page to get cookies...")
    try:
        home_resp = session.get("https://agmarknet.gov.in/", timeout=10, verify=False)
        print(f"Home Page Status: {home_resp.status_code}")
        print(f"Cookies: {session.cookies.get_dict()}")
    except Exception as e:
        print(f"Failed to visit home: {e}")

    test_date = "2024-04-26"
    
    # Try looping dates and states to find ANYTHING
    states = [28, 34, 20] # Punjab, UP, MP
    
    print(f"\n--- Testing Broad Search (April 20-30, 2024) with Cookies ---")
    
    start_date = datetime(2024, 4, 20)
    for i in range(10):
        check_date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
        print(f"Checking {check_date}...")
        
        for state_id in states:
            params = {
                "from_date": check_date, "to_date": check_date, 
                "data_type": "100004", 
                "state": state_id, 
                "commodity": 26, # Wheat
                "page": 1, "limit": 1
            }
            try:
                response = session.get(base_url, params=params, timeout=5, verify=False)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('data') and len(data['data']) > 0:
                        print(f"✅ FOUND DATA! Date: {check_date}, State: {state_id}")
                        print(json.dumps(data['data'][0], indent=2))
                        return
                else:
                     # print(f"Status: {response.status_code}") 
                     pass
            except: pass
            
    print("❌ Broad search with cookies failed.")

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()
    debug_api()
