import os
import django
import sys

# Setup Django environment
sys.path.append('c:\\AI\\agri_advisory_app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from advisory.services.enhanced_market_prices import EnhancedMarketPricesService

def test_mandi_prices():
    print("🌍 Testing Mandi-Specific Market Prices")
    print("=" * 60)
    
    service = EnhancedMarketPricesService()
    
    # Test 1: Get nearest mandis for Delhi
    print("\n📍 Test 1: Get Nearest Mandis for Delhi")
    mandis = service.get_nearest_mandis("Delhi", 28.6139, 77.2090)
    print(f"Found {len(mandis)} mandis:")
    for i, mandi in enumerate(mandis[:5]):
        print(f"  {i+1}. {mandi['name']} ({mandi['distance']}) - {mandi['specialty']}")
    
    # Test 2: Get general market prices for Delhi
    print("\n💰 Test 2: General Market Prices for Delhi")
    general_prices = service.get_market_prices("Delhi", 28.6139, 77.2090)
    if general_prices.get('status') == 'success':
        print(f"Auto-selected Mandi: {general_prices.get('auto_selected_mandi')}")
        print(f"Available Mandis: {general_prices.get('nearest_mandis')}")
        print(f"Top 3 Crops:")
        for i, crop in enumerate(general_prices['crops'][:3]):
            print(f"  {i+1}. {crop['name']}: ₹{crop['current_price']}/quintal (Mandi: {crop['mandi']})")
    
    # Test 3: Get mandi-specific prices
    if mandis:
        mandi_name = mandis[0]['name']
        print(f"\n🏪 Test 3: Mandi-Specific Prices for {mandi_name}")
        mandi_prices = service.get_mandi_specific_prices(mandi_name, "Delhi", 28.6139, 77.2090)
        if mandi_prices.get('status') == 'success':
            print(f"Mandi: {mandi_prices.get('mandi')}")
            print(f"Top 3 Crops:")
            for i, crop in enumerate(mandi_prices['crops'][:3]):
                print(f"  {i+1}. {crop['name']}: ₹{crop['current_price']}/quintal")
    
    # Test 4: Compare prices across different locations
    print("\n🔄 Test 4: Price Comparison Across Locations")
    locations = [("Delhi", 28.6139, 77.2090), ("Mumbai", 19.0760, 72.8777), ("Chennai", 13.0827, 80.2707)]
    
    for loc_name, lat, lon in locations:
        prices = service.get_market_prices(loc_name, lat, lon)
        if prices.get('status') == 'success' and prices['crops']:
            wheat = next((c for c in prices['crops'] if 'wheat' in c['name'].lower()), None)
            if wheat:
                print(f"  {loc_name}: Wheat @ ₹{wheat['current_price']}/quintal (Mandi: {wheat['mandi']})")

if __name__ == "__main__":
    test_mandi_prices()
