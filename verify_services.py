import os
import django
import sys
import json

# Setup Django environment
sys.path.append('c:\\AI\\agri_advisory_app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from advisory.services.ultra_dynamic_government_api import UltraDynamicGovernmentAPI
from advisory.api.views import ChatbotViewSet

def test_services():
    print("🌍 Testing Agricultural Services")
    print("=" * 50)
    
    gov_api = UltraDynamicGovernmentAPI()
    
    # 1. Weather Service
    print("\n🌤️ Testing Weather Service (Delhi)")
    weather = gov_api.get_weather_data("Delhi", 28.6139, 77.2090)
    if weather.get('status') == 'success':
        data = weather.get('data', {})
        print(f"  Temp: {data.get('temperature')}")
        print(f"  Condition: {data.get('condition')}")
        print("  ✅ Weather Service Working")
    else:
        print("  ❌ Weather Service Failed")
        
    # 2. Market Prices Service
    print("\n💰 Testing Market Prices Service (Delhi)")
    market = gov_api.get_market_prices_v2("Delhi")
    if market.get('status') == 'success':
        data = market.get('data', {})
        print(f"  Mandi: {data.get('mandi')}")
        if data.get('top_crops'):
            print(f"  Top Crop: {data['top_crops'][0]['crop_name']} - {data['top_crops'][0]['current_price']}")
        print("  ✅ Market Prices Service Working")
    else:
        print("  ❌ Market Prices Service Failed")

    # 3. Chatbot Service
    print("\n🤖 Testing Chatbot Service")
    chatbot = ChatbotViewSet()
    # Mocking a request is hard, so we'll test the internal handler if possible
    # Or just test the fallback logic which uses government data
    
    query = "What should I grow in Delhi?"
    print(f"  Query: {query}")
    
    # We can't easily call the viewset methods without a request object, 
    # but we can test the _get_intelligent_fallback_with_government_data method
    # by manually fetching gov data first.
    
    gov_data = gov_api.get_comprehensive_government_data("Delhi")
    response = chatbot._get_intelligent_fallback_with_government_data(
        query=query,
        language="en",
        location="Delhi",
        gov_data=gov_data
    )
    
    if response and response.get('response'):
        print(f"  Response Preview: {response['response'][:100]}...")
        print("  ✅ Chatbot Logic Working")
    else:
        print("  ❌ Chatbot Logic Failed")

if __name__ == "__main__":
    test_services()
