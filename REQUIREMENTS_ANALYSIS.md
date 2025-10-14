# 📋 Requirements Analysis - Krishimitra AI

## 🔍 **ANALYSIS COMPLETED**

After analyzing all files in the project, here are the missing dependencies and requirements that need to be added:

---

## ❌ **MISSING DEPENDENCIES**

### 1. **System Monitoring**
- **`psutil`** - Used in `performance_monitor.py` for system metrics
- **Status**: ❌ Missing from requirements.txt

### 2. **Async HTTP Requests**
- **`aiohttp`** - Used in multiple consolidated services
- **Status**: ✅ Present in requirements.txt

### 3. **Machine Learning Model Persistence**
- **`joblib`** - Used in `consolidated_crop_service.py` for model saving/loading
- **Status**: ❌ Missing from requirements.txt

### 4. **JWT Authentication**
- **`djangorestframework-simplejwt`** - Used in settings and URLs
- **Status**: ✅ Present in requirements-production.txt, ❌ Missing from requirements.txt

### 5. **IP Address Handling**
- **`ipaddress`** - Referenced in middleware comments but not imported
- **Status**: ✅ Built-in Python module (no installation needed)

### 6. **Error Monitoring**
- **`sentry-sdk`** - Used in settings.py
- **Status**: ❌ Missing from both requirements files

### 7. **Text-to-Speech**
- **`gtts`** and **`pyttsx3`** - Used for TTS functionality
- **Status**: ✅ Present in requirements-production.txt, ❌ Missing from requirements.txt

### 8. **Geolocation**
- **`geopy`** - Used for location services
- **Status**: ✅ Present in requirements-production.txt, ❌ Missing from requirements.txt

---

## ✅ **PRESENT DEPENDENCIES**

### **Core Dependencies (All Present):**
- ✅ Django>=4.2.0
- ✅ djangorestframework>=3.14.0
- ✅ django-cors-headers>=4.0.0
- ✅ django-filter>=23.0
- ✅ psycopg2-binary>=2.9.0
- ✅ redis>=4.5.0
- ✅ celery>=5.3.0
- ✅ django-celery-beat>=2.5.0
- ✅ scikit-learn>=1.3.0
- ✅ numpy>=1.24.0
- ✅ pandas>=2.0.0
- ✅ nltk>=3.8.0
- ✅ requests>=2.31.0
- ✅ urllib3>=2.0.0
- ✅ python-dateutil>=2.8.0
- ✅ pytz>=2023.3
- ✅ gunicorn>=21.0.0
- ✅ whitenoise>=6.5.0
- ✅ python-decouple>=3.8
- ✅ dj-database-url>=2.1.0
- ✅ drf-spectacular>=0.26.0
- ✅ django-ratelimit>=4.0.0
- ✅ streamlit>=1.28.0
- ✅ plotly>=5.17.0
- ✅ Pillow>=10.0.0
- ✅ google-generativeai>=0.3.0
- ✅ google-ai-generativelanguage>=0.4.0
- ✅ aiohttp>=3.8.0
- ✅ asyncio-mqtt>=0.13.0
- ✅ uvloop>=0.17.0
- ✅ beautifulsoup4>=4.12.0
- ✅ lxml>=4.9.0

---

## 🔧 **REQUIRED FIXES**

### **1. Update requirements.txt**
Add missing dependencies to the main requirements file.

### **2. Update requirements-production.txt**
Ensure all production dependencies are included.

### **3. Fix Import Issues**
- Add proper ipaddress import in middleware
- Ensure sentry_sdk is properly imported in settings

### **4. Environment Variables**
Ensure all required environment variables are documented.

---

## 📊 **DEPENDENCY SUMMARY**

| Category | Total | Present | Missing | Status |
|----------|-------|---------|---------|---------|
| **Core Django** | 5 | 5 | 0 | ✅ Complete |
| **Database** | 1 | 1 | 0 | ✅ Complete |
| **Caching/Tasks** | 3 | 3 | 0 | ✅ Complete |
| **AI/ML** | 4 | 4 | 0 | ✅ Complete |
| **HTTP/Requests** | 2 | 2 | 0 | ✅ Complete |
| **Data Processing** | 2 | 2 | 0 | ✅ Complete |
| **Development** | 2 | 2 | 0 | ✅ Complete |
| **Production** | 4 | 4 | 0 | ✅ Complete |
| **API Documentation** | 1 | 1 | 0 | ✅ Complete |
| **Security** | 1 | 1 | 0 | ✅ Complete |
| **Frontend** | 3 | 3 | 0 | ✅ Complete |
| **Google AI** | 2 | 2 | 0 | ✅ Complete |
| **Performance** | 3 | 3 | 0 | ✅ Complete |
| **Data Processing** | 2 | 2 | 0 | ✅ Complete |
| **Missing Critical** | 5 | 0 | 5 | ❌ Needs Fix |

---

## 🎯 **NEXT STEPS**

1. **Update requirements.txt** with missing dependencies
2. **Update requirements-production.txt** to match
3. **Fix import issues** in middleware and settings
4. **Test installation** with updated requirements
5. **Document environment variables**

---

**Total Missing Dependencies: 5 critical dependencies need to be added**



