# 🧪 Dynamic Government API Verification Guide

## 📋 Purpose

This guide will help you verify that:
1. ✅ All services are giving correct output from government APIs
2. ✅ Output is **dynamic** and changes based on location/parameters
3. ✅ Data is real-time with current timestamps
4. ✅ All 6 service cards work with live government data

---

## 🚀 Step 1: Fix Server Startup Issues

The Django server needs these dependencies installed:

```powershell
cd C:\AI\agri_advisory_app

# Install required packages
pip install django djangorestframework django-cors-headers drf-spectacular google-generativeai requests python-dateutil

# Optional: Install Celery dependencies (or keep them disabled)
pip install celery redis psutil

# Run migrations
python manage.py migrate

# Start the server
python manage.py runserver
```

**Expected Output:**
```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
Django version 5.2.6, using settings 'core.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

---

## 🧪 Step 2: Test Service Cards in Browser

### Open the Application:
```
http://localhost:8000
```

### Click Each Service Card:

| # | Service Card | What to Click | Expected Result |
|---|-------------|---------------|-----------------|
| 1 | 🏛️ सरकारी योजनाएं | Click the card | Opens government schemes section |
| 2 | 🌱 फसल सुझाव | Click the card | Opens crop recommendation form |
| 3 | 🌤️ मौसम पूर्वानुमान | Click the card | Opens weather information |
| 4 | 📈 बाजार कीमतें | Click the card | Opens market prices section |
| 5 | 🐛 कीट नियंत्रण | Click the card | Opens pest control section |
| 6 | 🤖 AI सहायक | Click the card | Opens AI chatbot interface |

**✅ Verification:** All 6 cards should be clickable and open their respective sections.

---

## 🌐 Step 3: Test Government APIs Directly

### Test 1: Weather API (IMD) - Dynamic by Location

#### Test Delhi:
```javascript
// Open browser console (F12) and run:
fetch('http://localhost:8000/api/locations/real_time_weather/?lat=28.7041&lon=77.1025')
  .then(r => r.json())
  .then(data => {
    console.log('Delhi Weather:', data);
    console.log('Temperature:', data.temperature || data.temp || data.main?.temp);
    console.log('Timestamp:', data.timestamp || data.dt);
  })
```

#### Test Mumbai:
```javascript
fetch('http://localhost:8000/api/locations/real_time_weather/?lat=19.0760&lon=72.8777')
  .then(r => r.json())
  .then(data => {
    console.log('Mumbai Weather:', data);
    console.log('Temperature:', data.temperature || data.temp || data.main?.temp);
  })
```

**✅ DYNAMIC VERIFICATION:**
- Delhi and Mumbai should have **different temperatures**
- Timestamps should be **current** (within last few hours)
- Data structure should include: temperature, humidity, wind speed, description

---

### Test 2: Market Prices API (Agmarknet/e-NAM) - Dynamic by State/Commodity

#### Test Wheat in Delhi:
```javascript
fetch('http://localhost:8000/api/locations/real_time_market_prices/?commodity=wheat&state=Delhi')
  .then(r => r.json())
  .then(data => {
    console.log('Wheat prices in Delhi:', data);
    console.log('Modal Price:', data.modal_price || data.price);
  })
```

#### Test Rice in Maharashtra:
```javascript
fetch('http://localhost:8000/api/locations/real_time_market_prices/?commodity=rice&state=Maharashtra')
  .then(r => r.json())
  .then(data => {
    console.log('Rice prices in Maharashtra:', data);
  })
```

**✅ DYNAMIC VERIFICATION:**
- Wheat and Rice should have **different prices**
- Delhi and Maharashtra should show **different mandis**
- Prices should be in **₹ (Rupees)**
- Data should include: modal_price, min_price, max_price, market_name

---

### Test 3: Crop Recommendations API (ICAR) - Dynamic by Location

#### Test Delhi:
```javascript
fetch('http://localhost:8000/api/locations/real_time_crop_recommendations/?location=Delhi&season=rabi')
  .then(r => r.json())
  .then(data => {
    console.log('Crops for Delhi (Rabi):', data);
    console.log('Recommended crops:', data.crops || data.recommendations);
  })
```

#### Test Mumbai:
```javascript
fetch('http://localhost:8000/api/locations/real_time_crop_recommendations/?location=Mumbai&season=kharif')
  .then(r => r.json())
  .then(data => {
    console.log('Crops for Mumbai (Kharif):', data);
  })
```

**✅ DYNAMIC VERIFICATION:**
- Delhi and Mumbai should have **different crop recommendations**
- Rabi and Kharif seasons should suggest **different crops**
- Data should include: crop names, suitability, expected yield

---

### Test 4: Comprehensive Government Data API - All Sources Together

```javascript
fetch('http://localhost:8000/api/locations/comprehensive_government_data/?lat=28.7041&lon=77.1025&location=Delhi&commodity=wheat')
  .then(r => r.json())
  .then(data => {
    console.log('Comprehensive Government Data:', data);
    console.log('Has Weather?', 'weather' in data || 'imd' in data);
    console.log('Has Market Prices?', 'market' in data || 'prices' in data);
    console.log('Has Crop Data?', 'crops' in data || 'recommendations' in data);
    console.log('Timestamp:', data.timestamp || data.last_updated);
  })
