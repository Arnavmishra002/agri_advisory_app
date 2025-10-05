# 🚀 Complete Usage Guide: From Server Start to Full Feature Usage

## 📋 **Step 1: Start the Server**

### **Option A: Using Batch File (Easiest)**
```cmd
# Open Command Prompt and navigate to project
cd C:\AI\agri_advisory_app

# Run the enhanced startup script
start_all_enhanced.bat
```

### **Option B: Manual Commands**
```cmd
# Navigate to project
cd C:\AI\agri_advisory_app

# Activate virtual environment
venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements_basic.txt

# Create migrations
python manage.py makemigrations advisory

# Apply migrations
python manage.py migrate

# Start server
python manage.py runserver 127.0.0.1:8000
```

## 🌐 **Step 2: Access Your Application**

After server starts, open these URLs in your browser:

### **Main Access Points:**
- **API Documentation**: http://localhost:8000/api/schema/swagger-ui/
- **Admin Panel**: http://localhost:8000/admin/
- **Main API**: http://localhost:8000/api/
- **Health Check**: http://localhost:8000/api/health/

### **Admin Credentials:**
- Username: `admin`
- Password: `admin123`

## 🤖 **Step 3: Test Enhanced Chatbot Features**

### **3.1 Test Basic Chatbot (Automated)**
```cmd
# Open another Command Prompt
cd C:\AI\agri_advisory_app
venv\Scripts\activate.bat
test_chatbot.bat
```

### **3.2 Test via Browser (Interactive)**
1. Go to: http://localhost:8000/api/schema/swagger-ui/
2. Find `/api/advisories/chatbot/` endpoint
3. Click "Try it out"
4. Enter test data:
```json
{
  "query": "Hello! How are you?",
  "language": "en",
  "user_id": "test_user",
  "session_id": "test_session_001"
}
```
5. Click "Execute"

### **3.3 Test Multilingual Support**

#### **English Chat:**
```cmd
curl -X POST http://localhost:8000/api/advisories/chatbot/ -H "Content-Type: application/json" -d "{\"query\": \"Hello! How are you?\", \"language\": \"en\", \"user_id\": \"test_user\"}"
```

#### **Hindi Chat:**
```cmd
curl -X POST http://localhost:8000/api/advisories/chatbot/ -H "Content-Type: application/json" -d "{\"query\": \"नमस्ते! आप कैसे हैं?\", \"language\": \"hi\", \"user_id\": \"test_user\"}"
```

#### **Bengali Chat:**
```cmd
curl -X POST http://localhost:8000/api/advisories/chatbot/ -H "Content-Type: application/json" -d "{\"query\": \"নমস্কার! আপনি কেমন আছেন?\", \"language\": \"bn\", \"user_id\": \"test_user\"}"
```

#### **Telugu Chat:**
```cmd
curl -X POST http://localhost:8000/api/advisories/chatbot/ -H "Content-Type: application/json" -d "{\"query\": \"నమస్కారం! మీరు ఎలా ఉన్నారు?\", \"language\": \"te\", \"user_id\": \"test_user\"}"
```

#### **Tamil Chat:**
```cmd
curl -X POST http://localhost:8000/api/advisories/chatbot/ -H "Content-Type: application/json" -d "{\"query\": \"வணக்கம்! நீங்கள் எப்படி இருக்கிறீர்கள்?\", \"language\": \"ta\", \"user_id\": \"test_user\"}"
```

### **3.4 Test Agricultural Queries**

#### **Crop Recommendation:**
```cmd
curl -X POST http://localhost:8000/api/advisories/chatbot/ -H "Content-Type: application/json" -d "{\"query\": \"What crops should I plant in Delhi?\", \"language\": \"en\", \"user_id\": \"test_user\"}"
```

#### **Weather Query:**
```cmd
curl -X POST http://localhost:8000/api/advisories/chatbot/ -H "Content-Type: application/json" -d "{\"query\": \"What's the weather like in Mumbai?\", \"language\": \"en\", \"user_id\": \"test_user\"}"
```

#### **Market Price Query:**
```cmd
curl -X POST http://localhost:8000/api/advisories/chatbot/ -H "Content-Type: application/json" -d "{\"query\": \"What are the current wheat prices?\", \"language\": \"en\", \"user_id\": \"test_user\"}"
```

## 🌤️ **Step 4: Test Weather API**

### **Current Weather:**
```cmd
# Delhi weather
curl "http://localhost:8000/api/weather/current/?lat=28.6139&lon=77.2090&lang=en"

# Mumbai weather
curl "http://localhost:8000/api/weather/current/?lat=19.0760&lon=72.8777&lang=en"

# Chennai weather
curl "http://localhost:8000/api/weather/current/?lat=13.0827&lon=80.2707&lang=en"
```

### **Weather Forecast:**
```cmd
# 3-day forecast for Delhi
curl "http://localhost:8000/api/weather/forecast/?lat=28.6139&lon=77.2090&lang=en&days=3"
```

