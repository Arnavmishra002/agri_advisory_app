#!/usr/bin/env python
"""
Service Cards Fix Verification Script
Verifies that all CSS and JavaScript fixes are properly applied to index.html
"""

import os
import re

def verify_fixes():
    """Verify all fixes are applied to index.html"""
    
    print("🔍 Verifying Service Cards Fix...")
    print("=" * 60)
    
    # Read the index.html file
    file_path = os.path.join(os.path.dirname(__file__), 'core', 'templates', 'index.html')
    
    if not os.path.exists(file_path):
        print("❌ ERROR: index.html not found!")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    all_checks_passed = True
    
    # Check 1: .service-card::before has pointer-events: none
    print("\n1. Checking .service-card::before...")
    if re.search(r'\.service-card::before\s*\{[^}]*pointer-events:\s*none', content, re.DOTALL):
        print("   ✅ pointer-events: none found in .service-card::before")
    else:
        print("   ❌ pointer-events: none NOT found in .service-card::before")
        all_checks_passed = False
    
    # Check 2: .service-status has pointer-events: none
    print("\n2. Checking .service-status...")
    if re.search(r'\.service-status\s*\{[^}]*pointer-events:\s*none', content, re.DOTALL):
        print("   ✅ pointer-events: none found in .service-status")
    else:
        print("   ❌ pointer-events: none NOT found in .service-status")
        all_checks_passed = False
    
    # Check 3: .service-icon has pointer-events: none
    print("\n3. Checking .service-icon...")
    if re.search(r'\.service-icon\s*\{[^}]*pointer-events:\s*none', content, re.DOTALL):
        print("   ✅ pointer-events: none found in .service-icon")
    else:
        print("   ❌ pointer-events: none NOT found in .service-icon")
        all_checks_passed = False
    
    # Check 4: .service-title has pointer-events: none
    print("\n4. Checking .service-title...")
    if re.search(r'\.service-title\s*\{[^}]*pointer-events:\s*none', content, re.DOTALL):
        print("   ✅ pointer-events: none found in .service-title")
    else:
        print("   ❌ pointer-events: none NOT found in .service-title")
        all_checks_passed = False
    
    # Check 5: .service-description has pointer-events: none
    print("\n5. Checking .service-description...")
    if re.search(r'\.service-description\s*\{[^}]*pointer-events:\s*none', content, re.DOTALL):
        print("   ✅ pointer-events: none found in .service-description")
    else:
        print("   ❌ pointer-events: none NOT found in .service-description")
        all_checks_passed = False
    
    # Check 6: .service-button::before has pointer-events: none
    print("\n6. Checking .service-button::before...")
    if re.search(r'\.service-button::before\s*\{[^}]*pointer-events:\s*none', content, re.DOTALL):
        print("   ✅ pointer-events: none found in .service-button::before")
    else:
        print("   ❌ pointer-events: none NOT found in .service-button::before")
        all_checks_passed = False
    
    # Check 7: Only one DOMContentLoaded handler exists
    print("\n7. Checking for duplicate DOMContentLoaded handlers...")
    dom_loaded_count = len(re.findall(r"document\.addEventListener\('DOMContentLoaded'", content))
    print(f"   Found {dom_loaded_count} DOMContentLoaded handler(s)")
    if dom_loaded_count == 1:
        print("   ✅ Single DOMContentLoaded handler found (duplicate removed)")
    elif dom_loaded_count == 2:
        print("   ⚠️  WARNING: Duplicate DOMContentLoaded handler still present")
        all_checks_passed = False
    else:
        print(f"   ❌ Unexpected number of DOMContentLoaded handlers: {dom_loaded_count}")
        all_checks_passed = False
    
    # Check 8: Merged DOMContentLoaded handler has all necessary code
    print("\n8. Checking merged DOMContentLoaded handler...")
    if "// Initialize when page loads - MERGED HANDLER" in content:
        print("   ✅ Merged handler comment found")
        
        # Check if it has service card setup
        if re.search(r"serviceCards\.forEach.*data-service", content, re.DOTALL):
            print("   ✅ Service card event listeners setup found")
        else:
            print("   ❌ Service card event listeners setup NOT found")
            all_checks_passed = False
        
        # Check if it has initialization code
        if "sessionId = 'session_' + Date.now()" in content:
            print("   ✅ Session initialization found")
        else:
            print("   ❌ Session initialization NOT found")
            all_checks_passed = False
    else:
        print("   ❌ Merged handler comment NOT found")
        all_checks_passed = False
    
    # Check 9: HTML closing tag
    print("\n9. Checking HTML structure...")
    if content.strip().endswith("</html>"):
        print("   ✅ </html> closing tag found")
    else:
        print("   ❌ </html> closing tag missing")
        all_checks_passed = False
    
    # Check 10: Service cards have data-service attributes
    print("\n10. Checking service cards structure...")
    service_cards = re.findall(r'data-service="([^"]+)"', content)
    expected_services = ['government-schemes', 'crop-recommendations', 'weather', 'market-prices', 'pest-control', 'ai-assistant']
    
    print(f"   Found {len(service_cards)} service card(s):")
    for service in service_cards:
        print(f"      - {service}")
    
    if set(service_cards) == set(expected_services):
        print("   ✅ All 6 service cards present with correct data-service attributes")
    else:
        print("   ❌ Service cards incomplete or incorrect")
        missing = set(expected_services) - set(service_cards)
        if missing:
            print(f"      Missing: {', '.join(missing)}")
        all_checks_passed = False
    
    # Check 11: Global click delegation fallback
    print("\n11. Checking global click delegation fallback...")
    if "// Global click delegation fallback to ensure service cards always work" in content:
        print("   ✅ Global click delegation fallback found")
    else:
        print("   ⚠️  WARNING: Global click delegation fallback comment not found")
    
    # Check 12: showService function exists
    print("\n12. Checking showService function...")
    if "function showService(serviceName)" in content:
        print("   ✅ showService function found")
    else:
        print("   ❌ showService function NOT found")
        all_checks_passed = False
    
    # Final Summary
    print("\n" + "=" * 60)
    if all_checks_passed:
        print("✅ ALL CHECKS PASSED!")
        print("🎉 Service cards fix is properly applied!")
        print("\n📋 Next Steps:")
        print("   1. Start Django server: python manage.py runserver")
        print("   2. Open browser: http://localhost:8000")
        print("   3. Test clicking on each service card")
        print("   4. Verify hover effects work correctly")
        print("   5. Check browser console for any errors")
        return True
    else:
        print("❌ SOME CHECKS FAILED!")
        print("⚠️  Please review the failed checks above.")
        return False

if __name__ == '__main__':
    success = verify_fixes()
    exit(0 if success else 1)

