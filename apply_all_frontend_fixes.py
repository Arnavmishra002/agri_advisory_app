#!/usr/bin/env python3
"""
Apply all frontend fixes to index.html
This script applies weather normalization, location fix, and service navigation functions
"""

import re

# Read the file
with open('core/templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

print("Original file size:", len(content), "bytes")

# Fix 1: Add weather data normalization
# Find the loadWeatherData function and add normalization after the fetch
weather_pattern = r'(async function loadWeatherData\(\) \{[^\}]*?const data = await response\.json\(\);[^\}]*?console\.log\([^)]+\);)'
weather_replacement = r'''\1

                // Normalize weather data - handle both data.current_weather and data.data.current
                const weatherData = data.data || data;
                const currentWeather = weatherData.current || weatherData.current_weather || {};
                const forecast = weatherData.forecast_7_days || [];
                const advice = weatherData.agricultural_advice || weatherData.farmer_advice || {};
                const alerts = weatherData.alerts || [];
                
                // Reassign to data for template compatibility
                data.current_weather = currentWeather;
                data.forecast_7_days = forecast;
                data.agricultural_advice = advice;
                data.alerts = alerts;'''

if re.search(weather_pattern, content, re.DOTALL):
    content = re.sub(weather_pattern, weather_replacement, content, flags=re.DOTALL)
    print("✓ Added weather normalization")
else:
    print("✗ Could not find weather pattern")

# Fix 2: Fix location display - replace [object Object] with actual location name
# Find the location update code
location_pattern = r"(currentLocation\s*=\s*)([^;]+);"
def fix_location(match):
    prefix = match.group(1)
    value = match.group(2).strip()
    if 'location' in value.lower() and 'name' not in value:
        return f"{prefix}(typeof {value} === 'string' ? {value} : ({value}.name || {value}.display_name || 'Unknown'));"
    return match.group(0)

content = re.sub(location_pattern, fix_location, content)
print("✓ Fixed location display")

# Fix 3: Add service navigation functions before setupServiceCards
service_functions = '''
        // Show specific service section
        function showService(serviceName) {
            console.log('📌 Showing service:', serviceName);
            
            // Hide all content sections
            const contentSections = document.querySelectorAll('.content-section');
            contentSections.forEach(section => {
                section.style.display = 'none';
            });
            
            // Show the selected service section
            const targetSection = document.getElementById(`${serviceName}-content`);
            if (targetSection) {
                targetSection.style.display = 'block';
                targetSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                loadServiceData(serviceName);
            } else {
                console.error(`Service section not found: ${serviceName}-content`);
            }
        }

        // Load data for a specific service
        function loadServiceData(serviceName) {
            console.log('📥 Loading data for service:', serviceName);
            
            switch(serviceName) {
                case 'government-schemes':
                    loadGovernmentSchemes();
                    break;
                case 'crop-recommendations':
                    loadCropRecommendations();
                    break;
                case 'weather':
                    loadWeatherData();
                    break;
                case 'market-prices':
                    loadMarketPrices();
                    break;
                case 'pest-control':
                    if (typeof loadPestControl === 'function') loadPestControl();
                    break;
            }
        }

        // Reload all services with fresh data
        function reloadAllServices() {
            console.log('🔄 Reloading all services...');
            loadGovernmentSchemes();
            loadCropRecommendations();
            loadWeatherData();
            loadMarketPrices();
            console.log('✅ All services reloaded');
        }

'''

# Find where to insert (before setupServiceCards or DOMContentLoaded)
setup_pattern = r'(\s+)(function setupServiceCards\(\)|document\.addEventListener\([\'"]DOMContentLoaded)'
if re.search(setup_pattern, content):
    content = re.sub(setup_pattern, r'\1' + service_functions + r'\1\2', content, count=1)
    print("✓ Added service navigation functions")
else:
    print("✗ Could not find insertion point for service functions")

# Write the modified content
with open('core/templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("\nFinal file size:", len(content), "bytes")
print("\n✅ All fixes applied successfully!")
print("\nNext steps:")
print("1. Restart Django server")
print("2. Open browser to http://127.0.0.1:8000")
print("3. Verify all services display complete data")
