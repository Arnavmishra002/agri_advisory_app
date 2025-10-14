#!/usr/bin/env python3
import requests
import json
from datetime import datetime

BASE = "https://krishmitra-zrk4.onrender.com"
API = f"{BASE}/api"

def log(name, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name} :: {detail}")

def get_json(resp):
    try:
        return resp.json()
    except Exception:
        return {"raw": resp.text}

def check_health():
    r = requests.get(f"{API}/health/", timeout=20)
    log("health", r.status_code == 200, f"{r.status_code}")

def check_chatbot():
    payload = {
        "query": "What crops should I grow in Delhi?",
        "language": "en",
        "location_name": "Delhi",
        "session_id": f"check_{int(datetime.now().timestamp())}"
    }
    r = requests.post(f"{API}/chatbot/", json=payload, timeout=40)
    ok = r.status_code == 200 and len(get_json(r).get("response", "")) > 30
    log("chatbot (Delhi)", ok, f"{r.status_code}")

def check_weather_locations():
    locations = ["Delhi", "Mumbai"]
    outputs = {}
    ok_all = True
    for loc in locations:
        r = requests.get(f"{API}/realtime-gov/weather/", params={"location": loc}, timeout=30)
        ok = r.status_code == 200
        data = get_json(r)
        outputs[loc] = data
        log(f"weather ({loc})", ok, f"{r.status_code}")
        ok_all = ok_all and ok
    # Compare a field to ensure change
    try:
        d1 = json.dumps(outputs[locations[0]])
        d2 = json.dumps(outputs[locations[1]])
        changed = d1 != d2
        log("weather location variance", changed)
    except Exception:
        log("weather location variance", False, "comparison error")

def check_market_prices():
    r = requests.get(f"{API}/realtime-gov/market_prices/", params={"location": "Delhi", "crop": "wheat"}, timeout=40)
    ok = r.status_code == 200
    log("market prices (wheat, Delhi)", ok, f"{r.status_code}")

def check_government_schemes():
    r = requests.get(f"{API}/realtime-gov/government_schemes/", params={"location": "Delhi"}, timeout=40)
    ok = r.status_code == 200
    log("government schemes (Delhi)", ok, f"{r.status_code}")

def main():
    print(f"Running live checks @ {datetime.now().isoformat()}")
    check_health()
    check_chatbot()
    check_weather_locations()
    check_market_prices()
    check_government_schemes()

if __name__ == "__main__":
    main()


