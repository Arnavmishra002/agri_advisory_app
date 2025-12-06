#!/usr/bin/env python3
"""
Apply remaining frontend fixes to index.html
Fixes:
1. Market Prices data normalization
2. Service navigation functions (showService, loadServiceData, reloadAllServices)
"""

import re

def apply_fixes():
    file_path = r'c:\AI\agri_advisory_app\core\templates\index.html'
    
    print("[*] Reading index.html...")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Fix 1: Market Prices Normalization
    print("[*] Fix 1: Adding Market Prices data normalization...")
    
    # Find and replace the market prices check
    old_market_check = r"                \r\n                // Force square box layout for all cases\r\n                if \(data\.market_data && data\.market_data\.top_crops && data\.market_data\.top_crops\.length > 0\) \{"
    
    new_market_check = """                
                // Normalize market data - handle both data.market_data and data.market_prices
                const marketPrices = data.market_prices || data.market_data || {};
                const crops = marketPrices.crops || marketPrices.top_crops || [];
                const nearbyMandis = marketPrices.nearby_mandis || data.nearest_mandis_data || [];
                
                // Force square box layout for all cases
                if (crops && crops.length > 0) {"""
    
    content = re.sub(old_market_check, new_market_check, content)
    
    # Fix 2: Update market data references
    print("[*] Fix 2: Updating market data references...")
    
    # Replace data.market_data.nearby_mandis with nearbyMandis
    content = content.replace(
        '${data.market_data.nearby_mandis ? data.market_data.nearby_mandis.map(mandi =>',
        '${nearbyMandis ? nearbyMandis.map(mandi =>'
    )
    
    # Replace data.market_data.top_crops with crops
    content = content.replace(
        '${data.market_data.top_crops.map(crop =>',
        '${crops.map(crop =>'
    )
    
    # Fix 3: Add service navigation functions
    print("[*] Fix 3: Adding service navigation functions...")
    
    # Find the location to insert (before "// Setup service cards")
    setup_service_cards_marker = "        // Setup service cards with proper event listeners"
    
    service_functions = """        // Show specific service section
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

        """
    
    if setup_service_cards_marker in content:
        content = content.replace(
            setup_service_cards_marker,
            service_functions + setup_service_cards_marker
        )
    
    # Check if changes were made
    if content == original_content:
        print("[!] Warning: No changes were made. Markers might not match exactly.")
        print("    Attempting alternative approach...")
        
        # Alternative: Use simpler pattern matching
        # For market prices, look for the simpler pattern
        if 'if (data.market_data && data.market_data.top_crops && data.market_data.top_crops.length > 0)' in content:
            content = content.replace(
                '                // Force square box layout for all cases\r\n                if (data.market_data && data.market_data.top_crops && data.market_data.top_crops.length > 0) {',
                '''                // Normalize market data - handle both data.market_data and data.market_prices
                const marketPrices = data.market_prices || data.market_data || {};
                const crops = marketPrices.crops || marketPrices.top_crops || [];
                const nearbyMandis = marketPrices.nearby_mandis || data.nearest_mandis_data || [];
                
                // Force square box layout for all cases
                if (crops && crops.length > 0) {'''
            )
            print("    [+] Applied market prices fix using alternative pattern")
    
    # Write the updated content
    print("[*] Writing updated index.html...")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Summary
    changes_made = content != original_content
    if changes_made:
        print("\n[SUCCESS] All fixes applied successfully!")
        print("\n[SUMMARY] Changes made:")
        print("   1. [+] Market Prices data normalization added")
        print("   2. [+] Market data references updated")
        print("   3. [+] Service navigation functions added")
        print("\n[NEXT STEPS]:")
        print("   1. Start Django server: python manage.py runserver")
        print("   2. Open browser to http://127.0.0.1:8000")
        print("   3. Verify all services display real data")
    else:
        print("\n[ERROR] No changes were made. Please check the file manually.")
    
    return changes_made

if __name__ == '__main__':
    try:
        success = apply_fixes()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        exit(1)
