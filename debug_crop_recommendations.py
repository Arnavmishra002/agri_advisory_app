#!/usr/bin/env python3
"""
Debug Crop Recommendations Service
"""

import requests
import json

def debug_crop_recommendations():
    """Debug the crop recommendations service"""
    print("DEBUGGING CROP RECOMMENDATIONS SERVICE")
    print("=" * 50)
    
    # Test with different locations
    test_locations = [
        {"name": "Mumbai", "lat": 19.0760, "lon": 72.8777},
        {"name": "Delhi", "lat": 28.7041, "lon": 77.1025},
        {"name": "Bangalore", "lat": 12.9716, "lon": 77.5946}
    ]
    
    for location in test_locations:
        print(f"\nTesting Location: {location['name']}")
        print("-" * 30)
        
        url = f"http://127.0.0.1:8000/api/realtime-gov/crop_recommendations/"
        params = {
            "location": location["name"],
            "latitude": location["lat"],
            "longitude": location["lon"],
            "season": "rabi"
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"SUCCESS - Got {len(data.get('top_4_recommendations', []))} recommendations")
                
                # Show first recommendation
                if data.get('top_4_recommendations'):
                    first_crop = data['top_4_recommendations'][0]
                    print(f"First Crop: {first_crop.get('crop_name', 'N/A')}")
                    print(f"Profit: ₹{first_crop.get('profit', 'N/A')}")
                    print(f"Yield: {first_crop.get('yield_prediction', 'N/A')} quintals/hectare")
            else:
                print(f"ERROR - Status: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error: {error_data.get('error', 'Unknown error')}")
                except:
                    print(f"Raw Response: {response.text[:200]}")
                    
        except Exception as e:
            print(f"EXCEPTION: {e}")
    
    print(f"\nDebug completed!")

if __name__ == "__main__":
    debug_crop_recommendations()
Debug Crop Recommendations Service
"""

import requests
import json

def debug_crop_recommendations():
    """Debug the crop recommendations service"""
    print("DEBUGGING CROP RECOMMENDATIONS SERVICE")
    print("=" * 50)
    
    # Test with different locations
    test_locations = [
        {"name": "Mumbai", "lat": 19.0760, "lon": 72.8777},
        {"name": "Delhi", "lat": 28.7041, "lon": 77.1025},
        {"name": "Bangalore", "lat": 12.9716, "lon": 77.5946}
    ]
    
    for location in test_locations:
        print(f"\nTesting Location: {location['name']}")
        print("-" * 30)
        
        url = f"http://127.0.0.1:8000/api/realtime-gov/crop_recommendations/"
        params = {
            "location": location["name"],
            "latitude": location["lat"],
            "longitude": location["lon"],
            "season": "rabi"
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"SUCCESS - Got {len(data.get('top_4_recommendations', []))} recommendations")
                
                # Show first recommendation
                if data.get('top_4_recommendations'):
                    first_crop = data['top_4_recommendations'][0]
                    print(f"First Crop: {first_crop.get('crop_name', 'N/A')}")
                    print(f"Profit: ₹{first_crop.get('profit', 'N/A')}")
                    print(f"Yield: {first_crop.get('yield_prediction', 'N/A')} quintals/hectare")
            else:
                print(f"ERROR - Status: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error: {error_data.get('error', 'Unknown error')}")
                except:
                    print(f"Raw Response: {response.text[:200]}")
                    
        except Exception as e:
            print(f"EXCEPTION: {e}")
    
    print(f"\nDebug completed!")

if __name__ == "__main__":
    debug_crop_recommendations()