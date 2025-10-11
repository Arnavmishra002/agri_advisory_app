# 🚀 Krishimitra AI - Enhanced API Documentation

## 📋 **API Overview**

The Krishimitra AI Agricultural Assistant provides comprehensive RESTful APIs for agricultural advisory, government scheme information, market data, and AI-powered recommendations.

---

## 🔗 **Base URL**
```
Production: https://your-domain.com/api/
Development: http://localhost:8000/api/
```

---

## 🔐 **Authentication**

### JWT Token Authentication
```http
Authorization: Bearer <your-jwt-token>
```

### Token Endpoints
- **POST** `/api/token/` - Obtain access token
- **POST** `/api/token/refresh/` - Refresh access token

---

## 🤖 **AI Chatbot Endpoints**

### Chat with AI Assistant
```http
POST /api/chatbot/
```

**Request Body:**
```json
{
  "query": "wheat ke liye fertilizer kya lagayein",
  "language": "hinglish",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "location": "Delhi"
}
```

**Response:**
```json
{
  "response": "🌱 Delhi में wheat के लिए उर्वरक सलाह:\n\n💰 सरकारी उर्वरक कीमतें:\n• Urea: ₹242/50kg bag (50% subsidy)\n• DAP: ₹1,350/50kg bag (60% subsidy)\n• MOP: ₹1,750/50kg bag (40% subsidy)\n\n📊 Wheat के लिए उर्वरक अनुशंसा:\n• Urea: 100-120 kg/hectare\n• DAP: 50-60 kg/hectare\n• MOP: 40-50 kg/hectare\n• Zinc Sulphate: 25 kg/hectare",
  "intent": "fertilizer_recommendation",
  "entities": {
    "crop": "wheat",
    "location": "delhi"
  },
  "language": "hinglish",
  "timestamp": 1641234567.89,
  "confidence_score": 0.92
}
```

---

## 🌾 **Crop Advisory Endpoints**

### Get Crop Recommendations
```http
POST /api/advisories/ml_crop_recommendation/
```

**Request Body:**
```json
{
  "soil_type": "loamy",
  "season": "rabi",
  "temperature": 25,
  "rainfall": 150,
  "humidity": 65,
  "ph": 7.2,
  "organic_matter": 2.5,
  "user_id": "user123"
}
```

**Response:**
```json
{
  "recommendations": [
    {
      "crop": "wheat",
      "confidence": 0.85,
      "reasoning": "Suitable soil and climate conditions",
      "expected_yield": "4.5 tonnes/hectare",
      "market_price": "₹2,275/quintal (MSP)"
    },
    {
      "crop": "barley",
      "confidence": 0.80,
      "reasoning": "Good alternative crop for the season",
      "expected_yield": "3.2 tonnes/hectare",
      "market_price": "₹1,850/quintal (MSP)"
    }
  ],
  "soil_analysis": {
    "ph_status": "optimal",
    "nutrient_level": "medium",
    "recommendations": ["Add organic manure", "Apply zinc sulfate"]
  }
}
```

### Get Fertilizer Recommendations
```http
POST /api/advisories/ml_fertilizer_recommendation/
```

**Request Body:**
```json
{
  "crop_type": "wheat",
  "soil_type": "loamy",
  "season": "rabi",
  "temperature": 25,
  "rainfall": 150,
  "humidity": 65,
  "ph": 7.2,
  "organic_matter": 2.5
}
```

**Response:**
```json
{
  "fertilizer_plan": {
    "primary_nutrients": {
      "urea": {
        "amount": "110 kg/hectare",
        "timing": "Split application",
        "cost": "₹532/hectare",
        "subsidy": "50% available"
      },
      "dap": {
        "amount": "55 kg/hectare",
        "timing": "Basal application",
        "cost": "₹742/hectare",
        "subsidy": "60% available"
      }
    },
    "secondary_nutrients": {
      "zinc_sulphate": {
        "amount": "25 kg/hectare",
        "cost": "₹450/hectare",
        "subsidy": "30% available"
      }
    },
    "application_schedule": {
      "basal": "DAP, MOP, Zinc Sulphate at sowing",
      "top_dressing_1": "Urea (1/3) at 25-30 days",
      "top_dressing_2": "Urea (1/3) at 45-50 days",
      "top_dressing_3": "Urea (1/3) at 60-65 days"
    },
    "total_cost": "₹1,724/hectare",
    "subsidy_savings": "₹862/hectare"
  }
}
```

