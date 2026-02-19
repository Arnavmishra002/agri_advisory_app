
import requests
import json
from datetime import datetime, timedelta

def test_agmarknet():
    # Punjab = 28, Wheat = 26 (Group 2) from browser findings
    url = "https://api.agmarknet.gov.in/v1/daily-price-arrival/report"
    
    headers = {
        'Origin': 'https://agmarknet.gov.in',
        'Referer': 'https://agmarknet.gov.in/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Content-Type': 'application/json'
    }

    print("Testing Agmarknet Internal API for last 10 days...")
    
    found = False
    for i in range(10):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        print(f"Checking {date}...")
        
        params = {
            'from_date': date,
            'to_date': date,
            'data_type': '100004', # Price
            'group': '2', # Cereals
            'commodity': '26', # Wheat
            'state': '[28]', # Punjab
            'district': '[]',
            'market': '[]',
            'grade': '[]',
            'variety': '[]',
            'page': '1',
            'limit': '10'
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10, verify=False)
            if response.status_code == 200:
                data = response.json()
                if data.get('data') and len(data['data']) > 0:
                    print(f"✅ SUCCESS on {date}!")
                    print(json.dumps(data['data'][0], indent=2))
                    found = True
                    break
                else:
                    print(f"❌ No data for {date}")
            else:
                print(f"⚠️ HTTP {response.status_code} for {date}")
                print(response.text[:200])
        except Exception as e:
            print(f"❌ Error for {date}: {e}")

    if not found:
        print("\n❌ Failed to find ANY data in last 10 days (2026).")
        
        # Try 2025
        print("\nChecking 2025 dates...")
        date = "2025-02-18"
        try:
            params = {
                'from_date': date,
                'to_date': date,
                'data_type': '100004', 
                'group': '2', 
                'commodity': '26', 
                'state': '[28]', 
                'district': '[]', 'market': '[]', 'grade': '[]', 'variety': '[]', 'page': '1', 'limit': '10'
            }
            response = requests.get(url, params=params, headers=headers, timeout=10, verify=False)
            if response.status_code == 200 and len(response.json().get('data', [])) > 0:
                print(f"✅ SUCCESS on {date}!")
            else:
                 print(f"❌ No data for {date}")
        except: pass

        # Try 2024
        print("\nChecking 2024 dates...")
        date = "2024-04-26"
        try:
             params['from_date'] = date
             params['to_date'] = date
             response = requests.get(url, params=params, headers=headers, timeout=10, verify=False)
             if response.status_code == 200 and len(response.json().get('data', [])) > 0:
                print(f"✅ SUCCESS on {date}!")
             else:
                 print(f"❌ No data for {date}")
        except: pass

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()
    test_agmarknet()