```

**✅ VERIFICATION:**
- Should include data from **3 sources**: IMD (weather), Agmarknet (prices), ICAR (crops)
- Should have a **current timestamp**
- Response should be **large** (multiple KB)
- Data reliability score should be **>= 80%**

---

### Test 5: AI Chatbot API - Location-Aware Responses

```javascript
fetch('http://localhost:8000/api/chatbot/', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    query: 'Delhi mein kya fasal lagayein?',
    language: 'hinglish',
    location: 'Delhi',
    latitude: 28.7041,
    longitude: 77.1025
  })
})
  .then(r => r.json())
  .then(data => {
    console.log('AI Response:', data.response || data.answer);
  })
```

**✅ VERIFICATION:**
- Response should mention **Delhi** specifically
- Should suggest crops **suitable for Delhi** (wheat, mustard, vegetables)
- Response should be in **Hinglish** (mix of Hindi and English)

---

## 📊 Step 4: Test Dynamic Behavior in UI

### Test Weather Service:

1. Click **"मौसम पूर्वानुमान"** (Weather) card
2. Change location dropdown to different cities:
   - Select **Delhi**
   - Note the temperature and weather condition
   - Select **Mumbai**
   - Temperature should **change**
   - Select **Bangalore**
   - Temperature should be **different again**

**✅ DYNAMIC VERIFICATION:**
- Temperature differs by at least 2-5°C between cities
- Weather descriptions vary (sunny, cloudy, rainy, etc.)
- Humidity levels are different

---

### Test Crop Recommendations Service:

1. Click **"फसल सुझाव"** (Crop Recommendations) card
2. Test different locations:
   - Select **Punjab** → Should recommend: Wheat, Rice, Cotton
   - Select **Kerala** → Should recommend: Coconut, Rubber, Spices
   - Select **Maharashtra** → Should recommend: Cotton, Sugarcane, Soybean

**✅ DYNAMIC VERIFICATION:**
- Different crops recommended for different regions
- MSP (Minimum Support Price) varies by crop
- Profitability scores differ based on location

---

### Test Market Prices Service:

1. Click **"बाजार कीमतें"** (Market Prices) card
2. Test different combinations:
   
   **Test 1:** Wheat in Delhi
   - State: Delhi
   - Commodity: Wheat
   - Note the prices
   
   **Test 2:** Wheat in Punjab
   - State: Punjab
   - Commodity: Wheat
   - Prices should be **different**
   
   **Test 3:** Rice in Tamil Nadu
   - State: Tamil Nadu
   - Commodity: Rice
   - Prices should be **different from wheat**

**✅ DYNAMIC VERIFICATION:**
- Prices vary by state (5-20% difference)
- Different commodities have different prices
- Multiple mandis shown per region
- Arrival quantities differ

---

## 🔍 Step 5: Verify Real-Time Data

### Check Timestamps:

For each API response, verify the timestamp is current:

```javascript
// Run this to check current time vs API timestamp
const now = new Date();
console.log('Current Time:', now.toISOString());

// Then compare with API timestamp
fetch('http://localhost:8000/api/locations/real_time_weather/?lat=28.7041&lon=77.1025')
  .then(r => r.json())
  .then(data => {
    const apiTime = new Date(data.timestamp || data.dt * 1000);
    const diffMinutes = (now - apiTime) / 1000 / 60;
    console.log('API Timestamp:', apiTime.toISOString());
    console.log('Age:', diffMinutes.toFixed(0), 'minutes old');
    
    if (diffMinutes < 60) {
      console.log('✅ Data is fresh (< 1 hour old)');
    } else {
      console.log('⚠️ Data might be cached or stale');
    }
  })
```

**✅ VERIFICATION:**
- Timestamps should be within **30-60 minutes** of current time
- Cache should refresh every **30 seconds** (per your settings)
- Data should not be days/weeks old

---

## 📈 Step 6: Performance Verification

### Check Response Times:

```javascript
// Test response speed
const startTime = performance.now();

fetch('http://localhost:8000/api/locations/comprehensive_government_data/?lat=28.7041&lon=77.1025&location=Delhi&commodity=wheat')
  .then(r => r.json())
  .then(data => {
    const endTime = performance.now();
    const responseTime = ((endTime - startTime) / 1000).toFixed(2);
    console.log('Response Time:', responseTime, 'seconds');
    
    if (responseTime < 2) {
      console.log('✅ FAST: Response under 2 seconds');
    } else if (responseTime < 5) {
      console.log('⚠️ OK: Response under 5 seconds');
    } else {
      console.log('❌ SLOW: Response over 5 seconds');
    }
  })
