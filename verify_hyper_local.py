
import os
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from advisory.services.ultra_dynamic_government_api import UltraDynamicGovernmentAPI

def verify_hyper_local():
    api = UltraDynamicGovernmentAPI()
    
    # Test 1: District Specificity (Nagpur)
    # Nagpur is famous for Oranges. Our logic has a specific bonus for this.
    loc = "Nagpur (Maharashtra)"
    print(f"\n--- Testing District Specificity for {loc} ---")
    data = api._get_fallback_crop_data(loc)
    
    recs = data['data']['recommendations']
    if not recs:
        print("No recommendations found. Check Season.")
        return

    top_crop = recs[0]
    print(f"Top Recommendation: {top_crop['name']} (Score: {top_crop['suitability_score']})")
    print(f"Reason: {top_crop['reason']}")
    print(f"Outlook: {top_crop.get('outlook', 'N/A')}")
    
    # Check for "District" or "Regional" priority in reason
    if "Regional Priority" in top_crop['reason'] or "Regional Specialty" in str(top_crop['factors']):
        print("✅ PASS: District/Regional Priority Applied.")
    else:
        print("❌ FAIL: District Priority missing.")

    # Test 2: Future Weather Integration
    print("\n--- Testing Future Weather Factor ---")
    if 'outlook' in top_crop and top_crop['outlook']:
        print(f"✅ PASS: Future Weather Outlook Included: '{top_crop['outlook']}'")
    else:
        print("❌ FAIL: Outlook key missing.")
        
    # Test 3: Financials
    if 'financials' in top_crop:
        print(f"Financials: {top_crop['financials']}")
        print("✅ PASS: Financial Data Included.")
    else:
        print("❌ FAIL: Financials missing.")

if __name__ == "__main__":
    verify_hyper_local()
