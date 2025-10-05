# 🚀 Krishimitra Project - Complete Startup Guide

## 📋 Quick Start (Recommended)

### Option 1: Automated Startup (Easiest)
```bash
# Navigate to project directory
cd C:\AI\agri_advisory_app

# Run the automated startup script
.\start_all.bat
```

This will:
- ✅ Start Django server on http://127.0.0.1:8000
- ✅ Start Streamlit app on http://127.0.0.1:8501
- ✅ Test API endpoints
- ✅ Activate virtual environment automatically

---

## 🔧 Manual Startup (Step-by-Step)

### Step 1: Navigate to Project Directory
```bash
cd C:\AI\agri_advisory_app
```

### Step 2: Activate Virtual Environment
```bash
.\venv\Scripts\activate
```

### Step 3: Start Django Server
```bash
# Start Django server in background
start "Django Server" cmd /k "cd /d C:\AI\agri_advisory_app && .\venv\Scripts\activate && python manage.py runserver 127.0.0.1:8000"
```

### Step 4: Test Django Server (Optional)
```bash
# Test API endpoints
python quick_test.py
```

### Step 5: Start Streamlit Frontend
```bash
# Start Streamlit app
start "Streamlit App" cmd /k "cd /d C:\AI\agri_advisory_app && .\venv\Scripts\activate && streamlit run streamlit_final.py --server.port 8501 --server.address 127.0.0.1"
```

---

## 🌐 Access Your Application

### Django API Server
- **URL**: http://127.0.0.1:8000
- **API Documentation**: http://127.0.0.1:8000/api/schema/swagger-ui/
- **Admin Panel**: http://127.0.0.1:8000/admin/

### Streamlit Frontend
- **URL**: http://127.0.0.1:8501
- **Features**: 
  - 🤖 AI Chatbot with 25+ language support
  - 🌦️ Real-time weather data
  - 🌱 Trending crops information
  - 💰 Market prices and analysis
  - 📋 Government schemes and advisory
  - 🎤 Voice input capabilities

---

## 🧪 Testing Your Setup

### 1. Test Django API
```bash
# Test basic API connectivity
curl http://127.0.0.1:8000/api/

# Test weather API
curl "http://127.0.0.1:8000/api/weather/current/?lat=28.6139&lon=77.2090&lang=en"

# Test chatbot API
curl -X POST http://127.0.0.1:8000/api/advisories/chatbot/ \
  -H "Content-Type: application/json" \
  -d '{"query": "What crops should I grow in Delhi?", "language": "en"}'
```

### 2. Test Streamlit Features
1. Open http://127.0.0.1:8501
2. Try the AI Chatbot with different languages
3. Check Weather & Location tab
4. View Trending Crops
5. Browse Market Prices
6. Explore Agricultural Advisory

---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### 1. "Streamlit command not found"
```bash
# Make sure virtual environment is activated
.\venv\Scripts\activate
pip install streamlit
```

#### 2. "Django server not starting"
```bash
# Check if port 8000 is available
netstat -an | findstr :8000

# Try different port
python manage.py runserver 127.0.0.1:8001
```

#### 3. "API endpoints returning 404"
```bash
# Make sure Django server is running
# Check server logs for errors
# Verify URLs are correct
```

#### 4. "Virtual environment issues"
```bash
# Recreate virtual environment
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

---

## 📊 Project Status

### ✅ Completed Features
- [x] Django REST API with comprehensive endpoints
- [x] Advanced AI Chatbot with ChatGPT-like capabilities
- [x] Real-time weather integration (IMD APIs)
- [x] Market prices tracking (Agmarknet)
- [x] Trending crops data (e-NAM)
- [x] Government schemes integration
- [x] Multilingual support (25+ languages)
- [x] Voice input/output capabilities
- [x] Full page translation (Hindi/English)
- [x] Chat history persistence
- [x] Advanced ML models
- [x] Security enhancements
- [x] Performance optimization
- [x] Comprehensive testing
- [x] Production-ready deployment

### 🎯 Key Features Working
1. **AI Chatbot**: Ask any agricultural question in any language
2. **Weather Data**: Real-time weather with government APIs
3. **Market Prices**: Live mandi prices and trends
4. **Crop Recommendations**: ICAR-based intelligent suggestions
5. **Government Schemes**: Complete scheme information
6. **Voice Input**: Speech recognition for easy interaction
7. **Language Translation**: Full UI translation to Hindi/English

---

## 🚀 Production Deployment

### For Production Use:
1. **Set Environment Variables**:
   ```bash
   DJANGO_SECRET_KEY=your-secret-key
   DJANGO_DEBUG=False
   DATABASE_URL=postgresql://user:pass@host:port/db
   ```

2. **Use Production Server**:
   ```bash
   # Install gunicorn
   pip install gunicorn
   
   # Run with gunicorn
   gunicorn core.wsgi:application --bind 0.0.0.0:8000
   ```

3. **Docker Deployment**:
   ```bash
   # Use existing docker-compose.yml
   docker-compose up -d
   ```

---

## 📞 Support

If you encounter any issues:

1. **Check Logs**: Look at Django server logs and Streamlit logs
2. **Verify Dependencies**: Ensure all packages are installed
3. **Test APIs**: Use the quick_test.py script
4. **Check Network**: Ensure ports 8000 and 8501 are accessible

---

## 🎉 Success!

Once both servers are running, you'll have access to:

- **Complete Agricultural AI Assistant** with government data integration
- **Multilingual support** for Hindi, English, and 25+ other languages
- **Real-time data** from IMD, Agmarknet, and e-NAM
- **Advanced AI capabilities** with ChatGPT-like conversations
- **Voice interaction** for easy user experience
- **Production-ready** system with comprehensive features

**Your Krishimitra Agricultural AI Assistant is now ready to help farmers across India! 🌾**