```

**✅ VERIFICATION:**
- Individual APIs: < 1 second
- Comprehensive API: < 2 seconds
- Chatbot API: < 3 seconds
- No timeout errors

---

## ✅ Step 7: Complete Verification Checklist

### Service Cards (UI):
- [ ] All 6 service cards are clickable
- [ ] Hover effects work smoothly
- [ ] Active state styling applies
- [ ] Smooth scroll to content works
- [ ] No JavaScript console errors

### Weather Service:
- [ ] Weather API responds (200 OK)
- [ ] Temperature data is present
- [ ] Data changes by location (Delhi ≠ Mumbai)
- [ ] Timestamps are current
- [ ] IMD as data source

### Market Prices Service:
- [ ] Market API responds (200 OK)
- [ ] Prices are in Indian Rupees (₹)
- [ ] Data changes by state
- [ ] Data changes by commodity
- [ ] Multiple mandis shown
- [ ] Agmarknet/e-NAM as source

### Crop Recommendations Service:
- [ ] Crop API responds (200 OK)
- [ ] Recommendations differ by location
- [ ] Recommendations differ by season
- [ ] MSP prices included
- [ ] ICAR as data source

### Comprehensive API:
- [ ] Includes weather data
- [ ] Includes market prices
- [ ] Includes crop recommendations
- [ ] Current timestamp present
- [ ] Response < 2 seconds

### AI Chatbot:
- [ ] Chatbot responds to queries
- [ ] Location-aware responses
- [ ] Multilingual support (Hindi/English/Hinglish)
- [ ] Answers farming questions
- [ ] Response < 3 seconds

### Dynamic Behavior:
- [ ] Weather varies by coordinates
- [ ] Prices vary by state/commodity
- [ ] Crops vary by location/season
- [ ] Real-time timestamps
- [ ] No cached old data

---

## 🎯 Expected Results Summary

### ✅ All Services Should Show:

1. **Different Data by Location:**
   - Delhi weather ≠ Mumbai weather
   - Punjab crops ≠ Kerala crops
   - Delhi prices ≠ Maharashtra prices

2. **Current Timestamps:**
   - All data within last hour
   - 30-second cache refresh
   - No stale data

3. **Government Sources:**
   - IMD for weather
   - Agmarknet/e-NAM for prices
   - ICAR for crop recommendations
   - Live API connections

4. **Fast Performance:**
   - APIs respond in < 2 seconds
   - No timeouts
   - Smooth user experience

5. **Correct Data Format:**
   - Temperatures in Celsius
   - Prices in Rupees
   - Crop names in local language
   - Proper units and measurements

---

## 🐛 Troubleshooting

### Issue: Server Won't Start

**Solutions:**
```powershell
# Install missing dependencies
pip install -r requirements.txt

# Or install individually
pip install django djangorestframework django-cors-headers

# Check Python version
python --version  # Should be 3.8+
```

### Issue: APIs Return Errors

**Check:**
1. Django server is running
2. No firewall blocking localhost:8000
3. Database migrations are applied: `python manage.py migrate`
4. Check server logs for error messages

### Issue: Data Appears Same for All Locations

**Possible Causes:**
1. Cache not refreshing - restart server
2. Mock data being served - check API implementation
3. Government APIs down - check external API status

### Issue: Slow Response Times

**Optimizations:**
1. Check internet connection
2. Verify cache is working (30-second TTL)
3. Check if external government APIs are slow
4. Consider Redis for better caching

---

## 📊 Automated Testing Script

Once the server is running, use the automated test:

```powershell
cd C:\AI
python test_dynamic_government_apis.py
```

This will automatically test:
- ✅ All 5 API endpoints
- ✅ Multiple locations (Delhi, Mumbai, Bangalore, Chennai)
- ✅ Multiple commodities (wheat, rice, potato, onion)
- ✅ Dynamic behavior verification
- ✅ Timestamp freshness
- ✅ Response time measurement

---

## 🎉 Success Criteria

Your system is working correctly if:

✅ **All service cards are clickable** (6/6)  
✅ **Weather data varies by location** (Delhi ≠ Mumbai)  
✅ **Market prices vary by state/commodity**  
✅ **Crop recommendations differ by region**  
✅ **All timestamps are current** (< 1 hour old)  
✅ **Response times are fast** (< 2 seconds)  
✅ **No console errors**  
✅ **Government sources verified** (IMD, Agmarknet, ICAR)  
✅ **Data is in correct format** (Celsius, Rupees, etc.)  
✅ **Cache refreshes every 30 seconds**  

---

**🌾 Your Krishimitra AI should pass all these tests to confirm government APIs are working correctly with dynamic output!**

---

_Last Updated: October 14, 2025_  
_Version: v4.1_  
_Status: Ready for Verification_