---

## 🏛️ **Government Schemes Endpoints**

### Get Government Schemes
```http
GET /api/government-schemes/?lang=en
```

**Response:**
```json
{
  "schemes": [
    {
      "name": "PM Kisan Samman Nidhi",
      "description": "₹6,000 annual income support for farmers",
      "eligibility": "All farmers with valid land records",
      "status": "Active",
      "amount": "₹6,000 per year",
      "beneficiaries": "12 crore farmers",
      "application_process": "Online application at pmkisan.gov.in",
      "helpline": "1800-180-1551"
    },
    {
      "name": "Pradhan Mantri Fasal Bima Yojana",
      "description": "Crop insurance scheme for farmers",
      "eligibility": "Farmers growing notified crops",
      "status": "Active",
      "amount": "Subsidized premium",
      "beneficiaries": "6 crore farmers",
      "coverage": "90% premium subsidy",
      "helpline": "1800-425-1551"
    }
  ]
}
```

---

## 🌤️ **Weather Data Endpoints**

### Get Current Weather
```http
GET /api/weather/current/?lat=28.6139&lon=77.2090&lang=en
```

**Response:**
```json
{
  "location": {
    "name": "Delhi",
    "latitude": 28.6139,
    "longitude": 77.2090
  },
  "current": {
    "temperature": 28,
    "humidity": 65,
    "rainfall": 0,
    "wind_speed": 12,
    "condition": "Partly Cloudy"
  },
  "agricultural_advisory": {
    "irrigation": "Recommended for wheat crop",
    "pest_control": "Monitor for aphid infestation",
    "fertilizer_timing": "Good time for top dressing"
  }
}
```

### Get Weather Forecast
```http
GET /api/weather/forecast/?lat=28.6139&lon=77.2090&lang=en&days=5
```

---

## 📊 **Market Data Endpoints**

### Get Market Prices
```http
GET /api/market-prices/prices/?lat=28.6139&lon=77.2090&lang=en&product=wheat
```

**Response:**
```json
{
  "product": "wheat",
  "location": "Delhi",
  "prices": {
    "mandi_price": "₹2,350/quintal",
    "msp_price": "₹2,275/quintal",
    "trend": "+2.5%",
    "last_updated": "2025-01-10T10:30:00Z"
  },
  "market_analysis": {
    "demand": "High",
    "supply": "Moderate",
    "price_outlook": "Stable to increasing"
  }
}
```

### Get Trending Crops
```http
GET /api/trending-crops/?lat=28.6139&lon=77.2090&lang=en
```

---

## 🐛 **Pest Detection Endpoints**

### Detect Pests from Image
```http
POST /api/pest-detection/detect/
```

**Request:** Multipart form data with image file

**Response:**
```json
{
  "detections": [
    {
      "pest_name": "Aphid",
      "confidence": 0.92,
      "severity": "Medium",
      "treatment": "Apply neem oil spray",
      "prevention": "Remove affected leaves, improve air circulation"
    }
  ],
  "image_analysis": {
    "healthy_percentage": 75,
    "affected_percentage": 25,
    "overall_condition": "Good with minor issues"
  }
}
```

---

## 📱 **SMS/IVR Endpoints**

### Receive SMS
```http
POST /api/sms-ivr/receive-sms/
```

**Request Body:**
```json
{
  "phone_number": "+919876543210",
  "message": "wheat price delhi"
}
```

### Handle IVR Input
```http
POST /api/sms-ivr/ivr-input/
```

**Request Body:**
```json
{
  "phone_number": "+919876543210",
  "user_input": "1"
}
```

---

## 🔊 **Text-to-Speech Endpoints**

### Convert Text to Speech
```http
POST /api/tts/speak/
```

**Request Body:**
```json
{
  "text": "Wheat के लिए fertilizer की सलाह",
  "language": "hi"
}
```

**Response:**
```json
{
  "audio_url": "http://localhost:8000/media/audio/speech_1641234567.mp3"
}
```

---

## 👥 **User Management Endpoints**

### Get Users (Admin Only)
```http
GET /api/users/
```

### Create User (Admin Only)
```http
POST /api/users/
```

**Request Body:**
```json
{
  "username": "farmer123",
  "email": "farmer@example.com",
  "role": "farmer",
  "phone": "+919876543210"
}
```

