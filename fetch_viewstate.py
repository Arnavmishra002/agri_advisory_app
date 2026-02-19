
import requests
from bs4 import BeautifulSoup

def fetch_viewstate():
    url = "https://agmarknet.gov.in/PriceTrends/SA_Pri_Month.aspx"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        viewstate = soup.find('input', {'id': '__VIEWSTATE'})
        eventvalidation = soup.find('input', {'id': '__EVENTVALIDATION'})
        
        if viewstate:
            print(f"__VIEWSTATE found (len={len(viewstate['value'])})")
        else:
            print("__VIEWSTATE NOT found")
            
        if eventvalidation:
             print(f"__EVENTVALIDATION found (len={len(eventvalidation['value'])})")
        else:
             print("__EVENTVALIDATION NOT found")
             
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()
    fetch_viewstate()
