// Enhanced Service Loading Functions for Agri-Advisory App
// Complete implementations for all services: Market Prices, Weather, Government Schemes, Crop Recommendations

// Global variables for location
let currentLocation = 'Delhi';
let currentLatitude = 28.7041;
let currentLongitude = 77.1025;

// ========================================
// MARKET PRICES SERVICE
// ========================================
async function loadMarketPrices() {
    try {
        const container = document.getElementById('pricesData');
        if (!container) {
            console.error('Market prices container not found');
            return;
        }

        container.innerHTML = '<div class="loading">बाजार भाव लोड हो रहे हैं...</div>';

        const response = await fetch(`/api/market-prices/?location=${currentLocation}&latitude=${currentLatitude}&longitude=${currentLongitude}&v=v2.0`);
        const data = await response.json();

        console.log('✅ Market prices data loaded:', data);

        // Extract crops from the correct path in response
        const crops = data.crops || data.market_prices?.top_crops || [];
        const nearbyMandis = data.nearby_mandis || data.market_prices?.nearby_mandis || [];

        if (crops && crops.length > 0) {
            let html = `
                <div class="real-time-header" style="margin-bottom: 20px;">
                    <h4 style="color: #2d5016;">💰 बाजार भाव - ${data.location}</h4>
                    <p style="color: #666; margin: 5px 0;">📊 स्रोत: ${data.data_source || 'Agmarknet + e-NAM'}</p>
                    <p style="color: #666; margin: 5px 0;">🕒 अंतिम अपडेट: ${new Date(data.timestamp || Date.now()).toLocaleString('hi-IN')}</p>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; margin-top: 20px;">
            `;

            crops.forEach(crop => {
                const profitColor = crop.profit >= 0 ? '#28a745' : '#dc3545';
                html += `
                    <div style="background: white; border-radius: 15px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); transition: transform 0.3s;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <h6 style="margin: 0; color: #2d5016; font-weight: 700;">🌾 ${crop.crop_name_hindi || crop.crop_name}</h6>
                            <span style="font-size: 1.2rem;">${crop.trend === 'बढ़ रहा' ? '📈' : crop.trend === 'गिर रहा' ? '📉' : '📊'}</span>
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

            // Add nearby mandis
            if (nearbyMandis && nearbyMandis.length > 0) {
                html += `
                    <div style="margin-top: 30px;">
                        <h5 style="color: #2d5016; margin-bottom: 15px;">🏪 निकटतम मंडी</h5>
                        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px;">
                `;

                nearbyMandis.forEach(mandi => {
                    const statusColor = mandi.status === 'खुला' ? '#28a745' : '#dc3545';
                    html += `
                        <div style="background: #f8f9fa; border-radius: 10px; padding: 15px; border-left: 4px solid #4a7c59;">
                            <div style="font-weight: 700; color: #2d5016; margin-bottom: 5px;">${mandi.name}</div>
                            <div style="font-size: 0.85rem; color: #666;">📍 ${mandi.distance}</div>
                            <div style="font-size: 0.85rem; color: #666;">🏷️ ${mandi.specialty}</div>
                            <div style="font-size: 0.85rem; color: ${statusColor}; font-weight: 600;">${mandi.status}</div>
                        </div>
                    `;
                });

                html += '</div></div>';
            }

            container.innerHTML = html;
            console.log(`✅ Displayed ${crops.length} crops and ${nearbyMandis?.length || 0} mandis`);
        } else {
            container.innerHTML = '<div style="padding: 20px; text-align: center; color: #666;">बाजार भाव डेटा उपलब्ध नहीं है</div>';
        }
    } catch (error) {
        console.error('❌ Error loading market prices:', error);
        const container = document.getElementById('pricesData');
        if (container) {
            container.innerHTML = '<div style="padding: 20px; text-align: center; color: #dc3545;">बाजार भाव लोड करने में त्रुटि</div>';
        }
    }
}

// ========================================
// WEATHER SERVICE
// ========================================
async function loadWeatherData() {
    try {
        const container = document.getElementById('weatherData');
        if (!container) {
            console.log('Weather container not found');
            return;
        }

        container.innerHTML = '<div class="loading">मौसम डेटा लोड हो रहा है...</div>';

        const response = await fetch(`/api/weather/?location=${currentLocation}&latitude=${currentLatitude}&longitude=${currentLongitude}`);
        const data = await response.json();

        console.log('✅ Weather data loaded:', data);

        // Extract weather data from the correct path
        const weather = data.current_weather || data.data?.current || {};
        const forecast = data.forecast_7_days || data.data?.forecast_7_days || [];

        if (weather && (weather.temperature || data.location)) {
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

            // Add forecast if available
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
                            <div style="font-size: 1.5rem; color: #4a7c59; margin: 10px 0;">${day.temperature || '28°C'}</div>
                            <div style="font-size: 0.85rem; color: #666;">${day.condition || 'साफ'}</div>
                        </div>
                    `;
                });

                html += '</div></div>';
            }

            container.innerHTML = html;
        } else {
            container.innerHTML = '<div style="padding: 20px; text-align: center; color: #666;">मौसम डेटा उपलब्ध नहीं है</div>';
        }
    } catch (error) {
        console.error('❌ Error loading weather:', error);
        const container = document.getElementById('weatherData');
        if (container) {
            container.innerHTML = '<div style="padding: 20px; text-align: center; color: #dc3545;">मौसम डेटा लोड करने में त्रुटि</div>';
        }
    }
}