---

## 💬 **Forum Endpoints**

### Get Forum Posts
```http
GET /api/forum/
```

### Create Forum Post
```http
POST /api/forum/
```

**Request Body:**
```json
{
  "title": "Best fertilizer for wheat",
  "content": "What fertilizer works best for wheat in Punjab?"
}
```

---

## 📍 **Location Services Endpoints**

### Search Locations
```http
GET /api/locations/search/?q=delhi&limit=5
```

**Response:**
```json
{
  "locations": [
    {
      "name": "Delhi",
      "state": "Delhi",
      "country": "India",
      "latitude": 28.6139,
      "longitude": 77.2090,
      "type": "city",
      "agricultural_zone": "Northern Plains"
    }
  ]
}
```

---

## 📈 **Analytics Endpoints**

### Get Model Performance
```http
GET /api/advisories/model_performance/
```

### Get Feedback Analytics
```http
GET /api/advisories/feedback_analytics/?days=30
```

### Collect User Feedback
```http
POST /api/advisories/collect_feedback/
```

**Request Body:**
```json
{
  "user_id": "user123",
  "session_id": "session456",
  "prediction_type": "crop_recommendation",
  "input_data": {"soil_type": "loamy", "season": "rabi"},
  "system_prediction": {"crop": "wheat", "confidence": 0.85},
  "actual_result": {"crop": "wheat", "yield": "4.2 tonnes/hectare"},
  "feedback_rating": 4,
  "feedback_text": "Good recommendation, yield was as expected"
}
```

---

## ⚡ **Rate Limiting**

- **General endpoints:** 100 requests/minute per user
- **ML prediction endpoints:** 10 requests/minute per user
- **File upload endpoints:** 5 requests/minute per user

---

## 🔒 **Error Handling**

### Error Response Format
```json
{
  "error": "Validation failed",
  "message": "Invalid input parameters",
  "errors": [
    {
      "field": "latitude",
      "message": "Must be between -90 and 90"
    }
  ],
  "recovery_options": [
    {
      "action": "correct_input",
      "message": "Please provide valid coordinates",
      "examples": ["28.6139", "77.2090"]
    }
  ],
  "timestamp": 1641234567.89
}
```

### HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `429` - Too Many Requests
- `500` - Internal Server Error

---

## 🚀 **Performance Optimization**

### Response Times
- **AI Chatbot:** < 2 seconds
- **Government Data:** < 1 second (cached)
- **Market Prices:** < 1 second (cached)
- **ML Predictions:** < 3 seconds

### Caching Strategy
- **Government Schemes:** 24 hours
- **Market Prices:** 1 hour
- **Weather Data:** 30 minutes
- **ML Predictions:** 30 minutes
- **Fallback Data:** 7 days

---

## 📚 **Interactive Documentation**

Visit the interactive API documentation at:
- **Swagger UI:** `http://localhost:8000/api/schema/swagger-ui/`
- **ReDoc:** `http://localhost:8000/api/schema/redoc/`

---

## 🔧 **SDK and Integration**

### Python SDK Example
```python
import requests

# Initialize client
api_client = requests.Session()
api_client.headers.update({
    'Authorization': 'Bearer YOUR_JWT_TOKEN',
    'Content-Type': 'application/json'
})

# Chat with AI
response = api_client.post('http://localhost:8000/api/chatbot/', json={
    'query': 'wheat fertilizer advice',
    'language': 'en',
    'latitude': 28.6139,
    'longitude': 77.2090
})

print(response.json())
```

### JavaScript SDK Example
```javascript
const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api/',
  headers: {
    'Authorization': 'Bearer YOUR_JWT_TOKEN',
    'Content-Type': 'application/json'
  }
});

// Chat with AI
const response = await apiClient.post('/chatbot/', {
  query: 'wheat fertilizer advice',
  language: 'en',
  latitude: 28.6139,
  longitude: 77.2090
});

console.log(response.data);
```

---

## 📞 **Support and Contact**

- **Technical Support:** support@krishimitra.ai
- **API Issues:** api-support@krishimitra.ai
- **Documentation:** docs@krishimitra.ai

---

## 📄 **Version History**

- **v2.0** - Enhanced fertilizer recommendations, improved caching
- **v1.5** - Added government schemes integration
- **v1.0** - Initial API release

---

*Last Updated: January 10, 2025*
