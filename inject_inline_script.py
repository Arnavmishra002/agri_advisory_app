import re

# Read the index.html file
with open('c:/AI/agri_advisory_app/core/templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Complete inline script with RICH UI
inline_script = '''
    <!-- Inline Service Loading Script -->
    <script>
    (function() {
        console.log('🌾 Inline Service Loader Starting...');
        
        // Global variables
        let currentLocation = 'Delhi';
        let currentLatitude = 28.7041;
        let currentLongitude = 77.1025;
        
        // Show/Hide service sections
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
        
        // Setup service card clicks
        function setupServiceCards() {
            const serviceCards = document.querySelectorAll('.service-card, [onclick*="showService"]');
            serviceCards.forEach((card, index) => {
                const onclickAttr = card.getAttribute('onclick');
                if (onclickAttr) {
                    const match = onclickAttr.match(/showService\\('([^']+)'\\)/);
                    if (match) {
                        const serviceName = match[1];
                        card.onclick = function(e) {
                            e.preventDefault();
                            showService(serviceName);
                        };
                    }
                }
            });
            console.log('✅ Service cards setup complete');
        }
        
        // Market Prices Loader - RICH UI
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
        
        // Weather Loader - RICH UI with Forecast
        async function loadWeatherData() {
            try {
                const container = document.getElementById('weatherData');
                if (!container) return;
                
                container.innerHTML = '<div class="loading">मौसम डेटा लोड हो रहा है...</div>';
                
                const response = await fetch(`/api/weather/?location=${currentLocation}&latitude=${currentLatitude}&longitude=${currentLongitude}`);
                const data = await response.json();
                
                console.log('Weather data:', data);
                
                const weather = data.current_weather || {};
                const forecast = data.forecast_7_days || [];
                
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
                    
                    // Add 7-day forecast
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
        
        // Schemes Loader - RICH UI with Benefits & Eligibility
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
        
        // Crops Loader - RICH UI with Suitability Scores
        async function loadCropRecommendations() {
            try {
                const container = document.getElementById('cropsData');
                if (!container) return;
                
                container.innerHTML = '<div class="loading">फसल सुझाव लोड हो रहे हैं...</div>';
                
                const response = await fetch(`/api/advisories/?location=${currentLocation}`);
                const data = await response.json();
                
                console.log('Crops data:', data);
                
                const recommendations = data.recommendations || [];
                
                if (recommendations && recommendations.length > 0) {
                    let html = '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px;">';
                    
                    recommendations.forEach(crop => {
                        const suitabilityColor = crop.suitability_score >= 80 ? '#28a745' : crop.suitability_score >= 60 ? '#ffc107' : '#dc3545';
                        html += `
                            <div style="background: white; border-radius: 15px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                                <h6 style="color: #2d5016; font-weight: 700; margin-bottom: 10px;">🌱 ${crop.crop_name_hindi || crop.crop_name}</h6>
                                <div style="margin-bottom: 10px;">
                                    <div style="font-size: 0.85rem; color: #666;">उपयुक्तता स्कोर</div>
                                    <div style="font-size: 1.5rem; font-weight: 700; color: ${suitabilityColor};">${crop.suitability_score || 85}%</div>
                                </div>
                                <div style="font-size: 0.9rem; color: #666;">
                                    ${crop.reason_hindi || crop.reason || 'इस मौसम के लिए उपयुक्त'}
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
        
        // Make functions globally available
        window.showService = showService;
        window.loadMarketPrices = loadMarketPrices;
        window.loadWeatherData = loadWeatherData;
        window.loadGovernmentSchemes = loadGovernmentSchemes;
        window.loadCropRecommendations = loadCropRecommendations;
        
        // Auto-load on page ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() {
                console.log('📊 Page loaded, setting up services...');
                setupServiceCards();
                setTimeout(() => {
                    loadMarketPrices();
                    loadWeatherData();
                    loadGovernmentSchemes();
                    loadCropRecommendations();
                }, 500);
            });
        } else {
            console.log('📊 Page already loaded, setting up services...');
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
'''

# Find and replace the inline script section
pattern = r'<!-- Inline Service Loading Script -->.*?</script>'
content = re.sub(pattern, inline_script.strip(), content, flags=re.DOTALL)

# Write back
with open('c:/AI/agri_advisory_app/core/templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Rich UI with complete data display restored!")