## 📊 **Step 5: Test Market Prices API**

### **Get Market Prices:**
```cmd
# All prices for Delhi area
curl "http://localhost:8000/api/market-prices/prices/?lat=28.6139&lon=77.2090&lang=en"

# Specific product prices
curl "http://localhost:8000/api/market-prices/prices/?lat=28.6139&lon=77.2090&lang=en&product=wheat"
```

### **Get Trending Crops:**
```cmd
curl "http://localhost:8000/api/trending-crops/?lat=28.6139&lon=77.2090&lang=en"
```

## 🌾 **Step 6: Test Agricultural Features**

### **6.1 Crop Recommendations:**
```cmd
curl -X POST http://localhost:8000/api/advisories/ml_crop_recommendation/ -H "Content-Type: application/json" -d "{\"soil_type\": \"Loamy\", \"latitude\": 28.6139, \"longitude\": 77.2090, \"season\": \"kharif\", \"user_id\": \"test_user\", \"forecast_days\": 7}"
```

### **6.2 Fertilizer Recommendations:**
```cmd
curl -X POST http://localhost:8000/api/advisories/fertilizer_recommendation/ -H "Content-Type: application/json" -d "{\"crop_type\": \"wheat\", \"soil_type\": \"Loamy\", \"season\": \"rabi\", \"area_hectares\": 2.0, \"language\": \"en\"}"
```

### **6.3 Yield Prediction:**
```cmd
curl -X POST http://localhost:8000/api/advisories/predict_yield/ -H "Content-Type: application/json" -d "{\"crop_type\": \"wheat\", \"soil_type\": \"Loamy\", \"temperature\": 25.0, \"rainfall\": 800.0, \"humidity\": 60.0, \"ph\": 6.5, \"organic_matter\": 2.0}"
```

## 💬 **Step 7: Test Chat History Persistence**

### **7.1 Start a Conversation Session:**
```cmd
# First message
curl -X POST http://localhost:8000/api/advisories/chatbot/ -H "Content-Type: application/json" -d "{\"query\": \"Hello, I'm a farmer from Punjab\", \"language\": \"en\", \"user_id\": \"farmer_001\", \"session_id\": \"session_001\"}"

# Second message (should remember context)
curl -X POST http://localhost:8000/api/advisories/chatbot/ -H "Content-Type: application/json" -d "{\"query\": \"What crops grow well here?\", \"language\": \"en\", \"user_id\": \"farmer_001\", \"session_id\": \"session_001\"}"

# Third message (should maintain conversation)
curl -X POST http://localhost:8000/api/advisories/chatbot/ -H "Content-Type: application/json" -d "{\"query\": \"Tell me about wheat cultivation\", \"language\": \"en\", \"user_id\": \"farmer_001\", \"session_id\": \"session_001\"}"
```

### **7.2 Test Different Languages in Same Session:**
```cmd
# English
curl -X POST http://localhost:8000/api/advisories/chatbot/ -H "Content-Type: application/json" -d "{\"query\": \"Hello\", \"language\": \"en\", \"user_id\": \"test_user\", \"session_id\": \"multi_lang_session\"}"

# Hindi
curl -X POST http://localhost:8000/api/advisories/chatbot/ -H "Content-Type: application/json" -d "{\"query\": \"नमस्ते\", \"language\": \"hi\", \"user_id\": \"test_user\", \"session_id\": \"multi_lang_session\"}"

# Bengali
curl -X POST http://localhost:8000/api/advisories/chatbot/ -H "Content-Type: application/json" -d "{\"query\": \"নমস্কার\", \"language\": \"bn\", \"user_id\": \"test_user\", \"session_id\": \"multi_lang_session\"}"
```

## 🧪 **Step 8: Run Comprehensive Tests**

### **8.1 Django Tests:**
```cmd
# Run all tests
python manage.py test

# Run specific test
python manage.py test advisory.tests

# Run with verbose output
python manage.py test --verbosity=2
```

### **8.2 Chatbot Tests:**
```cmd
# Run the automated test script
python simple_test_chatbot.py

# Or use the batch file
test_chatbot.bat
```

## 🎤 **Step 9: Test Voice Features**

### **9.1 Text-to-Speech:**
```cmd
curl -X POST http://localhost:8000/api/tts/speak/ -H "Content-Type: application/json" -d "{\"text\": \"Hello, welcome to the agricultural advisory system\", \"language\": \"en\"}"
```

### **9.2 Hindi TTS:**
```cmd
curl -X POST http://localhost:8000/api/tts/speak/ -H "Content-Type: application/json" -d "{\"text\": \"नमस्ते, कृषि सलाहकार प्रणाली में आपका स्वागत है\", \"language\": \"hi\"}"
```

## 🐛 **Step 10: Test Pest Detection**

### **10.1 Upload Image for Pest Detection:**
```cmd
# Note: This requires an image file
curl -X POST http://localhost:8000/api/pest-detection/detect/ -F "image=@path/to/your/image.jpg"
```

