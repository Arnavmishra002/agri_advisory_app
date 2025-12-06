
import requests
import threading
import time
import statistics
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
ENDPOINTS = [
    "/api/market-prices/?location=Delhi&v=v2.0",
    "/api/weather/?location=Mumbai",
    "/api/advisories/?location=Pune"
]
CONCURRENT_USERS = 20
REQUESTS_PER_USER = 5

success_count = 0
failure_count = 0
latencies = []
lock = threading.Lock()

def simulate_user(user_id):
    global success_count, failure_count, latencies
    
    print(f"User {user_id} started.")
    for _ in range(REQUESTS_PER_USER):
        for endpoint in ENDPOINTS:
            try:
                start_time = time.time()
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
                latency = (time.time() - start_time) * 1000 # ms
                
                with lock:
                    latencies.append(latency)
                    if response.status_code == 200:
                        success_count += 1
                    else:
                        failure_count += 1
                        print(f"User {user_id} failed: {endpoint} -> {response.status_code}")
            except Exception as e:
                with lock:
                    failure_count += 1
                print(f"User {user_id} exception: {e}")
    
    print(f"User {user_id} finished.")

def run_load_test():
    print(f"Starting Load Test: {CONCURRENT_USERS} users, {REQUESTS_PER_USER} requests each.")
    print(f"Target: {BASE_URL}")
    print("-" * 50)
    
    start_time = time.time()
    threads = []
    
    for i in range(CONCURRENT_USERS):
        t = threading.Thread(target=simulate_user, args=(i, ))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    total_time = time.time() - start_time
    
    print("-" * 50)
    print("LOAD TEST RESULTS")
    print("-" * 50)
    print(f"Total Requests: {success_count + failure_count}")
    print(f"Successful:     {success_count}")
    print(f"Failed:         {failure_count}")
    print(f"Total Time:     {total_time:.2f}s")
    print(f"RPS:            {(success_count + failure_count) / total_time:.2f}")
    
    if latencies:
        print(f"Avg Latency:    {statistics.mean(latencies):.2f} ms")
        print(f"Max Latency:    {max(latencies):.2f} ms")
        print(f"Min Latency:    {min(latencies):.2f} ms")
    else:
        print("No requests completed.")

if __name__ == "__main__":
    run_load_test()