// ========================================
// GOVERNMENT SCHEMES SERVICE
// ========================================
async function loadGovernmentSchemes() {
    try {
        const container = document.getElementById('schemesData');
        if (!container) {
            console.log('Schemes container not found');
            return;
        }

        container.innerHTML = '<div class="loading">योजनाएं लोड हो रही हैं...</div>';

        const response = await fetch(`/api/government-schemes/?location=${currentLocation}`);
        const data = await response.json();

        console.log('✅ Government schemes loaded:', data);

        // Extract schemes from response
        const schemes = data.schemes || [];

        if (schemes && schemes.length > 0) {
            let html = '<div style="display: grid; gap: 20px;">';

            schemes.forEach(scheme => {
                html += `
                    <div style="background: white; border-radius: 15px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-left: 5px solid #4a7c59;">
                        <h5 style="color: #2d5016; margin-bottom: 15px;">📋 ${scheme.name_hindi || scheme.name}</h5>
                        <p style="color: #666; margin-bottom: 15px; line-height: 1.6;">${scheme.description_hindi || scheme.description || ''}</p>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px;">
                            <div>
                                <strong style="color: #2d5016;">💰 लाभ:</strong>
                                <div style="color: #666; font-size: 0.9rem; margin-top: 5px;">${scheme.benefits_hindi || scheme.benefits || 'विवरण उपलब्ध नहीं'}</div>
                            </div>
                            <div>
                                <strong style="color: #2d5016;">✅ पात्रता:</strong>
                                <div style="color: #666; font-size: 0.9rem; margin-top: 5px;">${scheme.eligibility_hindi || scheme.eligibility || 'सभी किसान'}</div>
                            </div>
                        </div>
                    </div>
                `;
            });

            html += '</div>';
            container.innerHTML = html;
            console.log(`✅ Displayed ${schemes.length} schemes`);
        } else {
            container.innerHTML = '<div style="padding: 20px; text-align: center; color: #666;">योजनाएं उपलब्ध नहीं हैं</div>';
        }
    } catch (error) {
        console.error('❌ Error loading schemes:', error);
        const container = document.getElementById('schemesData');
        if (container) {
            container.innerHTML = '<div style="padding: 20px; text-align: center; color: #dc3545;">योजनाएं लोड करने में त्रुटि</div>';
        }
    }
}

