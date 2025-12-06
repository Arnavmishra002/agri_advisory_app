import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from advisory.services.comprehensive_crop_recommendations import ComprehensiveCropRecommendations

service = ComprehensiveCropRecommendations()
recs = service._get_comprehensive_recommendations_simple('Delhi')

print("Top 4 Recommendations:")
for crop in recs['top_4_recommendations']:
    print(f"Name: {crop['crop_name']}")
    print(f"Name Hindi (Raw): {crop['name_hindi']}")
    print(f"Name Hindi (Type): {type(crop['name_hindi'])}")
    print("-" * 20)
