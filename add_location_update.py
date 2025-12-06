#!/usr/bin/env python3
"""
Add location update functionality to enhanced_services.js
This allows the location button to update global location variables
"""

# Read the current file
with open('core/enhanced_services.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Add location update function before the DOMContentLoaded
location_update_code = '''
// ========================================
// LOCATION UPDATE FUNCTION
// ========================================
function updateLocation(locationName, latitude, longitude) {
    currentLocation = locationName;
    currentLatitude = latitude;
    currentLongitude = longitude;
    
    console.log(`📍 Location updated to: ${locationName} (${latitude}, ${longitude})`);
    
    // Reload all services with new location
    console.log('🔄 Reloading all services for new location...');
    loadMarketPrices();
    loadWeatherData();
    loadGovernmentSchemes();
    loadCropRecommendations();
}

// Make function globally available
window.updateLocation = updateLocation;

'''

# Insert before DOMContentLoaded
insertion_point = content.find('// ========================================\n// AUTO-LOAD ALL SERVICES')
if insertion_point != -1:
    content = content[:insertion_point] + location_update_code + content[insertion_point:]
    
    with open('core/enhanced_services.js', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Added location update function to enhanced_services.js")
    print("\nNow you can call: updateLocation('Mumbai', 19.0760, 72.8777)")
    print("from anywhere in your code to update location and reload all services!")
else:
    print("❌ Could not find insertion point")
