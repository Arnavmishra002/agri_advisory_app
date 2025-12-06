#!/usr/bin/env python3
"""
Comment out old JavaScript functions in index.html that conflict with enhanced_services.js
"""

with open('core/templates/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and comment out the old functions
in_function = False
function_start = None
functions_to_comment = [
    'async function loadGovernmentSchemes()',
    'async function loadCropRecommendations()',
    'async function loadWeatherData()',
    'async function loadMarketPrices()',
    'function forceReloadMarketPrices()',
    'function reloadAllServices()',
    'function forceReloadAllServices()',
    'function showService(serviceName)',
    'function loadServiceData(serviceName)',
    'function setupServiceCards()',
]

modified_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Check if this line starts one of the functions we want to comment
    if any(func in line for func in functions_to_comment):
        # Found function start - comment it out
        modified_lines.append(f'        /* COMMENTED OUT - Using enhanced_services.js instead\n')
        modified_lines.append(f'        {line}')
        
        # Find the matching closing brace
        brace_count = line.count('{') - line.count('}')
        i += 1
        
        while i < len(lines) and brace_count > 0:
            line = lines[i]
            modified_lines.append(f'        {line}')
            brace_count += line.count('{') - line.count('}')
            i += 1
        
        # Add closing comment
        modified_lines.append(f'        */\n')
        continue
    
    modified_lines.append(line)
    i += 1

# Write back
with open('core/templates/index.html', 'w', encoding='utf-8') as f:
    f.writelines(modified_lines)

print("✅ Commented out old functions in index.html")
print("The following functions are now disabled:")
for func in functions_to_comment:
    print(f"  - {func}")
print("\nenhanced_services.js will now take over!")
