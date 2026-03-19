        (function () {
            console.log('🌾 Complete Service Loader Starting...');

            // Global variables
            let currentLocation = 'Delhi';
            let currentLatitude = 28.7041;
            let currentLongitude = 77.1025;
            let currentMandi = 'All Mandis';
            let locationSearchTimeout;

            // ========================================
            // LOCATION FUNCTIONS
            // ========================================

            function updateLocation(locationName, latitude, longitude) {
                currentLocation = locationName;
                currentLatitude = latitude;
                currentLongitude = longitude;

                console.log(`📍 Location updated to: ${locationName} (${latitude}, ${longitude})`);

                const locationDisplay = document.getElementById('currentLocationDisplay');
                if (locationDisplay) {
                    locationDisplay.textContent = locationName;
                }

                console.log('🔄 Reloading all services for new location...');
                loadMarketPrices();
                loadWeatherData();
                loadGovernmentSchemes();
                loadCropRecommendations();
            }

            function searchLocations(event) {
                clearTimeout(locationSearchTimeout);

                const input = event.target;
                const query = input.value.trim();

                if (query.length < 2) {
                    hideLocationSuggestions();
                    return;
                }

                locationSearchTimeout = setTimeout(() => {
                    const indianCities = [
                        { name: 'Delhi', lat: 28.7041, lon: 77.1025 },
                        { name: 'Mumbai', lat: 19.0760, lon: 72.8777 },
                        { name: 'Bangalore', lat: 12.9716, lon: 77.5946 },
                        { name: 'Hyderabad', lat: 17.3850, lon: 78.4867 },
                        { name: 'Chennai', lat: 13.0827, lon: 80.2707 },
                        { name: 'Kolkata', lat: 22.5726, lon: 88.3639 },
                        { name: 'Pune', lat: 18.5204, lon: 73.8567 },
                        { name: 'Ahmedabad', lat: 23.0225, lon: 72.5714 },
                        { name: 'Jaipur', lat: 26.9124, lon: 75.7873 },
                        { name: 'Lucknow', lat: 26.8467, lon: 80.9462 },
                        { name: 'Chandigarh', lat: 30.7333, lon: 76.7794 },
                        { name: 'Indore', lat: 22.7196, lon: 75.8577 },
                        { name: 'Bhopal', lat: 23.2599, lon: 77.4126 },
                        { name: 'Patna', lat: 25.5941, lon: 85.1376 },
                        { name: 'Nagpur', lat: 21.1458, lon: 79.0882 }
                    ];

                    const filtered = indianCities.filter(city =>
                        city.name.toLowerCase().includes(query.toLowerCase())
                    );

                    showLocationSuggestions(filtered);
                }, 300);
            }

            function showLocationSuggestions(suggestions) {
                const container = document.getElementById('locationSuggestions');
                if (!container || !suggestions) return;

                if (suggestions.length === 0) {
                    container.style.display = 'none';
                    return;
                }

                let html = '';
                suggestions.forEach(location => {
                    html += `
            <div class="location-suggestion" onclick="selectLocation('${location.name}', ${location.lat}, ${location.lon})" >
                        📍 ${location.name}
                    </div>
            `;
                });

                container.innerHTML = html;
                container.style.display = 'block';
            }

            function hideLocationSuggestions() {
                const container = document.getElementById('locationSuggestions');
                if (container) {
                    container.style.display = 'none';
                }
            }

            function selectLocation(locationName, latitude, longitude) {
                const input = document.getElementById('locationSearchInput');
                if (input) {
                    input.value = locationName;
                }

                hideLocationSuggestions();
                updateLocation(locationName, latitude, longitude);
            }

            function searchCurrentLocation() {
                const input = document.getElementById('locationSearchInput');
                if (input && input.value.trim()) {
                    const event = new Event('keyup');
                    input.dispatchEvent(event);
                }
            }

            function detectLocation() {
                if (!navigator.geolocation) {
                    alert('Geolocation is not supported by your browser');
                    return;
                }

                console.log('🌍 Detecting location...');

                navigator.geolocation.getCurrentPosition(
                    position => {
                        const lat = position.coords.latitude;
                        const lon = position.coords.longitude;

                        console.log(`📍 Detected coordinates: ${lat}, ${lon} `);

                        // Fetch location name using Reverse Geocoding
                        fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`)
                            .then(response => response.json())
                            .then(data => {
                                console.log('📍 Reverse geocoding result:', data);
                                const address = data.address;
                                // Try to find the most relevant location name
                                const locationName = address.city || address.town || address.village || address.suburb || address.county || 'Detected Location';

                                console.log(`📍 Resolved location name: ${locationName}`);
                                updateLocation(locationName, lat, lon);
                            })
                            .catch(error => {
                                console.error('❌ Error fetching location name:', error);
                                updateLocation('Detected Location', lat, lon);
                            });
                    },
                    error => {
                        console.error('Geolocation error:', error);
                        alert('Unable to detect location. Please search manually.');
                    }
                );
            }

            // ========================================
            // SERVICE NAVIGATION
            // ========================================

            function showService(serviceName) {
                const sections = document.querySelectorAll('.content-section');
                sections.forEach(section => {
                    section.style.display = 'none';
                });

                const targetSection = document.getElementById(serviceName + '-content');
                if (targetSection) {
                    targetSection.style.display = 'block';
                    targetSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }

            function setupServiceCards() {
                const serviceCards = document.querySelectorAll('.service-card, [onclick*="showService"]');
                serviceCards.forEach((card, index) => {
                    const onclickAttr = card.getAttribute('onclick');
                    if (onclickAttr) {
                        const match = onclickAttr.match(/showService\('([^']+)'\)/);
                        if (match) {
                            const serviceName = match[1];
                            card.onclick = function (e) {
                                e.preventDefault();
                                showService(serviceName);
                            };
                        }
                    }
                });
                console.log('✅ Service cards setup complete');
            }

            // ========================================
            // DATA LOADING FUNCTIONS
            // ========================================

            async function loadMarketPrices() {
                try {
                    const container = document.getElementById('pricesData');
                    if (!container) return;

                    container.innerHTML = '<div class="loading">बाजार भाव लोड हो रहे हैं...</div>';

                    const response = await fetch(`/api/market-prices/?location=${currentLocation}&latitude=${currentLatitude}&longitude=${currentLongitude}&v=v2.0`);
                    const data = await response.json();

                    console.log('Market data:', data);

                    const crops = data.crops || data.market_prices?.top_crops || [];
                    const nearbyMandis = data.nearby_mandis || data.market_prices?.nearby_mandis || [];

                    if (crops && crops.length > 0) {
                        let html = `
                        <div class="real-time-header" style="margin-bottom: 20px;">
                            <h4 style="color: #2d5016;">💰 बाजार भाव - ${data.location}</h4>
                            <p style="color: #666; margin: 5px 0;">📊 स्रोत: ${data.data_source || 'Agmarknet + e-NAM'}</p>
                            <p style="color: #666; margin: 5px 0;">🏪 मंडी: ${currentMandi}</p>
                            <p style="color: #666; margin: 5px 0;">🕒 अंतिम अपडेट: ${new Date(data.timestamp || Date.now()).toLocaleString('hi-IN')}</p>
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; margin-top: 20px;">
                    `;

                        crops.forEach(crop => {
                            const profitColor = crop.profit >= 0 ? '#28a745' : '#dc3545';
                            const trendIcon = crop.trend === 'बढ़ रहा' ? '📈' : crop.trend === 'गिर रहा' ? '📉' : '📊';
                            html += `
                            <div style="background: white; border-radius: 15px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); transition: transform 0.3s;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                                    <h6 style="margin: 0; color: #2d5016; font-weight: 700;">🌾 ${crop.crop_name_hindi || crop.crop_name}</h6>
                                    <span style="font-size: 1.2rem;">${trendIcon}</span>
                                </div>
                                <div style="text-align: center; margin-bottom: 15px;">
                                    <div style="font-size: 1.8rem; font-weight: 700; color: #4a7c59;">₹${crop.current_price.toLocaleString('hi-IN')}</div>
                                    <div style="color: #666; font-size: 0.9rem;">/quintal</div>
                                </div>
                                <div style="font-size: 0.9rem; line-height: 1.8;">
                                    <div style="display: flex; justify-content: space-between;">
                                        <span style="color: #666;">MSP:</span>
                                        <span style="font-weight: 600;">₹${crop.msp.toLocaleString('hi-IN')}</span>
                                    </div>
                                    <div style="display: flex; justify-content: space-between;">
                                        <span style="color: #666;">लाभ:</span>
                                        <span style="font-weight: 600; color: ${profitColor};">₹${crop.profit.toLocaleString('hi-IN')}</span>
                                    </div>
                                    <div style="display: flex; justify-content: space-between;">
                                        <span style="color: #666;">मांग:</span>
                                        <span style="font-weight: 600;">${crop.demand || 'मध्यम'}</span>
                                    </div>
                                    <div style="display: flex; justify-content: space-between;">
                                        <span style="color: #666;">आपूर्ति:</span>
                                        <span style="font-weight: 600;">${crop.supply || 'मध्यम'}</span>
                                    </div>
                                </div>
                            </div>
                        `;
                        });

                        html += '</div>';

                        if (nearbyMandis && nearbyMandis.length > 0) {
                            html += `
                            <div style="margin-top: 30px;">
                                <h5 style="color: #2d5016; margin-bottom: 15px;">🏪 निकटतम मंडी (क्लिक करें चयन के लिए)</h5>
                                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px;">
                        `;

                            nearbyMandis.forEach(mandi => {
                                const statusColor = mandi.status === 'खुला' ? '#28a745' : '#dc3545';
                                const isSelected = currentMandi === mandi.name;
                                const borderStyle = isSelected ? 'border: 3px solid #4a7c59;' : 'border: 1px solid #ddd;';
                                html += `
                                <div style="background: ${isSelected ? '#f0f8f0' : '#f8f9fa'}; border-radius: 10px; padding: 15px; ${borderStyle} cursor: pointer; transition: all 0.3s;" 
                                     onclick="selectMandi('${mandi.name}')"
                                     onmouseover="this.style.transform='scale(1.05)'"
                                     onmouseout="this.style.transform='scale(1)'">
                                    <div style="font-weight: 700; color: #2d5016; margin-bottom: 5px;">${mandi.name} ${isSelected ? '✓' : ''}</div>
                                    <div style="font-size: 0.85rem; color: #666;">📍 ${mandi.distance}</div>
                                    <div style="font-size: 0.85rem; color: #666;">🏷️ ${mandi.specialty}</div>
                                    <div style="font-size: 0.85rem; color: ${statusColor}; font-weight: 600;">${mandi.status}</div>
                                </div>
                            `;
                            });

                            html += '</div></div>';
                        }

                        container.innerHTML = html;
                        console.log('✅ Market prices loaded:', crops.length, 'crops,', nearbyMandis.length, 'mandis');
                    } else {
                        container.innerHTML = '<div style="padding: 20px; text-align: center;">बाजार भाव डेटा उपलब्ध नहीं है</div>';
                    }
                } catch (error) {
                    console.error('Market prices error:', error);
                    const container = document.getElementById('pricesData');
                    if (container) container.innerHTML = '<div style="padding: 20px; text-align: center; color: #dc3545;">बाजार भाव लोड करने में त्रुटि</div>';
                }
            }

            function selectMandi(mandiName) {
                console.log('🏪 Selected mandi:', mandiName);
                currentMandi = mandiName;
                loadMarketPrices();
            }

            async function loadWeatherData() {
                try {
                    const container = document.getElementById('weatherData');
                    if (!container) return;

                    container.innerHTML = '<div class="loading">मौसम डेटा लोड हो रहा है...</div>';

                    const response = await fetch(`/api/weather/?location=${currentLocation}&latitude=${currentLatitude}&longitude=${currentLongitude}`);
                    const data = await response.json();
                    // Store weather data globally for chatbot context
                    window.lastWeatherData = data;

                    console.log('Weather data:', data);

                    // Support both API response formats (current vs current_weather)
                    const weather = data.current_weather || data.current || {};
                    const forecast = data.forecast_7_days || data.forecast_7day || [];

                    if (weather && data.location) {
                        let html = `
                        <div style="background: white; border-radius: 15px; padding: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 20px;">
                            <h4 style="color: #2d5016; margin-bottom: 20px;">🌤️ मौसम की जानकारी - ${data.location}</h4>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">
                                <div style="text-align: center;">
                                    <div style="font-size: 3rem; font-weight: 700; color: #4a7c59;">${weather.temperature || '28°C'}</div>
                                    <div style="color: #666; margin-top: 10px;">${weather.condition || weather.description || 'साफ आसमान'}</div>
                                </div>
                                <div>
                                    <div style="margin-bottom: 10px;">💧 नमी: ${weather.humidity || '65%'}</div>
                                    <div style="margin-bottom: 10px;">💨 हवा: ${weather.wind_speed || '12 km/h'}</div>
                                    <div style="margin-bottom: 10px;">🌡️ अनुभव: ${weather.feels_like || '30°C'}</div>
                                    <div style="margin-bottom: 10px;">📊 दबाव: ${weather.pressure || '1013'} ${weather.pressure_unit || 'hPa'}</div>
                                </div>
                            </div>
                        </div>
                    `;

                        if (forecast && forecast.length > 0) {
                            html += `
                            <div style="background: white; border-radius: 15px; padding: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                                <h5 style="color: #2d5016; margin-bottom: 15px;">📅 7 दिन का पूर्वानुमान</h5>
                                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 15px;">
                        `;

                            forecast.slice(0, 7).forEach(day => {
                                html += `
                                <div style="background: #f8f9fa; border-radius: 10px; padding: 15px; text-align: center;">
                                    <div style="font-weight: 700; color: #2d5016; margin-bottom: 5px;">${day.day || day.date}</div>
                                    <div style="font-size: 1.5rem; color: #4a7c59; margin: 10px 0;">${day.temperature || (day.max_temp ? day.max_temp + '°C' : '28°C')}</div>
                                    <div style="font-size: 0.85rem; color: #555;">${day.condition || 'साफ'}</div>
                                    ${day.rainfall_mm !== undefined ? `<div style="font-size: 0.8rem; color: #007bff; margin-top: 4px;">🌧 ${day.rainfall_mm}mm</div>` : ''}
                                </div>
                            `;
                            });

                            html += '</div></div>';
                        }

                        container.innerHTML = html;
                        console.log('✅ Weather loaded with', forecast.length, 'day forecast');
                    } else {
                        container.innerHTML = '<div style="padding: 20px; text-align: center;">मौसम डेटा उपलब्ध नहीं है</div>';
                    }
                } catch (error) {
                    console.error('Weather error:', error);
                    const container = document.getElementById('weatherData');
                    if (container) container.innerHTML = '<div style="padding: 20px; text-align: center; color: #dc3545;">मौसम लोड करने में त्रुटि</div>';
                }
            }

            async function loadGovernmentSchemes() {
                try {
                    const container = document.getElementById('schemesData');
                    if (!container) return;

                    container.innerHTML = '<div class="loading">योजनाएं लोड हो रही हैं...</div>';

                    const response = await fetch(`/api/government-schemes/?location=${currentLocation}`);
                    const data = await response.json();

                    console.log('Schemes data:', data);

                    const schemes = data.schemes || [];

                    if (schemes && schemes.length > 0) {
                        let html = '<div style="display: grid; gap: 20px;">';

                        schemes.forEach(scheme => {
                            // Support both field naming conventions
                            const officialUrl = scheme.official_website || scheme.website || scheme.apply_url || `https://www.google.com/search?q=${encodeURIComponent(scheme.name + ' official website')}`;
                            const benefitText = scheme.benefits_hindi || scheme.benefit_hindi || scheme.benefit || 'विवरण उपलब्ध नहीं';
                            const eligibilityText = scheme.eligibility_hindi || scheme.eligibility || 'सभी किसान';
                            const descText = scheme.description_hindi || scheme.description || '';
                            html += `
                            <div style="background: white; border-radius: 15px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-left: 5px solid #4a7c59; cursor: pointer; transition: transform 0.3s;"
                                 onclick="window.open('${officialUrl}', '_blank')"
                                 onmouseover="this.style.transform='translateY(-5px)'; this.style.boxShadow='0 8px 25px rgba(0,0,0,0.15)'"
                                 onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(0,0,0,0.1)'">
                                <div style="display: flex; justify-content: space-between; align-items: start;">
                                    <h5 style="color: #2d5016; margin-bottom: 15px;">📋 ${scheme.name_hindi || scheme.name}</h5>
                                    <span style="color: #4a7c59; font-size: 1.5rem;">🔗</span>
                                </div>
                                <p style="color: #666; margin-bottom: 15px; line-height: 1.6;">${descText}</p>
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px;">
                                    <div>
                                        <strong style="color: #2d5016;">💰 लाभ:</strong>
                                        <div style="color: #666; font-size: 0.9rem; margin-top: 5px;">${benefitText}</div>
                                    </div>
                                    <div>
                                        <strong style="color: #2d5016;">✅ पात्रता:</strong>
                                        <div style="color: #666; font-size: 0.9rem; margin-top: 5px;">${eligibilityText}</div>
                                    </div>
                                </div>
                                <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #eee; color: #4a7c59; font-size: 0.9rem; font-weight: 600;">
                                    👆 क्लिक करें आधिकारिक वेबसाइट पर जाने के लिए
                                </div>
                            </div>
                        `;
                        });

                        html += '</div>';
                        container.innerHTML = html;
                        console.log('✅ Schemes loaded:', schemes.length, 'schemes');
                    } else {
                        container.innerHTML = '<div style="padding: 20px; text-align: center;">योजनाएं उपलब्ध नहीं हैं</div>';
                    }
                } catch (error) {
                    console.error('Schemes error:', error);
                    const container = document.getElementById('schemesData');
                    if (container) container.innerHTML = '<div style="padding: 20px; text-align: center; color: #dc3545;">योजनाएं लोड करने में त्रुटि</div>';
                }
            }

            async function loadCropRecommendations() {
                try {
                    const container = document.getElementById('cropsData');
                    if (!container) return;

                    container.innerHTML = '<div class="loading">फसल सुझाव लोड हो रहे हैं...</div>';

                    const response = await fetch(`/api/advisories/?location=${currentLocation}`);
                    const data = await response.json();

                    console.log('Crops data:', data);

                    const recommendations = data.recommendations || [];

                    // Helper for category icons
                    const getCategoryIcon = (category) => {
                        const icons = {
                            'Cereal': '🌾', 'Pulse': '🫘', 'Oilseed': '🌻', 'Vegetable': '🥦',
                            'Fruit': '🍎', 'Spice': '🌶️', 'Commercial': '💰', 'Medicinal': '🌿',
                            'Fiber': 'cotton', 'Beverage': '☕', 'Nut': '🥜', 'Sugar': '🍬',
                            'Fungi': '🍄', 'Algae': '🦠', 'Exotic': '✨', 'Flower': '🌸'
                        };
                        return icons[category] || '🌱';
                    };

                    // Helper for water requirement color
                    const getWaterColor = (req) => {
                        if (req === 'high' || req === 'High') return '#007bff'; // Blue
                        if (req === 'moderate' || req === 'Moderate') return '#28a745'; // Green
                        return '#fd7e14'; // Orange for low
                    };

                    if (recommendations && recommendations.length > 0) {
                        let html = `
                        <div class="real-time-header" style="background: linear-gradient(135deg, #2d5016 0%, #4a7c59 100%); margin-bottom: 25px;">
                            <h4 style="color: white; margin-bottom: 10px;">${data.season} के लिए सर्वोत्तम फसल सुझाव - ${data.region}</h4>
                            <p style="color: rgba(255,255,255,0.9); margin: 5px 0;">📊 स्रोत: ${data.data_source}</p>
                            <p style="color: rgba(255,255,255,0.8); font-size: 0.9rem;">${data.message}</p>
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px;">
                    `;

                        recommendations.forEach(crop => {
                            const suitabilityColor = crop.suitability_score >= 85 ? '#28a745' : crop.suitability_score >= 70 ? '#ffc107' : '#dc3545';
                            const categoryIcon = getCategoryIcon(crop.category);
                            const waterColor = getWaterColor(crop.water_requirement);

                            // Check for ML predictions
                            let mlBadge = '';
                            if (crop.ml_confidence || (crop.prediction_data && crop.prediction_data.confidence)) {
                                const confidence = crop.ml_confidence || crop.prediction_data.confidence;
                                const confidencePercent = Math.round(confidence * 100);
                                if (confidencePercent > 0) {
                                    mlBadge = `<div style="margin-top: 10px; background: #e8f0fe; padding: 8px; border-radius: 8px; font-size: 0.85rem; color: #1967d2; display: flex; align-items: center; gap: 5px; border: 1px solid #d2e3fc;">
                                        <span>🤖 AI Confidence: <strong>${confidencePercent}%</strong></span>
                                        ${crop.prediction_data && crop.prediction_data.predicted_yield ? `<span style="margin-left: auto; border-left: 1px solid #ccc; padding-left: 8px;">Est. Yield: <strong>${crop.prediction_data.predicted_yield.toFixed(1)} Q/ha</strong></span>` : ''}
                                    </div>`;
                                }
                            }

                            html += `
                            <div style="background: white; border-radius: 15px; padding: 20px; box-shadow: 0 5px 15px rgba(0,0,0,0.08); transition: transform 0.3s; position: relative; overflow: hidden; border-top: 4px solid ${suitabilityColor};">
                                <div style="position: absolute; top: 10px; right: 10px; background: #f8f9fa; padding: 5px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 700; color: #333; border: 1px solid #ddd;">
                                    ${categoryIcon} ${crop.category}
                                </div>
                                
                                <h5 style="color: #2d5016; font-weight: 700; margin-bottom: 5px; font-size: 1.25rem;">${crop.crop_name_hindi}</h5>
                                <div style="color: #444; font-size: 0.9rem; margin-bottom: 15px; font-weight: 500;">${crop.crop_name}</div>
                                
                                <div style="display: flex; align-items: center; margin-bottom: 15px;">
                                    <div style="flex-grow: 1; height: 8px; background: #eee; border-radius: 4px; overflow: hidden;">
                                        <div style="width: ${crop.suitability_score}%; height: 100%; background: ${suitabilityColor}; border-radius: 4px;"></div>
                                    </div>
                                    <span style="margin-left: 10px; font-weight: 700; color: ${suitabilityColor};">${crop.suitability_score}%</span>
                                </div>
                                
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.9rem; background: #f8f9fa; padding: 10px; border-radius: 10px; mb-3; border: 1px solid #eee;">
                                    <div>
                                        <div style="color: #444; font-size: 0.85rem; font-weight: 600;">अनुमानित लाभ</div>
                                        <div style="font-weight: 700; color: #28a745; font-size: 1rem;">₹${crop.profit_per_hectare.toLocaleString('hi-IN')}</div>
                                    </div>
                                    <div>
                                        <div style="color: #444; font-size: 0.85rem; font-weight: 600;">उपज (क्विंटल/हे.)</div>
                                        <div style="font-weight: 700; color: #2d5016; font-size: 1rem;">${crop.yield_per_hectare} Q</div>
                                    </div>
                                    <div>
                                        <div style="color: #444; font-size: 0.85rem; font-weight: 600;">अवधि</div>
                                        <div style="font-weight: 600; color: #333;">${crop.duration_days} दिन</div>
                                    </div>
                                     <div>
                                        <div style="color: #444; font-size: 0.85rem; font-weight: 600;">पानी की आवश्यकता</div>
                                        <div style="font-weight: 600; color: ${waterColor}; text-transform: capitalize;">${crop.water_requirement}</div>
                                    </div>
                                </div>

                                ${mlBadge}
                                
                                <div style="margin-top: 15px; font-size: 0.9rem; color: #222; background: #fff3cd; padding: 10px; border-radius: 8px; border-left: 3px solid #ffc107;">
                                    💡 <strong>सुझाव:</strong> ${crop.reason_hindi}
                                </div>
                            </div>
                        `;
                        });

                        html += '</div>';
                        container.innerHTML = html;
                        console.log('✅ Crops loaded:', recommendations.length, 'recommendations');
                    } else {
                        container.innerHTML = '<div style="padding: 20px; text-align: center;">फसल सुझाव उपलब्ध नहीं हैं</div>';
                    }
                } catch (error) {
                    console.error('Crops error:', error);
                    const container = document.getElementById('cropsData');
                    if (container) container.innerHTML = '<div style="padding: 20px; text-align: center; color: #dc3545;">फसल सुझाव लोड करने में त्रुटि</div>';
                }
            }

            // ========================================
            // KRISHI RAKSHA 2.0 DIAGNOSTICS
            // ========================================
            async function runKrishiRakshaDiagnosis() {
                const cropSelect = document.getElementById('krCropSelect');
                const resultsContainer = document.getElementById('krishiRakshaResults');

                const crop = cropSelect.value;
                if (!crop) {
                    alert('कृपया फसल चुनें / Please select a crop first');
                    return;
                }

                // Show loading state
                resultsContainer.style.display = 'block';
                resultsContainer.innerHTML = `
                    <div class="text-center p-5">
                        <i class="fas fa-spinner fa-spin fa-3x text-success"></i>
                        <h4 class="mt-3">Analyzing ${crop.charAt(0).toUpperCase() + crop.slice(1)}...</h4>
                        <p>Running Dual AI Pipeline • Verifying with Weather Data...</p>
                    </div>
                `;

                try {
                    const response = await fetch('/api/diagnostics/detect/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            crop: crop,
                            location: currentLocation,
                            images: {},
                            session_id: 'kr_' + Date.now()
                        })
                    });

                    const data = await response.json();
                    console.log('KrishiRaksha Response:', data);

                    if (data.status === 'success') {
                        displayKrishiRakshaResults(data);
                    } else {
                        resultsContainer.innerHTML = `
                            <div class="alert alert-danger">
                                <i class="fas fa-exclamation-triangle"></i> ${data.message || 'Diagnosis failed'}
                            </div>
                        `;
                    }
                } catch (error) {
                    console.error('KrishiRaksha Error:', error);
                    resultsContainer.innerHTML = `
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-triangle"></i> Error connecting to diagnostic service
                        </div>
                    `;
                }
            }

            function displayKrishiRakshaResults(data) {
                const resultsContainer = document.getElementById('krishiRakshaResults');
                const diagnoses = data.diagnosis || [];

                let html = `
                    <div class="real-time-header">
                        <h4>🩺 Diagnostic Report: ${data.crop_detected.charAt(0).toUpperCase() + data.crop_detected.slice(1)}</h4>
                        <p class="data-source">📍 Location: ${data.location}</p>
                        <p class="timestamp">🕒 ${new Date(data.timestamp).toLocaleString('hi-IN')}</p>
                    </div>

                    <div class="row g-4 mt-3">
                `;

                diagnoses.forEach((d, idx) => {
                    const severityColor = d.severity_label === 'High' ? '#dc3545' : (d.severity_label === 'Medium' ? '#ffc107' : '#28a745');
                    const confidencePercent = Math.round(d.confidence * 100);

                    html += `
                        <div class="col-md-6">
                            <div class="card shadow-sm h-100" style="border-left: 4px solid ${severityColor};">
                                <div class="card-header bg-light">
                                    <h5 class="mb-0" style="color: #2d5016; font-weight: 700;">${d.name}</h5>
                                    <small style="color: #444; font-weight: 600;">Rank #${idx + 1}</small>
                                </div>
                                <div class="card-body">
                                    <!-- Confidence -->
                                    <div class="mb-3">
                                        <div class="d-flex justify-content-between mb-1">
                                            <span style="color: #333;"><strong>Confidence:</strong></span>
                                            <span class="badge bg-primary">${confidencePercent}%</span>
                                        </div>
                                        <div class="progress" style="height: 8px;">
                                            <div class="progress-bar bg-primary" style="width: ${confidencePercent}%"></div>
                                        </div>
                                    </div>

                                    <!-- Severity -->
                                    <div class="mb-3">
                                        <div class="d-flex justify-content-between mb-1">
                                            <span style="color: #333;"><strong>Severity:</strong></span>
                                            <span class="badge" style="background-color: ${severityColor}; color: white;">${d.severity_label} (${d.severity_score}%)</span>
                                        </div>
                                        <div class="progress" style="height: 8px;">
                                            <div class="progress-bar" style="width: ${d.severity_score}%; background-color: ${severityColor};"></div>
                                        </div>
                                    </div>

                                    <!-- Symptoms -->
                                    <div class="mb-3">
                                        <strong style="color: #2d5016;">Symptoms:</strong>
                                        <ul class="mb-0 mt-1" style="color: #333;">
                                            ${d.symptoms.map(s => `<li>${s}</li>`).join('')}
                                        </ul>
                                    </div>

                                    <!-- Treatment -->
                                    <div class="mb-2">
                                        <strong style="color: #2d5016;">Treatment:</strong>
                                        <ul class="mb-0 mt-1" style="color: #333;">
                                            ${d.treatment.map(t => `<li>${t}</li>`).join('')}
                                        </ul>
                                    </div>

                                    ${d.verification_note ? `
                                        <div class="alert alert-info py-2 px-3 mt-3 mb-0" style="background-color: #d1ecf1; border-color: #bee5eb; color: #0c5460;">
                                            <small><i class="fas fa-info-circle"></i> ${d.verification_note}</small>
                                        </div>
                                    ` : ''}

                                    ${d.explanation ? `
                                        <div class="alert alert-secondary py-2 px-3 mt-2 mb-0" style="background-color: #e2e3e5; border-color: #d6d8db; color: #383d41;">
                                            <small><strong>Explanation:</strong> ${d.explanation}</small>
                                        </div>
                                    ` : ''}
                                </div>
                            </div>
                        </div>
                    `;
                });

                html += `
                    </div>

                    <!-- Feedback Section -->
                    <div class="card mt-4 shadow-sm">
                        <div class="card-header bg-warning text-dark">
                            <h5 class="mb-0"><i class="fas fa-comment-dots"></i> Was this diagnosis helpful?</h5>
                        </div>
                        <div class="card-body text-center">
                            <button class="btn btn-success me-2" onclick="submitKRFeedback(true)">
                                <i class="fas fa-thumbs-up"></i> Yes, Accurate
                            </button>
                            <button class="btn btn-danger" onclick="submitKRFeedback(false)">
                                <i class="fas fa-thumbs-down"></i> No, Incorrect
                            </button>
                        </div>
                    </div>
                `;

                resultsContainer.innerHTML = html;
            }

            async function submitKRFeedback(isCorrect) {
                try {
                    await fetch('/api/diagnostics/feedback/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            session_id: 'kr_' + Date.now(),
                            is_correct: isCorrect
                        })
                    });
                    alert(isCorrect ? 'धन्यवाद! Feedback recorded.' : 'Thank you. We will improve our model.');
                } catch (error) {
                    console.error('Feedback error:', error);
                }
            }

            // ========================================
            // MAKE FUNCTIONS GLOBALLY AVAILABLE
            // ========================================
            window.updateLocation = updateLocation;
            window.searchLocations = searchLocations;
            window.showLocationSuggestions = showLocationSuggestions;
            window.selectLocation = selectLocation;
            window.searchCurrentLocation = searchCurrentLocation;
            window.detectLocation = detectLocation;
            window.selectMandi = selectMandi;
            window.showService = showService;
            window.loadMarketPrices = loadMarketPrices;
            window.loadWeatherData = loadWeatherData;
            window.loadGovernmentSchemes = loadGovernmentSchemes;
            window.loadCropRecommendations = loadCropRecommendations;
            window.runKrishiRakshaDiagnosis = runKrishiRakshaDiagnosis;
            window.submitKRFeedback = submitKRFeedback;
            window.sendMessage = handleChatUserMessage;
            window.askSuggested = askSuggested;
            window.clearChat = clearChat;

            // ========================================
            // AUTO-INITIALIZE
            // ========================================
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', function () {
                    console.log('📊 Page loaded, initializing...');
                    setupServiceCards();
                    setTimeout(() => {
                        loadMarketPrices();
                        loadWeatherData();
                        loadGovernmentSchemes();
                        loadCropRecommendations();
                    }, 500);
                });
            } else {
                console.log('📊 Page already loaded, initializing...');
                setupServiceCards();
                setTimeout(() => {
                    loadMarketPrices();
                    loadWeatherData();
                    loadGovernmentSchemes();
                    loadCropRecommendations();
                }, 500);
            }
        })();
    </script>
