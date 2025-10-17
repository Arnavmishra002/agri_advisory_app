// Simple fix for the market prices functionality
const fs = require('fs');

// Read the current HTML file
let content = fs.readFileSync('core/templates/index.html', 'utf8');

// Find the loadMarketPrices function and replace it with a clean version
const functionStart = content.indexOf('async function loadMarketPrices() {');
const functionEnd = content.indexOf('async function searchMandiByLocation() {');

if (functionStart !== -1 && functionEnd !== -1) {
    const beforeFunction = content.substring(0, functionStart);
    const afterFunction = content.substring(functionEnd);
    
    const newFunction = `async function loadMarketPrices() {
        try {
            const container = document.getElementById('pricesData');
            container.innerHTML = '<div class="loading">बाजार भाव लोड हो रहे हैं...</div>';
            
            const response = await fetch(\`/api/realtime-gov/market_prices/?location=\${currentLocation}&latitude=\${currentLatitude}&longitude=\${currentLongitude}\`);
            const data = await response.json();
            
            console.log('Market Prices Data:', data);
            
            if (data.status === 'success' && data.crops && data.crops.length > 0) {
                // Store data globally for mandi selection
                window.allCropsData = data;
                
                // Convert crops array to marketData format for compatibility
                const marketData = {};
                data.crops.forEach(crop => {
                    marketData[crop.name] = crop;
                });
                
                // Display all crops with different prices
                displayAllCropsWithDifferentPrices(data);
            } else {
                container.innerHTML = '<div class="error">बाजार भाव डेटा उपलब्ध नहीं है</div>';
            }
        } catch (error) {
            console.error('Market prices load error:', error);
            document.getElementById('pricesData').innerHTML = '<div class="error">बाजार भाव लोड करने में त्रुटि</div>';
        }
    }

    function displayAllCropsWithDifferentPrices(data) {
        const container = document.getElementById('pricesData');
        
        // Create mandi dropdown options
        const mandiOptions = data.nearest_mandis ? 
            data.nearest_mandis.map(mandi => \`<option value="\${mandi}">\${mandi}</option>\`).join('') : '';
        
        container.innerHTML = \`
            <div class="real-time-header">
                <h4>💰 बाजार भाव - \${data.location}</h4>
                <p class="data-source">📊 स्रोत: \${data.sources ? data.sources.join(', ') : 'Government APIs'}</p>
                <p class="timestamp">🕒 अंतिम अपडेट: \${new Date(data.timestamp).toLocaleString('hi-IN')}</p>
                <p class="reliability">🎯 विश्वसनीयता: \${Math.round((data.data_reliability || 0.9) * 100)}%</p>
            </div>
            
            <div class="mandi-search-container">
                <h5>🔍 मंडी और फसल खोजें</h5>
                <div class="search-boxes-container">
                    <div class="search-box">
                        <label>📍 मंडी चुनें</label>
                        <select id="mandiSelect" class="form-control" onchange="selectMandiFromDropdown()">
                            <option value="">निकटतम मंडी चुनें...</option>
                            \${mandiOptions}
                        </select>
                    </div>
                    <div class="search-box">
                        <label>🌾 फसल खोजें</label>
                        <input type="text" id="cropSearchInput" placeholder="फसल का नाम टाइप करें" class="form-control">
                        <button onclick="searchCropFromSelectedMandi()" class="btn btn-success">खोजें</button>
                    </div>
                </div>
                <div class="current-mandi-display">
                    <span>🏪 वर्तमान: <span id="currentMandiDisplay">सभी मंडियों का औसत</span></span>
                    <button onclick="resetMandiSelection()" class="btn btn-secondary btn-sm">रीसेट</button>
                </div>
            </div>
            
            <div class="mandi-prices-grid">
                \${data.crops.map(crop => \`
                    <div class="mandi-price-square">
                        <div class="square-header">
                            <h6>🌾 \${crop.name}</h6>
                            <span class="trend-icon">📈</span>
                        </div>
                        <div class="square-content">
                            <div class="price-main">
                                <span class="current-price">₹\${crop.current_price?.toLocaleString('hi-IN') || 'N/A'}</span>
                                <span class="price-unit">/quintal</span>
                            </div>
                            <div class="price-details">
                                <div class="detail-row">
                                    <span class="label">MSP:</span>
                                    <span class="value">₹\${crop.msp?.toLocaleString('hi-IN') || 'N/A'}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="label">लाभ:</span>
                                    <span class="value profit">₹\${crop.profit_margin?.toLocaleString('hi-IN') || 'N/A'}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="label">%:</span>
                                    <span class="value">\${crop.profit_percentage || 'N/A'}%</span>
                                </div>
                            </div>
                            <div class="mandi-info">
                                <span class="mandi-name">\${crop.mandi || 'N/A'}</span>
                                <span class="date">\${crop.date || new Date().toLocaleDateString('hi-IN')}</span>
                            </div>
                        </div>
                    </div>
                \`).join('')}
            </div>
        \`;
    }

    // Global variables for mandi selection
    let selectedMandi = null;

    // Function to select mandi from dropdown
    async function selectMandiFromDropdown() {
        const mandiSelect = document.getElementById('mandiSelect');
        const selectedValue = mandiSelect.value;
        const currentMandiDisplay = document.getElementById('currentMandiDisplay');
        
        if (selectedValue) {
            selectedMandi = selectedValue;
            currentMandiDisplay.textContent = selectedValue;
            
            // Fetch prices for selected mandi
            await fetchMandiPrices(selectedValue);
        } else {
            selectedMandi = null;
            currentMandiDisplay.textContent = 'सभी मंडियों का औसत';
            if (window.allCropsData) {
                displayAllCropsWithDifferentPrices(window.allCropsData);
            }
        }
    }

    // Function to fetch prices for specific mandi
    async function fetchMandiPrices(mandiName) {
        try {
            const container = document.getElementById('pricesData');
            container.innerHTML = '<div class="loading">मंडी की कीमतें लोड हो रही हैं...</div>';
            
            const response = await fetch(\`/api/realtime-gov/mandi_prices/?mandi=\${encodeURIComponent(mandiName)}&location=\${currentLocation}\`);
            const data = await response.json();
            
            if (data.status === 'success' && data.crops && data.crops.length > 0) {
                displayMandiSpecificCrops(data.crops, mandiName);
            } else {
                container.innerHTML = '<div class="error">इस मंडी के लिए कीमत जानकारी उपलब्ध नहीं है</div>';
            }
        } catch (error) {
            console.error('Error fetching mandi prices:', error);
            document.getElementById('pricesData').innerHTML = '<div class="error">मंडी कीमतें लोड करने में त्रुटि</div>';
        }
    }

    // Function to display mandi-specific crops
    function displayMandiSpecificCrops(crops, mandiName) {
        const container = document.getElementById('pricesData');
        
        container.innerHTML = \`
            <div class="real-time-header">
                <h4>💰 मंडी: \${mandiName}</h4>
                <p class="data-source">📊 स्रोत: Real-time Mandi Data</p>
                <p class="timestamp">🕒 अंतिम अपडेट: \${new Date().toLocaleString('hi-IN')}</p>
            </div>
            
            <div class="mandi-prices-grid">
                \${crops.map(crop => \`
                    <div class="mandi-price-square">
                        <div class="square-header">
                            <h6>🌾 \${crop.name}</h6>
                            <span class="trend-icon">📈</span>
                        </div>
                        <div class="square-content">
                            <div class="price-main">
                                <span class="current-price">₹\${crop.current_price?.toLocaleString('hi-IN') || 'N/A'}</span>
                                <span class="price-unit">/quintal</span>
                            </div>
                            <div class="price-details">
                                <div class="detail-row">
                                    <span class="label">MSP:</span>
                                    <span class="value">₹\${crop.msp?.toLocaleString('hi-IN') || 'N/A'}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="label">लाभ:</span>
                                    <span class="value profit">₹\${crop.profit_margin?.toLocaleString('hi-IN') || 'N/A'}</span>
                                </div>
                                <div class="detail-row">
                                    <span class="label">%:</span>
                                    <span class="value">\${crop.profit_percentage || 'N/A'}%</span>
                                </div>
                            </div>
                            <div class="mandi-info">
                                <span class="mandi-name">\${crop.mandi || mandiName}</span>
                                <span class="date">\${crop.date || new Date().toLocaleDateString('hi-IN')}</span>
                            </div>
                        </div>
                    </div>
                \`).join('')}
            </div>
        \`;
    }

    // Function to search crop from selected mandi
    async function searchCropFromSelectedMandi() {
        const cropInput = document.getElementById('cropSearchInput');
        const cropName = cropInput.value.trim().toLowerCase();
        
        if (!cropName) {
            alert('कृपया फसल का नाम दर्ज करें');
            return;
        }
        
        if (!selectedMandi) {
            alert('पहले मंडी चुनें');
            return;
        }
        
        try {
            const container = document.getElementById('pricesData');
            container.innerHTML = '<div class="loading">फसल की कीमत खोज रहे हैं...</div>';
            
            const response = await fetch(\`/api/realtime-gov/mandi_prices/?mandi=\${encodeURIComponent(selectedMandi)}&location=\${currentLocation}\`);
            const data = await response.json();
            
            if (data.status === 'success' && data.crops && data.crops.length > 0) {
                const foundCrop = data.crops.find(crop => 
                    crop.name.toLowerCase().includes(cropName)
                );
                
                if (foundCrop) {
                    displayMandiSpecificCrops([foundCrop], selectedMandi);
                } else {
                    container.innerHTML = \`<div class="error">\${selectedMandi} में "\${cropName}" फसल नहीं मिली</div>\`;
                }
            } else {
                container.innerHTML = '<div class="error">इस मंडी के लिए कीमत जानकारी उपलब्ध नहीं है</div>';
            }
        } catch (error) {
            console.error('Error searching crop:', error);
            document.getElementById('pricesData').innerHTML = '<div class="error">फसल खोज में त्रुटि</div>';
        }
    }

    // Function to reset mandi selection
    function resetMandiSelection() {
        const mandiSelect = document.getElementById('mandiSelect');
        const currentMandiDisplay = document.getElementById('currentMandiDisplay');
        const cropInput = document.getElementById('cropSearchInput');
        
        mandiSelect.value = '';
        selectedMandi = null;
        currentMandiDisplay.textContent = 'सभी मंडियों का औसत';
        cropInput.value = '';
        
        if (window.allCropsData) {
            displayAllCropsWithDifferentPrices(window.allCropsData);
        }
    }
    
    // Mandi Search Functions`;

    // Combine the parts
    const newContent = beforeFunction + newFunction + afterFunction;
    
    // Write back to file
    fs.writeFileSync('core/templates/index.html', newContent);
    console.log('Fixed market prices functionality');
} else {
    console.log('Could not find function boundaries');
}