// ========================================
// CROP RECOMMENDATIONS SERVICE
// ========================================
async function loadCropRecommendations() {
    try {
        const container = document.getElementById('cropsData') || document.getElementById('cropRecommendationsData');
        if (!container) {
            console.log('Crop recommendations container not found');
            return;
        }

        container.innerHTML = '<div class="loading">फसल सुझाव लोड हो रहे हैं...</div>';

        const response = await fetch(`/api/advisories/?location=${currentLocation}`);
        const data = await response.json();

        console.log('✅ Crop recommendations loaded:', data);

        const recommendations = data.recommendations || [];

        // Helper for category icons
        const getCategoryIcon = (category) => {
            const icons = {
                'Cereal': '🌾', 'Pulse': '🫘', 'Oilseed': '🌻', 'Vegetable': '🥦',
                'Fruit': '🍎', 'Spice': '🌶️', 'Commercial': '💰', 'Medicinal': '🌿'
            };
            return icons[category] || '🌱';
        };

        // Helper for water requirement color
        const getWaterColor = (req) => {
            if (req === 'high') return '#007bff'; // Blue
            if (req === 'moderate') return '#28a745'; // Green
            return '#fd7e14'; // Orange for low
        };

        if (recommendations && recommendations.length > 0) {
            let html = `
                <div class="real-time-header" style="background: linear-gradient(135deg, #2d5016 0%, #4a7c59 100%); margin-bottom: 25px; padding: 20px; border-radius: 12px;">
                    <h4 style="color: white; margin-bottom: 10px;">${data.season} के लिए सर्वोत्तम फसल सुझाव - ${data.region}</h4>
                    <p style="color: rgba(255,255,255,0.9); margin: 5px 0;">📊 स्रोत: ${data.data_source}</p>
                    <p style="color: rgba(255,255,255,0.8); font-size: 0.9rem; margin: 0;">${data.message}</p>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px;">
            `;

            recommendations.forEach((crop, index) => {
                const suitabilityColor = crop.suitability_score >= 85 ? '#28a745' : crop.suitability_score >= 70 ? '#ffc107' : '#dc3545';
                const categoryIcon = getCategoryIcon(crop.category);
                const waterColor = getWaterColor(crop.water_requirement);

                html += `
                    <div style="background: white; border-radius: 15px; padding: 20px; box-shadow: 0 5px 15px rgba(0,0,0,0.08); transition: transform 0.3s; position: relative; overflow: hidden; border-top: 4px solid ${suitabilityColor};">
                        <div style="position: absolute; top: 10px; right: 10px; background: #f8f9fa; padding: 5px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; color: #666; border: 1px solid #eee;">
                            ${categoryIcon} ${crop.category}
                        </div>
                        
                        <h5 style="color: #2d5016; font-weight: 700; margin-bottom: 5px; font-size: 1.25rem;">${index + 1}. ${crop.crop_name_hindi}</h5>
                        <div style="color: #666; font-size: 0.9rem; margin-bottom: 15px;">${crop.crop_name}</div>
                        
                        <div style="display: flex; align-items: center; margin-bottom: 15px;">
                            <div style="flex-grow: 1; height: 8px; background: #eee; border-radius: 4px; overflow: hidden;">
                                <div style="width: ${crop.suitability_score}%; height: 100%; background: ${suitabilityColor}; border-radius: 4px;"></div>
                            </div>
                            <span style="margin-left: 10px; font-weight: 700; color: ${suitabilityColor};">${crop.suitability_score}%</span>
                        </div>
                        
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.9rem; background: #f8f9fa; padding: 10px; border-radius: 10px; margin-bottom: 15px;">
                            <div>
                                <div style="color: #666; font-size: 0.8rem;">अनुमानित लाभ</div>
                                <div style="font-weight: 700; color: #28a745;">₹${crop.profit_per_hectare.toLocaleString('hi-IN')}</div>
                            </div>
                            <div>
                                <div style="color: #666; font-size: 0.8rem;">उपज (क्विंटल/हे.)</div>
                                <div style="font-weight: 700; color: #2d5016;">${crop.yield_per_hectare} Q</div>
                            </div>
                            <div>
                                <div style="color: #666; font-size: 0.8rem;">अवधि</div>
                                <div style="font-weight: 600; color: #555;">${crop.duration_days} दिन</div>
                            </div>
                             <div>
                                <div style="color: #666; font-size: 0.8rem;">पानी की आवश्यकता</div>
                                <div style="font-weight: 600; color: ${waterColor}; text-transform: capitalize;">${crop.water_requirement}</div>
                            </div>
                        </div>
                        
                        <div style="font-size: 0.9rem; color: #555; background: #fff3cd; padding: 10px; border-radius: 8px; border-left: 3px solid #ffc107;">
                            💡 <strong>सुझाव:</strong> ${crop.reason_hindi}
                        </div>
                    </div>
                `;
            });

            html += '</div>';
            container.innerHTML = html;
            console.log(`✅ Displayed ${data.recommendations.length} crop recommendations`);
        } else {
            container.innerHTML = '<div style="padding: 20px; text-align: center; color: #666;">फसल सुझाव उपलब्ध नहीं हैं</div>';
        }
    } catch (error) {
        console.error('❌ Error loading crop recommendations:', error);
        const container = document.getElementById('cropsData') || document.getElementById('cropRecommendationsData');
        if (container) {
            container.innerHTML = '<div style="padding: 20px; text-align: center; color: #dc3545;">फसल सुझाव लोड करने में त्रुटि</div>';
        }
    }
}


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

