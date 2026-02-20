import requests
import json

def test_bing_scraper_chatbot():
    url = "http://127.0.0.1:8000/api/chatbot/query/"
    payload = {
        "query": "wheat price in punjab today mandi",
        "location": "Punjab",
        "language": "en"
    }
    headers = {'Content-Type': 'application/json'}
    
    print(f"Testing Chatbot logic instead of direct Bing Scraping (Blocked by Captcha): {url}")
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Chatbot Response: \n{data.get('response')}")
        else:
            print(f"Failed to get chatbot response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_bing_scraper_chatbot()
