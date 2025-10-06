# Krishimitra AI - Manual Startup Commands

## 🚀 Complete Manual Startup Guide

### Step 1: Navigate to Project Directory
```cmd
cd C:\AI\agri_advisory_app
```

### Step 2: Create Virtual Environment
```cmd
python -m venv venv
```

### Step 3: Activate Virtual Environment
```cmd
venv\Scripts\activate
```

### Step 4: Install Dependencies
```cmd
pip install -r requirements.txt
```

### Step 5: Setup Database
```cmd
python manage.py makemigrations
python manage.py migrate
```

### Step 6: Create Superuser (Optional)
```cmd
python manage.py createsuperuser
```

### Step 7: Start Django Development Server
```cmd
python manage.py runserver 8000
```

### Step 8: Access Your Application
- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/docs/
- **Admin Panel**: http://localhost:8000/admin/

---

## 🔧 Advanced Setup (Optional)

### Start Redis Server (for caching)
```cmd
redis-server
```

### Start Celery Worker (for background tasks)
```cmd
celery -A core worker --loglevel=info
```

### Start Celery Beat (for scheduled tasks)
```cmd
celery -A core beat --loglevel=info
```

---

## 📋 Quick Start Commands (All in One)

```cmd
cd C:\AI\agri_advisory_app
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py runserver 8000
```

---

## 🛠️ Troubleshooting Commands

### Check Django Version
```cmd
python -m django --version
```

### Check Installed Packages
```cmd
pip list
```

### Check Database Status
```cmd
python manage.py showmigrations
```

### Collect Static Files (if needed)
```cmd
python manage.py collectstatic
```

### Check Project Structure
```cmd
dir
```

---

## 🌐 API Testing Commands

### Test Chatbot API
```cmd
curl -X POST http://localhost:8000/api/advisories/chatbot/ -H "Content-Type: application/json" -d "{\"query\": \"Hello\", \"language\": \"en\"}"
```

### Test Weather API
```cmd
curl http://localhost:8000/api/weather/current/?lat=28.6139&lon=77.2090&lang=en
```

### Test Market Prices API
```cmd
curl http://localhost:8000/api/market-prices/prices/?lat=28.6139&lon=77.2090&lang=en&product=wheat
```

---

## 📱 Service URLs

- **Main App**: http://localhost:8000/
- **API Root**: http://localhost:8000/api/
- **Chatbot**: http://localhost:8000/api/advisories/chatbot/
- **Weather**: http://localhost:8000/api/weather/
- **Market**: http://localhost:8000/api/market-prices/
- **Admin**: http://localhost:8000/admin/
- **API Docs**: http://localhost:8000/api/schema/swagger-ui/

---

## ⚡ Quick Commands Summary

| Action | Command |
|--------|---------|
| **Start Project** | `cd C:\AI\agri_advisory_app && venv\Scripts\activate && python manage.py runserver 8000` |
| **Install Dependencies** | `pip install -r requirements.txt` |
| **Database Setup** | `python manage.py migrate` |
| **Create Admin** | `python manage.py createsuperuser` |
| **Check Status** | `python manage.py check` |
| **Stop Server** | `Ctrl + C` |

---

## 🎯 Production Commands

### Install Production Dependencies
```cmd
pip install gunicorn whitenoise psycopg2-binary
```

### Run with Gunicorn
```cmd
gunicorn core.wsgi:application --bind 0.0.0.0:8000
```

### Run with Production Settings
```cmd
python manage.py runserver 0.0.0.0:8000 --settings=core.settings_production
```

---

**🌾 Krishimitra AI - Empowering Indian Farmers with Intelligent Agricultural Guidance!**