## 📱 **Step 11: Test SMS/IVR Integration**

### **11.1 SMS Integration:**
```cmd
curl -X POST http://localhost:8000/api/sms-ivr/receive-sms/ -H "Content-Type: application/json" -d "{\"phone_number\": \"+919876543210\", \"message\": \"What crops should I plant?\"}"
```

### **11.2 IVR Integration:**
```cmd
curl -X POST http://localhost:8000/api/sms-ivr/ivr-input/ -H "Content-Type: application/json" -d "{\"phone_number\": \"+919876543210\", \"user_input\": \"1\"}"
```

## 👥 **Step 12: Test Community Features**

### **12.1 Forum Posts:**
```cmd
# Get forum posts
curl "http://localhost:8000/api/forum/"

# Create forum post (requires authentication)
curl -X POST http://localhost:8000/api/forum/ -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_TOKEN" -d "{\"title\": \"Best crops for rainy season\", \"content\": \"What are the best crops to plant during monsoon?\"}"
```

## 📊 **Step 13: Test Analytics and Feedback**

### **13.1 Submit Feedback:**
```cmd
curl -X POST http://localhost:8000/api/advisories/collect_feedback/ -H "Content-Type: application/json" -d "{\"user_id\": \"test_user\", \"session_id\": \"session_001\", \"prediction_type\": \"crop_recommendation\", \"input_data\": {\"soil_type\": \"Loamy\"}, \"system_prediction\": {\"crop\": \"wheat\"}, \"actual_result\": {\"crop\": \"wheat\"}, \"feedback_rating\": 5, \"feedback_text\": \"Very helpful recommendation!\"}"
```

### **13.2 Get Feedback Analytics:**
```cmd
curl "http://localhost:8000/api/advisories/feedback_analytics/?days=30"
```

### **13.3 Get Model Performance:**
```cmd
curl "http://localhost:8000/api/advisories/model_performance/"
```

## 🎯 **Step 14: Complete Feature Testing Script**

Create a comprehensive test script:

```cmd
# Save this as test_all_features.bat
@echo off
echo Testing All Enhanced Chatbot Features...
echo.

echo 1. Testing English Chat...
curl -X POST http://localhost:8000/api/advisories/chatbot/ -H "Content-Type: application/json" -d "{\"query\": \"Hello! I'm a farmer from Delhi\", \"language\": \"en\", \"user_id\": \"test_user\"}"
echo.

echo 2. Testing Hindi Chat...
curl -X POST http://localhost:8000/api/advisories/chatbot/ -H "Content-Type: application/json" -d "{\"query\": \"नमस्ते! मैं दिल्ली का किसान हूं\", \"language\": \"hi\", \"user_id\": \"test_user\"}"
echo.

echo 3. Testing Agricultural Query...
curl -X POST http://localhost:8000/api/advisories/chatbot/ -H "Content-Type: application/json" -d "{\"query\": \"What crops should I plant in Delhi?\", \"language\": \"en\", \"user_id\": \"test_user\"}"
echo.

echo 4. Testing Weather API...
curl "http://localhost:8000/api/weather/current/?lat=28.6139&lon=77.2090&lang=en"
echo.

echo 5. Testing Market Prices...
curl "http://localhost:8000/api/market-prices/prices/?lat=28.6139&lon=77.2090&lang=en"
echo.

echo 6. Testing Chat History...
curl -X POST http://localhost:8000/api/advisories/chatbot/ -H "Content-Type: application/json" -d "{\"query\": \"Hello\", \"language\": \"en\", \"user_id\": \"test_user\", \"session_id\": \"test_session\"}"
echo.

curl -X POST http://localhost:8000/api/advisories/chatbot/ -H "Content-Type: application/json" -d "{\"query\": \"Remember me?\", \"language\": \"en\", \"user_id\": \"test_user\", \"session_id\": \"test_session\"}"
echo.

echo All tests completed!
pause
```

## ✅ **Verification Checklist**

After running all commands, verify:

- [ ] Server starts without errors
- [ ] API documentation loads at http://localhost:8000/api/schema/swagger-ui/
- [ ] Chatbot responds in multiple languages
- [ ] Chat history persists across messages
- [ ] Weather API returns data
- [ ] Market prices API works
- [ ] Agricultural queries get relevant responses
- [ ] Voice features work (TTS)
- [ ] Database migrations applied successfully
- [ ] Admin panel accessible

## 🎉 **You're All Set!**

Your enhanced agricultural chatbot with ChatGPT-like capabilities is now fully functional with:
- ✅ 25+ language support
- ✅ Persistent chat history
- ✅ Advanced AI conversations
- ✅ Agricultural expertise
- ✅ Real-time weather and market data
- ✅ Voice support
- ✅ Community features
- ✅ Analytics and feedback system

**Enjoy your enhanced agricultural chatbot!** 🌾🤖
