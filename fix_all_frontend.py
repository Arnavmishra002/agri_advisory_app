#!/usr/bin/env python3
"""
Apply ALL critical frontend fixes to index.html
This script applies all necessary fixes in one go
"""

import re

# Read the file
with open('core/templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

print(f"Original file size: {len(content)} bytes")
original_content = content

# Fix 1: Add market price normalization in loadMarketPrices
# Find where market data is used and add normalization
market_norm_pattern = r'(const data = await response\.json\(\);[\s\S]{0,200}?)(if \(data\.market_data)'
market_norm_replacement = r'''\1
                // Normalize market data - handle both data.market_data and data.market_prices
                const marketPrices = data.market_prices || data.market_data || {};
                const crops = marketPrices.crops || marketPrices.top_crops || data.crops || [];
                const nearbyMandis = marketPrices.nearby_mandis || data.nearest_mandis_data || [];
                
                \2'''

if re.search(market_norm_pattern, content):
    content = re.sub(market_norm_pattern, market_norm_replacement, content, count=1)
    print("✓ Added market price normalization")
else:
    print("✗ Market price pattern not found")

# Fix 2: Replace data.market_data.top_crops with crops variable
content = re.sub(r'data\.market_data\.top_crops', 'crops', content)
content = re.sub(r'data\.market_data\.nearby_mandis', 'nearbyMandis', content)
print("✓ Updated market price references")

# Fix 3: Add service navigation functions
service_nav_code = '''
        // Service Navigation Functions
        function showService(serviceName) {
            console.log('📌 Showing service:', serviceName);
            const contentSections = document.querySelectorAll('.content-section');
            contentSections.forEach(section => section.style.display = 'none');
            
            const targetSection = document.getElementById(`${serviceName}-content`);
            if (targetSection) {
                targetSection.style.display = 'block';
                targetSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                loadServiceData(serviceName);
            }
        }

        function loadServiceData(serviceName) {
            console.log('📥 Loading data for service:', serviceName);
            switch(serviceName) {
                case 'government-schemes': loadGovernmentSchemes(); break;
                case 'crop-recommendations': loadCropRecommendations(); break;
                case 'weather': loadWeatherData(); break;
                case 'market-prices': loadMarketPrices(); break;
            }
        }

        function reloadAllServices() {
            console.log('🔄 Reloading all services...');
            loadGovernmentSchemes();
            loadCropRecommendations();
            loadWeatherData();
            loadMarketPrices();
        }

'''

# Insert before DOMContentLoaded or at end of script
dom_pattern = r'(\s+)(document\.addEventListener\([\'"]DOMContentLoaded)'
if re.search(dom_pattern, content):
    content = re.sub(dom_pattern, service_nav_code + r'\1\2', content, count=1)
    print("✓ Added service navigation functions")
else:
    # Try inserting before closing script tag
    content = content.replace('</script>', service_nav_code + '\n    </script>')
    print("✓ Added service navigation functions (at end)")

# Fix 4: Fix location display
# Replace currentLocation = location with proper extraction
location_fix_pattern = r'currentLocation\s*=\s*location\s*;'
location_fix_replacement = r"currentLocation = (typeof location === 'string' ? location : (location.name || location.display_name || location.city || 'Unknown'));"
content = re.sub(location_fix_pattern, location_fix_replacement, content)
print("✓ Fixed location display")

# Write the file
with open('core/templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\nFinal file size: {len(content)} bytes")
print(f"Size change: {len(content) - len(original_content):+d} bytes")
print("\n✅ ALL FIXES APPLIED!")
print("\nRestart server and test in browser.")