// ========================================
// SERVICE NAVIGATION FUNCTIONS
// ========================================

function showService(serviceName) {
    console.log('🎯 Showing service:', serviceName);

    try {
        // Hide all content sections
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.remove('active');
        });

        // Show selected content
        const content = document.getElementById(serviceName + '-content');
        if (content) {
            content.classList.add('active');
            content.scrollIntoView({ behavior: 'smooth' });

            // Load data for the service
            loadServiceData(serviceName);
        } else {
            console.error('Content section not found:', serviceName + '-content');
        }
    } catch (error) {
        console.error('Error showing service:', error);
    }
}

function loadServiceData(serviceName) {
    switch (serviceName) {
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
            console.log('Pest control service not yet enhanced');
            break;
        case 'ai-assistant':
            // AI assistant is already loaded
            break;
        default:
            console.warn('Unknown service:', serviceName);
    }
}

function setupServiceCards() {
    const serviceCards = document.querySelectorAll('.service-card');
    console.log('🎯 Setting up', serviceCards.length, 'service cards');

    serviceCards.forEach((card, index) => {
        // Add click event listener
        card.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();

            // Get service name from onclick attribute
            const onclickAttr = this.getAttribute('onclick');
            const serviceName = onclickAttr?.match(/showService\('([^']+)'\)/)?.[1];

            if (serviceName) {
                console.log('🎯 Service card clicked:', serviceName);
                showService(serviceName);

                // Add visual feedback
                this.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    this.style.transform = '';
                }, 150);
            } else {
                console.error('Service name not found for card:', this);
            }
        });

        console.log(`✅ Service card ${index + 1} setup complete`);
    });
}

// Make functions globally available
window.showService = showService;
window.loadServiceData = loadServiceData;
window.setupServiceCards = setupServiceCards;

// ========================================
// AUTO-LOAD ALL SERVICES
// ========================================
document.addEventListener('DOMContentLoaded', function () {
    console.log('🌾 Enhanced Services Script Loaded - All Services Ready');

    // Setup service cards
    setupServiceCards();

    // Auto-load all services after page load
    setTimeout(() => {
        console.log('📊 Loading all services...');
        loadMarketPrices();
        loadWeatherData();
        loadGovernmentSchemes();
        loadCropRecommendations();
        console.log('✅ All services loaded');
    }, 1000);
});

console.log('✅ Enhanced Services Module Ready - Market Prices, Weather, Schemes, Crop Recommendations');
