
import os
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from advisory.services.ultra_dynamic_government_api import UltraDynamicGovernmentAPI

def verify_logic():
    api = UltraDynamicGovernmentAPI()
    
    print("--- 1. Testing Rajasthan (Sandy Soil, Low Rain) ---")
    data_raj = api._get_fallback_crop_data("Jaipur (Rajasthan)")
    print(f"Zone Detected: {data_raj['data']['agro_zone']}")
    
    recs_raj = data_raj['data']['recommendations']
    top_crops_raj = [r['name'] for r in recs_raj[:5]]
    print(f"Top 5 Crops: {top_crops_raj}")
    
    # Validation: Bajra should be high, Rice should be lower or absent from top
    if 'Bajra' in top_crops_raj or 'Mustard' in top_crops_raj:
        print("✅ PASS: Arid suitable crops found.")
    else:
        print(f"❌ FAIL: Expected Bajra/Mustard, got {top_crops_raj}")
        
    print("\n--- 2. Testing Maharashtra (Black Soil) ---")
    data_mh = api._get_fallback_crop_data("Pune (Maharashtra)")
    print(f"Zone Detected: {data_mh['data']['agro_zone']}")
    
    recs_mh = data_mh['data']['recommendations']
    top_crops_mh = [r['name'] for r in recs_mh[:5]]
    print(f"Top 5 Crops: {top_crops_mh}")
    
    # Validation
    if 'Cotton' in top_crops_mh:
        print("✅ PASS: Black Soil suitable crop (Cotton) found.")
    else:
        print(f"❌ FAIL: Expected Cotton, got {top_crops_mh}")

    print("\n--- 3. Testing Reasoning Accuracy ---")
    # Check if reasoning mentions Soil
    sample_reason = recs_mh[0]['reason']
    print(f"Sample Reason (MH): {sample_reason}")
    
    if "Soil" in sample_reason or "Regional Priority" in sample_reason:
        print("✅ PASS: Reasoning includes scientific/regional factors.")
    else:
        print(f"❌ FAIL: Generic reason found: {sample_reason}")
        
if __name__ == "__main__":
    verify_logic()
