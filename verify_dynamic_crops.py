import os
import django
import sys
import json

# Setup Django environment
sys.path.append('c:\\AI\\agri_advisory_app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from advisory.services.comprehensive_crop_recommendations import ComprehensiveCropRecommendations
from advisory.services.ultra_dynamic_government_api import UltraDynamicGovernmentAPI

def test_dynamic_recommendations():
    print("Testing Dynamic Crop Recommendations (95+ Crops Integration)")
    print("=" * 60)
    
    gov_api = UltraDynamicGovernmentAPI()
    
    locations = [
        ("Delhi", "Rabi", "North"),
        ("Mumbai", "Kharif", "West"),
        ("Chennai", "Rabi", "South"), # Chennai Rabi is actually cool season but often wet
        ("Kolkata", "Zaid", "East")
    ]
    
    for loc, season_hint, region_hint in locations:
        print(f"\nTesting Location: {loc} ({region_hint})")
        
        # 1. Fetch Comprehensive Data
        print(f"   Fetching government data...")
        data = gov_api.get_comprehensive_government_data(location=loc)
        
        # 2. specific check for crop recommendations
        crop_data = data.get('government_data', {}).get('crop_recommendations', {})
        
        if not crop_data:
            print(f"   No crop data found for {loc}")
            continue
            
        recommendations = crop_data.get('recommendations', [])
        data_source = crop_data.get('data_source', 'Unknown')
        
        print(f"   Data Source: {data_source}")
        print(f"   Found {len(recommendations)} recommendations")
        
        if len(recommendations) > 0:
            print(f"   Top 3 Recommendations:")
            for i, crop in enumerate(recommendations[:3]):
                name = crop.get('crop_name', 'Unknown')
                hindi = crop.get('crop_name_hindi', '')
                score = crop.get('suitability_score', 0)
                profit = crop.get('profit_per_hectare', 0)
                print(f"      {i+1}. {name} - Score: {score}% - Profit: INR {profit}")
                
            # Verify specific fields exist (Deep Verification)
            first_crop = recommendations[0]
            required_fields = ['duration_days', 'water_requirement', 'region_suitability', 'yield_per_hectare']
            missing = [f for f in required_fields if f not in first_crop]
            
            if not missing:
                print(f"   Deep Verification Passed: All advanced metrics present.")
            else:
                print(f"   Deep Verification Failed: Missing fields {missing}")
        else:
            print("   No specific crops returned.")

if __name__ == "__main__":
    test_dynamic_recommendations()
