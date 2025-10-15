# 🌾 Krishimitra AI - Backend APIs Only

## Overview
This is the backend API service for Krishimitra AI agricultural advisory system. All frontend/UI components have been removed to allow for rebuilding.

## 🚀 Available APIs

### 🤖 AI Chatbot APIs
- `POST /api/chatbot/` - Main AI chatbot endpoint
- `POST /api/advisories/chatbot/` - Advisory chatbot

### 🌤️ Weather APIs
- `GET /api/realtime-gov/weather/?location=Delhi` - Real-time weather data

### 💰 Market Price APIs
- `GET /api/realtime-gov/market_prices/?location=Delhi` - Market prices from government APIs

### 🌾 Crop Recommendation APIs
- `GET /api/realtime-gov/crop_recommendations/` - AI-powered crop recommendations

### 🏛️ Government Schemes APIs
- `GET /api/realtime-gov/government_schemes/?location=Delhi` - Government agricultural schemes

### 🐛 Pest Detection APIs
- `GET /api/pest-detection/` - Pest detection and control

### 🌱 Soil Health APIs
- `GET /api/realtime-gov/soil_health/` - Soil health data

## 🛠️ Backend Services

### Core Services Directory: `advisory/services/`
- **AI/ML Services**: Advanced AI models and chatbot intelligence
- **Government APIs**: Integration with IMD, Agmarknet, ICAR, PM-Kisan
- **Real-time Data**: Weather, market prices, crop recommendations
- **Location Services**: Dynamic location-based data
- **Multilingual Support**: Hindi, English, Hinglish

### Key Service Files:
- `realtime_government_ai.py` - Main AI service
- `ollama_integration.py` - Ollama/Llama3 integration
- `consolidated_government_service.py` - Government API consolidation
- `ultimate_realtime_system.py` - Comprehensive real-time system
- `pest_detection.py` - Pest detection service
- `weather_api.py` - Weather data service
- `market_api.py` - Market price service

## 🔧 Setup

1. **Install Dependencies**:
                                                        ```bash
   pip install -r requirements.txt
   ```

2. **Run Server**:
                                                          ```bash
                                                          python manage.py runserver
                                                        ```

3. **Access APIs**:
   - Main page: `http://localhost:8000/`
   - API endpoints: `http://localhost:8000/api/`

## 📊 Features

- ✅ **Real-time Government Data**: IMD, Agmarknet, ICAR integration
- ✅ **AI Intelligence**: Google AI Studio + Ollama integration
- ✅ **Location-based Services**: Dynamic updates for 50+ Indian cities
- ✅ **Multilingual Support**: Hindi, English, Hinglish
- ✅ **Comprehensive APIs**: All agricultural services available
- ✅ **Production Ready**: Deployed on Render

## 🌐 Deployment

- **GitHub**: https://github.com/Arnavmishra002/agri_advisory_app
- **Live API**: https://krishmitra-zrk4.onrender.com/

## 📝 Next Steps

1. **Frontend Rebuild**: Create new UI components
2. **API Integration**: Connect frontend to existing APIs
3. **Testing**: Validate all API endpoints
4. **Deployment**: Deploy updated frontend

## 🔍 API Testing

All APIs are functional and ready for frontend integration. Test endpoints using:
- Postman
- curl commands
- Frontend HTTP requests

---

**Status**: ✅ Backend APIs Ready | 🔄 Frontend Removed for Rebuilding