import os
import sys
import django
import logging

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from advisory.services.village_location_service import EnhancedLocationService
import inspect
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)

# Patch requests.Session.get to have a longer default timeout
original_get = requests.Session.get
def patched_get(self, url, **kwargs):
    if 'timeout' not in kwargs:
        kwargs['timeout'] = 15
    return original_get(self, url, **kwargs)
requests.Session.get = patched_get

def test_village_search():
    print(f"Module file: {inspect.getfile(EnhancedLocationService)}")
    service = EnhancedLocationService()
    
    # Test cases: Known villages in India
    villages = ['Punsari', 'Mawlynnong', 'Hiware Bazar', 'Dharnai']
    
    print("\n--- Testing Village Search ---")
    for village in villages:
        print(f"\nSearching for: {village}")
        results = service.search_locations(village)
        
        if results:
            print(f"Found {len(results)} results:")
            for res in results:
                print(f"  - {res['name']} ({res['type']}): {res['full_address']}")
                print(f"    Source: {res['source']}")
        else:
            print("  No results found.")

if __name__ == "__main__":
    test_village_search()
