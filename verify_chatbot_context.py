
import os
import sys

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from advisory.services.ultra_dynamic_government_api import UltraDynamicGovernmentAPI
import json

def verify_chatbot_context():
    try:
        api = UltraDynamicGovernmentAPI()
        loc = "Delhi"
        
        report = []
        report.append(f"--- Testing Chatbot Context for {loc} ---")
        
        # 1. Fetch Context
        context = api.get_comprehensive_government_data(loc)
        
        # 2. Verify Weather
        w = context.get('weather', {})
        report.append(f"Weather: {w.get('temp_max')}°C, Risk: {w.get('risk')}")
        if w.get('temp_max') is None:
            report.append("FAIL: Weather missing")
        else:
            report.append("PASS: Weather integrated")

        # 3. Verify Market
        m = context.get('market', {})
        report.append(f"Mandi: {m.get('mandi')}")
        crops = m.get('top_crops', [])
        if crops:
            report.append(f"Top Market Crop: {crops[0]['name']} @ {crops[0]['price']}")
            report.append("PASS: Market integrated")
        else:
            report.append("FAIL: Market missing")

        # 4. Verify Soil
        s = context.get('soil', {})
        report.append(f"Soil Status: {s.get('status')} (Moisture: {s.get('moisture')})")
        if s.get('status'):
            report.append("PASS: Soil integrated")

        # 5. Verify Schemes
        sch = context.get('schemes', [])
        report.append(f"Schemes Found: {len(sch)}")
        if sch:
            report.append("PASS: Schemes integrated")
        
        report.append("\nFull Data:")
        report.append(json.dumps(context, indent=2, ensure_ascii=False))

        with open('context_verify_result.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        print("Verification complete. Results saved to context_verify_result.txt")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_chatbot_context()
