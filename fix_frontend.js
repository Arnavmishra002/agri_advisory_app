const fs = require('fs');

// Read the HTML file
let content = fs.readFileSync('core/templates/index.html', 'utf8');

// Find and replace the broken fetchMarketPrices function
const oldFunctionStart = content.indexOf('async function fetchMarketPrices() {');
const oldFunctionEnd = content.indexOf('async function searchMandiByLocation() {');

if (oldFunctionStart !== -1 && oldFunctionEnd !== -1) {
    const beforeFunction = content.substring(0, oldFunctionStart);
    const afterFunction = content.substring(oldFunctionEnd);
    
    const newFunction = `async function fetchMarketPrices() {
        try {
            const container = document.getElementById('pricesData');
            container.innerHTML = '<div class="loading">बाजार भाव लोड हो रहे हैं...</div>';
            
            const response = await fetch(\`/api/realtime-gov/market_prices/?location=\${currentLocation}&latitude=\${currentLatitude}&longitude=\${currentLongitude}\`);
            const data = await response.json();
            
            // Convert crops array to marketData format for compatibility
            const marketData = {};
            if (data.crops && data.crops.length > 0) {
                data.crops.forEach(crop => {
                    marketData[crop.name] = crop;
                });
            }
            
            // Use the new displayAllCrops function
            if (marketData && Object.keys(marketData).length > 0) {
                displayAllCrops(data);
            } else {
                container.innerHTML = '<div class="error">बाजार भाव डेटा उपलब्ध नहीं है</div>';
            }
        } catch (error) {
            console.error('Market prices fetch error:', error);
            document.getElementById('pricesData').innerHTML = '<div class="error">बाजार भाव लोड करने में त्रुटि</div>';
        }
    }`;
    
    // Combine the parts
    const newContent = beforeFunction + newFunction + afterFunction;
    
    // Write back to file
    fs.writeFileSync('core/templates/index.html', newContent);
    console.log('Fixed fetchMarketPrices function');
} else {
    console.log('Could not find function boundaries');
}
