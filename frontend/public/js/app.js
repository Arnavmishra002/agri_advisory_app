(function () {
    console.log('🌾 Complete Service Loader Starting...');

    /** Resolve API URL (config.js module may load slightly after this script). */
    function apiFetch(path) {
        if (typeof window.apiUrl === 'function') {
            return window.apiUrl(path);
        }
        const base = String(window.API_BASE_URL || '').replace(/\/$/, '');
        const p = path.startsWith('/') ? path : `/${path}`;
        if (base) {
            return `${base}${p}`;
        }
        return p;
    }

    async function apiGetJson(path) {
        const response = await fetch(apiFetch(path));
        if (!response.ok) {
            let detail = '';
            try {
                const errBody = await response.json();
                detail = errBody.message || errBody.error || '';
            } catch (e) {
                detail = '';
            }
            throw new Error(`HTTP ${response.status}${detail ? ': ' + detail : ''}`);
        }
        return response.json();
    }

    async function apiPostJson(path, body) {
        const response = await fetch(apiFetch(path), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!response.ok) {
            let detail = '';
            try {
                const errBody = await response.json();
                detail = errBody.message || errBody.error || '';
            } catch (e) {
                detail = '';
            }
            throw new Error(`HTTP ${response.status}${detail ? ': ' + detail : ''}`);
        }
        return response.json();
    }

    // Global variables
    let currentLocation = 'Delhi';
    let currentLatitude = 28.7041;
    let currentLongitude = 77.1025;
    let currentState = 'Delhi';
    let currentLocationAccuracy = null;
    let allMandisCache = [];
    let mandiDropdownVisibleCount = 100;
    let currentMandi = '';
    let currentCropSearch = '';
    let krSelectedCrop = '';
    let locationSearchTimeout;
    let cropSearchTimeout;
    let krCropSearchTimeout;
    const sessionId = (() => {
        try {
            const key = 'krishi_session_id';
            let id = localStorage.getItem(key);
            if (!id) {
                id = 'sess_' + Date.now();
                localStorage.setItem(key, id);
            }
            return id;
        } catch (e) {
            return 'sess_' + Date.now();
        }
    })();

    const escapeHtml = (s) => String(s || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');

    const INDIAN_CITIES = [
        { name: 'Delhi', state: 'Delhi', lat: 28.7041, lon: 77.1025 },
        { name: 'Mumbai', state: 'Maharashtra', lat: 19.0760, lon: 72.8777 },
        { name: 'Bangalore', state: 'Karnataka', lat: 12.9716, lon: 77.5946 },
        { name: 'Hyderabad', state: 'Telangana', lat: 17.3850, lon: 78.4867 },
        { name: 'Chennai', state: 'Tamil Nadu', lat: 13.0827, lon: 80.2707 },
        { name: 'Kolkata', state: 'West Bengal', lat: 22.5726, lon: 88.3639 },
        { name: 'Pune', state: 'Maharashtra', lat: 18.5204, lon: 73.8567 },
        { name: 'Ahmedabad', state: 'Gujarat', lat: 23.0225, lon: 72.5714 },
        { name: 'Jaipur', state: 'Rajasthan', lat: 26.9124, lon: 75.7873 },
        { name: 'Lucknow', state: 'Uttar Pradesh', lat: 26.8467, lon: 80.9462 },
        { name: 'Chandigarh', state: 'Chandigarh', lat: 30.7333, lon: 76.7794 },
        { name: 'Indore', state: 'Madhya Pradesh', lat: 22.7196, lon: 75.8577 },
        { name: 'Bhopal', state: 'Madhya Pradesh', lat: 23.2599, lon: 77.4126 },
        { name: 'Patna', state: 'Bihar', lat: 25.5941, lon: 85.1376 },
        { name: 'Nagpur', state: 'Maharashtra', lat: 21.1458, lon: 79.0882 },
        { name: 'Noida', state: 'Uttar Pradesh', lat: 28.5355, lon: 77.3910 },
        { name: 'Gurgaon', state: 'Haryana', lat: 28.4595, lon: 77.0266 },
        { name: 'Surat', state: 'Gujarat', lat: 21.1702, lon: 72.8311 },
        { name: 'Kanpur', state: 'Uttar Pradesh', lat: 26.4499, lon: 80.3319 },
        { name: 'Varanasi', state: 'Uttar Pradesh', lat: 25.3176, lon: 82.9739 },
        { name: 'Ludhiana', state: 'Punjab', lat: 30.9010, lon: 75.8573 },
        { name: 'Amritsar', state: 'Punjab', lat: 31.6340, lon: 74.8723 },
        { name: 'Dehradun', state: 'Uttarakhand', lat: 30.3165, lon: 78.0322 },
        { name: 'Bhubaneswar', state: 'Odisha', lat: 20.2961, lon: 85.8245 },
        { name: 'Guwahati', state: 'Assam', lat: 26.1445, lon: 91.7362 },
        { name: 'Ranchi', state: 'Jharkhand', lat: 23.3441, lon: 85.3096 },
        { name: 'Raipur', state: 'Chhattisgarh', lat: 21.2514, lon: 81.6296 },
        { name: 'Greater Noida', state: 'Uttar Pradesh', lat: 28.4745, lon: 77.5040 },
    ];

    function buildLocationQuery(extraParams = '') {
        let q = `location=${encodeURIComponent(currentLocation)}`;
        if (currentLatitude != null && currentLongitude != null) {
            q += `&latitude=${currentLatitude}&longitude=${currentLongitude}`;
        }
        if (currentState) {
            q += `&state=${encodeURIComponent(currentState)}`;
        }
        if (currentLocationAccuracy != null) {
            q += `&accuracy=${currentLocationAccuracy}&accuracy_meters=${currentLocationAccuracy}`;
        }
        // Always pass the active language so all API responses are in the right language
        const lang = (typeof window.getCurrentLang === 'function') ? window.getCurrentLang() : 'hi';
        q += `&language=${encodeURIComponent(lang)}`;
        q += `&_t=${Date.now()}`;
        return extraParams ? `${q}&${extraParams}` : q;
    }

    function updateAccuracyBadge(accuracyMeters) {
        const badge = document.getElementById('locationAccuracyBadge');
        if (!badge) return;
        if (accuracyMeters == null || isNaN(accuracyMeters)) {
            badge.style.display = 'none';
            return;
        }
        const rounded = Math.round(accuracyMeters);
        badge.textContent = `±${rounded}m`;
        badge.className = 'location-accuracy-badge';
        if (rounded <= 15) {
            badge.classList.add('accuracy-good');
            badge.title = 'High-accuracy GPS (building/village level)';
        } else if (rounded <= 100) {
            badge.classList.add('accuracy-medium');
            badge.title = 'GPS accuracy — street level';
        } else {
            badge.title = 'GPS accuracy — approximate';
        }
        badge.style.display = 'inline-block';
    }

    function filterLocalCitySuggestions(query) {
        const q = query.toLowerCase();
        return INDIAN_CITIES.filter(c =>
            c.name.toLowerCase().includes(q) || (c.state && c.state.toLowerCase().includes(q))
        ).slice(0, 8).map(c => ({
            name: c.name,
            subtitle: c.state,
            lat: c.lat,
            lon: c.lon,
            state: c.state,
            type: 'city',
        }));
    }

    // ========================================
    // LOCATION FUNCTIONS
    // ========================================

    function updateLocation(locationName, latitude, longitude, accuracyMeters, stateName) {
        currentLocation = locationName;
        if (latitude != null && longitude != null) {
            currentLatitude = latitude;
            currentLongitude = longitude;
        }
        if (stateName) {
            currentState = stateName;
        }
        if (accuracyMeters !== undefined && accuracyMeters !== null) {
            currentLocationAccuracy = accuracyMeters;
        }
        updateAccuracyBadge(currentLocationAccuracy);

        currentMandi = '';
        const mandiSel = document.getElementById('mandiSelector');
        if (mandiSel) mandiSel.value = '';

        const accLabel = currentLocationAccuracy != null
            ? ` ±${Math.round(currentLocationAccuracy)}m` : '';
        console.log(`📍 Location updated to: ${locationName} (${currentLatitude}, ${currentLongitude}) state=${currentState}${accLabel}`);

        const locationDisplay = document.getElementById('currentLocationDisplay');
        if (locationDisplay) {
            locationDisplay.textContent = stateName && stateName !== locationName
                ? `${locationName}, ${stateName}` : locationName;
        }

        const searchInput = document.getElementById('locationSearchInput');
        if (searchInput) searchInput.value = locationName;

        console.log('🔄 Reloading all services for new location...');
        reloadAllServices();
    }

    function searchLocations(event) {
        clearTimeout(locationSearchTimeout);

        const input = event.target;
        const query = input.value.trim();

        if (query.length < 2) {
            hideLocationSuggestions();
            return;
        }

        locationSearchTimeout = setTimeout(async () => {
            let suggestions = filterLocalCitySuggestions(query);
            try {
                const response = await fetch(
                    apiFetch(`/api/locations/search/?q=${encodeURIComponent(query)}`),
                );
                const data = await response.json();
                const apiResults = (data.results || []).map(r => ({
                    name: r.name,
                    subtitle: [r.village, r.district, r.state].filter(Boolean).join(', '),
                    lat: r.lat,
                    lon: r.lon,
                    state: r.state || '',
                    type: r.type || 'place',
                }));
                if (apiResults.length) {
                    const seen = new Set(apiResults.map(r => `${r.lat}:${r.lon}`));
                    for (const local of suggestions) {
                        const key = `${local.lat}:${local.lon}`;
                        if (!seen.has(key)) {
                            apiResults.push(local);
                            seen.add(key);
                        }
                    }
                    suggestions = apiResults;
                }
            } catch (err) {
                console.error('Location search failed:', err);
            }
            showLocationSuggestions(suggestions);
        }, 300);
    }

    function showLocationSuggestions(suggestions) {
        const container = document.getElementById('locationSuggestions');
        if (!container) return;

        container.innerHTML = '';
        if (!suggestions || suggestions.length === 0) {
            container.style.display = 'none';
            return;
        }

        suggestions.forEach(loc => {
            const lat = loc.lat != null ? Number(loc.lat) : null;
            const lon = loc.lon != null ? Number(loc.lon) : null;
            if (lat == null || lon == null || isNaN(lat) || isNaN(lon)) {
                return;
            }

            const div = document.createElement('div');
            div.className = 'location-suggestion';
            div.setAttribute('role', 'option');

            const nameEl = document.createElement('span');
            nameEl.className = 'suggestion-name';
            nameEl.textContent = `📍 ${loc.name}`;

            const detailEl = document.createElement('span');
            detailEl.className = 'suggestion-details';
            detailEl.textContent = loc.subtitle || loc.state || loc.type || '';

            div.appendChild(nameEl);
            if (detailEl.textContent) div.appendChild(detailEl);

            div.addEventListener('click', () => {
                selectLocation(loc.name, lat, lon, loc.state || '');
            });
            container.appendChild(div);
        });

        container.style.display = container.childElementCount ? 'block' : 'none';
    }

    function hideLocationSuggestions() {
        const container = document.getElementById('locationSuggestions');
        if (container) {
            container.style.display = 'none';
        }
    }

    function selectLocation(locationName, latitude, longitude, stateName) {
        hideLocationSuggestions();
        updateLocation(locationName, latitude, longitude, 500, stateName || '');
    }

    function searchCurrentLocation() {
        applyManualLocation();
    }

    function applyManualLocation() {
        const input = document.getElementById('locationSearchInput');
        if (!input || !input.value.trim()) return;
        const query = input.value.trim();
        hideLocationSuggestions();

        const match = INDIAN_CITIES.find(c => c.name.toLowerCase() === query.toLowerCase())
            || INDIAN_CITIES.find(c => c.name.toLowerCase().includes(query.toLowerCase()));

        if (match) {
            updateLocation(match.name, match.lat, match.lon, 500, match.state);
        } else {
            apiGetJson(`/api/locations/resolve/?location=${encodeURIComponent(query)}`)
                .then(data => {
                    const loc = data.location || {};
                    updateLocation(
                        loc.display_name || query,
                        loc.latitude,
                        loc.longitude,
                        loc.accuracy_meters || 500,
                        loc.state || ''
                    );
                })
                .catch(() => updateLocation(
                    query,
                    currentLatitude,
                    currentLongitude,
                    null,
                    currentState || ''
                ));
        }
    }

    function detectLocation() {
        if (!navigator.geolocation) {
            alert('Geolocation is not supported by your browser');
            return;
        }

        console.log('🌍 Detecting high-accuracy GPS location...');
        const locationDisplay = document.getElementById('currentLocationDisplay');
        if (locationDisplay) locationDisplay.textContent = 'Locating… (GPS)';
        updateAccuracyBadge(null);

        const geoOptions = {
            enableHighAccuracy: true,
            maximumAge: 0,
            timeout: 25000
        };

        let watchId = null;
        let bestPosition = null;
        let gpsFinalized = false;

        const applyPosition = async (position) => {
            if (gpsFinalized) return;
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            const accuracy = position.coords.accuracy;

            if (locationDisplay) {
                locationDisplay.textContent = `Locating… ±${Math.round(accuracy)}m`;
            }
            updateAccuracyBadge(accuracy);

            if (!bestPosition || accuracy < bestPosition.coords.accuracy) {
                bestPosition = position;
            }
            if (accuracy <= 12) {
                if (watchId != null) {
                    navigator.geolocation.clearWatch(watchId);
                    watchId = null;
                }
                await finalizeGpsLocation(lat, lon, accuracy);
            }
        };

        const finalizeGpsLocation = async (lat, lon, accuracy) => {
            if (gpsFinalized) return;
            gpsFinalized = true;
            console.log(`📍 GPS: ${lat}, ${lon} (±${Math.round(accuracy)}m)`);
            try {
                const url = apiFetch(`/api/locations/reverse/?lat=${lat}&lon=${lon}&accuracy=${accuracy}&accuracy_meters=${accuracy}`);
                const response = await fetch(url);
                const data = await response.json();
                const loc = data.location || {};
                const parts = [
                    loc.sublocality,
                    loc.village,
                    loc.locality,
                    loc.display_name,
                    loc.name,
                    loc.city,
                ].filter(Boolean);
                const locationName = parts[0] || 'Your location';
                updateLocation(locationName, lat, lon, accuracy, loc.state || '');
            } catch (error) {
                console.error('❌ Reverse geocode failed:', error);
                updateLocation('Your location', lat, lon, accuracy);
            }
        };

        const onError = (error) => {
            if (watchId != null) {
                navigator.geolocation.clearWatch(watchId);
                watchId = null;
            }
            if (bestPosition) {
                const { latitude, longitude, accuracy } = bestPosition.coords;
                finalizeGpsLocation(latitude, longitude, accuracy);
                return;
            }
            console.error('Geolocation error:', error);
            if (locationDisplay) locationDisplay.textContent = currentLocation;
            alert('Unable to detect location. Allow GPS permission or search your village/city.');
        };

        const finishWatch = () => {
            if (watchId != null) {
                navigator.geolocation.clearWatch(watchId);
                watchId = null;
            }
            if (bestPosition) {
                const { latitude, longitude, accuracy } = bestPosition.coords;
                finalizeGpsLocation(latitude, longitude, accuracy);
            }
        };

        watchId = navigator.geolocation.watchPosition(applyPosition, onError, geoOptions);
        setTimeout(finishWatch, 12000);
        navigator.geolocation.getCurrentPosition(applyPosition, () => {}, geoOptions);
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

        // Reload live data when user opens a service panel
        const loaders = {
            'government-schemes': loadGovernmentSchemes,
            'crop-recommendations': loadCropRecommendations,
            'weather': loadWeatherData,
            'market-prices': function () {
                populateMandiDropdown().then(() => loadMarketPrices());
            },
            'field-advisory': function () { loadFieldAdvisoryWithoutSensor(); },
            'pest-control': function () { /* KrishiRaksha — user triggers detect */ },
            'ai-assistant': function () { /* chat on demand */ },
        };
        const load = loaders[serviceName];
        if (typeof load === 'function') {
            try {
                load();
            } catch (err) {
                console.error('Service load error:', serviceName, err);
            }
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

    function renderMandiOptions(mandis, visibleCount) {
        const sel = document.getElementById('mandiSelector');
        if (!sel) return;
        const slice = mandis.slice(0, visibleCount);
        sel.innerHTML = '<option value="">-- सभी मंडियां (All Mandis) --</option>';
        slice.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.name;
            const parts = [m.name];
            if (m.district) parts.push(m.district);
            const distLabel = m.distance
                || (m.distance_km != null ? `${m.distance_km} km` : '');
            if (distLabel) parts.push(distLabel);
            if (m.live) parts.unshift('● live');
            else if (m.live === false) parts.push('ref');
            opt.textContent = parts.join(' — ');
            if (currentMandi && currentMandi === m.name) opt.selected = true;
            sel.appendChild(opt);
        });
    }

    function loadMoreMandis() {
        mandiDropdownVisibleCount += 100;
        renderMandiOptions(allMandisCache, mandiDropdownVisibleCount);
        const btn = document.getElementById('mandiLoadMoreBtn');
        if (btn && mandiDropdownVisibleCount >= allMandisCache.length) {
            btn.style.display = 'none';
        }
    }

    async function populateMandiDropdown(location) {
        const sel = document.getElementById('mandiSelector');
        const badge = document.getElementById('mandiStatusBadge');
        const loadMoreBtn = document.getElementById('mandiLoadMoreBtn');
        if (!sel) return;

        sel.innerHTML = '<option value="">-- मंडियां लोड हो रही हैं... --</option>';
        if (badge) badge.textContent = '⏳ Live mandi list…';
        if (loadMoreBtn) loadMoreBtn.style.display = 'none';

        try {
            const data = await apiGetJson(`/api/market-prices/mandis/?${buildLocationQuery()}`);
            allMandisCache = data.mandis || [];
            mandiDropdownVisibleCount = 100;

            renderMandiOptions(allMandisCache, mandiDropdownVisibleCount);

            if (loadMoreBtn && allMandisCache.length > mandiDropdownVisibleCount) {
                loadMoreBtn.style.display = 'inline-block';
                loadMoreBtn.textContent =
                    `और मंडियां (+${allMandisCache.length - mandiDropdownVisibleCount})`;
            }

            if (badge) {
                if (!allMandisCache.length) {
                    badge.textContent = '⚠️ Register DATA_GOV_IN_API_KEY in .env for mandi list';
                } else if (data.using_demo_key) {
                    badge.textContent =
                        `🏪 ${allMandisCache.length} mandis (${data.live_count || 0} live) — add DATA_GOV_IN_API_KEY for full coverage`;
                } else {
                    const nearest = allMandisCache[0];
                    const nearHint = nearest && nearest.distance_km != null
                        ? ` · nearest ${nearest.name} (${nearest.distance_km} km)`
                        : '';
                    badge.textContent =
                        `🏪 ${allMandisCache.length} mandis (${data.live_count || 0} live) · ${data.coverage || 'full'}${nearHint}`;
                }
            }
        } catch (err) {
            console.error('Mandi list error:', err);
            sel.innerHTML = '<option value="">-- सभी मंडियां (All Mandis) --</option>';
            if (badge) badge.textContent = '';
        }
    }

    function onMandiSelected(mandiName) {
        currentMandi = mandiName || '';
        const badge = document.getElementById('mandiStatusBadge');
        if (badge) {
            badge.textContent = mandiName
                ? `📍 ${mandiName} — live data fetching…`
                : `🏪 सभी मंडियों का राज्य-स्तरीय भाव`;
        }
        // Clear refresh timer so mandi change triggers a fresh fetch immediately
        if (_mandiRefreshTimer) { clearTimeout(_mandiRefreshTimer); _mandiRefreshTimer = null; }
        loadMarketPrices();
    }

    function hideCropPriceSuggestions() {
        const el = document.getElementById('cropPriceSuggestions');
        if (el) el.style.display = 'none';
    }

    function showCropPriceSuggestions(results) {
        const container = document.getElementById('cropPriceSuggestions');
        if (!container) return;
        if (!results.length) {
            container.style.display = 'none';
            return;
        }
        let html = '';
        results.forEach(c => {
            const id = escapeHtml(c.id || c.name || '');
            const name = escapeHtml(c.search_term || c.name || '');
            const label = escapeHtml(c.label || c.name || '');
            html += `<div class="crop-suggestion" data-crop-id="${id}" data-crop-name="${name}" data-crop-label="${label}">
                <div class="crop-suggestion-name">${escapeHtml(c.label || c.name)}</div>
                <div class="crop-suggestion-details">${escapeHtml(c.category || '')}${c.msp ? ' • MSP ₹' + escapeHtml(c.msp) : ''}</div>
            </div>`;
        });
        container.innerHTML = html;
        container.querySelectorAll('.crop-suggestion').forEach(el => {
            el.addEventListener('click', () => {
                selectCropForMarket(
                    el.getAttribute('data-crop-id'),
                    el.getAttribute('data-crop-name'),
                    el.getAttribute('data-crop-label')
                );
            });
        });
        container.style.display = 'block';
    }

    async function searchCropsForMarket(event) {
        clearTimeout(cropSearchTimeout);
        const query = event.target.value.trim();
        if (query.length < 1) {
            hideCropPriceSuggestions();
            return;
        }
        cropSearchTimeout = setTimeout(async () => {
            try {
                const r = await fetch(apiFetch(`/api/market-prices/crop-search/?q=${encodeURIComponent(query)}`));
                const data = await r.json();
                showCropPriceSuggestions(data.results || []);
            } catch (e) {
                console.error('Crop search failed', e);
            }
        }, 280);
    }

    function selectCropForMarket(id, name, label) {
        currentCropSearch = name || id;
        const input = document.getElementById('cropPriceSearchInput');
        if (input) input.value = label || name;
        const badge = document.getElementById('selectedCropBadge');
        if (badge) badge.textContent = `🔍 ${label || name} — ${currentLocation} के भाव`;
        hideCropPriceSuggestions();
        loadMarketPrices();
    }

    function clearCropPriceSearch() {
        currentCropSearch = '';
        const input = document.getElementById('cropPriceSearchInput');
        if (input) input.value = '';
        const badge = document.getElementById('selectedCropBadge');
        if (badge) badge.textContent = '';
        hideCropPriceSuggestions();
        loadMarketPrices();
    }

    function forceReloadMarketPrices() {
        loadMarketPrices();
    }

    function hideCropSuggestions() {
        const el = document.getElementById('cropSuggestions');
        if (el) el.style.display = 'none';
    }

    function showCropSuggestionsList(results) {
        const container = document.getElementById('cropSuggestions');
        if (!container) return;
        if (!results.length) {
            container.style.display = 'none';
            return;
        }
        let html = '';
        results.forEach((c) => {
            const label = escapeHtml(c.label || c.name || '');
            const name = escapeHtml(c.search_term || c.name || '');
            html += `<div class="crop-suggestion" data-crop-name="${name}" data-crop-label="${label}">
                <div class="crop-suggestion-name">${label}</div>
                <div class="crop-suggestion-details">${escapeHtml(c.category || '')}</div>
            </div>`;
        });
        container.innerHTML = html;
        container.querySelectorAll('.crop-suggestion').forEach((el) => {
            el.addEventListener('click', () => {
                const input = document.getElementById('cropSearchInput');
                const label = el.getAttribute('data-crop-label');
                if (input) input.value = label;
                hideCropSuggestions();
                searchSpecificCrop();
            });
        });
        container.style.display = 'block';
    }

    function showCropSuggestions() {
        const input = document.getElementById('cropSearchInput');
        if (input && input.value.trim().length >= 1) {
            searchCrop({ target: input });
        }
    }

    async function searchCrop(event) {
        clearTimeout(cropSearchTimeout);
        const query = (event.target.value || '').trim();
        if (query.length < 1) {
            hideCropSuggestions();
            return;
        }
        cropSearchTimeout = setTimeout(async () => {
            try {
                const r = await fetch(
                    apiFetch(`/api/market-prices/crop-search/?q=${encodeURIComponent(query)}`),
                );
                const data = await r.json();
                showCropSuggestionsList(data.results || []);
            } catch (e) {
                console.error('Crop recommendation search failed', e);
            }
        }, 280);
    }

    function searchSpecificCrop() {
        const input = document.getElementById('cropSearchInput');
        const query = input ? input.value.trim() : '';
        if (!query) return;
        showService('crop-recommendations');
        loadCropRecommendations();
    }

    function hideKrCropSuggestions() {
        const el = document.getElementById('krCropSuggestions');
        if (el) el.style.display = 'none';
    }

    function showKrCropSuggestions(results) {
        const container = document.getElementById('krCropSuggestions');
        if (!container) return;
        if (!results.length) {
            container.style.display = 'none';
            return;
        }
        let html = '';
        results.forEach(c => {
            const id = (c.id || c.name || '').replace(/'/g, '');
            const label = (c.label || c.name || '').replace(/'/g, '');
            html += `<div class="crop-suggestion" onclick="selectCropForDiagnostics('${id}', '${label}')">
                <div class="crop-suggestion-name">${c.label || c.name}</div>
                <div class="crop-suggestion-details">${c.category || 'crop'}</div>
            </div>`;
        });
        container.innerHTML = html;
        container.style.display = 'block';
    }

    async function searchCropsForDiagnostics(event) {
        clearTimeout(krCropSearchTimeout);
        const query = event.target.value.trim();
        krSelectedCrop = query;
        document.getElementById('krCropValue').value = query;
        if (query.length < 1) {
            hideKrCropSuggestions();
            document.getElementById('krSelectedCropLabel').textContent = '';
            return;
        }
        krCropSearchTimeout = setTimeout(async () => {
            try {
                const r = await fetch(apiFetch(`/api/diagnostics/crop-search/?q=${encodeURIComponent(query)}`));
                const data = await r.json();
                showKrCropSuggestions(data.results || []);
            } catch (e) {
                console.error('Diagnostic crop search failed', e);
            }
        }, 280);
    }

    function selectCropForDiagnostics(id, label) {
        krSelectedCrop = id;
        document.getElementById('krCropValue').value = id;
        const input = document.getElementById('krCropSearchInput');
        if (input) input.value = label;
        document.getElementById('krSelectedCropLabel').textContent = `✓ Selected: ${label}`;
        hideKrCropSuggestions();
    }

    function updateMarketLiveBanner(data) {
        const banner = document.getElementById('marketLiveBanner');
        if (!banner) return;

        const showEstimates = document.getElementById('showMspEstimates')?.checked;
        const isLive        = data.is_live === true && data.status !== 'fallback';
        const isPartial     = data.status === 'partial';
        const isFallback    = data.status === 'fallback' || data._auto_estimates;
        const isUnavailable = data.status === 'unavailable';

        if (isLive) {
            banner.style.display = 'none';
            banner.textContent = '';
            return;
        }

        banner.style.display = 'block';

        if (isPartial) {
            banner.className = 'market-live-banner market-live-banner--partial';
            banner.innerHTML = '🟡 Partial live feed — only live rows shown. Some mandis may have delayed data.';
        } else if (isFallback) {
            banner.className = 'market-live-banner market-live-banner--estimate';
            banner.innerHTML = '📊 MSP seasonal estimates — NOT live mandi trade prices. '
                + '<a href="https://data.gov.in/user/register" target="_blank">Register free key</a> for live data.';
        } else if (isUnavailable) {
            banner.className = 'market-live-banner market-live-banner--warn';
            const reg = data.api_key_registered;
            if (!reg) {
                banner.innerHTML = '🔴 Live mandi data needs DATA_GOV_IN_API_KEY — '
                    + '<a href="https://data.gov.in/user/register" target="_blank" style="color:#856404;font-weight:700;">Register free at data.gov.in</a> '
                    + '(set key in .env → restart server)';
            } else {
                banner.innerHTML = `🔴 ${escapeHtml(data.message || 'Live data temporarily unavailable — try again in a moment.')}`;
            }
        } else {
            banner.className = 'market-live-banner market-live-banner--warn';
            banner.innerHTML = escapeHtml(data.message || 'Market data status unknown');
        }
    }

    // Auto-refresh timer for market prices
    let _mandiRefreshTimer = null;
    let _mandiLastFetchedAt = null;

    async function loadMarketPrices() {
        const container = document.getElementById('pricesData');
        if (!container) return;

        // Clear any existing auto-refresh
        if (_mandiRefreshTimer) { clearTimeout(_mandiRefreshTimer); _mandiRefreshTimer = null; }

        container.innerHTML = `<div class="loading" style="text-align:center;padding:30px;">
            <i class="fas fa-spinner fa-spin fa-2x" style="color:#4a7c59;"></i>
            <p style="margin-top:12px;color:#2d5016;">${(typeof window.t === 'function' ? window.t('loading') : 'Loading...')} मंडी भाव…</p>
        </div>`;

        try {
            const estimatesChecked = document.getElementById('showMspEstimates')?.checked;
            let data;

            // Use mandi-specific endpoint when a mandi is selected (more accurate)
            if (currentMandi && currentMandi.trim()) {
                let mandiPath = `/api/market-prices/mandi-prices/?${buildLocationQuery()}`;
                mandiPath += `&mandi=${encodeURIComponent(currentMandi)}`;
                if (currentCropSearch) mandiPath += `&crop=${encodeURIComponent(currentCropSearch)}`;
                if (estimatesChecked) mandiPath += '&include_estimates=true';
                data = await apiGetJson(mandiPath);
            } else {
                // Generic state-level prices
                let marketPath = `/api/market-prices/?${buildLocationQuery()}`;
                if (currentCropSearch) marketPath += `&crop=${encodeURIComponent(currentCropSearch)}`;
                if (estimatesChecked) marketPath += '&include_estimates=true';
                data = await apiGetJson(marketPath);
            }

            // Auto-fetch estimates if no live rows and estimates not yet shown
            if ((!data.top_crops || data.top_crops.length === 0) &&
                (data.status === 'unavailable' || data.status === 'partial') && !estimatesChecked) {
                const ePath = currentMandi
                    ? `/api/market-prices/mandi-prices/?${buildLocationQuery()}&mandi=${encodeURIComponent(currentMandi)}&include_estimates=true`
                    : `/api/market-prices/?${buildLocationQuery()}&include_estimates=true`;
                const est = await apiGetJson(ePath);
                if (est.top_crops?.length) { data = est; data._auto_estimates = true; }
            }

            _mandiLastFetchedAt = new Date();
            updateMarketLiveBanner(data);
            _renderMarketPrices(data, container);

            // Schedule auto-refresh (live: 3min, estimates: 10min)
            const refreshMs = data.is_live ? 180000 : 600000;
            _mandiRefreshTimer = setTimeout(() => {
                const badge = document.getElementById('mandiStatusBadge');
                if (badge) badge.textContent += ' (refreshing…)';
                loadMarketPrices();
            }, refreshMs);

        } catch (error) {
            container.innerHTML = `<div style="padding:20px;text-align:center;color:#dc3545;">
                <i class="fas fa-exclamation-triangle"></i> बाजार भाव लोड त्रुटि: ${escapeHtml(error.message)}
                <br><small>Backend चालू है? — <code>python manage.py runserver</code></small>
            </div>`;
        }
    }

    function _renderMarketPrices(data, container) {
        const crops = (data.top_crops || data.crops || []).filter(c => {
            if (data.is_live && !document.getElementById('showMspEstimates')?.checked) {
                return c.price_source !== 'msp_seasonal_estimate' && c.price_source !== 'msp_mandi_estimate' && !c.supplemented;
            }
            return true;
        });

        const selectedMandi = data.selected_mandi || data.mandi_filter || currentMandi || data.location || currentLocation;
        const isLive = data.is_live === true && data.status !== 'fallback';
        const isPartial = data.status === 'partial';
        const isEstimatesOnly = data.status === 'fallback' || data._auto_estimates;

        // Live status bar
        const ageText = _mandiLastFetchedAt
            ? `अपडेट: ${_mandiLastFetchedAt.toLocaleTimeString('hi-IN')}`
            : '';
        const liveDot = isLive ? '🟢' : isPartial ? '🟡' : '🔴';
        const liveLabel = isLive
            ? `${liveDot} Live — ${escapeHtml(data.data_source || 'Agmarknet / data.gov.in')}`
            : isEstimatesOnly
            ? `${liveDot} MSP अनुमान — असली मंडी भाव नहीं (DATA_GOV_IN_API_KEY सेट करें)`
            : `${liveDot} ${escapeHtml(data.message || 'Live data unavailable')}`;

        if (!crops.length) {
            const setupMsg = data.api_key_registered === false
                ? `<div style="background:#fff3e0;border-radius:10px;padding:18px;margin-top:10px;">
                    <h6 style="color:#e65100;">📋 Live मंडी भाव कैसे पाएं?</h6>
                    <ol style="color:#555;font-size:0.88rem;line-height:2;">
                        <li><a href="https://data.gov.in/user/register" target="_blank">data.gov.in/user/register</a> पर Free registration करें</li>
                        <li>API Keys section से अपना key copy करें</li>
                        <li><code>.env</code> में <code>DATA_GOV_IN_API_KEY=your_key</code> set करें</li>
                        <li>Server restart करें</li>
                    </ol>
                    <div style="margin-top:10px;">या <button class="btn btn-sm btn-outline-warning" onclick="document.getElementById('showMspEstimates').checked=true;loadMarketPrices();">MSP अनुमान देखें</button></div>
                  </div>`
                : '';
            container.innerHTML = `<div style="padding:20px;text-align:center;">
                <div style="font-size:0.88rem;color:#888;margin-bottom:10px;">${liveLabel}</div>
                <p style="color:#856404;">${escapeHtml(data.message || 'कोई मंडी भाव उपलब्ध नहीं')}</p>
                ${setupMsg}
            </div>`;
            return;
        }

        // Header
        let html = `<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:16px;">
            <div>
                <div style="font-size:0.85rem;font-weight:600;">${liveLabel}</div>
                <div style="font-size:0.75rem;color:#aaa;">${ageText} · ${crops.length} commodities</div>
                ${data.using_demo_key ? '<div style="font-size:0.72rem;color:#f57f17;">⚠️ Demo key (10 rows max) — register your own DATA_GOV_IN_API_KEY</div>' : ''}
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
                <span style="font-size:0.85rem;font-weight:700;color:#2d5016;">🏪 ${escapeHtml(selectedMandi)}</span>
                <button onclick="loadMarketPrices()" style="background:none;border:1px solid #4a7c59;border-radius:20px;padding:3px 10px;font-size:0.75rem;color:#4a7c59;cursor:pointer;" title="Refresh">
                    <i class="fas fa-sync-alt"></i>
                </button>
            </div>
        </div>`;

        // Crop cards grid
        html += `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:14px;">`;

        crops.forEach(crop => {
            const isEst = !crop.is_live || crop.price_source === 'msp_seasonal_estimate' || crop.supplemented;
            const price = crop.modal_price || crop.current_price || 0;
            const msp   = crop.msp || 0;
            const minP  = crop.min_price;
            const maxP  = crop.max_price;
            const profit = typeof crop.profit_vs_msp === 'number' ? crop.profit_vs_msp : null;
            const profitColor = profit !== null ? (profit >= 0 ? '#28a745' : '#dc3545') : '#888';
            const indicator   = crop.profit_indicator || (profit !== null ? (profit >= 0 ? '📈' : '📉') : '–');
            const arrivalDate = crop.date ? `<div style="font-size:0.7rem;color:#bbb;margin-top:4px;">📅 ${escapeHtml(crop.date)}</div>` : '';
            const mandiLabel  = crop.mandi_name && crop.mandi_name !== selectedMandi
                ? `<div style="font-size:0.7rem;color:#999;margin-top:3px;">🏪 ${escapeHtml(crop.mandi_name)}</div>`
                : '';
            const cropLocal   = crop.crop_name_hindi || crop.crop_name || '';

            html += `<div style="background:white;border-radius:13px;padding:16px;box-shadow:0 3px 12px rgba(0,0,0,0.07);
                        border-top:3px solid ${isEst ? '#ffc107' : '#28a745'};position:relative;overflow:hidden;">
                <!-- Live/Estimate badge -->
                <div style="position:absolute;top:8px;right:8px;font-size:0.65rem;font-weight:700;padding:2px 6px;border-radius:8px;
                    background:${isEst ? '#fff3cd' : '#d4edda'};color:${isEst ? '#856404' : '#155724'};">
                    ${isEst ? 'MSP est.' : '● Live'}
                </div>

                <div style="font-weight:700;color:#2d5016;font-size:0.95rem;margin-bottom:10px;padding-right:55px;">
                    ${escapeHtml(cropLocal)} <span style="font-size:1rem;">${indicator}</span>
                </div>

                <div style="text-align:center;background:linear-gradient(135deg,#f0fff0,#e8f5e8);border-radius:10px;padding:10px;margin-bottom:10px;">
                    <div style="font-size:1.8rem;font-weight:800;color:#2d5016;">₹${price.toLocaleString('hi-IN')}</div>
                    <div style="color:#888;font-size:0.72rem;">Modal Price / क्विंटल</div>
                    ${(minP && maxP) ? `<div style="color:#aaa;font-size:0.7rem;margin-top:2px;">₹${minP.toLocaleString()} – ₹${maxP.toLocaleString()}</div>` : ''}
                </div>

                <div style="font-size:0.82rem;line-height:1.9;">
                    <div style="display:flex;justify-content:space-between;">
                        <span style="color:#666;">MSP 2024-25</span>
                        <span style="font-weight:600;color:#555;">₹${msp > 0 ? msp.toLocaleString('hi-IN') : '—'}</span>
                    </div>
                    ${profit !== null ? `<div style="display:flex;justify-content:space-between;">
                        <span style="color:#666;">MSP से ${profit >= 0 ? 'लाभ' : 'नुकसान'}</span>
                        <span style="font-weight:700;color:${profitColor};">${profit >= 0 ? '+' : ''}${profit}%</span>
                    </div>` : ''}
                    ${crop.variety ? `<div style="display:flex;justify-content:space-between;"><span style="color:#aaa;">Variety</span><span style="color:#666;">${escapeHtml(crop.variety)}</span></div>` : ''}
                </div>

                ${mandiLabel}
                ${arrivalDate}
            </div>`;
        });

        html += '</div>';

        // Footer note for estimates
        if (isEstimatesOnly || data._auto_estimates) {
            html += `<div style="margin-top:14px;background:#fff8e1;border-radius:8px;padding:10px 14px;font-size:0.78rem;color:#856404;">
                ℹ️ ये MSP-आधारित अनुमान हैं, असली मंडी भाव नहीं।
                Live prices के लिए: <a href="https://agmarknet.gov.in" target="_blank">agmarknet.gov.in</a> देखें
                या <code>DATA_GOV_IN_API_KEY</code> .env में सेट करें।
            </div>`;
        }

        container.innerHTML = html;
    }

    function selectMandi(mandiName) {
        currentMandi = mandiName || '';
        const sel = document.getElementById('mandiSelector');
        if (sel) sel.value = mandiName || '';
        onMandiSelected(mandiName);
    }

    async function loadWeatherData() {
        try {
            const container = document.getElementById('weatherData');
            if (!container) return;

            container.innerHTML = `<div class="loading">${(typeof window.t === 'function' ? window.t('loading') : 'Loading...')}</div>`;

            const data = await apiGetJson(`/api/weather/?${buildLocationQuery()}`);
            window.lastWeatherData = data;

            const weather = data.current_weather || data.current || {};
            const forecast = data.forecast_7_days || data.forecast_7day || [];
            const alerts  = data.farming_alerts || [];
            const locLabel = data.location || currentLocation;
            const lang = (typeof window.getCurrentLang === 'function') ? window.getCurrentLang() : 'hi';

            const liveBadge = data.is_live === false
                ? `<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:8px 14px;margin-bottom:12px;font-size:0.85rem;color:#856404;">⚠️ ${escapeHtml(data.data_source || 'Estimated — all APIs unavailable')}</div>`
                : `<div style="background:#d4edda;border:1px solid #c3e6cb;border-radius:8px;padding:8px 14px;margin-bottom:12px;font-size:0.85rem;color:#155724;">✅ Live: ${escapeHtml(data.data_source || 'Open-Meteo (Real-time, Free, 1km)')} · Real-time</div>`;

            if (weather && weather.temperature != null) {
                let html = liveBadge;

                // Farming alerts banner
                if (alerts.length) {
                    html += `<div style="background:#fff3e0;border-left:4px solid #ff6f00;border-radius:8px;padding:12px 16px;margin-bottom:14px;">
                        <strong style="color:#e65100;">⚠️ कृषि चेतावनी</strong>
                        ${alerts.map(a => `<div style="font-size:0.88rem;color:#555;margin-top:4px;">${escapeHtml(a)}</div>`).join('')}
                    </div>`;
                }

                // Current weather card
                html += `<div style="background:white;border-radius:15px;padding:25px;box-shadow:0 4px 15px rgba(0,0,0,0.08);margin-bottom:18px;">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:15px;">
                        <div>
                            <h4 style="color:#2d5016;margin-bottom:4px;">🌤️ ${escapeHtml(locLabel)}</h4>
                            <div style="color:#666;font-size:0.88rem;">${escapeHtml(weather.condition_local || weather.condition || 'Partly Cloudy')}</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:3.5rem;font-weight:800;color:#2d5016;line-height:1;">${weather.temperature != null ? weather.temperature + '°C' : '--'}</div>
                            <div style="color:#888;font-size:0.85rem;">feels ${weather.feels_like != null ? weather.feels_like + '°C' : '--'}</div>
                        </div>
                    </div>
                    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-top:18px;">
                        <div style="background:#f0f8ff;border-radius:10px;padding:10px;text-align:center;">
                            <div style="font-size:1.3rem;font-weight:700;color:#0277bd;">${weather.humidity != null ? weather.humidity + '%' : '--'}</div>
                            <div style="font-size:0.78rem;color:#666;">${(typeof window.t === 'function') ? window.t('weather_humidity') : 'Humidity'}</div>
                        </div>
                        <div style="background:#f0fff0;border-radius:10px;padding:10px;text-align:center;">
                            <div style="font-size:1.3rem;font-weight:700;color:#2e7d32;">${weather.wind_speed != null ? Math.round(weather.wind_speed) + ' km/h' : '--'}</div>
                            <div style="font-size:0.78rem;color:#666;">${(typeof window.t === 'function') ? window.t('weather_wind') : 'Wind'}</div>
                        </div>
                        <div style="background:#fff8e1;border-radius:10px;padding:10px;text-align:center;">
                            <div style="font-size:1.3rem;font-weight:700;color:#f57f17;">${weather.rainfall_mm != null ? weather.rainfall_mm + ' mm' : '0 mm'}</div>
                            <div style="font-size:0.78rem;color:#666;">${(typeof window.t === 'function') ? window.t('weather_rain') : 'Rain'}</div>
                        </div>
                        <div style="background:#fce4ec;border-radius:10px;padding:10px;text-align:center;">
                            <div style="font-size:1.3rem;font-weight:700;color:#c2185b;">${weather.uv_index != null ? weather.uv_index : '--'}</div>
                            <div style="font-size:0.78rem;color:#666;">UV Index</div>
                        </div>
                        ${weather.et0_mm != null ? `<div style="background:#f3e5f5;border-radius:10px;padding:10px;text-align:center;">
                            <div style="font-size:1.3rem;font-weight:700;color:#7b1fa2;">${weather.et0_mm.toFixed(1)} mm</div>
                            <div style="font-size:0.78rem;color:#666;">ET₀/day</div>
                        </div>` : ''}
                    </div>
                    ${data.farming_advice ? `<div style="margin-top:15px;background:#e8f5e9;border-radius:8px;padding:10px 14px;font-size:0.88rem;color:#2d5016;">🌾 ${escapeHtml(data.farming_advice)}</div>` : ''}
                </div>`;

                // 16-day forecast
                if (forecast && forecast.length > 0) {
                    html += `<div style="background:white;border-radius:15px;padding:25px;box-shadow:0 4px 15px rgba(0,0,0,0.08);">
                        <h5 style="color:#2d5016;margin-bottom:15px;">📅 ${forecast.length}-दिन पूर्वानुमान <span style="font-size:0.78rem;color:#888;font-weight:400;">(Open-Meteo, real-time)</span></h5>
                        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:12px;">`;

                    forecast.slice(0, 16).forEach(day => {
                        const rain = day.rainfall_mm ?? 0;
                        const maxT = day.max_temp;
                        const minT = day.min_temp;
                        const needsIrr = day.irrigation_needed;
                        const wbal = day.water_balance_mm;
                        const rainColor = rain > 20 ? '#0277bd' : rain > 5 ? '#29b6f6' : '#bdbdbd';
                        html += `<div style="background:#f8f9fa;border-radius:10px;padding:12px;text-align:center;border-top:3px solid ${rain > 20 ? '#29b6f6' : '#4a7c59'};">
                            <div style="font-weight:700;color:#2d5016;font-size:0.82rem;">${escapeHtml(day.date || '')}</div>
                            <div style="font-size:1.4rem;font-weight:800;color:#2d5016;margin:6px 0;">${maxT != null ? Math.round(maxT) + '°' : '--'}</div>
                            <div style="font-size:0.78rem;color:#888;">${minT != null ? Math.round(minT) + '°' : ''}</div>
                            <div style="font-size:0.82rem;color:${rainColor};margin-top:4px;">🌧 ${rain}mm</div>
                            ${needsIrr ? `<div style="font-size:0.7rem;color:#0277bd;margin-top:3px;">💧 Irrigate</div>` : ''}
                            ${day.farming_note ? `<div style="font-size:0.68rem;color:#555;margin-top:4px;line-height:1.2;">${escapeHtml(day.farming_note.substring(0,35))}</div>` : ''}
                        </div>`;
                    });

                    html += '</div></div>';
                }

                container.innerHTML = html;
            } else {
                container.innerHTML = `${liveBadge}<div style="padding:20px;text-align:center;color:#888;">${data.message || 'मौसम डेटा उपलब्ध नहीं — Backend चालू करें'}</div>`;
            }
        } catch (error) {
            const container = document.getElementById('weatherData');
            if (container) container.innerHTML = `<div style="padding:20px;text-align:center;color:#dc3545;">मौसम लोड त्रुटि: ${escapeHtml(error.message)}</div>`;
        }
    }

    async function loadGovernmentSchemes() {
        const container = document.getElementById('schemesData');
        if (!container) return;

        try {
            container.innerHTML = `<div class="loading">${(typeof window.t === 'function' ? window.t('loading') : 'Loading...')}</div>`;

            const data = await apiGetJson(`/api/schemes/?${buildLocationQuery()}`);
            console.log('Schemes data:', data);

            const schemes = data.schemes || [];

            if (schemes && schemes.length > 0) {
                const schemeBanner = data.is_live
                    ? ''
                    : `<div style="background:#e8f4fd;border:1px solid #b8daff;border-radius:8px;padding:10px 14px;margin-bottom:16px;font-size:0.88rem;color:#004085;">📋 Official scheme catalog (MOAFW/DAC&FW reference) — enrollment status is on respective portals, not live API.</div>`;
                let html = schemeBanner + '<div style="display: grid; gap: 20px;">';

                schemes.forEach(scheme => {
                    const officialUrl = escapeHtml(scheme.official_website || scheme.website || scheme.apply_url || '#');
                    const benefitText = escapeHtml(scheme.benefits_hindi || scheme.benefit_hindi || scheme.benefit || 'विवरण उपलब्ध नहीं');
                    const eligibilityText = escapeHtml(scheme.eligibility_hindi || scheme.eligibility || 'सभी किसान');
                    const descText = escapeHtml(scheme.description_hindi || scheme.description || '');
                    const schemeTitle = escapeHtml(scheme.name_hindi || scheme.name || '');

                    html += `
                    <div style="background: white; border-radius: 15px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-left: 5px solid #4a7c59; cursor: pointer; transition: transform 0.3s;"
                         onclick="window.open('${officialUrl}', '_blank')"
                         onmouseover="this.style.transform='translateY(-5px)'; this.style.boxShadow='0 8px 25px rgba(0,0,0,0.15)'"
                         onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(0,0,0,0.1)'">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <h5 style="color: #2d5016; margin-bottom: 15px;">📋 ${schemeTitle}</h5>
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
                container.innerHTML = '<div style="padding: 20px; text-align: center;">योजनाएं उपलब्ध नहीं हैं (No schemes data)</div>';
            }
        } catch (error) {
            console.error('Schemes error:', error);
            const hint = error.message.includes('Failed to fetch')
                ? '<br><small>Backend चालू करें: <code>python manage.py runserver</code> (port 8000) और frontend: <code>npm run dev</code></small>'
                : '';
            container.innerHTML = `<div style="padding: 20px; text-align: center; color: #dc3545;">
                <strong>योजनाएं लोड करने में त्रुटि</strong><br>
                <small>${escapeHtml(error.message)}</small>${hint}
            </div>`;
        }
    }

    // =====================================================
    // FIELD-LEVEL ADVISORY (IoT sensor + Open-Meteo soil)
    // =====================================================

    async function loadFieldAdvisory(withoutSensor = false) {
        const container = document.getElementById('fieldAdvisoryResults');
        if (!container) return;
        const lang = (typeof window.getCurrentLang === 'function') ? window.getCurrentLang() : 'hi';
        container.innerHTML = `<div class="loading text-center py-5">
            <i class="fas fa-spinner fa-spin fa-2x text-success"></i>
            <p class="mt-3" style="color:#2d5016;">🔬 Open-Meteo + Soil Health Card + Sensor विश्लेषण…</p>
        </div>`;

        try {
            const body = {
                latitude: currentLatitude,
                longitude: currentLongitude,
                location: currentLocation,
                state: currentState || '',
                language: lang,
                irrigation_type: document.getElementById('fa_irrigation')?.value || 'unknown',
                previous_crop: (document.getElementById('fa_prev_crop')?.value || '').trim(),
            };

            if (!withoutSensor) {
                const fieldMap = {
                    fa_n: 'nitrogen_kg_ha', fa_p: 'phosphorus_kg_ha', fa_k: 'potassium_kg_ha',
                    fa_ph: 'ph', fa_ec: 'ec_ds_m', fa_moisture: 'moisture_pct',
                    fa_soil_temp: 'soil_temp_c', fa_oc: 'organic_carbon',
                };
                const sensors = {};
                Object.entries(fieldMap).forEach(([id, key]) => {
                    const v = parseFloat(document.getElementById(id)?.value);
                    if (!isNaN(v)) sensors[key] = v;
                });
                if (Object.keys(sensors).length > 0) body.sensors = sensors;
            }

            const resp = await fetch(apiFetch('/api/field-advisory/recommend/'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.message || `HTTP ${resp.status}`);

            const soil    = data.soil_profile || {};
            const status  = soil.soil_status || {};
            const recs    = data.recommendations || [];
            const gaps    = data.input_gaps || [];
            const weather = data.weather || {};
            const alerts  = weather.farming_alerts || [];
            const irrigSched = weather.irrigation_schedule || [];

            const badge = (label, val) => {
                const c = {'Low':'#dc3545','Very Low':'#dc3545','Medium':'#ffc107','High':'#28a745',
                    'Optimal':'#28a745','Safe':'#28a745','Acidic':'#fd7e14','Alkaline':'#fd7e14',
                    'Highly Alkaline':'#dc3545','Waterlogged':'#dc3545','Very Dry':'#dc3545','Dry':'#fd7e14'}[val] || '#6c757d';
                return `<span style="background:${c}18;color:${c};border:1px solid ${c}40;padding:3px 9px;border-radius:12px;font-size:0.75rem;font-weight:600;">${label}: ${val}</span>`;
            };
            const sBar = (s) => `<div style="height:7px;background:#f0f0f0;border-radius:4px;margin:5px 0;overflow:hidden;"><div style="width:${s}%;height:100%;background:${s>=80?'#28a745':s>=60?'#ffc107':'#dc3545'};border-radius:4px;"></div></div>`;

            let html = '';

            // Summary
            if (data.summary) {
                html += `<div style="background:linear-gradient(135deg,#1b5e20,#2e7d32);color:white;border-radius:15px;padding:20px;margin-bottom:18px;">
                    <div style="font-size:1rem;line-height:1.7;">${escapeHtml(data.summary)}</div>
                    <div style="margin-top:10px;opacity:0.75;font-size:0.78rem;">📡 ${(data.data_sources||[]).map(s => escapeHtml(s)).join(' · ')}</div>
                    <div style="margin-top:4px;opacity:0.7;font-size:0.75rem;">Grid: ${escapeHtml(data.grid_resolution||'1km')} · Analysis: field-level</div>
                </div>`;
            }

            // Soil status
            if (Object.keys(status).length) {
                html += `<div style="background:white;border-radius:12px;padding:18px;margin-bottom:16px;box-shadow:0 2px 10px rgba(0,0,0,0.06);">
                    <h6 style="color:#2d5016;margin-bottom:12px;">🧪 मिट्टी की स्थिति</h6>
                    <div style="display:flex;flex-wrap:wrap;gap:7px;margin-bottom:12px;">
                        ${Object.entries(status).map(([k,v]) => badge(k.replace(/_/g,' ').toUpperCase(), v)).join('')}
                    </div>
                    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px;">
                        ${soil.nitrogen_kg_ha!=null ? `<div style="text-align:center;background:#e8f5e9;border-radius:8px;padding:8px;"><div style="font-size:1.2rem;font-weight:800;color:#2d5016;">${soil.nitrogen_kg_ha}</div><div style="font-size:0.72rem;color:#666;">N kg/ha</div></div>` : ''}
                        ${soil.phosphorus_kg_ha!=null ? `<div style="text-align:center;background:#fff3e0;border-radius:8px;padding:8px;"><div style="font-size:1.2rem;font-weight:800;color:#e65100;">${soil.phosphorus_kg_ha}</div><div style="font-size:0.72rem;color:#666;">P kg/ha</div></div>` : ''}
                        ${soil.potassium_kg_ha!=null ? `<div style="text-align:center;background:#e3f2fd;border-radius:8px;padding:8px;"><div style="font-size:1.2rem;font-weight:800;color:#1565c0;">${soil.potassium_kg_ha}</div><div style="font-size:0.72rem;color:#666;">K kg/ha</div></div>` : ''}
                        ${soil.ph!=null ? `<div style="text-align:center;background:#f3e5f5;border-radius:8px;padding:8px;"><div style="font-size:1.2rem;font-weight:800;color:#6a1b9a;">${soil.ph}</div><div style="font-size:0.72rem;color:#666;">pH</div></div>` : ''}
                        ${soil.moisture_pct!=null ? `<div style="text-align:center;background:#e1f5fe;border-radius:8px;padding:8px;"><div style="font-size:1.2rem;font-weight:800;color:#0277bd;">${soil.moisture_pct}%</div><div style="font-size:0.72rem;color:#666;">Moisture</div></div>` : ''}
                        ${soil.organic_carbon!=null ? `<div style="text-align:center;background:#f1f8e9;border-radius:8px;padding:8px;"><div style="font-size:1.2rem;font-weight:800;color:#558b2f;">${soil.organic_carbon}%</div><div style="font-size:0.72rem;color:#666;">OC %</div></div>` : ''}
                    </div>
                    ${(soil.moisture_layers?.root_3_9cm_pct != null) ? `
                    <div style="margin-top:10px;padding:8px;background:#f0f8ff;border-radius:8px;font-size:0.78rem;color:#444;">
                        <strong>🛰️ Open-Meteo Satellite Soil Layers:</strong>
                        Surface ${soil.moisture_layers.surface_0_1cm_pct??'--'}% ·
                        Root zone ${soil.moisture_layers.root_3_9cm_pct??'--'}% ·
                        Subsoil ${soil.moisture_layers.subsoil_9_27cm_pct??'--'}% ·
                        Deep ${soil.moisture_layers.deep_27_81cm_pct??'--'}%
                    </div>` : ''}
                </div>`;
            }

            // Weather alerts
            if (alerts.length || weather.planting_window) {
                html += `<div style="background:#fff8e1;border-left:4px solid #ff8f00;border-radius:10px;padding:14px 18px;margin-bottom:16px;">
                    <h6 style="color:#e65100;margin-bottom:8px;">🌤️ मौसम विश्लेषण (16-day Open-Meteo)</h6>
                    ${alerts.map(a => `<div style="font-size:0.88rem;margin:3px 0;">${escapeHtml(a.message||a)}</div>`).join('')}
                    ${weather.planting_window ? `<div style="margin-top:6px;font-size:0.85rem;color:#2d5016;font-weight:600;">🌱 बुवाई विंडो: ${escapeHtml(weather.planting_window)}</div>` : ''}
                    <div style="margin-top:6px;font-size:0.78rem;color:#888;">🌧 7-day rain: ${weather.rain_7d_mm??'--'}mm · Max temp: ${weather.avg_max_temp_7d??'--'}°C · ET₀: ${weather.total_et0_7d_mm??'--'}mm</div>
                </div>`;
            }

            // Irrigation schedule
            if (irrigSched.length) {
                html += `<div style="background:white;border-radius:12px;padding:16px;margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
                    <h6 style="color:#0277bd;margin-bottom:10px;">💧 सिंचाई अनुसूची (ET₀ आधारित)</h6>
                    <div style="overflow-x:auto;"><table style="width:100%;border-collapse:collapse;font-size:0.8rem;">
                    <thead><tr style="background:#e3f2fd;">
                        <th style="padding:6px 10px;text-align:left;">तारीख</th>
                        <th style="padding:6px;text-align:center;">पानी (mm)</th>
                        <th style="padding:6px;text-align:left;">सही समय</th>
                        <th style="padding:6px;text-align:left;color:#666;">ET₀ vs Rain</th>
                    </tr></thead><tbody>
                    ${irrigSched.map(s => `<tr style="border-bottom:1px solid #f0f0f0;">
                        <td style="padding:6px 10px;font-weight:600;">${escapeHtml(s.date)}</td>
                        <td style="padding:6px;text-align:center;font-weight:700;color:#0277bd;">${s.irrigation_mm}</td>
                        <td style="padding:6px;color:#2d5016;font-size:0.75rem;">${escapeHtml(s.best_time)}</td>
                        <td style="padding:6px;color:#888;font-size:0.72rem;">${escapeHtml(s.reason)}</td>
                    </tr>`).join('')}
                    </tbody></table></div>
                </div>`;
            }

            // Crop recommendations
            if (recs.length) {
                html += `<h5 style="color:#2d5016;margin-bottom:14px;">🌾 फसल सुझाव — ${recs.length} crops scored</h5>
                <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:18px;margin-bottom:22px;">`;
                recs.slice(0, 6).forEach((crop, i) => {
                    const sc = crop.suitability_score;
                    const sc_color = sc >= 80 ? '#28a745' : sc >= 60 ? '#ffc107' : '#dc3545';
                    const npk = crop.npk_match || {};
                    const npkBadges = Object.entries(npk).slice(0,4).map(([k,v]) => {
                        const icon = ['Sufficient','Adequate','Safe','Optimal'].includes(v.status) ? '✅' : v.status?.includes('Low') || v.status?.includes('Critical') ? '⚠️' : v.status === 'Very Low' || v.status === 'Toxic' ? '❌' : '●';
                        return `<span style="font-size:0.72rem;margin-right:6px;">${icon} ${k}${v.value!=null ? ': '+v.value : ''}</span>`;
                    }).join('');
                    html += `<div style="background:white;border-radius:14px;padding:18px;box-shadow:0 4px 12px rgba(0,0,0,0.08);border-top:4px solid ${sc_color};">
                        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">
                            <div>
                                <div style="font-size:1.05rem;font-weight:700;color:#2d5016;">${i+1}. ${escapeHtml(crop.crop_name_hindi||crop.crop_name)}</div>
                                <div style="font-size:0.78rem;color:#888;">${escapeHtml(crop.crop_name)} · ${escapeHtml(crop.category)}</div>
                            </div>
                            <div style="font-size:1.3rem;font-weight:800;color:${sc_color};">${sc}%</div>
                        </div>
                        ${sBar(sc)}
                        <div style="display:flex;flex-wrap:wrap;gap:2px;margin:6px 0 10px;">${npkBadges}</div>
                        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;font-size:0.78rem;margin-bottom:8px;">
                            <div style="background:#e8f5e9;border-radius:6px;padding:5px;text-align:center;"><div style="font-weight:700;color:#28a745;">₹${(crop.profit_per_hectare||0).toLocaleString()}</div><div style="color:#888;font-size:0.68rem;">लाभ/हे.</div></div>
                            <div style="background:#e3f2fd;border-radius:6px;padding:5px;text-align:center;"><div style="font-weight:700;color:#1565c0;">${crop.yield_per_hectare||0}q</div><div style="color:#888;font-size:0.68rem;">उत्पादन</div></div>
                            <div style="background:#fff8e1;border-radius:6px;padding:5px;text-align:center;"><div style="font-weight:700;color:#f57f17;">${crop.msp_per_quintal?'₹'+crop.msp_per_quintal:'No MSP'}</div><div style="color:#888;font-size:0.68rem;">MSP/q</div></div>
                        </div>
                        ${(crop.input_adjustments||[]).length ? `<div style="background:#fff3cd;border-radius:6px;padding:6px 8px;font-size:0.75rem;margin-bottom:6px;">${crop.input_adjustments.slice(0,2).map(a=>'⚠️ '+escapeHtml(a)).join('<br>')}</div>` : ''}
                        <div style="font-size:0.72rem;color:#aaa;">${escapeHtml((crop.scoring_reasons||[]).slice(0,2).join(' · '))}</div>
                    </div>`;
                });
                html += '</div>';
            }

            // Input gaps / fertiliser plan
            if (gaps.length) {
                html += `<div style="background:white;border-radius:12px;padding:18px;margin-bottom:18px;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
                    <h6 style="color:#2d5016;margin-bottom:12px;">📋 खाद/उर्वरक योजना (ICAR Based)</h6>`;
                gaps.forEach(g => {
                    html += `<div style="margin-bottom:14px;border-bottom:1px solid #f0f0f0;padding-bottom:14px;">
                        <strong style="color:#2d5016;">🌾 ${escapeHtml(g.crop)}</strong>
                        <div style="overflow-x:auto;margin-top:8px;"><table style="width:100%;border-collapse:collapse;font-size:0.78rem;">
                        <thead><tr style="background:#e8f5e9;">
                            <th style="padding:5px 8px;text-align:left;">पोषक</th>
                            <th style="padding:5px;text-align:center;">वर्तमान</th>
                            <th style="padding:5px;text-align:center;">न्यूनतम</th>
                            <th style="padding:5px;text-align:center;color:#dc3545;">कमी</th>
                            <th style="padding:5px;text-align:left;">उपाय</th>
                            <th style="padding:5px;text-align:left;color:#888;">समय</th>
                        </tr></thead><tbody>
                        ${(g.amendments||[]).map(a=>`<tr style="border-bottom:1px solid #f5f5f5;">
                            <td style="padding:5px 8px;font-weight:600;color:#2d5016;">${escapeHtml(a.nutrient||'')}</td>
                            <td style="padding:5px;text-align:center;">${a.current_kg_ha??a.current_pct??'-'}</td>
                            <td style="padding:5px;text-align:center;">${a.required_min_kg_ha??a.target_pct??'-'}</td>
                            <td style="padding:5px;text-align:center;color:#dc3545;font-weight:700;">${a.deficit_kg_ha??'-'}</td>
                            <td style="padding:5px;color:#1565c0;font-size:0.72rem;">${escapeHtml(a.amendment||'')}</td>
                            <td style="padding:5px;color:#888;font-size:0.68rem;">${escapeHtml(a.timing||'')}</td>
                        </tr>`).join('')}
                        </tbody></table></div>
                    </div>`;
                });
                html += '</div>';
            }

            // Footer
            html += `<div style="background:#f8f9fa;border-radius:8px;padding:10px 14px;font-size:0.75rem;color:#888;text-align:center;">
                📡 Sources: ${(data.data_sources||[]).join(' · ')} · Grid: ${data.grid_resolution||'1km'} · <span style="color:#28a745;">✅ Real-time</span>
            </div>`;

            container.innerHTML = html;

        } catch (err) {
            const container = document.getElementById('fieldAdvisoryResults');
            if (container) container.innerHTML = `<div style="background:#ffebee;border-radius:10px;padding:20px;color:#c62828;text-align:center;">❌ ${escapeHtml(err.message)}<br><small>Backend: python manage.py runserver</small></div>`;
        }
    }

    function loadFieldAdvisoryWithoutSensor() {
        ['fa_n','fa_p','fa_k','fa_ph','fa_ec','fa_moisture','fa_soil_temp','fa_oc'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        loadFieldAdvisory(true);
    }

    function fillPreset(type) {
        const presets = {
            fertile:   { fa_n: 180, fa_p: 28, fa_k: 200, fa_ph: 6.8, fa_ec: 0.3, fa_moisture: 45, fa_soil_temp: 24, fa_oc: 0.85 },
            deficient: { fa_n: 80,  fa_p: 8,  fa_k: 90,  fa_ph: 6.2, fa_ec: 0.4, fa_moisture: 28, fa_soil_temp: 26, fa_oc: 0.35 },
            saline:    { fa_n: 120, fa_p: 15, fa_k: 130, fa_ph: 8.2, fa_ec: 5.5, fa_moisture: 35, fa_soil_temp: 28, fa_oc: 0.4  },
            acidic:    { fa_n: 110, fa_p: 12, fa_k: 110, fa_ph: 4.8, fa_ec: 0.3, fa_moisture: 40, fa_soil_temp: 22, fa_oc: 0.6  },
        };
        const vals = presets[type] || {};
        Object.entries(vals).forEach(([id, val]) => {
            const el = document.getElementById(id);
            if (el) el.value = val;
        });
    }

    async function checkBackendHealth() {
        try {
            const r = await fetch(apiFetch('/api/health/'), { method: 'GET' });
            return r.ok;
        } catch (e) {
            return false;
        }
    }

    async function loadCropRecommendations() {
        try {
            const container = document.getElementById('cropsData');
            if (!container) return;
            const lang = (typeof window.getCurrentLang === 'function') ? window.getCurrentLang() : 'hi';

            container.innerHTML = `<div class="loading">${(typeof window.t === 'function' ? window.t('loading') : 'Loading...')}</div>`;

            const data = await apiGetJson(`/api/advisories/?${buildLocationQuery()}`);
            const recommendations = data.recommendations || data.top_4_recommendations || [];

            const getCategoryIcon = (cat) => ({'Cereal':'🌾','Pulse':'🫘','Oilseed':'🌻','Vegetable':'🥦','Fruit':'🍎','Spice':'🌶️','Cash':'💰','Millet':'🌿','Fiber':'🧵','Plantation':'🌴','Medicinal':'🌱'}[cat] || '🌱');
            const scoreColor  = (s) => s >= 85 ? '#28a745' : s >= 65 ? '#ffc107' : '#dc3545';
            const scoreBar    = (s) => `<div style="height:8px;background:#eee;border-radius:4px;overflow:hidden;margin:6px 0;"><div style="width:${s}%;height:100%;background:${scoreColor(s)};border-radius:4px;transition:width 1s;"></div></div>`;
            const waterColor  = (w) => ({'high':'#0277bd','very high':'#0277bd','moderate':'#2e7d32','low':'#ff8f00'}[String(w).toLowerCase()] || '#2e7d32');

            if (recommendations.length > 0) {
                // Header banner
                const liveMkt = data.market_is_live;
                const agro    = data.agro_zone || data.soil_type || '';
                let html = `<div style="background:linear-gradient(135deg,#2d5016,#4a7c59);color:white;border-radius:15px;padding:20px 25px;margin-bottom:22px;">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;">
                        <div>
                            <h4 style="color:white;margin:0 0 4px;">${escapeHtml(data.season || '')} — ${escapeHtml(data.region || currentLocation)}</h4>
                            <div style="opacity:0.88;font-size:0.85rem;">${escapeHtml(agro ? 'Zone: ' + agro : '')}</div>
                        </div>
                        <div style="display:flex;gap:8px;flex-wrap:wrap;">
                            <span style="background:rgba(255,255,255,0.15);border-radius:20px;padding:4px 12px;font-size:0.78rem;">🌤️ Live Open-Meteo</span>
                            <span style="background:${liveMkt ? 'rgba(40,167,69,0.3)' : 'rgba(255,193,7,0.3)'};border-radius:20px;padding:4px 12px;font-size:0.78rem;">
                                ${liveMkt ? '✅ Live Mandi' : '⚠️ Mandi: set DATA_GOV_IN_API_KEY'}
                            </span>
                        </div>
                    </div>
                    ${(data.factors_analyzed||[]).length ? `<div style="margin-top:10px;opacity:0.8;font-size:0.78rem;">${data.factors_analyzed.slice(0,5).map(f => '• ' + f).join('  ')}</div>` : ''}
                </div>`;

                // Weather snapshot if available
                const ws = data.weather_snapshot;
                if (ws && ws.temperature != null) {
                    html += `<div style="background:white;border-radius:10px;padding:12px 18px;margin-bottom:16px;display:flex;gap:20px;flex-wrap:wrap;align-items:center;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
                        <span style="font-size:0.85rem;color:#555;">🌡️ <b>${ws.temperature}°C</b></span>
                        <span style="font-size:0.85rem;color:#555;">💧 <b>${ws.humidity}%</b></span>
                        <span style="font-size:0.85rem;color:#555;">💨 <b>${ws.wind_speed} km/h</b></span>
                        <span style="font-size:0.85rem;color:#555;">${escapeHtml(ws.condition_local || ws.condition || '')}</span>
                        <span style="font-size:0.78rem;color:#888;margin-left:auto;">Open-Meteo · Real-time</span>
                    </div>`;
                }

                html += `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px;">`;

                recommendations.forEach((crop, i) => {
                    const sc   = crop.suitability_score;
                    const icon = getCategoryIcon(crop.category);
                    const loc  = crop.crop_name_local || crop.crop_name_hindi || crop.crop_name;
                    const hint = crop.reason_hindi || crop.reason || '';

                    html += `<div style="background:white;border-radius:15px;padding:20px;box-shadow:0 4px 15px rgba(0,0,0,0.08);border-top:4px solid ${scoreColor(sc)};">
                        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
                            <div>
                                <div style="font-size:1.1rem;font-weight:700;color:#2d5016;">${i+1}. ${escapeHtml(loc)}</div>
                                <div style="font-size:0.8rem;color:#888;">${escapeHtml(crop.crop_name)} ${icon} ${escapeHtml(crop.category)}</div>
                            </div>
                            <div style="text-align:center;min-width:50px;">
                                <div style="font-size:1.4rem;font-weight:800;color:${scoreColor(sc)};">${sc}%</div>
                                <div style="font-size:0.65rem;color:#aaa;">suitability</div>
                            </div>
                        </div>
                        ${scoreBar(sc)}
                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:12px 0;font-size:0.82rem;">
                            <div style="background:#f0fff0;border-radius:8px;padding:8px;text-align:center;">
                                <div style="font-weight:700;color:#28a745;">₹${(crop.profit_per_hectare||0).toLocaleString()}</div>
                                <div style="color:#888;font-size:0.72rem;">लाभ/हे.</div>
                            </div>
                            <div style="background:#f0f8ff;border-radius:8px;padding:8px;text-align:center;">
                                <div style="font-weight:700;color:#1565c0;">${crop.yield_per_hectare||0} q/ha</div>
                                <div style="color:#888;font-size:0.72rem;">उत्पादन</div>
                            </div>
                            <div style="background:#fff8e1;border-radius:8px;padding:8px;text-align:center;">
                                <div style="font-weight:700;color:#f57f17;">${crop.msp_per_quintal ? '₹'+crop.msp_per_quintal : 'No MSP'}</div>
                                <div style="color:#888;font-size:0.72rem;">MSP/q</div>
                            </div>
                            <div style="background:#fce4ec;border-radius:8px;padding:8px;text-align:center;">
                                <div style="font-weight:700;color:${waterColor(crop.water_requirement)};text-transform:capitalize;">${crop.water_requirement||'Moderate'}</div>
                                <div style="color:#888;font-size:0.72rem;">पानी</div>
                            </div>
                        </div>
                        ${crop.market_price && crop.market_is_live ? `<div style="font-size:0.78rem;color:#2e7d32;margin-bottom:6px;">📊 Live mandi: ₹${crop.market_price}/q</div>` : ''}
                        ${hint ? `<div style="background:#fff9c4;border-radius:8px;padding:8px 10px;font-size:0.82rem;color:#333;border-left:3px solid #ffc107;">💡 ${escapeHtml(hint)}</div>` : ''}
                        <div style="margin-top:8px;font-size:0.75rem;color:#aaa;">${escapeHtml(crop.duration_days||120)} days · ${escapeHtml(String(crop.temperature_range||''))}</div>
                    </div>`;
                });

                html += `</div><div style="margin-top:16px;font-size:0.78rem;color:#888;text-align:center;">
                    🧬 Engine v3 · 80 crops · ${escapeHtml(data.analysis_method||'multi_factor_scoring_v3')} ·
                    ${escapeHtml(data.data_source||'KrishiMitra Agro-Climatic Engine')}
                </div>`;
                container.innerHTML = html;
            } else {
                container.innerHTML = `<div style="padding:20px;text-align:center;color:#888;">फसल सुझाव उपलब्ध नहीं — GPS allow करें</div>`;
            }
        } catch (error) {
            const container = document.getElementById('cropsData');
            if (container) container.innerHTML = `<div style="padding:20px;text-align:center;color:#dc3545;">फसल सुझाव त्रुटि: ${escapeHtml(error.message)}</div>`;
        }

    }  // end loadCropRecommendations
    }

    // ========================================
    // KRISHI RAKSHA 2.0 DIAGNOSTICS
    // ========================================
    function fileToDataUrl(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    async function collectKrishiImages() {
        const mapping = [
            ['imgWhole', 'whole'],
            ['imgCloseUp', 'close_up'],
            ['imgLeaf', 'leaf'],
        ];
        const images = {};
        for (const [inputId, key] of mapping) {
            const input = document.getElementById(inputId);
            if (input?.files?.[0]) {
                images[key] = await fileToDataUrl(input.files[0]);
            }
        }
        return images;
    }

    async function runKrishiRakshaDiagnosis() {
        const cropInput = document.getElementById('krCropSearchInput');
        const resultsContainer = document.getElementById('krishiRakshaResults');

        const crop = (document.getElementById('krCropValue')?.value || cropInput?.value || '').trim();
        if (!crop) {
            alert('कृपया फसल खोजें और चुनें / Please search and select a crop first');
            return;
        }

        const images = await collectKrishiImages();
        if (Object.keys(images).length === 0) {
            alert('कृपया कम से कम एक पत्ती/फसल की तस्वीर अपलोड करें\nPlease upload at least one leaf or plant photo.');
            return;
        }

        // Show loading state
        resultsContainer.style.display = 'block';
        resultsContainer.innerHTML = `
            <div class="text-center p-5">
                <i class="fas fa-spinner fa-spin fa-3x text-success"></i>
                <h4 class="mt-3">Analyzing ${crop.charAt(0).toUpperCase() + crop.slice(1)}...</h4>
                <p>Plant validation • EfficientNet-B3 • Weather check...</p>
            </div>
        `;

        try {
            const response = await fetch(apiFetch('/api/diagnostics/detect/'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    crop: crop,
                    location: currentLocation,
                    latitude: currentLatitude,
                    longitude: currentLongitude,
                    accuracy: currentLocationAccuracy,
                    images: images,
                    session_id: sessionId,
                }),
            });

            const data = await response.json();
            console.log('KrishiRaksha Response:', data);

            const okStatuses = ['success', 'low_confidence', 'not_plant', 'photo_required', 'model_unavailable', 'tensorflow_missing'];
            if (okStatuses.includes(data.status)) {
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
        const statusAlerts = {
            not_plant: 'alert-warning',
            low_confidence: 'alert-warning',
            model_unavailable: 'alert-info',
            photo_required: 'alert-info',
        };
        const alertClass = statusAlerts[data.status] || 'alert-success';
        const statusMsg = data.message || (data.ml_prediction && data.ml_prediction.message) || '';

        let html = `
            <div class="real-time-header">
                <h4>🩺 Diagnostic Report: ${(data.crop_display || data.crop_detected || 'Crop').toString()}</h4>
                <p class="data-source">📍 ${data.location || ''}</p>
                <p class="timestamp">🕒 ${new Date(data.timestamp).toLocaleString('hi-IN')}</p>
            </div>
        `;
        if (statusMsg) {
            html += `<div class="alert ${alertClass} mt-3">${statusMsg}</div>`;
        }
        if (data.ml_prediction && data.ml_prediction.top_predictions && data.ml_prediction.top_predictions.length) {
            html += '<div class="small text-muted mb-2"><strong>Top AI guesses:</strong> ';
            html += data.ml_prediction.top_predictions.map(p =>
                `${p.crop_name || '?'} / ${p.disease_name || '?'} (${Math.round((p.probability || 0) * 100)}%)`
            ).join(' · ');
            html += '</div>';
        }

        html += `<div class="row g-4 mt-3">`;

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
            await fetch(apiFetch('/api/diagnostics/feedback/'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    is_correct: isCorrect
                })
            });
            alert(isCorrect ? 'धन्यवाद! Feedback recorded.' : 'Thank you. We will improve our model.');
        } catch (error) {
            console.error('Feedback error:', error);
        }
    }

    // ========================================
    // AI CHAT FUNCTIONS
    // ========================================
    async function handleChatUserMessage() {
        const input = document.getElementById('messageInput');
        const chatMessages = document.getElementById('chatMessages');
        if (!input || !chatMessages) return;

        const message = input.value.trim();
        if (!message) return;

        // Add user message to chat
        const userDiv = document.createElement('div');
        userDiv.className = 'message user-message';
        userDiv.style.cssText = 'background:#4a7c59;color:white;padding:12px 16px;border-radius:12px 12px 4px 12px;margin:8px 0 8px auto;max-width:80%;text-align:right;';
        userDiv.textContent = message;
        chatMessages.appendChild(userDiv);
        input.value = '';
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // Show loading indicator (inline, not the shared #loading div)
        const loadingDiv = document.createElement('div');
        loadingDiv.id = 'chatLoadingMsg';
        loadingDiv.style.cssText = 'padding:12px;color:#4a7c59;font-size:0.9rem;';
        loadingDiv.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${(typeof window.t === 'function' ? window.t('loading') : 'Loading...')}`;
        chatMessages.appendChild(loadingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            const data = await apiPostJson('/api/chatbot/query/', {
                query: message,
                location: currentLocation,
                latitude: currentLatitude,
                longitude: currentLongitude,
                accuracy: currentLocationAccuracy,
                language: (typeof window.getCurrentLang === 'function' ? window.getCurrentLang() : (document.documentElement.lang === 'en' ? 'en' : 'hi')),
                session_id: sessionId,
            });
            const botReply = data.response || data.answer || data.message || 'मुझे समझ नहीं आया, कृपया फिर से पूछें।';

            // Remove loading indicator
            const ld = document.getElementById('chatLoadingMsg');
            if (ld) ld.remove();

            const escapeHtml = (s) => String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

            let extra = '';
            const suggestions = data.crop_suggestions || [];
            if (suggestions.length) {
                extra += '<div style="margin-top:12px;padding:10px;background:#fff;border-radius:8px;border:1px solid #d4edda;">';
                extra += '<strong style="color:#2d5016;font-size:0.9rem;">📌 सुझाव:</strong><ul style="margin:6px 0 0 18px;padding:0;font-size:0.88rem;">';
                suggestions.forEach(s => {
                    if (s.type === 'crop_recommendation') {
                        extra += '<li><b>' + escapeHtml(s.crop) + '</b> (' + escapeHtml(s.hindi) + ') — ' + escapeHtml(s.score) + '%: ' + escapeHtml(s.reason) + '</li>';
                    } else if (s.type === 'market_price') {
                        extra += '<li>' + escapeHtml(s.crop) + ': ₹' + escapeHtml(s.modal_price) + '/q (MSP ₹' + escapeHtml(s.msp) + ')</li>';
                    }
                });
                extra += '</ul></div>';
            }
            const sources = data.sources || [];
            if (sources.length) {
                extra += '<div style="margin-top:8px;font-size:0.75rem;color:#666;">📡 स्रोत: ' + escapeHtml(sources.slice(0, 3).join(' • ')) + '</div>';
            }

            const botDiv = document.createElement('div');
            botDiv.className = 'message bot-message';
            botDiv.style.cssText = 'background:linear-gradient(135deg,#e8f5e8,#f0fff0);border-left:4px solid #4a7c59;border-radius:10px;padding:15px;margin:8px 0;';
            botDiv.innerHTML = '<strong style="color:#2d5016;">🌾 KrishiMitra AI:</strong><div style="margin-top:8px;color:#333;line-height:1.6;white-space:pre-wrap;">' + escapeHtml(botReply) + '</div>' + extra;
            chatMessages.appendChild(botDiv);
        } catch (error) {
            const ld = document.getElementById('chatLoadingMsg');
            if (ld) ld.remove();

            const errDiv = document.createElement('div');
            errDiv.style.cssText = 'background:#fff3cd;border-left:4px solid #ffc107;border-radius:10px;padding:12px;margin:8px 0;color:#856404;';
            errDiv.textContent = `त्रुटि: ${error.message || 'नेटवर्क — कृपया दोबारा प्रयास करें'}`;
            chatMessages.appendChild(errDiv);
        } finally {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    function askSuggested(question) {
        const input = document.getElementById('messageInput');
        if (input) {
            input.value = question;
            handleChatUserMessage();
        }
    }

    function clearChat() {
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            chatMessages.innerHTML = '<div class="message bot-message" style="background:linear-gradient(135deg,#e8f5e8,#f0fff0);border-left:4px solid #4a7c59;border-radius:10px;padding:15px;"><strong style="color:#2d5016;">🌾 KrishiMitra AI:</strong><div style="margin-top:8px;color:#333;line-height:1.6;">नमस्ते! मैं KrishiMitra AI हूँ। कोई भी कृषि संबंधी सवाल पूछें! 🌾</div></div>';
        }
    }

    // ========================================
    // MAKE FUNCTIONS GLOBALLY AVAILABLE
    // ========================================
    window.apiFetch = apiFetch;
    window.apiGetJson = apiGetJson;
    window.apiPostJson = apiPostJson;
    window.updateLocation = updateLocation;
    window.searchLocations = searchLocations;
    window.showLocationSuggestions = showLocationSuggestions;
    window.selectLocation = selectLocation;
    window.searchCurrentLocation = searchCurrentLocation;
    window.detectLocation = detectLocation;
    window.selectMandi = selectMandi;
    window.onMandiSelected = onMandiSelected;
    window.populateMandiDropdown = populateMandiDropdown;
    window.loadMoreMandis = loadMoreMandis;
    window.applyManualLocation = applyManualLocation;
    window.showService = showService;
    window.loadMarketPrices = loadMarketPrices;
    window.forceReloadMarketPrices = forceReloadMarketPrices;
    window.searchCropsForMarket = searchCropsForMarket;
    window.clearCropPriceSearch = clearCropPriceSearch;
    window.selectCropForMarket = selectCropForMarket;
    window.searchCrop = searchCrop;
    window.showCropSuggestions = showCropSuggestions;
    window.searchSpecificCrop = searchSpecificCrop;
    window.searchCropsForDiagnostics = searchCropsForDiagnostics;
    window.selectCropForDiagnostics = selectCropForDiagnostics;
    window.loadWeatherData = loadWeatherData;
    window.loadGovernmentSchemes = loadGovernmentSchemes;
    window.loadCropRecommendations = loadCropRecommendations;
    window.runKrishiRakshaDiagnosis = runKrishiRakshaDiagnosis;
    window.submitKRFeedback = submitKRFeedback;
    window.handleChatUserMessage = handleChatUserMessage;
    window.sendMessage = handleChatUserMessage;
    window.askSuggested = askSuggested;
    window.clearChat = clearChat;

    // ========================================
    // AUTO-INITIALIZE
    // ========================================
    document.addEventListener('click', function (e) {
        const box = document.querySelector('.location-search-container');
        if (box && !box.contains(e.target)) {
            hideLocationSuggestions();
        }
    });

    function reloadAllServices() {
        populateMandiDropdown().then(() => loadMarketPrices()).catch(err => {
            console.error('Mandi/market load error:', err);
        });
        loadWeatherData();
        loadGovernmentSchemes();
        loadCropRecommendations();
    }

    async function bootstrapApp() {
        console.log('📊 Page loaded, initializing...');
        setupServiceCards();

        const apiOk = await checkBackendHealth();
        if (!apiOk) {
            let banner = document.getElementById('backendOfflineBanner');
            if (!banner) {
                banner = document.createElement('div');
                banner.id = 'backendOfflineBanner';
                banner.style.cssText = 'background:#f8d7da;color:#721c24;padding:12px 16px;text-align:center;font-size:0.95rem;border-bottom:2px solid #f5c6cb;';
                document.body.prepend(banner);
            }
            banner.innerHTML = '⚠️ API सर्वर नहीं मिला — कुछ डेटा लोड नहीं हो सकता। चलाएं: <code>python manage.py runserver</code> (8000) और <code>cd frontend && npm run dev</code> (5173)';
        } else {
            const banner = document.getElementById('backendOfflineBanner');
            if (banner) banner.remove();
        }

        reloadAllServices();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => setTimeout(bootstrapApp, 300));
    } else {
        setTimeout(bootstrapApp, 300);
    }
})();
