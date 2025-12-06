// Simple diagnostic test
console.log('=== DIAGNOSTIC TEST START ===');

// Test 1: Check if containers exist
console.log('Test 1: Container Check');
const pricesContainer = document.getElementById('pricesData');
const weatherContainer = document.getElementById('weatherData');
const schemesContainer = document.getElementById('schemesData');
const cropsContainer = document.getElementById('cropsData');

console.log('pricesData container:', pricesContainer ? 'FOUND' : 'NOT FOUND');
console.log('weatherData container:', weatherContainer ? 'FOUND' : 'NOT FOUND');
console.log('schemesData container:', schemesContainer ? 'FOUND' : 'NOT FOUND');
console.log('cropsData container:', cropsContainer ? 'FOUND' : 'NOT FOUND');

// Test 2: Test API call
console.log('\nTest 2: API Call Test');
fetch('/api/market-prices/?location=Delhi&latitude=28.7041&longitude=77.1025')
    .then(response => {
        console.log('API Response Status:', response.status);
        return response.json();
    })
    .then(data => {
        console.log('API Data Received:', data);
        console.log('Has market_prices?', !!data.market_prices);
        console.log('Has crops?', !!data.crops);
        if (data.market_prices) {
            console.log('market_prices.top_crops:', data.market_prices.top_crops);
        }
    })
    .catch(error => {
        console.error('API Error:', error);
    });

console.log('=== DIAGNOSTIC TEST END ===');
